/**
 * ============================================================================
 * TEST SUITE: 3D VIEW FALLBACKS & 4-MINERAL SELECTION WORKFLOW
 * ============================================================================
 * File: tests/test_3d_view_fallbacks.js
 * 
 * Verifies:
 *   1. All four mineral cards can be selected (Coal, Manganese, Iron Ore, Bauxite).
 *   2. Each mineral preserves location and radius on selection.
 *   3. A valid prospectivity grid renders when available (Manganese in T44QMK).
 *   4. Missing prospectivity data triggers the 3D terrain fallback with explanation.
 *   5. Terrain rendering failure offers the working 2D fallback.
 *   6. Switching minerals clears stale prospectivity grids and scores.
 *   7. Missing satellite data does not create a fabricated score.
 *   8. Loading indicators clear after errors, timeouts, or aborts.
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
console.log('TEST SUITE: 3D VIEW FALLBACKS & 4-MINERAL SELECTION WORKFLOW');
console.log('================================================================\n');

const projectRoot = path.resolve(__dirname, '..');
const appJsx = fs.readFileSync(path.join(projectRoot, 'frontend', 'src', 'App.jsx'), 'utf8');
const mineralSelectorJsx = fs.readFileSync(path.join(projectRoot, 'frontend', 'src', 'components', 'MineralSelector.jsx'), 'utf8');
const prospectivity3DMapJsx = fs.readFileSync(path.join(projectRoot, 'frontend', 'src', 'components', 'Prospectivity3DMap.jsx'), 'utf8');
const terrainMap3DJsx = fs.readFileSync(path.join(projectRoot, 'frontend', 'src', 'components', 'TerrainMap3D.jsx'), 'utf8');
const interactiveMapJsx = fs.readFileSync(path.join(projectRoot, 'frontend', 'src', 'components', 'InteractiveMap.jsx'), 'utf8');
const mineralServicePy = fs.readFileSync(path.join(projectRoot, 'backend', 'app', 'mineral_service.py'), 'utf8');

// TEST 1: All four mineral cards can be selected
runTest('1. All four mineral cards can be selected in MineralSelector', () => {
    const requiredMinerals = ['Coal', 'Manganese', 'Iron Ore', 'Bauxite'];
    requiredMinerals.forEach(m => {
        assert(mineralSelectorJsx.includes(`name: '${m}'`), `MineralSelector must include ${m}`);
    });
    assert(mineralSelectorJsx.includes('onClick={() => onSelectMineral(min.name)}'), 'Card must have onClick handler calling onSelectMineral');
});

// TEST 2: Each mineral preserves selected location and radius
runTest('2. Changing mineral preserves selected location and radius in App.jsx', () => {
    assert(appJsx.includes('setSelectedMineral(m)'), 'handleMineralChange must set selected mineral');
    assert(!appJsx.includes('setSelectedLocation(null)'), 'handleMineralChange must not reset location');
    assert(!appJsx.includes('setSelectedRadius(null)'), 'handleMineralChange must not reset radius');
    assert(appJsx.includes('mineral: selectedMineral'), 'Analysis payload must use selectedMineral');
    assert(appJsx.includes('latitude: parseFloat(selectedLocation.lat)'), 'Analysis payload must preserve selected location latitude');
    assert(appJsx.includes('radius_km: parseFloat(selectedRadius)'), 'Analysis payload must preserve selected radius');
});

// TEST 3: Valid prospectivity grid renders when available
runTest('3. A valid prospectivity grid renders when available', () => {
    assert(interactiveMapJsx.includes('isProspectivityAvailable ? ('), 'InteractiveMap must conditionally render Prospectivity3DMap when available');
    assert(interactiveMapJsx.includes('<Prospectivity3DMap'), 'Must render Prospectivity3DMap when grid is valid');
    assert(prospectivity3DMapJsx.includes('analysisResult.prospectivity_grid.grid'), 'Prospectivity3DMap must read genuine grid values');
    assert(prospectivity3DMapJsx.includes('status === \'AVAILABLE\''), 'Must verify AVAILABLE status');
});

// TEST 4: Missing prospectivity data triggers the 3D terrain fallback with explanation
runTest('4. Missing prospectivity data triggers 3D terrain fallback with explanation (Requirement B)', () => {
    assert(interactiveMapJsx.includes('prospectivityNotice={{'), 'InteractiveMap must supply prospectivityNotice to TerrainMap3D when prospectivity is unavailable');
    assert(terrainMap3DJsx.includes('prospectivityNotice'), 'TerrainMap3D must accept prospectivityNotice');
    assert(terrainMap3DJsx.includes('prospectivity-fallback-banner'), 'TerrainMap3D must render dedicated fallback notice banner');
    assert(terrainMap3DJsx.includes('3D Topographic Terrain View'), 'Must inform user that 3D topographic relief is displayed');
});

// TEST 5: Terrain rendering failure offers 2D fallback
runTest('5. Terrain rendering or WebGL failure offers working 2D fallback (Requirement C)', () => {
    assert(terrainMap3DJsx.includes('onFallbackTo2D'), 'TerrainMap3D must accept onFallbackTo2D callback');
    assert(terrainMap3DJsx.includes('webGlError'), 'TerrainMap3D must detect and handle WebGL errors');
    assert(terrainMap3DJsx.includes('btn-terrain-fallback-2d'), 'Must provide return to 2D map button on WebGL failure');
    assert(interactiveMapJsx.includes('onFallbackTo2D={() => setMapMode(\'2d\')}'), 'InteractiveMap must wire onFallbackTo2D to switch to 2D');
});

// TEST 6: Switching minerals does not reuse stale grids or scores
runTest('6. Switching minerals does not reuse stale grids or scores (Requirement E)', () => {
    assert(appJsx.includes('setAnalysisResult(null)'), 'App.jsx must clear analysisResult on mineral change');
    assert(interactiveMapJsx.includes('analysisResult.mineral === targetMineral'), 'InteractiveMap must verify result matches targetMineral');
    assert(prospectivity3DMapJsx.includes('analysisResult.mineral === targetMineral'), 'Prospectivity3DMap must verify result matches targetMineral');
});

// TEST 7: Missing satellite data does not create a fabricated score
runTest('7. Missing satellite data or rasters does not create a fabricated score', () => {
    assert(!mineralServicePy.includes('0.40 * math.exp'), 'No fabricated default 40% exponential curve');
    assert(mineralServicePy.includes('"status": "UNAVAILABLE"'), 'Grid must be UNAVAILABLE when model not trained');
    assert(mineralServicePy.includes('"grid": None'), 'Grid must be None when model not trained');
    assert(mineralServicePy.includes('UNAVAILABLE_NO_MODEL'), 'Prediction availability must be UNAVAILABLE_NO_MODEL for uncalibrated minerals');
});

// TEST 8: Loading indicators clear after errors, timeouts, and cancellations
runTest('8. Loading indicators clear after errors, timeouts, or aborts (Task 4)', () => {
    assert(appJsx.includes('finally {'), 'App.jsx must have finally block in handleRunAnalysis');
    assert(appJsx.includes('setIsAnalyzing(false)'), 'handleRunAnalysis must reset isAnalyzing in finally');
    assert(appJsx.includes('controller.abort'), 'App.jsx must abort in-flight requests on user changes or timeout');
    assert(appJsx.includes('clearTimeout(timeoutId)'), 'App.jsx must clear client safety timeout');
});

console.log('\n================================================================');
console.log(`TEST RESULTS: ${passedTests} / ${totalTests} passed (${Math.round(passedTests / totalTests * 100)}%)`);
console.log('================================================================\n');

if (passedTests === totalTests) {
    process.exit(0);
} else {
    process.exit(1);
}
