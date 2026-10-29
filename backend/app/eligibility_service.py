"""
================================================================================
AI MINERAL EXPLORATION & PROSPECTIVITY PIPELINE — NATIONWIDE ELIGIBILITY SERVICE
================================================================================
Module: backend/app/eligibility_service.py

Provides unified nationwide geographic eligibility and evidence coverage audits:
1. Sovereign territorial boundary check (Survey of India baseline).
2. Satellite imagery availability & local raster download check (Copernicus CDSE).
3. Cloud cover & valid pixel count verification (Scene Classification Layer).
4. Mineral-specific model domain & spatial footprint check (Tile T44QMK for Manganese).
5. Defensible model training and validation status check (Manganese vs. Iron Ore / Coal / Bauxite).
6. Clear separation between evidence availability and model prediction eligibility.

Standard Eligibility Status Codes:
- OUTSIDE_SUPPORTED_TERRITORY: Coordinates lie outside sovereign boundaries of India.
- NO_SATELLITE_DATA: No Sentinel-2 satellite scenes exist in catalogue.
- DATA_NOT_DOWNLOADED: Satellite scene discovered in catalogue, but local GeoTIFF bands are not downloaded.
- INSUFFICIENT_VALID_PIXELS: Exploration radius has 0 valid pixels after cloud/nodata masking.
- OUTSIDE_MODEL_DOMAIN: Coordinates lie outside the validated model training footprint (e.g. Manganese outside T44QMK).
- MODEL_UNAVAILABLE: No validated machine learning model exists for the target commodity (Coal, Iron Ore, Bauxite).
- EVIDENCE_ONLY: Permissive evidence analysis is active, but predictive prospectivity scores remain withheld.
- ELIGIBLE_FOR_ANALYSIS: Target meets all criteria for full validated model inference and calibrated 3D prospectivity.
================================================================================
"""

import os
import math
from typing import Dict, Any, Optional

try:
    from .geological_service import is_within_india_boundaries
    from .copernicus_service import discover_copernicus_sentinel2
    from .raster_ingestion_service import ingest_and_process_satellite_rasters
except ImportError:
    from backend.app.geological_service import is_within_india_boundaries
    from backend.app.copernicus_service import discover_copernicus_sentinel2
    from backend.app.raster_ingestion_service import ingest_and_process_satellite_rasters

T44QMK_BOUNDS = {
    "min_lat": 21.4880,
    "max_lat": 22.4220,
    "min_lon": 79.7900,
    "max_lon": 80.7600
}

def is_within_tile(lat: float, lon: float) -> bool:
    """Checks if coordinates lie within validated Sentinel-2 Tile T44QMK footprint."""
    return (T44QMK_BOUNDS["min_lat"] <= lat <= T44QMK_BOUNDS["max_lat"] and
            T44QMK_BOUNDS["min_lon"] <= lon <= T44QMK_BOUNDS["max_lon"])

SUPPORTED_MINERALS = ["Coal", "Manganese", "Iron Ore", "Bauxite"]


def get_geographic_eligibility(
    lat: float,
    lon: float,
    mineral_name: str,
    radius_km: float = 10.0,
    mock_satellite_error: Optional[str] = None,
    sat_discovery: Optional[Dict[str, Any]] = None,
    spectral_proc: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Evaluates nationwide geographic eligibility, satellite data availability,
    pixel sufficiency, and model domain compliance.
    Can reuse pre-computed satellite discovery and spectral processing evidence
    to eliminate duplicate network calls.
    """
    # 0. Canonical mineral normalization
    canonical_mineral = mineral_name.strip().title()
    if canonical_mineral.lower() == "iron ore":
        canonical_mineral = "Iron Ore"

    # 1. Sovereign Territorial Boundary Check
    in_india, territory_msg = is_within_india_boundaries(lat, lon)
    if not in_india:
        return {
            "status": "OUTSIDE_SUPPORTED_TERRITORY",
            "overall_eligibility": "OUTSIDE_SUPPORTED_TERRITORY",
            "is_within_india": False,
            "mineral": canonical_mineral,
            "latitude": lat,
            "longitude": lon,
            "radius_km": radius_km,
            "territorial_status": "OUTSIDE_SUPPORTED_TERRITORY",
            "satellite_status": "NOT_ACCESSED",
            "pixel_status": "SKIPPED_OUTSIDE_TERRITORY",
            "model_domain_status": "OUTSIDE_TERRITORY",
            "model_training_status": "NOT_APPLICABLE",
            "prediction_eligible": False,
            "evidence_eligible": False,
            "explanation": territory_msg,
            "limitations": [
                "Target coordinates lie outside the sovereign territorial boundary of India.",
                "Exploration screening is supported strictly within Indian metallogenic basins."
            ],
            "supported_actions": [
                "Adjust search coordinates within mainland India (6.5°N - 37.5°N, 68.0°E - 97.5°E)."
            ]
        }

    # 2. Satellite Discovery Check (Copernicus CDSE) - reuse pre-computed if available
    if sat_discovery is None:
        sat_discovery = discover_copernicus_sentinel2(
            lat=lat,
            lon=lon,
            radius_km=radius_km,
            timeout_sec=4.0,
            mock_error_type=mock_satellite_error
        )
    sat_scenes = sat_discovery.get("scenes", [])
    sat_catalogue_status = sat_discovery.get("status", "CATALOGUE_SERVICE_ERROR")

    # 3. Spectral & Pixel Processing Check - reuse pre-computed if available
    if spectral_proc is None:
        spectral_proc = ingest_and_process_satellite_rasters(
            lat=lat,
            lon=lon,
            radius_km=radius_km,
            mineral_name=canonical_mineral,
            discovered_scenes=sat_scenes,
            mock_error_type=mock_satellite_error
        )
    raster_processed = bool(spectral_proc.get("raster_pixels_processed"))
    pixel_cov = spectral_proc.get("pixel_coverage", {})
    valid_pixels = pixel_cov.get("valid_pixels", 0)
    cloud_pct = pixel_cov.get("cloud_mask_pct", 0.0)

    # Determine satellite & download status
    if raster_processed:
        satellite_status = "AVAILABLE_PROCESSED"
    elif sat_scenes:
        satellite_status = "DATA_NOT_DOWNLOADED"
    else:
        satellite_status = "NO_SATELLITE_DATA"

    # Determine pixel status
    if raster_processed and valid_pixels > 0:
        pixel_status = "VALID_PIXELS_AVAILABLE"
    elif raster_processed and valid_pixels == 0:
        pixel_status = "INSUFFICIENT_VALID_PIXELS"
    else:
        pixel_status = "PENDING_DOWNLOAD"

    # 4. Model Domain & Mineral-Specific Validation Check
    in_manganese_domain = is_within_tile(lat, lon)  # Tile T44QMK

    if canonical_mineral == "Manganese":
        if in_manganese_domain:
            model_domain_status = "WITHIN_MODEL_DOMAIN"
            model_training_status = "TRAINED_AND_VALIDATED"
            prediction_eligible = True
            model_reason = "Target lies within Sentinel-2 Tile T44QMK where the Manganese Random Forest model is trained and spatially validated."
        else:
            model_domain_status = "OUTSIDE_MODEL_DOMAIN"
            model_training_status = "TRAINED_BUT_OUT_OF_DOMAIN"
            prediction_eligible = False
            model_reason = "Manganese model is trained strictly within Tile T44QMK (Balaghat-Nagpur corridor). Out-of-tile prediction is withheld to prevent regional covariate shift."
    elif canonical_mineral == "Iron Ore":
        model_domain_status = "MODEL_UNAVAILABLE"
        model_training_status = "SPATIAL_VALIDATION_FAILED_AWAITING_GEOPHYSICS"
        prediction_eligible = False
        model_reason = "Iron Ore spatial validation demonstrated 47.7% leave-deposit-out accuracy. Predictive prospectivity scores remain withheld until authoritative GSI aeromagnetic tensor grids are integrated."
    elif canonical_mineral == "Coal":
        model_domain_status = "MODEL_UNAVAILABLE"
        model_training_status = "UNAVAILABLE_NO_SUBSURFACE_DATA"
        prediction_eligible = False
        model_reason = "Optical satellite reflectance cannot sense subsurface coal seams under overburden. Subsurface borehole logs are required before a defensible model can be trained."
    elif canonical_mineral == "Bauxite":
        model_domain_status = "MODEL_UNAVAILABLE"
        model_training_status = "UNAVAILABLE_NO_CHEMICAL_ASSAYS"
        prediction_eligible = False
        model_reason = "Optical SWIR sensors detect Al-OH absorption, but cannot determine chemical ore grade (Al2O3 >= 40%). XRF assay drill logs are required before training."
    else:
        model_domain_status = "MODEL_UNAVAILABLE"
        model_training_status = "UNKNOWN_COMMODITY"
        prediction_eligible = False
        model_reason = f"No exploration model available for commodity '{canonical_mineral}'."

    # 5. Synthesize Overall Eligibility Status
    if pixel_status == "INSUFFICIENT_VALID_PIXELS":
        overall_eligibility = "INSUFFICIENT_VALID_PIXELS"
        explanation = f"Exploration footprint has 0 valid pixels after cloud/shadow masking ({cloud_pct}% cloud cover). Analysis cannot proceed reliably."
    elif satellite_status == "NO_SATELLITE_DATA":
        overall_eligibility = "NO_SATELLITE_DATA"
        explanation = "No cloud-free Sentinel-2 satellite passes discovered in Copernicus catalogue for this location."
    elif canonical_mineral == "Manganese" and in_manganese_domain and (raster_processed or sat_scenes):
        overall_eligibility = "ELIGIBLE_FOR_ANALYSIS"
        explanation = "Target meets all geographic, spectral, and model validity criteria for Manganese exploration mapping."
    elif canonical_mineral == "Manganese" and not in_manganese_domain:
        overall_eligibility = "OUTSIDE_MODEL_DOMAIN"
        explanation = "Target is outside the validated Manganese model domain (Tile T44QMK). Evidence analysis is active, but predictive score is withheld."
    else:
        # Coal, Iron Ore, Bauxite
        overall_eligibility = "EVIDENCE_ONLY"
        explanation = f"Geological and remote-sensing evidence analysis is active for {canonical_mineral}. Predictive machine-learning scores are withheld to maintain scientific integrity."

    limitations = [
        model_reason,
        "A known mineral occurrence is evidence of a metallogenic trend, not proof of an economic deposit at every nearby coordinate.",
        "Visual rock specimen classifier is independent of geographical prospectivity modeling."
    ]

    supported_actions = [
        "View 2D cartographic map and verified reference mines.",
        "Inspect regional geological terranes, lithology, and host stratigraphy.",
        "Explore 3D terrain elevation and geomorphology."
    ]
    if prediction_eligible:
        supported_actions.append("Render calibrated 3D prospectivity surface mesh.")

    return {
        "status": overall_eligibility,
        "overall_eligibility": overall_eligibility,
        "is_within_india": True,
        "mineral": canonical_mineral,
        "latitude": lat,
        "longitude": lon,
        "radius_km": radius_km,
        "territorial_status": "WITHIN_TERRITORY",
        "satellite_status": satellite_status,
        "pixel_status": pixel_status,
        "model_domain_status": model_domain_status,
        "model_training_status": model_training_status,
        "prediction_eligible": prediction_eligible,
        "evidence_eligible": True,
        "valid_pixels": valid_pixels,
        "cloud_cover_pct": cloud_pct,
        "model_domain_tile": "T44QMK" if canonical_mineral == "Manganese" else None,
        "explanation": explanation,
        "model_reason": model_reason,
        "limitations": limitations,
        "supported_actions": supported_actions
    }
