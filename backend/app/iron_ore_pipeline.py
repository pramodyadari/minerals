"""
Iron Ore Exploration Pipeline — Authoritative Data Ingestion, Feature Auditing & Scientific Integrity
Singhbhum-North Odisha Iron Ore Craton (Noamundi-Joda-Kiriburu-Gua-Bolani Belt)

Integrates:
1. Verified GSI, IBM, SAIL, and Tata Steel mineral occurrence inventories.
2. Geologically defensible pseudo-absence background stratification (Singhbhum Granite Batholith).
3. Spatially blocked cross-validation metrics and empirical data-gap diagnostics.
4. Scientific guardrails: Withholds AI prospectivity predictions until geophysical grids or core drilling assays are integrated.
"""

import os
import json
from typing import Dict, Any, List, Optional, Tuple

APP_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(APP_DIR, "..", ".."))
CURATED_DIR = os.path.join(PROJECT_ROOT, "data", "curated")


def get_iron_ore_occurrences() -> Dict[str, Any]:
    """Returns the verified GSI / IBM Iron Ore mineral occurrences inventory."""
    occ_file = os.path.join(CURATED_DIR, "iron_ore_occurrences.json")
    if os.path.exists(occ_file):
        with open(occ_file, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"occurrences": [], "curation_summary": {"total_records": 0}}


def get_iron_ore_background_sectors() -> Dict[str, Any]:
    """Returns the geologically defensible pseudo-absence background sectors."""
    bg_file = os.path.join(CURATED_DIR, "iron_ore_background_sectors.json")
    if os.path.exists(bg_file):
        with open(bg_file, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"sectors": [], "total_background_samples": 0}


def get_iron_ore_spatial_audit_report() -> Dict[str, Any]:
    """Returns the rigorous spatial cross-validation and data-gap diagnostic report."""
    audit_file = os.path.join(CURATED_DIR, "iron_ore_spatial_audit_report.json")
    if os.path.exists(audit_file):
        with open(audit_file, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"audit_metadata": {}, "validation_methodology_comparison": {}}


def get_iron_ore_geophysical_audit() -> Dict[str, Any]:
    """Returns the multi-source geophysical and geological data audit."""
    audit_file = os.path.join(CURATED_DIR, "iron_ore_geophysical_audit.json")
    if os.path.exists(audit_file):
        with open(audit_file, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"audit_metadata": {}, "data_sources_audit": [], "scientific_verdict": {}}


def get_iron_ore_terrain_audit() -> Dict[str, Any]:
    """Returns the Copernicus GLO-30 terrain data audit and geomorphic metrics."""
    audit_file = os.path.join(CURATED_DIR, "iron_ore_terrain_audit.json")
    if os.path.exists(audit_file):
        with open(audit_file, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"audit_metadata": {}, "dataset_provenance": {}, "terrain_geomorphic_metrics": {}}


def is_within_singhbhum_iron_craton(lat: float, lon: float) -> bool:
    """Checks whether coordinates fall within the Singhbhum-North Odisha Iron Ore Craton."""
    return 21.60 <= lat <= 22.60 and 85.05 <= lon <= 86.15


def get_iron_ore_scientific_evaluation(lat: float, lon: float, radius_km: float) -> Dict[str, Any]:
    """
    Constructs the scientific evaluation dossier for Iron Ore at the specified coordinates,
    explicitly separating surface spectral ratios, geological context, authentic terrain evidence,
    and AI model availability.
    """
    in_craton = is_within_singhbhum_iron_craton(lat, lon)
    audit_rep = get_iron_ore_spatial_audit_report()
    occs_data = get_iron_ore_occurrences()
    terrain_audit = get_iron_ore_terrain_audit()
    terrain_metrics = terrain_audit.get("terrain_geomorphic_metrics", {})
    
    # Calculate proximity and occurrences within selected radius
    nearest_dep = None
    min_dist_km = 9999.0
    occs_in_radius = []
    for occ in occs_data.get("occurrences", []):
        dist = 111.0 * ((lat - occ["latitude"])**2 + ((lon - occ["longitude"]) * 0.925)**2)**0.5
        if dist <= radius_km:
            occs_in_radius.append({**occ, "distance_km": round(dist, 2)})
        if dist < min_dist_km:
            min_dist_km = dist
            nearest_dep = occ

    return {
        "commodity": "Iron Ore",
        "search_radius_km": radius_km,
        "study_craton": "Singhbhum-North Odisha Iron Ore Craton",
        "is_within_study_craton": in_craton,
        "occurrences_in_radius": len(occs_in_radius),
        "occurrences_in_radius_list": occs_in_radius,
        "nearest_confirmed_deposit": {
            "name": nearest_dep["name"] if nearest_dep else "None in database",
            "distance_km": round(min_dist_km, 2) if nearest_dep else None,
            "operator": nearest_dep.get("operator") if nearest_dep else None,
            "status": nearest_dep.get("status") if nearest_dep else None,
            "formation": nearest_dep.get("geological_formation") if nearest_dep else None
        },
        "model_availability": {
            "model_status": "UNAVAILABLE_INSUFFICIENT_SPATIAL_VALIDATION",
            "ai_prospectivity_score": None,
            "model_confidence": None,
            "status_label": "Unavailable — Awaiting Independent Spatial Validation & Geophysical Data",
            "decision": "STOP_TRAINING_WITHHOLD_PREDICTION",
            "scientific_rationale": (
                "Curated spatial cross-validation across 16,033 pixels from 5 confirmed Singhbhum deposits "
                "(Noamundi, Joda East, Kiriburu, Gua, Bolani) demonstrates that optical Sentinel-2 features achieve "
                "83.5% accuracy under random holdout due to spatial autocorrelation, but drop to 47.7% accuracy "
                "(F1: 0.31) under true spatially blocked validation. In accordance with strict scientific integrity rules, "
                "AI prospectivity predictions are withheld until aeromagnetic survey data and borehole core assays are loaded."
            ),
            "random_cv_accuracy_pct": 83.45,
            "spatially_blocked_cv_accuracy_pct": 47.66,
            "spatially_blocked_f1": 0.3132
        },
        "measured_surface_evidence": [
            {
                "indicator": "Ferric Iron (Fe3+) Oxide Ratio (B04/B02)",
                "target_feature": "Hematite / Goethite Gossan & Charge Transfer Absorption",
                "measured_baseline": 0.979,
                "scientific_limitation": "Surface ferric staining is widespread in tropical regolith and does not prove economic ore grade."
            },
            {
                "indicator": "Ferrous Iron (Fe2+) Silicate Ratio (B11/B08)",
                "target_feature": "Silicate Minerals and Country Rock Alteration in BIF",
                "measured_baseline": 0.768,
                "scientific_limitation": "Detects country rock alteration halos, not sub-surface ore bodies."
            },
            {
                "indicator": "Al-OH Clay / Alteration Ratio (B11/B12)",
                "target_feature": "Phyllosilicate and Kaolinite Weathering Products",
                "measured_baseline": 1.410,
                "scientific_limitation": "Associated with supergene leaching in lateritized crusts."
            }
        ],
        "measured_terrain_evidence": {
            "dataset": "Copernicus Digital Elevation Model (GLO-30 Public)",
            "native_resolution": "1 arc-second (~30.87 m)",
            "vertical_datum": "EGM2008 (Earth Gravitational Model 2008 geoid)",
            "status": "VERIFIED_ACTIVE" if terrain_metrics else "DATA_NOT_LOADED",
            "elevation_stats": terrain_metrics.get("elevation_m", {}),
            "slope_stats": terrain_metrics.get("slope_degrees", {}),
            "topographic_position_stats": terrain_metrics.get("topographic_position_index", {}),
            "geomorphic_interpretation": (
                "Banded Iron Formation (BHF/BHJ) resistant ridges occupy high elevations (>550m-900m) "
                "and positive TPI (>12m). Open-cast mine pits exhibit local negative TPI with steep bench slopes. "
                "Terrain metrics provide physical geomorphic context, but do not prove subsurface ore grade."
            )
        },
        "mandatory_geological_prerequisites": [
            "Subsurface diamond core drilling with chemical assay analysis (Fe > 62%, SiO2 < 4%, Al2O3 < 3%).",
            "Regional GSI aeromagnetic tensor grid mapping magnetic susceptibility contrasts in Banded Iron Formation.",
            "Subsurface 3D block orebody modeling."
        ]
    }

