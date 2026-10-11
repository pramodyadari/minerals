const fs = require('fs');
const path = require('path');
const assert = require('assert');

console.log('================================================================');
console.log('TEST SUITE: MAP & TARGET SEARCH UX VERIFICATION');
console.log('================================================================\n');

let passCount = 0;
let failCount = 0;

function runTest(name, fn) {
    try {
        fn();
        console.log(`[PASS] ${name}`);
        passCount++;
    } catch (err) {
        console.error(`[FAIL] ${name}: ${err.message}`);
        failCount++;
    }
}

// 1. Load modules
const LocationResolver = require('../js/locations');
const GeoEngine = require('../js/geo');
const MineralData = require('../js/data');
const ExplorationMap = require('../js/map');

// --- Test 1: Authoritative Geographic Database & Search ---
runTest('LocationResolver provides verified real places without hallucination', () => {
    assert.ok(LocationResolver);
    assert.strictEqual(typeof LocationResolver.searchLocations, 'function');
    assert.strictEqual(typeof LocationResolver.reverseGeocode, 'function');

    // Search for Ghondi
    const ghondiRes = LocationResolver.searchLocations('Ghondi');
    assert.ok(ghondiRes.length > 0);
    assert.strictEqual(ghondiRes[0].name, 'Ghondi, Madhya Pradesh');
    assert.strictEqual(ghondiRes[0].subArea, 'Balaghat District');
    assert.strictEqual(ghondiRes[0].lat, 21.9455);
    assert.strictEqual(ghondiRes[0].lon, 80.4295);

    // Search for Balaghat district
    const balaghatRes = LocationResolver.searchLocations('Balaghat');
    assert.ok(balaghatRes.length > 0);
    const hasBalaghat = balaghatRes.some(r => r.name.includes('Balaghat'));
    assert.ok(hasBalaghat);

    // Search for Candidate Discovery Zone
    const zoneRes = LocationResolver.searchLocations('Zone 67684');
    assert.ok(zoneRes.length > 0);
    assert.strictEqual(zoneRes[0].zoneId, 67684);
    assert.strictEqual(zoneRes[0].name, 'Zone 67684 — NW Cluster');
    assert.strictEqual(zoneRes[0].type, 'zone');
});

// --- Test 2: Accurate Reverse-Geocoding & Honest Fallbacks ---
runTest('Reverse-geocoding identifies places accurately without inventing names', () => {
    // Exact Ghondi mine coordinates
    const ghondiResolved = LocationResolver.reverseGeocode(21.9455, 80.4295);
    assert.strictEqual(ghondiResolved.placeName, 'Ghondi, Madhya Pradesh');
    assert.strictEqual(ghondiResolved.subArea, 'Balaghat District');
    assert.strictEqual(ghondiResolved.inTile, true);

    // Bharweli mine coordinates (21.8417, 80.2442)
    const bharweliResolved = LocationResolver.reverseGeocode(21.8417, 80.2442);
    assert.ok(bharweliResolved.placeName.includes('Bharweli'));

    // Candidate Zone 67684 (22.214160, 80.063632)
    const zoneResolved = LocationResolver.reverseGeocode(22.214160, 80.063632);
    assert.ok(zoneResolved.placeName.includes('Zone 67684'));
    assert.ok(zoneResolved.placeName.includes('NW Cluster'));
    assert.strictEqual(zoneResolved.isZone, true);

    // Unmapped exploration coordinate in tile (e.g. wilderness coordinate far from towns)
    const unmappedCoord = LocationResolver.reverseGeocode(22.40, 80.80);
    assert.ok(unmappedCoord.placeName.includes('Unnamed Exploration Area') || unmappedCoord.placeName.includes('of Bichhiya') || unmappedCoord.placeName.includes('of Baihar'));
    // Ensures no fake village names are fabricated
    assert.ok(!unmappedCoord.placeName.includes('FakeVillage') && !unmappedCoord.placeName.includes('Simulated'));
});

// --- Test 3: Cartographic Place Labels ---
runTest('LocationResolver provides cartographic place markers for Leaflet overlay', () => {
    const labels = LocationResolver.getMapPlaceLabels();
    assert.ok(Array.isArray(labels));
    assert.ok(labels.length >= 10);
    const names = labels.map(l => l.name);
    assert.ok(names.includes('Ghondi'));
    assert.ok(names.includes('Bharweli'));
    assert.ok(names.includes('Balaghat'));
    assert.ok(names.includes('Ukwa'));
});

// --- Test 4: ExplorationMap Neutral Startup & Lifecycle ---
runTest('ExplorationMap preserves neutral startup state (hasTarget === false)', () => {
    const state = ExplorationMap.getState();
    assert.strictEqual(state.hasTarget, false);
    assert.strictEqual(ExplorationMap.hasTarget(), false);
    assert.strictEqual(ExplorationMap.getTargetCoordinates(), null);
});

// --- Test 5: ExplorationMap User Target Activation & Place Resolution ---
runTest('Selecting target resolves place name, updates state and notifies listeners', () => {
    let notified = null;
    ExplorationMap.onLocationChange((payload) => {
        notified = payload;
    });

    // User clicks map at Ghondi coordinates
    ExplorationMap.setLocation(21.9455, 80.4295, 'Ghondi, Madhya Pradesh', 'map');

    assert.strictEqual(ExplorationMap.hasTarget(), true);
    const coords = ExplorationMap.getTargetCoordinates();
    assert.strictEqual(coords.lat, 21.9455);
    assert.strictEqual(coords.lon, 80.4295);

    const resolved = ExplorationMap.getResolvedPlace();
    assert.ok(resolved !== null);
    assert.strictEqual(resolved.placeName, 'Ghondi, Madhya Pradesh');
    assert.strictEqual(resolved.subArea, 'Balaghat District');

    assert.ok(notified !== null);
    assert.strictEqual(notified.hasTarget, true);
    assert.strictEqual(notified.lat, 21.9455);
    assert.strictEqual(notified.lon, 80.4295);
    assert.ok(notified.resolvedPlace !== null);
});

// --- Test 6: ExplorationMap Layer Toggles ---
runTest('ExplorationMap exposes layer overlay toggle controls', () => {
    assert.strictEqual(typeof ExplorationMap.togglePlaceLabels, 'function');
    assert.strictEqual(typeof ExplorationMap.toggleTileFootprint, 'function');
    assert.strictEqual(typeof ExplorationMap.toggleProspectivityOverlay, 'function');
    assert.strictEqual(typeof ExplorationMap.toggleCandidateZones, 'function');

    ExplorationMap.togglePlaceLabels(false);
    assert.strictEqual(ExplorationMap.getState().showLabels, false);
    ExplorationMap.togglePlaceLabels(true);
    assert.strictEqual(ExplorationMap.getState().showLabels, true);

    ExplorationMap.toggleTileFootprint(false);
    assert.strictEqual(ExplorationMap.getState().showTileFootprint, false);
    ExplorationMap.toggleTileFootprint(true);
    assert.strictEqual(ExplorationMap.getState().showTileFootprint, true);
});

// --- Test 7: DOM Structure & Controls in index.html ---
runTest('index.html contains all required UI elements for search and target place card', () => {
    const html = fs.readFileSync(path.join(__dirname, '..', 'index.html'), 'utf8');

    // Search boxes
    assert.ok(html.includes('id="location-search-input"'), 'Dashboard location search input exists');
    assert.ok(html.includes('id="location-suggestions-dropdown"'), 'Dashboard suggestions dropdown exists');
    assert.ok(html.includes('id="map-location-search-input"'), 'Map location search input exists');
    assert.ok(html.includes('id="map-location-suggestions-dropdown"'), 'Map suggestions dropdown exists');

    // Place name display cards
    assert.ok(html.includes('id="target-place-name"'), 'target-place-name exists');
    assert.ok(html.includes('id="target-place-subarea"'), 'target-place-subarea exists');
    assert.ok(html.includes('id="map-place-name"'), 'map-place-name exists');
    assert.ok(html.includes('id="map-place-subarea"'), 'map-place-subarea exists');

    // Layer checkboxes
    assert.ok(html.includes('id="toggle-place-labels"'), 'toggle-place-labels checkbox exists');
    assert.ok(html.includes('id="toggle-prospectivity-overlay"'), 'toggle-prospectivity-overlay exists');
    assert.ok(html.includes('id="toggle-tile-footprint"'), 'toggle-tile-footprint exists');
    assert.ok(html.includes('id="show-zones-toggle"'), 'show-zones-toggle exists');

    // Script tag
    assert.ok(html.includes('src="js/locations.js"'), 'locations.js script tag exists in index.html');
});

// --- Test 8: CSS Style Verification ---
runTest('styles.css contains styling for search autocomplete, target card, and target pin', () => {
    const css = fs.readFileSync(path.join(__dirname, '..', 'styles.css'), 'utf8');
    assert.ok(css.includes('.location-search-container'));
    assert.ok(css.includes('.suggestions-dropdown'));
    assert.ok(css.includes('.suggestion-item'));
    assert.ok(css.includes('.target-place-card'));
    assert.ok(css.includes('.selected-target-pin-wrap'));
    assert.ok(css.includes('.target-flag-tag'));
    assert.ok(css.includes('.map-place-tag'));
    assert.ok(css.includes('.layer-checkbox-label'));
});

console.log('\n================================================================');
console.log(`MAP & TARGET SEARCH UX RESULTS: ${passCount} / ${passCount + failCount} passed (${Math.round((passCount / (passCount + failCount)) * 100)}%)`);
console.log('================================================================\n');

if (failCount > 0) process.exit(1);
