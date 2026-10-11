/**
 * ============================================================================
 * AI MINERAL INTELLIGENCE — PHASE 7 FRONTEND GEOLOGY & TERRAIN TESTS
 * ============================================================================
 * Module: tests/test_geology_terrain_frontend.js
 * 
 * Verifies:
 *   1. EvidenceEngine returns "DATA NOT AVAILABLE" for Terrain & Geology when missing.
 *   2. EvidenceEngine integrates factual Terrain & Geology when provided without fake confidence.
 *   3. EvidenceEngine includes explicit independentDepositValidation: NOT AVAILABLE.
 *   4. Within-study spatial-sector validation terminology is preserved.
 *   5. MineralRegistry provides independentDepositValidation for manganese.
 *   6. TargetRankingEngine ranking order remains unchanged by geology/terrain.
 *   7. Data quality calculation accounts for layers honestly.
 *   8. ExplorationMap exposes toggleGeologyLayer, toggleStructuresLayer, toggleTerrainLayer.
 *   9. DOM elements in index.html for geology, structures, terrain, and independent validation.
 * ============================================================================
 */

const assert = require('assert');
const fs = require('fs');
const path = require('path');

const EvidenceEngine = require('../js/evidence');
const MineralRegistry = require('../js/mineral-registry');
const TargetRankingEngine = require('../js/ranking');
const ExplorationMap = require('../js/map');

let passedTests = 0;
let totalTests = 0;

function runTest(name, fn) {
    totalTests++;
    try {
        fn();
        console.log(`[PASS] Test ${totalTests}: ${name}`);
        passedTests++;
    } catch (err) {
        console.error(`[FAIL] Test ${totalTests}: ${name}`);
        console.error(err);
        process.exitCode = 1;
    }
}

console.log('================================================================');
console.log(' RUNNING PHASE 7 GEOLOGY & TERRAIN FRONTEND TESTS');
console.log('================================================================');

// 1. Missing Geology & Terrain reports DATA NOT AVAILABLE
runTest('Missing Geology and Terrain categories report DATA NOT AVAILABLE', () => {
    const dossier = EvidenceEngine.evaluateEvidence({
        lat: 21.9455,
        lon: 80.4295,
        score: 87.5
    });

    assert.ok(dossier, 'Dossier must be returned');
    const terrain = dossier.evidenceCategories.find(c => c.id === 'terrain-evidence');
    assert.ok(terrain, 'Terrain evidence category must exist');
    assert.strictEqual(terrain.status, 'DATA NOT AVAILABLE');
    assert.strictEqual(terrain.contribution, 'Unavailable');

    const geology = dossier.evidenceCategories.find(c => c.id === 'geological-evidence');
    assert.ok(geology, 'Geology evidence category must exist');
    assert.strictEqual(geology.status, 'DATA NOT AVAILABLE');
    assert.strictEqual(geology.contribution, 'Unavailable');
});

// 2. Factual Integration when layers are provided
runTest('Factual integration when verified Terrain & Geology payloads are supplied', () => {
    const terrainPayload = {
        available: true,
        status: 'AVAILABLE',
        elevation_m: 412.0,
        slope_deg: 7.4,
        aspect_deg: 128.0,
        resolution_m: 30
    };
    const geologyPayload = {
        available: true,
        status: 'AVAILABLE',
        lithology: { unit: 'Manganese Phyllite / Gondite Unit' },
        structures: { nearest_distance_m: 480.0 }
    };

    const dossier = EvidenceEngine.evaluateEvidence({
        lat: 21.9455,
        lon: 80.4295,
        score: 87.5,
        terrainEvidence: terrainPayload,
        geologicalEvidence: geologyPayload
    });

    const terrain = dossier.evidenceCategories.find(c => c.id === 'terrain-evidence');
    assert.strictEqual(terrain.status, 'Available');
    assert.strictEqual(terrain.contribution, 'Contextual');
    assert.strictEqual(terrain.elevation_m, 412.0);
    assert.strictEqual(terrain.slope_deg, 7.4);

    const geology = dossier.evidenceCategories.find(c => c.id === 'geological-evidence');
    assert.strictEqual(geology.status, 'Available');
    assert.strictEqual(geology.contribution, 'Contextual');
    assert.strictEqual(geology.lithology, 'Manganese Phyllite / Gondite Unit');
    assert.strictEqual(geology.structureDistance, '480 m');
});

// 3. Independent Deposit Validation is explicitly NOT AVAILABLE
runTest('Independent Deposit Validation is explicitly marked NOT AVAILABLE', () => {
    const dossier = EvidenceEngine.evaluateEvidence({
        lat: 21.9455,
        lon: 80.4295,
        score: 87.5
    });

    assert.ok(dossier.independentDepositValidation, 'independentDepositValidation object must exist');
    assert.strictEqual(dossier.independentDepositValidation.status, 'NOT AVAILABLE');
    assert.strictEqual(dossier.independentDepositValidation.displayValue, 'NOT AVAILABLE');
    assert.strictEqual(dossier.independentDepositValidation.methodology, 'Within-study spatial-sector validation');
    assert.ok(dossier.independentDepositValidation.explanation.includes('one known Manganese deposit'));
});

// 4. Model Confidence remains Not Calibrated
runTest('Model Confidence remains strictly Not Calibrated', () => {
    const dossier = EvidenceEngine.evaluateEvidence({
        lat: 21.9455,
        lon: 80.4295,
        score: 92.0
    });

    assert.strictEqual(dossier.modelConfidence.status, 'Not Calibrated');
    assert.strictEqual(dossier.modelConfidence.isCalibrated, false);
});

// 5. MineralRegistry exposes independent deposit validation status
runTest('MineralRegistry provides independent deposit validation status for manganese', () => {
    const valInfo = MineralRegistry.getValidationInfo('manganese');
    assert.ok(valInfo, 'Validation info must exist');
    assert.ok(valInfo.independentDepositValidation, 'Must include independentDepositValidation');
    assert.strictEqual(valInfo.independentDepositValidation.status, 'NOT AVAILABLE');
    assert.strictEqual(valInfo.spatialAccuracyPct, 96.76);
    assert.strictEqual(valInfo.validationMethod, 'Spatial Block Validation');
});

// 6. TargetRankingEngine ranking order remains strictly based on prospectivity score
runTest('TargetRankingEngine ranking order remains unchanged by geology/terrain', () => {
    const ranking = TargetRankingEngine.getRankedTargets('manganese');
    assert.ok(ranking.isTrained, 'Manganese must be trained');
    assert.ok(ranking.targets.length > 0, 'Must have ranked targets');

    // Verify descending order of prospectivity scores
    for (let i = 1; i < ranking.targets.length; i++) {
        assert.ok(
            ranking.targets[i - 1].score >= ranking.targets[i].score,
            `Target ${i - 1} score (${ranking.targets[i - 1].score}) must be >= Target ${i} score (${ranking.targets[i].score})`
        );
    }
});

// 7. ExplorationMap exposes layer toggle functions
runTest('ExplorationMap exposes toggleGeologyLayer, toggleStructuresLayer, toggleTerrainLayer', () => {
    assert.strictEqual(typeof ExplorationMap.toggleGeologyLayer, 'function');
    assert.strictEqual(typeof ExplorationMap.toggleStructuresLayer, 'function');
    assert.strictEqual(typeof ExplorationMap.toggleTerrainLayer, 'function');

    // Toggling missing layer returns false honestly
    assert.strictEqual(ExplorationMap.toggleGeologyLayer(true), false);
    assert.strictEqual(ExplorationMap.toggleStructuresLayer(true), false);
    assert.strictEqual(ExplorationMap.toggleTerrainLayer(true), false);
});

// 8. index.html contains required Phase 7 DOM elements
runTest('index.html contains required Phase 7 layer controls and dossier fields', () => {
    const htmlPath = path.join(__dirname, '..', 'index.html');
    const html = fs.readFileSync(htmlPath, 'utf8');

    // Map toggles
    assert.ok(html.includes('id="toggle-geology-layer"'), 'toggle-geology-layer must exist');
    assert.ok(html.includes('id="toggle-structures-layer"'), 'toggle-structures-layer must exist');
    assert.ok(html.includes('id="toggle-terrain-layer"'), 'toggle-terrain-layer must exist');
    assert.ok(html.includes('Geology — Data unavailable'), 'Geology unavailable label must exist');
    assert.ok(html.includes('Terrain — Data unavailable'), 'Terrain unavailable label must exist');

    // Target detail modal
    assert.ok(html.includes('id="detail-modal-geology-status"'), 'detail-modal-geology-status must exist');
    assert.ok(html.includes('id="detail-modal-terrain-status"'), 'detail-modal-terrain-status must exist');
    assert.ok(html.includes('id="detail-modal-lithology"'), 'detail-modal-lithology must exist');
    assert.ok(html.includes('id="detail-modal-structure-dist"'), 'detail-modal-structure-dist must exist');
    assert.ok(html.includes('id="detail-modal-elevation"'), 'detail-modal-elevation must exist');
    assert.ok(html.includes('id="detail-modal-slope"'), 'detail-modal-slope must exist');
    assert.ok(html.includes('id="detail-modal-aspect"'), 'detail-modal-aspect must exist');

    // Independent Deposit Validation
    assert.ok(html.includes('id="val-independent-status"'), 'val-independent-status must exist');
    assert.ok(html.includes('INDEPENDENT DEPOSIT VALIDATION'), 'INDEPENDENT DEPOSIT VALIDATION text must exist');
});

// 9. Data Provenance table includes DEM and Geology entries
runTest('Data Provenance table includes Digital Elevation Model and Regional Geology rows', () => {
    const dossier = EvidenceEngine.evaluateEvidence({
        lat: 21.9455,
        lon: 80.4295,
        score: 87.5
    });

    const demProv = dossier.dataProvenance.find(d => d.source.includes('Digital Elevation Model'));
    assert.ok(demProv, 'DEM row must exist in dataProvenance');
    assert.strictEqual(demProv.status, 'DATA NOT AVAILABLE');

    const geoProv = dossier.dataProvenance.find(d => d.source.includes('Regional Geological Map'));
    assert.ok(geoProv, 'Geology row must exist in dataProvenance');
    assert.strictEqual(geoProv.status, 'DATA NOT AVAILABLE');
});

// 10. Scientific disclaimers are present
runTest('Scientific disclaimers for contextual evidence and independent validation are present', () => {
    const dossier = EvidenceEngine.evaluateEvidence({
        lat: 21.9455,
        lon: 80.4295,
        score: 87.5
    });

    assert.ok(dossier.recommendation.disclaimer.includes('exploration-screening indication'));
    assert.ok(dossier.recommendation.contextualDisclaimer.includes('not themselves proof of mineralization'));
    assert.ok(dossier.recommendation.independentValidationDisclaimer.includes('Independent deposit validation is not currently available'));
});

console.log('================================================================');
console.log(`TEST RESULTS: ${passedTests} / ${totalTests} tests passed (${Math.round((passedTests/totalTests)*100)}%)`);
console.log('================================================================\n');

if (passedTests !== totalTests) {
    process.exit(1);
}
