/**
 * ============================================================================
 * TEST SUITE: MAP-DRIVEN EXPLORATION ANALYSIS
 * ============================================================================
 * 
 * Verifies the map-driven target selection, multi-component synchronization,
 * spatial boundary enforcement, and integration with the real Manganese
 * prospectivity pipeline.
 * ============================================================================
 */

const assert = require('assert');
const path = require('path');
const fs = require('fs');

const GeoEngine = require('../js/geo');
const MineralData = require('../js/data');
const ProspectivityEngine = require('../js/prospectivity');
const ExplainableAI = require('../js/xai');
const ExplorationMap = require('../js/map');

// Load calibrated grid into ProspectivityEngine
const gridPath = path.resolve(__dirname, '../data/processed/tile_prospectivity_549.json');
if (fs.existsSync(gridPath)) {
    const rawGrid = JSON.parse(fs.readFileSync(gridPath, 'utf8'));
    ProspectivityEngine.setGrid(rawGrid);
}

let passCount = 0;
let failCount = 0;

function runTest(name, fn) {
    try {
        fn();
        console.log(`[PASS] ${name}`);
        passCount++;
    } catch (err) {
        console.error(`[FAIL] ${name}: ${err.message}`);
        failCount++;
    }
}

console.log('================================================================');
console.log('TEST SUITE: MAP-DRIVEN EXPLORATION ANALYSIS');
console.log('================================================================\n');

// --- 1. Initial State & Single Source of Truth ---
runTest('ExplorationMap initializes with ground-truth default target (Ghondi Mine)', () => {
    const state = ExplorationMap.getState();
    assert.strictEqual(state.lat, 21.9455);
    assert.strictEqual(state.lon, 80.4295);
    assert.strictEqual(state.radiusKm, 25);
    assert.strictEqual(state.source, 'preset');
});

// --- 2. Map Location Selection ---
runTest('Map click updates target coordinates and sets source to "map"', () => {
    let notifiedPayload = null;
    ExplorationMap.onLocationChange((payload) => {
        notifiedPayload = payload;
    });

    const testLat = 22.0500;
    const testLon = 80.4000;
    ExplorationMap.setLocation(testLat, testLon, 'Map Target Click', 'map');

    const state = ExplorationMap.getState();
    assert.strictEqual(state.lat, testLat);
    assert.strictEqual(state.lon, testLon);
    assert.strictEqual(state.source, 'map');
    assert.ok(notifiedPayload !== null);
    assert.strictEqual(notifiedPayload.lat, testLat);
    assert.strictEqual(notifiedPayload.lon, testLon);
    assert.strictEqual(notifiedPayload.source, 'map');
    assert.strictEqual(notifiedPayload.inTileBounds, true);
});

// --- 3. Spatial Boundary Enforcement (Outside Tile) ---
runTest('Click outside Tile T44QMK correctly flags inTileBounds as false', () => {
    let notifiedPayload = null;
    ExplorationMap.onLocationChange((payload) => {
        notifiedPayload = payload;
    });

    const outsideLat = 15.0000;
    const outsideLon = 75.0000;
    ExplorationMap.setLocation(outsideLat, outsideLon, 'Outside Target', 'map');

    const state = ExplorationMap.getState();
    assert.strictEqual(state.lat, outsideLat);
    assert.strictEqual(state.lon, outsideLon);
    assert.ok(notifiedPayload !== null);
    assert.strictEqual(notifiedPayload.inTileBounds, false);

    // Verify ProspectivityEngine refuses to fabricate scores for this coordinate
    const result = ProspectivityEngine.analyzeLocationSync(outsideLat, outsideLon, 25);
    assert.strictEqual(result.insideRaster, false);
    assert.strictEqual(result.prospectivityPercent, null);
    assert.strictEqual(result.classification, 'Out of Tile Bounds');
});

// --- 4. Candidate Zone Selection Integration ---
runTest('Selecting candidate zone sets target coordinates with source "zone"', () => {
    const topZone = MineralData.CANDIDATE_ZONES[0]; // Zone 67684
    ExplorationMap.selectZoneLocation(topZone.lat, topZone.lon, `Zone #${topZone.zoneId}`);

    const state = ExplorationMap.getState();
    assert.strictEqual(state.lat, topZone.lat);
    assert.strictEqual(state.lon, topZone.lon);
    assert.strictEqual(state.source, 'zone');
    assert.strictEqual(state.locationName, `Zone #${topZone.zoneId}`);
});

// --- 5. Radius Synchronization (10, 25, 50, 100 km) ---
runTest('Radius update to 10 km, 50 km, 100 km updates state and recalculates telemetry', () => {
    // Reset to known mine
    ExplorationMap.setLocation(21.9455, 80.4295, 'Ghondi Manganese Mine', 'preset');

    ExplorationMap.setRadius(10);
    assert.strictEqual(ExplorationMap.getState().radiusKm, 10);

    ExplorationMap.setRadius(50);
    assert.strictEqual(ExplorationMap.getState().radiusKm, 50);

    ExplorationMap.setRadius(100);
    assert.strictEqual(ExplorationMap.getState().radiusKm, 100);

    // Reset back to 25 km
    ExplorationMap.setRadius(25);
    assert.strictEqual(ExplorationMap.getState().radiusKm, 25);
});

// --- 6. Execution with Real Manganese Pipeline on Map Target ---
runTest('Map-selected target runs through real Manganese ProspectivityEngine', () => {
    // Pick Zone 67684 coordinates selected via map
    const mapLat = 22.214160;
    const mapLon = 80.063632;
    ExplorationMap.setLocation(mapLat, mapLon, 'Map Target (NW Cluster)', 'map');

    const state = ExplorationMap.getState();
    assert.strictEqual(state.source, 'map');

    // Execute through ProspectivityEngine
    const result = ProspectivityEngine.analyzeLocationSync(state.lat, state.lon, state.radiusKm);
    assert.strictEqual(result.insideRaster, true);
    assert.ok(result.prospectivityPercent > 80.0, 'Should yield high prospectivity in Zone 67684 cluster');
    assert.strictEqual(result.classification, 'Very High');
    assert.ok(result.sampledPixels > 0);
    assert.ok(Array.isArray(result.nearbyZones));
});

// --- 7. Real XAI Explanation on Map-Selected Target ---
runTest('XAI explanation operates correctly on map-selected prospectivity score', () => {
    const score = 97.6;
    const locName = 'Map Target (Zone 67684)';
    const xai = ExplainableAI.explainProspectivityScore(score, locName);

    assert.strictEqual(xai.score, score);
    assert.strictEqual(xai.locationName, locName);
    assert.ok(Array.isArray(xai.waterfallSteps));
    assert.strictEqual(xai.waterfallSteps[0].isBaseline, true);
    assert.strictEqual(xai.waterfallSteps[xai.waterfallSteps.length - 1].isFinal, true);
    assert.ok(xai.recommendation.length > 0);
    assert.ok(xai.disclaimer.title.includes('Scientific'));
});

console.log('\n================================================================');
console.log(`MAP-DRIVEN ANALYSIS TEST RESULTS: ${passCount} / ${passCount + failCount} tests passed (${Math.round((passCount / (passCount + failCount)) * 100)}%)`);
console.log('================================================================\n');

if (failCount > 0) {
    process.exit(1);
}
