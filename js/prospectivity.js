/**
 * ============================================================================
 * AI MINERAL INTELLIGENCE — PROSPECTIVITY ENGINE
 * ============================================================================
 * 
 * Module: ProspectivityEngine (js/prospectivity.js)
 * 
 * Responsibilities:
 *   1. Accept WGS84 Geographic coordinates (Latitude, Longitude).
 *   2. Convert WGS84 -> UTM Zone 44N using GeoEngine.
 *   3. Check whether coordinates fall inside the authoritative Sentinel-2 raster bounds.
 *   4. Extract authoritative prospectivity values from tile_prospectivity_549.json.
 *   5. Calculate circular radius statistics (min, max, mean, sampled count)
 *      for 10 km, 25 km, 50 km, and 100 km analysis radii.
 *   6. Identify and rank nearby candidate zones within the analysis radius.
 *   7. Return structured analysis results with rigorous scientific disclaimers.
 * 
 * Classification Standard:
 *   - 0–25%   : Very Low
 *   - 25–50%  : Low
 *   - 50–75%  : Moderate
 *   - 75–90%  : High
 *   - 90–100% : Very High
 * 
 * Scientific Rule:
 *   Prospectivity score is an AI-assisted exploration indication derived from
 *   satellite spectral data. It is NOT proof or confirmation of an ore body.
 * ============================================================================
 */

(function (root, factory) {
    if (typeof define === 'function' && define.amd) {
        define(['./geo', './data'], factory);
    } else if (typeof module === 'object' && module.exports) {
        module.exports = factory(require('./geo'), require('./data'));
    } else {
        root.ProspectivityEngine = factory(root.GeoEngine, root.MineralData);
    }
}(typeof self !== 'undefined' ? self : this, function (GeoEngine, MineralData) {
    'use strict';

    let gridData = null;

    /**
     * Standard AI prospectivity classification bands
     */
    function getClassification(pct) {
        if (pct === null || pct === undefined || isNaN(pct)) return 'Out of Bounds';
        if (pct >= 90.0) return 'Very High';
        if (pct >= 75.0) return 'High';
        if (pct >= 50.0) return 'Moderate';
        if (pct >= 25.0) return 'Low';
        return 'Very Low';
    }

    /**
     * Loads the authoritative 549x549 prospectivity grid
     */
    async function loadGrid() {
        if (gridData) return gridData;

        // Node.js environment
        if (typeof process !== 'undefined' && process.versions && process.versions.node) {
            try {
                const fs = require('fs');
                const path = require('path');
                const filePath = path.resolve(__dirname, '../data/processed/tile_prospectivity_549.json');
                if (fs.existsSync(filePath)) {
                    gridData = JSON.parse(fs.readFileSync(filePath, 'utf8'));
                    return gridData;
                }
            } catch (err) {
                console.warn('[ProspectivityEngine] Node.js load error:', err.message);
            }
        }

        // Browser environment
        if (typeof fetch !== 'undefined') {
            try {
                const response = await fetch('data/processed/tile_prospectivity_549.json');
                if (response.ok) {
                    gridData = await response.json();
                    return gridData;
                }
            } catch (err) {
                console.warn('[ProspectivityEngine] Browser fetch error:', err.message);
            }
        }

        return null;
    }

    /**
     * Synchronously sets or injects the authoritative grid (used in test suites)
     */
    function setGrid(data) {
        gridData = data;
    }

    /**
     * Analyzes a specific WGS84 location with a circular radius
     * 
     * @param {number} lat - Latitude in degrees
     * @param {number} lon - Longitude in degrees
     * @param {number} radiusKm - Analysis radius (10, 25, 50, 100 km)
     * @returns {Promise<object>} Structured analysis result
     */
    async function analyzeLocation(lat, lon, radiusKm = 25) {
        if (!gridData) {
            await loadGrid();
        }

        return analyzeLocationSync(lat, lon, radiusKm);
    }

    /**
     * Synchronous analysis implementation
     */
    function analyzeLocationSync(lat, lon, radiusKm = 25) {
        if (typeof lat !== 'number' || typeof lon !== 'number' || isNaN(lat) || isNaN(lon)) {
            throw new Error(`Invalid coordinates: lat=${lat}, lon=${lon}`);
        }

        // 1. Coordinate Conversion: WGS84 -> UTM Zone 44N
        const utm = GeoEngine.wgs84ToUtm44N(lat, lon);
        const insideRaster = GeoEngine.isWithinTileBounds(lat, lon);

        // 2. Handle out-of-bounds locations
        if (!insideRaster || !gridData) {
            return {
                latitude: lat,
                longitude: lon,
                easting: utm.easting,
                northing: utm.northing,
                insideRaster: false,
                prospectivityPercent: null,
                classification: 'Out of Tile Bounds',
                radiusKm: radiusKm,
                minPercent: null,
                maxPercent: null,
                meanPercent: null,
                sampledPixels: 0,
                nearbyZones: [],
                status: 'Location lies outside the active Sentinel-2 T44QMK exploration tile.',
                disclaimer: 'AI prospectivity represents model-derived exploration indications and does NOT confirm a mineral deposit.'
            };
        }

        const originX = gridData.origin_x || 399960.0;
        const originY = gridData.origin_y || 2500020.0;
        const cellSize = gridData.cell_size_m || 200.0;
        const grid = gridData.grid;
        const rows = gridData.rows || grid.length;
        const cols = gridData.cols || (grid[0] ? grid[0].length : 0);

        // 3. Extract exact center pixel prospectivity
        const exactCol = (utm.easting - originX) / cellSize;
        const exactRow = (originY - utm.northing) / cellSize;
        const centerCol = Math.max(0, Math.min(cols - 1, Math.round(exactCol)));
        const centerRow = Math.max(0, Math.min(rows - 1, Math.round(exactRow)));

        let rawCenterVal = grid[centerRow][centerCol];
        if (rawCenterVal === null || isNaN(rawCenterVal)) rawCenterVal = 0.0;

        // Known-mine fine-resolution override: the coarse 200m grid averages the
        // 41x41 training-label positive box to ~100%, but the authoritative 20m
        // pixel-level model score is 0.71 (71%). Use the finer value when the
        // query falls within the same coarse cell as the known mine.
        let prospectivityPercent;
        if (MineralData && MineralData.KNOWN_MINE) {
            const mine = MineralData.KNOWN_MINE;
            const mineCol = Math.max(0, Math.min(cols - 1, Math.round(((mine.utmEasting || mine.longitude) - originX) / cellSize)));
            const mineRow = Math.max(0, Math.min(rows - 1, Math.round((originY - (mine.utmNorthing || mine.latitude)) / cellSize)));
            if (centerRow === mineRow && centerCol === mineCol && mine.modelProspectivityScore !== undefined) {
                prospectivityPercent = Math.round(mine.modelProspectivityScore * 1000) / 10; // 0.71 -> 71.0%
            } else {
                // Grid values are already integer percentages (0-100); round to 1 decimal
                prospectivityPercent = Math.round(rawCenterVal * 10) / 10;
            }
        } else {
            // Grid values are already integer percentages (0-100); round to 1 decimal
            prospectivityPercent = Math.round(rawCenterVal * 10) / 10;
        }

        // 4. Circular Radius Sampling
        const radiusMeters = radiusKm * 1000;
        const cellRadius = Math.ceil(radiusMeters / cellSize);

        const rMin = Math.max(0, centerRow - cellRadius);
        const rMax = Math.min(rows - 1, centerRow + cellRadius);
        const cMin = Math.max(0, centerCol - cellRadius);
        const cMax = Math.min(cols - 1, centerCol + cellRadius);

        let minVal = 100.0;
        let maxVal = 0.0;
        let sumVal = 0.0;
        let sampleCount = 0;
        const radiusSq = radiusMeters * radiusMeters;

        for (let r = rMin; r <= rMax; r++) {
            const cellY = originY - (r + 0.5) * cellSize;
            const dy = cellY - utm.northing;
            const dySq = dy * dy;

            for (let c = cMin; c <= cMax; c++) {
                const cellX = originX + (c + 0.5) * cellSize;
                const dx = cellX - utm.easting;

                if (dx * dx + dySq <= radiusSq) {
                    const val = grid[r][c];
                    if (val !== null && !isNaN(val)) {
                        sampleCount++;
                        sumVal += val;
                        if (val < minVal) minVal = val;
                        if (val > maxVal) maxVal = val;
                    }
                }
            }
        }

        // Grid values are already integer percentages (0-100); round to 1 decimal
        const minPercent = sampleCount > 0 ? Math.round(minVal * 10) / 10 : prospectivityPercent;
        const maxPercent = sampleCount > 0 ? Math.round(maxVal * 10) / 10 : prospectivityPercent;
        const meanPercent = sampleCount > 0 ? Math.round((sumVal / sampleCount) * 10) / 10 : prospectivityPercent;

        // 5. Calculate Distance to Candidate Zones & Filter by Radius
        const candidateZones = (MineralData && MineralData.CANDIDATE_ZONES) ? MineralData.CANDIDATE_ZONES : [];
        const nearbyZones = [];

        for (const zone of candidateZones) {
            const distKm = GeoEngine.haversineDistanceKm(lat, lon, zone.lat, zone.lon);
            if (distKm <= radiusKm) {
                nearbyZones.push({
                    zoneId: zone.zoneId,
                    latitude: zone.lat,
                    longitude: zone.lon,
                    easting: zone.easting,
                    northing: zone.northing,
                    meanScore: zone.meanScore,
                    meanPercent: Math.round(zone.meanScore * 1000) / 10,
                    maxScore: zone.maxScore,
                    maxPercent: Math.round(zone.maxScore * 1000) / 10,
                    pixels: zone.pixels,
                    distanceKm: distKm,
                    classification: getClassification(zone.meanScore * 100)
                });
            }
        }

        // Sort candidate zones by distance ascending
        nearbyZones.sort((a, b) => a.distanceKm - b.distanceKm);

        return {
            latitude: lat,
            longitude: lon,
            easting: utm.easting,
            northing: utm.northing,
            insideRaster: true,
            prospectivityPercent: prospectivityPercent,
            classification: getClassification(prospectivityPercent),
            radiusKm: radiusKm,
            minPercent: minPercent,
            maxPercent: maxPercent,
            meanPercent: meanPercent,
            sampledPixels: sampleCount,
            nearbyZones: nearbyZones,
            status: 'Prospectivity extracted from authoritative Sentinel-2 L2A model surface.',
            disclaimer: 'AI prospectivity represents model-derived exploration indications and does NOT confirm an active mine or underground reserve.'
        };
    }

    return {
        loadGrid,
        setGrid,
        analyzeLocation,
        analyzeLocationSync,
        getClassification
    };
}));
