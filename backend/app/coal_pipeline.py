"""
Coal Exploration Pipeline — Authoritative Data Ingestion, Basin Stratigraphy & Scientific Integrity
Gondwana & Tertiary Coal Basins of India (Godavari, Damodar, Mahanadi, Son-Singrauli, Korba)

Integrates:
1. Verified GSI, CMPDI, SCCL, and CIL coal occurrence inventories.
2. Stratigraphic host framework (Barakar & Raniganj Formations).
3. Multispectral optical surface constraints & underground seam disclaimers.
4. Scientific guardrails: Strictly withholds AI prospectivity scores until exploratory borehole core logs are available.
"""

import os
import json
from typing import Dict, Any, List, Optional

APP_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(APP_DIR, "..", ".."))
CURATED_DIR = os.path.join(PROJECT_ROOT, "data", "curated")


def get_coal_occurrences() -> Dict[str, Any]:
    """Returns the verified GSI / CMPDI / SCCL Coal mineral occurrences inventory."""
    occ_file = os.path.join(CURATED_DIR, "coal_occurrences.json")
    if os.path.exists(occ_file):
        with open(occ_file, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"occurrences": [], "provenance_meta": {"commodity": "Coal"}}


def is_within_coal_basin(lat: float, lon: float) -> tuple[bool, str]:
    """Checks whether coordinates fall within major Indian Gondwana or Tertiary coal basins."""
    # 1. Godavari Valley Basin
    if 17.20 <= lat <= 19.50 and 79.20 <= lon <= 81.30:
        return True, "Pranhita-Godavari Valley Coalfield (Telangana)"
    # 2. Damodar Valley Basin
    if 23.30 <= lat <= 24.20 and 84.80 <= lon <= 87.50:
        return True, "Damodar Valley Coalfield (Jharkhand / West Bengal)"
    # 3. Mahanadi Valley Basin
    if 20.70 <= lat <= 22.20 and 83.50 <= lon <= 85.50:
        return True, "Mahanadi Valley Coalfield (Odisha)"
    # 4. Son-Mahanadi & Singrauli Basin
    if 23.80 <= lat <= 24.50 and 82.20 <= lon <= 83.20:
        return True, "Singrauli & Son Valley Basin (MP / UP)"
    # 5. Hasdeo-Arand & Korba Basin
    if 22.10 <= lat <= 23.00 and 82.30 <= lon <= 83.20:
        return True, "Korba & Hasdeo-Arand Basin (Chhattisgarh)"
    return False, "Outside Known Primary Coal Basin Boundaries"

# Type alias helper
Tuple_bool_basin = tuple[bool, str]


def get_coal_spatial_audit_report() -> Dict[str, Any]:
    """Returns the spatial validation report and data gap audit for Coal."""
    return {
        "commodity": "Coal",
        "audit_status": "EVIDENCE_FRAMEWORK_ACTIVE_MODEL_WITHHELD",
        "scientific_integrity_rule": "DO_NOT_INFER_UNDERGROUND_SEAMS_FROM_SATELLITE_ALONE",
        "rationale": (
            "Coal seams in the Gondwana Supergroup dip beneath hundreds of meters of sandstone overburden. "
            "Optical multispectral satellite imagery (Sentinel-2 VNIR/SWIR) can detect opencast bench excavations, "
            "carbonaceous mine spoil, and coal-handling infrastructure, but has zero physical penetration into "
            "unmined subsurface strata. Training an AI model on surface spectral data to predict subsurface coal seams "
            "produces severe false positives over unmineralized dark soils and burnt ground. "
            "AI prospectivity predictions are therefore strictly withheld."
        ),
        "data_gap_analysis": {
            "satellite_optical_limitation": "Zero subsurface penetration; surface reflectance only reflects surface soil/spoil.",
            "required_geophysical_data": "High-resolution 2D/3D seismic reflection profiles across fault-bounded grabens.",
            "required_geological_data": "CMPDI diamond drill-core lithology logs, seam thickness correlations, and proximate chemical assays (ash %, moisture %, volatile matter, gross calorific value)."
        },
        "model_availability": {
            "model_status": "UNAVAILABLE_NO_MODEL",
            "ai_prospectivity_score": None,
            "model_confidence": None,
            "status_label": "Model Withheld — Subsurface Borehole Core Logs Required"
        }
    }


def get_coal_scientific_evaluation(lat: float, lon: float, radius_km: float = 10.0) -> Dict[str, Any]:
    """Constructs the comprehensive scientific evaluation dossier for Coal at the specified coordinates."""
    in_basin, basin_name = is_within_coal_basin(lat, lon)
    occs_data = get_coal_occurrences()
    
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
        "commodity": "Coal",
        "search_radius_km": radius_km,
        "study_basin": basin_name,
        "is_within_study_basin": in_basin,
        "occurrences_in_radius": len(occs_in_radius),
        "occurrences_in_radius_list": occs_in_radius,
        "nearest_confirmed_colliery": {
            "name": nearest_dep["name"] if nearest_dep else "None in database",
            "distance_km": round(min_dist_km, 2) if nearest_dep else None,
            "operator": nearest_dep.get("operator") if nearest_dep else None,
            "status": nearest_dep.get("status") if nearest_dep else None,
            "basin": nearest_dep.get("basin") if nearest_dep else None,
            "formation": nearest_dep.get("geological_formation") if nearest_dep else None,
            "typical_thickness": nearest_dep.get("typical_seam_thickness_m") if nearest_dep else None
        },
        "model_availability": {
            "model_status": "UNAVAILABLE_NO_MODEL",
            "ai_prospectivity_score": None,
            "model_confidence": None,
            "status_label": "Unavailable — Optical Satellite Seam Inference Strictly Guarded",
            "decision": "EVIDENCE_ONLY_NO_PREDICTION",
            "scientific_rationale": (
                "Optical multispectral Sentinel-2 imagery records surface reflectance only and cannot penetrate "
                "sandstone overburden to detect underground coal seams. In accordance with mining geology standards, "
                "AI prospectivity predictions are withheld to prevent fabricated or misleading underground seam inferences."
            )
        },
        "measured_surface_evidence": [
            {
                "indicator": "Surface VNIR Albedo & Carbonaceous Reflectance",
                "target_feature": "Opencast coal bench excavations and carbonaceous shale spoil tips",
                "scientific_limitation": "Maps active open-pit mining footprints and spoil dumps, not virgin underground seams."
            },
            {
                "indicator": "Vegetation Density & Canopy Vigour (NDVI)",
                "target_feature": "Forest clearings associated with colliery leases and industrial haul roads",
                "scientific_limitation": "Vegetation clearing occurs in any infrastructure development and is non-diagnostic for coal."
            },
            {
                "indicator": "Lower Gondwana Graben Geomorphology",
                "target_feature": "Fault-bounded synclinal troughs preserving Permian Barakar coal measures",
                "scientific_limitation": "Basin presence is permissive, but seam thickness and depth require borehole drill logs."
            }
        ],
        "mandatory_geological_prerequisites": [
            "CMPDI exploratory core drilling with seam intersection depth logs and lithological core samples.",
            "Proximate and ultimate chemical analysis (ash %, moisture %, fixed carbon, volatile matter, GCV in kcal/kg).",
            "High-resolution shallow seismic reflection profiling to map fault offsets and seam continuity."
        ]
    }
