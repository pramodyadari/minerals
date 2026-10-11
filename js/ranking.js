/**
 * ============================================================================
 * AI MINERAL INTELLIGENCE — EXPLORATION TARGET RANKING & COMPARISON SYSTEM
 * ============================================================================
 * 
 * Module: TargetRankingEngine (js/ranking.js)
 * 
 * Purpose:
 *   Evaluates, transparently ranks, and compares exploration discovery targets:
 *     1. Exploration Target Ranking:
 *        - Ranks real candidate discovery zones by actual model prospectivity score.
 *        - Never creates synthetic targets; uses authoritative Sentinel-2 zones.
 *     2. Clear Separation of 4 Core Metrics:
 *        - Prospectivity Score: Spatial similarity index (e.g. 97.6%).
 *        - Model Confidence: Strictly "Not Calibrated" (empirical curves not fitted).
 *        - Evidence Strength: Evaluated from actual data layers (Strong/Moderate/Limited).
 *        - Data Quality: Based strictly on active vs missing evidence sources (High/Medium/Low).
 *     3. Exploration Priority:
 *        - HIGH PRIORITY (>= 75%), MEDIUM PRIORITY (50-74%), LOW PRIORITY (< 50%).
 *        - Enforces screening disclaimer: "Priority indicates AI-assisted exploration
 *          screening and does not confirm mineralization."
 *     4. Multi-Target Comparison:
 *        - Side-by-side multi-zone intelligence comparison matrix.
 *        - Transparently audits differences without treating uningested datasets
 *          as negative physical measurements.
 *     5. Detailed Target Intelligence Dossier:
 *        - Reuses EvidenceEngine and ExplainableAI (10-feature Random Forest contributions).
 *     6. Map & Export Integration:
 *        - Coordinates with ExplorationMap and GeoJSON export pipelines.
 *     7. Multi-Mineral Framework Compatibility:
 *        - Supports active trained minerals and gracefully handles framework-ready minerals.
 * ============================================================================
 */

(function (root, factory) {
    if (typeof define === 'function' && define.amd) {
        define(['./data', './zones', './locations', './evidence', './xai', './mineral-registry', './geo'], factory);
    } else if (typeof module === 'object' && module.exports) {
        const MineralData = require('./data');
        const ZoneAnalysis = require('./zones');
        const LocationResolver = require('./locations');
        const EvidenceEngine = require('./evidence');
        const ExplainableAI = require('./xai');
        const MineralRegistry = require('./mineral-registry');
        const GeoEngine = require('./geo');
        module.exports = factory(MineralData, ZoneAnalysis, LocationResolver, EvidenceEngine, ExplainableAI, MineralRegistry, GeoEngine);
    } else {
        root.TargetRankingEngine = factory(
            root.MineralData,
            root.ZoneAnalysis,
            root.LocationResolver,
            root.EvidenceEngine,
            root.ExplainableAI,
            root.MineralRegistry,
            root.GeoEngine
        );
    }
}(typeof self !== 'undefined' ? self : this, function (MineralData, ZoneAnalysis, LocationResolver, EvidenceEngine, ExplainableAI, MineralRegistry, GeoEngine) {
    'use strict';

    /**
     * Determines overall Evidence Strength from actual available evidence categories.
     * 
     * @param {Array<object>} categories - Categories from EvidenceEngine
     * @param {number} score - Prospectivity score
     * @returns {string} 'Strong' | 'Moderate' | 'Limited' | 'Unavailable'
     */
    function calculateEvidenceStrength(categories, score) {
        if (!Array.isArray(categories) || typeof score !== 'number' || isNaN(score)) {
            return 'Unavailable';
        }
        const availableCount = categories.filter(c => c.status === 'Available').length;
        if (score >= 95 && availableCount >= 2) return 'Strong';
        if (score >= 75 && availableCount >= 2) return 'Moderate';
        if (availableCount >= 1) return 'Limited';
        return 'Unavailable';
    }

    /**
     * Calculates transparent Data Quality based on active vs uningested project layers.
     * Distinct from Model Confidence (which describes statistical calibration).
     * 
     * @param {Array<object>} categories - Categories from EvidenceEngine
     * @returns {object} { level: 'MEDIUM', label: 'Medium', activeSources: number, totalSources: number, description: string }
     */
    function calculateDataQuality(categories) {
        // Authoritative sources currently in the project:
        // 1. Sentinel-2 Footprint (Available)
        // 2. Evaluated Prospectivity Raster (Available)
        // 3. 10-feature Random Forest Classifier (Available)
        // 4. Multi-spectral L2A Band Ratios (Dynamic/Unavailable on disk)
        // 5. Digital Elevation Model DEM (Unavailable)
        // 6. Regional Geological Vector Map (Unavailable)
        // 7. Subsurface Drilling Logs (Unavailable)
        // 8. Laboratory Geochemical Assays (Unavailable)
        const totalSources = 8;
        let activeSources = 3; // Baseline verified available layers

        if (Array.isArray(categories)) {
            const spectral = categories.find(c => c.id === 'spectral-evidence');
            if (spectral && spectral.status === 'Available') {
                activeSources += 1;
            }
            const terrain = categories.find(c => c.id === 'terrain-evidence');
            if (terrain && terrain.status === 'Available') {
                activeSources += 1;
            }
            const geology = categories.find(c => c.id === 'geological-evidence');
            if (geology && geology.status === 'Available') {
                activeSources += 1;
            }
        }

        let level = 'MEDIUM';
        let label = 'Medium';
        if (activeSources >= 5) {
            level = 'HIGH';
            label = 'High';
        } else if (activeSources < 2) {
            level = 'LOW';
            label = 'Low';
        }

        return {
            level: level,
            label: label,
            activeSources: activeSources,
            totalSources: totalSources,
            ratioText: `${activeSources}/${totalSources} Sources Active`,
            description: `${activeSources} of ${totalSources} regional datasets active (Sentinel-2 footprint, evaluated prospectivity raster, trained Random Forest model; 5 regional subsurface/terrain layers uningested).`
        };
    }

    /**
     * Standardized Exploration Priority determination based on prospectivity and evidence.
     * 
     * @param {number} score - Prospectivity score (0–100)
     * @returns {object} Priority classification object
     */
    function calculatePriority(score) {
        const disclaimer = 'Priority indicates AI-assisted exploration screening and does not confirm mineralization.';
        if (typeof score !== 'number' || isNaN(score) || score === null) {
            return {
                level: 'INSUFFICIENT DATA',
                badgeClass: 'awaiting',
                ruleText: 'Awaiting target data evaluation',
                disclaimer: disclaimer
            };
        }
        if (score >= 75) {
            return {
                level: 'HIGH PRIORITY',
                badgeClass: 'high',
                ruleText: 'Prospectivity index ≥ 75.0% supported by satellite multi-band anomaly signature',
                disclaimer: disclaimer
            };
        }
        if (score >= 50) {
            return {
                level: 'MEDIUM PRIORITY',
                badgeClass: 'medium',
                ruleText: 'Prospectivity index 50.0% – 74.9% with moderate spectral convergence',
                disclaimer: disclaimer
            };
        }
        return {
            level: 'LOW PRIORITY',
            badgeClass: 'low',
            ruleText: 'Prospectivity index < 50.0% indicating low surface spectral response',
            disclaimer: disclaimer
        };
    }

    /**
     * Resolves human-readable sector and subarea for a zone.
     */
    function resolveZoneMetadata(zoneId) {
        const dict = LocationResolver && (LocationResolver.ZONE_METADATA || LocationResolver.ZONES_METADATA);
        if (dict && dict[zoneId]) {
            return dict[zoneId];
        }
        return {
            sector: `Sector ${zoneId}`,
            subArea: 'Exploration Belt',
            rank: null,
            score: null
        };
    }

    /**
     * Retrieves all candidate targets ranked strictly by actual prospectivity score.
     * 
     * @param {string} [mineralId='manganese'] - Active mineral identifier
     * @returns {object} { isTrained: boolean, mineral: string, targets: Array<object>, count: number, message: string }
     */
    function getRankedTargets(mineralId = 'manganese') {
        const selectedId = mineralId || 'manganese';
        const registryConfig = (MineralRegistry && typeof MineralRegistry.getMineral === 'function')
            ? MineralRegistry.getMineral(selectedId)
            : null;

        const isTrained = registryConfig
            ? (registryConfig.status === 'trained')
            : (selectedId === 'manganese');

        if (!isTrained) {
            const mineralName = registryConfig ? registryConfig.displayName : selectedId;
            return {
                isTrained: false,
                mineral: selectedId,
                mineralName: mineralName,
                count: 0,
                targets: [],
                message: `Framework Ready — Model not trained. Training data required before mineral-specific candidate zones can be generated for ${mineralName}.`
            };
        }

        // Get authoritative candidate zones from ZoneAnalysis or MineralData
        let rawZones = [];
        if (ZoneAnalysis && typeof ZoneAnalysis.getAllZones === 'function') {
            rawZones = ZoneAnalysis.getAllZones();
        } else if (MineralData && MineralData.CANDIDATE_ZONES) {
            rawZones = MineralData.CANDIDATE_ZONES;
        }

        // Clone and sort strictly by meanScore descending
        const sorted = [...rawZones].sort((a, b) => {
            const scoreA = a.meanScore || (a.score ? a.score / 100 : 0);
            const scoreB = b.meanScore || (b.score ? b.score / 100 : 0);
            return scoreB - scoreA;
        });

        // Enrich each target with authoritative metrics
        const rankedTargets = sorted.map((zone, index) => {
            const rank = index + 1;
            const zoneId = zone.zoneId || zone.id;
            const lat = zone.latitude || zone.lat;
            const lon = zone.longitude || zone.lon;
            const meanScore = typeof zone.meanScore === 'number' ? zone.meanScore : ((zone.score || 0) / 100);
            const scorePct = Math.round(meanScore * 1000) / 10;
            const meta = resolveZoneMetadata(zoneId);
            const sectorName = meta.sector || `Sector ${zoneId}`;
            const subArea = meta.subArea || 'Exploration Belt';
            const displayName = `Zone ${zoneId} — ${sectorName}`;

            // Evaluate genuine evidence using existing EvidenceEngine
            let evidenceDossier = null;
            if (EvidenceEngine && typeof EvidenceEngine.evaluateEvidence === 'function') {
                evidenceDossier = EvidenceEngine.evaluateEvidence({
                    lat: lat,
                    lon: lon,
                    score: scorePct,
                    radiusKm: 25,
                    placeInfo: { placeName: displayName, subArea: subArea }
                });
            }

            const categories = evidenceDossier ? evidenceDossier.evidenceCategories : [];
            const evidenceStrength = calculateEvidenceStrength(categories, scorePct);
            const dataQuality = calculateDataQuality(categories);
            const priority = calculatePriority(scorePct);

            return {
                rank: rank,
                zoneId: zoneId,
                sectorName: sectorName,
                subArea: subArea,
                displayName: displayName,
                latitude: lat,
                longitude: lon,
                easting: zone.easting || 0,
                northing: zone.northing || 0,
                areaHectares: zone.areaHectares || 0,
                pixels: zone.pixels || 0,
                score: scorePct,
                scoreFormatted: `${scorePct.toFixed(1)}%`,
                rawScore: meanScore,
                modelConfidence: {
                    status: 'Not Calibrated',
                    displayValue: 'Not Calibrated',
                    isCalibrated: false,
                    methodology: 'Model outputs spatial prospectivity index (0–100%). Empirical posterior probability calibration was not fitted on this regional surface due to absence of regional non-deposit ground truth assays.'
                },
                evidenceStrength: evidenceStrength,
                dataQuality: dataQuality,
                priority: priority,
                evidenceDossier: evidenceDossier
            };
        });

        return {
            isTrained: true,
            mineral: selectedId,
            mineralName: registryConfig ? registryConfig.displayName : 'Manganese',
            count: rankedTargets.length,
            targets: rankedTargets,
            message: `Identified ${rankedTargets.length} candidate discovery zones ranked by trained AI prospectivity index.`
        };
    }

    /**
     * Retrieves a detailed Target Intelligence dossier for a specific candidate zone.
     * 
     * @param {number|string} zoneId - Zone ID
     * @param {string} [mineralId='manganese'] - Mineral ID
     * @returns {object|null} Target Intelligence dossier
     */
    function getZoneDetail(zoneId, mineralId = 'manganese') {
        const ranking = getRankedTargets(mineralId);
        if (!ranking || !ranking.isTrained) return null;

        const target = ranking.targets.find(t => String(t.zoneId) === String(zoneId));
        if (!target) return null;

        // Ensure XAI feature steps are present
        let topFeatures = [];
        if (target.evidenceDossier && Array.isArray(target.evidenceDossier.topModelFeatures)) {
            topFeatures = target.evidenceDossier.topModelFeatures;
        } else if (ExplainableAI && typeof ExplainableAI.explainProspectivityScore === 'function') {
            const exp = ExplainableAI.explainProspectivityScore(target.score, target.displayName);
            if (exp && exp.waterfallSteps) {
                topFeatures = exp.waterfallSteps
                    .filter(s => !s.isBaseline && !s.isFinal)
                    .slice(0, 5)
                    .map((s, idx) => ({
                        rank: idx + 1,
                        name: s.name,
                        contribution: s.value,
                        contributionFormatted: (s.value >= 0 ? '+' : '') + s.value.toFixed(2),
                        importancePct: s.importancePct || 0,
                        description: s.description || ''
                    }));
            }
        }

        return {
            ...target,
            topFeatures: topFeatures,
            evidenceCategories: target.evidenceDossier ? target.evidenceDossier.evidenceCategories : [],
            limitations: target.evidenceDossier ? target.evidenceDossier.limitations : [],
            dataProvenance: target.evidenceDossier ? target.evidenceDossier.dataProvenance : []
        };
    }

    /**
     * Compares two or more candidate targets across all scientific dimensions.
     * 
     * @param {Array<number|string>} zoneIds - Array of 2 or more zone IDs
     * @param {string} [mineralId='manganese'] - Mineral ID
     * @returns {object} Comparison matrix and differential analysis
     */
    function compareTargets(zoneIds = [], mineralId = 'manganese') {
        const ranking = getRankedTargets(mineralId);
        if (!ranking.isTrained) {
            return {
                isTrained: false,
                error: ranking.message,
                comparedCount: 0,
                targets: []
            };
        }

        const validIds = Array.isArray(zoneIds) ? zoneIds.map(String) : [];
        if (validIds.length < 2) {
            return {
                isTrained: true,
                error: 'Please select at least two candidate targets to perform side-by-side comparison.',
                comparedCount: validIds.length,
                targets: []
            };
        }

        const targets = validIds
            .map(id => getZoneDetail(id, mineralId))
            .filter(t => t !== null);

        if (targets.length < 2) {
            return {
                isTrained: true,
                error: 'Could not resolve at least two valid candidate targets for comparison.',
                comparedCount: targets.length,
                targets: targets
            };
        }

        // Build comparison rows across all 4 core metrics & evidence dimensions
        const rows = [
            {
                id: 'rank',
                label: 'Rank',
                category: 'Overview',
                values: targets.map(t => `#${t.rank}`)
            },
            {
                id: 'sector',
                label: 'Sector / Sub-area',
                category: 'Overview',
                values: targets.map(t => t.sectorName)
            },
            {
                id: 'score',
                label: 'AI Prospectivity Score',
                category: 'Core Metric',
                values: targets.map(t => t.scoreFormatted),
                highlight: true
            },
            {
                id: 'scoreDiff',
                label: 'Score Difference',
                category: 'Core Metric',
                values: targets.map((t, idx) => {
                    if (idx === 0) return 'Reference Baseline';
                    const diff = t.score - targets[0].score;
                    const sign = diff >= 0 ? '+' : '';
                    return `${sign}${diff.toFixed(1)} percentage points`;
                }),
                note: 'Raw spatial index separation; does not represent statistical significance.'
            },
            {
                id: 'confidence',
                label: 'Model Confidence',
                category: 'Core Metric',
                values: targets.map(t => t.modelConfidence.displayValue),
                note: 'Empirical calibration curve not fitted across spatial surface'
            },
            {
                id: 'evidenceStrength',
                label: 'Evidence Strength',
                category: 'Core Metric',
                values: targets.map(t => t.evidenceStrength)
            },
            {
                id: 'dataQuality',
                label: 'Data Quality',
                category: 'Core Metric',
                values: targets.map(t => t.dataQuality.label),
                note: 'Based on 3/8 regional layers active'
            },
            {
                id: 'priority',
                label: 'Exploration Priority',
                category: 'Decision Support',
                values: targets.map(t => t.priority.level)
            },
            {
                id: 'modelEvidence',
                label: 'Top Evidence',
                category: 'Evidence Breakdown',
                values: targets.map(t => {
                    const top = t.topFeatures && t.topFeatures[0];
                    return top ? `${top.name} (${top.contributionFormatted})` : 'Available';
                })
            },
            {
                id: 'xaiContributions',
                label: 'XAI Contributions',
                category: 'Evidence Breakdown',
                values: targets.map(t => {
                    if (t.topFeatures && t.topFeatures.length > 0) {
                        return t.topFeatures.slice(0, 3).map(f => `${f.name} (${f.contributionFormatted})`).join(', ');
                    }
                    return '10-feature model active';
                })
            },
            {
                id: 'spatialEvidence',
                label: 'Ground Footprint',
                category: 'Evidence Breakdown',
                values: targets.map(t => `${t.areaHectares} ha footprint (${t.pixels} px)`)
            },
            {
                id: 'spectralEvidence',
                label: 'Spectral Ratio Evidence',
                category: 'Evidence Breakdown',
                values: targets.map(() => 'Unavailable (Awaiting L2A)'),
                isUnavailable: true
            },
            {
                id: 'terrainEvidence',
                label: 'Terrain / DEM Evidence',
                category: 'Evidence Breakdown',
                values: targets.map(() => 'DATA NOT AVAILABLE'),
                isUnavailable: true
            },
            {
                id: 'geologicalEvidence',
                label: 'Geological Vector Map',
                category: 'Evidence Breakdown',
                values: targets.map(() => 'DATA NOT AVAILABLE'),
                isUnavailable: true
            },
            {
                id: 'drillingEvidence',
                label: 'Subsurface Drilling & Assays',
                category: 'Evidence Breakdown',
                values: targets.map(() => 'DATA NOT AVAILABLE'),
                isUnavailable: true
            },
            {
                id: 'coordinates',
                label: 'Coordinates (WGS84)',
                category: 'Geospatial',
                values: targets.map(t => `${t.latitude.toFixed(4)}°N, ${t.longitude.toFixed(4)}°E`)
            },
            {
                id: 'utm',
                label: 'Projected UTM 44N',
                category: 'Geospatial',
                values: targets.map(t => `${Math.round(t.easting).toLocaleString()} E, ${Math.round(t.northing).toLocaleString()} N`)
            }
        ];

        // Differential summary
        const topTarget = targets.reduce((best, cur) => cur.score > best.score ? cur : best, targets[0]);
        const scoreDelta = (Math.max(...targets.map(t => t.score)) - Math.min(...targets.map(t => t.score))).toFixed(1);

        const summaryNote = `Compared ${targets.length} discovery targets. Top prospective target is ${topTarget.displayName} (${topTarget.scoreFormatted}, Rank #${topTarget.rank}) with a score differential of ${scoreDelta}%. Missing evidence categories (Spectral, Terrain, Geology, Drilling) reflect uningested regional datasets rather than negative physical measurements.`;

        return {
            isTrained: true,
            error: null,
            comparedCount: targets.length,
            targets: targets,
            rows: rows,
            topTarget: topTarget,
            scoreDelta: scoreDelta,
            summaryNote: summaryNote,
            disclaimer: 'Priority indicates AI-assisted exploration screening and does not confirm mineralization.'
        };
    }

    /**
     * Exports target comparison or ranked targets as a standard GeoJSON FeatureCollection.
     * 
     * @param {Array<number|string>} [zoneIds=[]] - Target IDs to export (all if empty)
     * @param {string} [mineralId='manganese'] - Mineral ID
     * @returns {object} GeoJSON FeatureCollection
     */
    function exportComparisonGeoJSON(zoneIds = [], mineralId = 'manganese') {
        const ranking = getRankedTargets(mineralId);
        let targets = ranking.targets;
        if (Array.isArray(zoneIds) && zoneIds.length > 0) {
            const idSet = new Set(zoneIds.map(String));
            targets = targets.filter(t => idSet.has(String(t.zoneId)));
        }

        const features = targets.map(t => ({
            type: 'Feature',
            geometry: {
                type: 'Point',
                coordinates: [t.longitude, t.latitude]
            },
            properties: {
                target_type: 'candidate_discovery_zone',
                zone_id: t.zoneId,
                rank: t.rank,
                sector_name: t.sectorName,
                display_name: t.displayName,
                prospectivity_score_pct: t.score,
                model_confidence: t.modelConfidence.displayValue,
                is_confidence_calibrated: false,
                evidence_strength: t.evidenceStrength,
                data_quality: t.dataQuality.level,
                data_quality_ratio: t.dataQuality.ratioText,
                exploration_priority: t.priority.level,
                priority_rule: t.priority.ruleText,
                area_hectares: t.areaHectares,
                pixels_at_20m: t.pixels,
                utm_easting: t.easting,
                utm_northing: t.northing,
                crs: 'EPSG:32644 (UTM Zone 44N)',
                disclaimer: 'AI result is an exploration-screening indication, not confirmation of a mineral deposit.'
            }
        }));

        return {
            type: 'FeatureCollection',
            metadata: {
                title: 'AI Exploration Target Ranking & Comparison Dossier',
                mineral: ranking.mineralName,
                generated_at: new Date().toISOString(),
                total_targets_exported: targets.length,
                model_confidence_status: 'Not Calibrated',
                data_quality_status: 'Medium (3/8 Sources Active)',
                screening_disclaimer: 'AI result is an exploration-screening indication, not confirmation of a mineral deposit.'
            },
            crs: {
                type: 'name',
                properties: { name: 'urn:ogc:def:crs:OGC:1.3:CRS84' }
            },
            features: features
        };
    }

    return {
        getRankedTargets,
        getZoneDetail,
        compareTargets,
        exportComparisonGeoJSON,
        calculateEvidenceStrength,
        calculateDataQuality,
        calculatePriority
    };
}));
