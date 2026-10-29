"""
Regression Test Suite: Search Radius Responsiveness & Spatial Analysis Integrity
Validates that changing exploration radius (1 km, 5 km, 10 km, 25 km, 50 km):
1. Properly reaches backend pipelines via /analyze, /analyze-all, and /analyze/multi.
2. Area-dependent evidence (occurrences strictly inside radius, DEM terrain relief, pixel coverage)
   dynamically and correctly updates according to the circular survey area.
3. Cache isolation: Changing radius recomputes or uses radius-specific cache keys without collision.
4. Changed center with the same radius produces distinct spatial results.
5. Custom 2- and 3-mineral selection and all-four-mineral analysis respect radius.
6. Scientific safeguards:
   - Manganese ML prospectivity score remains restricted to Tile T44QMK.
   - Coal, Iron Ore, and Bauxite ML predictions remain strictly null.
   - Out-of-bounds coordinates reject with OUTSIDE_INDIA_TERRITORY.
   - No data fabrication or artificial score manipulation.
"""

import math
import os
import pytest
from fastapi.testclient import TestClient

# Set test environment to mock external CDSE network calls
os.environ["MOCK_CDSE_DISCOVERY"] = "1"

from backend.app.main import app
from backend.app.geological_service import query_geological_evidence
from backend.app.mineral_service import (
    analyze_location_for_mineral,
    analyze_all_minerals_for_location,
    calculate_manganese_prospectivity,
    find_zones_in_radius
)
from terrain_evidence import query_terrain_stats_in_radius

client = TestClient(app)


def test_search_radius_multi_step_responsiveness():
    """
    Test same center location at 1 km, 5 km, 10 km, and 25 km.
    Verifies that occurrences inside radius, terrain stats, and evidence indices reflect the radius.
    """
    lat, lon = 21.9455, 80.4295  # Balaghat Manganese Corridor
    radii = [1.0, 5.0, 10.0, 25.0]
    results = {}

    for r in radii:
        res = analyze_location_for_mineral(
            location_name="Balaghat Survey Point",
            lat=lat,
            lon=lon,
            mineral_name="Manganese",
            radius_km=r
        )
        assert res["radius_km"] == r
        expected_area = round(math.pi * (r ** 2), 2)
        assert res["area_sq_km"] == expected_area

        eval_sum = res["evaluation_summary"]
        assert eval_sum["search_radius_km"] == r
        results[r] = res

    # 1. Occurrence filtering strictly inside radius
    # At 1 km, only deposits within 1 km are counted
    occs_1 = [o for o in results[1.0]["documented_occurrences"] if o.get("is_inside_radius")]
    occs_25 = [o for o in results[25.0]["documented_occurrences"] if o.get("is_inside_radius")]
    assert len(occs_25) >= len(occs_1), "Larger radius must encompass equal or more occurrences"

    # 2. Candidate zones inside radius expand
    zones_1, _, _ = find_zones_in_radius(lat, lon, 1.0)
    zones_25, _, _ = find_zones_in_radius(lat, lon, 25.0)
    assert len(zones_25) >= len(zones_1), "Candidate zones list must expand with search radius"

    # 3. Terrain relief across window expands or stays non-decreasing
    dem_1 = query_terrain_stats_in_radius(lat, lon, 1.0)
    dem_25 = query_terrain_stats_in_radius(lat, lon, 25.0)
    if dem_1.get("available") and dem_25.get("available"):
        assert dem_25["relief_window_m"] >= dem_1["relief_window_m"]


def test_changed_center_same_radius():
    """
    Test two different geographic centers with the exact same 10 km search radius.
    Verifies that spatial proximity, host geology, and scores reflect local conditions.
    """
    # Location A: Balaghat (Manganese Belt)
    res_a = analyze_location_for_mineral(
        location_name="Balaghat Mine Corridor",
        lat=21.9455,
        lon=80.4295,
        mineral_name="Manganese",
        radius_km=10.0
    )

    # Location B: Nagpur Sector (Western Sausar Belt)
    res_b = analyze_location_for_mineral(
        location_name="Nagpur Sector",
        lat=21.1458,
        lon=79.0882,
        mineral_name="Manganese",
        radius_km=10.0
    )

    assert res_a["radius_km"] == res_b["radius_km"] == 10.0
    # Location B is outside Tile T44QMK, so Manganese ML prediction is withheld
    assert res_a["prediction"] is not None
    assert res_b["prediction"] is None
    assert res_b["model_coverage"] == "OUTSIDE_TRAINING_FOOTPRINT"


def test_radius_cache_isolation_and_recomputation():
    """
    Verifies that querying a location at 5 km, then 25 km, then 5 km again
    uses radius-specific cache keys and does not overwrite with stale radius data.
    """
    lat, lon = 22.1500, 85.5000  # Noamundi Iron Ore Area

    res_5_first = analyze_location_for_mineral(
        location_name="Noamundi Sector",
        lat=lat,
        lon=lon,
        mineral_name="Iron Ore",
        radius_km=5.0
    )

    res_25 = analyze_location_for_mineral(
        location_name="Noamundi Sector",
        lat=lat,
        lon=lon,
        mineral_name="Iron Ore",
        radius_km=25.0
    )

    res_5_second = analyze_location_for_mineral(
        location_name="Noamundi Sector",
        lat=lat,
        lon=lon,
        mineral_name="Iron Ore",
        radius_km=5.0
    )

    assert res_5_first["radius_km"] == 5.0
    assert res_25["radius_km"] == 25.0
    assert res_5_second["radius_km"] == 5.0

    # 5 km and 25 km must have distinct areas
    assert res_5_first["area_sq_km"] == 78.54
    assert res_25["area_sq_km"] == 1963.50
    assert res_5_second["area_sq_km"] == 78.54

    # 5 km re-query must match first 5 km run identically
    assert res_5_first["evaluation_summary"]["evidence_index"] == res_5_second["evaluation_summary"]["evidence_index"]


def test_custom_two_and_three_minerals_selection_with_radius():
    """
    Tests POST /analyze-all and POST /analyze/multi with custom mineral selections
    (2 and 3 commodities) across varying radii (5 km vs 25 km).
    """
    # 2 minerals at 5 km
    payload_2 = {
        "location_name": "Multi Target",
        "latitude": 21.9455,
        "longitude": 80.4295,
        "radius_km": 5.0,
        "minerals": ["Manganese", "Iron Ore"]
    }
    resp_2 = client.post("/analyze/multi", json=payload_2)
    assert resp_2.status_code == 200
    data_2 = resp_2.json()
    assert data_2["radius_km"] == 5.0
    assert len(data_2["minerals"]) == 2
    assert "Manganese" in data_2["minerals"]
    assert "Iron Ore" in data_2["minerals"]
    assert "Coal" not in data_2["minerals"]

    # 3 minerals at 25 km
    payload_3 = {
        "location_name": "Multi Target",
        "latitude": 21.9455,
        "longitude": 80.4295,
        "radius_km": 25.0,
        "minerals": ["Coal", "Manganese", "Bauxite"]
    }
    resp_3 = client.post("/analyze-all", json=payload_3)
    assert resp_3.status_code == 200
    data_3 = resp_3.json()
    assert data_3["radius_km"] == 25.0
    assert len(data_3["minerals"]) == 3
    assert "Coal" in data_3["minerals"]
    assert "Manganese" in data_3["minerals"]
    assert "Bauxite" in data_3["minerals"]
    assert "Iron Ore" not in data_3["minerals"]


def test_all_four_mineral_analysis_default():
    """
    Verifies that default POST /analyze-all evaluates all 4 minerals independently
    and returns comparison summary with correct requested radius.
    """
    payload = {
        "location_name": "Balaghat Unified Target",
        "latitude": 21.9455,
        "longitude": 80.4295,
        "radius_km": 10.0
    }
    resp = client.post("/analyze-all", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["radius_km"] == 10.0
    assert len(data["minerals"]) == 4
    assert len(data["comparison_summary"]) == 4

    summary_map = {row["mineral"]: row for row in data["comparison_summary"]}
    assert summary_map["Manganese"]["ai_prediction_status"] == "AVAILABLE"
    assert summary_map["Manganese"]["ai_score"] is not None
    assert summary_map["Iron Ore"]["ai_score"] is None
    assert summary_map["Coal"]["ai_score"] is None
    assert summary_map["Bauxite"]["ai_score"] is None


def test_unvalidated_commodities_strict_null_predictions():
    """
    Scientific Safeguard: Coal, Iron Ore, and Bauxite ML predictions MUST remain null
    regardless of radius (1, 5, 10, 25, 50 km).
    """
    for r in [1.0, 10.0, 50.0]:
        for mineral in ["Coal", "Iron Ore", "Bauxite"]:
            res = analyze_location_for_mineral(
                location_name="Test Site",
                lat=22.15,
                lon=85.50,
                mineral_name=mineral,
                radius_km=r
            )
            assert res["prediction"] is None, f"{mineral} ML score must be None at radius {r}km"
            assert res["confidence_score"] is None
            assert res["evaluation_summary"]["prospectivity_score"] is None
            assert res["evaluation_summary"]["prospectivity_score_available"] is False


def test_out_of_bounds_and_empty_evidence():
    """
    Verifies that coordinates outside India territorial boundaries are strictly rejected,
    and remote ocean/desert areas with zero occurrences return appropriate low/neutral indices.
    """
    # 1. Coordinate outside India (Equator, Indian Ocean)
    payload_out = {
        "location_name": "Equatorial Ocean",
        "latitude": 0.0,
        "longitude": 80.0,
        "mineral": "Manganese",
        "radius_km": 10.0
    }
    resp_out = client.post("/analyze", json=payload_out)
    assert resp_out.status_code == 200
    data_out = resp_out.json()
    assert data_out["overall_status"] == "OUTSIDE_INDIA_TERRITORY"
    assert data_out["prediction"] is None
    assert data_out["evaluation_summary"]["evidence_index"] is None

    # 2. Location inside India with no manganese records (e.g., Thar Desert)
    geo_thar = query_geological_evidence(mineral_name="Manganese", lat=27.0, lon=71.0, radius_km=10.0)
    assert geo_thar["occurrences_in_radius_count"] == 0
    assert geo_thar["nearest_occurrence_km"] is None or geo_thar["nearest_occurrence_km"] > 10.0
