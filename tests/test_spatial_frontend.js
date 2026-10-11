/**
 * ============================================================================
 * AI MINERAL INTELLIGENCE — PHASE 6: FRONTEND MODEL VALIDATION TESTS
 * ============================================================================
 * Test Suite: tests/test_spatial_frontend.js
 * 
 * Verifies:
 *   1. MineralRegistry.getValidationInfo returns spatial metrics for Manganese
 *   2. MineralRegistry.getValidationInfo returns NOT_VALIDATED for untrained minerals
 *   3. EvidenceEngine includes "Model Validation" category
 *   4. Model Validation category in EvidenceEngine is marked NOT CALIBRATED
 *   5. index.html contains the compact MODEL VALIDATION panel
 *   6. Required metrics are present in index.html (Accuracy, F1, ROC-AUC, PR-AUC)
 *   7. WHY NOT CALIBRATED? rationale is clearly displayed in index.html
 *   8. Prospectivity score and validation accuracy remain strictly distinguished
 * ============================================================================
 */

const assert = require('assert');
const fs = require('fs');
const path = require('path');

const MineralRegistry = require('../js/mineral-registry');
const EvidenceEngine = require('../js/evidence');

let passedTests = 0;
let totalTests = 0;

function runTest(name, fn) {
    totalTests++;
    try {
        fn();
        passedTests++;
        console.log(`[PASS] ${name}`);
    } catch (e) {
        console.error(`[FAIL] ${name}: ${e.message}`);
    }
}

console.log('================================================================');
console.log('TEST SUITE: PHASE 6 FRONTEND MODEL VALIDATION & TRUST');
console.log('================================================================\n');

// 1. MineralRegistry validation info for Manganese
runTest('Test 1: MineralRegistry.getValidationInfo returns spatial validation for Manganese', () => {
    const info = MineralRegistry.getValidationInfo('manganese');
    assert.strictEqual(info.mineralId, 'manganese');
    assert.strictEqual(info.modelStatus, 'TRAINED');
    assert.strictEqual(info.validationStatus, 'SPATIALLY_VALIDATED');
    assert.strictEqual(info.calibrationStatus, 'NOT_CALIBRATED');
    assert.strictEqual(info.isSpatiallyValidated, true);
    assert.strictEqual(info.isCalibrated, false);
    assert.strictEqual(info.spatialAccuracyPct, 96.76);
    assert.strictEqual(info.spatialF1, 0.9671);
    assert.strictEqual(info.spatialRocAuc, 0.9931);
    assert.strictEqual(info.spatialPrAuc, 0.9923);
    assert.strictEqual(info.validationMethod, 'Spatial Block Validation');
});

// 2. Untrained minerals have NOT_VALIDATED status
runTest('Test 2: MineralRegistry.getValidationInfo returns NOT_VALIDATED for untrained minerals', () => {
    ['copper', 'iron_ore', 'bauxite', 'lithium', 'coal', 'limestone'].forEach(min => {
        const info = MineralRegistry.getValidationInfo(min);
        assert.strictEqual(info.validationStatus, 'NOT_VALIDATED');
        assert.strictEqual(info.calibrationStatus, 'NOT_CALIBRATED');
        assert.strictEqual(info.isSpatiallyValidated, false);
        assert.strictEqual(info.spatialAccuracyPct, null);
    });
});

// 3. EvidenceEngine includes Model Validation category
runTest('Test 3: EvidenceEngine includes Model Validation category in evidence categories', () => {
    const dossier = EvidenceEngine.evaluateEvidence({
        lat: 21.9455,
        lon: 80.4295,
        score: 71.0,
        mineral: 'manganese'
    });
    assert.ok(dossier.evidenceCategories, 'Must contain evidence categories');
    const valCat = dossier.evidenceCategories.find(c => c.id === 'validation-evidence');
    assert.ok(valCat, 'Must contain validation-evidence category');
    assert.strictEqual(valCat.name, 'Model Validation');
    assert.strictEqual(valCat.status, 'Available');
    assert.strictEqual(valCat.contribution, 'Verified');
    assert(valCat.explanation.includes('Spatial validation: Available'));
    assert(valCat.explanation.includes('Not calibrated'));
});

// 4. EvidenceEngine marks Model Validation unavailable for untrained mineral
runTest('Test 4: EvidenceEngine marks Model Validation as DATA NOT AVAILABLE for untrained mineral', () => {
    const dossier = EvidenceEngine.evaluateEvidence({
        lat: 21.9455,
        lon: 80.4295,
        score: 0,
        mineral: 'copper'
    });
    const valCat = dossier.evidenceCategories.find(c => c.id === 'validation-evidence');
    assert.ok(valCat);
    assert.strictEqual(valCat.status, 'DATA NOT AVAILABLE');
    assert.strictEqual(valCat.contribution, 'Unavailable');
});

// 5. index.html contains MODEL VALIDATION section
runTest('Test 5: index.html contains compact MODEL VALIDATION section', () => {
    const html = fs.readFileSync(path.join(__dirname, '../index.html'), 'utf-8');
    assert(html.includes('id="model-validation-card"'), 'Must contain model-validation-card');
    assert(html.includes('MODEL VALIDATION'), 'Must contain MODEL VALIDATION heading');
    assert(html.includes('id="val-methodology"'), 'Must contain val-methodology');
    assert(html.includes('id="val-spatial-accuracy"'), 'Must contain val-spatial-accuracy');
    assert(html.includes('id="val-spatial-f1"'), 'Must contain val-spatial-f1');
    assert(html.includes('id="val-spatial-roc"'), 'Must contain val-spatial-roc');
    assert(html.includes('id="val-spatial-pr"'), 'Must contain val-spatial-pr');
    assert(html.includes('id="val-calibration-status"'), 'Must contain val-calibration-status');
    assert(html.includes('WHY NOT CALIBRATED?'), 'Must contain WHY NOT CALIBRATED? explanation');
});

// 6. index.html displays genuine metrics
runTest('Test 6: index.html contains calculated metrics and uncalibrated explanation', () => {
    const html = fs.readFileSync(path.join(__dirname, '../index.html'), 'utf-8');
    assert(html.includes('96.76%'), 'Must include 96.76% spatial accuracy');
    assert(html.includes('0.9671'), 'Must include 0.9671 F1-score');
    assert(html.includes('0.9931'), 'Must include 0.9931 ROC-AUC');
    assert(html.includes('0.9923'), 'Must include 0.9923 PR-AUC');
    assert(html.includes('NOT CALIBRATED'), 'Must include NOT CALIBRATED');
    assert(html.includes('A calibrated probability of mineral occurrence has not been established'), 'Must explain why not calibrated');
});

// 7. app.js contains updateValidationUI
runTest('Test 7: app.js contains updateValidationUI handler', () => {
    const appJs = fs.readFileSync(path.join(__dirname, '../app.js'), 'utf-8');
    assert(appJs.includes('function updateValidationUI'), 'app.js must define updateValidationUI');
    assert(appJs.includes('updateValidationUI('), 'renderEvidencePanel must invoke updateValidationUI');
});

// 8. Prospectivity score vs Validation accuracy distinction
runTest('Test 8: Strict distinction maintained between prospectivity score, validation accuracy, and calibration', () => {
    const html = fs.readFileSync(path.join(__dirname, '../index.html'), 'utf-8');
    // Prospectivity score element
    assert(html.includes('id="score-number"'), 'score-number exists for prospectivity');
    assert(html.includes('AI Prospectivity & Model Confidence'), 'score heading exists');
    // Model confidence element
    assert(html.includes('id="model-confidence-status"'), 'model-confidence-status exists');
    assert(html.includes('Not Calibrated'), 'Not Calibrated label preserved');
    // Model validation element
    assert(html.includes('id="val-spatial-accuracy"'), 'val-spatial-accuracy exists separately');
});

console.log('\n================================================================');
console.log(`TEST RESULTS: ${passedTests} / ${totalTests} tests passed (${Math.round(passedTests/totalTests*100)}%)`);
console.log('================================================================\n');

if (passedTests !== totalTests) {
    process.exit(1);
}
