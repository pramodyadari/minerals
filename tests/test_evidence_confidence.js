/**
 * ============================================================================
 * AI MINERAL INTELLIGENCE — EVIDENCE & CONFIDENCE SYSTEM TEST SUITE
 * ============================================================================
 * Dedicated tests for:
 *   1. Evidence panel exists in HTML structure
 *   2. Evidence uses actual model data from XAI
 *   3. Missing data displays unavailable (no synthetic values)
 *   4. No fabricated confidence (Strictly "Not Calibrated")
 *   5. Seamless XAI integration (Reuses ExplainableAI module)
 *   6. Zone evidence popup integration
 *   7. Target popup evidence integration
 *   8. Recommendation classification & scientific disclaimer
 *   9. Data provenance & source auditing
 *  10. Neutral startup behavior preserved
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
const ExplainableAI = require(path.join(ROOT_DIR, 'js/xai.js'));
const EvidenceEngine = require(path.join(ROOT_DIR, 'js/evidence.js'));

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
console.log('TEST SUITE: AI PROSPECTIVITY EVIDENCE & CONFIDENCE SYSTEM');
console.log('================================================================\n');

// ----------------------------------------------------------------------------
// Test 1: Evidence panel exists in HTML structure
// ----------------------------------------------------------------------------
runTest('Test 1: Evidence panel and required sub-elements exist in index.html', () => {
    assert(htmlContent.includes('id="dash-evidence-panel"'), 'dash-evidence-panel missing');
    assert(htmlContent.includes('id="evidence-plain-explanation"'), 'evidence-plain-explanation missing');
    assert(htmlContent.includes('id="evidence-rec-tag"'), 'evidence-rec-tag missing');
    assert(htmlContent.includes('id="evidence-rec-action-text"'), 'evidence-rec-action-text missing');
    assert(htmlContent.includes('id="evidence-breakdown-cards"'), 'evidence-breakdown-cards missing');
    assert(htmlContent.includes('id="evidence-top-features-list"'), 'evidence-top-features-list missing');
    assert(htmlContent.includes('id="evidence-limitations-list"'), 'evidence-limitations-list missing');
    assert(htmlContent.includes('id="evidence-provenance-tbody"'), 'evidence-provenance-tbody missing');
    assert(htmlContent.includes('id="model-confidence-status"'), 'model-confidence-status missing in header');
    assert(htmlContent.includes('id="score-confidence-detail"'), 'score-confidence-detail missing in score card');
    assert(htmlContent.includes('<script src="js/evidence.js"></script>'), 'js/evidence.js script tag missing');
});

// ----------------------------------------------------------------------------
// Test 2: Evidence uses actual model data
// ----------------------------------------------------------------------------
runTest('Test 2: Evidence evaluation uses real 10-feature model weights', () => {
    const evalResult = EvidenceEngine.evaluateEvidence({
        lat: 21.9455,
        lon: 80.4295,
        score: 97.6,
        radiusKm: 25
    });

    assert(evalResult.hasTarget === true, 'Expected hasTarget to be true');
    assert.strictEqual(evalResult.score, 97.6, 'Score should match input');
    assert(Array.isArray(evalResult.topModelFeatures), 'topModelFeatures should be an array');
    assert(evalResult.topModelFeatures.length > 0, 'topModelFeatures should not be empty');

    // Verify features have actual names, importance, and formatted contributions
    const topFeat = evalResult.topModelFeatures[0];
    assert(typeof topFeat.name === 'string' && topFeat.name.length > 0, 'Feature must have real name');
    assert(typeof topFeat.contribution === 'number', 'Contribution must be numeric');
    assert(topFeat.contributionFormatted.startsWith('+') || topFeat.contributionFormatted.startsWith('-'), 'Must have sign in format');
    assert(typeof topFeat.importancePct === 'number' && topFeat.importancePct > 0, 'Must have positive importance %');
});

// ----------------------------------------------------------------------------
// Test 3: Missing data displays unavailable (no synthetic values)
// ----------------------------------------------------------------------------
runTest('Test 3: Missing datasets strictly report "DATA NOT AVAILABLE" without fabrication', () => {
    const evalResult = EvidenceEngine.evaluateEvidence({
        lat: 21.9455,
        lon: 80.4295,
        score: 97.6
    });

    const terrainCat = evalResult.evidenceCategories.find(c => c.id === 'terrain-evidence');
    assert(terrainCat, 'Terrain evidence category missing');
    assert.strictEqual(terrainCat.status, 'DATA NOT AVAILABLE', 'Terrain status must be DATA NOT AVAILABLE');
    assert.strictEqual(terrainCat.contribution, 'Unavailable', 'Terrain contribution must be Unavailable');

    const geoCat = evalResult.evidenceCategories.find(c => c.id === 'geological-evidence');
    assert(geoCat, 'Geological evidence category missing');
    assert.strictEqual(geoCat.status, 'DATA NOT AVAILABLE', 'Geology status must be DATA NOT AVAILABLE');
    assert.strictEqual(geoCat.contribution, 'Unavailable', 'Geology contribution must be Unavailable');

    const drillCat = evalResult.evidenceCategories.find(c => c.id === 'drilling-evidence');
    assert(drillCat, 'Drilling evidence category missing');
    assert.strictEqual(drillCat.status, 'DATA NOT AVAILABLE', 'Drilling status must be DATA NOT AVAILABLE');
    assert.strictEqual(drillCat.contribution, 'Unavailable', 'Drilling contribution must be Unavailable');
});

// ----------------------------------------------------------------------------
// Test 4: No fabricated confidence (Strictly "Not Calibrated")
// ----------------------------------------------------------------------------
runTest('Test 4: Model Confidence is distinguished from prospectivity score and marked "Not Calibrated"', () => {
    const evalResult = EvidenceEngine.evaluateEvidence({
        lat: 21.9455,
        lon: 80.4295,
        score: 97.6
    });

    assert.strictEqual(evalResult.modelConfidence.status, 'Not Calibrated', 'Confidence status must be Not Calibrated');
    assert.strictEqual(evalResult.modelConfidence.displayValue, 'Not Calibrated', 'Display value must be Not Calibrated');
    assert.strictEqual(evalResult.modelConfidence.isCalibrated, false, 'isCalibrated must be false');
    assert(evalResult.modelConfidence.methodology.includes('calibration'), 'Must include methodology explanation');

    // Ensure prospectivity score is distinct from confidence
    assert.notStrictEqual(evalResult.score, evalResult.modelConfidence.status, 'Score and confidence must be distinct');
});

// ----------------------------------------------------------------------------
// Test 5: Reuses existing XAI module (no second engine)
// ----------------------------------------------------------------------------
runTest('Test 5: Directly connects to ExplainableAI module and reuses feature weights', () => {
    const xaiDirect = ExplainableAI.explainProspectivityScore(85.0);
    const evalResult = EvidenceEngine.evaluateEvidence({
        lat: 21.9455,
        lon: 80.4295,
        score: 85.0
    });

    const xaiDirectTopName = xaiDirect.waterfallSteps.filter(s => !s.isBaseline && !s.isFinal)[0].name;
    const evidenceTopName = evalResult.topModelFeatures[0].name;
    assert.strictEqual(evidenceTopName, xaiDirectTopName, 'Top feature name must match XAI module exactly');
});

// ----------------------------------------------------------------------------
// Test 6: Zone evidence popup integration
// ----------------------------------------------------------------------------
runTest('Test 6: Candidate zone popups include "WHY THIS ZONE?", rank, and "Not Calibrated"', () => {
    assert(mapJsContent.includes('WHY THIS ZONE?'), 'WHY THIS ZONE? badge missing in map.js');
    assert(mapJsContent.includes('Confidence:'), 'Confidence field missing in map.js zone popup');
    assert(mapJsContent.includes('Not Calibrated'), 'Not Calibrated missing in map.js zone popup');
    assert(mapJsContent.includes('View Evidence'), 'View Evidence button missing in map.js zone popup');
    assert(mapJsContent.includes('dash-evidence-panel'), 'View Evidence action must target dash-evidence-panel');
});

// ----------------------------------------------------------------------------
// Test 7: Target popup evidence integration
// ----------------------------------------------------------------------------
runTest('Test 7: Target popup includes place name, priority, top evidence bullets, and [View Evidence]', () => {
    assert(mapJsContent.includes('TARGET'), 'TARGET badge missing in map.js target popup');
    assert(mapJsContent.includes('Top Evidence:'), 'Top Evidence title missing in map.js target popup');
    assert(mapJsContent.includes('View Evidence'), 'View Evidence button missing in map.js target popup');
    assert(mapJsContent.includes('priorityText'), 'Priority text missing in map.js target popup');
});

// ----------------------------------------------------------------------------
// Test 8: Recommendation classification & scientific disclaimer
// ----------------------------------------------------------------------------
runTest('Test 8: Recommendations classify correctly and enforce non-deposit disclaimer', () => {
    // High Priority (>= 75%)
    const highResult = EvidenceEngine.evaluateEvidence({ lat: 21.9, lon: 80.4, score: 88.0 });
    assert.strictEqual(highResult.recommendation.priority, 'HIGH PRIORITY', 'Expected HIGH PRIORITY for 88%');

    // Medium Priority (50% - 74%)
    const medResult = EvidenceEngine.evaluateEvidence({ lat: 21.9, lon: 80.4, score: 62.0 });
    assert.strictEqual(medResult.recommendation.priority, 'MEDIUM PRIORITY', 'Expected MEDIUM PRIORITY for 62%');

    // Low Priority (< 50%)
    const lowResult = EvidenceEngine.evaluateEvidence({ lat: 21.9, lon: 80.4, score: 35.0 });
    assert.strictEqual(lowResult.recommendation.priority, 'LOW PRIORITY', 'Expected LOW PRIORITY for 35%');

    // Insufficient Data (No score / target)
    const noneResult = EvidenceEngine.evaluateEvidence({});
    assert.strictEqual(noneResult.recommendation.priority, 'INSUFFICIENT DATA', 'Expected INSUFFICIENT DATA without score');

    // Mandatory Disclaimer check
    const expectedDisclaimer = 'AI result is an exploration-screening indication, not confirmation of a mineral deposit.';
    assert.strictEqual(highResult.recommendation.disclaimer, expectedDisclaimer, 'Mandatory disclaimer mismatch');
    assert(htmlContent.includes(expectedDisclaimer), 'Mandatory disclaimer missing in index.html');
});

// ----------------------------------------------------------------------------
// Test 9: Data provenance & source auditing
// ----------------------------------------------------------------------------
runTest('Test 9: Data provenance table audits real sources with correct availability', () => {
    const evalResult = EvidenceEngine.evaluateEvidence({ lat: 21.9, lon: 80.4, score: 90.0 });
    assert(Array.isArray(evalResult.dataProvenance), 'dataProvenance must be an array');
    assert(evalResult.dataProvenance.length >= 8, `Expected at least 8 audited sources, found ${evalResult.dataProvenance.length}`);

    const s2Source = evalResult.dataProvenance.find(s => s.source.includes('Sentinel-2'));
    assert(s2Source && (s2Source.status === 'Available' || s2Source.status === 'AVAILABLE'), 'Sentinel-2 footprint must be Available');

    const rfSource = evalResult.dataProvenance.find(s => s.source.includes('Random Forest'));
    assert(rfSource && (rfSource.status === 'Available' || rfSource.status === 'AVAILABLE'), 'Random Forest model must be Available');

    const drillSource = evalResult.dataProvenance.find(s => s.source.includes('Drilling'));
    assert(drillSource && (drillSource.status === 'Unavailable' || drillSource.status === 'DATA NOT AVAILABLE'), 'Drilling logs must be Unavailable');

    const assaySource = evalResult.dataProvenance.find(s => s.source.includes('Assays'));
    assert(assaySource && (assaySource.status === 'Unavailable' || assaySource.status === 'DATA NOT AVAILABLE'), 'Lab assays must be Unavailable');

    const geoSource = evalResult.dataProvenance.find(s => s.source.includes('Geological Map'));
    assert(geoSource && (geoSource.status === 'Unavailable' || geoSource.status === 'DATA NOT AVAILABLE'), 'Geological map must be Unavailable');
});

// ----------------------------------------------------------------------------
// Test 10: Neutral startup behavior preserved
// ----------------------------------------------------------------------------
runTest('Test 10: Neutral startup state cleanly sets Awaiting Target without errors', () => {
    const neutralResult = EvidenceEngine.evaluateEvidence({});
    assert.strictEqual(neutralResult.hasTarget, false, 'Neutral result hasTarget should be false');
    assert.strictEqual(neutralResult.classification, 'Awaiting Target', 'Classification should be Awaiting Target');
    assert.strictEqual(neutralResult.recommendation.priority, 'INSUFFICIENT DATA', 'Priority should be INSUFFICIENT DATA');
    assert(neutralResult.plainExplanation.includes('Select a location'), 'Plain explanation should prompt user to select a location');
    
    // Check snippet formatting
    const snippet = EvidenceEngine.formatPopupEvidenceSnippet(neutralResult);
    assert(snippet.includes('Awaiting target analysis'), 'Snippet should report awaiting target');

    // Check index.html default placeholders
    assert(htmlContent.includes('No Target Selected'), 'Default place card must show No Target Selected');
    assert(htmlContent.includes('Awaiting Target'), 'Default classification must show Awaiting Target');
});

console.log('\n================================================================');
console.log(`RESULTS: ${passedTests} / ${totalTests} tests passed (${Math.round((passedTests / totalTests) * 100)}%)`);
console.log('================================================================');

if (passedTests < totalTests) {
    process.exit(1);
}
