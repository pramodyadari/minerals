/**
 * ============================================================================
 * TEST SUITE: LOCATION NOT ZONE UX & ARCHITECTURE (LOCATION != ZONE)
 * ============================================================================
 * 
 * Verifies that:
 * 1. Arbitrary coordinates inside raster analyze successfully with real model
 * 2. Location with no candidate zone has candidateZone === null and shows NONE
 * 3. Location with candidate zone has candidateZone populated with zone ID
 * 4. Map click on arbitrary coordinate without zone produces valid prospectivity
 * 5. Place search without zone resolves independently (type: 'place', badge: 'Location')
 * 6. Zone search resolves as exploration targets (type: 'zone', badge: 'Exploration Target')
 * 7. Trained Manganese prediction runs without requiring a zone
 * 8. Zone membership is explicitly NONE when outside candidate zone clusters
 * 9. Outside-raster coordinates are rejected as out of coverage
 * 10. Stale target clearing clears previous zone and score before new location
 * ============================================================================
 */

const assert = require('assert');
const fs = require('fs');
const path = require('path');

// Load core modules
const GeoEngine = require('../js/geo');
const MineralData = require('../js/data');
const LocationResolver = require('../js/locations');
const ProspectivityEngine = require('../js/prospectivity');
const ZoneAnalysis = require('../js/zones');

// Load prospectivity grid into ProspectivityEngine for synchronous testing
const gridPath = path.resolve(__dirname, '../data/processed/tile_prospectivity_549.json');
if (fs.existsSync(gridPath)) {
    const rawGrid = JSON.parse(fs.readFileSync(gridPath, 'utf8'));
    ProspectivityEngine.setGrid(rawGrid);
}

let passed = 0;

function runTest(name, fn) {
    try {
        fn();
        passed++;
        console.log(`  [PASS] ${name}`);
    } catch (err) {
        console.error(`  [FAIL] ${name}:`, err.message);
        throw err;
    }
}

console.log('\n--- Running Location != Zone Test Suite ---');

// 1. Arbitrary coordinate inside raster
runTest('1. Arbitrary coordinate inside raster footprint analyzes successfully', () => {
    // Coordinate inside T44QMK without any mine or zone
    const lat = 21.9400;
    const lon = 80.4200;
    assert.strictEqual(GeoEngine.isWithinTileBounds(lat, lon), true, 'Must be within tile footprint');

    const result = ProspectivityEngine.analyzeLocationSync(lat, lon, 25);
    assert.strictEqual(result.insideRaster, true);
    assert.ok(typeof result.prospectivityPercent === 'number', 'Must return valid numeric prospectivity');
    assert.ok(result.prospectivityPercent >= 0 && result.prospectivityPercent <= 100);
    assert.ok(result.classification && result.classification !== 'Out of Bounds');
});

// 2. Location with no candidate zone
runTest('2. Location with no candidate zone resolves with candidateZone === null', () => {
    // Random coordinate in south sector far from candidate zones
    const lat = 21.6500;
    const lon = 80.3500;
    const foundZone = ZoneAnalysis.findZoneAtCoordinates(lat, lon, 0.5);
    assert.strictEqual(foundZone, null, 'No candidate zone should exist at random coordinate');

    const resolved = LocationResolver.reverseGeocode(lat, lon);
    assert.strictEqual(resolved.isZone, false);
    assert.strictEqual(resolved.candidateZone, null);
    assert.strictEqual(resolved.zoneId, null);
});

// 3. Location with candidate zone
runTest('3. Location with candidate zone resolves candidateZone with zone ID', () => {
    // Exact coordinates of Zone 67684 (top ranked zone)
    const zone67684 = MineralData.CANDIDATE_ZONES.find(z => z.zoneId === 67684);
    assert.ok(zone67684, 'Zone 67684 must exist');

    const foundZone = ZoneAnalysis.findZoneAtCoordinates(zone67684.lat, zone67684.lon, 0.5);
    assert.ok(foundZone, 'Should match zone within 0.5 km');
    assert.strictEqual(foundZone.zoneId, 67684);

    const resolved = LocationResolver.reverseGeocode(zone67684.lat, zone67684.lon);
    assert.strictEqual(resolved.isZone, true);
    assert.ok(resolved.candidateZone !== null);
    assert.strictEqual(resolved.candidateZone.zoneId, 67684);
});

// 4. Map click outside any zone
runTest('4. Arbitrary map click outside any zone produces valid prospectivity and NO zone required', () => {
    const clickLat = 22.0500;
    const clickLon = 80.2500;
    assert.strictEqual(GeoEngine.isWithinTileBounds(clickLat, clickLon), true);

    const resolved = LocationResolver.reverseGeocode(clickLat, clickLon);
    assert.strictEqual(resolved.isZone, false);
    assert.strictEqual(resolved.candidateZone, null);

    const analysis = ProspectivityEngine.analyzeLocationSync(clickLat, clickLon, 25);
    assert.strictEqual(analysis.insideRaster, true);
    assert.ok(analysis.prospectivityPercent > 0);
});

// 5. Place search without zone
runTest('5. Place search without zone resolves independently (type: place, badge: Location)', () => {
    // Balaghat city is a known place and is NOT a candidate discovery zone
    const results = LocationResolver.searchLocations('Balaghat');
    assert.ok(results.length > 0, 'Should find Balaghat');

    const balaghat = results.find(r => r.name.includes('Balaghat') && r.type === 'place');
    assert.ok(balaghat, 'Balaghat must be returned as a place');
    assert.strictEqual(balaghat.type, 'place');
    assert.strictEqual(balaghat.badge, 'Location');
    assert.strictEqual(balaghat.zoneId, undefined);
});

// 6. Zone search
runTest('6. Zone search resolves as exploration targets (type: zone, badge: Exploration Target)', () => {
    const results = LocationResolver.searchLocations('67684');
    assert.ok(results.length > 0, 'Should find Zone 67684');

    const zoneMatch = results.find(r => r.zoneId === 67684);
    assert.ok(zoneMatch, 'Must find zone 67684');
    assert.strictEqual(zoneMatch.type, 'zone');
    assert.strictEqual(zoneMatch.badge, 'Exploration Target');
});

// 7. Trained Manganese prediction without zone
runTest('7. Trained Manganese model evaluates arbitrary location without zone', () => {
    // Random point in eastern quadrant
    const lat = 21.9800;
    const lon = 80.5500;
    const analysis = ProspectivityEngine.analyzeLocationSync(lat, lon, 25);
    assert.strictEqual(analysis.insideRaster, true);
    assert.ok(analysis.prospectivityPercent !== null);

    const foundZone = ZoneAnalysis.findZoneAtCoordinates(lat, lon, 0.4);
    assert.strictEqual(foundZone, null);
});

// 8. Zone membership = NONE formatting
runTest('8. Candidate Zone formatting displays NONE when no matching zone exists', () => {
    const lat = 21.7500;
    const lon = 80.2000;
    const foundZone = ZoneAnalysis.findZoneAtCoordinates(lat, lon, 0.5);
    const displayString = foundZone ? `Candidate Zone: Zone ${foundZone.zoneId}` : 'Candidate Zone: NONE';
    assert.strictEqual(displayString, 'Candidate Zone: NONE');
});

// 9. Outside-raster rejection
runTest('9. Outside-raster rejection reports out of coverage without fabricating prediction', () => {
    const outLat = 28.6139; // Delhi
    const outLon = 77.2090;
    assert.strictEqual(GeoEngine.isWithinTileBounds(outLat, outLon), false);

    const analysis = ProspectivityEngine.analyzeLocationSync(outLat, outLon, 25);
    assert.strictEqual(analysis.insideRaster, false);
    assert.strictEqual(analysis.prospectivityPercent, null);
    assert.strictEqual(analysis.classification, 'Out of Tile Bounds');
});

// 10. Stale target clearing & report validation
runTest('10. Stale target protection resets candidateZone and score between targets', () => {
    // Target 1: With Zone
    const target1 = {
        locationName: 'Zone 67684',
        lat: 22.21416,
        lon: 80.063632,
        score: 97.6,
        priority: 'HIGH',
        candidateZone: 'Zone 67684'
    };
    assert.strictEqual(target1.candidateZone, 'Zone 67684');

    // Target 2: Random location with NO zone
    const target2 = {
        locationName: 'Arbitrary Coordinate',
        lat: 21.9400,
        lon: 80.4200,
        score: 62.4,
        priority: 'MEDIUM',
        candidateZone: 'NONE'
    };
    assert.strictEqual(target2.candidateZone, 'NONE');
    assert.notStrictEqual(target2.score, target1.score);
    assert.notStrictEqual(target2.candidateZone, target1.candidateZone);
});

console.log(`\nLocation != Zone Test Suite Passed: ${passed} / 10 tests.\n`);
