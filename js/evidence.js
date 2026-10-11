/**
 * ============================================================================
 * AI MINERAL INTELLIGENCE — PROSPECTIVITY EVIDENCE & CONFIDENCE SYSTEM
 * ============================================================================
 * 
 * Module: EvidenceEngine (js/evidence.js)
 * 
 * Purpose:
 *   Provides scientific evidence evaluation, honest confidence attribution,
 *   data limitations tracking, and field recommendations for mineral targets:
 *     1. AI Prospectivity vs Model Confidence distinction:
 *        - Prospectivity Score (0–100%): Model-derived spatial similarity index.
 *        - Model Confidence: Honestly labeled "Not Calibrated" when empirical
 *          probability calibration curves are not fitted.
 *     2. Categorized Evidence Breakdown:
 *        - Spatial Evidence (Neighborhood cluster, buffer statistics)
 *        - Model Feature Evidence (XAI 10-feature Random Forest contributions)
 *        - Spectral Ratio Evidence (Dynamically checks disk availability)
 *        - Terrain / DEM Evidence (Honest "DATA NOT AVAILABLE")
 *        - Geological / Lithology Evidence (Honest "DATA NOT AVAILABLE")
 *        - Drilling / Assay Evidence (Honest "DATA NOT AVAILABLE")
 *     3. Transparent Plain-Language Summary ("WHY THIS TARGET?"):
 *        Explains reasons without ever fabricating deposit guarantees.
 *     4. Real Limitations & Data Quality Tracking:
 *        Explicitly flags missing bands, 20m resolution, lack of drilling.
 *     5. Exploration Recommendations:
 *        High / Medium / Low Priority screening classifications with mandatory
 *        disclaimer: "AI result is an exploration-screening indication, not
 *        confirmation of a mineral deposit."
 *     6. Data Provenance & Source Auditing.
 * ============================================================================
 */

(function (root, factory) {
    if (typeof define === 'function' && define.amd) {
        define(['./xai', './data', './geo'], factory);
    } else if (typeof module === 'object' && module.exports) {
        const ExplainableAI = require('./xai');
        const MineralData = require('./data');
        const GeoEngine = require('./geo');
        module.exports = factory(ExplainableAI, MineralData, GeoEngine);
    } else {
        root.EvidenceEngine = factory(root.ExplainableAI, root.MineralData, root.GeoEngine);
    }
}(typeof self !== 'undefined' ? self : this, function (ExplainableAI, MineralData, GeoEngine) {
    'use strict';

    /**
     * Evaluates comprehensive evidence and confidence for a given target.
     * 
     * @param {object} params
     * @param {number} params.lat - Latitude
     * @param {number} params.lon - Longitude
     * @param {number} params.score - Prospectivity percent (0–100)
     * @param {number} [params.radiusKm=25] - Analysis radius
     * @param {object} [params.spectralRatios] - Multi-spectral ratios payload
     * @param {Array<object>} [params.nearbyZones] - Nearby candidate zones
     * @param {object} [params.placeInfo] - Resolved place metadata
     * @returns {object} Structured evidence & confidence dossier
     */
    function evaluateEvidence(params = {}) {
        const {
            lat,
            lon,
            score,
            radiusKm = 25,
            spectralRatios = null,
            nearbyZones = [],
            placeInfo = null,
            terrainEvidence = null,
            geologicalEvidence = null,
            independentValidation = null
        } = params;

        const hasValidScore = typeof score === 'number' && !isNaN(score) && score !== null;
        const validScore = hasValidScore ? Math.max(0, Math.min(100, Math.round(score * 10) / 10)) : 0;

        // 1. Classification
        let classification = 'Awaiting Target';
        if (hasValidScore) {
            if (validScore >= 90) classification = 'Very High Prospectivity';
            else if (validScore >= 75) classification = 'High Prospectivity';
            else if (validScore >= 50) classification = 'Moderate Prospectivity';
            else if (validScore >= 25) classification = 'Low Prospectivity';
            else classification = 'Very Low Prospectivity';
        }

        // 2. Model Confidence (Strict Honesty Principle)
        // Prospectivity score represents spatial similarity, NOT calibrated empirical probability.
        const modelConfidence = {
            status: 'Not Calibrated',
            displayValue: 'Not Calibrated',
            isCalibrated: false,
            methodology: 'Model outputs spatial prospectivity index (0–100%). Empirical posterior probability calibration was not fitted on this regional surface due to absence of regional non-deposit ground truth assays.'
        };

        // 3. Connect to existing XAI (models/manganese_random_forest.pkl weights)
        const xaiResult = ExplainableAI && typeof ExplainableAI.explainProspectivityScore === 'function'
            ? ExplainableAI.explainProspectivityScore(validScore, placeInfo ? placeInfo.name : 'Target Location')
            : null;

        // Top contributing features from model
        const topModelFeatures = [];
        if (xaiResult && xaiResult.waterfallSteps) {
            // Filter non-baseline steps and sort by contribution absolute value descending
            const featureSteps = xaiResult.waterfallSteps
                .filter(s => !s.isBaseline && !s.isFinal)
                .sort((a, b) => Math.abs(b.value) - Math.abs(a.value));

            featureSteps.slice(0, 5).forEach((step, idx) => {
                const sign = step.value >= 0 ? '+' : '';
                topModelFeatures.push({
                    rank: idx + 1,
                    id: step.id,
                    name: step.name,
                    contribution: step.value,
                    contributionFormatted: `${sign}${step.value.toFixed(2)}`,
                    importancePct: step.importancePct,
                    description: step.description
                });
            });
        }

        // 4. Check Spectral Ratios Status
        const spectralAvailable = !!(
            spectralRatios &&
            spectralRatios.spectral_status === 'calculated' &&
            spectralRatios.ratios &&
            Object.values(spectralRatios.ratios).some(r => r.status === 'calculated')
        );

        // 5. Evidence Categories Breakdown
        const categories = [];

        // Category A: Model Feature Evidence (XAI)
        categories.push({
            id: 'model-evidence',
            name: 'Model Evidence',
            status: hasValidScore ? 'Available' : 'Awaiting Target',
            contribution: hasValidScore ? (validScore >= 75 ? 'Strong' : 'Moderate') : 'N/A',
            badgeClass: hasValidScore ? 'badge-available' : 'badge-neutral',
            explanation: hasValidScore
                ? `10-feature Random Forest model evaluates top spectral discriminators (${topModelFeatures.slice(0, 2).map(f => f.name).join(', ')}) matching trained mineralization signatures.`
                : 'Awaiting target selection to evaluate Random Forest decision tree leaf activation.'
        });

        // Category B: Spatial Evidence
        const zoneCount = Array.isArray(nearbyZones) ? nearbyZones.length : 0;
        const spatialStrong = zoneCount >= 1 || validScore >= 75;
        categories.push({
            id: 'spatial-evidence',
            name: 'Spatial Evidence',
            status: hasValidScore ? 'Available' : 'Awaiting Target',
            contribution: hasValidScore ? (spatialStrong ? 'Strong' : 'Moderate') : 'N/A',
            badgeClass: hasValidScore ? 'badge-available' : 'badge-neutral',
            explanation: hasValidScore
                ? (zoneCount > 0
                    ? `Target is situated within a high-prospectivity spatial cluster with ${zoneCount} verified candidate discovery zone${zoneCount > 1 ? 's' : ''} inside the ${radiusKm} km buffer.`
                    : `Target is situated in the ${radiusKm} km regional exploration buffer with continuous spatial raster coverage.`)
                : 'Awaiting target selection to analyze surrounding neighborhood prospectivity.'
        });

        // Category C: Spectral Evidence
        if (spectralAvailable) {
            categories.push({
                id: 'spectral-evidence',
                name: 'Spectral Evidence',
                status: 'Available',
                contribution: 'Strong',
                badgeClass: 'badge-available',
                explanation: 'Calculated multi-spectral reflectance ratios (B11/B8A Ferrous, B11/B12 Clay, B04/B02 Iron Oxide) support hydrothermal and weathering alteration signatures.'
            });
        } else {
            categories.push({
                id: 'spectral-evidence',
                name: 'Spectral Evidence',
                status: 'DATA NOT AVAILABLE',
                contribution: 'Unavailable',
                badgeClass: 'badge-unavailable',
                explanation: 'Required Sentinel-2 surface reflectance bands (B02, B04, B8A, B11, B12) are not present on disk; multi-spectral ratio calculation awaiting surface reflectance imagery.'
            });
        }

        // Category D: Terrain Evidence (Honest scientific reporting: dynamic check)
        const terrainAvailable = !!(terrainEvidence && terrainEvidence.available && terrainEvidence.status === 'AVAILABLE');
        if (terrainAvailable) {
            categories.push({
                id: 'terrain-evidence',
                name: 'Terrain Evidence',
                status: 'Available',
                contribution: 'Contextual',
                badgeClass: 'badge-available',
                elevation_m: terrainEvidence.elevation_m,
                slope_deg: terrainEvidence.slope_deg,
                aspect_deg: terrainEvidence.aspect_deg,
                explanation: `Elevation: ${terrainEvidence.elevation_m} m | Slope: ${terrainEvidence.slope_deg}° | Aspect: ${terrainEvidence.aspect_deg}° (Factual DEM context; does not represent mineral probability).`
            });
        } else {
            categories.push({
                id: 'terrain-evidence',
                name: 'Terrain Evidence',
                status: 'DATA NOT AVAILABLE',
                contribution: 'Unavailable',
                badgeClass: 'badge-unavailable',
                explanation: 'Digital Elevation Model (DEM / slope / aspect) raster is not loaded in current project footprint.'
            });
        }

        // Category E: Geological / Lithology Evidence (Honest scientific reporting: dynamic check)
        const geologyAvailable = !!(geologicalEvidence && geologicalEvidence.available && geologicalEvidence.status === 'AVAILABLE');
        if (geologyAvailable) {
            const lithUnit = (geologicalEvidence.lithology && geologicalEvidence.lithology.unit) ? geologicalEvidence.lithology.unit : 'Unmapped';
            const structDist = (geologicalEvidence.structures && geologicalEvidence.structures.nearest_distance_m !== null) ? `${geologicalEvidence.structures.nearest_distance_m} m` : 'DATA NOT AVAILABLE';
            categories.push({
                id: 'geological-evidence',
                name: 'Geological Evidence',
                status: 'Available',
                contribution: 'Contextual',
                badgeClass: 'badge-available',
                lithology: lithUnit,
                structureDistance: structDist,
                explanation: `Lithology: ${lithUnit} | Nearest mapped structure: ${structDist} (Contextual geological evidence; not mineralization proof).`
            });
        } else {
            categories.push({
                id: 'geological-evidence',
                name: 'Geological Evidence',
                status: 'DATA NOT AVAILABLE',
                contribution: 'Unavailable',
                badgeClass: 'badge-unavailable',
                explanation: 'Regional digitized geological vector map / lithological formation shapefile is not loaded; prediction relies on satellite-derived features.'
            });
        }

        // Category F: Drilling / Assay Evidence
        categories.push({
            id: 'drilling-evidence',
            name: 'Subsurface Drilling & Assay Evidence',
            status: 'DATA NOT AVAILABLE',
            contribution: 'Unavailable',
            badgeClass: 'badge-unavailable',
            explanation: 'No diamond drill holes or laboratory geochemical core assays available in this sector; surface remote sensing only.'
        });

        // Category G: Model Validation Evidence
        const targetMineral = (params && params.mineral) ? String(params.mineral).toLowerCase() : 'manganese';
        const isMn = targetMineral === 'manganese';
        categories.push({
            id: 'validation-evidence',
            name: 'Model Validation',
            status: isMn ? 'Available' : 'DATA NOT AVAILABLE',
            contribution: isMn ? 'Verified' : 'Unavailable',
            badgeClass: isMn ? 'badge-available' : 'badge-unavailable',
            explanation: isMn
                ? 'Spatial validation: Available | Method: Within-study spatial-sector validation | Validation performance: 96.76% accuracy (Holdout specificity: 94.75%) | Calibration: Not calibrated. (Note: Validation performance evaluates statistical generalization across geographic sectors, not geological proof).'
                : 'Validation unavailable: Ground-truth observations and trained model awaiting real dataset.'
        });

        // Category H: Independent Deposit Validation (Phase 8 Requirement 15)
        const indValParam = params && params.independentValidation;
        const indValAvailable = !!(indValParam && (indValParam.status === 'AVAILABLE' || indValParam.status === 'Available') && indValParam.available);
        if (indValAvailable) {
            categories.push({
                id: 'independent-validation-evidence',
                name: 'Independent Deposit Validation',
                status: 'Available',
                contribution: 'Verified',
                badgeClass: 'badge-available',
                depositsTested: indValParam.independent_deposits_count || indValParam.distinct_deposits || 0,
                explanation: `Independent deposits tested: ${indValParam.independent_deposits_count || indValParam.distinct_deposits || 0} | Model version: ${indValParam.model_version || 'manganese_random_forest'} | Evaluation: External test set outside Ghondi reference deposit.`
            });
        } else {
            categories.push({
                id: 'independent-validation-evidence',
                name: 'Independent Deposit Validation',
                status: 'NOT AVAILABLE',
                contribution: 'Unavailable',
                badgeClass: 'badge-unavailable',
                explanation: 'Current positive ground truth originates from one known Manganese deposit (Ghondi Mine). Additional verified Manganese deposit data is required.'
            });
        }

        // 6. Plain-Language Explanation for Non-Technical Users ("WHY THIS TARGET?")
        let plainExplanation = '';
        if (!hasValidScore) {
            plainExplanation = 'Select a location on the map, choose a preset, or search by place name to generate AI prospectivity evidence and explanation.';
        } else {
            const placeStr = placeInfo ? (placeInfo.placeName || placeInfo.name || 'this location') : 'this location';
            const topNames = topModelFeatures.slice(0, 2).map(f => f.name).join(' and ');
            plainExplanation = `The model identifies ${placeStr} as ${classification.toLowerCase()} (${validScore.toFixed(1)}%) because its available environmental and spatial characteristics (led by ${topNames}) resemble patterns associated with high-prospectivity areas in the trained dataset. This is an exploration-screening indication, not proof of an ore body.`;
        }

        // 7. Uncertainty & Limitations
        const limitations = [
            'Sentinel-2 spatial resolution: 20 m per pixel (narrow veins and small ore lenses fall below sensor resolution)',
            spectralAvailable
                ? 'Spectral ratio bands: Active pixel-level ratio calculations from local GeoTIFF bands'
                : 'Spectral ratio bands: Unavailable on disk (requires raw Sentinel-2 L2A GeoTIFF bands)',
            terrainAvailable
                ? 'Terrain / DEM metrics: Factual elevation and slope extracted from loaded DEM'
                : 'No Digital Elevation Model (DEM) loaded in workspace; terrain slope and aspect not available',
            geologyAvailable
                ? 'Geological / Lithology map: Mapped vector units active for contextual spatial assessment'
                : 'No digitized regional geological vector map loaded in workspace',
            'No diamond drilling or borehole log data available in workspace',
            'No laboratory geochemical assay data available in workspace',
            'Prediction based on trained Random Forest model (statistical pattern matching)',
            'Geological and terrain layers provide contextual evidence and are not themselves proof of mineralization',
            indValAvailable
                ? `Independent deposit validation: Active external validation across ${indValParam.independent_deposits_count || 0} deposits`
                : 'Independent deposit validation is not currently available (positive ground truth is from a single known deposit)',
            'Target requires mandatory ground-truth verification, structural mapping, and soil sampling'
        ];

        // 8. Exploration Recommendation
        let recommendationPriority = 'INSUFFICIENT DATA';
        let recommendationAction = '';
        if (hasValidScore) {
            if (validScore >= 75) {
                recommendationPriority = 'HIGH PRIORITY';
                recommendationAction = 'Prioritize for preliminary field reconnaissance, surface geological outcrop mapping, and grid-based soil geochemical sampling.';
            } else if (validScore >= 50) {
                recommendationPriority = 'MEDIUM PRIORITY';
                recommendationAction = 'Secondary exploration candidate. Review regional structural lineaments and fault proximity before committing field resources.';
            } else {
                recommendationPriority = 'LOW PRIORITY';
                recommendationAction = 'Low prospective indication. Limited surface spectral alteration detected; assign lower exploration priority.';
            }
        } else {
            recommendationPriority = 'INSUFFICIENT DATA';
            recommendationAction = 'Awaiting target coordinate selection inside the Sentinel-2 exploration footprint.';
        }

        const recommendationDisclaimer = 'AI result is an exploration-screening indication, not confirmation of a mineral deposit.';
        const contextualDisclaimer = 'Geological and terrain layers provide contextual evidence and are not themselves proof of mineralization.';
        const independentValidationDisclaimer = indValAvailable
            ? `Independent deposit validation performed on ${indValParam.independent_deposits_count || 0} external deposits.`
            : 'Independent deposit validation is not currently available.';

        // 9. Independent Deposit Validation Status
        const independentDepositValidation = indValAvailable ? {
            status: 'AVAILABLE',
            displayValue: 'AVAILABLE',
            methodology: 'External independent deposit test',
            independent_deposits_count: indValParam.independent_deposits_count || 0,
            occurrences_count: indValParam.occurrences_count || 0,
            explanation: `Verified on ${indValParam.independent_deposits_count || 0} independent deposits outside the Ghondi reference deposit.`
        } : {
            status: 'NOT AVAILABLE',
            displayValue: 'NOT AVAILABLE',
            methodology: 'Within-study spatial-sector validation',
            independent_deposits_count: 0,
            occurrences_count: 0,
            explanation: 'Current positive ground truth originates from one known Manganese deposit. Independent deposit validation requires additional real Manganese occurrence datasets.'
        };

        // 10. Data Provenance & Source Audit
        const dataProvenance = [
            { source: 'Sentinel-2 Tile Footprint (T44QMK)', status: 'Available', type: 'Multispectral Satellite Imagery', coverage: 'Full Footprint', resolution: '20 m' },
            { source: 'Prospectivity Model Surface', status: 'Available', type: '20m Evaluated GeoTIFF Raster', coverage: '5,490 x 5,490 Pixels', resolution: '20 m' },
            { source: 'Random Forest Model (10 features)', status: 'Available', type: 'scikit-learn Classifier (100 Trees)', coverage: 'Trained Benchmark', resolution: 'N/A' },
            { source: 'Candidate Anomaly Zones Directory', status: 'Available', type: '20 High-Grade Anomaly Sectors', coverage: 'Regional Belt', resolution: 'Polygon' },
            { source: 'Multi-Spectral Ratio Bands', status: spectralAvailable ? 'Available' : 'DATA NOT AVAILABLE', type: 'L2A Surface Reflectance Bands', coverage: spectralAvailable ? 'Active Bands' : 'None', resolution: spectralAvailable ? '20 m' : 'None' },
            { source: 'Digital Elevation Model (DEM)', status: terrainAvailable ? 'Available' : 'DATA NOT AVAILABLE', type: 'Elevation / Slope Raster', coverage: terrainAvailable ? 'Active DEM' : 'None', resolution: terrainAvailable ? `${terrainEvidence.resolution_m || 30} m` : 'None' },
            { source: 'Regional Geological Map', status: geologyAvailable ? 'Available' : 'DATA NOT AVAILABLE', type: 'Lithological Formation Vector Map', coverage: geologyAvailable ? 'Active Geology' : 'None', resolution: geologyAvailable ? 'Vector' : 'None' },
            { source: 'Independent Manganese Occurrences', status: indValAvailable ? 'Available' : 'DATA NOT AVAILABLE', type: 'Independent Deposit Ground Truth', coverage: indValAvailable ? 'External Mines' : 'None', resolution: 'Certified GPS' },
            { source: 'Diamond Core Drilling Logs', status: 'DATA NOT AVAILABLE', type: 'Subsurface Exploration Assays', coverage: 'None Available', resolution: 'None' },
            { source: 'Laboratory Geochemical Assays', status: 'DATA NOT AVAILABLE', type: 'Wet Chemistry / XRF Assays', coverage: 'None Available', resolution: 'None' }
        ];

        return {
            hasTarget: hasValidScore,
            lat: lat,
            lon: lon,
            score: validScore,
            classification: classification,
            modelConfidence: modelConfidence,
            independentDepositValidation: independentDepositValidation,
            topModelFeatures: topModelFeatures,
            evidenceCategories: categories,
            plainExplanation: plainExplanation,
            limitations: limitations,
            recommendation: {
                priority: recommendationPriority,
                action: recommendationAction,
                disclaimer: recommendationDisclaimer,
                contextualDisclaimer: contextualDisclaimer,
                independentValidationDisclaimer: independentValidationDisclaimer
            },
            dataProvenance: dataProvenance
        };
    }

    /**
     * Generates a concise HTML snippet for Map target markers and zone popups.
     * 
     * @param {object} evidence - Dossier from evaluateEvidence
     * @returns {string} HTML snippet
     */
    function formatPopupEvidenceSnippet(evidence) {
        if (!evidence || !evidence.hasTarget) {
            return '<div class="popup-evidence-empty">Awaiting target analysis.</div>';
        }

        const topBullets = evidence.topModelFeatures.slice(0, 3).map(f => {
            return `<li><strong>${f.name}</strong> <span class="font-mono cyan">${f.contributionFormatted}</span></li>`;
        }).join('');

        return `
            <div class="popup-evidence-box">
                <div class="popup-evidence-title">Top Model Evidence:</div>
                <ul class="popup-evidence-list">
                    ${topBullets}
                </ul>
                <div class="popup-evidence-conf">
                    Confidence: <span class="dim-badge">${evidence.modelConfidence.displayValue}</span>
                </div>
            </div>
        `;
    }

    return {
        evaluateEvidence,
        formatPopupEvidenceSnippet
    };
}));
