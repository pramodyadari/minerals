/**
 * ============================================================================
 * AI MINERAL INTELLIGENCE — INTERACTIVE 2D EXPLORATION MAP (LEAFLET.JS)
 * ============================================================================
 * 
 * Module: ExplorationMap (js/map.js)
 * 
 * Purpose:
 *   Provides a real, full-featured GIS exploration map powered by Leaflet.js:
 *     1. Satellite, Dark Matter, and OpenStreetMap basemaps with live layer switching.
 *     2. Selected exploration center marker with pulsing beacon animation.
 *     3. Dynamic analysis radius circle (10 km, 25 km, 50 km, 100 km).
 *     4. Real Sentinel-2 Tile T44QMK bounding box outline (EPSG:32644 bounds).
 *     5. All 20 verified high-prospectivity candidate zones plotted as interactive markers.
 *     6. Rich popup cards displaying real Zone ID, AI Score, Pixel count, Hectares,
 *        UTM coordinates, and Haversine distance from the selected location.
 *     7. Interactive map clicks to dynamically select new exploration targets.
 *     8. Automatic candidate zone count & filtering within the analysis radius.
 * 
 * Reuses:
 *   - GeoEngine (js/geo.js) for coordinate transformations and bounds checking.
 *   - MineralData (js/data.js) for verified candidate zones and satellite metadata.
 * ============================================================================
 */

(function (root, factory) {
    if (typeof define === 'function' && define.amd) {
        define(['./geo', './data', './locations'], factory);
    } else if (typeof module === 'object' && module.exports) {
        let loc = null;
        try { loc = require('./locations'); } catch (e) {}
        module.exports = factory(require('./geo'), require('./data'), loc);
    } else {
        root.ExplorationMap = factory(root.GeoEngine, root.MineralData, root.LocationResolver);
    }
}(typeof self !== 'undefined' ? self : this, function (GeoEngine, MineralData, LocationResolver) {
    'use strict';

    // State variables
    let map = null;
    let baseLayers = {};
    let currentBaseLayer = null;
    let selectedMarker = null;
    let radiusCircle = null;
    let tileBoundsPolygon = null;
    let zoneMarkersLayer = null;
    let prospectivityOverlay = null;
    let labelsTileLayer = null;
    let placeMarkersLayer = null;
    let locationChangeListeners = [];

    // Current exploration state
    let state = {
        lat: MineralData ? MineralData.KNOWN_MINE.latitude : 21.9455,
        lon: MineralData ? MineralData.KNOWN_MINE.longitude : 80.4295,
        locationName: MineralData ? MineralData.KNOWN_MINE.name : "Ghondi Manganese Mine",
        radiusKm: 25,
        showZones: true,
        showLabels: true,
        showTileFootprint: true,
        showProspectivityOverlay: true,
        activeLayerType: 'satellite',
        opacity: 0.8,
        source: 'preset',
        hasTarget: false, // UX requirement: No target auto-selected on application startup
        resolvedPlace: null
    };

    /**
     * Initializes the Leaflet exploration map on the specified container.
     * 
     * @param {string} containerId - DOM ID of the map element
     * @param {object} initialOptions - Optional overrides for initial state
     * @returns {object|null} Map instance controller
     */
    function init(containerId = 'leaflet-map', initialOptions = {}) {
        const container = document.getElementById(containerId);
        if (!container) {
            console.warn(`[ExplorationMap] Container #${containerId} not found.`);
            return null;
        }

        // If map already initialized, just resize and refresh
        if (map) {
            map.invalidateSize();
            return publicApi;
        }

        // Apply any initial options
        if (initialOptions.lat !== undefined) state.lat = initialOptions.lat;
        if (initialOptions.lon !== undefined) state.lon = initialOptions.lon;
        if (initialOptions.radiusKm !== undefined) state.radiusKm = initialOptions.radiusKm;
        if (initialOptions.hasTarget !== undefined) state.hasTarget = initialOptions.hasTarget;

        // Ensure Leaflet is loaded
        if (typeof L === 'undefined') {
            console.error('[ExplorationMap] Leaflet (L) is not loaded. Please include leaflet.js.');
            return null;
        }

        // Sensible initial map center: center of Sentinel-2 Tile T44QMK exploration footprint (~21.95°N, 80.25°E)
        const initialCenter = (state.hasTarget && state.lat && state.lon)
            ? [state.lat, state.lon]
            : [21.95, 80.25];

        // Initialize Leaflet Map
        map = L.map(containerId, {
            center: initialCenter,
            zoom: 10,
            minZoom: 5,
            maxZoom: 18,
            zoomControl: false // Using custom buttons
        });

        // Add basemap tile providers
        setupTileLayers();

        // Add map place labels & cartographic context
        setupPlaceLabelsLayer();

        // Add Sentinel-2 T44QMK tile boundary footprint
        setupTileFootprint();

        // Add candidate zones layer
        setupCandidateZonesLayer();

        // Add prospectivity raster overlay
        setupProspectivityOverlay();

        // ONLY place marker and circular buffer if an active target is selected
        if (state.hasTarget && state.lat && state.lon) {
            updateSelectedLocation(state.lat, state.lon, state.locationName, state.source);
            updateZonesInRadius();
            updateLiveProspectivityCard(state.lat, state.lon, state.radiusKm);
        } else {
            resetLiveProspectivityCard();
        }

        // Bind interactive map click events
        map.on('click', handleMapClick);

        // Bind mouse move for coordinate readout
        map.on('mousemove', handleMapMouseMove);

        // Bind sidebar target presets and inputs
        setupSidebarControls();

        // Resize fix after initial DOM render
        setTimeout(() => {
            map.invalidateSize();
        }, 200);

        console.log('[ExplorationMap] Initialized successfully. Awaiting user-driven target selection.');
        return publicApi;
    }

    /**
     * Configures the available basemap tile providers:
     * 1. Esri World Imagery (High-resolution satellite view)
     * 2. CartoDB Dark Matter (Futuristic dark geospatial theme)
     * 3. OpenStreetMap Standard (Topographic/road context)
     * 4. Esri World Topo / Terrain (Topographic contours)
     */
    function setupTileLayers() {
        baseLayers.satellite = L.tileLayer(
            'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
            {
                attribution: '&copy; Esri &mdash; Earthstar Geographics, Sentinel-2',
                maxZoom: 18
            }
        );

        baseLayers.dark = L.tileLayer(
            'https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png',
            {
                attribution: '&copy; OpenStreetMap &copy; CARTO',
                subdomains: 'abcd',
                maxZoom: 19
            }
        );

        baseLayers.streets = L.tileLayer(
            'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',
            {
                attribution: '&copy; OpenStreetMap contributors',
                maxZoom: 19
            }
        );

        baseLayers.terrain = L.tileLayer(
            'https://server.arcgisonline.com/ArcGIS/rest/services/World_Topo_Map/MapServer/tile/{z}/{y}/{x}',
            {
                attribution: '&copy; Esri &mdash; Topographic World Map',
                maxZoom: 18
            }
        );

        // Default to satellite basemap for orbital mineral exploration feel
        currentBaseLayer = baseLayers.satellite;
        currentBaseLayer.addTo(map);
    }

    /**
     * Sets up the cartographic place labels overlay:
     * 1. Esri World Boundaries and Places reference tiles for real-world satellite context.
     * 2. Curated cartographic place markers for towns, mining hubs, and localities in Tile T44QMK.
     */
    function setupPlaceLabelsLayer() {
        if (!map || typeof L === 'undefined') return;

        labelsTileLayer = L.tileLayer(
            'https://server.arcgisonline.com/ArcGIS/rest/services/Reference/World_Boundaries_and_Places/MapServer/tile/{z}/{y}/{x}',
            {
                attribution: '&copy; Esri &mdash; Boundaries & Places',
                maxZoom: 18,
                zIndex: 350
            }
        );

        placeMarkersLayer = L.layerGroup();

        const res = LocationResolver || (typeof window !== 'undefined' ? window.LocationResolver : null);
        if (res && typeof res.getMapPlaceLabels === 'function') {
            const places = res.getMapPlaceLabels();
            places.forEach(p => {
                const icon = L.divIcon({
                    className: 'map-place-marker-wrapper',
                    html: `<div class="map-place-tag type-${p.type}"><span class="place-dot"></span><span class="place-name">${p.name}</span></div>`,
                    iconSize: [120, 24],
                    iconAnchor: [12, 12]
                });
                const m = L.marker([p.lat, p.lon], { icon: icon, interactive: false });
                placeMarkersLayer.addLayer(m);
            });
        }

        if (state.showLabels) {
            labelsTileLayer.addTo(map);
            placeMarkersLayer.addTo(map);
        }
    }

    /**
     * Plots the verified Sentinel-2 Tile T44QMK footprint polygon on the map.
     * Calculated directly from EPSG:32644 bounds (OriginX: 399960, OriginY: 2500020, etc.)
     */
    function setupTileFootprint() {
        if (!GeoEngine) return;

        const corners = GeoEngine.getTileBoundingBox();
        const latLngs = [
            [corners.nw.latitude, corners.nw.longitude],
            [corners.ne.latitude, corners.ne.longitude],
            [corners.se.latitude, corners.se.longitude],
            [corners.sw.latitude, corners.sw.longitude]
        ];

        tileBoundsPolygon = L.polygon(latLngs, {
            color: '#00f0ff',
            weight: 2,
            dashArray: '6, 6',
            fillColor: '#00f0ff',
            fillOpacity: 0.05
        }).addTo(map);

        tileBoundsPolygon.bindTooltip("<b>Sentinel-2 Tile T44QMK Footprint</b><br>109.8 km × 109.8 km (EPSG:32644)", {
            sticky: true,
            className: 'glass-tooltip'
        });
    }

    /**
     * Plots the 20 real high-prospectivity candidate zones from MineralData.
     */
    function setupCandidateZonesLayer() {
        zoneMarkersLayer = L.layerGroup().addTo(map);

        if (!MineralData || !MineralData.CANDIDATE_ZONES) return;

        MineralData.CANDIDATE_ZONES.forEach(zone => {
            const marker = createZoneMarker(zone);
            zoneMarkersLayer.addLayer(marker);
        });
    }

    /**
     * Creates an individual animated marker for a high-prospectivity candidate zone.
     * Keeps the percentage badge and attaches authoritative zone metadata + hover tooltip + rich popup.
     * 
     * @param {object} zone - Zone data object
     * @returns {L.Marker}
     */
    function createZoneMarker(zone) {
        // Score percentage for visual color coding
        const scorePct = Math.round(zone.meanScore * 100);

        // Resolve rich zone identity from LocationResolver
        const res = LocationResolver || (typeof window !== 'undefined' ? window.LocationResolver : null);
        const zoneInfo = res && typeof res.resolveZoneName === 'function' ? res.resolveZoneName(zone.zoneId) : null;
        const sectorName = zoneInfo ? zoneInfo.sectorName : (zone.sectorName || 'High-Grade Sector');
        const rankNum = zoneInfo ? zoneInfo.rank : (zone.rank || '#');
        const zoneTitle = `Zone ${zone.zoneId} — ${sectorName}`;

        // Custom HTML pulsing icon with percentage badge
        const iconHtml = `
            <div class="zone-pin" data-zone-id="${zone.zoneId}">
                <div class="zone-pulse"></div>
                <div class="zone-core">${scorePct}%</div>
            </div>
        `;

        const customIcon = L.divIcon({
            html: iconHtml,
            className: 'zone-marker-container',
            iconSize: [36, 36],
            iconAnchor: [18, 18],
            popupAnchor: [0, -18]
        });

        const marker = L.marker([zone.lat, zone.lon], { icon: customIcon });

        // Hover tooltip with zone identity + percentage
        marker.bindTooltip(`<b>${zoneTitle}</b><br>Prospectivity: ${(zone.meanScore * 100).toFixed(1)}% (Rank #${rankNum})`, {
            sticky: true,
            className: 'glass-tooltip'
        });

        // Calculate distance from current selected location
        const distKm = GeoEngine ? GeoEngine.haversineDistanceKm(state.lat, state.lon, zone.lat, zone.lon) : 0;

        // Resolve top evidence features for zone
        let topEvidenceStr = 'B06 Red Edge, NDVI, B8A NIR';
        const xaiMod = (typeof ExplainableAI !== 'undefined') ? ExplainableAI : (typeof window !== 'undefined' ? window.ExplainableAI : null);
        if (xaiMod && typeof xaiMod.explainProspectivityScore === 'function') {
            try {
                const exp = xaiMod.explainProspectivityScore(scorePct);
                if (exp && exp.waterfallSteps) {
                    const feats = exp.waterfallSteps.filter(s => !s.isBaseline && !s.isFinal).slice(0, 2);
                    if (feats.length > 0) {
                        topEvidenceStr = feats.map(f => `${f.name} (+${f.value.toFixed(1)}%)`).join(', ');
                    }
                }
            } catch (_) {}
        }

        // Rich interactive popup content matching Requirement 5 & 8
        const popupContent = `
            <div class="zone-popup glass-card">
                <div class="popup-header">
                    <span class="popup-badge">WHY THIS ZONE?</span>
                    <span class="popup-score high">${(zone.meanScore * 100).toFixed(1)}% Score</span>
                </div>
                <div class="popup-body">
                    <div style="font-size:0.86rem; font-weight:700; color:#fff; margin-bottom:6px;">${zoneTitle}</div>
                    <div class="popup-row">
                        <span class="p-label">Prospectivity:</span>
                        <span class="p-val font-mono cyan" style="font-weight:700;">${(zone.meanScore * 100).toFixed(1)}%</span>
                    </div>
                    <div class="popup-row">
                        <span class="p-label">Rank:</span>
                        <span class="p-val cyan">#${rankNum}</span>
                    </div>
                    <div class="popup-row">
                        <span class="p-label">Top Evidence:</span>
                        <span class="p-val" style="color:#00ff88; font-size:0.7rem;">${topEvidenceStr}</span>
                    </div>
                    <div class="popup-row">
                        <span class="p-label">Confidence:</span>
                        <span class="p-val" style="color:#f59e0b; font-family:monospace; font-weight:600;">Not Calibrated</span>
                    </div>
                    <div class="popup-row">
                        <span class="p-label">Ground Footprint:</span>
                        <span class="p-val">${zone.areaHectares} ha (${zone.pixels} pixels @ 20m)</span>
                    </div>
                    <div class="popup-row">
                        <span class="p-label">Coordinates:</span>
                        <span class="p-val font-mono">${zone.lat.toFixed(5)}°N, ${zone.lon.toFixed(5)}°E</span>
                    </div>
                    ${state.hasTarget ? `
                    <div class="popup-row">
                        <span class="p-label">Distance to Target:</span>
                        <span class="p-val cyan">${distKm} km</span>
                    </div>` : ''}
                    <div class="popup-row">
                        <span class="p-label">Projected UTM 44N:</span>
                        <span class="p-val font-mono">${zone.easting.toFixed(0)} E, ${zone.northing.toFixed(0)} N</span>
                    </div>
                    <div class="popup-row">
                        <span class="p-label">Raster Index:</span>
                        <span class="p-val font-mono">Row ${zone.row}, Col ${zone.col}</span>
                    </div>
                </div>
                <div class="popup-footer" style="display:flex;gap:4px;margin-top:10px;">
                    <button class="popup-btn" style="flex:1;" onclick="ExplorationMap.selectZoneLocation(${zone.lat}, ${zone.lon}, 'Zone #${zone.zoneId}')">
                        Set Target
                    </button>
                    <button class="popup-btn" style="flex:1;background:linear-gradient(135deg,#00f0ff,#7b2fff);color:#fff;" onclick="ExplorationMap.selectZoneLocation(${zone.lat}, ${zone.lon}, 'Zone #${zone.zoneId}');if(typeof navigateTo==='function'){navigateTo('dashboard');setTimeout(()=>{document.getElementById('dash-evidence-panel')?.scrollIntoView({behavior:'smooth'});},200);}">
                        View Evidence
                    </button>
                    <button class="popup-btn" style="flex:1;background:rgba(255,255,255,0.08);color:var(--cyan);border:1px solid rgba(0,240,255,0.3);" onclick="if(typeof addTargetToComparison==='function'){addTargetToComparison(${zone.zoneId});}else if(typeof navigateTo==='function'){navigateTo('dashboard');setTimeout(()=>{document.getElementById('dash-ranking-panel')?.scrollIntoView({behavior:'smooth'});},200);}">
                        Compare
                    </button>
                </div>
            </div>
        `;

        marker.bindPopup(popupContent, {
            maxWidth: 320,
            className: 'custom-leaflet-popup'
        });

        // Store reference on marker
        marker.zoneData = zone;
        return marker;
    }

    /**
     * Updates the exploration center marker and dynamic analysis radius circle.
     * 
     * @param {number} lat - Target latitude
     * @param {number} lon - Target longitude
     * @param {string} locationName - Human-readable name
     * @param {string} source - Origin of selection ('map' | 'zone' | 'preset' | 'manual' | 'search')
     * @param {object|null} resolvedPlaceObj - Optional pre-resolved place metadata
     */
    function updateSelectedLocation(lat, lon, locationName = "Custom Exploration Location", source = 'map', resolvedPlaceObj = null) {
        state.lat = lat;
        state.lon = lon;
        state.source = source;
        state.hasTarget = true;

        const res = LocationResolver || (typeof window !== 'undefined' ? window.LocationResolver : null);
        const resolved = resolvedPlaceObj || (res && typeof res.reverseGeocode === 'function' ? res.reverseGeocode(lat, lon) : null);
        state.resolvedPlace = resolved;

        if (locationName && locationName !== "Custom Exploration Location") {
            state.locationName = locationName;
        } else if (resolved) {
            state.locationName = resolved.fullName || resolved.placeName || locationName;
        } else {
            state.locationName = locationName;
        }

        const isInside = GeoEngine ? GeoEngine.isWithinTileBounds(lat, lon) : true;
        const placeTitle = resolved ? resolved.placeName : (locationName || 'Custom Exploration Target');
        const subArea = resolved ? resolved.subArea : '';
        const shortName = resolved ? (resolved.shortName || resolved.placeName) : 'Target';

        if (map && typeof L !== 'undefined') {
            // Selected target marker: Visually different from zone pins (TARGET ▼ badge + pulse beacon)
            const targetIconHtml = `
                <div class="selected-target-pin-wrap">
                    <div class="target-flag-tag">TARGET</div>
                    <div class="target-flag-name">${shortName}</div>
                    <div class="target-pin-arrow">▼</div>
                    <div class="target-beacon-core"></div>
                </div>
            `;

            const targetIcon = L.divIcon({
                html: targetIconHtml,
                className: 'target-marker-container',
                iconSize: [120, 60],
                iconAnchor: [60, 52],
                popupAnchor: [0, -48]
            });

            if (!selectedMarker) {
                selectedMarker = L.marker([lat, lon], { icon: targetIcon, zIndexOffset: 1000 }).addTo(map);
            } else {
                selectedMarker.setLatLng([lat, lon]);
                selectedMarker.setIcon(targetIcon);
            }

            // Calculate live prospective score and evidence if engine is ready
            let liveScoreNum = null;
            let liveScoreText = '—';
            let priorityText = 'AWAITING';
            let priorityColor = 'var(--text-dim)';
            let topEvidenceBullets = '<li>• Awaiting target calculation</li>';

            const engine = (typeof ProspectivityEngine !== 'undefined') ? ProspectivityEngine : (typeof window !== 'undefined' ? window.ProspectivityEngine : null);
            if (engine && typeof engine.analyzeLocationSync === 'function') {
                try {
                    const r = engine.analyzeLocationSync(lat, lon, state.radiusKm);
                    if (r && r.insideRaster) {
                        liveScoreNum = r.prospectivityPercent;
                        liveScoreText = `${r.prospectivityPercent}%`;
                        if (liveScoreNum >= 75) {
                            priorityText = 'HIGH';
                            priorityColor = '#00ff88';
                        } else if (liveScoreNum >= 50) {
                            priorityText = 'MEDIUM';
                            priorityColor = '#ffaa00';
                        } else {
                            priorityText = 'LOW';
                            priorityColor = '#94a3b8';
                        }
                    }
                } catch (e) {}
            }

            // Top model features from ExplainableAI
            const xaiEngine = (typeof ExplainableAI !== 'undefined') ? ExplainableAI : (typeof window !== 'undefined' ? window.ExplainableAI : null);
            if (xaiEngine && typeof xaiEngine.explainProspectivityScore === 'function' && liveScoreNum !== null) {
                try {
                    const exp = xaiEngine.explainProspectivityScore(liveScoreNum);
                    if (exp && exp.waterfallSteps) {
                        const feats = exp.waterfallSteps.filter(s => !s.isBaseline && !s.isFinal).slice(0, 3);
                        if (feats.length > 0) {
                            topEvidenceBullets = feats.map(f => {
                                const sign = f.value >= 0 ? '+' : '';
                                return `<li>• <strong>${f.name}</strong> <span class="cyan" style="font-family:monospace;">(${sign}${f.value.toFixed(1)}%)</span></li>`;
                            }).join('');
                        }
                    }
                } catch (_) {}
            }

            // Check matching candidate zone (optional property)
            let candidateZone = null;
            if (resolved && resolved.candidateZone) {
                candidateZone = resolved.candidateZone;
            } else if (typeof ZoneAnalysis !== 'undefined' && typeof ZoneAnalysis.findZoneAtCoordinates === 'function') {
                candidateZone = ZoneAnalysis.findZoneAtCoordinates(lat, lon, 0.5);
            }
            state.candidateZone = candidateZone;

            // Selected marker popup matching Requirement 12 & UX Correction
            selectedMarker.bindPopup(`
                <div class="zone-popup glass-card" style="min-width:260px;">
                    <div class="popup-header" style="margin-bottom:6px; display:flex; justify-content:space-between; align-items:center;">
                        <span class="popup-badge" style="background:linear-gradient(135deg,#00f0ff,#7b2fff);color:#030816;font-weight:800;letter-spacing:1.2px;">TARGET</span>
                        <span style="font-size:0.68rem; color:var(--cyan); font-weight:700;">Manganese</span>
                    </div>
                    <div class="popup-body">
                        <div style="font-size:0.92rem; font-weight:800; color:#fff; margin-bottom:2px;">${placeTitle}</div>
                        ${subArea ? `<div style="font-size:0.7rem; color:var(--text-dim); margin-bottom:8px;">${subArea}</div>` : ''}
                        <div class="popup-row">
                            <span class="p-label">Mineral:</span>
                            <span class="p-val" style="color:var(--cyan); font-weight:700;">Manganese</span>
                        </div>
                        <div class="popup-row">
                            <span class="p-label">Prospectivity:</span>
                            <span class="p-val font-mono bold" style="color:var(--cyan); font-weight:700;">${liveScoreText}</span>
                        </div>
                        <div class="popup-row">
                            <span class="p-label">Priority:</span>
                            <span class="p-val bold" style="color:${priorityColor}; font-weight:700;">${priorityText}</span>
                        </div>
                        <div class="popup-row">
                            <span class="p-label">Candidate Zone:</span>
                            <span class="p-val" style="color:${candidateZone ? 'var(--cyan)' : 'var(--text-dim)'}; font-weight:700;">${candidateZone ? (candidateZone.zoneId ? 'Zone ' + candidateZone.zoneId : candidateZone.name) : 'NONE'}</span>
                        </div>
                        <div class="popup-evidence-box">
                            <div class="popup-evidence-title">Top Evidence:</div>
                            <ul class="popup-evidence-list" style="list-style:none; padding-left:0; margin:0 0 6px 0;">
                                ${topEvidenceBullets}
                            </ul>
                        </div>
                        <div class="popup-row" style="margin-top:4px;">
                            <span class="p-label">Validation:</span>
                            <span class="p-val" style="color:#38bdf8; font-weight:600; font-size:0.7rem;">WITHIN-STUDY</span>
                        </div>
                        <div class="popup-row">
                            <span class="p-label">Independent Validation:</span>
                            <span class="p-val" style="color:#f87171; font-weight:700; font-size:0.68rem;">NOT AVAILABLE</span>
                        </div>
                        <div style="display:flex; flex-direction:column; gap:5px; margin-top:10px;">
                            <div style="display:flex; gap:5px;">
                                <button class="popup-btn" style="flex:1;background:linear-gradient(135deg,#00f0ff,#7b2fff);color:#fff;" onclick="if(typeof navigateTo==='function')navigateTo('dashboard');setTimeout(()=>{document.getElementById('dash-evidence-panel')?.scrollIntoView({behavior:'smooth'});},200);">
                                    VIEW EVIDENCE
                                </button>
                                <button class="popup-btn" style="flex:1;background:rgba(255,255,255,0.08);color:var(--cyan);border:1px solid rgba(0,240,255,0.3);" onclick="if(typeof navigateTo==='function')navigateTo('dashboard');setTimeout(()=>{document.getElementById('dash-ranking-panel')?.scrollIntoView({behavior:'smooth'});},200);">
                                    COMPARE
                                </button>
                            </div>
                            <button class="popup-btn" style="width:100%;background:rgba(0,240,255,0.12);color:#fff;border:1px solid rgba(0,240,255,0.4);" onclick="if(typeof openTargetReportModal==='function')openTargetReportModal();">
                                EXPORT TARGET REPORT
                            </button>
                        </div>
                    </div>
                </div>
            `, { className: 'custom-leaflet-popup', maxWidth: 320 });

            // Update or create radius circle
            const radiusMeters = state.radiusKm * 1000;
            const circleColor = isInside ? '#00f0ff' : '#ff4444';
            if (!radiusCircle) {
                radiusCircle = L.circle([lat, lon], {
                    radius: radiusMeters,
                    color: circleColor,
                    weight: 2,
                    dashArray: '8, 6',
                    fillColor: circleColor,
                    fillOpacity: 0.12
                }).addTo(map);
            } else {
                radiusCircle.setLatLng([lat, lon]);
                radiusCircle.setRadius(radiusMeters);
                radiusCircle.setStyle({
                    color: circleColor,
                    fillColor: circleColor
                });
            }
        }

        // Update UI statistics and trigger listeners
        updateZonesInRadius();
        updateLiveProspectivityCard(lat, lon, state.radiusKm);
        notifyLocationChange();
    }

    /**
     * Resets the live prospectivity card and coordinates readout to the neutral awaiting-target state.
     */
    function resetLiveProspectivityCard() {
        if (typeof document === 'undefined') return;
        const scoreNum = document.getElementById('map-score-number');
        const classTag = document.getElementById('map-classification-tag');
        const meanEl = document.getElementById('map-mean-score');
        const maxEl = document.getElementById('map-max-score');
        const minEl = document.getElementById('map-min-score');
        const zonesEl = document.getElementById('map-nearby-zones-count');
        const mapSpectral = document.getElementById('map-spectral-status');
        const statusBadge = document.getElementById('map-target-status');
        const coordsEl = document.getElementById('map-coordinates');

        // Target place cards
        const mapPlaceName = document.getElementById('map-place-name');
        const mapPlaceSub = document.getElementById('map-place-subarea');
        if (mapPlaceName) mapPlaceName.textContent = 'No Target Selected';
        if (mapPlaceSub) mapPlaceSub.textContent = 'Click the map or search for a location';

        const dashPlaceName = document.getElementById('target-place-name');
        const dashPlaceSub = document.getElementById('target-place-subarea');
        const dashCoordsDisp = document.getElementById('target-coords-display');
        if (dashPlaceName) dashPlaceName.textContent = 'No Target Selected';
        if (dashPlaceSub) dashPlaceSub.textContent = 'Click the map or search for a location';
        if (dashCoordsDisp) {
            dashCoordsDisp.textContent = '';
            dashCoordsDisp.style.display = 'none';
        }

        if (scoreNum) scoreNum.textContent = '—';
        if (classTag) {
            classTag.textContent = 'Awaiting Target';
            classTag.style.background = 'rgba(255, 255, 255, 0.08)';
            classTag.style.color = 'var(--text-dim)';
            classTag.style.borderColor = 'rgba(255, 255, 255, 0.15)';
        }
        if (meanEl) meanEl.textContent = '—';
        if (maxEl) maxEl.textContent = '—';
        if (minEl) minEl.textContent = '—';
        if (zonesEl) zonesEl.textContent = '—';
        if (mapSpectral) {
            mapSpectral.textContent = 'Awaiting Target';
            mapSpectral.style.color = 'var(--text-dim)';
        }
        if (statusBadge) {
            statusBadge.textContent = 'Click map or choose preset';
            statusBadge.className = 'target-tile-status';
            statusBadge.style.color = 'var(--text-dim)';
        }
        if (coordsEl) {
            coordsEl.innerHTML = '<span>Click anywhere on map to select exploration target</span>';
        }
    }

    /**
     * Updates the live prospectivity card and coordinate input fields in the map sidebar.
     * 
     * @param {number} lat - Target latitude
     * @param {number} lon - Target longitude
     * @param {number} radiusKm - Analysis radius
     */
    function updateLiveProspectivityCard(lat, lon, radiusKm) {
        if (typeof document === 'undefined') return;

        // Keep map sidebar inputs in sync
        const mapLatInp = document.getElementById('map-lat-input');
        const mapLonInp = document.getElementById('map-lon-input');
        if (mapLatInp && Math.abs(parseFloat(mapLatInp.value) - lat) > 0.0001) mapLatInp.value = lat.toFixed(4);
        if (mapLonInp && Math.abs(parseFloat(mapLonInp.value) - lon) > 0.0001) mapLonInp.value = lon.toFixed(4);

        // Keep dashboard target coordinates in sync
        const dashLatInp = document.getElementById('target-lat-input');
        const dashLonInp = document.getElementById('target-lon-input');
        if (dashLatInp && Math.abs(parseFloat(dashLatInp.value) - lat) > 0.0001) dashLatInp.value = lat.toFixed(4);
        if (dashLonInp && Math.abs(parseFloat(dashLonInp.value) - lon) > 0.0001) dashLonInp.value = lon.toFixed(4);

        // Update target place name card
        const resolved = state.resolvedPlace;
        const pName = resolved ? resolved.placeName : (state.locationName || 'Selected Target');
        const pSub = resolved ? (resolved.subArea || '') : '';

        const mapPlaceName = document.getElementById('map-place-name');
        const mapPlaceSub = document.getElementById('map-place-subarea');
        if (mapPlaceName) mapPlaceName.textContent = pName;
        if (mapPlaceSub) mapPlaceSub.textContent = pSub || `${lat.toFixed(4)}°N, ${lon.toFixed(4)}°E`;

        const dashPlaceName = document.getElementById('target-place-name');
        const dashPlaceSub = document.getElementById('target-place-subarea');
        const dashCoordsDisp = document.getElementById('target-coords-display');
        if (dashPlaceName) dashPlaceName.textContent = pName;
        if (dashPlaceSub) dashPlaceSub.textContent = pSub || 'Exploration Footprint';
        if (dashCoordsDisp) {
            dashCoordsDisp.textContent = `${lat.toFixed(4)}° N  •  ${lon.toFixed(4)}° E`;
            dashCoordsDisp.style.display = 'block';
        }

        const isInside = GeoEngine ? GeoEngine.isWithinTileBounds(lat, lon) : true;
        const statusBadge = document.getElementById('map-target-status');
        if (statusBadge) {
            if (isInside) {
                statusBadge.textContent = '✓ Inside Tile T44QMK';
                statusBadge.className = 'target-tile-status in-bounds';
            } else {
                statusBadge.textContent = '⚠ Outside Sentinel-2 Tile';
                statusBadge.className = 'target-tile-status out-of-bounds';
            }
        }

        const scoreNum = document.getElementById('map-score-number');
        const classTag = document.getElementById('map-classification-tag');
        const meanEl = document.getElementById('map-mean-score');
        const maxEl = document.getElementById('map-max-score');
        const minEl = document.getElementById('map-min-score');
        const zonesEl = document.getElementById('map-nearby-zones-count');

        if (!isInside) {
            if (scoreNum) scoreNum.textContent = 'N/A';
            if (classTag) {
                classTag.textContent = 'Outside Analysis Area';
                classTag.style.background = 'rgba(255, 68, 68, 0.2)';
                classTag.style.color = '#ff6b6b';
                classTag.style.borderColor = 'rgba(255, 68, 68, 0.4)';
            }
            if (meanEl) meanEl.textContent = '—';
            if (maxEl) maxEl.textContent = '—';
            if (minEl) minEl.textContent = '—';
            if (zonesEl) zonesEl.textContent = '0 zones';
            return;
        }

        // Use ProspectivityEngine to obtain authoritative statistics
        const engine = (typeof ProspectivityEngine !== 'undefined') ? ProspectivityEngine : (typeof window !== 'undefined' ? window.ProspectivityEngine : null);
        if (engine && typeof engine.analyzeLocationSync === 'function') {
            try {
                const res = engine.analyzeLocationSync(lat, lon, radiusKm);
                if (res && res.insideRaster) {
                    if (scoreNum) scoreNum.textContent = `${res.prospectivityPercent}%`;
                    if (classTag) {
                        classTag.textContent = `${res.classification} Potential`;
                        if (res.classification === 'Very High') {
                            classTag.style.background = 'rgba(255, 0, 85, 0.25)';
                            classTag.style.color = '#ff0055';
                            classTag.style.borderColor = 'rgba(255, 0, 85, 0.5)';
                        } else if (res.classification === 'High') {
                            classTag.style.background = 'rgba(255, 107, 53, 0.25)';
                            classTag.style.color = '#ff6b35';
                            classTag.style.borderColor = 'rgba(255, 107, 53, 0.5)';
                        } else if (res.classification === 'Moderate') {
                            classTag.style.background = 'rgba(255, 170, 0, 0.25)';
                            classTag.style.color = '#ffaa00';
                            classTag.style.borderColor = 'rgba(255, 170, 0, 0.5)';
                        } else {
                            classTag.style.background = 'rgba(0, 240, 255, 0.2)';
                            classTag.style.color = '#00f0ff';
                            classTag.style.borderColor = 'rgba(0, 240, 255, 0.4)';
                        }
                    }
                    if (meanEl) meanEl.textContent = `${res.meanPercent}%`;
                    if (maxEl) maxEl.textContent = `${res.maxPercent}%`;
                    if (minEl) minEl.textContent = `${res.minPercent}%`;
                    if (zonesEl) zonesEl.textContent = `${res.nearbyZones ? res.nearbyZones.length : 0} zones`;
                }
            } catch (e) {
                console.warn('[ExplorationMap] Live card update:', e);
            }
        }
    }

    /**
     * Sets up event listeners for the target location preset selector and manual coordinate inputs.
     */
    function setupSidebarControls() {
        if (typeof document === 'undefined') return;

        // Preset dropdown
        const locSelect = document.getElementById('map-location-select');
        if (locSelect) {
            locSelect.addEventListener('change', () => {
                const opt = locSelect.selectedOptions[0];
                if (opt && opt.dataset.lat && opt.dataset.lon) {
                    const pLat = parseFloat(opt.dataset.lat);
                    const pLon = parseFloat(opt.dataset.lon);
                    updateSelectedLocation(pLat, pLon, opt.textContent, 'preset');
                    if (map) map.flyTo([pLat, pLon], 11, { duration: 1.2 });
                }
            });
        }

        // Apply Coords button
        const btnApply = document.getElementById('btn-map-apply-coords');
        if (btnApply) {
            btnApply.addEventListener('click', () => {
                const latInp = document.getElementById('map-lat-input');
                const lonInp = document.getElementById('map-lon-input');
                if (latInp && lonInp) {
                    const vLat = parseFloat(latInp.value);
                    const vLon = parseFloat(lonInp.value);
                    if (!isNaN(vLat) && !isNaN(vLon)) {
                        updateSelectedLocation(vLat, vLon, `Target (${vLat.toFixed(4)}°N, ${vLon.toFixed(4)}°E)`, 'manual');
                        if (map) map.flyTo([vLat, vLon], 11, { duration: 1.0 });
                    }
                }
            });
        }
    }

    /**
     * Builds and attaches the authoritative prospectivity raster heatmap image overlay.
     */
    function setupProspectivityOverlay() {
        if (!map || typeof L === 'undefined' || !GeoEngine || typeof fetch === 'undefined') return;

        const corners = GeoEngine.getTileBoundingBox();
        const south = Math.min(corners.sw.latitude, corners.se.latitude);
        const north = Math.max(corners.nw.latitude, corners.ne.latitude);
        const west = Math.min(corners.nw.longitude, corners.sw.longitude);
        const east = Math.max(corners.ne.longitude, corners.se.longitude);
        const bounds = [[south, west], [north, east]];

        fetch('data/processed/tile_prospectivity_549.json')
            .then(res => res.json())
            .then(data => {
                if (!data || !data.grid) return;
                const rows = data.rows || data.grid.length;
                const cols = data.cols || data.grid[0].length;

                const canvas = document.createElement('canvas');
                canvas.width = cols;
                canvas.height = rows;
                const ctx = canvas.getContext('2d');
                const imgData = ctx.createImageData(cols, rows);

                for (let r = 0; r < rows; r++) {
                    for (let c = 0; c < cols; c++) {
                        const val = data.grid[r][c];
                        const idx = (r * cols + c) * 4;
                        if (val >= 90) { // Very High: Vibrant Magenta
                            imgData.data[idx] = 255; imgData.data[idx+1] = 0; imgData.data[idx+2] = 85; imgData.data[idx+3] = 200;
                        } else if (val >= 75) { // High: Red-Orange
                            imgData.data[idx] = 255; imgData.data[idx+1] = 68; imgData.data[idx+2] = 68; imgData.data[idx+3] = 175;
                        } else if (val >= 50) { // Moderate: Amber
                            imgData.data[idx] = 255; imgData.data[idx+1] = 170; imgData.data[idx+2] = 0; imgData.data[idx+3] = 140;
                        } else if (val >= 25) { // Low: Lime Green
                            imgData.data[idx] = 136; imgData.data[idx+1] = 204; imgData.data[idx+2] = 68; imgData.data[idx+3] = 90;
                        } else { // Very Low: Dim Green transparent
                            imgData.data[idx] = 0; imgData.data[idx+1] = 170; imgData.data[idx+2] = 68; imgData.data[idx+3] = 25;
                        }
                    }
                }
                ctx.putImageData(imgData, 0, 0);

                prospectivityOverlay = L.imageOverlay(canvas.toDataURL(), bounds, {
                    opacity: state.opacity,
                    zIndex: 200
                });

                if (state.activeLayerType === 'prospectivity' && map) {
                    prospectivityOverlay.addTo(map);
                }
            })
            .catch(err => {
                console.warn('[ExplorationMap] Prospectivity overlay note:', err.message);
            });
    }

    /**
     * Handles clicks directly on the map to set a new exploration point.
     * 
     * @param {L.LeafletMouseEvent} e - Map click event
     */
    function handleMapClick(e) {
        const lat = Math.round(e.latlng.lat * 100000) / 100000;
        const lon = Math.round(e.latlng.lng * 100000) / 100000;

        const res = LocationResolver || (typeof window !== 'undefined' ? window.LocationResolver : null);
        const resolved = res && typeof res.reverseGeocode === 'function' ? res.reverseGeocode(lat, lon) : null;
        const locName = resolved ? resolved.fullName : `Target (${lat.toFixed(4)}°N, ${lon.toFixed(4)}°E)`;

        updateSelectedLocation(lat, lon, locName, 'map', resolved);
        if (selectedMarker && map) {
            selectedMarker.openPopup();
        }
    }

    /**
     * Updates coordinate readout in the bottom right corner as cursor moves.
     */
    function handleMapMouseMove(e) {
        const coordsEl = document.getElementById('map-coordinates');
        if (coordsEl) {
            const lat = e.latlng.lat.toFixed(4);
            const lon = e.latlng.lng.toFixed(4);
            coordsEl.innerHTML = `<span>Lat: ${lat}°N</span> <span>Lng: ${lon}°E</span>`;
        }
    }

    /**
     * Counts and highlights candidate zones within the active analysis radius.
     */
    function updateZonesInRadius() {
        if (!MineralData || !MineralData.CANDIDATE_ZONES) return;

        let insideCount = 0;
        let nearestDist = Infinity;
        let nearestZone = null;

        MineralData.CANDIDATE_ZONES.forEach(zone => {
            const dist = GeoEngine ? GeoEngine.haversineDistanceKm(state.lat, state.lon, zone.lat, zone.lon) : 0;
            const isInside = dist <= state.radiusKm;

            if (isInside) {
                insideCount++;
            }

            if (dist < nearestDist) {
                nearestDist = dist;
                nearestZone = zone;
            }
        });

        // Update DOM elements on the map page if they exist
        if (typeof document !== 'undefined') {
            const centerEl = document.querySelector('.map-info .info-value:first-child');
            if (centerEl) centerEl.textContent = `${state.lat.toFixed(4)}°N, ${state.lon.toFixed(4)}°E`;

            const radiusEl = document.querySelector('.map-info .info-row:nth-child(2) .info-value');
            if (radiusEl) radiusEl.textContent = `${state.radiusKm} km`;

            const countEl = document.querySelector('.map-info .info-row:nth-child(3) .info-value');
            if (countEl) countEl.textContent = insideCount;

            // Also update dashboard metric if present
            const dashZonesEl = document.getElementById('dash-candidate-zones');
            if (dashZonesEl) dashZonesEl.textContent = insideCount;
        }

        return { insideCount, nearestDist: nearestDist === Infinity ? null : nearestDist, nearestZone };
    }

    /**
     * Changes the current basemap tile layer.
     * 
     * @param {'prospectivity'|'satellite'|'dark'|'streets'} layerType
     */
    function setBasemapLayer(layerType) {
        if (layerType === 'prospectivity') {
            if (currentBaseLayer !== baseLayers.satellite && baseLayers.satellite) {
                if (map && currentBaseLayer) map.removeLayer(currentBaseLayer);
                currentBaseLayer = baseLayers.satellite;
                if (map) currentBaseLayer.addTo(map);
            }
            if (prospectivityOverlay && map && !map.hasLayer(prospectivityOverlay)) {
                prospectivityOverlay.addTo(map);
            }
            state.activeLayerType = 'prospectivity';
        } else {
            if (prospectivityOverlay && map && map.hasLayer(prospectivityOverlay)) {
                map.removeLayer(prospectivityOverlay);
            }
            if (baseLayers[layerType] && baseLayers[layerType] !== currentBaseLayer) {
                if (map && currentBaseLayer) map.removeLayer(currentBaseLayer);
                currentBaseLayer = baseLayers[layerType];
                if (map) currentBaseLayer.addTo(map);
            }
            state.activeLayerType = layerType;
        }

        // Bring overlays to front
        if (tileBoundsPolygon) tileBoundsPolygon.bringToFront();
        if (radiusCircle) radiusCircle.bringToFront();
        if (selectedMarker) selectedMarker.bringToFront();
    }

    /**
     * Sets the active analysis radius in kilometers.
     * 
     * @param {number} radiusKm - 10, 25, 50, 100
     */
    function setAnalysisRadius(radiusKm) {
        state.radiusKm = Number(radiusKm);
        if (radiusCircle) {
            radiusCircle.setRadius(state.radiusKm * 1000);
        }
        updateZonesInRadius();
        updateLiveProspectivityCard(state.lat, state.lon, state.radiusKm);
        notifyLocationChange();
    }

    /**
     * Toggles visibility of candidate zone markers on the map.
     * 
     * @param {boolean} visible
     */
    function toggleCandidateZones(visible) {
        state.showZones = Boolean(visible);
        if (!zoneMarkersLayer) return;

        if (state.showZones) {
            if (map && !map.hasLayer(zoneMarkersLayer)) map.addLayer(zoneMarkersLayer);
        } else {
            if (map && map.hasLayer(zoneMarkersLayer)) map.removeLayer(zoneMarkersLayer);
        }
    }

    /**
     * Toggles visibility of cartographic place labels and reference tiles.
     * 
     * @param {boolean} visible
     */
    function togglePlaceLabels(visible) {
        state.showLabels = Boolean(visible);
        if (!map) return;
        if (state.showLabels) {
            if (labelsTileLayer && !map.hasLayer(labelsTileLayer)) map.addLayer(labelsTileLayer);
            if (placeMarkersLayer && !map.hasLayer(placeMarkersLayer)) map.addLayer(placeMarkersLayer);
        } else {
            if (labelsTileLayer && map.hasLayer(labelsTileLayer)) map.removeLayer(labelsTileLayer);
            if (placeMarkersLayer && map.hasLayer(placeMarkersLayer)) map.removeLayer(placeMarkersLayer);
        }
    }

    /**
     * Toggles visibility of the Sentinel-2 Tile T44QMK exploration boundary.
     * 
     * @param {boolean} visible
     */
    function toggleTileFootprint(visible) {
        state.showTileFootprint = Boolean(visible);
        if (!tileBoundsPolygon || !map) return;
        if (state.showTileFootprint) {
            if (!map.hasLayer(tileBoundsPolygon)) map.addLayer(tileBoundsPolygon);
        } else {
            if (map && map.hasLayer(tileBoundsPolygon)) map.removeLayer(tileBoundsPolygon);
        }
    }

    /**
     * Toggles visibility of the raster prospectivity heatmap overlay.
     * 
     * @param {boolean} visible
     */
    function toggleProspectivityOverlay(visible) {
        state.showProspectivityOverlay = Boolean(visible);
        if (!prospectivityOverlay || !map) return;
        if (state.showProspectivityOverlay) {
            if (!map.hasLayer(prospectivityOverlay)) map.addLayer(prospectivityOverlay);
        } else {
            if (map && map.hasLayer(prospectivityOverlay)) map.removeLayer(prospectivityOverlay);
        }
    }

    /**
     * Adjusts the opacity of the radius, tile, and prospectivity raster overlays.
     * 
     * @param {number} opacity - 0.0 to 1.0
     */
    function setOverlayOpacity(opacity) {
        state.opacity = opacity;
        if (radiusCircle) {
            radiusCircle.setStyle({ fillOpacity: opacity * 0.2, opacity: opacity });
        }
        if (tileBoundsPolygon) {
            tileBoundsPolygon.setStyle({ fillOpacity: opacity * 0.08, opacity: opacity });
        }
        if (prospectivityOverlay) {
            prospectivityOverlay.setOpacity(opacity);
        }
    }

    /**
     * Flies the map camera smoothly to a specific candidate zone.
     * 
     * @param {number} zoneId
     */
    function flyToZone(zoneId) {
        if (!MineralData || !MineralData.CANDIDATE_ZONES) return;

        const zone = MineralData.CANDIDATE_ZONES.find(z => z.zoneId === Number(zoneId));
        if (zone && map) {
            map.flyTo([zone.lat, zone.lon], 13, { duration: 1.5 });
        }
    }

    /**
     * Flies the map camera smoothly to arbitrary geographic coordinates (place or custom target).
     * 
     * @param {number} lat
     * @param {number} lon
     * @param {number} zoom
     */
    function flyToLocation(lat, lon, zoom = 12) {
        if (map && typeof map.flyTo === 'function') {
            map.flyTo([lat, lon], zoom, { duration: 1.5 });
        }
    }

    /**
     * Resets map view to fit the entire Sentinel-2 T44QMK tile.
     */
    function resetView() {
        if (tileBoundsPolygon && map) {
            map.fitBounds(tileBoundsPolygon.getBounds(), { padding: [20, 20] });
        } else if (map) {
            map.setView([state.lat, state.lon], 10);
        }
    }

    /**
     * Registers a listener callback invoked whenever the user updates the location or radius.
     * 
     * @param {function} callback
     */
    function onLocationChange(callback) {
        if (typeof callback === 'function') {
            locationChangeListeners.push(callback);
        }
    }

    function notifyLocationChange() {
        const stats = state.hasTarget ? updateZonesInRadius() : null;
        const isInside = (state.hasTarget && GeoEngine) ? GeoEngine.isWithinTileBounds(state.lat, state.lon) : false;
        const payload = {
            lat: state.lat,
            lon: state.lon,
            locationName: state.locationName,
            resolvedPlace: state.resolvedPlace,
            radiusKm: state.radiusKm,
            source: state.source || 'preset',
            inTileBounds: isInside,
            hasTarget: !!state.hasTarget,
            zonesInRadius: stats ? stats.insideCount : 0,
            nearestZoneDistKm: stats && stats.nearestDist ? Math.round(stats.nearestDist * 10) / 10 : null
        };

        locationChangeListeners.forEach(cb => {
            try { cb(payload); } catch (e) { console.error(e); }
        });
    }

    /**
     * Toggles optional geological lithology layer if available on disk.
     * When unavailable, stays disabled and logs transparent diagnostic.
     */
    function toggleGeologyLayer(visible) {
        console.info('[ExplorationMap] Geological lithology layer: DATA NOT AVAILABLE');
        return false;
    }

    /**
     * Toggles optional structural faults/lineaments layer if available on disk.
     */
    function toggleStructuresLayer(visible) {
        console.info('[ExplorationMap] Geological structural layer: DATA NOT AVAILABLE');
        return false;
    }

    /**
     * Toggles optional Digital Elevation Model (DEM) / Slope layer if available on disk.
     */
    function toggleTerrainLayer(visible) {
        console.info('[ExplorationMap] Terrain DEM/Slope layer: DATA NOT AVAILABLE');
        return false;
    }

    // Public API interface
    const publicApi = {
        init,
        setLocation: (lat, lon, name, source) => updateSelectedLocation(lat, lon, name, source || 'manual'),
        selectZoneLocation: (lat, lon, zoneName) => updateSelectedLocation(lat, lon, zoneName, 'zone'),
        setRadius: setAnalysisRadius,
        setBasemapLayer,
        toggleCandidateZones,
        togglePlaceLabels,
        toggleTileFootprint,
        toggleProspectivityOverlay,
        toggleGeologyLayer,
        toggleStructuresLayer,
        toggleTerrainLayer,
        setOverlayOpacity,
        flyToZone,
        flyToLocation,
        resetView,
        zoomIn: () => map && map.zoomIn(),
        zoomOut: () => map && map.zoomOut(),
        onLocationChange,
        getState: () => ({ ...state }),
        getResolvedPlace: () => state.resolvedPlace,
        hasTarget: () => !!state.hasTarget,
        getTargetCoordinates: () => (state.hasTarget ? { lat: state.lat, lon: state.lon } : null)
    };

    return publicApi;
}));
