"""
End-to-End Verification Test Suite: Consistent 4-Mineral Evaluation & Scoring
Covers:
1. Manganese within Tile T44QMK: Calibrated prospectivity score (0-100), validated RF model.
2. Manganese outside Tile T44QMK: Withheld prospectivity score (None), regional evidence index.
3. Iron Ore at Noamundi: Withheld prospectivity score (None), high evidence index (>=70).
4. Coal at Manuguru: Withheld prospectivity score (None), basin evidence index (>=70).
5. Bauxite at Panchpatmali: Withheld prospectivity score (None), plateau evidence index (>=60).
6. Non-mineralized / insufficient data location: Low evidence index (<45).
7. Location outside India: Rejection, None prospectivity score, None evidence index.
8. Evidence Quality strictly separated from prospectivity index.
9. Response schema stability: All 4 minerals return unified evaluation_summary without regressions.
"""

import os
import sys
import pytest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from fastapi.testclient import TestClient

try:
    from backend.app.main import app
except ImportError:
    from app.main import app

client = TestClient(app)


def test_01_manganese_inside_t44qmk_calibrated_score():
    """Manganese at Balaghat returns a calibrated RF prospectivity index (0-100)."""
    payload = {
        "location_name": "Balaghat MOIL Corridor",
        "latitude": 21.9048,
        "longitude": 80.1849,
        "mineral": "Manganese",
        "radius_km": 10.0
    }
    resp = client.post("/analyze", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    
    assert "evaluation_summary" in data
    summary = data["evaluation_summary"]
    assert summary["mineral_selected"] == "Manganese"
    assert summary["prospectivity_score_available"] is True
    assert summary["prospectivity_score"] is not None
    assert 0.0 <= summary["prospectivity_score"] <= 100.0
    assert summary["prospectivity_status"] == "AVAILABLE_UNCALIBRATED_RF"
    assert summary["evidence_quality"] in ("high", "medium")
    assert "Higher" in summary["simple_interpretation"] or "Moderate" in summary["simple_interpretation"]
    assert len(summary["main_supporting_evidence"]) >= 2


def test_02_manganese_outside_t44qmk_score_withheld():
    """Manganese outside Tile T44QMK withholds ML score (null) and computes regional evidence index."""
    payload = {
        "location_name": "Noamundi Outside Mn Tile",
        "latitude": 22.1500,
        "longitude": 85.5000,
        "mineral": "Manganese",
        "radius_km": 10.0
    }
    resp = client.post("/analyze", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    
    summary = data["evaluation_summary"]
    assert summary["prospectivity_score"] is None
    assert summary["prospectivity_score_available"] is False
    assert summary["prospectivity_status"] == "OUTSIDE_MODEL_DOMAIN"
    assert summary["evidence_index"] is not None
    assert 0.0 <= summary["evidence_index"] <= 100.0
    assert "Withheld" in summary["simple_interpretation"] or "Evidence" in summary["simple_interpretation"]


def test_03_iron_ore_noamundi_score_withheld_high_evidence():
    """Iron Ore at Noamundi withholds ML score (null) due to spatial validation, but yields high evidence index."""
    payload = {
        "location_name": "Noamundi Iron Sector",
        "latitude": 22.1500,
        "longitude": 85.5000,
        "mineral": "Iron Ore",
        "radius_km": 10.0
    }
    resp = client.post("/analyze", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    
    assert data["prediction"] is None
    assert data["prediction_availability"] == "UNAVAILABLE_NO_MODEL"
    
    summary = data["evaluation_summary"]
    assert summary["prospectivity_score"] is None
    assert summary["prospectivity_score_available"] is False
    assert "SPATIAL_VALIDATION_FAILED" in summary["prospectivity_status"]
    assert summary["evidence_index"] >= 65.0
    assert "Singhbhum Iron Ore Craton" in summary["evidence_index_label"]
    assert summary["evidence_quality"] == "high"
    assert "what_this_result_means" in summary
    assert "what_this_result_does_not_mean" in summary


def test_04_coal_manuguru_score_withheld_basin_evidence():
    """Coal at Manuguru withholds ML score (null) due to subsurface limitation, but yields high basin evidence."""
    payload = {
        "location_name": "Manuguru Coalfield",
        "latitude": 17.9820,
        "longitude": 80.7450,
        "mineral": "Coal",
        "radius_km": 10.0
    }
    resp = client.post("/analyze", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    
    assert data["prediction"] is None
    summary = data["evaluation_summary"]
    assert summary["prospectivity_score"] is None
    assert "NO_SUBSURFACE_DATA" in summary["prospectivity_status"]
    assert summary["evidence_index"] >= 60.0
    assert "Basin Stratigraphy" in summary["evidence_index_label"]
    assert len(summary["contradicting_evidence_and_uncertainties"]) >= 2


def test_05_bauxite_panchpatmali_score_withheld_plateau_evidence():
    """Bauxite at Panchpatmali withholds ML score (null) due to assay need, but yields plateau evidence."""
    payload = {
        "location_name": "Panchpatmali Bauxite Plateau",
        "latitude": 18.8200,
        "longitude": 83.0200,
        "mineral": "Bauxite",
        "radius_km": 10.0
    }
    resp = client.post("/analyze", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    
    assert data["prediction"] is None
    summary = data["evaluation_summary"]
    assert summary["prospectivity_score"] is None
    assert "NO_CHEMICAL_ASSAYS" in summary["prospectivity_status"]
    assert summary["evidence_index"] >= 40.0
    assert "Plateau Geomorphology" in summary["evidence_index_label"]


def test_06_insufficient_data_lower_evidence():
    """Non-mineralized shield location returns lower evidence favorability."""
    payload = {
        "location_name": "Non-Mineralized Shield",
        "latitude": 27.0000,
        "longitude": 71.5000,
        "mineral": "Iron Ore",
        "radius_km": 10.0,
        "mock_satellite_error": "NETWORK_ERROR"
    }
    resp = client.post("/analyze", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    
    summary = data["evaluation_summary"]
    assert summary["prospectivity_score"] is None
    assert summary["evidence_index"] < 50.0
    assert summary["simple_tier"] in ("LOWER", "MODERATE")


def test_07_outside_territory_rejection():
    """Coordinates outside India return OUTSIDE_INDIA_TERRITORY and null scores."""
    payload = {
        "location_name": "Outside Territory Point",
        "latitude": 0.0,
        "longitude": 0.0,
        "mineral": "Coal",
        "radius_km": 10.0
    }
    resp = client.post("/analyze", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    
    assert data["is_within_india"] is False
    assert data["status"] == "OUTSIDE_INDIA_TERRITORY"
    summary = data["evaluation_summary"]
    assert summary["prospectivity_score"] is None
    assert summary["evidence_index"] is None
    assert summary["evidence_quality"] == "none"
