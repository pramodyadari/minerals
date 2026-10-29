"""
Test suite for Phase 2: Authentic Noamundi Processed Evidence & Provenance API.
Validates:
- Real processed record retrieval for Noamundi Iron Ore (22.15°N, 85.50°E, 10 km)
- Exact pixel accounting (12,851 total, 4,640 valid / 36.11%, 6,190 cloud / 48.17%, 2,021 shadow / 15.73%, 0 nodata)
- Quadrant coverage breakdown (NE clearest at 51.3%)
- Scientific guardrail enforcement: ai_prospectivity_score is None, model_confidence is None
- Non-extrapolation: mismatched coordinates or radii return NO_PROCESSED_RECORD
- /api/spectral-ratios endpoint behavior (valid for Noamundi & Balaghat, 400 for out-of-bounds)
- Supplementary endpoints /api/health and /api/zones
"""

import os
import sys
import pytest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)


def test_noamundi_processed_evidence_endpoint():
    """
    Validates genuine Noamundi Iron Ore evidence returned from /evidence/processed:
    - Target: 22.15°N, 85.50°E, 10 km radius
    - Satellite product & acquisition timestamp
    - Tile T45QUE & CRS EPSG:32645
    - 7 bands verified with native resolutions
    - Verified pixel counts and percentages
    - Strict scientific integrity: score and confidence are None
    """
    response = client.get("/evidence/processed?latitude=22.15&longitude=85.50&mineral=Iron%20Ore&radius_km=10.0")
    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "SUCCESS"
    assert data["is_covered"] is True
    assert data["processing_status"] == "COMPLETED"

    # Coordinates & Radius
    assert data["target_coordinates"]["latitude"] == 22.15
    assert data["target_coordinates"]["longitude"] == 85.50
    assert data["target_coordinates"]["utm_zone"] == 45
    assert data["requested_radius_km"] == 10.0

    # Satellite Product
    assert "S2A_MSIL2A_20261010T045231" in data["satellite_product"]["product_identifier"]
    assert "T45QUE" in data["satellite_product"]["product_identifier"]
    assert data["satellite_product"]["acquisition_timestamp"] == "2026-10-10T04:52:31.024000Z"
    assert data["tile_info"]["tile_identifier"] == "T45QUE"
    assert data["tile_info"]["crs"] == "EPSG:32645"

    # Bands
    bands = [b["band"] for b in data["band_availability"]]
    assert set(bands) == {"B02", "B03", "B04", "B08", "B11", "B12", "SCL"}

    # Pixel Accounting (Phase 1 verification match + Phase 3 audit enrichment)
    pa = data["pixel_accounting"]
    assert pa["total_pixels_in_radius"] == 12851
    assert pa["valid_cloud_free_pixels"] == 4640
    assert pa["valid_percentage"] == 36.11
    assert pa["cloud_masked_pixels"] == 6190
    assert pa["cloud_percentage"] == 48.17
    assert pa["shadow_masked_pixels"] == 2021
    assert pa["shadow_percentage"] == 15.73
    assert pa["nodata_pixels"] == 0
    assert pa["obscured_percentage"] == 63.89

    # Spatial audit additions: effective resolution and native accounting
    assert pa["analysis_grid_resolution_m"] == 156.25
    assert pa["analysis_grid_dimensions"] == [128, 128]
    assert "native_10m_accounting" in pa
    n10 = pa["native_10m_accounting"]
    assert n10["total_pixels_in_radius"] == 3141587
    assert n10["valid_pixels"] == 1132448
    assert n10["valid_percentage"] == 36.05
    assert n10["pixel_resolution_m"] == 10

    assert "native_20m_accounting" in pa
    n20 = pa["native_20m_accounting"]
    assert n20["total_pixels_in_radius"] == 785401
    assert n20["valid_pixels"] == 283013
    assert n20["valid_percentage"] == 36.03
    assert n20["pixel_resolution_m"] == 20

    # Quadrant Coverage
    qc = data["quadrant_coverage"]
    assert qc["NE"]["valid_pct"] == 51.3
    assert qc["NW"]["valid_pct"] == 32.1
    assert qc["SW"]["valid_pct"] == 28.9
    assert qc["SE"]["valid_pct"] == 32.1

    # Spectral Indices
    indices = {idx["index_name"]: idx for idx in data["spectral_indices"]}
    assert "Ferric Iron (Fe3+) Oxide Ratio" in indices
    assert indices["Ferric Iron (Fe3+) Oxide Ratio"]["value"] == 0.979
    assert "B04 / B02" in indices["Ferric Iron (Fe3+) Oxide Ratio"]["formula"]

    assert "Ferrous Iron (Fe2+) Silicate Ratio" in indices
    assert indices["Ferrous Iron (Fe2+) Silicate Ratio"]["value"] == 0.768
    assert "B11 / B08" in indices["Ferrous Iron (Fe2+) Silicate Ratio"]["formula"]

    # Scientific Guardrail & Null Model Predictions
    assert data["model_availability"]["ai_prospectivity_score"] is None
    assert data["model_availability"]["model_confidence"] is None
    assert data["model_availability"]["model_coverage"] == "NO_MODEL_FOR_COMMODITY"
    assert data["model_availability"]["prediction_availability"] == "UNAVAILABLE_NO_MODEL"
    assert "no validated spatial iron ore model" in data["model_availability"]["status_label"].lower()
    assert "manganese" not in data["model_availability"]["commodity"].lower()

    # Data Quality Warning (36.11% warning)
    all_warnings = " ".join(data["data_quality_warnings"])
    assert "36.11%" in all_warnings
    assert "cloud" in all_warnings.lower()


def test_api_evidence_processed_alias():
    """Validates that /api/evidence/processed alias returns identical payload."""
    res1 = client.get("/evidence/processed?latitude=22.15&longitude=85.50&mineral=Iron%20Ore&radius_km=10.0")
    res2 = client.get("/api/evidence/processed?latitude=22.15&longitude=85.50&mineral=Iron%20Ore&radius_km=10.0")
    assert res1.status_code == 200
    assert res2.status_code == 200
    assert res1.json() == res2.json()


def test_different_location_returns_no_processed_record():
    """
    Validates that querying a location outside Noamundi (e.g. Balaghat) does NOT
    falsely reuse Noamundi evidence.
    """
    response = client.get("/evidence/processed?latitude=21.9048&longitude=80.1849&mineral=Iron%20Ore&radius_km=10.0")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "NO_PROCESSED_RECORD"
    assert data["is_covered"] is False
    assert "new satellite imagery must be acquired" in data["message"].lower()
    assert data["ai_prospectivity_score"] is None
    assert data["model_confidence"] is None


def test_different_radius_returns_no_processed_record():
    """
    Validates that querying a different radius (e.g. 25 km) for Noamundi does NOT
    falsely reuse 10 km coverage statistics.
    """
    response = client.get("/evidence/processed?latitude=22.15&longitude=85.50&mineral=Iron%20Ore&radius_km=25.0")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "NO_PROCESSED_RECORD"
    assert data["is_covered"] is False
    assert data["ai_prospectivity_score"] is None


def test_smaller_radius_returns_no_processed_record():
    """
    Validates that querying a smaller radius (e.g. 5 km) for Noamundi does NOT
    falsely reuse 10 km coverage statistics.
    """
    response = client.get("/evidence/processed?latitude=22.15&longitude=85.50&mineral=Iron%20Ore&radius_km=5.0")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "NO_PROCESSED_RECORD"
    assert data["is_covered"] is False
    assert data["ai_prospectivity_score"] is None


def test_invalid_parameters_return_bad_request():
    """
    Validates that invalid geographic coordinates or non-positive radius return 400 Bad Request.
    """
    # 1. Latitude > 90
    res1 = client.get("/evidence/processed?latitude=999.0&longitude=85.50&mineral=Iron%20Ore&radius_km=10.0")
    assert res1.status_code == 400
    assert "invalid" in res1.json()["message"].lower()

    # 2. Latitude < -90
    res2 = client.get("/evidence/processed?latitude=-120.0&longitude=85.50&mineral=Iron%20Ore&radius_km=10.0")
    assert res2.status_code == 400

    # 3. Longitude > 180
    res3 = client.get("/evidence/processed?latitude=22.15&longitude=300.0&mineral=Iron%20Ore&radius_km=10.0")
    assert res3.status_code == 400

    # 4. Radius <= 0
    res4 = client.get("/evidence/processed?latitude=22.15&longitude=85.50&mineral=Iron%20Ore&radius_km=-5.0")
    assert res4.status_code == 400

    res5 = client.get("/evidence/processed?latitude=22.15&longitude=85.50&mineral=Iron%20Ore&radius_km=0.0")
    assert res5.status_code == 400

    # 5. Non-numeric parameter returns 422
    res6 = client.get("/evidence/processed?latitude=invalid_lat&longitude=85.50&mineral=Iron%20Ore&radius_km=10.0")
    assert res6.status_code == 422


def test_different_mineral_returns_no_processed_record():
    """
    Validates that selecting Coal at Noamundi does not falsely claim processed Iron Ore evidence.
    """
    response = client.get("/evidence/processed?latitude=22.15&longitude=85.50&mineral=Coal&radius_km=10.0")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "NO_PROCESSED_RECORD"
    assert data["is_covered"] is False


def test_spectral_ratios_endpoint_noamundi():
    """Validates /api/spectral-ratios returns genuine Noamundi ratios without simulation."""
    response = client.get("/api/spectral-ratios?lat=22.15&lon=85.50&radius=10.0")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["data_availability"]["is_simulated"] is False
    assert data["ratios"]["ferrous_minerals"]["target_value"] == 0.768
    assert data["ratios"]["clay_minerals"]["target_value"] == 1.410
    assert data["ratios"]["iron_oxide"]["target_value"] == 0.979


def test_spectral_ratios_endpoint_out_of_bounds():
    """Validates /api/spectral-ratios returns 400 Bad Request for coordinates outside India."""
    response = client.get("/api/spectral-ratios?lat=0&lon=0&radius=25.0")
    assert response.status_code == 400
    data = response.json()
    assert data["status"] == "error"
    assert "outside" in data["message"].lower()


def test_supplementary_api_endpoints():
    """Validates /api/health and /api/zones."""
    h_res = client.get("/api/health")
    assert h_res.status_code == 200
    assert h_res.json()["status"] == "healthy"

    z_res = client.get("/api/zones")
    assert z_res.status_code == 200
    z_data = z_res.json()
    assert z_data["status"] == "success"
    assert len(z_data["zones"]) == 20
