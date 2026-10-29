/**
 * ============================================================================
 * REGRESSION TEST SUITE: MINERAL ELIGIBILITY & 3D VISUALIZATION INTEGRITY
 * ============================================================================
 * Test Suite: tests/test_mineral_eligibility_3d_frontend.js
 * 
 * Verifies:
 *   1. No common or hardcoded 40% score in Prospectivity3DMap.jsx or backend.
 *   2. Removal of synthetic peak formulas (peak1 = 0.88, peak2 = 0.72, 0.40 * exp).
 *   3. Initial peakScore state is null (no fake default score like 87.5).
 *   4. Authoritative availability guard isProspectivityAvailable requires genuine prediction and calibrated grid.
 *   5. Callout pin is strictly hidden when prospectivity data is unavailable.
 *   6. Prominent glassmorphism card displayed when 3D prospectivity is unavailable.
 *   7. 3D Terrain switch option is available when prospectivity data is unavailable.
 *   8. InteractiveMap passes onSwitchToTerrain to Prospectivity3DMap.
 *   9. MineralSelector independently labels Coal, Iron Ore, Bauxite as awaiting data and Manganese as trained on Tile T44QMK.
 *  10. App.jsx resets analysisResult on mineral selection to prevent stale score leakage.
 *  11. ResultsPanel withholds numerical prediction scores when model is unavailable.
 * ============================================================================
 */

const assert = require('assert');
const fs = require('fs');
const path = require('path');

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
console.log('TEST SUITE: MINERAL-SPECIFIC ELIGIBILITY & 3D SCORE INTEGRITY');
console.log('================================================================\n');

const projectRoot = path.resolve(__dirname, '..');
const prospectivityMapPath = path.join(projectRoot, 'frontend', 'src', 'components', 'Prospectivity3DMap.jsx');
const interactiveMapPath = path.join(projectRoot, 'frontend', 'src', 'components', 'InteractiveMap.jsx');
const mineralSelectorPath = path.join(projectRoot, 'frontend', 'src', 'components', 'MineralSelector.jsx');
const appJsxPath = path.join(projectRoot, 'frontend', 'src', 'App.jsx');
const resultsPanelPath = path.join(projectRoot, 'frontend', 'src', 'components', 'ResultsPanel.jsx');
const mineralServicePath = path.join(projectRoot, 'backend', 'app', 'mineral_service.py');

const prospectivityContent = fs.readFileSync(prospectivityMapPath, 'utf8');
const interactiveMapContent = fs.readFileSync(interactiveMapPath, 'utf8');
const mineralSelectorContent = fs.readFileSync(mineralSelectorPath, 'utf8');
const appJsxContent = fs.readFileSync(appJsxPath, 'utf8');
const resultsPanelContent = fs.readFileSync(resultsPanelPath, 'utf8');
const mineralServiceContent = fs.readFileSync(mineralServicePath, 'utf8');

// TEST 1: No hardcoded 0.40 exponential profile in backend
runTest('Backend mineral_service.py does NOT generate synthetic 0.40 exponential grid', () => {
    assert(!mineralServiceContent.includes('0.40 * math.exp'), 'Found forbidden 0.40 * math.exp formula in mineral_service.py');
    assert(mineralServiceContent.includes('"status": "UNAVAILABLE"'), 'mineral_service.py must return explicit UNAVAILABLE status');
    assert(mineralServiceContent.includes('"grid": None'), 'mineral_service.py must return grid: None when unvalidated');
});

// TEST 2: No synthetic peak formula in Prospectivity3DMap.jsx
runTest('Prospectivity3DMap.jsx does NOT generate synthetic peak1/peak2/ridge formulas', () => {
    assert(!prospectivityContent.includes('0.88 * Math.exp'), 'Found forbidden synthetic peak1 in Prospectivity3DMap.jsx');
    assert(!prospectivityContent.includes('0.72 * Math.exp'), 'Found forbidden synthetic peak2 in Prospectivity3DMap.jsx');
    assert(!prospectivityContent.includes('0.45 * Math.exp'), 'Found forbidden synthetic ridge in Prospectivity3DMap.jsx');
});

// TEST 3: No default initial score (e.g. 87.5) in Prospectivity3DMap.jsx
runTest('Prospectivity3DMap.jsx initializes peakScore to null', () => {
    assert(!prospectivityContent.includes('useState(87.5)'), 'Found hardcoded default peakScore 87.5 in Prospectivity3DMap.jsx');
    assert(prospectivityContent.includes('useState(null)'), 'peakScore must initialize to null');
});

// TEST 4: Authoritative isProspectivityAvailable condition
runTest('Prospectivity3DMap.jsx evaluates isProspectivityAvailable from authentic prediction and calibrated grid', () => {
    assert(prospectivityContent.includes('isProspectivityAvailable'), 'Must define isProspectivityAvailable');
    assert(prospectivityContent.includes('analysisResult.prediction'), 'Must check analysisResult.prediction');
    assert(prospectivityContent.includes('is_calibrated === true'), 'Must check is_calibrated === true');
    assert(prospectivityContent.includes('status === \'AVAILABLE\''), 'Must check grid status === AVAILABLE');
});

// TEST 5: Callout pin is strictly hidden when prospectivity is unavailable
runTest('Prospectivity3DMap.jsx guards callout pin with isProspectivityAvailable', () => {
    assert(prospectivityContent.includes('isProspectivityAvailable && showCallout'), 'Callout pin must be guarded by isProspectivityAvailable');
    assert(!prospectivityContent.includes('|| peakScore}%'), 'Callout pin must not fall back to peakScore');
});

// TEST 6: Dedicated unavailable card shown when prospectivity is unavailable
runTest('Prospectivity3DMap.jsx renders dedicated unavailable card explaining missing model or domain', () => {
    assert(prospectivityContent.includes('!isProspectivityAvailable'), 'Must render conditional unavailable state');
    assert(prospectivityContent.includes('3D Prospectivity Mesh Unavailable'), 'Must display clear unavailable heading');
    assert(prospectivityContent.includes('No validated spatial machine-learning model exists'), 'Must explain commodity model absence');
    assert(prospectivityContent.includes('Tile T44QMK'), 'Must explain regional footprint restriction for Manganese');
});

// TEST 7: 3D terrain switch option is available
runTest('Prospectivity3DMap.jsx supports switching to 3D Terrain View', () => {
    assert(prospectivityContent.includes('onSwitchToTerrain'), 'Must accept onSwitchToTerrain callback');
    assert(prospectivityContent.includes('Switch to 3D Terrain View'), 'Must render button to switch to 3D terrain');
});

// TEST 8: InteractiveMap passes onSwitchToTerrain
runTest('InteractiveMap.jsx passes onSwitchToTerrain to Prospectivity3DMap', () => {
    assert(interactiveMapContent.includes('onSwitchToTerrain={() => setMapMode(\'3d-terrain\')}'), 'InteractiveMap must wire onSwitchToTerrain');
});

// TEST 9: MineralSelector has mineral-specific statuses
runTest('MineralSelector.jsx distinguishes Coal, Iron Ore, Bauxite from Manganese', () => {
    assert(mineralSelectorContent.includes('AWAITING_DATA'), 'Must label unmodeled minerals as AWAITING_DATA');
    assert(mineralSelectorContent.includes('Tile T44QMK'), 'Must note Tile T44QMK limitation for Manganese');
});

// TEST 10: App.jsx clears analysisResult on mineral change
runTest('App.jsx resets analysisResult on mineral change to prevent score leakage', () => {
    assert(appJsxContent.includes('setSelectedMineral(m)'), 'Must update selected mineral');
    assert(appJsxContent.includes('setAnalysisResult(null)'), 'Must reset analysisResult on mineral change');
});

// TEST 11: ResultsPanel withholds numerical prediction scores when model is unavailable
runTest('ResultsPanel.jsx only displays numerical prospectivity score when isSuccess && prediction', () => {
    assert(resultsPanelContent.includes('{isSuccess && prediction && ('), 'Verdict score box must require isSuccess and prediction');
    assert(resultsPanelContent.includes('Prediction Score Withheld'), 'Must display score withheld note');
});

// TEST 12: Backend mineral-by-mineral independent checks
runTest('Backend mineral_service.py checks each commodity independently', () => {
    assert(mineralServiceContent.includes('elif canonical_mineral == "Coal":'), 'Must check Coal independently');
    assert(mineralServiceContent.includes('elif canonical_mineral == "Iron Ore":'), 'Must check Iron Ore independently');
    assert(mineralServiceContent.includes('elif canonical_mineral == "Bauxite":'), 'Must check Bauxite independently');
    assert(mineralServiceContent.includes('manganese_random_forest.pkl'), 'Must check manganese model artifact existence');
});

console.log('\n================================================================');
console.log(`TEST RESULTS: ${passedTests} / ${totalTests} passed (${Math.round(passedTests / totalTests * 100)}%)`);
console.log('================================================================\n');

if (passedTests === totalTests) {
    process.exit(0);
} else {
    process.exit(1);
}
