/**
 * ============================================================================
 * AI MINERAL INTELLIGENCE — MULTI-MINERAL REGISTRY
 * ============================================================================
 * 
 * Module: MineralRegistry (js/mineral-registry.js)
 * 
 * Purpose:
 *   Central configuration registry for all supported minerals.
 *   Each mineral entry declares its actual availability status:
 *     - Whether a trained ML model exists
 *     - Whether prospectivity raster/grid data exists
 *     - Whether candidate zones have been generated from real model output
 *     - Whether XAI feature importances are available from a trained model
 *     - Whether a production prediction model exists
 * 
 * Scientific Integrity Rule:
 *   A mineral is marked "trained" ONLY if a genuinely trained model and
 *   verified prediction data exist. All other minerals are marked
 *   "framework_ready" and MUST NOT receive fake predictions, candidate zones,
 *   or XAI explanations.
 * 
 * Current State (as of implementation):
 *   - Manganese: TRAINED — Real RF model, prospectivity raster, 20 candidate
 *     zones (scipy connected-component IDs), 10-feature XAI, production model.
 *   - All others: FRAMEWORK READY — No trained models, no data, no predictions.
 * ============================================================================
 */

(function (root, factory) {
    if (typeof define === 'function' && define.amd) {
        define([], factory);
    } else if (typeof module === 'object' && module.exports) {
        module.exports = factory();
    } else {
        root.MineralRegistry = factory();
    }
}(typeof self !== 'undefined' ? self : this, function () {
    'use strict';

    // -----------------------------------------------------------------------
    // MINERAL REGISTRY — Authoritative configuration for each mineral
    // -----------------------------------------------------------------------
    const MINERALS = {
        manganese: {
            id: "manganese",
            displayName: "Manganese",
            status: "trained",
            statusLabel: "AI Model Active",
            statusDescription: "Sentinel-2 trained Random Forest model available on Tile T44QMK (Balaghat belt, India).",
            modelAvailable: true,
            prospectivityAvailable: true,
            zonesAvailable: true,
            xaiAvailable: true,
            productionModelAvailable: true,
            testAccuracyPct: 83.51,
            validationStatus: "SPATIALLY_VALIDATED",
            validationMethod: "Spatial Block Validation",
            validationScope: "Within-study spatial-sector validation",
            independentDepositValidation: {
                status: "NOT AVAILABLE",
                displayValue: "NOT AVAILABLE",
                explanation: "Current positive ground truth originates from one known Manganese deposit. Independent deposit validation requires additional real Manganese occurrence datasets."
            },
            spatialAccuracyPct: 96.76,
            holdoutSpecificityPct: 94.75,
            spatialF1: 0.9671,
            spatialRocAuc: 0.9931,
            spatialPrAuc: 0.9923,
            calibrationStatus: "NOT_CALIBRATED",
            activeTile: "T44QMK",
            modelPath: "models/manganese_random_forest.pkl",
            gridPath: "data/processed/tile_prospectivity_549.json",
            zonesPath: "data/processed/high_prospectivity_zones.csv",
            productionModelPath: "models/production_random_forest.pkl",
            productionTreesPath: "data/processed/production_rf_trees.json",
            rasterPath: "outputs/manganese_prospectivity.tif",
            color: "#00f0ff",
            icon: "⛏️",
            requiredForTraining: null // Already trained
        },

        coal: {
            id: "coal",
            displayName: "Coal",
            status: "framework_ready",
            statusLabel: "Framework Ready — Model Not Yet Trained",
            statusDescription: "Carbon absorption feature pipelines configured; awaiting ground-truth training data and model training.",
            modelAvailable: false,
            prospectivityAvailable: false,
            zonesAvailable: false,
            xaiAvailable: false,
            productionModelAvailable: false,
            testAccuracyPct: null,
            activeTile: null,
            modelPath: null,
            gridPath: null,
            zonesPath: null,
            productionModelPath: null,
            productionTreesPath: null,
            rasterPath: null,
            color: "#64748b",
            icon: "🪨",
            requiredForTraining: [
                "Sentinel-2 tile covering known coal deposit",
                "Ground-truth coal mine coordinates for training labels",
                "Spectral feature extraction (coal-specific band selection)",
                "Labeled training data (positive + negative samples)",
                "RandomForestClassifier training and validation",
                "Prospectivity raster generation (predict_proba)",
                "Connected-component zone detection (scipy.ndimage.label)",
                "Feature importance extraction for XAI"
            ]
        },

        bauxite: {
            id: "bauxite",
            displayName: "Bauxite",
            status: "framework_ready",
            statusLabel: "Framework Ready — Model Not Yet Trained",
            statusDescription: "Al-rich lateritic spectral pipelines configured; requires labeled training samples from known bauxite deposits.",
            modelAvailable: false,
            prospectivityAvailable: false,
            zonesAvailable: false,
            xaiAvailable: false,
            productionModelAvailable: false,
            testAccuracyPct: null,
            activeTile: null,
            modelPath: null,
            gridPath: null,
            zonesPath: null,
            productionModelPath: null,
            productionTreesPath: null,
            rasterPath: null,
            color: "#d97706",
            icon: "🧱",
            requiredForTraining: [
                "Sentinel-2 tile covering known bauxite deposit",
                "Ground-truth bauxite mine coordinates for training labels",
                "Spectral feature extraction (laterite/Al-oxide band selection)",
                "Labeled training data (positive + negative samples)",
                "RandomForestClassifier training and validation",
                "Prospectivity raster generation (predict_proba)",
                "Connected-component zone detection (scipy.ndimage.label)",
                "Feature importance extraction for XAI"
            ]
        },

        limestone: {
            id: "limestone",
            displayName: "Limestone",
            status: "framework_ready",
            statusLabel: "Framework Ready — Model Not Yet Trained",
            statusDescription: "Carbonate absorption feature pipelines configured; awaiting ground-truth training data from known limestone quarries.",
            modelAvailable: false,
            prospectivityAvailable: false,
            zonesAvailable: false,
            xaiAvailable: false,
            productionModelAvailable: false,
            testAccuracyPct: null,
            activeTile: null,
            modelPath: null,
            gridPath: null,
            zonesPath: null,
            productionModelPath: null,
            productionTreesPath: null,
            rasterPath: null,
            color: "#a3a3a3",
            icon: "🪨",
            requiredForTraining: [
                "Sentinel-2 tile covering known limestone deposit",
                "Ground-truth limestone quarry coordinates for training labels",
                "Spectral feature extraction (carbonate absorption bands)",
                "Labeled training data (positive + negative samples)",
                "RandomForestClassifier training and validation",
                "Prospectivity raster generation (predict_proba)",
                "Connected-component zone detection (scipy.ndimage.label)",
                "Feature importance extraction for XAI"
            ]
        },

        iron_ore: {
            id: "iron_ore",
            displayName: "Iron Ore",
            status: "framework_ready",
            statusLabel: "Framework Ready — Model Not Yet Trained",
            statusDescription: "Hematite/magnetite ratio pipelines configured; awaiting ground-truth training data from known iron ore deposits.",
            modelAvailable: false,
            prospectivityAvailable: false,
            zonesAvailable: false,
            xaiAvailable: false,
            productionModelAvailable: false,
            testAccuracyPct: null,
            activeTile: null,
            modelPath: null,
            gridPath: null,
            zonesPath: null,
            productionModelPath: null,
            productionTreesPath: null,
            rasterPath: null,
            color: "#dc2626",
            icon: "⛰️",
            requiredForTraining: [
                "Sentinel-2 tile covering known iron ore deposit",
                "Ground-truth iron mine coordinates for training labels",
                "Spectral feature extraction (iron oxide ratio bands)",
                "Labeled training data (positive + negative samples)",
                "RandomForestClassifier training and validation",
                "Prospectivity raster generation (predict_proba)",
                "Connected-component zone detection (scipy.ndimage.label)",
                "Feature importance extraction for XAI"
            ]
        },

        copper: {
            id: "copper",
            displayName: "Copper",
            status: "framework_ready",
            statusLabel: "Framework Ready — Model Not Yet Trained",
            statusDescription: "Copper sulfide/oxide spectral pipelines configured; awaiting ground-truth training data.",
            modelAvailable: false,
            prospectivityAvailable: false,
            zonesAvailable: false,
            xaiAvailable: false,
            productionModelAvailable: false,
            testAccuracyPct: null,
            activeTile: null,
            modelPath: null,
            gridPath: null,
            zonesPath: null,
            productionModelPath: null,
            productionTreesPath: null,
            rasterPath: null,
            color: "#b45309",
            icon: "🔶",
            requiredForTraining: [
                "Sentinel-2 tile covering known copper deposit",
                "Ground-truth copper mine coordinates for training labels",
                "Spectral feature extraction (copper-specific bands)",
                "Labeled training data (positive + negative samples)",
                "RandomForestClassifier training and validation",
                "Prospectivity raster generation (predict_proba)",
                "Connected-component zone detection (scipy.ndimage.label)",
                "Feature importance extraction for XAI"
            ]
        },

        lithium: {
            id: "lithium",
            displayName: "Lithium",
            status: "framework_ready",
            statusLabel: "Framework Ready — Model Not Yet Trained",
            statusDescription: "Lithium pegmatite/brine spectral pipelines configured; awaiting ground-truth training data.",
            modelAvailable: false,
            prospectivityAvailable: false,
            zonesAvailable: false,
            xaiAvailable: false,
            productionModelAvailable: false,
            testAccuracyPct: null,
            activeTile: null,
            modelPath: null,
            gridPath: null,
            zonesPath: null,
            productionModelPath: null,
            productionTreesPath: null,
            rasterPath: null,
            color: "#06b6d4",
            icon: "🔋",
            requiredForTraining: [
                "Sentinel-2 tile covering known lithium deposit",
                "Ground-truth lithium mine coordinates for training labels",
                "Spectral feature extraction (lithium-specific bands)",
                "Labeled training data (positive + negative samples)",
                "RandomForestClassifier training and validation",
                "Prospectivity raster generation (predict_proba)",
                "Connected-component zone detection (scipy.ndimage.label)",
                "Feature importance extraction for XAI"
            ]
        }
    };

    // -----------------------------------------------------------------------
    // PUBLIC API
    // -----------------------------------------------------------------------

    /**
     * Returns the mineral configuration for the given mineral ID.
     * @param {string} mineralId
     * @returns {object|null}
     */
    function getMineral(mineralId) {
        return MINERALS[mineralId] || null;
    }

    /**
     * Returns an array of all registered mineral configurations.
     * @returns {Array<object>}
     */
    function getAllMinerals() {
        return Object.values(MINERALS);
    }

    /**
     * Returns only minerals that have a trained model.
     * @returns {Array<object>}
     */
    function getTrainedMinerals() {
        return Object.values(MINERALS).filter(m => m.status === 'trained');
    }

    /**
     * Returns only minerals that are framework-ready but not yet trained.
     * @returns {Array<object>}
     */
    function getUntrainedMinerals() {
        return Object.values(MINERALS).filter(m => m.status === 'framework_ready');
    }

    /**
     * Checks whether a given mineral has a trained model available.
     * @param {string} mineralId
     * @returns {boolean}
     */
    function isTrained(mineralId) {
        const m = MINERALS[mineralId];
        return m ? m.status === 'trained' : false;
    }

    /**
     * Checks whether prospectivity analysis can be performed for a mineral.
     * @param {string} mineralId
     * @returns {boolean}
     */
    function canAnalyze(mineralId) {
        const m = MINERALS[mineralId];
        return m ? (m.modelAvailable && m.prospectivityAvailable) : false;
    }

    /**
     * Checks whether candidate zones exist for a mineral.
     * @param {string} mineralId
     * @returns {boolean}
     */
    function hasZones(mineralId) {
        const m = MINERALS[mineralId];
        return m ? m.zonesAvailable : false;
    }

    /**
     * Checks whether XAI is available for a mineral.
     * @param {string} mineralId
     * @returns {boolean}
     */
    function hasXAI(mineralId) {
        const m = MINERALS[mineralId];
        return m ? m.xaiAvailable : false;
    }

    /**
     * Checks whether a production model exists for a mineral.
     * @param {string} mineralId
     * @returns {boolean}
     */
    function hasProductionModel(mineralId) {
        const m = MINERALS[mineralId];
        return m ? m.productionModelAvailable : false;
    }

    /**
     * Returns validation metrics and status for a given mineral.
     * @param {string} mineralId
     * @returns {object}
     */
    function getValidationInfo(mineralId) {
        const m = MINERALS[mineralId];
        if (!m || m.status !== 'trained') {
            return {
                mineralId: mineralId,
                modelStatus: m ? m.status : 'unknown',
                validationStatus: 'NOT_VALIDATED',
                calibrationStatus: 'NOT_CALIBRATED',
                validationMethod: 'None',
                spatialAccuracyPct: null,
                spatialF1: null,
                spatialRocAuc: null,
                spatialPrAuc: null,
                isSpatiallyValidated: false,
                isCalibrated: false,
                reason: 'Model awaiting real training data.'
            };
        }
        return {
            mineralId: m.id,
            modelStatus: 'TRAINED',
            validationStatus: m.validationStatus || 'SPATIALLY_VALIDATED',
            calibrationStatus: m.calibrationStatus || 'NOT_CALIBRATED',
            validationMethod: m.validationMethod || 'Spatial Block Validation',
            validationScope: m.validationScope || 'Within-study spatial-sector validation',
            independentDepositValidation: m.independentDepositValidation || {
                status: 'NOT AVAILABLE',
                displayValue: 'NOT AVAILABLE',
                explanation: 'Current positive ground truth originates from one known Manganese deposit. Independent deposit validation requires additional real Manganese occurrence datasets.'
            },
            spatialAccuracyPct: m.spatialAccuracyPct || 96.76,
            holdoutSpecificityPct: m.holdoutSpecificityPct || 94.75,
            spatialF1: m.spatialF1 || 0.9671,
            spatialRocAuc: m.spatialRocAuc || 0.9931,
            spatialPrAuc: m.spatialPrAuc || 0.9923,
            isSpatiallyValidated: true,
            isCalibrated: false,
            whyNotCalibrated: 'A calibrated probability of mineral occurrence has not been established from the available regional validation evidence.'
        };
    }

    return {
        MINERALS,
        getMineral,
        getAllMinerals,
        getTrainedMinerals,
        getUntrainedMinerals,
        isTrained,
        canAnalyze,
        hasZones,
        hasXAI,
        hasProductionModel,
        getValidationInfo
    };
}));
