/**
 * Frontend Unit & Structural Tests for Multi-Mineral Scorecards Dashboard
 *
 * Verifies:
 * 1. App.jsx primary action button clearly labelled "Analyze All Four Minerals" (#btn-analyze-all-minerals).
 * 2. App.jsx keeps existing single-mineral analysis available as an optional mode (#btn-analyze-geographical).
 * 3. ResultsPanel imports and renders MultiMineralScorecards with comparison table and 4 cards.
 * 4. Comparison table contains all 6 mandated columns:
 *    Mineral | AI Prediction Status | AI Score | Evidence Index | Evidence Quality | Main Explanation
 * 5. Scorecard components display:
 *    - Mineral name
 *    - AI prediction score (only if valid model available & eligible)
 *    - Evidence favorability index (only if sufficient evidence exists with documented formula)
 *    - Evidence quality (separated from favorability)
 *    - Geographic model eligibility
 *    - Main supporting evidence
 *    - Missing data and limitations
 *    - Clear result status
 * 6. Explicit 0-100 scale explanation without implying direct comparability between different score types.
 * 7. 3D Prospectivity / Terrain fallback logic.
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
    console.error(`  ✗ ${name}`);
    console.error(err);
    process.exit(1);
  }
}

console.log('\n--- Multi-Mineral Scorecards Frontend Tests ---');

const appJsxPath = path.join(__dirname, '../frontend/src/App.jsx');
const resultsPanelJsxPath = path.join(__dirname, '../frontend/src/components/ResultsPanel.jsx');
const multiScorecardsJsxPath = path.join(__dirname, '../frontend/src/components/MultiMineralScorecards.jsx');
const interactiveMapJsxPath = path.join(__dirname, '../frontend/src/components/InteractiveMap.jsx');
const terrainMapJsxPath = path.join(__dirname, '../frontend/src/components/TerrainMap3D.jsx');

const appJsx = fs.readFileSync(appJsxPath, 'utf8');
const resultsPanelJsx = fs.readFileSync(resultsPanelJsxPath, 'utf8');
const multiScorecardsJsx = fs.readFileSync(multiScorecardsJsxPath, 'utf8');
const interactiveMapJsx = fs.readFileSync(interactiveMapJsxPath, 'utf8');
const terrainMapJsx = fs.readFileSync(terrainMapJsxPath, 'utf8');

// Test 1: App.jsx primary action is clearly labelled "Analyze All Four Minerals"
test('App.jsx primary action button is clearly labelled "Analyze All Four Minerals"', () => {
  assert.ok(
    appJsx.includes('Analyze All Four Minerals'),
    'App.jsx must contain "Analyze All Four Minerals" button text'
  );
  assert.ok(
    appJsx.includes('id="btn-analyze-all-minerals"'),
    'App.jsx must provide #btn-analyze-all-minerals element'
  );
  assert.ok(
    appJsx.includes("handleRunAnalysis('all')"),
    'Primary button must trigger handleRunAnalysis with mode "all"'
  );
});

// Test 2: App.jsx maintains single-mineral analysis as optional mode
test('App.jsx maintains single-mineral analysis as optional mode', () => {
  assert.ok(
    appJsx.includes('Analyze {selectedMineral} Only (Single Mode)') ||
    appJsx.includes('Analyze {selectedMineral} Only'),
    'App.jsx must provide optional single-mineral analysis mode'
  );
  assert.ok(
    appJsx.includes("handleRunAnalysis('single')"),
    'Secondary button must trigger handleRunAnalysis with mode "single"'
  );
});

// Test 3: App.jsx handles multiResult and cleans up loading state
test('App.jsx manages multiResult state, timeout, and loading-state cleanup', () => {
  assert.ok(
    appJsx.includes('const [multiResult, setMultiResult] = useState(null);'),
    'App.jsx must declare multiResult state'
  );
  assert.ok(
    appJsx.includes('/analyze-all'),
    'App.jsx must call /analyze-all endpoint for multi-mineral analysis'
  );
  assert.ok(
    appJsx.includes('clearTimeout(timeoutId);'),
    'App.jsx must clear timeout timer on success and failure'
  );
  assert.ok(
    appJsx.includes('setIsAnalyzing(false);'),
    'App.jsx must reset isAnalyzing in finally block'
  );
});

// Test 4: ResultsPanel integrates MultiMineralScorecards with view toggle
test('ResultsPanel integrates MultiMineralScorecards with view toggle', () => {
  assert.ok(
    resultsPanelJsx.includes("import MultiMineralScorecards from './MultiMineralScorecards';"),
    'ResultsPanel.jsx must import MultiMineralScorecards'
  );
  assert.ok(
    resultsPanelJsx.includes('<MultiMineralScorecards'),
    'ResultsPanel.jsx must render MultiMineralScorecards component'
  );
  assert.ok(
    resultsPanelJsx.includes('Unified 4-Mineral Comparison'),
    'ResultsPanel.jsx must provide Unified 4-Mineral Comparison view mode'
  );
  assert.ok(
    resultsPanelJsx.includes('Deep {mineral} Dossier') || resultsPanelJsx.includes('Deep {selectedMineral} Dossier'),
    'ResultsPanel.jsx must allow drilling down to Deep Dossier'
  );
});

// Test 5: MultiMineralScorecards renders comparison summary table with all 6 columns
test('MultiMineralScorecards renders comparison summary table with 6 columns', () => {
  const mandatedHeaders = [
    'Mineral',
    'AI Prediction Status',
    'AI Score',
    'Evidence Index',
    'Evidence Quality',
    'Main Explanation'
  ];
  mandatedHeaders.forEach(header => {
    assert.ok(
      multiScorecardsJsx.includes(header),
      `MultiMineralScorecards must include table header: ${header}`
    );
  });
});

// Test 6: MultiMineralScorecards renders four distinct mineral cards
test('MultiMineralScorecards iterates over all four commodities', () => {
  const minerals = ['Coal', 'Manganese', 'Iron Ore', 'Bauxite'];
  minerals.forEach(m => {
    assert.ok(
      multiScorecardsJsx.includes(m),
      `MultiMineralScorecards must reference commodity: ${m}`
    );
  });
  assert.ok(
    multiScorecardsJsx.includes("['Coal', 'Manganese', 'Iron Ore', 'Bauxite'].map"),
    'MultiMineralScorecards must map through all four commodities'
  );
});

// Test 7: Scorecard requirement - AI score, Evidence Favorability Index, Quality separated
test('Scorecards distinctly separate AI Prediction Score from Evidence Favorability Index', () => {
  assert.ok(
    multiScorecardsJsx.includes('AI Prediction Score') || multiScorecardsJsx.includes('AI Prospectivity Score'),
    'Scorecards must present AI Prediction Score with eligibility check'
  );
  assert.ok(
    multiScorecardsJsx.includes('Evidence Favorability Index'),
    'Scorecards must present Evidence Favorability Index'
  );
  assert.ok(
    multiScorecardsJsx.includes('Evidence Quality'),
    'Scorecards must separate Evidence Quality from Favorability'
  );
  assert.ok(
    multiScorecardsJsx.includes('Geographic Model Eligibility'),
    'Scorecards must state Geographic Model Eligibility'
  );
});

// Test 8: Scorecard requirement - Expandable section for why result was produced
test('Scorecards allow users to expand to inspect why result was produced', () => {
  assert.ok(
    multiScorecardsJsx.includes('expandedMineral === mName'),
    'MultiMineralScorecards must manage expanded state per mineral'
  );
  assert.ok(
    multiScorecardsJsx.includes('toggleExpand'),
    'MultiMineralScorecards must have toggleExpand handler'
  );
  assert.ok(
    multiScorecardsJsx.includes('Main Supporting Evidence'),
    'Scorecards must show supporting evidence in scorecard view'
  );
  assert.ok(
    multiScorecardsJsx.includes('Missing Data & Boundaries') || multiScorecardsJsx.includes('Missing Data & Limitations'),
    'Scorecards must show missing data and limitations in scorecard view'
  );
});

// Test 9: Score scale disclaimer explicitly explains meaning and prevents false equivalence
test('Score scale disclaimer explains meaning without mixing incomparable types', () => {
  assert.ok(
    multiScorecardsJsx.includes('Scientific Interpretation Guidelines: 0–100 Normalized Scale Meaning'),
    'Dashboard must display scientific scale explanation callout'
  );
  assert.ok(
    multiScorecardsJsx.includes('AI Prediction Score (0–100): Valid ONLY for Manganese'),
    'Must explain AI prediction score is valid only for Manganese'
  );
  assert.ok(
    multiScorecardsJsx.includes('Evidence Favorability Index (0–100): Calculated from multi-criteria'),
    'Must document the evidence favorability index methodology'
  );
  assert.ok(
    multiScorecardsJsx.includes('Direct numerical comparison between an AI Prediction and an Evidence Favorability Index is scientifically invalid'),
    'Must warn against comparing disparate score types'
  );
});

// Test 10: 3D Visualization safeguards prevent cross-mineral grid display
test('3D Visualization safeguards prevent cross-mineral grid display', () => {
  assert.ok(
    interactiveMapJsx.includes('isProspectivityAvailable'),
    'InteractiveMap must verify prospectivity mesh availability'
  );
  assert.ok(
    interactiveMapJsx.includes("targetMineral !== 'Manganese'"),
    'InteractiveMap must check mineral match before rendering prospectivity mesh'
  );
  assert.ok(
    interactiveMapJsx.includes('No validated spatial machine-learning model exists for ${targetMineral}'),
    'InteractiveMap must show explicit fallback banner explaining why 3D terrain is displayed'
  );
  assert.ok(
    terrainMapJsx.includes('WebGL') || terrainMapJsx.includes('Switch to 2D Cartography'),
    'TerrainMap3D must provide WebGL resilience and 2D fallback'
  );
});

console.log(`\nAll ${passedTests} Multi-Mineral Scorecards frontend tests passed successfully!\n`);
