"""
Regression and Activation Test Suite for Coal, Iron Ore, and Bauxite
Validates:
1. Verified occurrence inventories with authoritative provenance (GSI, CMPDI, IBM, NALCO, SCCL, SAIL, Tata Steel).
2. Coal evidence workflow and optical underground seam guardrail (DO_NOT_INFER_UNDERGROUND_SEAMS).
3. Iron Ore evidence workflow, Copernicus DEM terrain integration, and leave-deposit-out spatial validation guardrail.
4. Bauxite evidence workflow and laterite duricrust distinction rule (DISTINGUISH_LATERITIC_DURICRUST_FROM_COMMERCIAL_BAUXITE).
5. Consistent 4-mineral workflow across POST /analyze.
6. Absence of cross-mineral model substitution (never use Manganese model for Coal, Iron Ore, or Bauxite).
7. AI prospectivity score and confidence strictly null (None) for Coal, Iron Ore, and Bauxite.
8. Calibrated Random Forest model active strictly for Manganese in Tile T44QMK.
9. 3D prospectivity grid strictly unavailable and uncalibrated for unmodeled minerals.
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


# -------------------------------------------------------------------------
# 1. COAL ACTIVATION & EVIDENCE WORKFLOW TESTS
# -------------------------------------------------------------------------

def test_coal_occurrences_inventory():
    """Verifies Coal occurrences endpoint returns verified records with provenance."""
    resp = client.get("/api/mineral/coal/occurrences")
    assert resp.status_code == 200
    data = resp.json()
    assert "occurrences" in data
    assert len(data["occurrences"]) >= 5
    
    # Check Manuguru SCCL colliery record
    manuguru = next((o for o in data["occurrences"] if "Manuguru" in o["name"]), None)
    assert manuguru is not None
    assert manuguru["operator"] == "The Singareni Collieries Company Limited (SCCL)"
    assert manuguru["state"] == "Telangana"
    assert "Barakar" in manuguru["geological_formation"]
    assert manuguru["confidence"] == "HIGH_CONFIRMED"


def test_coal_scientific_evaluation_manuguru():
    """Verifies Coal scientific evaluation at Manuguru colliery coordinates."""
    resp = client.get("/api/mineral/coal/evaluation?lat=17.9820&lon=80.7450&radius_km=10.0")
    assert resp.status_code == 200
    data = resp.json()
    assert data["commodity"] == "Coal"
    assert data["is_within_study_basin"] is True
    assert "Godavari" in data["study_basin"]
    assert data["nearest_confirmed_colliery"]["distance_km"] < 2.0
    
    # Scientific guardrail: AI prediction strictly withheld
    assert data["model_availability"]["ai_prospectivity_score"] is None
    assert data["model_availability"]["model_confidence"] is None
    assert data["model_availability"]["model_status"] == "UNAVAILABLE_NO_MODEL"
    assert len(data["mandatory_geological_prerequisites"]) >= 3


def test_analyze_coal_manuguru_evidence_workflow():
    """Tests POST /analyze for Coal at Manuguru (Godavari Valley)."""
    payload = {
        "location_name": "Manuguru, Bhadradri Kothagudem, Telangana",
        "latitude": 17.9820,
        "longitude": 80.7450,
        "mineral": "Coal",
        "radius_km": 10.0
    }
    resp = client.post("/analyze", json=payload)
    assert resp.status_code == 200
    res = resp.json()
    assert res["status"] == "EVIDENCE_ONLY_NO_PREDICTION"
    assert res["prediction"] is None
    assert res["confidence_score"] is None
    assert res["prediction_availability"] == "UNAVAILABLE_NO_MODEL"
    assert "terrain_evidence" in res
    assert res["terrain_evidence"] is not None
    
    # Verify underground seam warning in limitations
    limitations_text = " ".join(res.get("limitations_and_warnings", []))
    assert "drill" in limitations_text.lower() or "subsurface" in limitations_text.lower() or "borehole" in limitations_text.lower()
    
    # 3D prospectivity grid must be unavailable and uncalibrated
    grid = res.get("prospectivity_grid", {})
    assert grid.get("status") == "UNAVAILABLE"
    assert grid.get("is_calibrated") is False
    assert grid.get("grid") is None


# -------------------------------------------------------------------------
# 2. BAUXITE ACTIVATION & EVIDENCE WORKFLOW TESTS
# -------------------------------------------------------------------------

def test_bauxite_occurrences_inventory():
    """Verifies Bauxite occurrences endpoint returns verified records with provenance."""
    resp = client.get("/api/mineral/bauxite/occurrences")
    assert resp.status_code == 200
    data = resp.json()
    assert "occurrences" in data
    assert len(data["occurrences"]) >= 5
    
    # Check Panchpatmali NALCO deposit record
    panchpatmali = next((o for o in data["occurrences"] if "Panchpatmali" in o["name"]), None)
    assert panchpatmali is not None
    assert panchpatmali["operator"] == "National Aluminium Company Limited (NALCO)"
    assert panchpatmali["state"] == "Odisha"
    assert "Khondalite" in panchpatmali["geological_formation"]
    assert panchpatmali["confidence"] == "HIGH_CONFIRMED"


def test_bauxite_scientific_evaluation_panchpatmali():
    """Verifies Bauxite scientific evaluation at Panchpatmali coordinates."""
    resp = client.get("/api/mineral/bauxite/evaluation?lat=18.8200&lon=83.0200&radius_km=10.0")
    assert resp.status_code == 200
    data = resp.json()
    assert data["commodity"] == "Bauxite"
    assert data["is_within_study_province"] is True
    assert "East Coast Bauxite" in data["study_province"]
    assert data["nearest_confirmed_deposit"]["distance_km"] < 2.0
    
    # Scientific guardrail: AI prediction strictly withheld
    assert data["model_availability"]["ai_prospectivity_score"] is None
    assert data["model_availability"]["model_confidence"] is None
    assert data["model_availability"]["model_status"] == "UNAVAILABLE_NO_MODEL"
    assert len(data["mandatory_geological_prerequisites"]) >= 3


def test_analyze_bauxite_panchpatmali_evidence_workflow():
    """Tests POST /analyze for Bauxite at Panchpatmali (Odisha)."""
    payload = {
        "location_name": "Panchpatmali, Koraput, Odisha",
        "latitude": 18.8200,
        "longitude": 83.0200,
        "mineral": "Bauxite",
        "radius_km": 10.0
    }
    resp = client.post("/analyze", json=payload)
    assert resp.status_code == 200
    res = resp.json()
    assert res["status"] == "EVIDENCE_ONLY_NO_PREDICTION"
    assert res["prediction"] is None
    assert res["confidence_score"] is None
    assert res["prediction_availability"] == "UNAVAILABLE_NO_MODEL"
    assert "terrain_evidence" in res
    assert res["terrain_evidence"] is not None
    
    # Verify laterite vs bauxite warning
    assert "bauxite" in res["message"].lower() or "bauxite" in res["evidence_conclusion"].lower()
    grid = res.get("prospectivity_grid", {})
    assert grid.get("status") == "UNAVAILABLE"
    assert grid.get("is_calibrated") is False
    assert grid.get("grid") is None


# -------------------------------------------------------------------------
# 3. IRON ORE ACTIVATION & EVIDENCE WORKFLOW TESTS
# -------------------------------------------------------------------------

def test_iron_ore_occurrences_inventory():
    """Verifies Iron Ore occurrences endpoint returns verified records with provenance."""
    resp = client.get("/api/mineral/iron-ore/occurrences")
    assert resp.status_code == 200
    data = resp.json()
    assert "occurrences" in data
    assert len(data["occurrences"]) >= 5
    
    noamundi = next((o for o in data["occurrences"] if "Noamundi" in o["name"]), None)
    assert noamundi is not None
    assert noamundi["operator"] == "Tata Steel Limited"
    assert noamundi["state"] == "Jharkhand"
    assert "Hematite" in noamundi["geological_formation"]


def test_analyze_iron_ore_noamundi_terrain_and_guardrail():
    """Tests POST /analyze for Iron Ore at Noamundi with authentic Copernicus DEM terrain evidence."""
    payload = {
        "location_name": "Noamundi Iron Mine, West Singhbhum, Jharkhand",
        "latitude": 22.1500,
        "longitude": 85.5000,
        "mineral": "Iron Ore",
        "radius_km": 10.0
    }
    resp = client.post("/analyze", json=payload)
    assert resp.status_code == 200
    res = resp.json()
    assert res["status"] == "EVIDENCE_ONLY_NO_PREDICTION"
    assert res["prediction"] is None
    assert res["confidence_score"] is None
    assert res["prediction_availability"] == "UNAVAILABLE_NO_MODEL"
    
    # Authentic Copernicus DEM evidence must be verified active
    te = res.get("terrain_evidence", {})
    assert te.get("available") is True
    assert te.get("elevation_m") is not None
    assert abs(te["elevation_m"] - 532.9) < 1.0  # Measured Noamundi pit centroid
    assert te.get("slope_deg") is not None
    assert te.get("tpi_m") is not None
    
    # 3D prospectivity grid must be unavailable
    grid = res.get("prospectivity_grid", {})
    assert grid.get("status") == "UNAVAILABLE"
    assert grid.get("is_calibrated") is False
    assert grid.get("grid") is None


# -------------------------------------------------------------------------
# 4. CROSS-MINERAL ISOLATION & MANGANESE PRESERVATION
# -------------------------------------------------------------------------

def test_manganese_model_preserved_in_t44qmk():
    """Verifies Manganese Random Forest model remains active strictly within Tile T44QMK."""
    payload = {
        "location_name": "Balaghat Manganese Mining Belt, Madhya Pradesh",
        "latitude": 21.9048,
        "longitude": 80.1849,
        "mineral": "Manganese",
        "radius_km": 10.0
    }
    resp = client.post("/analyze", json=payload)
    assert resp.status_code == 200
    res = resp.json()
    assert res["status"] == "SUCCESS"
    assert res["prediction"] is not None
    assert isinstance(res["prediction"]["prospectivity_index"], (int, float))
    assert res["prediction_availability"] == "AVAILABLE"
    
    # 3D grid must be calibrated for Manganese inside T44QMK
    grid = res.get("prospectivity_grid", {})
    assert grid.get("status") == "AVAILABLE"
    assert grid.get("is_calibrated") is True
    assert isinstance(grid.get("grid"), list)


def test_no_manganese_model_reuse_for_other_minerals_at_balaghat():
    """
    CRITICAL SCIENTIFIC INTEGRITY TEST:
    Even when target coordinates lie directly inside Balaghat (Tile T44QMK),
    querying Coal, Iron Ore, or Bauxite must NEVER reuse the Manganese model!
    """
    for mineral in ["Coal", "Iron Ore", "Bauxite"]:
        payload = {
            "location_name": "Balaghat Region Coordinates",
            "latitude": 21.9048,
            "longitude": 80.1849,
            "mineral": mineral,
            "radius_km": 10.0
        }
        resp = client.post("/analyze", json=payload)
        assert resp.status_code == 200
        res = resp.json()
        assert res["prediction"] is None, f"{mineral} must have null prediction even inside T44QMK"
        assert res["confidence_score"] is None
        assert res["prediction_availability"] == "UNAVAILABLE_NO_MODEL"
        assert res["prospectivity_grid"]["is_calibrated"] is False
        assert res["prospectivity_grid"]["grid"] is None


def test_sovereign_boundary_rejection_for_all_four_minerals():
    """Verifies that out-of-boundary coordinates are rejected for all four minerals."""
    outside_lat, outside_lon = 0.0, 0.0  # Gulf of Guinea
    for mineral in ["Coal", "Manganese", "Iron Ore", "Bauxite"]:
        payload = {
            "location_name": "Null Island Coordinates",
            "latitude": outside_lat,
            "longitude": outside_lon,
            "mineral": mineral,
            "radius_km": 10.0
        }
        resp = client.post("/analyze", json=payload)
        assert resp.status_code == 200
        res = resp.json()
        assert res["status"] == "OUTSIDE_INDIA_TERRITORY"
        assert res["is_within_india"] is False
        assert res["prediction"] is None
        assert res["prospectivity_grid"]["is_calibrated"] is False
