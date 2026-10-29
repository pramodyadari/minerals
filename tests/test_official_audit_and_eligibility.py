"""
================================================================================
AI MINERAL EXPLORATION SYSTEM — OFFICIAL DATA AUDIT & ELIGIBILITY TEST SUITE
================================================================================
Test Suite: tests/test_official_audit_and_eligibility.py

Validates:
1. Official data inventory schema, checksums, and readiness classifications.
2. Shared nationwide geographic eligibility engine across all 4 commodities.
3. Sovereign boundary rejection (OUTSIDE_SUPPORTED_TERRITORY).
4. Satellite imagery availability and valid pixel evaluation.
5. Model domain boundary enforcement (Manganese strictly in Tile T44QMK).
6. Evidence-only status for unvalidated commodities (Iron Ore, Coal, Bauxite).
7. FastAPI endpoints: GET /api/eligibility and GET /api/data/inventory.
8. Backward compatibility and non-regression of POST /analyze payload contracts.
================================================================================
"""

import os
import sys
import json
import pytest
from fastapi.testclient import TestClient

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from backend.app.main import app
from backend.app.eligibility_service import get_geographic_eligibility

client = TestClient(app)


def test_01_official_data_inventory_schema_and_provenance():
    """Verifies that the official data inventory is valid, complete, and contains verified checksums."""
    inv_file = os.path.join(PROJECT_ROOT, "data", "audits", "official_data_inventory.json")
    assert os.path.exists(inv_file), "official_data_inventory.json must exist in data/audits/"
    
    with open(inv_file, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    assert "audit_metadata" in data
    assert "datasets" in data
    datasets = data["datasets"]
    assert len(datasets) >= 6, "Must catalog all 6+ major official datasets"
    
    # Check required fields in each dataset record
    required_fields = [
        "dataset_id", "dataset_name", "source_organization", "official_source_url",
        "minerals", "intended_use", "licence_and_permitted_usage", "access_status",
        "download_status", "readiness_status", "model_suitability"
    ]
    for ds in datasets:
        for rf in required_fields:
            assert rf in ds, f"Field '{rf}' missing in dataset {ds.get('dataset_id')}"
            
    # Verify Copernicus GLO-30 DEM record and real SHA256 checksum
    cop_dem = next((d for d in datasets if d["dataset_id"] == "COP_DEM_GLO30_NOAMUNDI"), None)
    assert cop_dem is not None
    assert cop_dem["download_status"] == "DOWNLOADED"
    assert cop_dem["readiness_status"] == "READY_FOR_EVIDENCE"
    assert "noamundi_utm45n_SHA256" in cop_dem["integrity_hashes"]


def test_02_eligibility_outside_india():
    """Coordinates outside India sovereign territory return OUTSIDE_SUPPORTED_TERRITORY."""
    res = get_geographic_eligibility(lat=0.0, lon=0.0, mineral_name="Manganese")
    assert res["status"] == "OUTSIDE_SUPPORTED_TERRITORY"
    assert res["overall_eligibility"] == "OUTSIDE_SUPPORTED_TERRITORY"
    assert res["is_within_india"] is False
    assert res["prediction_eligible"] is False
    assert res["evidence_eligible"] is False
    assert len(res["supported_actions"]) >= 1


def test_03_eligibility_manganese_inside_t44qmk():
    """Manganese inside validated Tile T44QMK returns ELIGIBLE_FOR_ANALYSIS."""
    res = get_geographic_eligibility(lat=21.9048, lon=80.1849, mineral_name="Manganese")
    assert res["status"] == "ELIGIBLE_FOR_ANALYSIS"
    assert res["overall_eligibility"] == "ELIGIBLE_FOR_ANALYSIS"
    assert res["is_within_india"] is True
    assert res["model_domain_status"] == "WITHIN_MODEL_DOMAIN"
    assert res["model_training_status"] == "TRAINED_AND_VALIDATED"
    assert res["prediction_eligible"] is True
    assert res["evidence_eligible"] is True


def test_04_eligibility_manganese_outside_t44qmk():
    """Manganese outside Tile T44QMK returns OUTSIDE_MODEL_DOMAIN and withholds prediction."""
    res = get_geographic_eligibility(lat=23.7500, lon=86.4200, mineral_name="Manganese")
    assert res["status"] == "OUTSIDE_MODEL_DOMAIN"
    assert res["overall_eligibility"] == "OUTSIDE_MODEL_DOMAIN"
    assert res["is_within_india"] is True
    assert res["model_domain_status"] == "OUTSIDE_MODEL_DOMAIN"
    assert res["prediction_eligible"] is False
    assert res["evidence_eligible"] is True


def test_05_eligibility_iron_ore_noamundi():
    """Iron Ore at Noamundi returns EVIDENCE_ONLY with spatial validation failure notice."""
    res = get_geographic_eligibility(lat=22.1500, lon=85.5000, mineral_name="Iron Ore")
    assert res["status"] == "EVIDENCE_ONLY"
    assert res["overall_eligibility"] == "EVIDENCE_ONLY"
    assert res["is_within_india"] is True
    assert res["model_domain_status"] == "MODEL_UNAVAILABLE"
    assert "SPATIAL_VALIDATION_FAILED" in res["model_training_status"]
    assert res["prediction_eligible"] is False
    assert res["evidence_eligible"] is True


def test_06_eligibility_coal_manuguru():
    """Coal at Manuguru returns EVIDENCE_ONLY with subsurface seam warning."""
    res = get_geographic_eligibility(lat=17.9820, lon=80.7450, mineral_name="Coal")
    assert res["status"] == "EVIDENCE_ONLY"
    assert res["overall_eligibility"] == "EVIDENCE_ONLY"
    assert res["is_within_india"] is True
    assert res["model_domain_status"] == "MODEL_UNAVAILABLE"
    assert "NO_SUBSURFACE_DATA" in res["model_training_status"]
    assert res["prediction_eligible"] is False
    assert res["evidence_eligible"] is True


def test_07_eligibility_bauxite_panchpatmali():
    """Bauxite at Panchpatmali returns EVIDENCE_ONLY with chemical assay requirement."""
    res = get_geographic_eligibility(lat=18.8200, lon=83.0200, mineral_name="Bauxite")
    assert res["status"] == "EVIDENCE_ONLY"
    assert res["overall_eligibility"] == "EVIDENCE_ONLY"
    assert res["is_within_india"] is True
    assert res["model_domain_status"] == "MODEL_UNAVAILABLE"
    assert "NO_CHEMICAL_ASSAYS" in res["model_training_status"]
    assert res["prediction_eligible"] is False
    assert res["evidence_eligible"] is True


def test_08_api_eligibility_endpoint():
    """GET /api/eligibility returns 200 with complete structured eligibility payload."""
    resp = client.get("/api/eligibility?lat=21.9048&lon=80.1849&mineral=Manganese&radius_km=10.0")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ELIGIBLE_FOR_ANALYSIS"
    assert data["mineral"] == "Manganese"
    assert data["prediction_eligible"] is True
    assert len(data["supported_actions"]) >= 3


def test_09_api_data_inventory_endpoint():
    """GET /api/data/inventory returns 200 with authoritative dataset inventory."""
    resp = client.get("/api/data/inventory")
    assert resp.status_code == 200
    data = resp.json()
    assert "datasets" in data
    assert len(data["datasets"]) >= 6
    gsi_occ = next((d for d in data["datasets"] if "GSI_NMI" in d["dataset_id"]), None)
    assert gsi_occ is not None


def test_10_post_analyze_embeds_geographic_eligibility():
    """POST /analyze includes geographic_eligibility block without breaking contracts."""
    payload = {
        "location_name": "Noamundi Iron Mine",
        "latitude": 22.15,
        "longitude": 85.50,
        "mineral": "Iron Ore",
        "radius_km": 10.0
    }
    resp = client.post("/analyze", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert "geographic_eligibility" in data
    assert data["geographic_eligibility"] is not None
    assert data["geographic_eligibility"]["overall_eligibility"] == "EVIDENCE_ONLY"
    assert data["prediction"] is None
    assert data["prediction_availability"] == "UNAVAILABLE_NO_MODEL"
