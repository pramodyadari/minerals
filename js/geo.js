/**
 * ============================================================================
 * AI MINERAL INTELLIGENCE — GEOSPATIAL & COORDINATE CONVERSION ENGINE
 * ============================================================================
 * 
 * Module: GeoEngine (js/geo.js)
 * 
 * Purpose:
 *   Provides accurate, bidirectional coordinate transformations between:
 *     1. WGS84 Geographic Coordinates (Latitude, Longitude in decimal degrees - EPSG:4326)
 *     2. Sentinel-2 Projected Coordinates (UTM Zone 44N Easting, Northing in meters - EPSG:32644)
 *     3. Sentinel-2 L2A Raster Pixels (Row, Column in 20m grid)
 *     4. Geodesic surface distances using Haversine spherical trigonometry (in km)
 * 
 * Coordinate Reference System (CRS) Details:
 *   - Name: WGS 84 / UTM zone 44N
 *   - EPSG Code: 32644
 *   - Projection: Transverse Mercator
 *   - Central Meridian: 81°00'00" E (Zone 44)
 *   - Scale Factor on Central Meridian (k0): 0.9996
 *   - False Easting: 500,000.0 meters
 *   - False Northing: 0.0 meters (Northern Hemisphere)
 *   - Reference Ellipsoid: WGS 84 (a = 6378137.0 m, 1/f = 298.257223563)
 * 
 * Sentinel-2 Tile T44QMK Raster Transform Details:
 *   - Upper-Left X (West boundary / Left Easting): 399,960.0 meters
 *   - Upper-Left Y (North boundary / Top Northing): 2,500,020.0 meters
 *   - Pixel Size (Ground Sampling Distance): 20.0 meters per pixel
 *   - Raster Dimensions: 5,490 pixels wide × 5,490 pixels high
 *   - Lower-Right X (East boundary): 399,960.0 + (5,490 × 20) = 509,760.0 meters
 *   - Lower-Right Y (South boundary): 2,500,020.0 - (5,490 × 20) = 2,390,220.0 meters
 * 
 * Why this matters:
 *   Computer screens and 3D graphs use Cartesian coordinates (X, Y, Z), whereas
 *   maps and satellites use geographic angles (Latitude, Longitude) or projected
 *   grid coordinates (Easting, Northing). This engine guarantees that:
 *     - 1 pixel on the 3D surface = exactly 20 meters on Earth.
 *     - X-axis in 3D is projected Easting (meters), NOT arbitrary "Raster X".
 *     - Y-axis in 3D is projected Northing (meters), NOT arbitrary "Raster Y".
 *     - Coordinates on the 2D map match the exact Sentinel-2 pixel in the ML model.
 * ============================================================================
 */

(function (root, factory) {
    if (typeof define === 'function' && define.amd) {
        define([], factory);
    } else if (typeof module === 'object' && module.exports) {
        module.exports = factory();
    } else {
        root.GeoEngine = factory();
    }
}(typeof self !== 'undefined' ? self : this, function () {
    'use strict';

    // ------------------------------------------------------------------------
    // 1. CONSTANTS & ELLIPSOID PARAMETERS (WGS 84)
    // ------------------------------------------------------------------------
    const WGS84 = {
        // Semi-major axis of the Earth (equatorial radius) in meters
        a: 6378137.0,
        // Flattening factor of the Earth
        f: 1.0 / 298.257223563,
        // Semi-minor axis (polar radius) in meters: b = a * (1 - f)
        b: 6356752.314245,
        // First eccentricity squared: e^2 = 2f - f^2
        e2: 0.00669437999014,
        // Second eccentricity squared: e'^2 = (a^2 - b^2) / b^2 = e^2 / (1 - e^2)
        ePrime2: 0.00673949674228,
        // Mean Earth radius for Haversine distance calculations in kilometers
        meanRadiusKm: 6371.0088
    };

    // ------------------------------------------------------------------------
    // 2. UTM ZONE 44N PARAMETERS (EPSG:32644)
    // ------------------------------------------------------------------------
    const UTM_ZONE_44N = {
        epsg: 32644,
        zoneNumber: 44,
        // Central meridian of Zone 44 is 81° E
        centralMeridianDeg: 81.0,
        centralMeridianRad: 81.0 * (Math.PI / 180.0),
        // Standard UTM scale reduction factor on the central meridian
        k0: 0.9996,
        // False Easting shifts coordinates so all Eastings in the zone are positive
        falseEasting: 500000.0,
        // False Northing is 0 for northern hemisphere
        falseNorthing: 0.0
    };

    // ------------------------------------------------------------------------
    // 3. SENTINEL-2 T44QMK RASTER TRANSFORM (20m Pixel Grid)
    // ------------------------------------------------------------------------
    const RASTER_GRID = {
        tileId: "T44QMK",
        crs: "EPSG:32644",
        pixelSizeMeters: 20.0,
        widthPixels: 5490,
        heightPixels: 5490,
        
        // Raster top-left corner coordinates (UTM Zone 44N meters)
        originX: 399960.0, // Left (West)
        originY: 2500020.0, // Top (North)
        
        // Raster bottom-right corner coordinates (UTM Zone 44N meters)
        maxX: 509760.0, // 399960.0 + 5490 * 20.0
        minY: 2390220.0  // 2500020.0 - 5490 * 20.0
    };

    // ------------------------------------------------------------------------
    // 4. COORDINATE CONVERSION: WGS84 (Lat, Lon) -> UTM Zone 44N (Easting, Northing)
    // ------------------------------------------------------------------------
    /**
     * Converts WGS84 Geographic Coordinates (Latitude, Longitude) into
     * projected UTM Zone 44N coordinates (Easting, Northing) in meters.
     * 
     * Uses the Transverse Mercator formulation (Krüger / Redfearn series).
     * Accuracy: Sub-millimeter across the Sentinel-2 tile extent.
     * 
     * @param {number} lat - Latitude in decimal degrees (e.g., 21.9455)
     * @param {number} lon - Longitude in decimal degrees (e.g., 80.4295)
     * @returns {{ easting: number, northing: number, zone: number, hemisphere: string }}
     */
    function wgs84ToUtm44N(lat, lon) {
        if (typeof lat !== 'number' || typeof lon !== 'number' || isNaN(lat) || isNaN(lon)) {
            throw new Error(`Invalid WGS84 input coordinates: lat=${lat}, lon=${lon}`);
        }

        const phi = lat * (Math.PI / 180.0);
        const lambda = lon * (Math.PI / 180.0);
        const lambda0 = UTM_ZONE_44N.centralMeridianRad;

        const a = WGS84.a;
        const e2 = WGS84.e2;
        const ePrime2 = WGS84.ePrime2;
        const k0 = UTM_ZONE_44N.k0;

        const deltaLambda = lambda - lambda0;

        const sinPhi = Math.sin(phi);
        const cosPhi = Math.cos(phi);
        const tanPhi = Math.tan(phi);

        // Radius of curvature in the prime vertical: N = a / sqrt(1 - e^2 * sin^2(phi))
        const N = a / Math.sqrt(1.0 - e2 * sinPhi * sinPhi);

        const T = tanPhi * tanPhi;
        const C = ePrime2 * cosPhi * cosPhi;
        const A = cosPhi * deltaLambda;

        // Meridian distance M (arc length along the meridian from the equator to latitude phi)
        const M = a * (
            (1.0 - e2 / 4.0 - 3.0 * e2 * e2 / 64.0 - 5.0 * Math.pow(e2, 3) / 256.0) * phi
            - (3.0 * e2 / 8.0 + 3.0 * e2 * e2 / 32.0 + 45.0 * Math.pow(e2, 3) / 1024.0) * Math.sin(2.0 * phi)
            + (15.0 * e2 * e2 / 256.0 + 45.0 * Math.pow(e2, 3) / 1024.0) * Math.sin(4.0 * phi)
            - (35.0 * Math.pow(e2, 3) / 3072.0) * Math.sin(6.0 * phi)
        );

        // Easting calculation
        const A3 = Math.pow(A, 3);
        const A5 = Math.pow(A, 5);
        const easting = UTM_ZONE_44N.falseEasting + k0 * N * (
            A
            + (1.0 - T + C) * A3 / 6.0
            + (5.0 - 18.0 * T + T * T + 72.0 * C - 58.0 * ePrime2) * A5 / 120.0
        );

        // Northing calculation
        const A2 = Math.pow(A, 2);
        const A4 = Math.pow(A, 4);
        const A6 = Math.pow(A, 6);
        const northing = UTM_ZONE_44N.falseNorthing + k0 * (
            M + N * tanPhi * (
                A2 / 2.0
                + (5.0 - T + 9.0 * C + 4.0 * C * C) * A4 / 24.0
                + (61.0 - 58.0 * T + T * T + 600.0 * C - 330.0 * ePrime2) * A6 / 720.0
            )
        );

        return {
            easting: Math.round(easting * 1000) / 1000,
            northing: Math.round(northing * 1000) / 1000,
            zone: UTM_ZONE_44N.zoneNumber,
            hemisphere: 'N'
        };
    }

    // ------------------------------------------------------------------------
    // 5. COORDINATE CONVERSION: UTM Zone 44N (Easting, Northing) -> WGS84 (Lat, Lon)
    // ------------------------------------------------------------------------
    /**
     * Converts projected UTM Zone 44N coordinates (Easting, Northing in meters)
     * back into WGS84 Geographic Coordinates (Latitude, Longitude in decimal degrees).
     * 
     * @param {number} easting - UTM Easting in meters (e.g., 441089.33)
     * @param {number} northing - UTM Northing in meters (e.g., 2426904.20)
     * @returns {{ latitude: number, longitude: number }}
     */
    function utm44NToWgs84(easting, northing) {
        if (typeof easting !== 'number' || typeof northing !== 'number' || isNaN(easting) || isNaN(northing)) {
            throw new Error(`Invalid UTM input coordinates: easting=${easting}, northing=${northing}`);
        }

        const a = WGS84.a;
        const e2 = WGS84.e2;
        const ePrime2 = WGS84.ePrime2;
        const k0 = UTM_ZONE_44N.k0;
        const lambda0 = UTM_ZONE_44N.centralMeridianRad;

        const x = easting - UTM_ZONE_44N.falseEasting;
        const y = northing - UTM_ZONE_44N.falseNorthing;

        // Footprint latitude: the latitude of the point on the central meridian at distance M = y / k0
        const M = y / k0;
        const mu = M / (a * (1.0 - e2 / 4.0 - 3.0 * e2 * e2 / 64.0 - 5.0 * Math.pow(e2, 3) / 256.0));

        const e1 = (1.0 - Math.sqrt(1.0 - e2)) / (1.0 + Math.sqrt(1.0 - e2));

        // Footprint latitude phi1
        const phi1 = mu
            + (3.0 * e1 / 2.0 - 27.0 * Math.pow(e1, 3) / 32.0) * Math.sin(2.0 * mu)
            + (21.0 * e1 * e1 / 16.0 - 55.0 * Math.pow(e1, 4) / 32.0) * Math.sin(4.0 * mu)
            + (151.0 * Math.pow(e1, 3) / 96.0) * Math.sin(6.0 * mu)
            + (1097.0 * Math.pow(e1, 4) / 512.0) * Math.sin(8.0 * mu);

        const sinPhi1 = Math.sin(phi1);
        const cosPhi1 = Math.cos(phi1);
        const tanPhi1 = Math.tan(phi1);

        const N1 = a / Math.sqrt(1.0 - e2 * sinPhi1 * sinPhi1);
        const R1 = a * (1.0 - e2) / Math.pow(1.0 - e2 * sinPhi1 * sinPhi1, 1.5);
        const D = x / (N1 * k0);

        const T1 = tanPhi1 * tanPhi1;
        const C1 = ePrime2 * cosPhi1 * cosPhi1;

        const D2 = Math.pow(D, 2);
        const D3 = Math.pow(D, 3);
        const D4 = Math.pow(D, 4);
        const D5 = Math.pow(D, 5);
        const D6 = Math.pow(D, 6);

        // Latitude in radians
        const latRad = phi1 - (N1 * tanPhi1 / R1) * (
            D2 / 2.0
            - (5.0 + 3.0 * T1 + 10.0 * C1 - 4.0 * C1 * C1 - 9.0 * ePrime2) * D4 / 24.0
            + (61.0 + 90.0 * T1 + 298.0 * C1 + 45.0 * T1 * T1 - 252.0 * ePrime2 - 3.0 * C1 * C1) * D6 / 720.0
        );

        // Longitude in radians
        const lonRad = lambda0 + (
            D
            - (1.0 + 2.0 * T1 + C1) * D3 / 6.0
            + (5.0 - 2.0 * C1 + 28.0 * T1 - 3.0 * C1 * C1 + 8.0 * ePrime2 + 24.0 * T1 * T1) * D5 / 120.0
        ) / cosPhi1;

        const latDeg = latRad * (180.0 / Math.PI);
        const lonDeg = lonRad * (180.0 / Math.PI);

        return {
            latitude: Math.round(latDeg * 1000000) / 1000000,
            longitude: Math.round(lonDeg * 1000000) / 1000000
        };
    }

    // ------------------------------------------------------------------------
    // 6. RASTER COORDINATE TRANSFORM (UTM Zone 44N <-> 20m Grid Pixel Row/Col)
    // ------------------------------------------------------------------------
    /**
     * Converts projected UTM Easting and Northing (meters) to 20m raster grid indices.
     * 
     * Sentinel-2 affine matrix:
     *   col = (Easting - OriginX) / PixelSize
     *   row = (OriginY - Northing) / PixelSize
     * 
     * @param {number} easting - UTM Easting in meters
     * @param {number} northing - UTM Northing in meters
     * @returns {{ row: number, col: number, exactRow: number, exactCol: number, inBounds: boolean }}
     */
    function utmToRasterPixel(easting, northing) {
        const exactCol = (easting - RASTER_GRID.originX) / RASTER_GRID.pixelSizeMeters;
        const exactRow = (RASTER_GRID.originY - northing) / RASTER_GRID.pixelSizeMeters;

        const col = Math.floor(exactCol);
        const row = Math.floor(exactRow);

        const inBounds = (
            col >= 0 &&
            col < RASTER_GRID.widthPixels &&
            row >= 0 &&
            row < RASTER_GRID.heightPixels
        );

        return {
            row: row,
            col: col,
            exactRow: Math.round(exactRow * 1000) / 1000,
            exactCol: Math.round(exactCol * 1000) / 1000,
            inBounds: inBounds
        };
    }

    /**
     * Converts raster pixel grid indices (Row, Column) into projected UTM Easting and Northing.
     * 
     * @param {number} row - Raster row index (0 to 5489)
     * @param {number} col - Raster column index (0 to 5489)
     * @param {'center'|'corner'} offset - 'center' returns pixel center (+0.5), 'corner' returns upper-left
     * @returns {{ easting: number, northing: number }}
     */
    function rasterPixelToUtm(row, col, offset = 'center') {
        const delta = (offset === 'center') ? 0.5 : 0.0;
        const easting = RASTER_GRID.originX + (col + delta) * RASTER_GRID.pixelSizeMeters;
        const northing = RASTER_GRID.originY - (row + delta) * RASTER_GRID.pixelSizeMeters;

        return {
            easting: Math.round(easting * 1000) / 1000,
            northing: Math.round(northing * 1000) / 1000
        };
    }

    /**
     * End-to-end forward transform: WGS84 (Lat, Lon) -> Raster Pixel (Row, Col)
     * 
     * @param {number} lat - Latitude
     * @param {number} lon - Longitude
     * @returns {{ row: number, col: number, exactRow: number, exactCol: number, easting: number, northing: number, inBounds: boolean }}
     */
    function wgs84ToRasterPixel(lat, lon) {
        const utm = wgs84ToUtm44N(lat, lon);
        const pixel = utmToRasterPixel(utm.easting, utm.northing);

        return {
            row: pixel.row,
            col: pixel.col,
            exactRow: pixel.exactRow,
            exactCol: pixel.exactCol,
            easting: utm.easting,
            northing: utm.northing,
            inBounds: pixel.inBounds
        };
    }

    /**
     * End-to-end reverse transform: Raster Pixel (Row, Col) -> WGS84 (Lat, Lon)
     * 
     * @param {number} row - Raster row index
     * @param {number} col - Raster column index
     * @param {'center'|'corner'} offset - Pixel alignment ('center' default)
     * @returns {{ latitude: number, longitude: number, easting: number, northing: number }}
     */
    function rasterPixelToWgs84(row, col, offset = 'center') {
        const utm = rasterPixelToUtm(row, col, offset);
        const wgs84 = utm44NToWgs84(utm.easting, utm.northing);

        return {
            latitude: wgs84.latitude,
            longitude: wgs84.longitude,
            easting: utm.easting,
            northing: utm.northing
        };
    }

    // ------------------------------------------------------------------------
    // 7. BOUNDS & COVERAGE VERIFICATION
    // ------------------------------------------------------------------------
    /**
     * Checks if a given geographic location falls within the Sentinel-2 T44QMK footprint.
     * 
     * @param {number} lat - Latitude
     * @param {number} lon - Longitude
     * @returns {boolean}
     */
    function isWithinTileBounds(lat, lon) {
        try {
            const utm = wgs84ToUtm44N(lat, lon);
            return (
                utm.easting >= RASTER_GRID.originX &&
                utm.easting <= RASTER_GRID.maxX &&
                utm.northing >= RASTER_GRID.minY &&
                utm.northing <= RASTER_GRID.originY
            );
        } catch {
            return false;
        }
    }

    /**
     * Returns the 4 geographic corner coordinates of the Sentinel-2 Tile T44QMK footprint.
     * Useful for rendering bounding box outlines on Leaflet maps.
     * 
     * @returns {{ nw: {lat: number, lon: number}, ne: {lat: number, lon: number}, se: {lat: number, lon: number}, sw: {lat: number, lon: number} }}
     */
    function getTileBoundingBox() {
        const nw = utm44NToWgs84(RASTER_GRID.originX, RASTER_GRID.originY);
        const ne = utm44NToWgs84(RASTER_GRID.maxX, RASTER_GRID.originY);
        const se = utm44NToWgs84(RASTER_GRID.maxX, RASTER_GRID.minY);
        const sw = utm44NToWgs84(RASTER_GRID.originX, RASTER_GRID.minY);

        return { nw, ne, se, sw };
    }

    // ------------------------------------------------------------------------
    // 8. GEODESIC DISTANCE (Haversine Formula)
    // ------------------------------------------------------------------------
    /**
     * Calculates the great-circle distance between two geographic points in kilometers.
     * 
     * @param {number} lat1 - Point 1 Latitude
     * @param {number} lon1 - Point 1 Longitude
     * @param {number} lat2 - Point 2 Latitude
     * @param {number} lon2 - Point 2 Longitude
     * @returns {number} Distance in kilometers rounded to 3 decimal places
     */
    function haversineDistanceKm(lat1, lon1, lat2, lon2) {
        const R = WGS84.meanRadiusKm;

        const phi1 = lat1 * (Math.PI / 180.0);
        const phi2 = lat2 * (Math.PI / 180.0);
        const deltaPhi = (lat2 - lat1) * (Math.PI / 180.0);
        const deltaLambda = (lon2 - lon1) * (Math.PI / 180.0);

        const a = Math.sin(deltaPhi / 2.0) * Math.sin(deltaPhi / 2.0) +
                  Math.cos(phi1) * Math.cos(phi2) *
                  Math.sin(deltaLambda / 2.0) * Math.sin(deltaLambda / 2.0);

        const c = 2.0 * Math.atan2(Math.sqrt(a), Math.sqrt(1.0 - a));

        return Math.round(R * c * 1000) / 1000;
    }

    // ------------------------------------------------------------------------
    // 9. PUBLIC API EXPORT
    // ------------------------------------------------------------------------
    return {
        // Constants & metadata
        WGS84,
        UTM_ZONE_44N,
        RASTER_GRID,

        // Core coordinate transformations
        wgs84ToUtm44N,
        utm44NToWgs84,

        // Raster pixel mappings
        utmToRasterPixel,
        rasterPixelToUtm,
        wgs84ToRasterPixel,
        rasterPixelToWgs84,

        // Spatial bounding & distance helpers
        isWithinTileBounds,
        getTileBoundingBox,
        haversineDistanceKm
    };
}));
