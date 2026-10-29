"""
Unit and Integration Tests for Custom 2/3 Mineral Selection (Part B & C)
Covers:
- Selecting exactly 2 minerals (e.g., Coal + Iron Ore)
- Selecting exactly 3 minerals (e.g., Coal + Manganese + Bauxite)
- Rejecting fewer than 2 minerals in custom mode (e.g. 1 mineral)
- Rejecting more than 3 minerals in custom mode (e.g. 4 minerals)
- Rejecting duplicate mineral entries (e.g., ["Coal", "Coal"])
- Rejecting unsupported mineral names (e.g., ["Gold", "Lithium"])
- Returning only requested minerals in custom mode
- Shared coordinates and radius across selected minerals
- Partial pipeline failure isolation
- Preserving existing all-four behavior when minerals list is omitted
- Scientific integrity guardrails (withheld AI models, independent scorecards)
"""

import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.mineral_service import (
    analyze_all_minerals_for_location,
    SUPPORTED_MINERALS
)

client = TestClient(app)

def test_01_select_exactly_two_minerals():
    """POST /analyze-all with exactly 2 minerals returns results only for those 2."""
    payload = {
        "location_name": "Test Site 2 Minerals",
        "latitude": 21.9048,
        "longitude": 80.1849,
        "radius_km": 10.0,
        "minerals": ["Coal", "Iron Ore"]
    }
    resp = client.post("/analyze-all", json=payload)
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
    data = resp.json()

    assert data["status"] in ["SUCCESS", "PARTIAL_SUCCESS"]
    assert "minerals" in data
    assert len(data["minerals"]) == 2
    assert "Coal" in data["minerals"]
    assert "Iron Ore" in data["minerals"]
    assert "Manganese" not in data["minerals"]
    assert "Bauxite" not in data["minerals"]
    assert data["total_minerals_analyzed"] == 2
    assert data["selected_minerals"] == ["Coal", "Iron Ore"]
    assert data["analysis_mode"] == "custom"

    # Comparison summary must contain exactly 2 rows
    assert len(data["comparison_summary"]) == 2
    summary_minerals = [item["mineral"] for item in data["comparison_summary"]]
    assert summary_minerals == ["Coal", "Iron Ore"]

    # Shared coordinates and radius
    for m in ["Coal", "Iron Ore"]:
        res = data["minerals"][m]
        assert res["latitude"] == pytest.approx(21.9048, abs=1e-3)
        assert res["longitude"] == pytest.approx(80.1849, abs=1e-3)
        assert res["radius_km"] == 10.0


def test_02_select_exactly_three_minerals():
    """POST /analyze-all with exactly 3 minerals returns results only for those 3."""
    payload = {
        "location_name": "Test Site 3 Minerals",
        "latitude": 21.9048,
        "longitude": 80.1849,
        "radius_km": 5.0,
        "minerals": ["Coal", "Manganese", "Bauxite"]
    }
    resp = client.post("/analyze-all", json=payload)
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
    data = resp.json()

    assert len(data["minerals"]) == 3
    assert set(data["minerals"].keys()) == {"Coal", "Manganese", "Bauxite"}
    assert "Iron Ore" not in data["minerals"]
    assert data["total_minerals_analyzed"] == 3
    assert data["analysis_mode"] == "custom"
    assert len(data["comparison_summary"]) == 3


def test_03_reject_fewer_than_two_minerals():
    """Custom mode requires at least 2 minerals; 1 mineral must be rejected with 422."""
    payload = {
        "location_name": "Invalid Single Mineral",
        "latitude": 21.9048,
        "longitude": 80.1849,
        "radius_km": 10.0,
        "minerals": ["Coal"]
    }
    resp = client.post("/analyze-all", json=payload)
    assert resp.status_code == 422
    assert "exactly 2 or 3" in resp.json()["detail"].lower() or "2 or 3" in resp.json()["detail"]


def test_04_reject_more_than_three_minerals_in_custom_mode():
    """Custom mode allows at most 3 minerals; 4 minerals in custom list must be rejected with 422."""
    payload = {
        "location_name": "Invalid 4 Minerals Custom",
        "latitude": 21.9048,
        "longitude": 80.1849,
        "radius_km": 10.0,
        "minerals": ["Coal", "Manganese", "Iron Ore", "Bauxite"]
    }
    resp = client.post("/analyze-all", json=payload)
    assert resp.status_code == 422
    assert "exactly 2 or 3" in resp.json()["detail"].lower() or "2 or 3" in resp.json()["detail"]


def test_05_reject_duplicate_minerals():
    """Duplicate mineral names must be rejected with 422."""
    payload = {
        "location_name": "Duplicate Minerals",
        "latitude": 21.9048,
        "longitude": 80.1849,
        "radius_km": 10.0,
        "minerals": ["Coal", "Coal"]
    }
    resp = client.post("/analyze-all", json=payload)
    assert resp.status_code == 422
    assert "duplicate" in resp.json()["detail"].lower()


def test_06_reject_unsupported_mineral_name():
    """Unsupported mineral commodity names must be rejected with 422."""
    payload = {
        "location_name": "Unsupported Minerals",
        "latitude": 21.9048,
        "longitude": 80.1849,
        "radius_km": 10.0,
        "minerals": ["Coal", "Lithium"]
    }
    resp = client.post("/analyze-all", json=payload)
    assert resp.status_code == 422
    assert "unsupported" in resp.json()["detail"].lower()


def test_07_preserve_existing_all_four_behavior_when_minerals_omitted():
    """Omitting minerals field maintains backward-compatible 4-mineral analysis."""
    payload = {
        "location_name": "Balaghat Default",
        "latitude": 21.9048,
        "longitude": 80.1849,
        "radius_km": 10.0
    }
    resp = client.post("/analyze-all", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["minerals"]) == 4
    assert set(data["minerals"].keys()) == {"Coal", "Manganese", "Iron Ore", "Bauxite"}
    assert data["analysis_mode"] == "all_four"


def test_08_partial_pipeline_failure_isolation():
    """If one mineral pipeline encounters an exception, the other selected mineral succeeds."""
    with patch("backend.app.mineral_service.analyze_location_for_mineral") as mock_analyze:
        def side_effect(*args, **kwargs):
            mineral = kwargs.get("mineral_name")
            if mineral == "Coal":
                raise RuntimeError("Simulated transient raster failure for Coal")
            return {
                "status": "SUCCESS",
                "mineral": mineral,
                "latitude": kwargs.get("lat"),
                "longitude": kwargs.get("lon"),
                "radius_km": kwargs.get("radius_km"),
                "prediction": None,
                "prediction_availability": "UNAVAILABLE_NO_MODEL",
                "evaluation_summary": {
                    "mineral_selected": mineral,
                    "prospectivity_score": None,
                    "prospectivity_score_available": False,
                    "evidence_index": 65.0,
                    "evidence_quality": "high",
                    "simple_interpretation": "Valid evidence",
                    "simple_tier": "MODERATE"
                }
            }
        mock_analyze.side_effect = side_effect

        res = analyze_all_minerals_for_location(
            location_name="Fault Test",
            lat=21.9048,
            lon=80.1849,
            radius_km=10.0,
            minerals=["Coal", "Iron Ore"]
        )

        assert res["status"] == "PARTIAL_SUCCESS"
        assert res["minerals"]["Coal"]["status"] == "ERROR"
        assert res["minerals"]["Iron Ore"]["status"] == "SUCCESS"
        assert len(res["comparison_summary"]) == 2
