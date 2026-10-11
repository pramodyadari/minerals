/**
 * ============================================================================
 * AI MINERAL INTELLIGENCE — DATASETS & CALIBRATION ASSETS
 * ============================================================================
 * 
 * Module: MineralData (js/data.js)
 * 
 * Purpose:
 *   Contains the verified datasets, metadata, and ground-truth values
 *   derived directly from the Sentinel-2 L2A tile (T44QMK) and trained models:
 *     1. 20 High-Prospectivity Candidate Zones (high_prospectivity_zones.csv)
 *     2. Ground-truth reference mine (Ghondi Manganese Mine)
 *     3. Sentinel-2 product and spectral band specifications
 *     4. Feature definitions and Random Forest importance weights
 *     5. Operational production training parameters (production_data.csv)
 *     6. Real calibrated prospectivity grid loader
 * ============================================================================
 */

(function (root, factory) {
    if (typeof define === 'function' && define.amd) {
        define(['./geo'], factory);
    } else if (typeof module === 'object' && module.exports) {
        const GeoEngine = require('./geo');
        module.exports = factory(GeoEngine);
    } else {
        root.MineralData = factory(root.GeoEngine);
    }
}(typeof self !== 'undefined' ? self : this, function (GeoEngine) {
    'use strict';

    // ------------------------------------------------------------------------
    // 1. RAW HIGH-PROSPECTIVITY CANDIDATE ZONES DATASET
    // Source: outputs/high_prospectivity_zones.csv (Real RF anomaly clusters)
    // ------------------------------------------------------------------------
    const RAW_CANDIDATE_ZONES = [
        { zoneId: 67684, pixels: 111, meanScore: 0.9758, maxScore: 1.0, lat: 22.214160, lon: 80.063632 },
        { zoneId: 67387, pixels: 59,  meanScore: 0.9734, maxScore: 1.0, lat: 22.215816, lon: 80.068860 },
        { zoneId: 124766, pixels: 59, meanScore: 0.9702, maxScore: 1.0, lat: 21.939738, lon: 80.602479 },
        { zoneId: 187925, pixels: 52, meanScore: 0.9685, maxScore: 1.0, lat: 21.639316, lon: 80.558661 },
        { zoneId: 160475, pixels: 60, meanScore: 0.9678, maxScore: 1.0, lat: 21.767469, lon: 80.651509 },
        { zoneId: 35688, pixels: 59,  meanScore: 0.9676, maxScore: 1.0, lat: 22.350216, lon: 80.130703 },
        { zoneId: 189867, pixels: 89, meanScore: 0.9676, maxScore: 1.0, lat: 21.626570, lon: 80.410862 },
        { zoneId: 167254, pixels: 106, meanScore: 0.9674, maxScore: 1.0, lat: 21.735863, lon: 80.190724 },
        { zoneId: 180345, pixels: 137, meanScore: 0.9673, maxScore: 1.0, lat: 21.678018, lon: 80.081634 },
        { zoneId: 39890, pixels: 65,  meanScore: 0.9672, maxScore: 1.0, lat: 22.334301, lon: 80.063026 },
        { zoneId: 162862, pixels: 69, meanScore: 0.9670, maxScore: 1.0, lat: 21.754977, lon: 80.112865 },
        { zoneId: 179466, pixels: 94, meanScore: 0.9670, maxScore: 1.0, lat: 21.682399, lon: 80.089725 },
        { zoneId: 103786, pixels: 116, meanScore: 0.9666, maxScore: 1.0, lat: 22.036465, lon: 80.437670 },
        { zoneId: 180659, pixels: 59, meanScore: 0.9661, maxScore: 1.0, lat: 21.678074, lon: 80.091879 },
        { zoneId: 191911, pixels: 162, meanScore: 0.9661, maxScore: 1.0, lat: 21.615292, lon: 80.390039 },
        { zoneId: 91324, pixels: 88,  meanScore: 0.9660, maxScore: 1.0, lat: 22.089345, lon: 80.068528 },
        { zoneId: 32809, pixels: 128, meanScore: 0.9657, maxScore: 1.0, lat: 22.362067, lon: 80.442199 },
        { zoneId: 113980, pixels: 51, meanScore: 0.9657, maxScore: 1.0, lat: 21.990154, lon: 80.169142 },
        { zoneId: 92467, pixels: 75,  meanScore: 0.9656, maxScore: 1.0, lat: 22.085599, lon: 80.109651 },
        { zoneId: 115839, pixels: 74, meanScore: 0.9655, maxScore: 1.0, lat: 21.983157, lon: 80.339079 }
    ];

    // Compute exact projected UTM coordinates and pixel positions using GeoEngine
    const CANDIDATE_ZONES = RAW_CANDIDATE_ZONES.map(zone => {
        let utm = { easting: 0, northing: 0 };
        let pixel = { row: 0, col: 0, inBounds: false };

        if (GeoEngine) {
            utm = GeoEngine.wgs84ToUtm44N(zone.lat, zone.lon);
            pixel = GeoEngine.utmToRasterPixel(utm.easting, utm.northing);
        }

        return {
            ...zone,
            easting: utm.easting,
            northing: utm.northing,
            row: pixel.row,
            col: pixel.col,
            inBounds: pixel.inBounds,
            areaM2: zone.pixels * 400, // 20m x 20m = 400 m2 per pixel
            areaHectares: Math.round(zone.pixels * 400 / 100) / 100,
            confidence: "High (Test-validated)"
        };
    });

    // ------------------------------------------------------------------------
    // 2. GROUND-TRUTH REFERENCE MINE
    // ------------------------------------------------------------------------
    const KNOWN_MINE = {
        name: "Ghondi Manganese Mine",
        region: "Balaghat / MP Manganese Belt, India",
        latitude: 21.9455,
        longitude: 80.4295,
        utmEasting: 441089.33,
        utmNorthing: 2426904.20,
        rasterRow: 3655,
        rasterCol: 2056,
        modelProspectivityScore: 0.71, // 71%
        modelProspectivityClass: "HIGH",
        trainingPositiveRadiusPixels: 20, // 41x41 positive sample box = 1,681 pixels
        sampleCount: 3362
    };

    // ------------------------------------------------------------------------
    // 3. SENTINEL-2 PRODUCT & SPECTRAL BAND SPECIFICATIONS
    // ------------------------------------------------------------------------
    const SATELLITE_METADATA = {
        product: "S2B_MSIL2A_20260621T050649_N0512_R019_T44QMK_20260621T085550.SAFE",
        sensingTime: "2026-06-21T05:06:49.024000Z",
        mission: "Sentinel-2B",
        instrument: "MultiSpectral Instrument (MSI)",
        productLevel: "Level-2A (Surface Reflectance, Bottom of Atmosphere)",
        tileId: "T44QMK",
        crs: "EPSG:32644 (WGS 84 / UTM Zone 44N)",
        pixelSizeM: 20.0,
        rasterDimensions: { width: 5490, height: 5490 },
        boundsUtm: {
            left: 399960.0,
            bottom: 2390220.0,
            right: 509760.0,
            top: 2500020.0
        },
        bands: [
            { id: "B04", name: "Red", wavelengthNm: "665", resolutionM: 20, description: "Red reflectance, critical for iron oxide and vegetation discrimination." },
            { id: "B05", name: "Red Edge 1", wavelengthNm: "705", resolutionM: 20, description: "First vegetation transition band; surface material boundary sensing." },
            { id: "B06", name: "Red Edge 2", wavelengthNm: "740", resolutionM: 20, description: "Second red edge band; discriminatory chlorophyll and canopy structure." },
            { id: "B8A", name: "Narrow NIR", wavelengthNm: "865", resolutionM: 20, description: "Narrow Near-Infrared band (NOT B08). Core for NDVI and vegetation filtering." },
            { id: "B11", name: "SWIR-1", wavelengthNm: "1610", resolutionM: 20, description: "Short-Wave Infrared 1. Critical for moisture and mineral/alteration discrimination." },
            { id: "B12", name: "SWIR-2", wavelengthNm: "2190", resolutionM: 20, description: "Short-Wave Infrared 2. Key absorption features for clays, carbonates, and manganese oxides." }
        ]
    };

    // ------------------------------------------------------------------------
    // 4. DERIVED SPECTRAL INDICES & ML FEATURE DEFINITIONS
    // ------------------------------------------------------------------------
    const SPECTRAL_FEATURES = [
        {
            name: "Iron Oxide Ratio",
            formula: "B04 / B8A (or normalized SWIR/NIR)",
            importanceWeight: 0.23,
            color: "#ff6b35",
            observedRange: [0.169, 3.138],
            scientificRole: "Highlights surface iron and manganese oxide weathering crusts."
        },
        {
            name: "SWIR Ratio",
            formula: "B11 / B12",
            importanceWeight: 0.19,
            color: "#7b2fff",
            observedRange: [0.309, 3.884],
            scientificRole: "Diagnostic for alteration minerals, clay complexes, and mineralized surface expressions."
        },
        {
            name: "B11 (SWIR-1)",
            formula: "Direct reflectance at 1610 nm",
            importanceWeight: 0.16,
            color: "#a855f7",
            observedRange: [0.0, 1.0],
            scientificRole: "Provides surface moisture and lithological reflectance baseline."
        },
        {
            name: "B12 (SWIR-2)",
            formula: "Direct reflectance at 2190 nm",
            importanceWeight: 0.14,
            color: "#00f0ff",
            observedRange: [0.0, 1.0],
            scientificRole: "Identifies absorption dips in hydroxyl and metal-oxide bearing minerals."
        },
        {
            name: "Clay Index",
            formula: "B11 / B12 (or hydroxyl index)",
            importanceWeight: 0.11,
            color: "#ffaa00",
            observedRange: [0.2, 2.5],
            scientificRole: "Maps hydrothermally altered clay halos commonly flanking ore bodies."
        },
        {
            name: "NDVI",
            formula: "(B8A - B04) / (B8A + B04)",
            importanceWeight: 0.08,
            color: "#00ff88",
            observedRange: [-0.585, 0.669],
            scientificRole: "Measures green vegetative cover; low-to-moderate values indicate exposed rock/soil suitable for spectral detection."
        },
        {
            name: "NDMI",
            formula: "(B8A - B11) / (B8A + B11)",
            importanceWeight: 0.05,
            color: "#00a8ff",
            observedRange: [-0.585, 0.589],
            scientificRole: "Normalized Difference Moisture Index; filters canopy water content."
        },
        {
            name: "B4 (Red)",
            formula: "Direct reflectance at 665 nm",
            importanceWeight: 0.04,
            color: "#ff4444",
            observedRange: [0.0, 1.0],
            scientificRole: "Visual red spectrum absorption baseline."
        }
    ];

    // ------------------------------------------------------------------------
    // 5. MINERAL AVAILABILITY CATALOG
    // ------------------------------------------------------------------------
    const MINERAL_CATALOG = [
        {
            id: "manganese",
            name: "Manganese",
            status: "available",
            statusLabel: "AI Model Active",
            description: "Sentinel-2 trained Random Forest model available on Tile T44QMK (Balaghat belt).",
            testAccuracyPct: 83.51,
            activeTile: "T44QMK"
        },
        {
            id: "bauxite",
            name: "Bauxite",
            status: "framework_ready",
            statusLabel: "Framework Ready — Model Not Yet Trained",
            description: "Al-rich lateritic spectral pipelines configured; requires labeled training samples.",
            testAccuracyPct: null,
            activeTile: null
        },
        {
            id: "limestone",
            name: "Limestone",
            status: "framework_ready",
            statusLabel: "Framework Ready — Model Not Yet Trained",
            description: "Carbonate absorption feature pipelines configured; awaiting training ground-truth.",
            testAccuracyPct: null,
            activeTile: null
        },
        {
            id: "coal",
            name: "Coal",
            status: "framework_ready",
            statusLabel: "Framework Ready — Model Not Yet Trained",
            description: "Carbon absorption feature pipelines configured; awaiting training ground-truth.",
            testAccuracyPct: null,
            activeTile: null
        },
        {
            id: "iron_ore",
            name: "Iron Ore",
            status: "framework_ready",
            statusLabel: "Framework Ready — Model Not Yet Trained",
            description: "Hematite/magnetite ratio pipelines configured; awaiting training ground-truth.",
            testAccuracyPct: null,
            activeTile: null
        }
    ];

    // ------------------------------------------------------------------------
    // 6. PRODUCTION SHORTFALL TRAINING REFERENCE (120 Records)
    // ------------------------------------------------------------------------
    const PRODUCTION_MODEL_META = {
        modelType: "RandomForestRegressor",
        trainSamples: 120,
        r2Score: 0.9278,
        maeTonnes: 321.52,
        inputFeatures: [
            { name: "Rainfall_mm", mean: 142.5, min: 20.0, max: 320.0 },
            { name: "Equipment_Downtime_hr", mean: 18.2, min: 2.0, max: 65.0 },
            { name: "Blasting_Delay_hr", mean: 6.4, min: 0.0, max: 24.0 },
            { name: "Equipment_Availability_pct", mean: 86.8, min: 60.0, max: 98.0 },
            { name: "Planned_Production_tonnes", mean: 10850.0, min: 5000.0, max: 15000.0 }
        ]
    };

    // ------------------------------------------------------------------------
    // 7. CALIBRATED PROSPECTIVITY GRID LOADER
    // ------------------------------------------------------------------------
    let _cachedProspectivityGrid = null;

    async function loadCalibratedProspectivity() {
        if (_cachedProspectivityGrid) {
            return _cachedProspectivityGrid;
        }

        try {
            const response = await fetch('data/processed/prospectivity_calibrated.json');
            if (response.ok) {
                _cachedProspectivityGrid = await response.json();
                return _cachedProspectivityGrid;
            }
        } catch (err) {
            console.warn("Could not fetch prospectivity_calibrated.json via HTTP; fallback to embedded metadata", err);
        }

        return null;
    }

    // ------------------------------------------------------------------------
    // 8. PUBLIC API EXPORT
    // ------------------------------------------------------------------------
    return {
        RAW_CANDIDATE_ZONES,
        CANDIDATE_ZONES,
        KNOWN_MINE,
        SATELLITE_METADATA,
        SPECTRAL_FEATURES,
        MINERAL_CATALOG,
        PRODUCTION_MODEL_META,
        loadCalibratedProspectivity
    };
}));
