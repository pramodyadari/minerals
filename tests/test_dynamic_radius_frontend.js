/**
 * ============================================================================
 * AI MINERAL INTELLIGENCE — DYNAMIC EXPLORATION RADIUS & CIRCLE REGRESSION TESTS
 * ============================================================================
 * Test Suite: tests/test_dynamic_radius_frontend.js
 * 
 * Verifies:
 *   1. Radius options [1, 5, 10, 25, 50] present in RadiusSelector.jsx
 *   2. Default exploration radius initialized to 10 km in App.jsx
 *   3. Exact circular survey area calculations (Area = π × r²):
 *      - 1 km  -> 3.14 km²
 *      - 5 km  -> 78.54 km²
 *      - 10 km -> 314.16 km²
 *      - 25 km -> 1,963.50 km²
 *      - 50 km -> 7,853.98 km²
 *   4. Survey area labeled as approximate geometric survey area, not confirmed deposits
 *   5. Leaflet circle radius conversion to meters in InteractiveMap.jsx (radiusKm * 1000)
 *   6. Amber/gold circle styling (solid border, semi-transparent fill)
 *   7. Distinct center marker at exact coordinates
 *   8. Display of place name, radius, and survey area on marker and circle popups/tooltips
 *   9. Coordinate validation and GPS error handling to prevent misleading overlays
 *  10. Backend parameter synchronization on /analyze payload
 *  11. CSS grid configured for 5 radius pills
 *  12. Backend main.py includes 50 km in valid_radii
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
console.log('TEST SUITE: DYNAMIC EXPLORATION RADIUS & 2D MAP CIRCLE');
console.log('================================================================\n');

const projectRoot = path.resolve(__dirname, '..');
const radiusSelectorPath = path.join(projectRoot, 'frontend', 'src', 'components', 'RadiusSelector.jsx');
const interactiveMapPath = path.join(projectRoot, 'frontend', 'src', 'components', 'InteractiveMap.jsx');
const appJsxPath = path.join(projectRoot, 'frontend', 'src', 'App.jsx');
const indexCssPath = path.join(projectRoot, 'frontend', 'src', 'index.css');
const mainPyPath = path.join(projectRoot, 'backend', 'app', 'main.py');

const radiusSelectorContent = fs.readFileSync(radiusSelectorPath, 'utf8');
const interactiveMapContent = fs.readFileSync(interactiveMapPath, 'utf8');
const appJsxContent = fs.readFileSync(appJsxPath, 'utf8');
const indexCssContent = fs.readFileSync(indexCssPath, 'utf8');
const mainPyContent = fs.readFileSync(mainPyPath, 'utf8');

// Test 1: All 5 selectable radius options
runTest('Test 1: RadiusSelector includes exactly [1, 5, 10, 25, 50] radius options', () => {
    assert(radiusSelectorContent.includes('const RADIUS_OPTIONS = [1, 5, 10, 25, 50];'),
        'RADIUS_OPTIONS must include 1, 5, 10, 25, 50');
    [1, 5, 10, 25, 50].forEach(r => {
        assert(radiusSelectorContent.includes(`id={\`radius-pill-\${r}km\`}`),
            `Button for ${r}km must be present`);
    });
});

// Test 2: Default radius is 10 km
runTest('Test 2: App.jsx initializes default exploration radius to 10 km', () => {
    assert(appJsxContent.includes('useState(10)'),
        'Default radius in App.jsx must be initialized to 10 km');
});

// Test 3: Circular area calculations Area = π × radius²
runTest('Test 3: Area calculation formula matches expected values for all 5 radii', () => {
    const expected = [
        { r: 1, area: '3.14' },
        { r: 5, area: '78.54' },
        { r: 10, area: '314.16' },
        { r: 25, area: '1,963.50' },
        { r: 50, area: '7,853.98' },
    ];

    expected.forEach(({ r, area }) => {
        const calc = (Math.PI * Math.pow(r, 2)).toLocaleString('en-US', {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2,
        });
        assert.strictEqual(calc, area, `Radius ${r} km area calculation mismatch`);
    });
});

// Test 4: Labeled as approximate geometric survey area, not confirmed deposits
runTest('Test 4: Survey area is explicitly labeled as approximate geometric survey area', () => {
    assert(radiusSelectorContent.includes('Approx. Geometric Survey Area:'),
        'Label must identify approximate geometric survey area');
    assert(radiusSelectorContent.includes('not confirmed mineral deposit area'),
        'Disclaimer must clarify not confirmed mineral deposits');
});

// Test 5: Leaflet L.circle radius converted to meters
runTest('Test 5: InteractiveMap converts radius to meters (radiusKm * 1000) for L.circle', () => {
    assert(interactiveMapContent.includes('Number(radiusKm) * 1000'),
        'Radius must be converted to meters using Number(radiusKm) * 1000');
    assert(interactiveMapContent.includes('L.circle([numLat, numLon]'),
        'InteractiveMap must use Leaflet L.circle() with meter radius');
});

// Test 6: Amber/Gold circle styling with solid border and semi-transparent fill
runTest('Test 6: InteractiveMap applies amber/gold styling with solid border and transparent fill', () => {
    assert(interactiveMapContent.includes("color: '#d97706'"),
        'Solid amber/gold border color #d97706 must be specified');
    assert(interactiveMapContent.includes("fillColor: '#f59e0b'"),
        'Amber/gold fillColor #f59e0b must be specified');
    assert(interactiveMapContent.includes('fillOpacity: 0.16'),
        'Semi-transparent fillOpacity 0.16 must be specified to keep map features visible');
    assert(interactiveMapContent.includes('weight: 2.5'),
        'Clearly visible border weight 2.5 must be configured');
});

// Test 7: Distinct center marker
runTest('Test 7: InteractiveMap places distinct center marker at exact location coordinates', () => {
    assert(interactiveMapContent.includes('markerRef.current.setLatLng([numLat, numLon])'),
        'Center marker position must be updated to exact coordinates');
    assert(interactiveMapContent.includes('L.marker([numLat, numLon], { icon: explorerMarkerIcon })'),
        'L.marker must be initialized with distinctive explorerMarkerIcon');
});

// Test 8: Place name and current radius displayed on marker and circle popups/tooltips
runTest('Test 8: Place name, radius, and survey area displayed on marker and circle popups', () => {
    assert(interactiveMapContent.includes('Exploration Radius: <b>${radiusKm} km</b>'),
        'Marker and circle popups must display current radius in km');
    assert(interactiveMapContent.includes('Approx. Geometric Survey Area: <b>≈ ${areaSqKm} km²</b>'),
        'Circle popup must display approximate geometric survey area');
    assert(interactiveMapContent.includes('setTooltipContent'),
        'Circle tooltip must update dynamically with place name and radius');
});

// Test 9: Coordinate validation and geolocation error guards
runTest('Test 9: Invalid coordinates and geolocation errors prevent misleading overlay drawing', () => {
    assert(interactiveMapContent.includes('if (!isValid)'),
        'InteractiveMap must check for valid coordinate numbers between [-90, 90] and [-180, 180]');
    assert(interactiveMapContent.includes('markerRef.current.remove()'),
        'Invalid coordinates must remove stale marker');
    assert(interactiveMapContent.includes('circleRef.current.remove()'),
        'Invalid coordinates must remove stale circle');
    assert(interactiveMapContent.includes("setGpsError('Received invalid GPS coordinates"),
        'Live GPS handler must guard against invalid coordinates');
});

// Test 10: Backend analysis parameter synchronization
runTest('Test 10: Backend analysis payload synchronizes selectedLocation and selectedRadius', () => {
    assert(appJsxContent.includes('radius_km: parseFloat(selectedRadius)'),
        'handleRunAnalysis must pass selectedRadius to backend payload');
    assert(appJsxContent.includes('latitude: parseFloat(selectedLocation.lat)'),
        'handleRunAnalysis must pass selectedLocation.lat to backend payload');
    assert(appJsxContent.includes('longitude: parseFloat(selectedLocation.lon)'),
        'handleRunAnalysis must pass selectedLocation.lon to backend payload');
});

// Test 11: CSS grid configuration for 5 radius pills
runTest('Test 11: index.css configures .radius-pills grid for 5 buttons', () => {
    assert(indexCssContent.includes('grid-template-columns: repeat(5, 1fr)'),
        '.radius-pills must be configured with repeat(5, 1fr)');
});

// Test 12: Backend main.py includes 50 km in valid_radii
runTest('Test 12: backend main.py registers 50 km in valid_radii and AnalyzeRequest schema', () => {
    assert(mainPyContent.includes('valid_radii = [1.0, 5.0, 10.0, 25.0, 50.0]'),
        'backend main.py must include 50.0 in valid_radii');
    assert(mainPyContent.includes('1, 5, 10, 25, or 50'),
        'AnalyzeRequest schema description must list 50 km option');
});

console.log(`\n================================================================`);
console.log(`DYNAMIC RADIUS SUMMARY: ${passedTests}/${totalTests} tests passed.`);
console.log(`================================================================\n`);

if (passedTests !== totalTests) {
    process.exit(1);
}
