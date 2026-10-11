/**
 * ============================================================================
 * TEST SUITE: GEOSPATIAL ENGINE & DATA ASSETS (PHASE 1 & PHASE 2 VERIFICATION)
 * ============================================================================
 */

const GeoEngine = require('../js/geo');
const MineralData = require('../js/data');

console.log("================================================================");
console.log("TEST SUITE: AI MINERAL INTELLIGENCE GEOSPATIAL ENGINE (EPSG:32644)");
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
// TEST 1: Forward Transformation WGS84 -> UTM Zone 44N (Known Mine Ground-Truth)
// ----------------------------------------------------------------------------
console.log("--- 1. Testing WGS84 -> UTM Zone 44N Forward Projection ---");
const mineLat = 21.9455;
const mineLon = 80.4295;
const expectedMineX = 441089.328;
const expectedMineY = 2426904.204;

const utmMine = GeoEngine.wgs84ToUtm44N(mineLat, mineLon);
const diffX = Math.abs(utmMine.easting - expectedMineX);
const diffY = Math.abs(utmMine.northing - expectedMineY);

assert(
    diffX < 0.05 && diffY < 0.05,
    `Known Mine WGS84 (21.9455°, 80.4295°) -> UTM44N matches GDAL (${expectedMineX}, ${expectedMineY})`,
    `Computed: Easting=${utmMine.easting}, Northing=${utmMine.northing} | Diff X=${diffX.toFixed(4)}m, Y=${diffY.toFixed(4)}m`
);

// ----------------------------------------------------------------------------
// TEST 2: Inverse Transformation UTM Zone 44N -> WGS84
// ----------------------------------------------------------------------------
console.log("\n--- 2. Testing UTM Zone 44N -> WGS84 Inverse Projection ---");
const revMine = GeoEngine.utm44NToWgs84(expectedMineX, expectedMineY);
const diffLat = Math.abs(revMine.latitude - mineLat);
const diffLon = Math.abs(revMine.longitude - mineLon);

assert(
    diffLat < 0.00001 && diffLon < 0.00001,
    `UTM44N (${expectedMineX}, ${expectedMineY}) -> WGS84 matches original (21.9455°, 80.4295°)`,
    `Computed: Lat=${revMine.latitude}°, Lon=${revMine.longitude}° | Diff Lat=${diffLat.toFixed(7)}°, Lon=${diffLon.toFixed(7)}°`
);

// ----------------------------------------------------------------------------
// TEST 3: Round-Trip Transformation Consistency
// ----------------------------------------------------------------------------
console.log("\n--- 3. Testing Round-Trip Accuracy Across Multiple Coordinates ---");
const testPoints = [
    { name: "Ghondi Mine", lat: 21.9455, lon: 80.4295 },
    { name: "Zone 67684", lat: 22.214160, lon: 80.063632 },
    { name: "Zone 124766", lat: 21.939738, lon: 80.602479 },
    { name: "Tile NW Corner", lat: 22.6102, lon: 80.0343 },
    { name: "Tile SE Corner", lat: 21.6033, lon: 81.0963 }
];

testPoints.forEach(pt => {
    const fwd = GeoEngine.wgs84ToUtm44N(pt.lat, pt.lon);
    const rev = GeoEngine.utm44NToWgs84(fwd.easting, fwd.northing);
    const latError = Math.abs(rev.latitude - pt.lat);
    const lonError = Math.abs(rev.longitude - pt.lon);
    assert(
        latError < 0.000005 && lonError < 0.000005,
        `Round-trip sub-meter consistency for ${pt.name} (${pt.lat}°, ${pt.lon}°)`,
        `Lat Error: ${latError.toFixed(8)}°, Lon Error: ${lonError.toFixed(8)}°`
    );
});

// ----------------------------------------------------------------------------
// TEST 4: Sentinel-2 Raster Pixel Mapping (Row, Col)
// ----------------------------------------------------------------------------
console.log("\n--- 4. Testing Sentinel-2 Raster Transform (20m Pixel Grid) ---");
const expectedMineRow = 3655;
const expectedMineCol = 2056;

const pixelMine = GeoEngine.wgs84ToRasterPixel(mineLat, mineLon);
assert(
    pixelMine.row === expectedMineRow && pixelMine.col === expectedMineCol,
    `Known Mine WGS84 maps to Sentinel-2 Pixel (Row: ${expectedMineRow}, Col: ${expectedMineCol})`,
    `Computed Row=${pixelMine.row} (exact: ${pixelMine.exactRow}), Col=${pixelMine.col} (exact: ${pixelMine.exactCol})`
);

// Reverse pixel to UTM
const utmFromPixel = GeoEngine.rasterPixelToUtm(expectedMineRow, expectedMineCol, 'corner');
const pixelColToEasting = GeoEngine.RASTER_GRID.originX + expectedMineCol * 20.0;
const pixelRowToNorthing = GeoEngine.RASTER_GRID.originY - expectedMineRow * 20.0;
assert(
    utmFromPixel.easting === pixelColToEasting && utmFromPixel.northing === pixelRowToNorthing,
    `Raster pixel (${expectedMineRow}, ${expectedMineCol}) -> UTM matches raster transform math`,
    `Easting=${utmFromPixel.easting}, Northing=${utmFromPixel.northing}`
);

// ----------------------------------------------------------------------------
// TEST 5: Candidate Zones Verification
// ----------------------------------------------------------------------------
console.log("\n--- 5. Testing Candidate Zones Dataset (20 Zones) ---");
assert(
    MineralData.CANDIDATE_ZONES.length === 20,
    `All 20 candidate zones loaded from high_prospectivity_zones.csv`,
    `Loaded: ${MineralData.CANDIDATE_ZONES.length}`
);

const topZone = MineralData.CANDIDATE_ZONES[0];
assert(
    topZone.zoneId === 67684 && topZone.meanScore === 0.9758 && topZone.inBounds === true,
    `Top Zone 67684 matches ground truth (Mean Score: 0.9758, inBounds: true)`,
    `UTM: (${topZone.easting}, ${topZone.northing}), Pixel: (row: ${topZone.row}, col: ${topZone.col})`
);

// ----------------------------------------------------------------------------
// TEST 6: Haversine Geodesic Distance
// ----------------------------------------------------------------------------
console.log("\n--- 6. Testing Haversine Distance Helper ---");
const distToTopZone = GeoEngine.haversineDistanceKm(mineLat, mineLon, topZone.lat, topZone.lon);
assert(
    distToTopZone > 40 && distToTopZone < 60,
    `Haversine distance between Known Mine and Zone 67684 is reasonable (~${distToTopZone} km)`,
    `Computed Distance: ${distToTopZone} km`
);

// Distance to self should be 0
const distSelf = GeoEngine.haversineDistanceKm(mineLat, mineLon, mineLat, mineLon);
assert(distSelf === 0, `Distance from location to itself is exactly 0.0 km`);

// ----------------------------------------------------------------------------
// SUMMARY
// ----------------------------------------------------------------------------
console.log("\n================================================================");
console.log(`TEST RESULTS: ${passedTests} / ${totalTests} tests passed (${Math.round(passedTests / totalTests * 100)}%)`);
console.log("================================================================\n");

if (passedTests === totalTests) {
    process.exit(0);
} else {
    process.exit(1);
}
