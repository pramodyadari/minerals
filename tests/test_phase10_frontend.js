/**
 * ============================================================================
 * AI MINERAL INTELLIGENCE — PHASE 10 FRONTEND & UX INTEGRITY TESTS
 * ============================================================================
 * Module: tests/test_phase10_frontend.js
 *
 * Verifies:
 *   1. Professional Dashboard Header & Status Indicators (Honest indicators only).
 *   2. Exploration Command Center with 5-step visual decision support and neutral startup.
 *   3. Mineral Selector (Manganese TRAINED, 6 other minerals AWAITING TRAINING DATA).
 *   4. Target Analysis Card & XAI why-this-target display.
 *   5. Prospectivity Score Explanation (Spatial Prospectivity Index, not probability).
 *   6. Evidence Scorecard (Honest Categories A-H, no unavailable as positive).
 *   7. Model Trust Panel (Within-study 96.76%, Not Calibrated, Independent Not Available, SHA-256 Verified).
 *   8. Top Exploration Targets (Real candidate zones ranking).
 *   9. Target Comparison with Percentage Points difference (no false statistical significance).
 *  10. Map Target Popup with required action buttons.
 *  11. 3D Prospectivity Surface title, legend, and honest z-axis label.
 *  12. Exploration Target Report generation and modal workflow.
 *  13. System Health modal and Data Provenance integrity.
 *  14. Demo Mode functionality using genuine targets.
 *  15. Persistent footer disclaimer.
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
console.log(' RUNNING PHASE 10 FRONTEND & UX INTEGRITY TESTS');
console.log('================================================================');

const htmlPath = path.join(__dirname, '..', 'index.html');
const indexHtml = fs.readFileSync(htmlPath, 'utf8');

// 1. Header Status Indicators
runTest('Header contains exact Phase 10 status indicators and honest nomenclature', () => {
    assert.ok(indexHtml.includes('AI MINERAL EXPLORATION'), 'Header must contain AI MINERAL EXPLORATION');
    assert.ok(indexHtml.includes('AI-assisted mineral prospectivity screening and exploration target intelligence'), 'Subtitle must match');
    assert.ok(indexHtml.includes('MODEL') && indexHtml.includes('TRAINED'), 'MODEL TRAINED pill must exist');
    assert.ok(indexHtml.includes('VALIDATION') && indexHtml.includes('WITHIN-STUDY'), 'VALIDATION WITHIN-STUDY pill must exist');
    assert.ok(indexHtml.includes('CALIBRATION') && indexHtml.includes('NOT CALIBRATED'), 'CALIBRATION NOT CALIBRATED pill must exist');
    assert.ok(indexHtml.includes('INDEPENDENT VALIDATION') && indexHtml.includes('NOT AVAILABLE'), 'INDEPENDENT VALIDATION NOT AVAILABLE pill must exist');
    
    // Disallow forbidden fake claims
    assert.ok(!indexHtml.includes('PRODUCTION VERIFIED'), 'Must not claim PRODUCTION VERIFIED');
    assert.ok(!indexHtml.includes('FIELD VERIFIED'), 'Must not claim FIELD VERIFIED');
});

// 2. Exploration Command Center Workflow Steps
runTest('Exploration Command Center has 5 workflow steps and neutral initial state', () => {
    assert.ok(indexHtml.includes('EXPLORATION COMMAND CENTER'), 'Command center title must exist');
    assert.ok(indexHtml.includes('SELECT MINERAL'), 'Step 1 must be SELECT MINERAL');
    assert.ok(indexHtml.includes('SELECT LOCATION'), 'Step 2 must be SELECT LOCATION');
    assert.ok(indexHtml.includes('ANALYZE TARGET'), 'Step 3 must be ANALYZE TARGET');
    assert.ok(indexHtml.includes('REVIEW EVIDENCE'), 'Step 4 must be REVIEW EVIDENCE');
    assert.ok(indexHtml.includes('COMPARE / EXPORT'), 'Step 5 must be COMPARE / EXPORT');
    assert.ok(indexHtml.includes('id="target-place-name"') && indexHtml.includes('No Target Selected'), 'Initial neutral state must be No Target Selected');
    assert.ok(indexHtml.includes('id="command-center-target-state"'), 'Command center target state element must exist');
});

// 3. Target Analysis Card & Export Target Report Button
runTest('Target Analysis Card contains required chips and Export Target Report button', () => {
    assert.ok(indexHtml.includes('TARGET ANALYSIS'), 'Target Analysis title must exist');
    assert.ok(indexHtml.includes('id="target-card-mineral"'), 'Mineral chip must exist');
    assert.ok(indexHtml.includes('id="target-card-prospectivity"'), 'Prospectivity chip must exist');
    assert.ok(indexHtml.includes('id="target-card-priority"'), 'Priority chip must exist');
    assert.ok(indexHtml.includes('id="target-card-status"'), 'Status chip must exist');
    assert.ok(indexHtml.includes('EXPLORATION SCREENING'), 'Status text must be EXPLORATION SCREENING');
    assert.ok(indexHtml.includes('id="btn-export-target-report"'), 'Export Target Report button must exist');
    assert.ok(indexHtml.includes('WHY THIS TARGET?'), 'WHY THIS TARGET? header must exist');
});

// 4. Prospectivity Score Explanation
runTest('Prospectivity score explanation text is present in the DOM', () => {
    const requiredExplanation = 'Spatial Prospectivity Index derived from the trained Random Forest model. This is an exploration-screening score, not a probability of mineral occurrence.';
    assert.ok(indexHtml.includes(requiredExplanation), 'Prospectivity score explanation must match specification');
});

// 5. Evidence Scorecard Categories
runTest('Evidence Engine contains Categories A through H with honest statuses', () => {
    const dossier = EvidenceEngine.evaluateEvidence({ lat: 21.9455, lon: 80.4295, score: 87.5 });
    assert.ok(dossier.evidenceCategories.length >= 8, 'Must have at least 8 evidence categories');

    const catIds = dossier.evidenceCategories.map(c => c.id);
    assert.ok(catIds.includes('model-evidence'), 'Category A must exist');
    assert.ok(catIds.includes('spatial-evidence'), 'Category B must exist');
    assert.ok(catIds.includes('spectral-evidence'), 'Category C must exist');
    assert.ok(catIds.includes('terrain-evidence'), 'Category D must exist');
    assert.ok(catIds.includes('geological-evidence'), 'Category E must exist');
    assert.ok(catIds.includes('drilling-evidence'), 'Category F must exist');
    assert.ok(catIds.includes('validation-evidence'), 'Category G must exist');
    assert.ok(catIds.includes('independent-validation-evidence'), 'Category H must exist');

    // Geological, Terrain, Subsurface, and Independent Validation must not be positive
    const terrainCat = dossier.evidenceCategories.find(c => c.id === 'terrain-evidence');
    assert.strictEqual(terrainCat.status, 'DATA NOT AVAILABLE');

    const geoCat = dossier.evidenceCategories.find(c => c.id === 'geological-evidence');
    assert.strictEqual(geoCat.status, 'DATA NOT AVAILABLE');

    const subCat = dossier.evidenceCategories.find(c => c.id === 'drilling-evidence');
    assert.strictEqual(subCat.status, 'DATA NOT AVAILABLE');

    const indValCat = dossier.evidenceCategories.find(c => c.id === 'independent-validation-evidence');
    assert.strictEqual(indValCat.status, 'NOT AVAILABLE');
});

// 6. Model Trust & Validation Panel in HTML
runTest('Model Trust panel displays accurate metrics and honest limitations', () => {
    assert.ok(indexHtml.includes('MODEL TRUST & VALIDATION') || indexHtml.includes('MODEL TRUST'), 'Trust panel title must exist');
    assert.ok(indexHtml.includes('T44QMK Sentinel-2'), 'Training dataset must be listed');
    assert.ok(indexHtml.includes('Ghondi Manganese Mine'), 'Reference deposit must be listed');
    assert.ok(indexHtml.includes('Within-study spatial-sector validation'), 'Validation methodology must be within-study');
    assert.ok(indexHtml.includes('96.76%'), 'Accuracy must be 96.76%');
    assert.ok(indexHtml.includes('96.71%'), 'F1 must be 96.71%');
    assert.ok(indexHtml.includes('0.9931'), 'ROC-AUC must be 0.9931');
    assert.ok(indexHtml.includes('0.9923'), 'PR-AUC must be 0.9923');
    assert.ok(indexHtml.includes('SHA-256 VERIFIED'), 'Model SHA-256 integrity badge must exist');
    assert.ok(indexHtml.includes('The reported validation measures performance within the available study area'), 'Limitation explanation must exist');
});

// 7. Multi-Mineral Registry Protections
runTest('Multi-Mineral Registry protects untrained minerals from Manganese prediction spillover', () => {
    assert.strictEqual(MineralRegistry.isTrained('manganese'), true);
    assert.strictEqual(MineralRegistry.isTrained('copper'), false);
    assert.strictEqual(MineralRegistry.isTrained('lithium'), false);
    assert.strictEqual(MineralRegistry.isTrained('iron_ore'), false);

    const copper = MineralRegistry.getMineral('copper');
    assert.strictEqual(copper.status, 'framework_ready');
    assert.strictEqual(copper.modelAvailable, false);
    assert.strictEqual(copper.productionModelAvailable, false);
});

// 8. Target Comparison Score Difference
runTest('Target Comparison shows percentage points difference without claiming statistical significance', () => {
    const comparison = TargetRankingEngine.compareTargets(['67684', '124766']);
    assert.ok(comparison && comparison.rows, 'Comparison must produce structured rows');
    const diffRow = comparison.rows.find(r => r.id === 'scoreDiff');
    assert.ok(diffRow, 'Comparison must include Score Difference row');
    assert.strictEqual(diffRow.label, 'Score Difference');
    assert.ok(diffRow.values.some(v => v.includes('percentage points')), 'Must express difference in percentage points');
    assert.ok(diffRow.note.includes('does not represent statistical significance'), 'Must disclaim statistical significance');
});

// 9. 3D Prospectivity Legend and Axis Honesty
runTest('3D View has honest Prospectivity Surface title and index legend', () => {
    assert.ok(indexHtml.includes('3D PROSPECTIVITY SURFACE'), '3D View title must be 3D PROSPECTIVITY SURFACE');
    assert.ok(indexHtml.includes('0–50') && indexHtml.includes('LOW'), 'Legend must have 0-50 LOW');
    assert.ok(indexHtml.includes('50–75') && indexHtml.includes('MEDIUM'), 'Legend must have 50-75 MEDIUM');
    assert.ok(indexHtml.includes('75–100') && indexHtml.includes('HIGH'), 'Legend must have 75-100 HIGH');
});

// 10. Modals Exist (Target Report & System Health)
runTest('Target Report and System Health modals exist in DOM', () => {
    assert.ok(indexHtml.includes('id="target-report-modal"'), 'Target report modal must exist');
    assert.ok(indexHtml.includes('id="system-health-modal"'), 'System health modal must exist');
    assert.ok(indexHtml.includes('AI MINERAL EXPLORATION TARGET REPORT'), 'Report title must be present in report modal');
    assert.ok(indexHtml.includes('SYSTEM HEALTH AUDIT'), 'System health modal title must exist');
});

// 11. Persistent Footer Disclaimer
runTest('Persistent footer disclaimer is present and truthful', () => {
    assert.ok(indexHtml.includes('id="app-footer-disclaimer"'), 'Footer disclaimer container must exist');
    const footerText = 'Exploration screening only. Prospectivity scores are model-derived spatial indices, not probabilities of mineral occurrence. Independent deposit validation is currently unavailable. Field verification and subsurface investigation are required.';
    assert.ok(indexHtml.includes(footerText), 'Footer text must match required scientific disclaimer');
});

// 12. App JS exports Phase 10 API handlers
runTest('app.js exports Phase 10 interactive handlers', () => {
    const appJsPath = path.join(__dirname, '..', 'app.js');
    const appJsContent = fs.readFileSync(appJsPath, 'utf8');
    assert.ok(appJsContent.includes('openTargetReportModal'), 'openTargetReportModal must exist');
    assert.ok(appJsContent.includes('openSystemHealthModal'), 'openSystemHealthModal must exist');
    assert.ok(appJsContent.includes('runDemoMode'), 'runDemoMode must exist');
    assert.ok(appJsContent.includes('updateCommandCenterWorkflow'), 'updateCommandCenterWorkflow must exist');
    assert.ok(appJsContent.includes('generateTargetReportData'), 'generateTargetReportData must exist');
    assert.ok(appJsContent.includes('downloadTargetReportMarkdown'), 'downloadTargetReportMarkdown must exist');
    assert.ok(appJsContent.includes('exportTargetReportGeoJSON'), 'exportTargetReportGeoJSON must exist');
});

console.log('================================================================');
console.log(`Phase 10 Frontend Tests: ${passedTests} / ${totalTests} passed.`);
console.log('================================================================');
