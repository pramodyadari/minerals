/**
 * Test Suite: Phase 3 Noamundi Dashboard Integration & Scientific Layers
 * Validates:
 * 1. HTML structure: Warning banner container, Noamundi presets in both dropdowns
 * 2. Map legend: 4 distinct, separate scientific layers (AI prospectivity, spectral, terrain, geology)
 * 3. app.js: displayNoamundiIronOreEvidence and displayUnprocessedIronOreState exist
 * 4. app.js: getProcessedEvidence method defined in API
 * 5. Scientific guardrails: Null score, 36.11% cloud-free warning, non-extrapolation
 * 6. locations.js: Noamundi entry in KNOWN_PLACES
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
    } catch (err) {
        console.error(`[FAIL] ${name}: ${err.message}`);
    }
}

console.log('================================================================');
console.log('TEST SUITE: PHASE 3 NOAMUNDI DASHBOARD INTEGRATION');
console.log('================================================================\n');

const htmlPath = path.join(__dirname, '..', 'index.html');
const appJsPath = path.join(__dirname, '..', 'app.js');
const locationsJsPath = path.join(__dirname, '..', 'js', 'locations.js');

const htmlContent = fs.readFileSync(htmlPath, 'utf8');
const appJsContent = fs.readFileSync(appJsPath, 'utf8');
const locationsJsContent = fs.readFileSync(locationsJsPath, 'utf8');

// 1. Warning Container in index.html
runTest('Test 1: #noamundi-quality-warning-container exists in index.html', () => {
    assert(htmlContent.includes('id="noamundi-quality-warning-container"'), 'Container must exist');
});

// 2. Noamundi preset options in location dropdowns
runTest('Test 2: Noamundi Iron Sector options present in location selects', () => {
    assert(htmlContent.includes('value="noamundi"'), 'noamundi option must exist');
    assert(htmlContent.includes('data-lat="22.1500" data-lon="85.5000"'), 'Noamundi coordinates must match 22.15, 85.50');
});

// 3. Four scientifically distinct map legend sections
runTest('Test 3: Map legend contains 4 distinct scientific layer sections', () => {
    assert(htmlContent.includes('id="legend-ai-prospectivity"'), 'AI prospectivity section must exist');
    assert(htmlContent.includes('id="legend-spectral-evidence"'), 'Spectral evidence section must exist');
    assert(htmlContent.includes('id="legend-terrain-elevation"'), 'Terrain elevation section must exist');
    assert(htmlContent.includes('id="legend-geological-context"'), 'Geological context section must exist');
    assert(htmlContent.includes('Tile T44QMK Validated Only'), 'Manganese limitation note must be present');
    assert(htmlContent.includes('Surface reflectance indications only'), 'Spectral disclaimer must be present');
});

// 4. app.js API method getProcessedEvidence
runTest('Test 4: API.getProcessedEvidence defined in app.js', () => {
    assert(appJsContent.includes('async getProcessedEvidence('), 'getProcessedEvidence method must exist');
    assert(appJsContent.includes('/api/evidence/processed'), 'Must call backend endpoint /api/evidence/processed');
});

// 5. app.js Noamundi evidence display handler
runTest('Test 5: displayNoamundiIronOreEvidence defined in app.js', () => {
    assert(appJsContent.includes('async function displayNoamundiIronOreEvidence('), 'Function must be defined');
    assert(appJsContent.includes('Unavailable — no validated spatial Iron Ore model'), 'Must enforce unvalidated model status');
    assert(appJsContent.includes('36.11%'), 'Must display 36.11% valid coverage warning');
    assert(appJsContent.includes('63.89%'), 'Must state 63.89% cloud/shadow obscured');
});

// 6. app.js non-extrapolation handler for Iron Ore
runTest('Test 6: displayUnprocessedIronOreState defined in app.js', () => {
    assert(appJsContent.includes('function displayUnprocessedIronOreState('), 'Function must be defined');
    assert(appJsContent.includes('New satellite imagery must be acquired and processed'), 'Must indicate acquisition required');
});

// 7. locations.js includes Noamundi
runTest('Test 7: Noamundi Iron Sector registered in locations.js KNOWN_PLACES', () => {
    assert(locationsJsContent.includes('noamundi-iron-mine'), 'Noamundi id must be in KNOWN_PLACES');
    assert(locationsJsContent.includes('22.15'), 'Latitude 22.15 must be registered');
    assert(locationsJsContent.includes('85.5'), 'Longitude 85.50 must be registered');
});

console.log(`\n================================================================`);
console.log(`TEST RESULTS: ${passedTests} / ${totalTests} tests passed (${Math.round((passedTests/totalTests)*100)}%)`);
console.log(`================================================================\n`);

if (passedTests !== totalTests) {
    process.exit(1);
}
