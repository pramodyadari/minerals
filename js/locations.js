/**
 * ============================================================================
 * AI MINERAL INTELLIGENCE — GEOGRAPHIC RESOLVER & LOCATION SEARCH MODULE
 * ============================================================================
 * 
 * Module: LocationResolver (js/locations.js)
 * 
 * Purpose:
 *   Provides authentic geographic search, suggestions, and reverse-geocoding
 *   for the Sentinel-2 Tile T44QMK mineral exploration belt (Central India).
 * 
 * Key Features:
 *   1. Real geographic place names (Towns, Tehsils, Mining Hubs, Districts).
 *   2. Reverse-geocoding from coordinates without inventing fake village names.
 *   3. Search suggestions covering places, districts, discovery zones, and presets.
 *   4. Zoom-stratified map labels for interactive Leaflet visualization.
 * ============================================================================
 */

(function (root, factory) {
    if (typeof define === 'function' && define.amd) {
        define(['./geo', './data'], factory);
    } else if (typeof module === 'object' && module.exports) {
        const GeoEngine = require('./geo');
        const MineralData = require('./data');
        module.exports = factory(GeoEngine, MineralData);
    } else {
        root.LocationResolver = factory(root.GeoEngine, root.MineralData);
    }
}(typeof self !== 'undefined' ? self : this, function (GeoEngine, MineralData) {
    'use strict';

    // ------------------------------------------------------------------------
    // 1. AUTHENTIC GEOGRAPHICAL PLACES (SENTINEL-2 T44QMK TILE FOOTPRINT)
    // ------------------------------------------------------------------------
    const KNOWN_PLACES = [
        // Known mining sites and reference deposits
        {
            id: 'ghondi-mine',
            name: 'Ghondi',
            displayName: 'Ghondi, Madhya Pradesh',
            subArea: 'Balaghat District',
            district: 'Balaghat District',
            state: 'Madhya Pradesh',
            lat: 21.9455,
            lon: 80.4295,
            type: 'deposit',
            badge: 'Known Deposit',
            importance: 10,
            minZoom: 9
        },
        {
            id: 'bharweli-mine',
            name: 'Bharweli',
            displayName: 'Bharweli, Madhya Pradesh',
            subArea: 'MOIL Manganese Mine, Balaghat District',
            district: 'Balaghat District',
            state: 'Madhya Pradesh',
            lat: 21.8488,
            lon: 80.2289,
            type: 'mine',
            badge: 'Active Mine (MOIL)',
            importance: 9,
            minZoom: 10
        },
        {
            id: 'ukwa-mine',
            name: 'Ukwa',
            displayName: 'Ukwa, Madhya Pradesh',
            subArea: 'Ukwa Manganese Belt, Balaghat District',
            district: 'Balaghat District',
            state: 'Madhya Pradesh',
            lat: 21.9678,
            lon: 80.4682,
            type: 'mine',
            badge: 'Manganese Center',
            importance: 9,
            minZoom: 10
        },
        {
            id: 'malanjkhand-mine',
            name: 'Malanjkhand',
            displayName: 'Malanjkhand, Madhya Pradesh',
            subArea: 'HCL Copper Mining Hub, Balaghat District',
            district: 'Balaghat District',
            state: 'Madhya Pradesh',
            lat: 22.0200,
            lon: 80.7100,
            type: 'mine',
            badge: 'Copper Belt (HCL)',
            importance: 9,
            minZoom: 10
        },
        {
            id: 'tirodi-mine',
            name: 'Tirodi',
            displayName: 'Tirodi, Madhya Pradesh',
            subArea: 'Tirodi Manganese Mines, Balaghat District',
            district: 'Balaghat District',
            state: 'Madhya Pradesh',
            lat: 21.6847,
            lon: 79.9482,
            type: 'mine',
            badge: 'Manganese Mining Town',
            importance: 8,
            minZoom: 10
        },
        {
            id: 'ramrama-mine',
            name: 'Ramrama',
            displayName: 'Ramrama, Madhya Pradesh',
            subArea: 'Ramrama Manganese Mines, Balaghat District',
            district: 'Balaghat District',
            state: 'Madhya Pradesh',
            lat: 21.8500,
            lon: 80.1167,
            type: 'mine',
            badge: 'Manganese Mine',
            importance: 8,
            minZoom: 11
        },

        // District Headquarters & Major Towns
        {
            id: 'balaghat-city',
            name: 'Balaghat',
            displayName: 'Balaghat, Madhya Pradesh',
            subArea: 'District Headquarters',
            district: 'Balaghat District',
            state: 'Madhya Pradesh',
            lat: 21.8129,
            lon: 80.1837,
            type: 'town',
            badge: 'District HQ',
            importance: 10,
            minZoom: 8
        },
        {
            id: 'baihar-town',
            name: 'Baihar',
            displayName: 'Baihar, Madhya Pradesh',
            subArea: 'Tehsil Headquarters, Balaghat District',
            district: 'Balaghat District',
            state: 'Madhya Pradesh',
            lat: 22.1039,
            lon: 80.5476,
            type: 'town',
            badge: 'Tehsil Town',
            importance: 8,
            minZoom: 9
        },
        {
            id: 'waraseoni-town',
            name: 'Waraseoni',
            displayName: 'Waraseoni, Madhya Pradesh',
            subArea: 'Tehsil Town, Balaghat District',
            district: 'Balaghat District',
            state: 'Madhya Pradesh',
            lat: 21.7619,
            lon: 80.0483,
            type: 'town',
            badge: 'Tehsil Town',
            importance: 8,
            minZoom: 9
        },
        {
            id: 'lalburra-town',
            name: 'Lalburra',
            displayName: 'Lalburra, Madhya Pradesh',
            subArea: 'Tehsil Center, Balaghat District',
            district: 'Balaghat District',
            state: 'Madhya Pradesh',
            lat: 21.9218,
            lon: 80.0240,
            type: 'town',
            badge: 'Tehsil Center',
            importance: 7,
            minZoom: 10
        },
        {
            id: 'katangi-town',
            name: 'Katangi',
            displayName: 'Katangi, Madhya Pradesh',
            subArea: 'Manganese Belt, Balaghat District',
            district: 'Balaghat District',
            state: 'Madhya Pradesh',
            lat: 21.7761,
            lon: 79.7925,
            type: 'town',
            badge: 'Mining Belt',
            importance: 7,
            minZoom: 10
        },
        {
            id: 'paraswada-town',
            name: 'Paraswada',
            displayName: 'Paraswada, Madhya Pradesh',
            subArea: 'Tehsil Center, Balaghat District',
            district: 'Balaghat District',
            state: 'Madhya Pradesh',
            lat: 22.1833,
            lon: 80.3000,
            type: 'town',
            badge: 'Tehsil Center',
            importance: 7,
            minZoom: 10
        },
        {
            id: 'lanji-town',
            name: 'Lanji',
            displayName: 'Lanji, Madhya Pradesh',
            subArea: 'Lanji Tehsil / Fort Area, Balaghat District',
            district: 'Balaghat District',
            state: 'Madhya Pradesh',
            lat: 21.5033,
            lon: 80.5467,
            type: 'town',
            badge: 'Tehsil Town',
            importance: 7,
            minZoom: 10
        },
        {
            id: 'kirnapur-town',
            name: 'Kirnapur',
            displayName: 'Kirnapur, Madhya Pradesh',
            subArea: 'Tehsil Center, Balaghat District',
            district: 'Balaghat District',
            state: 'Madhya Pradesh',
            lat: 21.6528,
            lon: 80.3167,
            type: 'town',
            badge: 'Tehsil Center',
            importance: 7,
            minZoom: 10
        },
        {
            id: 'lamta-town',
            name: 'Lamta',
            displayName: 'Lamta, Madhya Pradesh',
            subArea: 'Railway Station / Town, Balaghat District',
            district: 'Balaghat District',
            state: 'Madhya Pradesh',
            lat: 22.1333,
            lon: 80.1833,
            type: 'town',
            badge: 'Railway Hub',
            importance: 7,
            minZoom: 10
        },
        {
            id: 'nainpur-town',
            name: 'Nainpur',
            displayName: 'Nainpur, Madhya Pradesh',
            subArea: 'Railway Junction, Mandla District',
            district: 'Mandla District',
            state: 'Madhya Pradesh',
            lat: 22.4333,
            lon: 80.1167,
            type: 'town',
            badge: 'Mandla Northern Sector',
            importance: 7,
            minZoom: 9
        },
        {
            id: 'bichhiya-town',
            name: 'Bichhiya',
            displayName: 'Bichhiya, Madhya Pradesh',
            subArea: 'Tehsil Town, Mandla District',
            district: 'Mandla District',
            state: 'Madhya Pradesh',
            lat: 22.4500,
            lon: 80.7000,
            type: 'town',
            badge: 'Mandla District',
            importance: 7,
            minZoom: 10
        },
        {
            id: 'gondia-city',
            name: 'Gondia',
            displayName: 'Gondia, Maharashtra',
            subArea: 'District Headquarters, Maharashtra',
            district: 'Gondia District',
            state: 'Maharashtra',
            lat: 21.4589,
            lon: 80.1961,
            type: 'town',
            badge: 'Southern Border',
            importance: 8,
            minZoom: 8
        },
        {
            id: 'tiroda-town',
            name: 'Tiroda',
            displayName: 'Tiroda, Maharashtra',
            subArea: 'Gondia District, Maharashtra',
            district: 'Gondia District',
            state: 'Maharashtra',
            lat: 21.4167,
            lon: 79.9333,
            type: 'town',
            badge: 'Industrial Town',
            importance: 7,
            minZoom: 10
        },
        {
            id: 'amgaon-town',
            name: 'Amgaon',
            displayName: 'Amgaon, Maharashtra',
            subArea: 'Gondia District, Maharashtra',
            district: 'Gondia District',
            state: 'Maharashtra',
            lat: 21.3667,
            lon: 80.3833,
            type: 'town',
            badge: 'Maharashtra Border',
            importance: 6,
            minZoom: 10
        }
    ];

    // ------------------------------------------------------------------------
    // 2. CANDIDATE DISCOVERY ZONES DIRECTORY
    // ------------------------------------------------------------------------
    const ZONE_METADATA = {
        67684:  { sector: 'NW Cluster', subArea: 'Paraswada / Lamta Sector, Balaghat', rank: 1, score: 97.6 },
        67387:  { sector: 'NW Cluster North', subArea: 'Paraswada Sector, Balaghat', rank: 2, score: 97.3 },
        124766: { sector: 'Central East', subArea: 'Baihar East Sector, Balaghat', rank: 3, score: 97.0 },
        187925: { sector: 'South East', subArea: 'Lanji Sector, Balaghat', rank: 4, score: 96.9 },
        160475: { sector: 'Eastern Range', subArea: 'Lanji / Amgaon Border, Balaghat', rank: 5, score: 96.8 },
        35688:  { sector: 'Northern Ridge', subArea: 'Nainpur South Sector, Mandla/Balaghat', rank: 6, score: 96.8 },
        189867: { sector: 'Southern Anomaly', subArea: 'Kirnapur South Sector, Balaghat', rank: 7, score: 96.8 },
        167254: { sector: 'South Central', subArea: 'Waraseoni / Balaghat West Sector', rank: 8, score: 96.7 },
        180345: { sector: 'SW Cluster', subArea: 'Waraseoni SW Sector, Balaghat', rank: 9, score: 96.7 },
        39890:  { sector: 'NW Edge', subArea: 'Lamta North Sector, Balaghat', rank: 10, score: 96.7 },
        162862: { sector: 'Central West', subArea: 'Waraseoni Sector, Balaghat', rank: 11, score: 96.7 },
        179466: { sector: 'SW Anomaly', subArea: 'Waraseoni SW Sector, Balaghat', rank: 12, score: 96.7 },
        103786: { sector: 'Central Belt', subArea: 'Ukwa / Baihar Corridor, Balaghat', rank: 13, score: 96.7 },
        180659: { sector: 'SW Ridge', subArea: 'Waraseoni Sector, Balaghat', rank: 14, score: 96.6 },
        191911: { sector: 'Southern Belt', subArea: 'Kirnapur Sector, Balaghat', rank: 15, score: 96.6 },
        91324:  { sector: 'West Central', subArea: 'Lalburra North Sector, Balaghat', rank: 16, score: 96.6 },
        32809:  { sector: 'Far North', subArea: 'Baihar North Sector, Balaghat', rank: 17, score: 96.6 },
        113980: { sector: 'Balaghat NW', subArea: 'Balaghat NW Sector, Balaghat', rank: 18, score: 96.6 },
        92467:  { sector: 'Central West Anomaly', subArea: 'Lalburra Sector, Balaghat', rank: 19, score: 96.6 },
        115839: { sector: 'North Corridor', subArea: 'Ghondi / Ukwa West Sector, Balaghat', rank: 20, score: 96.6 }
    };

    /**
     * Calculates the cardinal direction compass bearing from point A to point B.
     */
    function getCardinalDirection(lat1, lon1, lat2, lon2) {
        const dLat = lat2 - lat1;
        const dLon = lon2 - lon1;
        const angle = (Math.atan2(dLon, dLat) * 180 / Math.PI + 360) % 360;
        
        const directions = ['N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW', 'N'];
        const index = Math.round(angle / 45);
        return directions[index];
    }

    /**
     * Builds list of all searchable discovery zones using MineralData.
     */
    function getSearchableZones() {
        if (!MineralData || !MineralData.CANDIDATE_ZONES) return [];
        return MineralData.CANDIDATE_ZONES.map(z => {
            const meta = ZONE_METADATA[z.zoneId] || { sector: 'Cluster', subArea: 'Balaghat Belt', rank: '—', score: Math.round(z.meanScore * 1000) / 10 };
            return {
                id: `zone-${z.zoneId}`,
                zoneId: z.zoneId,
                name: `Zone ${z.zoneId} — ${meta.sector}`,
                displayName: `Zone ${z.zoneId} — ${meta.sector} (${meta.score}%)`,
                subArea: meta.subArea,
                district: 'Balaghat District',
                state: 'Madhya Pradesh',
                lat: z.lat,
                lon: z.lon,
                type: 'zone',
                badge: `Zone #${meta.rank} (${meta.score}%)`,
                score: meta.score,
                rank: meta.rank,
                areaHectares: z.areaHectares
            };
        });
    }

    /**
     * Searches locations, places, districts, and candidate zones matching the user query.
     * 
     * @param {string} query - Free text input from user
     * @param {number} maxResults - Max items to return
     * @returns {Array<object>} Suggestions matching query
     */
    function searchLocations(query, maxResults = 8) {
        if (!query || typeof query !== 'string') return [];
        const clean = query.trim().toLowerCase();
        if (clean.length === 0) return [];

        const results = [];
        const seenIds = new Set();

        // 1. Match against known towns, mines, and deposits
        for (const place of KNOWN_PLACES) {
            const matchName = place.name.toLowerCase().includes(clean);
            const matchDisplay = place.displayName.toLowerCase().includes(clean);
            const matchDistrict = place.district.toLowerCase().includes(clean);
            const matchSubArea = place.subArea.toLowerCase().includes(clean);
            const matchState = place.state.toLowerCase().includes(clean);

            if (matchName || matchDisplay || matchDistrict || matchSubArea || matchState) {
                results.push({
                    id: place.id,
                    name: place.displayName,
                    shortName: place.name,
                    displayName: place.displayName,
                    subArea: place.subArea,
                    district: place.district,
                    state: place.state,
                    lat: place.lat,
                    lon: place.lon,
                    type: 'place',
                    badge: 'Location',
                    placeType: place.type,
                    placeBadge: place.badge,
                    icon: '📍',
                    score: matchName ? 100 : (matchDisplay ? 80 : 50)
                });
                seenIds.add(place.id);
            }
        }

        // 2. Match against candidate discovery zones
        const zones = getSearchableZones();
        for (const zone of zones) {
            const zoneIdStr = String(zone.zoneId);
            const matchId = zoneIdStr.includes(clean);
            const matchName = zone.name.toLowerCase().includes(clean);
            const matchSector = zone.subArea.toLowerCase().includes(clean);
            const matchZoneWord = clean.includes('zone') || clean.includes('cluster') || clean.includes('anomaly') || clean.includes('target');

            if (matchId || matchName || matchSector || (matchZoneWord && clean.length > 2)) {
                if (!seenIds.has(zone.id)) {
                    results.push({
                        ...zone,
                        type: 'zone',
                        badge: 'Exploration Target',
                        icon: '🎯',
                        score: matchId ? 95 : 75
                    });
                    seenIds.add(zone.id);
                }
            }
        }

        // 3. Support coordinate string inputs in search box (e.g. "21.94, 80.42")
        const coordMatch = clean.match(/^([+-]?\d+(?:\.\d+)?)[,\s]+([+-]?\d+(?:\.\d+)?)$/);
        if (coordMatch) {
            const cLat = parseFloat(coordMatch[1]);
            const cLon = parseFloat(coordMatch[2]);
            if (!isNaN(cLat) && !isNaN(cLon) && cLat >= -90 && cLat <= 90 && cLon >= -180 && cLon <= 180) {
                const inTile = GeoEngine ? GeoEngine.isWithinTileBounds(cLat, cLon) : true;
                results.unshift({
                    id: `coord-${cLat.toFixed(4)}-${cLon.toFixed(4)}`,
                    name: `Coordinate (${cLat.toFixed(4)}°N, ${cLon.toFixed(4)}°E)`,
                    displayName: `Coordinate (${cLat.toFixed(4)}°N, ${cLon.toFixed(4)}°E)`,
                    subArea: inTile ? 'Inside Tile T44QMK Footprint' : 'Outside Analysis Area',
                    district: 'Custom Location',
                    state: 'Central India',
                    lat: cLat,
                    lon: cLon,
                    type: 'place',
                    badge: inTile ? 'Location' : 'Out of Bounds',
                    icon: '📍',
                    score: 200
                });
            }
        }

        // Sort by relevance score descending
        results.sort((a, b) => b.score - a.score);
        return results.slice(0, maxResults);
    }

    /**
     * Resolves a coordinate pair (lat, lon) to a legitimate geographical place name
     * without requiring or coupling to a candidate discovery zone.
     * 
     * @param {number} lat - Target latitude
     * @param {number} lon - Target longitude
     * @returns {object} { placeName, subArea, district, state, inTileBounds, isZone, candidateZone, zoneId }
     */
    function reverseGeocode(lat, lon) {
        if (typeof lat !== 'number' || typeof lon !== 'number' || isNaN(lat) || isNaN(lon)) {
            return {
                placeName: 'Invalid Coordinates',
                shortName: 'Invalid',
                subArea: 'N/A',
                district: 'N/A',
                state: 'N/A',
                inTileBounds: false,
                isZone: false,
                candidateZone: null,
                zoneId: null,
                isDirectMatch: false
            };
        }

        const isInside = GeoEngine ? GeoEngine.isWithinTileBounds(lat, lon) : true;

        if (!isInside) {
            return {
                placeName: 'Outside Sentinel-2 Analysis Area',
                shortName: 'Outside Area',
                subArea: 'Beyond Sentinel-2 T44QMK Footprint (Model coverage unavailable)',
                district: 'Out of Bounds',
                state: 'Central India',
                inTile: false,
                inTileBounds: false,
                isZone: false,
                candidateZone: null,
                zoneId: null,
                isDirectMatch: false
            };
        }

        // Check distance to all known places
        let closestPlace = null;
        let minPlaceDist = Infinity;

        for (const p of KNOWN_PLACES) {
            const dist = GeoEngine ? GeoEngine.haversineDistanceKm(lat, lon, p.lat, p.lon) : 999;
            if (dist < minPlaceDist) {
                minPlaceDist = dist;
                closestPlace = p;
            }
        }

        // Check distance to all candidate discovery zones
        const zones = getSearchableZones();
        let closestZone = null;
        let minZoneDist = Infinity;

        for (const z of zones) {
            const dist = GeoEngine ? GeoEngine.haversineDistanceKm(lat, lon, z.lat, z.lon) : 999;
            if (dist < minZoneDist) {
                minZoneDist = dist;
                closestZone = z;
            }
        }

        // Zone membership is OPTIONAL: only set if coordinate is within the immediate discovery cluster (<= 0.5 km)
        const matchingZone = (closestZone && minZoneDist <= 0.5) ? closestZone : null;

        // Place naming logic (Places are independent of zones)
        let placeName = '';
        let shortName = '';
        let subArea = '';
        let district = closestPlace ? closestPlace.district : 'Balaghat District';
        let state = closestPlace ? closestPlace.state : 'Madhya Pradesh';

        if (matchingZone) {
            placeName = matchingZone.name;
            shortName = `Zone ${matchingZone.zoneId}`;
            subArea = `${matchingZone.subArea} (Rank #${matchingZone.rank}, ${matchingZone.score}%)`;
        } else if (closestPlace && minPlaceDist <= 3.0) {
            placeName = closestPlace.displayName;
            shortName = closestPlace.name;
            subArea = closestPlace.subArea;
        } else if (closestPlace && minPlaceDist <= 15.0) {
            const direction = getCardinalDirection(closestPlace.lat, closestPlace.lon, lat, lon);
            const distKm = Math.round(minPlaceDist * 10) / 10;
            placeName = `${distKm} km ${direction} of ${closestPlace.name}, ${closestPlace.state}`;
            shortName = closestPlace.name;
            subArea = `${district}, ${state}`;
        } else {
            placeName = `Exploration Location (${lat.toFixed(4)}°N, ${lon.toFixed(4)}°E)`;
            shortName = `Target (${lat.toFixed(2)}, ${lon.toFixed(2)})`;
            subArea = `Balaghat Mineral Belt, ${district}`;
        }

        return {
            placeName: placeName,
            shortName: shortName,
            subArea: subArea,
            district: district,
            state: state,
            inTile: true,
            inTileBounds: true,
            isDirectMatch: matchingZone ? true : (closestPlace && minPlaceDist <= 3.0),
            isZone: Boolean(matchingZone),
            zoneMetadata: matchingZone,
            candidateZone: matchingZone,
            zoneId: matchingZone ? matchingZone.zoneId : null,
            type: matchingZone ? 'zone' : 'place'
        };
    }

    /**
     * Returns the list of cartographic labels for interactive Leaflet place labels layer.
     */
    function getMapPlaceLabels() {
        return KNOWN_PLACES.map(p => ({
            name: p.name,
            displayName: p.displayName,
            lat: p.lat,
            lon: p.lon,
            type: p.type,
            minZoom: p.minZoom
        }));
    }

    return {
        searchLocations,
        reverseGeocode,
        getMapPlaceLabels,
        getSearchableZones,
        KNOWN_PLACES,
        ZONE_METADATA
    };
}));
