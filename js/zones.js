/**
 * ============================================================================
 * AI MINERAL INTELLIGENCE — CANDIDATE ZONE ANALYSIS MODULE
 * ============================================================================
 * 
 * Module: ZoneAnalysis (js/zones.js)
 * 
 * Purpose:
 *   Manages and evaluates the 20 authoritative high-prospectivity candidate anomaly
 *   zones derived directly from outputs/high_prospectivity_zones.csv:
 *     - Calculates geodesic distance from any selected exploration center.
 *     - Filters candidate zones according to selected analysis radius (10, 25, 50, 100 km).
 *     - Sorts candidate zones by distance ascending.
 *     - Computes standardized prospectivity classification.
 *     - Emits zone selection events to coordinate the 2D Map, 3D Plotly surface,
 *       and telemetry statistics synchronously.
 * ============================================================================
 */

(function (root, factory) {
    if (typeof define === 'function' && define.amd) {
        define(['./geo', './data'], factory);
    } else if (typeof module === 'object' && module.exports) {
        module.exports = factory(require('./geo'), require('./data'));
    } else {
        root.ZoneAnalysis = factory(root.GeoEngine, root.MineralData);
    }
}(typeof self !== 'undefined' ? self : this, function (GeoEngine, MineralData) {
    'use strict';

    let zoneSelectListeners = [];

    /**
     * Standard candidate zone classification
     * High anomaly clusters from Random Forest spatial aggregation
     */
    function classifyZone(score) {
        const val = score > 1.0 ? score / 100.0 : score;
        if (val >= 0.97) return 'Top Priority Anomaly';
        if (val >= 0.95) return 'Very High Prospectivity';
        if (val >= 0.90) return 'High Prospectivity';
        if (val >= 0.75) return 'Moderate Prospectivity';
        return 'Low Prospectivity';
    }

    /**
     * Retrieves all 20 authoritative candidate zones enriched with UTM coordinates
     */
    function getAllZones() {
        if (!MineralData || !MineralData.CANDIDATE_ZONES) {
            return [];
        }
        return MineralData.CANDIDATE_ZONES.map(z => ({
            zoneId: z.zoneId,
            latitude: z.lat,
            longitude: z.lon,
            easting: z.easting,
            northing: z.northing,
            pixels: z.pixels,
            areaHectares: z.areaHectares || (Math.round(z.pixels * 400 / 100) / 100),
            meanScore: z.meanScore,
            meanPercent: Math.round(z.meanScore * 1000) / 10,
            maxScore: z.maxScore,
            maxPercent: Math.round(z.maxScore * 1000) / 10,
            classification: classifyZone(z.meanScore)
        }));
    }

    /**
     * Analyzes candidate zones relative to a selected exploration center and radius
     * 
     * @param {number} centerLat - Latitude of exploration center
     * @param {number} centerLon - Longitude of exploration center
     * @param {number} radiusKm - Analysis radius (10, 25, 50, 100 km)
     * @returns {Array<object>} Filtered and sorted candidate zones
     */
    function getZonesInRadius(centerLat, centerLon, radiusKm = 25) {
        const all = getAllZones();

        const evaluated = all.map(zone => {
            const distanceKm = GeoEngine.haversineDistanceKm(centerLat, centerLon, zone.latitude, zone.longitude);
            return {
                ...zone,
                distanceKm: distanceKm,
                inRadius: distanceKm <= radiusKm
            };
        });

        // Filter by radius and sort by distance ascending
        const filtered = evaluated
            .filter(z => z.inRadius)
            .sort((a, b) => a.distanceKm - b.distanceKm);

        return filtered;
    }

    /**
     * Finds a candidate zone by its unique Zone ID
     */
    function getZoneById(zoneId) {
        const id = Number(zoneId);
        const zones = getAllZones();
        return zones.find(z => z.zoneId === id) || null;
    }

    /**
     * Emits a zone selection event to all registered listeners
     */
    function selectZone(zoneId) {
        const zone = getZoneById(zoneId);
        if (!zone) {
            console.warn(`[ZoneAnalysis] Zone ID ${zoneId} not found.`);
            return null;
        }

        console.log(`[ZoneAnalysis] Candidate Zone ${zoneId} selected at (${zone.latitude}, ${zone.longitude})`);
        zoneSelectListeners.forEach(listener => {
            try {
                listener(zone);
            } catch (err) {
                console.error('[ZoneAnalysis] Error in zone select listener:', err);
            }
        });

        return zone;
    }

    /**
     * Registers a listener callback for zone selection events
     */
    function onZoneSelect(callback) {
        if (typeof callback === 'function') {
            zoneSelectListeners.push(callback);
        }
    }

    /**
     * Formats an HTML table row for a candidate zone
     */
    function renderZoneTableRow(zone, isSelected = false) {
        const badgeClass = zone.meanPercent >= 97 ? 'high' : (zone.meanPercent >= 95 ? 'medium' : 'low');
        const selectedClass = isSelected ? 'selected-zone' : '';

        return `
            <tr class="zone-row ${selectedClass}" data-zone-id="${zone.zoneId}" onclick="ZoneAnalysis.selectZone(${zone.zoneId})">
                <td style="font-weight: 600; color: var(--cyan); font-family: var(--font-display);">#${zone.zoneId}</td>
                <td>${zone.easting.toLocaleString()} m</td>
                <td>${zone.northing.toLocaleString()} m</td>
                <td><span class="score-badge ${badgeClass}">${zone.meanPercent}%</span></td>
                <td>${zone.maxPercent}%</td>
                <td>${zone.distanceKm !== undefined ? zone.distanceKm.toFixed(1) + ' km' : '--'}</td>
                <td><span class="status-badge complete">${zone.classification}</span></td>
                <td>
                    <button class="btn-xs btn-primary btn-select-zone" onclick="event.stopPropagation(); ZoneAnalysis.selectZone(${zone.zoneId})">
                        Explore
                    </button>
                </td>
            </tr>
        `;
    }

    /**
     * Finds if a given coordinate falls within a candidate discovery zone cluster (~0.4 km).
     * @param {number} lat - Latitude
     * @param {number} lon - Longitude
     * @param {number} [maxDistanceKm=0.4] - Cluster matching threshold in km
     * @returns {object|null} Matching candidate zone object or null if none
     */
    function findZoneAtCoordinates(lat, lon, maxDistanceKm = 0.4) {
        if (typeof lat !== 'number' || typeof lon !== 'number' || isNaN(lat) || isNaN(lon)) return null;
        const all = getAllZones();
        let closest = null;
        let minD = Infinity;
        for (const z of all) {
            const d = GeoEngine ? GeoEngine.haversineDistanceKm(lat, lon, z.latitude, z.longitude) : 999;
            if (d <= maxDistanceKm && d < minD) {
                minD = d;
                closest = z;
            }
        }
        return closest;
    }

    return {
        getAllZones,
        getZonesInRadius,
        getZoneById,
        findZoneAtCoordinates,
        selectZone,
        onZoneSelect,
        classifyZone,
        renderZoneTableRow
    };
}));
