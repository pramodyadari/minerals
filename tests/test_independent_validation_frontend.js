/**
 * ============================================================================
 * AI MINERAL INTELLIGENCE — PHASE 8 FRONTEND INDEPENDENT VALIDATION TESTS
 * ============================================================================
 * Module: tests/test_independent_validation_frontend.js
 * 
 * Verifies:
 *   1. Category H (Independent Deposit Validation) defaults to "NOT AVAILABLE".
 *   2. Category H formats external evaluation correctly when verified data is active.
 *   3. Separation between Model Confidence (Not Calibrated) and Independent Validation.
 *   4. Separation between within-study spatial-sector validation and independent validation.
 *   5. Data Provenance table includes Independent Manganese Occurrences row.
 *   6. Disclaimers clearly state independent deposit validation status.
 *   7. index.html contains required Phase 8 DOM elements.
 * ============================================================================
 */

const assert = require('assert');
const fs = require('fs');
const path = require('path');

const EvidenceEngine = require('../js/evidence');
const MineralRegistry = require('../js/mineral-registry');
const TargetRankingEngine = require('../js/ranking');

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
console.log(' RUNNING PHASE 8 INDEPENDENT VALIDATION FRONTEND TESTS');
console.log('================================================================');

// 1. Category H defaults to NOT AVAILABLE
runTest('Category H defaults to NOT AVAILABLE when no external dataset is loaded', () => {
    const dossier = EvidenceEngine.evaluateEvidence({
        lat: 21.9455,
        lon: 80.4295,
        score: 87.5
    });

    const indValCat = dossier.evidenceCategories.find(c => c.id === 'independent-validation-evidence');
    assert.ok(indValCat, 'Category H must exist in evidenceCategories');
    assert.strictEqual(indValCat.status, 'NOT AVAILABLE');
    assert.strictEqual(indValCat.contribution, 'Unavailable');
    assert.ok(indValCat.explanation.includes('Ghondi Mine'));
});

// 2. Category H populates when independent validation payload is supplied
runTest('Category H reflects active validation when independent payload is supplied', () => {
    const mockIndependent = {
        status: 'AVAILABLE',
        available: true,
        independent_deposits_count: 3,
        occurrences_count: 5,
        model_version: 'manganese_random_forest'
    };

    const dossier = EvidenceEngine.evaluateEvidence({
        lat: 21.9455,
        lon: 80.4295,
        score: 87.5,
        independentValidation: mockIndependent
    });

    const indValCat = dossier.evidenceCategories.find(c => c.id === 'independent-validation-evidence');
    assert.ok(indValCat);
    assert.strictEqual(indValCat.status, 'Available');
    assert.strictEqual(indValCat.contribution, 'Verified');
    assert.strictEqual(indValCat.depositsTested, 3);
    assert.ok(indValCat.explanation.includes('Independent deposits tested: 3'));
});

// 3. Clear separation between Model Confidence and Independent Validation
runTest('Model Confidence remains strictly Not Calibrated during independent evaluation', () => {
    const dossier = EvidenceEngine.evaluateEvidence({
        lat: 21.9455,
        lon: 80.4295,
        score: 95.0,
        independentValidation: {
            status: 'AVAILABLE',
            available: true,
            independent_deposits_count: 2
        }
    });

    assert.strictEqual(dossier.modelConfidence.status, 'Not Calibrated');
    assert.strictEqual(dossier.modelConfidence.isCalibrated, false);
});

// 4. Separation between within-study spatial validation and independent validation
runTest('Within-study spatial validation and independent validation are kept separate', () => {
    const dossier = EvidenceEngine.evaluateEvidence({
        lat: 21.9455,
        lon: 80.4295,
        score: 90.0
    });

    const spatialVal = dossier.evidenceCategories.find(c => c.id === 'validation-evidence');
    assert.ok(spatialVal);
    assert.ok(spatialVal.explanation.includes('Within-study spatial-sector validation'));

    const indVal = dossier.evidenceCategories.find(c => c.id === 'independent-validation-evidence');
    assert.ok(indVal);
    assert.strictEqual(indVal.status, 'NOT AVAILABLE');
});

// 5. Data Provenance table includes Independent Occurrences row
runTest('Data Provenance table includes Independent Manganese Occurrences row', () => {
    const dossier = EvidenceEngine.evaluateEvidence({
        lat: 21.9455,
        lon: 80.4295,
        score: 87.5
    });

    const row = dossier.dataProvenance.find(d => d.source.includes('Independent Manganese Occurrences'));
    assert.ok(row, 'Independent occurrences row must exist in provenance table');
    assert.strictEqual(row.status, 'DATA NOT AVAILABLE');
});

// 6. Mandatory disclaimers
runTest('Mandatory disclaimers for screening and independent validation are present', () => {
    const dossier = EvidenceEngine.evaluateEvidence({
        lat: 21.9455,
        lon: 80.4295,
        score: 87.5
    });

    assert.ok(dossier.recommendation.disclaimer.includes('exploration-screening indication'));
    assert.ok(dossier.recommendation.independentValidationDisclaimer.includes('not currently available'));
});

// 7. index.html contains Phase 8 elements
runTest('index.html contains Phase 8 DOM elements for training deposit and independent validation', () => {
    const htmlPath = path.join(__dirname, '..', 'index.html');
    const html = fs.readFileSync(htmlPath, 'utf8');

    assert.ok(html.includes('id="val-training-deposit"'), 'val-training-deposit must exist');
    assert.ok(html.includes('id="val-independent-deposits-count"'), 'val-independent-deposits-count must exist');
    assert.ok(html.includes('id="val-leakage-check"'), 'val-leakage-check must exist');
    assert.ok(html.includes('id="val-independent-status"'), 'val-independent-status must exist');
    assert.ok(html.includes('Ghondi Manganese Mine'), 'Ghondi training deposit label must be in html');
});

// 8. Ranking preserved
runTest('Ranking order is unchanged by Phase 8 additions', () => {
    const ranking = TargetRankingEngine.getRankedTargets('manganese');
    assert.ok(ranking.isTrained);
    assert.strictEqual(ranking.targets.length, 20);
    assert.strictEqual(ranking.targets[0].rank, 1);
});

console.log('================================================================');
console.log(`TEST RESULTS: ${passedTests} / ${totalTests} tests passed (${Math.round((passedTests/totalTests)*100)}%)`);
console.log('================================================================\n');

if (passedTests !== totalTests) {
    process.exit(1);
}
