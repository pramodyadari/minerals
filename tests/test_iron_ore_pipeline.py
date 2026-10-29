"""
Test Suite: tests/test_iron_ore_pipeline.py
Validates the Iron Ore Exploration Pipeline:
1. Curated occurrence inventory (GSI / IBM verified mines vs uncertain prospects).
2. Geologically defensible pseudo-absence methodology (Singhbhum Granite Batholith).
3. Spatially blocked cross-validation diagnostics and data-gap report.
4. FastAPI endpoints (/api/mineral/iron-ore/occurrences, /api/mineral/iron-ore/audit, /api/mineral/iron-ore/evaluation).
5. Strict scientific integrity: Iron Ore AI score remains null without Manganese substitution.
6. Non-regression for Manganese, Coal, and Bauxite.
"""

import os
import sys
import json
import pytest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.iron_ore_pipeline import (
    get_iron_ore_occurrences,
    get_iron_ore_background_sectors,
    get_iron_ore_spatial_audit_report,
    get_iron_ore_scientific_evaluation,
    get_iron_ore_geophysical_audit,
    is_within_singhbhum_iron_craton
)
from backend.app.mineral_service import analyze_location_for_mineral

client = TestClient(app)


class TestIronOreCuratedData:
    """Verifies curated ground truth occurrences and background sectors."""

    def test_01_curated_occurrence_inventory_schema_and_sources(self):
        """Verifies authoritative occurrence records from GSI/IBM in Singhbhum craton."""
        data = get_iron_ore_occurrences()
        assert "occurrences" in data
        assert "curation_summary" in data

        summary = data["curation_summary"]
        assert summary["total_records"] >= 7
        assert summary["confirmed_positive_mines"] == 5
        assert summary["uncertain_reference_prospects"] == 2

        # Check required confirmed deposits
        confirmed_names = {occ["name"] for occ in data["occurrences"] if occ["record_type"] == "CONFIRMED_MINE_LEASE"}
        expected_mines = {
            "Noamundi Iron Ore Mine",
            "Joda East Iron Mine",
            "Kiriburu Iron Mine",
            "Gua Iron Ore Mine",
            "Bolani Iron Ore Mine"
        }
        assert expected_mines.issubset(confirmed_names)

        # Check every record has CRS, coordinates, and provenance
        for occ in data["occurrences"]:
            assert 21.0 <= occ["latitude"] <= 23.0
            assert 85.0 <= occ["longitude"] <= 86.0
            assert occ["utm_zone"] == 45
            assert "source" in occ
            assert len(occ["source"]) > 5
            assert "geological_formation" in occ

    def test_02_background_pseudo_absence_defensibility(self):
        """Verifies background sectors are geologically unmineralized granites, not fake drill holes."""
        data = get_iron_ore_background_sectors()
        assert "sectors" in data
        assert len(data["sectors"]) >= 3
        assert data["total_background_samples"] >= 1800

        # Check scientific justification
        justifications = " ".join(data.get("scientific_justification", []))
        assert "Singhbhum Granite" in justifications
        assert "pseudo-absences" in justifications.lower()
        assert "barren" in justifications.lower()

        # Check coordinates are east of the IOG synclinorium
        for sec in data["sectors"]:
            assert sec["longitude"] >= 85.60  # East of IOG belt
            assert "Singhbhum Granite" in sec["formation"]

    def test_03_spatial_audit_and_data_gap_report(self):
        """Verifies spatial cross-validation metrics demonstrate generalization deficit."""
        report = get_iron_ore_spatial_audit_report()
        assert "validation_methodology_comparison" in report
        comp = report["validation_methodology_comparison"]

        # Random holdout is high due to spatial autocorrelation
        random_cv = comp["random_stratified_5fold_cv"]
        assert random_cv["accuracy"] > 0.80
        assert random_cv["roc_auc"] > 0.90
        assert "SPATIAL_AUTOCORRELATION" in random_cv["evaluation_diagnostic"]

        # Spatially blocked validation shows the true generalization deficit
        spatial_cv = comp["spatially_blocked_leave_group_out_cv"]
        assert spatial_cv["accuracy"] < 0.60
        assert spatial_cv["f1_score"] < 0.50
        assert "GENUINE_SPATIAL_GENERALIZATION_DEFICIT" in spatial_cv["evaluation_diagnostic"]

        # Decision is to withhold prediction
        decision_info = report["scientific_decision_and_data_gap_report"]
        assert decision_info["model_decision"] == "STOP_TRAINING_WITHHOLD_PREDICTION"
        assert len(decision_info["mandatory_prerequisites_for_future_iron_ore_model"]) >= 3


class TestIronOreApiIntegration:
    """Verifies FastAPI endpoints for Iron Ore."""

    def test_04_occurrences_endpoint(self):
        """GET /api/mineral/iron-ore/occurrences returns 200 with confirmed deposits."""
        resp = client.get("/api/mineral/iron-ore/occurrences")
        assert resp.status_code == 200
        data = resp.json()
        assert data["curation_summary"]["confirmed_positive_mines"] == 5

    def test_05_audit_endpoint(self):
        """GET /api/mineral/iron-ore/audit returns 200 with spatial validation diagnostics."""
        resp = client.get("/api/mineral/iron-ore/audit")
        assert resp.status_code == 200
        data = resp.json()
        assert "validation_methodology_comparison" in data
        assert "feature_importances_ranking" in data

    def test_06_evaluation_endpoint_noamundi(self):
        """GET /api/mineral/iron-ore/evaluation returns 200 with withheld prediction."""
        resp = client.get("/api/mineral/iron-ore/evaluation?lat=22.15&lon=85.50&radius_km=10.0")
        assert resp.status_code == 200
        data = resp.json()
        assert data["is_within_study_craton"] is True
        assert data["model_availability"]["ai_prospectivity_score"] is None
        assert data["model_availability"]["model_confidence"] is None
        assert "Noamundi" in data["nearest_confirmed_deposit"]["name"]

    def test_07_analyze_endpoint_noamundi_iron_ore_withholds_score(self):
        """POST /analyze for Iron Ore at Noamundi returns null prediction and unavailable 3D grid."""
        payload = {
            "location_name": "Noamundi Mining Sector",
            "latitude": 22.1500,
            "longitude": 85.5000,
            "mineral": "Iron Ore",
            "radius_km": 10.0
        }
        resp = client.post("/analyze", json=payload)
        assert resp.status_code == 200
        data = resp.json()

        assert data["mineral"] == "Iron Ore"
        assert data["prediction"] is None
        assert data["confidence_score"] is None
        assert data["model_coverage"] == "NO_MODEL_FOR_COMMODITY"
        assert data["prediction_availability"] == "UNAVAILABLE_NO_MODEL"
        assert data["prospectivity_grid"]["status"] == "UNAVAILABLE"
        assert data["prospectivity_grid"]["grid"] is None

        # Evidence items and geological context remain active
        assert len(data["evidence_items"]) > 0
        assert data["geological_province"] is not None

    def test_08_processed_evidence_endpoint_includes_audit_references(self):
        """GET /evidence/processed returns verified audit references."""
        resp = client.get("/evidence/processed?latitude=22.15&longitude=85.50&mineral=Iron%20Ore&radius_km=10.0")
        assert resp.status_code == 200
        data = resp.json()

        ma = data["model_availability"]
        assert ma["ai_prospectivity_score"] is None
        assert ma["model_coverage"] == "NO_MODEL_FOR_COMMODITY"
        assert "iron_ore_spatial_audit_report.json" in ma["spatial_audit_report_ref"]
        assert "iron_ore_occurrences.json" in ma["curated_occurrences_ref"]
        assert ma["evaluation_diagnostics"]["spatially_blocked_cv_accuracy_pct"] == 47.66


class TestMultiMineralIntegrityPreserved:
    """Ensures Coal, Manganese, and Bauxite behaviors are completely unaffected."""

    def test_09_manganese_inside_t44qmk_remains_active(self):
        """Manganese inside T44QMK still runs its validated model."""
        res = analyze_location_for_mineral(
            location_name="Balaghat Sector",
            lat=21.9048,
            lon=80.1849,
            mineral_name="Manganese",
            radius_km=10.0
        )
        assert res["mineral"] == "Manganese"
        assert res["model_coverage"] == "VALIDATED_ACTIVE"
        assert res["prediction_availability"] == "AVAILABLE"
        assert res["prediction"] is not None

    def test_10_coal_and_bauxite_remain_unavailable(self):
        """Coal and Bauxite retain unmodeled status."""
        for mineral in ["Coal", "Bauxite"]:
            res = analyze_location_for_mineral(
                location_name="Test Location",
                lat=22.1500,
                lon=85.5000,
                mineral_name=mineral,
                radius_km=10.0
            )
            assert res["prediction"] is None
            assert res["model_coverage"] == "NO_MODEL_FOR_COMMODITY"

    def test_11_geophysical_audit_endpoint_and_scientific_integrity(self):
        """GET /api/mineral/iron-ore/geophysical-audit returns 200 with complete audit details."""
        resp = client.get("/api/mineral/iron-ore/geophysical-audit")
        assert resp.status_code == 200
        data = resp.json()

        # Audit metadata
        assert data["audit_metadata"]["status"] == "DATA_AUDIT_COMPLETE_ACQUISITION_BLOCKED"
        assert data["audit_metadata"]["scientific_recommendation"] == "RETAIN_UNAVAILABLE_STATUS_PENDING_GOVERNMENT_GRID_DISPATCH"

        # Data sources audit
        sources = {src["source_id"]: src for src in data["data_sources_audit"]}
        assert "GSI_NAGMP_HRAS" in sources
        assert "GSI_BHUKOSH_GEOLOGY_1_50K" in sources
        assert "NOAA_NCEI_EMAG2V3" in sources
        assert "ESA_COPERNICUS_DEM_GLO30" in sources

        # Check blocker details
        assert "BLOCKED_PORTAL_AUTHENTICATION_REQUIRED" == sources["GSI_NAGMP_HRAS"]["access_status"]
        assert "ngdr.gsi.gov.in" in sources["GSI_NAGMP_HRAS"]["portal_url"]

        # Check NOAA EMAG2v3 resolution limitation
        assert "VERIFIED_ACCESSIBLE_BUT_SCIENTIFICALLY_INADEQUATE" == sources["NOAA_NCEI_EMAG2V3"]["access_status"]
        assert "3.7 km" in sources["NOAA_NCEI_EMAG2V3"]["scientific_critique"]

        # Check petrophysical paradox
        petro = data["petrophysical_and_geological_suitability_audit"]
        assert "magnetite_vs_hematite_paradox" in petro
        assert "newer_dolerite_false_positives" in petro

        # Check scientific verdict
        verdict = data["scientific_verdict"]
        assert verdict["status"] == "UNAVAILABLE_INSUFFICIENT_SPATIAL_VALIDATION"
        assert verdict["ai_prospectivity_score"] is None
        assert verdict["model_confidence"] is None
