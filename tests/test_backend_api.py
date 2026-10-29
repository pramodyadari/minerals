"""
Integration and Unit Test Suite for Mineral Exploration & Analysis System
Validates Section 7 requirements:
  - Supported Manganese location inside Tile T44QMK (Balaghat)
  - Manuguru, Telangana (Godavari Valley Coalfield) outside current model coverage
  - Singhbhum/North Odisha Iron Ore (BIF/BHQ stratigraphy & surface oxide distinction)
  - East Coast Bauxite (Panchpatmali Plateau laterite vs bauxite distinction)
  - All four mineral classes (Coal, Manganese, Iron Ore, Bauxite)
  - Satellite discovery error modes (empty catalogues, authentication failures, network timeouts)
  - Missing geological records (unmineralized regions)
  - Unvalidated prediction models vs validated models
  - Rock specimen image classifier (4 classes)
"""

import os
import sys
import io
import pytest
from PIL import Image

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from fastapi.testclient import TestClient

try:
    from backend.app.main import app
except ImportError:
    from app.main import app

client = TestClient(app)

# -------------------------------------------------------------
# 1. System Health & Mineral Registry
# -------------------------------------------------------------

def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["supported_mineral_classes"] == ["Coal", "Manganese", "Iron Ore", "Bauxite"]
    assert data["image_classifier_available"] is True
    assert data["manganese_geographical_model_available"] is True

def test_minerals_endpoint():
    response = client.get("/minerals")
    assert response.status_code == 200
    data = response.json()
    assert data["total_classes"] == 4
    names = [m["name"] for m in data["minerals"]]
    assert names == ["Coal", "Manganese", "Iron Ore", "Bauxite"]

# -------------------------------------------------------------
# 2. Manganese inside Tile T44QMK (Balaghat Belt - Validated Model)
# -------------------------------------------------------------

def test_supported_manganese_inside_t44qmk():
    """
    Validates genuine Manganese workflow inside Sentinel-2 Tile T44QMK:
    - Model coverage is VALIDATED_ACTIVE
    - Prediction is AVAILABLE and computed from Random Forest model
    - 5 separate status fields are properly returned
    """
    payload = {
        "location_name": "Balaghat Mining Corridor",
        "latitude": 21.9048,
        "longitude": 80.1849,
        "mineral": "Manganese",
        "radius_km": 5.0
    }
    response = client.post("/analyze", json=payload)
    assert response.status_code == 200
    data = response.json()

    # 5 Separate status fields (Section 4)
    assert data["overall_status"] == "SUCCESS"
    assert data["model_coverage"] == "VALIDATED_ACTIVE"
    assert data["prediction_availability"] == "AVAILABLE"
    assert data["satellite_imagery_availability"] in ("AVAILABLE_LIVE", "AVAILABLE_ARCHIVED")
    assert data["geological_evidence_availability"] in ("RECORDS_IDENTIFIED", "REGIONAL_FRAMEWORK_ONLY")

    # Prediction presence
    assert data["prediction"] is not None
    assert data["prediction"]["prospectivity_index"] > 0
    assert data["prediction"]["classification"] in ("HIGH", "MODERATE", "LOW")

    # Uncalibrated confidence notice
    assert data["confidence_score"] is None
    assert "calibrated probability" in data["confidence_note"].lower()

    # Geological evidence from Sausar belt
    assert "Sausar" in data["geological_context"]
    assert len(data["evidence_items"]) >= 4

# -------------------------------------------------------------
# 3. Manuguru, Telangana — Coal (Outside Model Coverage, Genuine Evidence)
# -------------------------------------------------------------

def test_manuguru_telangana_coal():
    """
    Validates Manuguru Coal analysis:
    - Located in Godavari Valley Coalfield (Pranhita-Godavari Basin)
    - Genuine GSI / Bhukosh geological occurrences (SCCL Manuguru Colliery)
    - Prediction model is NOT available for coal (honest EVIDENCE_ONLY_NO_PREDICTION)
    - Strict scientific rule: Underground coal seams NOT inferred from optical satellite indices
    """
    payload = {
        "location_name": "Manuguru Coalfield, Telangana",
        "latitude": 17.9820,
        "longitude": 80.7450,
        "mineral": "Coal",
        "radius_km": 10.0,
        # Use mocked timeout to test offline resilience without blocking on network jitter
        "mock_satellite_error": "TIMEOUT"
    }
    response = client.post("/analyze", json=payload)
    assert response.status_code == 200
    data = response.json()

    # Status fields
    assert data["overall_status"] == "EVIDENCE_ONLY_NO_PREDICTION"
    assert data["model_coverage"] == "NO_MODEL_FOR_COMMODITY"
    assert data["prediction_availability"] == "UNAVAILABLE_NO_MODEL"
    assert data["prediction"] is None
    assert data["geological_evidence_availability"] == "RECORDS_IDENTIFIED"

    # Documented occurrences
    assert len(data["documented_occurrences"]) >= 1
    occ_names = [o["name"] for o in data["documented_occurrences"]]
    assert any("Manuguru" in n for n in occ_names)

    # Scientific rule: Optical satellites cannot infer underground coal seams
    limitations = " ".join(data["limitations_and_warnings"])
    assert "drill" in limitations.lower() or "borehole" in limitations.lower() or "underground" in limitations.lower()

# -------------------------------------------------------------
# 4. Manuguru, Telangana — Manganese (Outside Balaghat Model Footprint)
# -------------------------------------------------------------

def test_manuguru_manganese_outside_t44qmk():
    """
    Validates that the Balaghat Manganese model is NOT invalidly applied to Manuguru:
    - Location is in Telangana (outside Tile T44QMK)
    - model_coverage is OUTSIDE_TRAINING_FOOTPRINT
    - prediction is None (score is withheld to preserve scientific integrity)
    - overall_status is NOT 'OUT_OF_COVERAGE' when data is discovered
    """
    payload = {
        "location_name": "Manuguru, Telangana",
        "latitude": 17.9820,
        "longitude": 80.7450,
        "mineral": "Manganese",
        "radius_km": 10.0,
        "mock_satellite_error": "EMPTY"
    }
    response = client.post("/analyze", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["model_coverage"] == "OUTSIDE_TRAINING_FOOTPRINT"
    assert data["prediction_availability"] == "UNAVAILABLE_UNVALIDATED_REGION"
    assert data["prediction"] is None
    # Section 4: Do not return OUT_OF_COVERAGE merely because outside Balaghat model
    assert data["overall_status"] in ("EVIDENCE_ONLY_NO_PREDICTION", "INSUFFICIENT_DATA")
    assert data["status"] != "OUT_OF_COVERAGE"

# -------------------------------------------------------------
# 5. Iron Ore — Singhbhum-North Odisha (Noamundi / Joda Belt)
# -------------------------------------------------------------

def test_iron_ore_singhbhum_north_odisha():
    """
    Validates Iron Ore analysis:
    - Located in Horseshoe Synclinorium (Archean Iron Ore Group / BHQ)
    - Documented deposits: Noamundi, Joda East
    - Strict rule: Distinguishes surface ferric oxide signatures from economic iron-ore deposits
    - Model coverage is NO_MODEL_FOR_COMMODITY
    """
    payload = {
        "location_name": "Noamundi Iron Sector, Jharkhand",
        "latitude": 22.1500,
        "longitude": 85.5000,
        "mineral": "Iron Ore",
        "radius_km": 10.0,
        "mock_satellite_error": "EMPTY"
    }
    response = client.post("/analyze", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["overall_status"] == "EVIDENCE_ONLY_NO_PREDICTION"
    assert data["geological_evidence_availability"] == "RECORDS_IDENTIFIED"
    assert len(data["documented_occurrences"]) >= 1
    assert any("Noamundi" in o["name"] for o in data["documented_occurrences"])

    # Prediction withheld
    assert data["prediction"] is None
    assert data["model_coverage"] == "NO_MODEL_FOR_COMMODITY"

    # Surface oxide vs ore deposit distinction
    evidence_text = str(data["evidence_items"]) + str(data["limitations_and_warnings"])
    assert "ferric" in evidence_text.lower()
    assert "ore" in evidence_text.lower()

# -------------------------------------------------------------
# 6. Bauxite — East Coast Bauxite Province (Panchpatmali Plateau)
# -------------------------------------------------------------

def test_bauxite_east_coast_panchpatmali():
    """
    Validates Bauxite analysis:
    - Located in Eastern Ghats Khondalite Belt
    - Documented occurrences: NALCO Panchpatmali Plateau Mine
    - Strict rule: Laterite capping / Al-OH absorption alone does NOT prove commercial bauxite
    - Prediction is None
    """
    payload = {
        "location_name": "Panchpatmali Bauxite Plateau, Odisha",
        "latitude": 18.8200,
        "longitude": 83.0200,
        "mineral": "Bauxite",
        "radius_km": 10.0,
        "mock_satellite_error": "EMPTY"
    }
    response = client.post("/analyze", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["overall_status"] == "EVIDENCE_ONLY_NO_PREDICTION"
    assert data["geological_evidence_availability"] == "RECORDS_IDENTIFIED"
    assert any("Panchpatmali" in o["name"] for o in data["documented_occurrences"])

    # Prediction withheld
    assert data["prediction"] is None
    assert data["model_coverage"] == "NO_MODEL_FOR_COMMODITY"

    # Laterite vs bauxite distinction
    evidence_text = str(data["evidence_items"]) + str(data["limitations_and_warnings"])
    assert "laterite" in evidence_text.lower()
    assert "bauxite" in evidence_text.lower()

# -------------------------------------------------------------
# 7. Satellite Discovery Error Modes (Mocked Testing Hooks)
# -------------------------------------------------------------

def test_satellite_empty_catalogue_handling():
    """Validates behavior when satellite catalogue search returns zero intersecting scenes."""
    payload = {
        "location_name": "Central India Inland Sector",
        "latitude": 20.0,
        "longitude": 78.0,
        "mineral": "Coal",
        "radius_km": 5.0,
        "mock_satellite_error": "EMPTY"  # Explicitly simulated
    }
    response = client.post("/analyze", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["satellite_imagery_availability"] == "NOT_FOUND_IN_CATALOGUE"
    assert len(data["satellite_scenes"]) == 0

def test_satellite_auth_failure_handling():
    """Validates behavior when satellite catalogue reports authentication required (HTTP 401)."""
    payload = {
        "location_name": "Test Site",
        "latitude": 20.0,
        "longitude": 80.0,
        "mineral": "Iron Ore",
        "radius_km": 5.0,
        "mock_satellite_error": "AUTH_ERROR"  # Explicitly simulated
    }
    response = client.post("/analyze", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["satellite_imagery_availability"] == "CATALOGUE_AUTH_REQUIRED"
    assert len(data["satellite_scenes"]) == 0

def test_satellite_network_timeout_error_handling():
    """Validates behavior when satellite catalogue query encounters network timeout."""
    payload = {
        "location_name": "Network Timeout Sector",
        "latitude": 20.0,
        "longitude": 80.0,
        "mineral": "Bauxite",
        "radius_km": 5.0,
        "mock_satellite_error": "TIMEOUT"  # Explicitly simulated
    }
    response = client.post("/analyze", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["satellite_imagery_availability"] == "CATALOGUE_SERVICE_ERROR"
    assert "timed out" in data["satellite_error_details"].lower()

# -------------------------------------------------------------
# 8. Unmineralized Location (Missing Geological Records)
# -------------------------------------------------------------

def test_location_missing_geological_records():
    """
    Validates behavior for an unmineralized location (Jaipur, Rajasthan):
    - geological_evidence_availability is NO_RECORDS_IN_RADIUS
    - documented_occurrences is empty
    - model_coverage is OUTSIDE_TRAINING_FOOTPRINT
    - overall_status reports INSUFFICIENT_DATA or EVIDENCE_ONLY
    """
    payload = {
        "location_name": "Jaipur, Rajasthan",
        "latitude": 26.9124,
        "longitude": 75.7873,
        "mineral": "Manganese",
        "radius_km": 10.0,
        "mock_satellite_error": "EMPTY"
    }
    response = client.post("/analyze", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["geological_evidence_availability"] == "NO_RECORDS_IN_RADIUS"
    assert len(data["documented_occurrences"]) == 0
    assert data["model_coverage"] == "OUTSIDE_TRAINING_FOOTPRINT"
    assert data["prediction"] is None
    assert data["overall_status"] == "INSUFFICIENT_DATA"

def test_outside_india_boundary_validation():
    """
    Validates sovereign territorial boundary enforcement for coordinates outside India (Colombo, Sri Lanka).
    """
    payload = {
        "location_name": "Colombo, Sri Lanka",
        "latitude": 6.9271,
        "longitude": 79.8612,
        "mineral": "Coal",
        "radius_km": 5.0
    }
    response = client.post("/analyze", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "OUTSIDE_INDIA_TERRITORY"
    assert data["is_within_india"] is False
    assert "sovereign" in data["message"].lower() or "territory" in data["message"].lower()
    assert data["prediction"] is None

# -------------------------------------------------------------
# 9. Invalid Mineral Class Rejection
# -------------------------------------------------------------

def test_analyze_invalid_mineral_rejected():
    payload = {
        "location_name": "Test Site",
        "latitude": 21.85,
        "longitude": 80.25,
        "mineral": "Lithium",  # 5th mineral forbidden
        "radius_km": 5.0
    }
    response = client.post("/analyze", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ERROR"
    assert "Invalid mineral class" in data["message"]

# -------------------------------------------------------------
# 10. Specimen Image Classifier (4-Class CNN)
# -------------------------------------------------------------

def test_classify_image_endpoint():
    img = Image.new("RGB", (128, 128), color=(180, 80, 50))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    buf.seek(0)

    files = {"file": ("rock_sample.jpg", buf, "image/jpeg")}
    response = client.post("/classify-image", files=files)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "SUCCESS"
    assert data["predicted_mineral"] in ["Coal", "Manganese", "Iron Ore", "Bauxite"]
    assert 0.0 <= data["confidence_score"] <= 1.0
    assert len(data["class_probabilities_pct"]) == 4

# -------------------------------------------------------------
# 11. Supplementary Endpoints
# -------------------------------------------------------------

def test_candidate_zones_endpoint():
    response = client.get("/candidate-zones")
    assert response.status_code == 200
    data = response.json()
    assert data["total_zones"] == 20

def test_production_forecast_endpoint():
    response = client.get("/production-forecast?mineral=Manganese")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "AVAILABLE"
    assert data["mineral"] == "Manganese"
