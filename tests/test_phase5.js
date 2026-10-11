/**
 * ============================================================================
 * AI MINERAL INTELLIGENCE — PHASE 5 COMPLETE INTEGRATION VALIDATION SUITE
 * ============================================================================
 * 
 * Verifies all Phase 5 Modules:
 *   - Module 5.1: Prospectivity Engine
 *   - Module 5.2: Candidate Zone Analysis
 *   - Module 5.3: Production Shortfall Random Forest
 *   - Module 5.4: Explainable AI
 * 
 * Test Scenarios:
 *   1. Known mine coordinates (Ghondi Manganese Mine: 21.9455°N, 80.4295°E)
 *   2. Candidate Zone 67684 (Top anomaly cluster)
 *   3. Analysis radius: 10 km (local cluster)
 *   4. Analysis radius: 25 km (regional block)
 *   5. Analysis radius: 50 km (broad belt)
 *   6. Analysis radius: 100 km (tile overview)
 *   7. Coordinates outside raster bounds
 *   8. WGS84 -> UTM Zone 44N coordinate conversion
 *   9. Prospectivity extraction from authoritative grid
 *  10. Candidate-zone distance calculation and filtering
 *  11. Production model loading and prediction
 *  12. Production shortfall calculation and risk classification
 *  13. XAI 10-feature importance weights (sum = 100%)
 *  14. Scientific disclaimer compliance
 * ============================================================================
 */

const assert = require('assert');
const path = require('path');
const fs = require('fs');

// Load Modules
const GeoEngine = require('../js/geo');
const MineralData = require('../js/data');
const ProspectivityEngine = require('../js/prospectivity');
const ZoneAnalysis = require('../js/zones');
const ProductionEngine = require('../js/production');
const ExplainableAI = require('../js/xai');

let passedTests = 0;
let totalTests = 0;

function runTest(name, fn) {
    totalTests++;
    try {
        fn();
        passedTests++;
        console.log(`[PASS] ${name}`);
    } catch (err) {
        console.error(`[FAIL] ${name}: ${err.message}`);
        console.error(err.stack);
    }
}

console.log('================================================================');
console.log('TEST SUITE: AI MINERAL INTELLIGENCE PHASE 5 VERIFICATION');
console.log('================================================================\n');

// Initialize grid and models
const gridPath = path.resolve(__dirname, '../data/processed/tile_prospectivity_549.json');
if (fs.existsSync(gridPath)) {
    const grid = JSON.parse(fs.readFileSync(gridPath, 'utf8'));
    ProspectivityEngine.setGrid(grid);
}

const prodModelPath = path.resolve(__dirname, '../data/processed/production_rf_trees.json');
if (fs.existsSync(prodModelPath)) {
    const model = JSON.parse(fs.readFileSync(prodModelPath, 'utf8'));
    ProductionEngine.setModel(model);
}

// ----------------------------------------------------------------------------
// 1. WGS84 -> UTM Zone 44N Coordinate Conversion
// ----------------------------------------------------------------------------
runTest('Coordinate Conversion: Ghondi Mine to UTM Zone 44N matches GDAL within 0.1m', () => {
    const utm = GeoEngine.wgs84ToUtm44N(21.9455, 80.4295);
    assert(Math.abs(utm.easting - 441089.328) < 0.1, `Easting mismatch: ${utm.easting}`);
    assert(Math.abs(utm.northing - 2426904.204) < 0.1, `Northing mismatch: ${utm.northing}`);
    assert.strictEqual(utm.zone, 44);
});

// ----------------------------------------------------------------------------
// 2. Known Mine Coordinates & Authoritative Prospectivity Extraction
// ----------------------------------------------------------------------------
runTest('Authoritative Prospectivity Extraction: Known Ghondi Mine yields 71.0%', () => {
    const result = ProspectivityEngine.analyzeLocationSync(21.9455, 80.4295, 25);
    assert.strictEqual(result.insideRaster, true, 'Mine should be inside raster');
    assert.strictEqual(result.prospectivityPercent, 71.0, `Score mismatch: expected 71.0%, got ${result.prospectivityPercent}%`);
    assert.strictEqual(result.classification, 'Moderate', `Classification mismatch: expected Moderate, got ${result.classification}`);
});

// ----------------------------------------------------------------------------
// 3. Candidate Zone 67684 Coordinates & Classification
// ----------------------------------------------------------------------------
runTest('Candidate Zone 67684: Correct coordinates, mean score (97.6%) and top classification', () => {
    const zone = ZoneAnalysis.getZoneById(67684);
    assert(zone !== null, 'Zone 67684 should exist');
    assert.strictEqual(zone.latitude, 22.21416);
    assert.strictEqual(zone.longitude, 80.063632);
    assert.strictEqual(zone.meanPercent, 97.6);
    assert.strictEqual(zone.classification, 'Top Priority Anomaly');
});

// ----------------------------------------------------------------------------
// 4. Analysis Radius Filtering: 10 km, 25 km, 50 km, 100 km
// ----------------------------------------------------------------------------
runTest('Radius 10 km: Local cluster analysis from Known Mine', () => {
    const res10 = ProspectivityEngine.analyzeLocationSync(21.9455, 80.4295, 10);
    assert.strictEqual(res10.radiusKm, 10);
    assert(res10.sampledPixels > 0, 'Should sample pixels within 10 km');
    assert(res10.nearbyZones.length >= 0, 'Nearby zones array should be present');
    // Zone distance check
    res10.nearbyZones.forEach(z => {
        assert(z.distanceKm <= 10.0, `Zone ${z.zoneId} exceeds 10 km: ${z.distanceKm}`);
    });
});

runTest('Radius 25 km: Regional block analysis from Known Mine', () => {
    const res25 = ProspectivityEngine.analyzeLocationSync(21.9455, 80.4295, 25);
    assert.strictEqual(res25.radiusKm, 25);
    assert(res25.sampledPixels > 2000, `Sample count should reflect 25km radius: ${res25.sampledPixels}`);
    assert(res25.meanPercent > 0, `Mean prospectivity should be > 0: ${res25.meanPercent}`);
    assert(res25.minPercent <= res25.meanPercent && res25.meanPercent <= res25.maxPercent);
    // At 25 km, there are 3 nearby zones (verified by Haversine: 124766, 103786, 115839)
    assert.strictEqual(res25.nearbyZones.length, 3, `Expected 3 candidate zones within 25km, got ${res25.nearbyZones.length}`);
});

runTest('Radius 50 km: Broad belt analysis from Known Mine', () => {
    const res50 = ProspectivityEngine.analyzeLocationSync(21.9455, 80.4295, 50);
    assert.strictEqual(res50.radiusKm, 50);
    assert(res50.sampledPixels > res50.sampledPixels / 2);
    assert(res50.nearbyZones.length >= 10, `Expected at least 10 zones within 50 km, got ${res50.nearbyZones.length}`);
    // Check sorted order
    for (let i = 1; i < res50.nearbyZones.length; i++) {
        assert(res50.nearbyZones[i].distanceKm >= res50.nearbyZones[i - 1].distanceKm, 'Zones should be sorted by distance ascending');
    }
});

runTest('Radius 100 km: Tile overview includes all candidate zones within tile footprint', () => {
    const res100 = ProspectivityEngine.analyzeLocationSync(21.9455, 80.4295, 100);
    assert.strictEqual(res100.radiusKm, 100);
    // All 20 candidate zones lie within 100km of Ghondi mine
    assert.strictEqual(res100.nearbyZones.length, 20, `Expected all 20 zones within 100 km, got ${res100.nearbyZones.length}`);
});

// ----------------------------------------------------------------------------
// 5. Coordinates Outside Raster Bounds
// ----------------------------------------------------------------------------
runTest('Location Outside Raster: Correctly flags out-of-bounds without fabricating scores', () => {
    const outResult = ProspectivityEngine.analyzeLocationSync(15.0, 75.0, 25);
    assert.strictEqual(outResult.insideRaster, false, 'Should be out of bounds');
    assert.strictEqual(outResult.prospectivityPercent, null, 'Prospectivity should be null for out of bounds');
    assert.strictEqual(outResult.classification, 'Out of Tile Bounds');
    assert.strictEqual(outResult.sampledPixels, 0);
});

// ----------------------------------------------------------------------------
// 6. Geodesic Distance Calculation
// ----------------------------------------------------------------------------
runTest('Distance Calculation: Haversine distance accuracy', () => {
    const distZero = GeoEngine.haversineDistanceKm(21.9455, 80.4295, 21.9455, 80.4295);
    assert.strictEqual(distZero, 0.0, 'Distance to self must be 0.0 km');

    const distZone67684 = GeoEngine.haversineDistanceKm(21.9455, 80.4295, 22.21416, 80.063632);
    assert(Math.abs(distZone67684 - 48.09) < 0.2, `Distance to Zone 67684 should be ~48.1 km, got ${distZone67684}`);
});

// ----------------------------------------------------------------------------
// 7. Production Model Loading & Prediction Fidelity
// ----------------------------------------------------------------------------
runTest('Production Prediction: Exact match to scikit-learn ground truth (8402.90 tonnes)', () => {
    const testInput = {
        rainfall: 150.0,
        equipmentDowntime: 20.0,
        blastingDelay: 8.0,
        equipmentAvailability: 85.0,
        plannedProduction: 11000.0
    };
    const pred = ProductionEngine.predictProduction(testInput);

    // Exact sklearn output is 8402.90 tonnes
    assert(Math.abs(pred.predictedProduction - 8402.90) < 0.05, `Mismatch in prediction: ${pred.predictedProduction} vs 8402.90`);
    assert(Math.abs(pred.shortfallTonnes - 2597.10) < 0.05, `Mismatch in shortfall: ${pred.shortfallTonnes} vs 2597.10`);
    assert.strictEqual(pred.shortfallPercentage, 23.6, `Shortfall percentage mismatch: ${pred.shortfallPercentage}% vs 23.6%`);
    assert.strictEqual(pred.riskLevel, 'HIGH', `Risk should be HIGH for 23.6% shortfall, got ${pred.riskLevel}`);
    assert(pred.recommendation.length > 20, 'Actionable recommendation should be provided');
});

runTest('Production Shortfall: Operational risk classification under favorable conditions', () => {
    const favorableInput = {
        rainfall: 20.0,
        equipmentDowntime: 2.0,
        blastingDelay: 0.0,
        equipmentAvailability: 98.0,
        plannedProduction: 10000.0
    };
    const pred = ProductionEngine.predictProduction(favorableInput);

    // The trained RF model predicts ~8830 tonnes for these inputs,
    // resulting in a shortfall of ~1169 tonnes (11.7%).
    // Per ProductionEngine risk classification:
    //   shortfall >= 1000 || shortfallPct >= 7.0 => MEDIUM
    assert(pred.predictedProduction > 8000.0, `Predicted should be substantial under favorable conditions: ${pred.predictedProduction}`);
    assert(pred.shortfallTonnes > 0, `Model predicts shortfall even under favorable conditions: ${pred.shortfallTonnes}`);
    assert(pred.shortfallPercentage >= 7.0 && pred.shortfallPercentage < 15.0,
        `Shortfall percentage should be in MEDIUM range (7-15%): ${pred.shortfallPercentage}%`);
    assert.strictEqual(pred.riskLevel, 'MEDIUM',
        `Risk should be MEDIUM for ${pred.shortfallPercentage}% shortfall, got ${pred.riskLevel}`);
    assert(pred.recommendation.length > 20, 'Actionable recommendation should be provided');
});

// ----------------------------------------------------------------------------
// 8. Explainable AI Feature Importance & Guardrails
// ----------------------------------------------------------------------------
runTest('XAI Features: Exactly 10 features with weights summing to 100%', () => {
    const features = ExplainableAI.getFeatureImportance();
    assert.strictEqual(features.length, 10, 'Should have exactly 10 features');

    const totalWeight = features.reduce((sum, f) => sum + f.importancePct, 0);
    assert(Math.abs(totalWeight - 100.0) < 0.1, `Feature weights sum should be 100%, got ${totalWeight}`);

    // Verify key features exist
    const featureIds = features.map(f => f.id);
    assert(featureIds.includes('B06'), 'B06 should be present');
    assert(featureIds.includes('NDVI'), 'NDVI should be present');
    assert(featureIds.includes('B8A'), 'B8A should be present');
    assert(featureIds.includes('B12'), 'B12 should be present');
    assert(featureIds.includes('B11'), 'B11 should be present');
    assert(featureIds.includes('RED_SWIR_RATIO'), 'RED_SWIR_RATIO should be present');
    assert(featureIds.includes('B04'), 'B04 should be present');
    assert(featureIds.includes('NDMI'), 'NDMI should be present');
    assert(featureIds.includes('SWIR_RATIO'), 'SWIR_RATIO should be present');
    assert(featureIds.includes('B05'), 'B05 should be present');
});

runTest('XAI Guardrails: Scientific disclaimer must distinguish indication from confirmed deposit', () => {
    const explanation = ExplainableAI.explainProspectivityScore(71.0, 'Ghondi Manganese Mine');
    assert(explanation.disclaimer !== undefined, 'Disclaimer must be present');
    assert(explanation.disclaimer.summary.includes('NOT confirm the presence'), 'Must disclaim confirmation of mineral deposit');
    assert(explanation.disclaimer.keyDistinctions.length >= 2, 'Must include key terminology distinctions');
    assert.strictEqual(explanation.score, 71.0);
    assert(explanation.waterfallSteps.length === 12, '1 baseline + 10 features + 1 final = 12 steps');
});

// ----------------------------------------------------------------------------
// Final Results
// ----------------------------------------------------------------------------
console.log('\n================================================================');
console.log(`PHASE 5 TEST RESULTS: ${passedTests} / ${totalTests} tests passed (${Math.round(passedTests / totalTests * 100)}%)`);
console.log('================================================================\n');

if (passedTests !== totalTests) {
    process.exit(1);
}
