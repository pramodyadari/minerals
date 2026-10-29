"""
Bauxite Exploration Pipeline — Authoritative Data Ingestion, Plateau Duricrust Geomorphology & Scientific Integrity
East Coast Bauxite Province (Odisha / AP), Central India Patlands, and Western Ghats Belts

Integrates:
1. Verified GSI, IBM, NALCO, and OMC bauxite occurrence inventories.
2. High-elevation plateau ("pat") laterite morphology (>900m - 1200m ASL).
3. Sentinel-2 SWIR Al-OH absorption ratios and lateritic duricrust indicators.
4. Scientific guardrails: Strictly distinguishes lateritic iron duricrust from commercial gibbsitic bauxite ore.
"""

import os
import json
from typing import Dict, Any, List, Optional

APP_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(APP_DIR, "..", ".."))
CURATED_DIR = os.path.join(PROJECT_ROOT, "data", "curated")


def get_bauxite_occurrences() -> Dict[str, Any]:
    """Returns the verified GSI / IBM / NALCO Bauxite mineral occurrences inventory."""
    occ_file = os.path.join(CURATED_DIR, "bauxite_occurrences.json")
    if os.path.exists(occ_file):
        with open(occ_file, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"occurrences": [], "provenance_meta": {"commodity": "Bauxite"}}


def is_within_bauxite_province(lat: float, lon: float) -> tuple[bool, str]:
    """Checks whether coordinates fall within major Indian bauxite provinces."""
    # 1. East Coast Bauxite Province (Odisha / AP)
    if 18.00 <= lat <= 20.00 and 82.50 <= lon <= 84.00:
        return True, "East Coast Bauxite Province (Odisha / Andhra Pradesh)"
    # 2. Central India Maikala Range & Patlands (MP / Chhattisgarh)
    if 21.80 <= lat <= 23.50 and 81.00 <= lon <= 84.00:
        return True, "Central India Laterite Plateau & Patland Province (MP / Chhattisgarh)"
    # 3. Western Ghats Belt (Maharashtra / Karnataka)
    if 15.00 <= lat <= 17.50 and 73.50 <= lon <= 74.80:
        return True, "Western Ghats High-Level Laterite Belt (Maharashtra / Karnataka)"
    # 4. Coastal Gujarat Belt (Kutch / Jamnagar)
    if 21.80 <= lat <= 23.80 and 69.00 <= lon <= 70.80:
        return True, "Coastal Gujarat Bauxite Belt (Kutch / Jamnagar)"
    return False, "Outside Known Primary Bauxite Province Boundaries"


def get_bauxite_spatial_audit_report() -> Dict[str, Any]:
    """Returns the spatial validation report and data gap audit for Bauxite."""
    return {
        "commodity": "Bauxite",
        "audit_status": "EVIDENCE_FRAMEWORK_ACTIVE_MODEL_WITHHELD",
        "scientific_integrity_rule": "DISTINGUISH_LATERITIC_DURICRUST_FROM_COMMERCIAL_BAUXITE",
        "rationale": (
            "Tertiary bauxite deposits in India form blanket cappings on high-elevation peneplains ('patlands' >900m ASL). "
            "While remote-sensing SWIR ratios (B11/B12 Al-OH absorption) and Copernicus DEM elevation can identify "
            "elevated lateritized plateau surfaces, optical sensors cannot distinguish low-grade ferruginous laterite "
            "(Al2O3 < 35%, Fe2O3 > 30%) from commercial refractory/metallurgical gibbsitic bauxite (Al2O3 > 45%, reactive SiO2 < 3%). "
            "Training an AI model solely on optical pixels leads to massive false-positive over-estimation on unmineralized "
            "lateritic soils across the Indian Shield. AI prospectivity predictions are therefore strictly withheld."
        ),
        "data_gap_analysis": {
            "satellite_optical_limitation": "Cannot chemically differentiate gibbsite-rich ore from barren ferruginous laterite or lithomargic clay.",
            "required_geochemical_data": "Systematic grid percussion / diamond drilling (50m x 50m) with X-Ray Fluorescence (XRF) assays for Al2O3, Fe2O3, reactive SiO2, TiO2, and Loss on Ignition (LOI).",
            "required_geomorphological_data": "High-resolution DEM plateau masking isolating flat-topped mesas (>900m ASL) from dissected valley slopes."
        },
        "model_availability": {
            "model_status": "UNAVAILABLE_NO_MODEL",
            "ai_prospectivity_score": None,
            "model_confidence": None,
            "status_label": "Model Withheld — Chemical Assay & Core Drilling Required"
        }
    }


def get_bauxite_scientific_evaluation(lat: float, lon: float, radius_km: float = 10.0) -> Dict[str, Any]:
    """Constructs the comprehensive scientific evaluation dossier for Bauxite at the specified coordinates."""
    in_prov, prov_name = is_within_bauxite_province(lat, lon)
    occs_data = get_bauxite_occurrences()
    
    # Calculate proximity and occurrences within selected radius
    nearest_dep = None
    min_dist_km = 9999.0
    occs_in_radius = []
    for occ in occs_data.get("occurrences", []):
        dist = 111.0 * ((lat - occ["latitude"])**2 + ((lon - occ["longitude"]) * 0.94)**2)**0.5
        if dist <= radius_km:
            occs_in_radius.append({**occ, "distance_km": round(dist, 2)})
        if dist < min_dist_km:
            min_dist_km = dist
            nearest_dep = occ

    return {
        "commodity": "Bauxite",
        "search_radius_km": radius_km,
        "study_province": prov_name,
        "is_within_study_province": in_prov,
        "occurrences_in_radius": len(occs_in_radius),
        "occurrences_in_radius_list": occs_in_radius,
        "nearest_confirmed_deposit": {
            "name": nearest_dep["name"] if nearest_dep else "None in database",
            "distance_km": round(min_dist_km, 2) if nearest_dep else None,
            "operator": nearest_dep.get("operator") if nearest_dep else None,
            "status": nearest_dep.get("status") if nearest_dep else None,
            "province": nearest_dep.get("province") if nearest_dep else None,
            "formation": nearest_dep.get("geological_formation") if nearest_dep else None,
            "typical_al2o3_pct": nearest_dep.get("ore_grade_typical_pct_al2o3") if nearest_dep else None
        },
        "model_availability": {
            "model_status": "UNAVAILABLE_NO_MODEL",
            "ai_prospectivity_score": None,
            "model_confidence": None,
            "status_label": "Unavailable — Laterite Duricrust vs Gibbsitic Ore Distinguishable only via Assay",
            "decision": "EVIDENCE_ONLY_NO_PREDICTION",
            "scientific_rationale": (
                "Surface remote sensing maps lateritized plateau morphology and Al-OH absorption, but chemical ore grade "
                "requires systematic assay analysis. In accordance with mining standards, numerical AI scores are withheld."
            )
        },
        "measured_surface_evidence": [
            {
                "indicator": "Al-OH Molecular Absorption Ratio (B11/B12)",
                "target_feature": "Hydroxylated aluminous minerals (gibbsite, kaolinite) in laterite profiles",
                "scientific_limitation": "Detects hydroxylated clay minerals; cannot distinguish low-grade clay/laterite from metallurgical-grade bauxite."
            },
            {
                "indicator": "Ferric Iron (Fe3+) Oxide Ratio (B04/B02)",
                "target_feature": "Ferruginous laterite duricrust caprock overlying aluminous ore horizons",
                "scientific_limitation": "Lateritic iron staining is ubiquitous in tropical profiles and is non-diagnostic for commercial bauxite."
            },
            {
                "indicator": "Elevated Plateau / Mesa Morphology",
                "target_feature": "High-altitude flat-topped peneplain surfaces (>900m ASL) preserving Tertiary weathering crusts",
                "scientific_limitation": "Plateau geometry confirms permissive geomorphic preservation, but ore presence must be confirmed by drilling."
            }
        ],
        "mandatory_geological_prerequisites": [
            "Grid-pattern diamond or percussion core drilling through the laterite blanket into basal lithomargic clay.",
            "Laboratory X-Ray Fluorescence (XRF) assays establishing Al2O3 > 40%, reactive SiO2 < 4%, and Fe2O3 < 20%.",
            "Mineralogical X-Ray Diffraction (XRD) determining trihydrate gibbsite vs monohydrate boehmite/diaspore ratio for alumina refinery digestion kinetics."
        ]
    }
