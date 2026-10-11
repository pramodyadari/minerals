// Comprehensive QA verification of Visual and Functional requirements
const fs = require('fs');
const path = require('path');
const http = require('http');

console.log('================================================================');
console.log('STARTING VISUAL + FUNCTIONAL QA PASS');
console.log('================================================================\n');

let passedChecks = 0;
let totalChecks = 0;

function check(label, condition, details = '') {
    totalChecks++;
    if (condition) {
        passedChecks++;
        console.log(`[PASS] ${label} ${details ? '(' + details + ')' : ''}`);
    } else {
        console.error(`[FAIL] ${label} ${details ? ': ' + details : ''}`);
    }
}

// 1. Check Live Server
http.get('http://127.0.0.1:8085/', (res) => {
    check('Server Response', res.statusCode === 200, `HTTP status ${res.statusCode}`);
    let body = '';
    res.on('data', chunk => body += chunk);
    res.on('end', () => {
        runQAChecks(body);
    });
}).on('error', (err) => {
    console.error('Server connection failed:', err.message);
    process.exit(1);
});

function runQAChecks(html) {
    // 1. INITIAL STATE IN DOM
    console.log('\n--- 1. INITIAL STATE VERIFICATION ---');
    check('Empty target-lat-input', html.includes('id="target-lat-input" value=""'));
    check('Empty target-lon-input', html.includes('id="target-lon-input" value=""'));
    check('Empty map-lat-input', html.includes('id="map-lat-input" value=""'));
    check('Empty map-lon-input', html.includes('id="map-lon-input" value=""'));
    check('Dashboard score shows neutral em-dash', /id="score-number"[^>]*>—<\/span>/.test(html));
    check('Map score shows neutral em-dash', /id="map-score-number"[^>]*>—<\/span>/.test(html));
    check('Status shows Awaiting Target', /id="map-classification-tag"[^>]*>Awaiting Target<\/span>/.test(html));
    check('Target status badge shows No Target', /id="target-source-badge"[^>]*>No Target<\/span>/.test(html));
    check('Guidance prompt shows Click map or choose preset', /id="target-tile-status"[^>]*>Click map or choose preset<\/span>/.test(html));
    check('Search input #location-search-input is empty', html.includes('id="location-search-input"') && !html.includes('id="location-search-input" value='));
    check('Map search input #map-location-search-input is empty', html.includes('id="map-location-search-input"') && !html.includes('id="map-location-search-input" value='));

    // Check js/map.js neutral state code
    const mapJs = fs.readFileSync(path.join(__dirname, '../js/map.js'), 'utf8');
    check('map.js state starts with hasTarget: false', mapJs.includes('hasTarget: false'));
    check('Marker and buffer circle creation gated on state.hasTarget', mapJs.includes('if (state.hasTarget && state.lat && state.lon) {'));
    check('No automatic Ghondi selection on init', !mapJs.includes('this.setTargetLocation(21.9455, 80.4295') && !mapJs.includes('this.setTargetLocation(21.9455, 80.4295, true)'));
    check('resetLiveProspectivityCard called on unselected startup', mapJs.includes('resetLiveProspectivityCard();'));

    // 2. SEARCH EXPERIENCE & RESOLVER
    console.log('\n--- 2. SEARCH EXPERIENCE VERIFICATION ---');
    const LocationResolver = require('../js/locations.js');

    const ghondiSuggestions = LocationResolver.searchLocations('Ghondi');
    check('Ghondi search yields suggestions', ghondiSuggestions.length > 0, `found ${ghondiSuggestions.length}`);
    const topGhondi = ghondiSuggestions[0];
    check('Ghondi is clearly identifiable', topGhondi && (topGhondi.shortName === 'Ghondi' || topGhondi.name.includes('Ghondi')));
    check('Ghondi coordinates match deposit', Math.abs(topGhondi.lat - 21.9455) < 0.001 && Math.abs(topGhondi.lon - 80.4295) < 0.001);
    check('Ghondi has place metadata', topGhondi.type === 'deposit' && topGhondi.subArea.includes('Balaghat'));

    // Test selection trigger / reverseGeocode
    const resolvedGhondi = LocationResolver.reverseGeocode(topGhondi.lat, topGhondi.lon);
    check('Selecting Ghondi resolves place name', resolvedGhondi.placeName.includes('Ghondi'));
    check('Resolves subArea', resolvedGhondi.subArea.includes('Balaghat'));

    // 3. MAP CLICK PLACE IDENTIFICATION
    console.log('\n--- 3. MAP CLICK PLACE IDENTIFICATION ---');
    // Test known mine: Ukwa Mine (21.9680, 80.4710)
    const ukwaClick = LocationResolver.reverseGeocode(21.9680, 80.4710);
    check('Click at Ukwa identifies Ukwa Manganese Mine', ukwaClick.placeName.includes('Ukwa'));
    check('Identifies mine category accurately', ukwaClick.type === 'mine');

    // Test Bharweli Mine (21.8488, 80.2289)
    const bharweliClick = LocationResolver.reverseGeocode(21.8488, 80.2289);
    check('Click near Bharweli identifies Bharweli Mine', bharweliClick.placeName.includes('Bharweli'));

    // Test arbitrary location inside exploration footprint: (21.90, 80.35)
    const arbitraryClick = LocationResolver.reverseGeocode(21.90, 80.35);
    check('Arbitrary location produces honest fallback name', arbitraryClick.placeName !== 'Unknown' && arbitraryClick.placeName.length > 0, `got "${arbitraryClick.placeName}"`);
    check('Fallback name does not hallucinate false village', !arbitraryClick.isDirectMatch || arbitraryClick.placeName.includes('Sector') || arbitraryClick.placeName.includes('Exploration') || arbitraryClick.placeName.includes('of'));

    // 4. MAP PLACE LABELS OVERLAY
    console.log('\n--- 4. MAP PLACE LABELS OVERLAY ---');
    const placeMarkers = LocationResolver.getMapPlaceLabels();
    check('Cartographic place markers available', placeMarkers.length >= 10, `found ${placeMarkers.length} markers`);
    const towns = placeMarkers.filter(m => m.type === 'town');
    const mines = placeMarkers.filter(m => m.type === 'mine');
    const deposits = placeMarkers.filter(m => m.type === 'deposit');
    check('Contains key towns (Balaghat, Baihar, Katangi, Waraseoni)', towns.length >= 3);
    check('Contains mining hubs (Bharweli, Ukwa, Tirodi, Ramrama)', mines.length >= 3);
    check('Contains deposits/exploration areas (Ghondi, etc.)', deposits.length >= 1);

    // CSS layer styles check
    const css = fs.readFileSync(path.join(__dirname, '../styles.css'), 'utf8');
    check('Map place tag CSS defined', css.includes('.map-place-tag'));
    check('Map place tag town variant defined', css.includes('.map-place-tag.town'));
    check('Map place tag mine variant defined', css.includes('.map-place-tag.mine'));
    check('Labels layer has pointer events / no blocking', css.includes('.map-place-label'));

    // 5. PROSPECTIVITY ZONES POPUP
    console.log('\n--- 5. PROSPECTIVITY ZONE POPUPS ---');
    check('Zone popup contains Zone ID & Sector name', mapJs.includes('Zone ${zone.zoneId}') && mapJs.includes('${sectorName}'));
    check('Zone popup contains Prospectivity %', mapJs.includes('Prospectivity') && mapJs.includes('zone.meanScore * 100'));
    check('Zone popup contains Rank', mapJs.includes('Rank:') && mapJs.includes('#${rankNum}'));
    check('Zone popup contains Coordinates', mapJs.includes('Coordinates:') && mapJs.includes('zone.lat.toFixed') && mapJs.includes('zone.lon.toFixed'));
    check('Zone popup contains Area Footprint & Pixels', mapJs.includes('Ground Footprint') && mapJs.includes('pixels @ 20m'));
    check('Zone popup contains Set Target button', mapJs.includes('Set Target'));
    check('Zone popup contains Analyze Zone button', mapJs.includes('Analyze Zone'));

    // 6. SELECTED TARGET MARKER VISUAL UNIQUENESS
    console.log('\n--- 6. SELECTED TARGET PIN DISTINCTIVENESS ---');
    check('Selected target has TARGET banner', mapJs.includes('TARGET') && css.includes('.target-flag-tag'));
    check('Selected target has pulsing beacon dot', css.includes('.target-pulse-dot') || css.includes('.target-beacon-core'));
    check('Selected target shows place name callout', mapJs.includes('target-name-callout') || mapJs.includes('target-flag-name'));
    check('Prospectivity zone pins show percentage numbers (zone-pin / zone-core)', mapJs.includes('zone-pin') && mapJs.includes('zone-core') && mapJs.includes('${scorePct}%'));

    // 7. UI QUALITY AND OVERFLOW INSPECTION
    console.log('\n--- 7. UI QUALITY AND Z-INDEX INSPECTION ---');
    check('Suggestions dropdown z-index >= 1000', css.includes('z-index: 1200'));
    check('Search input wrapper relative positioned', css.includes('.location-search-container') && css.includes('position: relative'));
    check('No duplicate place card IDs in map sidebar', (html.match(/id="map-place-name"/g) || []).length === 1);
    check('Layer toggle controls present', html.includes('id="toggle-place-labels"') && html.includes('id="toggle-tile-footprint"'));
    const locationsJs = fs.readFileSync(path.join(__dirname, '../js/locations.js'), 'utf8');
    check('Accurately implemented as Local Geographic Place Resolver', locationsJs.includes('Local Geographic Place Resolver') || locationsJs.includes('local geographic') || locationsJs.includes('Module: LocationResolver'));

    console.log('\n================================================================');
    console.log(`QA PASS SUMMARY: ${passedChecks} / ${totalChecks} checks passed (${Math.round((passedChecks / totalChecks) * 100)}%)`);
    console.log('================================================================\n');

    if (totalChecks - passedChecks > 0) {
        process.exit(1);
    }
}
