const fs = require('fs');
const path = require('path');
const assert = require('assert');

console.log('================================================================');
console.log('TEST SUITE: USER-DRIVEN TARGET SELECTION VALIDATION');
console.log('================================================================\n');

// 1. Inspect index.html for neutral/unselected startup state
const htmlContent = fs.readFileSync(path.join(__dirname, '..', 'index.html'), 'utf8');

// Check location presets dropdown default
assert(htmlContent.includes('<option value="" disabled selected>— Select Target Preset —</option>'),
    'index.html: location-select must have disabled unselected default option');

// Check target coordinate inputs have empty default value and placeholders
assert(htmlContent.includes('id="target-lat-input" value="" placeholder="e.g. 21.9455"'),
    'index.html: target-lat-input must have value="" and placeholder');
assert(htmlContent.includes('id="target-lon-input" value="" placeholder="e.g. 80.4295"'),
    'index.html: target-lon-input must have value="" and placeholder');
assert(htmlContent.includes('id="map-lat-input" value="" placeholder="e.g. 21.9455"'),
    'index.html: map-lat-input must have value="" and placeholder');
assert(htmlContent.includes('id="map-lon-input" value="" placeholder="e.g. 80.4295"'),
    'index.html: map-lon-input must have value="" and placeholder');

// Check target status badge & pill have neutral initial text
assert(htmlContent.includes('id="target-source-badge"') && htmlContent.includes('>No Target</span>'),
    'index.html: target-source-badge must start as "No Target"');
assert(htmlContent.includes('id="target-tile-status"') && htmlContent.includes('>Click map or choose preset</span>'),
    'index.html: target-tile-status must start as "Click map or choose preset"');

// Check map live prospectivity card starts awaiting target
assert(htmlContent.includes('id="map-score-number"') && htmlContent.includes('>—</span>'),
    'index.html: map-score-number must start with "—"');
assert(htmlContent.includes('id="map-classification-tag"') && htmlContent.includes('>Awaiting Target</span>'),
    'index.html: map-classification-tag must start as "Awaiting Target"');

// Check map coordinate readout prompt
assert(htmlContent.includes('id="map-coordinates"') && htmlContent.includes('Click anywhere on map to select exploration target'),
    'index.html: map-coordinates must guide user to click anywhere on map');

// Check Ghondi is still present as an available preset option
assert(htmlContent.includes('value="ghondi" data-lat="21.9455" data-lon="80.4295"'),
    'index.html: Ghondi preset must remain available in dropdown options');

console.log('[PASS] Test 1: index.html defaults are neutral with no active target pre-selected.');

// 2. Inspect js/map.js for startup and target logic
const mapJsContent = fs.readFileSync(path.join(__dirname, '..', 'js', 'map.js'), 'utf8');

// Ensure map.js has hasTarget in state
assert(mapJsContent.includes('hasTarget: false'), 'js/map.js: state must initialize with hasTarget: false');

// Ensure map.js centers sensibly over tile footprint without placing marker on startup
assert(mapJsContent.includes('const initialCenter = (state.hasTarget && state.lat && state.lon)'),
    'js/map.js: map center must check state.hasTarget');
assert(mapJsContent.includes('if (state.hasTarget && state.lat && state.lon) {'),
    'js/map.js: marker & buffer circle creation must be gated on state.hasTarget');
assert(mapJsContent.includes('resetLiveProspectivityCard();'),
    'js/map.js: resetLiveProspectivityCard must be called when no target on init');

// Ensure updating location sets hasTarget to true
assert(mapJsContent.includes('state.hasTarget = true;'),
    'js/map.js: updateSelectedLocation must set state.hasTarget = true');

// Ensure public API exposes hasTarget and getTargetCoordinates
assert(mapJsContent.includes('hasTarget: () => !!state.hasTarget'),
    'js/map.js: publicApi must expose hasTarget()');
assert(mapJsContent.includes('getTargetCoordinates: () => (state.hasTarget ? { lat: state.lat, lon: state.lon } : null)'),
    'js/map.js: publicApi must expose getTargetCoordinates() returning null when no target');

console.log('[PASS] Test 2: js/map.js state lifecycle correctly handles unselected startup and target activation.');

// 3. Inspect app.js for target-driven execution
const appJsContent = fs.readFileSync(path.join(__dirname, '..', 'app.js'), 'utf8');

// Ensure no startup call to updateSpectralFingerprint(21.9455, 80.4295, 25)
const startupSpectralMatches = appJsContent.match(/updateSpectralFingerprint\(21\.9455,\s*80\.4295,\s*25\);/g);
assert(!startupSpectralMatches, 'app.js: hardcoded startup call to updateSpectralFingerprint must NOT exist');

// Ensure onLocationChange ignores when !info.hasTarget
assert(appJsContent.includes('if (!info || !info.hasTarget) {'),
    'app.js: onLocationChange must guard against unselected target');

// Ensure executeProspectivityAnalysis is called when user selects a target
assert(appJsContent.includes('executeProspectivityAnalysis(info.lat, info.lon, info.locationName, info.radiusKm);'),
    'app.js: executeProspectivityAnalysis must be triggered on user target selection');

// Ensure executeProspectivityAnalysis updates XAI, Spectral Fingerprint, and Production Risk
assert(appJsContent.includes('updateWhyExplanation(result.score, locName, result.classification, true);'),
    'app.js: executeProspectivityAnalysis must update XAI waterfall');
assert(appJsContent.includes('updateSpectralFingerprint(lat, lon, radiusKm);'),
    'app.js: executeProspectivityAnalysis must update Spectral Fingerprint');
assert(appJsContent.includes('ProductionEngine.predictProduction(inputs);'),
    'app.js: executeProspectivityAnalysis must update Production Risk analysis');

// Ensure btnRun warns if user clicks without target
assert(appJsContent.includes('Select Target First'),
    'app.js: btnRun and btnExport must guard against execution without a selected target');

console.log('[PASS] Test 3: app.js cascades analysis and panel updates strictly on user-driven selection.');

console.log('\n================================================================');
console.log('ALL USER-DRIVEN TARGET SELECTION VALIDATION TESTS PASSED (100%)');
console.log('================================================================');
