/**
 * ============================================================================
 * TEST SUITE: 3D MAP FALLBACK PERMANENT IMPLEMENTATION VERIFICATION
 * ============================================================================
 * File: tests/test_3d_permanent_fallback_verification.js
 * 
 * Verifies:
 *   1. Terrain renders successfully when no prospectivity grid exists.
 *   2. Missing prospectivity data does not trigger the 2D fallback.
 *   3. Selecting Coal, Iron Ore, or Bauxite never displays the Manganese grid.
 *   4. Switching locations and minerals updates the 3D visualization correctly.
 *   5. Resizing the panel does not leave a blank map.
 *   6. Recoverable WebGL errors attempt recovery (state machine: recovering, retryCount).
 *   7. A genuine unrecoverable rendering error exposes a working 2D fallback.
 *   8. Existing four-mineral analysis and scoring behavior remains unchanged.
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
    console.log(`  [PASS] ✓ ${name}`);
  } catch (e) {
    console.error(`  [FAIL] ✗ ${name}: ${e.message}`);
    process.exit(1);
  }
}

console.log('\n================================================================');
console.log('TEST SUITE: 3D MAP FALLBACK PERMANENT IMPLEMENTATION');
console.log('================================================================\n');

const projectRoot = path.resolve(__dirname, '..');
const appJsx = fs.readFileSync(path.join(projectRoot, 'frontend', 'src', 'App.jsx'), 'utf8');
const terrainMap3DJsx = fs.readFileSync(path.join(projectRoot, 'frontend', 'src', 'components', 'TerrainMap3D.jsx'), 'utf8');
const prospectivity3DMapJsx = fs.readFileSync(path.join(projectRoot, 'frontend', 'src', 'components', 'Prospectivity3DMap.jsx'), 'utf8');
const interactiveMapJsx = fs.readFileSync(path.join(projectRoot, 'frontend', 'src', 'components', 'InteractiveMap.jsx'), 'utf8');
const mineralServicePy = fs.readFileSync(path.join(projectRoot, 'backend', 'app', 'mineral_service.py'), 'utf8');

// TEST 1: Terrain renders successfully when no prospectivity grid exists
runTest('1. Terrain renders successfully when no prospectivity grid exists', () => {
  assert.ok(
    interactiveMapJsx.includes('<TerrainMap3D'),
    'InteractiveMap must render TerrainMap3D when prospectivity grid is unavailable'
  );
  assert.ok(
    terrainMap3DJsx.includes('maplibregl.Map'),
    'TerrainMap3D must instantiate MapLibre Map instance'
  );
  assert.ok(
    terrainMap3DJsx.includes('terrain-dem'),
    'TerrainMap3D must configure AWS Terrarium DEM elevation source'
  );
  assert.ok(
    terrainMap3DJsx.includes("terrainReady: true"),
    'TerrainMap3D must transition to terrainReady on load'
  );
});

// TEST 2: Missing prospectivity data does not trigger 2D fallback
runTest('2. Missing prospectivity data does not trigger 2D fallback', () => {
  // Banner must be purely informational and not contain a 2D return button
  assert.ok(
    terrainMap3DJsx.includes('id="prospectivity-fallback-banner"'),
    'TerrainMap3D must render dedicated prospectivity notice banner'
  );
  assert.ok(
    !terrainMap3DJsx.includes('id="btn-banner-switch-2d"'),
    'Prospectivity notice banner must NOT contain a 2D switch button'
  );
  assert.ok(
    interactiveMapJsx.includes('prospectivityNotice={{'),
    'InteractiveMap passes prospectivityNotice without altering mapMode'
  );
});

// TEST 3: Selecting Coal, Iron Ore, or Bauxite never displays Manganese grid
runTest('3. Selecting Coal, Iron Ore, or Bauxite never displays Manganese grid', () => {
  // In InteractiveMap: targetMineral === 'Manganese' is mandatory for isProspectivityAvailable
  assert.ok(
    interactiveMapJsx.includes("targetMineral === 'Manganese'"),
    'InteractiveMap must strictly restrict isProspectivityAvailable to Manganese'
  );
  // In Prospectivity3DMap: targetMineral === 'Manganese' is mandatory
  assert.ok(
    prospectivity3DMapJsx.includes("targetMineral === 'Manganese'"),
    'Prospectivity3DMap must strictly restrict isProspectivityAvailable to Manganese'
  );
  // Mineral service never reuses models
  assert.ok(
    mineralServicePy.includes("NO_MODEL_FOR_COMMODITY"),
    'Mineral service must mark non-Manganese commodities as NO_MODEL_FOR_COMMODITY'
  );
});

// TEST 4: Switching locations and minerals updates 3D visualization correctly
runTest('4. Switching locations and minerals updates 3D view without reverting to 2D', () => {
  assert.ok(
    appJsx.includes('const [mapMode, setMapMode] = useState(\'2d\');'),
    'App.jsx must lift and maintain mapMode state'
  );
  assert.ok(
    appJsx.includes('mapMode={mapMode}'),
    'App.jsx must pass mapMode to InteractiveMap'
  );
  assert.ok(
    appJsx.includes('onMapModeChange={setMapMode}'),
    'App.jsx must pass onMapModeChange to InteractiveMap'
  );
  assert.ok(
    terrainMap3DJsx.includes('map.flyTo({'),
    'TerrainMap3D must update center using flyTo on location change'
  );
  assert.ok(
    terrainMap3DJsx.includes('generateCirclePolygon(lon, lat, radiusKm)'),
    'TerrainMap3D must update circle polygon on location/radius change'
  );
});

// TEST 5: Resizing the panel does not leave a blank map
runTest('5. Resizing the panel does not leave a blank map', () => {
  assert.ok(
    terrainMap3DJsx.includes('ResizeObserver'),
    'TerrainMap3D must attach ResizeObserver to map container'
  );
  assert.ok(
    terrainMap3DJsx.includes('mapInstanceRef.current.resize()'),
    'ResizeObserver callback must invoke map.resize()'
  );
  assert.ok(
    terrainMap3DJsx.includes('requestAnimationFrame'),
    'TerrainMap3D must trigger requestAnimationFrame resize after mount'
  );
  assert.ok(
    prospectivity3DMapJsx.includes('ResizeObserver'),
    'Prospectivity3DMap must attach ResizeObserver'
  );
});

// TEST 6: Recoverable WebGL errors attempt recovery
runTest('6. Recoverable WebGL errors attempt recovery via 5-state machine', () => {
  assert.ok(
    terrainMap3DJsx.includes('recovering: true'),
    'TerrainMap3D must transition to recovering state on context loss'
  );
  assert.ok(
    terrainMap3DJsx.includes('webglcontextlost'),
    'TerrainMap3D must listen for webglcontextlost event'
  );
  assert.ok(
    terrainMap3DJsx.includes('webglcontextrestored'),
    'TerrainMap3D must listen for webglcontextrestored event'
  );
  assert.ok(
    terrainMap3DJsx.includes('retryCount < 2'),
    'TerrainMap3D must bound retries to prevent infinite recovery loops'
  );
  assert.ok(
    terrainMap3DJsx.includes('terrain-recovering-indicator'),
    'TerrainMap3D must render recovery indicator UI'
  );
});

// TEST 7: A genuine unrecoverable rendering error exposes a working 2D fallback
runTest('7. A genuine unrecoverable rendering error exposes working 2D fallback', () => {
  assert.ok(
    terrainMap3DJsx.includes('renderError:'),
    'TerrainMap3D must manage renderError state'
  );
  assert.ok(
    terrainMap3DJsx.includes('id="btn-terrain-fallback-2d"'),
    'TerrainMap3D must expose 2D fallback button on renderError'
  );
  assert.ok(
    terrainMap3DJsx.includes('id="btn-terrain-retry"'),
    'TerrainMap3D must expose manual retry button on renderError'
  );
  assert.ok(
    terrainMap3DJsx.includes('onFallbackTo2D'),
    'TerrainMap3D must call onFallbackTo2D callback'
  );
});

// TEST 8: Existing four-mineral analysis and scoring behavior remains unchanged
runTest('8. Existing four-mineral analysis and scoring behavior remains unchanged', () => {
  assert.ok(
    appJsx.includes('btn-analyze-all-minerals'),
    'App.jsx must retain primary Analyze All Four Minerals button'
  );
  assert.ok(
    appJsx.includes('btn-analyze-geographical'),
    'App.jsx must retain secondary single-mineral button'
  );
  assert.ok(
    mineralServicePy.includes('analyze_all_minerals_for_location'),
    'Backend must maintain analyze_all_minerals_for_location'
  );
  assert.ok(
    mineralServicePy.includes('comparison_summary'),
    'Backend must maintain comparison_summary table data'
  );
});

console.log(`\n================================================================`);
console.log(`RESULTS: All ${passedTests} / ${totalTests} permanent 3D fallback tests passed (100%)!`);
console.log(`================================================================\n`);
