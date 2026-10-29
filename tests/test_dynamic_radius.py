"""
================================================================================
AI MINERAL EXPLORATION — DYNAMIC EXPLORATION RADIUS & 50 KM VALIDATION TESTS
================================================================================
Tests:
1. All 5 radius values: 1 km, 5 km, 10 km, 25 km, 50 km.
2. Exact circular survey area calculations (π × r²):
   - 1 km  -> 3.14 km²
   - 5 km  -> 78.54 km²
   - 10 km -> 314.16 km²
   - 25 km -> 1,963.50 km²
   - 50 km -> 7,853.98 km²
3. Backend parameter synchronization on /analyze with all 5 radius values.
4. Multi-tile boundary intersection detection at 50 km.
5. Scientific guardrails:
   - 50 km does NOT fabricate predictions for Coal, Iron Ore, or Bauxite.
   - 50 km outside Tile T44QMK does NOT fabricate predictions for Manganese.
   - Coordinates outside India are rejected regardless of radius.
================================================================================
"""

import math
import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.raster_ingestion_service import analyze_tile_intersections

client = TestClient(app)

RADIUS_TEST_CASES = [
    (1.0, 3.14),
    (5.0, 78.54),
    (10.0, 314.16),
    (25.0, 1963.50),
    (50.0, 7853.98),
]


def test_geometric_survey_area_formula():
    """Validates exact geometric circular survey area: Area = π × radius²."""
    for r, expected_area in RADIUS_TEST_CASES:
        calc_area = round(math.pi * (r ** 2), 2)
        assert calc_area == expected_area, f"Radius {r}km expected {expected_area} km², got {calc_area} km²"


@pytest.mark.parametrize("radius_km,expected_area", RADIUS_TEST_CASES)
def test_backend_analysis_parameter_sync_all_radii(radius_km, expected_area):
    """Verifies backend /analyze accepts each of the five radius values and synchronizes survey area."""
    payload = {
        "location_name": "Balaghat Reference Corridor",
        "latitude": 21.9048,
        "longitude": 80.1849,
        "mineral": "Manganese",
        "radius_km": radius_km
    }
    response = client.post("/analyze", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["radius_km"] == radius_km
    assert data["area_sq_km"] == expected_area
    assert data["overall_status"] == "SUCCESS"
    assert data["prediction"] is not None
    assert "prospectivity_index" in data["prediction"]


def test_50km_multi_tile_boundary_intersection():
    """Verifies that 50 km radius correctly triggers multi-tile boundary intersection detection."""
    info = analyze_tile_intersections(21.9048, 80.1849, radius_km=50.0)
    assert info["tile_boundary_crossed"] is True
    assert "crosses Sentinel-2 tile boundaries" in info["multi_tile_coverage_note"]
    assert info["utm_bounding_box"]["easting_max"] - info["utm_bounding_box"]["easting_min"] == 100000.0  # 100 km box


def test_50km_scientific_guardrails_coal_no_fabricated_prediction():
    """Verifies 50 km exploration radius does NOT bypass Coal guardrails (no subsurface optical predictions)."""
    payload = {
        "location_name": "Manuguru Coalfield",
        "latitude": 17.9500,
        "longitude": 80.7800,
        "mineral": "Coal",
        "radius_km": 50.0
    }
    response = client.post("/analyze", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["radius_km"] == 50.0
    assert data["area_sq_km"] == 7853.98
    assert data["model_coverage"] == "NO_MODEL_FOR_COMMODITY"
    assert data["prediction_availability"] == "UNAVAILABLE_NO_MODEL"
    assert data["prediction"] is None


def test_50km_scientific_guardrails_iron_ore_no_fabricated_prediction():
    """Verifies 50 km exploration radius does NOT bypass Iron Ore guardrails (surface gossan != ore body)."""
    payload = {
        "location_name": "Noamundi Iron Mine",
        "latitude": 22.1500,
        "longitude": 85.5000,
        "mineral": "Iron Ore",
        "radius_km": 50.0
    }
    response = client.post("/analyze", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["radius_km"] == 50.0
    assert data["area_sq_km"] == 7853.98
    assert data["model_coverage"] == "NO_MODEL_FOR_COMMODITY"
    assert data["prediction_availability"] == "UNAVAILABLE_NO_MODEL"
    assert data["prediction"] is None


def test_50km_scientific_guardrails_bauxite_no_fabricated_prediction():
    """Verifies 50 km exploration radius does NOT bypass Bauxite guardrails (laterite != gibbsitic bauxite)."""
    payload = {
        "location_name": "Panchpatmali Bauxite Plateau",
        "latitude": 18.8200,
        "longitude": 83.0000,
        "mineral": "Bauxite",
        "radius_km": 50.0
    }
    response = client.post("/analyze", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["radius_km"] == 50.0
    assert data["area_sq_km"] == 7853.98
    assert data["model_coverage"] == "NO_MODEL_FOR_COMMODITY"
    assert data["prediction_availability"] == "UNAVAILABLE_NO_MODEL"
    assert data["prediction"] is None


def test_50km_manganese_outside_t44qmk_no_fabricated_prediction():
    """Verifies 50 km Manganese analysis outside Tile T44QMK halts safely without extrapolating Balaghat model."""
    payload = {
        "location_name": "Sandur Manganese Belt, Bellary, Karnataka",
        "latitude": 15.0800,
        "longitude": 76.5500,
        "mineral": "Manganese",
        "radius_km": 50.0
    }
    response = client.post("/analyze", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["radius_km"] == 50.0
    assert data["model_coverage"] == "OUTSIDE_TRAINING_FOOTPRINT"
    assert data["prediction_availability"] == "UNAVAILABLE_UNVALIDATED_REGION"
    assert data["prediction"] is None


def test_50km_outside_india_sovereign_boundary_rejected():
    """Verifies coordinates outside India are rejected even with 50 km radius."""
    payload = {
        "location_name": "International Waters",
        "latitude": 0.0,
        "longitude": 0.0,
        "mineral": "Manganese",
        "radius_km": 50.0
    }
    response = client.post("/analyze", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["overall_status"] == "OUTSIDE_INDIA_TERRITORY"
    assert data["prediction"] is None
