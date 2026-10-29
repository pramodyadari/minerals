/**
 * Tests for Custom 2/3 Mineral Selection & 3D WebGL Robustness (Part B & Part C)
 *
 * Verifies:
 * 1. MineralSelector provides Analysis Mode Selector with "Analyze All Four" and "Choose Minerals" modes
 * 2. MineralSelector displays selected minerals count and bounds (exactly 2 or 3 in custom mode)
 * 3. MineralSelector provides "Select All Four" shortcut control
 * 4. MineralSelector provides "Clear Selection" control
 * 5. App.jsx dynamic primary action button label ("Analyze All Four Minerals", "Analyze Selected 2 Minerals", "Analyze Selected 3 Minerals")
 * 6. App.jsx disables analyze action if fewer than 2 or more than 3 minerals are selected in custom mode
 * 7. MultiMineralScorecards renders dynamic scorecards and comparison table for requested minerals only
 * 8. MapLibre GL WebGL lifecycle cleanup and context loss protection in TerrainMap3D.jsx
 */

const assert = require('assert');
const fs = require('fs');
const path = require('path');

let passedTests = 0;
function test(name, fn) {
  try {
    fn();
    console.log(`  [PASS] ✓ ${name}`);
    passedTests++;
  } catch (err) {
    console.error(`  [FAIL] ✗ ${name}`);
    console.error(err);
    process.exit(1);
  }
}

console.log('\n--- Custom 2/3 Mineral Selection & 3D WebGL Tests ---');

const projectRoot = path.resolve(__dirname, '..');
const appJsx = fs.readFileSync(path.join(projectRoot, 'frontend', 'src', 'App.jsx'), 'utf8');
const mineralSelectorJsx = fs.readFileSync(path.join(projectRoot, 'frontend', 'src', 'components', 'MineralSelector.jsx'), 'utf8');
const multiScorecardsJsx = fs.readFileSync(path.join(projectRoot, 'frontend', 'src', 'components', 'MultiMineralScorecards.jsx'), 'utf8');
const terrainMap3DJsx = fs.readFileSync(path.join(projectRoot, 'frontend', 'src', 'components', 'TerrainMap3D.jsx'), 'utf8');

// Test 1: MineralSelector provides mode selector with both modes
test('MineralSelector provides analysis mode selector with Analyze All Four and Choose Minerals', () => {
  assert.ok(
    mineralSelectorJsx.includes('btn-mode-analyze-all-four'),
    'MineralSelector must include #btn-mode-analyze-all-four button'
  );
  assert.ok(
    mineralSelectorJsx.includes('btn-mode-choose-minerals'),
    'MineralSelector must include #btn-mode-choose-minerals button'
  );
  assert.ok(
    mineralSelectorJsx.includes('Analyze All Four') && mineralSelectorJsx.includes('Choose Minerals'),
    'MineralSelector must display mode labels'
  );
});

// Test 2: MineralSelector shows count and enforces 2 or 3 selection bounds
test('MineralSelector shows selected count and enforces exactly 2 or 3 selection bounds', () => {
  assert.ok(
    mineralSelectorJsx.includes('customCount') || mineralSelectorJsx.includes('customMinerals.length'),
    'MineralSelector must track selected custom count'
  );
  assert.ok(
    mineralSelectorJsx.includes('customMinerals.length >= 3'),
    'MineralSelector must prevent selecting more than 3 minerals in custom mode'
  );
  assert.ok(
    mineralSelectorJsx.includes('Need 2 or 3') || mineralSelectorJsx.includes('choose 2 or 3'),
    'MineralSelector must indicate valid selection range (2 or 3)'
  );
});

// Test 3: MineralSelector provides Select All Four and Clear Selection controls
test('MineralSelector provides Select All Four and Clear Selection controls', () => {
  assert.ok(
    mineralSelectorJsx.includes('btn-select-all-four-shortcut'),
    'MineralSelector must include #btn-select-all-four-shortcut control'
  );
  assert.ok(
    mineralSelectorJsx.includes('btn-clear-minerals-selection'),
    'MineralSelector must include #btn-clear-minerals-selection control'
  );
  assert.ok(
    mineralSelectorJsx.includes('handleSelectAllFour'),
    'MineralSelector must provide handleSelectAllFour handler'
  );
  assert.ok(
    mineralSelectorJsx.includes('handleClearSelection'),
    'MineralSelector must provide handleClearSelection handler'
  );
});

// Test 4: App.jsx primary action button label is dynamic
test('App.jsx primary action button provides dynamic labels for All Four, 2, and 3 minerals', () => {
  assert.ok(
    appJsx.includes('Analyze All Four Minerals'),
    'App.jsx must support "Analyze All Four Minerals" label'
  );
  assert.ok(
    appJsx.includes('Analyze Selected 2 Minerals'),
    'App.jsx must support "Analyze Selected 2 Minerals" label'
  );
  assert.ok(
    appJsx.includes('Analyze Selected 3 Minerals'),
    'App.jsx must support "Analyze Selected 3 Minerals" label'
  );
});

// Test 5: App.jsx disables submission when fewer than 2 or more than 3 minerals are selected in custom mode
test('App.jsx disables submission when fewer than 2 or more than 3 minerals selected in custom mode', () => {
  assert.ok(
    appJsx.includes('customMinerals.length < 2 || customMinerals.length > 3'),
    'App.jsx must validate custom selection length (2 or 3)'
  );
  assert.ok(
    appJsx.includes('isCustomModeInvalid'),
    'App.jsx must compute isCustomModeInvalid'
  );
  assert.ok(
    appJsx.includes('isAnalyzeDisabled'),
    'App.jsx must disable analyze button when custom selection is invalid'
  );
});

// Test 6: MultiMineralScorecards dynamically renders requested minerals
test('MultiMineralScorecards dynamically renders cards and comparison table for requested minerals', () => {
  assert.ok(
    multiScorecardsJsx.includes('selected_minerals'),
    'MultiMineralScorecards must read selected_minerals from result'
  );
  assert.ok(
    multiScorecardsJsx.includes('Selected ${mineralCount}-Mineral') || multiScorecardsJsx.includes('Selected ${count}-Mineral'),
    'MultiMineralScorecards must render dynamic header title'
  );
  assert.ok(
    multiScorecardsJsx.includes('comparison_summary'),
    'MultiMineralScorecards must render dynamic comparison_summary table'
  );
});

// Test 7: TerrainMap3D WebGL lifecycle cleanup and worker resolution
test('TerrainMap3D uses Vite worker URL and protects against false context-loss during unmount', () => {
  assert.ok(
    terrainMap3DJsx.includes('maplibreWorkerUrl'),
    'TerrainMap3D must import resolved worker URL from Vite'
  );
  assert.ok(
    terrainMap3DJsx.includes('setWorkerUrl'),
    'TerrainMap3D must register worker URL with MapLibre'
  );
  assert.ok(
    terrainMap3DJsx.includes('isDestroyingRef'),
    'TerrainMap3D must track isDestroyingRef to prevent unmount context loss loop'
  );
  assert.ok(
    terrainMap3DJsx.includes('removeEventListener'),
    'TerrainMap3D must clean up webglcontextlost listeners on unmount'
  );
});

console.log(`\nAll ${passedTests} Custom 2/3 Mineral Selection & 3D WebGL tests passed!`);
