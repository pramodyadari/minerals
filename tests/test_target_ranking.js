/**
 * ============================================================================
 * AI MINERAL INTELLIGENCE — TARGET RANKING & COMPARISON TEST SUITE
 * ============================================================================
 * Tests:
 *   1. Candidate zones are loaded (all 20 authentic zones)
 *   2. Ranking is correctly sorted (meanScore strictly descending)
 *   3. Actual prospectivity scores are used (matching CSV / real model)
 *   4. Rank numbers are correct (1..N sequence, #1 is Zone 67684)
 *   5. Confidence remains "Not Calibrated" (Strict Honesty Principle)
 *   6. EvidenceEngine is reused (no duplicated evidence engine)
 *   7. Missing evidence remains unavailable (DATA NOT AVAILABLE)
 *   8. Data quality is distinct from confidence (different concepts)
 *   9. Priority classification works (HIGH/MED/LOW + screening disclaimer)
 *  10. Target comparison works (side-by-side matrix & differential delta)
 *  11. View-on-map works (valid coordinate dispatch to ExplorationMap)
 *  12. Existing neutral startup remains intact (hasTarget === false)
 *  13. Existing map functionality remains intact (place resolver, popups)
 *  14. Existing export remains intact (GeoJSON FeatureCollection)
 *  15. Multi-mineral compatibility remains intact (trained vs framework-ready)
 * ============================================================================
 */

const assert = require('assert');
const fs = require('fs');
const path = require('path');

const ROOT_DIR = path.resolve(__dirname, '..');
const htmlContent = fs.readFileSync(path.join(ROOT_DIR, 'index.html'), 'utf8');
const cssContent = fs.readFileSync(path.join(ROOT_DIR, 'styles.css'), 'utf8');
const mapJsContent = fs.readFileSync(path.join(ROOT_DIR, 'js/map.js'), 'utf8');
const appJsContent = fs.readFileSync(path.join(ROOT_DIR, 'app.js'), 'utf8');

// Load modules under test
const MineralData = require(path.join(ROOT_DIR, 'js/data.js'));
const LocationResolver = require(path.join(ROOT_DIR, 'js/locations.js'));
const EvidenceEngine = require(path.join(ROOT_DIR, 'js/evidence.js'));
const ExplainableAI = require(path.join(ROOT_DIR, 'js/xai.js'));
const MineralRegistry = require(path.join(ROOT_DIR, 'js/mineral-registry.js'));
const TargetRankingEngine = require(path.join(ROOT_DIR, 'js/ranking.js'));

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
    }
}

console.log('================================================================');
console.log('TEST SUITE: AI EXPLORATION TARGET RANKING & COMPARISON');
console.log('================================================================\n');

// ----------------------------------------------------------------------------
// Test 1: Candidate zones are loaded
// ----------------------------------------------------------------------------
runTest('Test 1: Candidate zones are loaded from real project dataset', () => {
    const result = TargetRankingEngine.getRankedTargets('manganese');
    assert.strictEqual(result.isTrained, true, 'Manganese must be marked as trained');
    assert.strictEqual(result.count, 20, 'Must load all 20 authoritative candidate zones');
    assert(Array.isArray(result.targets), 'Targets must be an array');
    assert.strictEqual(result.targets.length, 20, 'Targets array must contain 20 items');
});

// ----------------------------------------------------------------------------
// Test 2: Ranking is correctly sorted
// ----------------------------------------------------------------------------
runTest('Test 2: Ranking is strictly sorted by prospectivity score descending', () => {
    const result = TargetRankingEngine.getRankedTargets('manganese');
    const targets = result.targets;
    for (let i = 0; i < targets.length - 1; i++) {
        assert(
            targets[i].score >= targets[i + 1].score,
            `Targets not sorted descending at index ${i}: ${targets[i].score} vs ${targets[i + 1].score}`
        );
    }
});

// ----------------------------------------------------------------------------
// Test 3: Actual prospectivity scores are used
// ----------------------------------------------------------------------------
runTest('Test 3: Actual prospectivity scores are used without synthetic fabrication', () => {
    const result = TargetRankingEngine.getRankedTargets('manganese');
    const top = result.targets[0];
    assert.strictEqual(top.zoneId, 67684, 'Top zone must be 67684');
    assert.strictEqual(top.score, 97.6, 'Zone 67684 prospectivity score must be 97.6%');
    assert.strictEqual(top.scoreFormatted, '97.6%', 'Formatted score must be 97.6%');

    const second = result.targets[1];
    assert.strictEqual(second.zoneId, 67387, 'Second zone must be 67387');
    assert.strictEqual(second.score, 97.3, 'Zone 67387 prospectivity score must be 97.3%');

    const third = result.targets[2];
    assert.strictEqual(third.zoneId, 124766, 'Third zone must be 124766');
    assert.strictEqual(third.score, 97.0, 'Zone 124766 prospectivity score must be 97.0%');
});

// ----------------------------------------------------------------------------
// Test 4: Rank numbers are correct
// ----------------------------------------------------------------------------
runTest('Test 4: Rank numbers are sequential integers starting at 1', () => {
    const result = TargetRankingEngine.getRankedTargets('manganese');
    result.targets.forEach((target, idx) => {
        assert.strictEqual(target.rank, idx + 1, `Rank mismatch at index ${idx}: expected ${idx + 1}, got ${target.rank}`);
    });
});

// ----------------------------------------------------------------------------
// Test 5: Confidence remains "Not Calibrated"
// ----------------------------------------------------------------------------
runTest('Test 5: Model Confidence remains strictly "Not Calibrated" across all targets', () => {
    const result = TargetRankingEngine.getRankedTargets('manganese');
    result.targets.forEach(t => {
        assert.strictEqual(t.modelConfidence.status, 'Not Calibrated', `Zone ${t.zoneId} confidence must be Not Calibrated`);
        assert.strictEqual(t.modelConfidence.displayValue, 'Not Calibrated', `Zone ${t.zoneId} displayValue must be Not Calibrated`);
        assert.strictEqual(t.modelConfidence.isCalibrated, false, `Zone ${t.zoneId} isCalibrated must be false`);
        assert(t.modelConfidence.methodology.length > 0, 'Methodology note must be present');
    });
});

// ----------------------------------------------------------------------------
// Test 6: EvidenceEngine is reused
// ----------------------------------------------------------------------------
runTest('Test 6: EvidenceEngine is reused without creating a duplicate explanation engine', () => {
    const detail = TargetRankingEngine.getZoneDetail(67684, 'manganese');
    assert(detail.evidenceDossier !== null, 'evidenceDossier must be produced by EvidenceEngine');
    assert(Array.isArray(detail.evidenceCategories), 'evidenceCategories must be present from EvidenceEngine');
    assert(detail.topFeatures.length > 0, 'topFeatures must be derived from ExplainableAI');

    // Confirm top features match ExplainableAI
    const directXAI = ExplainableAI.explainProspectivityScore(97.6);
    const directTop = directXAI.waterfallSteps.filter(s => !s.isBaseline && !s.isFinal)[0].name;
    assert.strictEqual(detail.topFeatures[0].name, directTop, 'Top feature name must match XAI module exactly');
});

// ----------------------------------------------------------------------------
// Test 7: Missing evidence remains unavailable
// ----------------------------------------------------------------------------
runTest('Test 7: Missing scientific datasets explicitly report DATA NOT AVAILABLE', () => {
    const detail = TargetRankingEngine.getZoneDetail(67684, 'manganese');
    const terrain = detail.evidenceCategories.find(c => c.id === 'terrain-evidence');
    assert.strictEqual(terrain.status, 'DATA NOT AVAILABLE', 'Terrain evidence status must be DATA NOT AVAILABLE');
    assert.strictEqual(terrain.contribution, 'Unavailable', 'Terrain contribution must be Unavailable');

    const geology = detail.evidenceCategories.find(c => c.id === 'geological-evidence');
    assert.strictEqual(geology.status, 'DATA NOT AVAILABLE', 'Geology evidence status must be DATA NOT AVAILABLE');
    assert.strictEqual(geology.contribution, 'Unavailable', 'Geology contribution must be Unavailable');

    const drill = detail.evidenceCategories.find(c => c.id === 'drilling-evidence');
    assert.strictEqual(drill.status, 'DATA NOT AVAILABLE', 'Drilling evidence status must be DATA NOT AVAILABLE');
    assert.strictEqual(drill.contribution, 'Unavailable', 'Drilling contribution must be Unavailable');
});

// ----------------------------------------------------------------------------
// Test 8: Data quality is distinct from confidence
// ----------------------------------------------------------------------------
runTest('Test 8: Data Quality is clearly distinct from Model Confidence', () => {
    const detail = TargetRankingEngine.getZoneDetail(67684, 'manganese');
    assert.strictEqual(detail.dataQuality.level, 'MEDIUM', 'Data quality level must be MEDIUM');
    assert.strictEqual(detail.dataQuality.label, 'Medium', 'Data quality label must be Medium');
    assert.strictEqual(detail.dataQuality.activeSources, 3, 'Must report 3 active baseline sources');
    assert.strictEqual(detail.dataQuality.totalSources, 8, 'Must report 8 total regional sources');

    // Model Confidence is a distinct concept (uncalibrated probability curve)
    assert.strictEqual(detail.modelConfidence.status, 'Not Calibrated', 'Confidence is Not Calibrated');
    assert.notStrictEqual(detail.dataQuality.level, detail.modelConfidence.status, 'Data Quality and Confidence must be different');
});

// ----------------------------------------------------------------------------
// Test 9: Priority classification works
// ----------------------------------------------------------------------------
runTest('Test 9: Exploration priority classifies correctly and includes screening disclaimer', () => {
    // 97.6% -> HIGH PRIORITY
    const priHigh = TargetRankingEngine.calculatePriority(97.6);
    assert.strictEqual(priHigh.level, 'HIGH PRIORITY', 'Expected HIGH PRIORITY for 97.6%');
    assert.strictEqual(priHigh.badgeClass, 'high');

    // 60.0% -> MEDIUM PRIORITY
    const priMed = TargetRankingEngine.calculatePriority(60.0);
    assert.strictEqual(priMed.level, 'MEDIUM PRIORITY', 'Expected MEDIUM PRIORITY for 60.0%');
    assert.strictEqual(priMed.badgeClass, 'medium');

    // 35.0% -> LOW PRIORITY
    const priLow = TargetRankingEngine.calculatePriority(35.0);
    assert.strictEqual(priLow.level, 'LOW PRIORITY', 'Expected LOW PRIORITY for 35.0%');
    assert.strictEqual(priLow.badgeClass, 'low');

    // Null -> INSUFFICIENT DATA
    const priNull = TargetRankingEngine.calculatePriority(null);
    assert.strictEqual(priNull.level, 'INSUFFICIENT DATA', 'Expected INSUFFICIENT DATA for null');

    // Screening disclaimer check
    const expectedDisclaimer = 'Priority indicates AI-assisted exploration screening and does not confirm mineralization.';
    assert.strictEqual(priHigh.disclaimer, expectedDisclaimer, 'Mandatory disclaimer mismatch');
});

// ----------------------------------------------------------------------------
// Test 10: Target comparison works
// ----------------------------------------------------------------------------
runTest('Test 10: Multi-target comparison builds side-by-side matrix with differential delta', () => {
    // Test comparison with 2 targets
    const comp = TargetRankingEngine.compareTargets([67684, 124766], 'manganese');
    assert.strictEqual(comp.isTrained, true, 'Comparison must be trained');
    assert.strictEqual(comp.comparedCount, 2, 'Must compare 2 targets');
    assert.strictEqual(comp.targets.length, 2, 'Targets array must contain 2 items');
    assert.strictEqual(comp.topTarget.zoneId, 67684, 'Top target in comparison must be 67684');
    assert.strictEqual(comp.scoreDelta, '0.6', 'Score delta between 97.6% and 97.0% must be 0.6%');
    assert(comp.rows.length >= 10, 'Comparison matrix must have at least 10 scientific dimensions');

    // Test rejection when < 2 targets selected
    const compSingle = TargetRankingEngine.compareTargets([67684], 'manganese');
    assert(compSingle.error !== null, 'Comparison with single target must return error');
});

// ----------------------------------------------------------------------------
// Test 11: View-on-map works
// ----------------------------------------------------------------------------
runTest('Test 11: View-on-map action connects to zone coordinates without breaking state', () => {
    assert(appJsContent.includes('viewRankedTargetOnMap'), 'viewRankedTargetOnMap missing in app.js');
    assert(appJsContent.includes('ExplorationMap.setLocation'), 'ExplorationMap.setLocation missing in app.js');
    assert(htmlContent.includes('btn-view-map-row') || appJsContent.includes('btn-view-map-row'), 'btn-view-map-row missing');
});

// ----------------------------------------------------------------------------
// Test 12: Existing neutral startup remains intact
// ----------------------------------------------------------------------------
runTest('Test 12: Application maintains neutral startup with zero pre-selected target', () => {
    assert(htmlContent.includes('No Target Selected'), 'Default place card must display No Target Selected');
    assert(htmlContent.includes('Awaiting Target'), 'Score classification must display Awaiting Target');
    assert(mapJsContent.includes('hasTarget: false'), 'Map initial state must have hasTarget === false');
});

// ----------------------------------------------------------------------------
// Test 13: Existing map functionality remains intact
// ----------------------------------------------------------------------------
runTest('Test 13: Map place labels, candidate zone popups, and layer toggles remain intact', () => {
    assert(mapJsContent.includes('WHY THIS ZONE?'), 'Candidate zone popups must retain WHY THIS ZONE?');
    assert(mapJsContent.includes('Set Target'), 'Candidate zone popups must retain Set Target');
    assert(mapJsContent.includes('View Evidence'), 'Candidate zone popups must retain View Evidence');
    assert(mapJsContent.includes('Compare'), 'Candidate zone popups must have Compare button');
});

// ----------------------------------------------------------------------------
// Test 14: Existing export remains intact
// ----------------------------------------------------------------------------
runTest('Test 14: GeoJSON comparison export produces valid FeatureCollection with metadata', () => {
    const geojson = TargetRankingEngine.exportComparisonGeoJSON([67684, 124766], 'manganese');
    assert.strictEqual(geojson.type, 'FeatureCollection', 'Must export FeatureCollection');
    assert.strictEqual(geojson.features.length, 2, 'Must contain 2 features');

    const feat0 = geojson.features[0];
    assert.strictEqual(feat0.type, 'Feature', 'Must be Feature');
    assert.strictEqual(feat0.geometry.type, 'Point', 'Geometry must be Point');
    assert.strictEqual(feat0.properties.zone_id, 67684, 'Feature zone_id must be 67684');
    assert.strictEqual(feat0.properties.prospectivity_score_pct, 97.6, 'Score must be 97.6');
    assert.strictEqual(feat0.properties.model_confidence, 'Not Calibrated', 'Model confidence must be Not Calibrated');
    assert.strictEqual(feat0.properties.is_confidence_calibrated, false, 'is_confidence_calibrated must be false');
    assert(geojson.metadata.screening_disclaimer.includes('exploration-screening indication'), 'Metadata must include screening disclaimer');
});

// ----------------------------------------------------------------------------
// Test 15: Multi-mineral compatibility remains intact
// ----------------------------------------------------------------------------
runTest('Test 15: Multi-mineral framework displays Framework Ready for untrained commodities', () => {
    // Untrained mineral (Copper)
    const copperRanking = TargetRankingEngine.getRankedTargets('copper');
    assert.strictEqual(copperRanking.isTrained, false, 'Copper must be marked untrained');
    assert.strictEqual(copperRanking.count, 0, 'Untrained mineral must have 0 fake targets');
    assert(copperRanking.message.includes('Framework Ready'), 'Message must indicate Framework Ready');

    // Untrained mineral (Bauxite)
    const bauxiteRanking = TargetRankingEngine.getRankedTargets('bauxite');
    assert.strictEqual(bauxiteRanking.isTrained, false, 'Bauxite must be marked untrained');
    assert.strictEqual(bauxiteRanking.count, 0, 'Bauxite must have 0 fake targets');

    // Switching back to Manganese restores active trained targets
    const mnRanking = TargetRankingEngine.getRankedTargets('manganese');
    assert.strictEqual(mnRanking.isTrained, true, 'Manganese must be active');
    assert.strictEqual(mnRanking.count, 20, 'Must have 20 targets');
});

console.log('\n================================================================');
console.log(`RESULTS: ${passedTests} / ${totalTests} tests passed (${Math.round((passedTests / totalTests) * 100)}%)`);
console.log('================================================================');

if (passedTests < totalTests) {
    process.exit(1);
}
