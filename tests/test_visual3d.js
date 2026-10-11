/**
 * ============================================================================
 * PHASE 4 TEST & CRITICAL VALIDATION SUITE — 3D PROSPECTIVITY VISUALIZATION
 * ============================================================================
 */

const fs = require('fs');
const GeoEngine = require('../js/geo');
const MineralData = require('../js/data');

// Mock window and document for headless Node execution
global.document = {
    getElementById: (id) => ({
        id: id,
        innerHTML: '',
        querySelector: () => null,
        querySelectorAll: () => []
    }),
    querySelector: () => null,
    querySelectorAll: () => [],
    fullscreenElement: null
};

global.window = {
    Plotly: {
        react: () => {}
    },
    document: global.document
};

const Visual3D = require('../js/visual3d');

// Load full tile grid data directly for headless testing
const tileJson = JSON.parse(fs.readFileSync('data/processed/tile_prospectivity_549.json', 'utf8'));

console.log("================================================================");
console.log("TEST SUITE: 3D MINERAL PROSPECTIVITY VISUALIZATION (PHASE 4)");
console.log("================================================================\n");

let passedTests = 0;
let totalTests = 0;

function assert(condition, message, details = "") {
    totalTests++;
    if (condition) {
        console.log(`[PASS] ${message}`);
        passedTests++;
    } else {
        console.error(`[FAIL] ${message}`);
        if (details) console.error(`       Details: ${details}`);
    }
}

// ----------------------------------------------------------------------------
// TEST 1: Known Project Location (Ghondi Mine: 21.9455°N, 80.4295°E, Radius 25km)
// ----------------------------------------------------------------------------
console.log("--- TEST 1: Known Mine Ground-Truth 3D Surface Extraction ---");
const test1Params = { lat: 21.9455, lon: 80.4295, radiusKm: 25, resolution: 50 };
Visual3D.init('dummy', test1Params);

// Extract spatial window
const res1 = Visual3D.setLocation(21.9455, 80.4295, "Ghondi Manganese Mine");
const val1 = Visual3D.getValidation();

assert(res1 !== null, "Spatial window extracted successfully for Known Mine");
assert(res1.eastings.length === 50 && res1.northings.length === 50, "X and Y coordinate grids have 50x50 resolution");
assert(res1.zScores.length === 50 && res1.zScores[0].length === 50, "Z-Score 2D matrix matches 50x50 dimensions");

// Verify coordinates are actual projected UTM Zone 44N meters
const expectedEasting = 441089.33;
const expectedNorthing = 2426904.20;
const centerEasting = (res1.stats.xMin + res1.stats.xMax) / 2;
const centerNorthing = (res1.stats.yMin + res1.stats.yMax) / 2;

assert(Math.abs(centerEasting - expectedEasting) < 1.0, `X Axis centered on UTM Easting ${expectedEasting.toFixed(0)}m (Got: ${centerEasting.toFixed(0)}m)`);
assert(Math.abs(centerNorthing - expectedNorthing) < 1.0, `Y Axis centered on UTM Northing ${expectedNorthing.toFixed(0)}m (Got: ${centerNorthing.toFixed(0)}m)`);

// Verify Z values are actual percentages (0-100%) and match model
assert(res1.stats.maxScore > 80.0, `Peak prospectivity within 25km window is high (Got: ${res1.stats.maxScore.toFixed(1)}%)`);
assert(res1.stats.minScore >= 0.0 && res1.stats.maxScore <= 100.0, `All Z scores strictly bounded between 0% and 100%`);

// ----------------------------------------------------------------------------
// TEST 2: Different Location in Sentinel-2 Tile (Candidate Zone 67684: 22.214160°N, 80.063632°E)
// ----------------------------------------------------------------------------
console.log("\n--- TEST 2: Different Location within Tile (Candidate Zone 67684) ---");
const res2 = Visual3D.setLocation(22.214160, 80.063632, "Candidate Zone #67684");

assert(res2 !== null, "Spatial window extracted for Zone 67684");
assert(res2.stats.xMin !== res1.stats.xMin, "Bounding box changes dynamically when location changes");
assert(res2.stats.maxScore >= 95.0, `Zone 67684 window contains verified high peak (Got: ${res2.stats.maxScore.toFixed(1)}%)`);

// ----------------------------------------------------------------------------
// TEST 3: 10 km Radius
// ----------------------------------------------------------------------------
console.log("\n--- TEST 3: 10 km Local Cluster Radius ---");
Visual3D.setRadius(10);
const res3 = Visual3D.setLocation(21.9455, 80.4295, "Ghondi Mine (10km)");
const widthKm3 = (res3.stats.xMax - res3.stats.xMin) / 1000;
assert(widthKm3 === 20.0, `10 km radius creates exactly 20 km × 20 km spatial window (Got: ${widthKm3} km)`);

// ----------------------------------------------------------------------------
// TEST 4: 50 km Radius
// ----------------------------------------------------------------------------
console.log("\n--- TEST 4: 50 km Regional Belt Radius ---");
Visual3D.setRadius(50);
const res4 = Visual3D.setLocation(21.9455, 80.4295, "Ghondi Mine (50km)");
const widthKm4 = (res4.stats.xMax - res4.stats.xMin) / 1000;
assert(widthKm4 === 100.0, `50 km radius creates exactly 100 km × 100 km spatial window (Got: ${widthKm4} km)`);
assert(res4.stats.zonesCount > res3.stats.zonesCount, `50 km window captures more candidate zones (${res4.stats.zonesCount}) than 10 km window (${res3.stats.zonesCount})`);

// ----------------------------------------------------------------------------
// TEST 5: 100 km Radius
// ----------------------------------------------------------------------------
console.log("\n--- TEST 5: 100 km Tile Overview Radius ---");
Visual3D.setRadius(100);
const res5 = Visual3D.setLocation(21.9455, 80.4295, "Ghondi Mine (100km)");
assert(res5.stats.zonesCount === 20, `100 km radius captures all 20 candidate zones on tile (Got: ${res5.stats.zonesCount} zones)`);

// ----------------------------------------------------------------------------
// REQUIREMENT 19: CRITICAL VALIDATION LOGGING
// ----------------------------------------------------------------------------
console.log("\n================================================================");
console.log("REQUIREMENT 19: CRITICAL VALIDATION LOG OUTPUT");
console.log("================================================================");

// Log validation for 25km Known Mine exploration target
Visual3D.setRadius(25);
Visual3D.setLocation(21.9455, 80.4295, "Ghondi Manganese Mine");
const finalVal = Visual3D.getValidation();

console.log(JSON.stringify(finalVal, null, 2));

console.log("\n================================================================");
console.log(`TEST RESULTS: ${passedTests} / ${totalTests} tests passed (${Math.round(passedTests / totalTests * 100)}%)`);
console.log("================================================================\n");

if (passedTests === totalTests) {
    process.exit(0);
} else {
    process.exit(1);
}
