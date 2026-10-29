"""
Unit & Integration Tests for Multi-Mineral Scorecards Backend
Covers:
- POST /analyze-all and POST /analyze/multi
- Shared coordinates & radius across 4 commodities
- Individual pipeline error isolation (partial success)
- Comparison summary table columns & scientific guardrails
- No cross-mineral model reuse
- Manganese geographic restrictions
- Null scores and missing evidence handling
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

def test_01_all_four_minerals_analyzed_in_one_action():
    """POST /analyze-all returns independent results for Coal, Manganese, Iron Ore, Bauxite."""
    payload = {
        "location_name": "Balaghat Mining Corridor",
        "latitude": 21.9048,
        "longitude": 80.1849,
        "radius_km": 10.0
    }
    resp = client.post("/analyze-all", json=payload)
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
    data = resp.json()

    assert data["status"] in ["SUCCESS", "PARTIAL_SUCCESS"]
    assert "minerals" in data
    assert "comparison_summary" in data

    # All 4 minerals must be present
    for m in ["Coal", "Manganese", "Iron Ore", "Bauxite"]:
        assert m in data["minerals"], f"Missing mineral: {m}"
        min_data = data["minerals"][m]
        assert min_data["latitude"] == pytest.approx(21.9048, abs=1e-3)
        assert min_data["longitude"] == pytest.approx(80.1849, abs=1e-3)
        assert min_data["radius_km"] == 10.0
        assert "evidence_favorability_index" in min_data or "evidence_index" in min_data
        assert "evidence_quality" in min_data


def test_02_comparison_summary_table_columns_and_guardrails():
    """Verify comparison table columns: Mineral, AI Prediction Status, AI Score, Evidence Index, Evidence Quality, Main Explanation."""
    payload = {
        "location_name": "Noamundi Iron Ore Mine",
        "latitude": 22.15,
        "longitude": 85.50,
        "radius_km": 10.0
    }
    resp = client.post("/analyze-all", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    summary = data["comparison_summary"]

    assert len(summary) == 4, f"Expected 4 summary rows, got {len(summary)}"
    expected_cols = [
        "mineral",
        "ai_prediction_status",
        "ai_score_label",
        "evidence_index",
        "evidence_quality",
        "main_explanation"
    ]
    for row in summary:
        for col in expected_cols:
            assert col in row, f"Missing column {col} in summary row for {row.get('mineral')}"
            assert row[col] is not None, f"Column {col} cannot be None"


def test_03_no_cross_mineral_model_reuse_and_strict_ml_withholding():
    """Ensure Manganese model is NEVER used for Iron Ore, Coal, or Bauxite."""
    payload = {
        "location_name": "Balaghat Core Training Footprint",
        "latitude": 21.9048,
        "longitude": 80.1849,
        "radius_km": 10.0
    }
    resp = client.post("/analyze-all", json=payload)
    assert resp.status_code == 200
    minerals = resp.json()["minerals"]

    # Manganese in Balaghat: AI model is eligible (uncalibrated)
    mn = minerals["Manganese"]
    assert mn["model_coverage"] == "VALIDATED_ACTIVE"
    assert mn["prediction"] is not None

    # Iron Ore: ML score withheld due to spatial validation deficit
    fe = minerals["Iron Ore"]
    assert fe["prediction"] is None
    assert fe["model_coverage"] == "NO_MODEL_FOR_COMMODITY"
    assert "withheld" in fe["prediction_availability"].lower() or "unavailable" in fe["prediction_availability"].lower()

    # Coal: ML score withheld due to lack of underground seam training
    coal = minerals["Coal"]
    assert coal["prediction"] is None
    assert coal["model_coverage"] == "NO_MODEL_FOR_COMMODITY"

    # Bauxite: ML score withheld due to lack of chemical assay data
    baux = minerals["Bauxite"]
    assert baux["prediction"] is None
    assert baux["model_coverage"] == "NO_MODEL_FOR_COMMODITY"


def test_04_manganese_geographic_restriction():
    """Manganese outside its training tile (e.g. Manuguru 17.9820, 80.7450) must withhold ML score."""
    payload = {
        "location_name": "Manuguru Coal Belt",
        "latitude": 17.9820,
        "longitude": 80.7450,
        "radius_km": 10.0
    }
    resp = client.post("/analyze-all", json=payload)
    assert resp.status_code == 200
    mn = resp.json()["minerals"]["Manganese"]

    # Outside T44QMK, Manganese prediction MUST be null
    assert mn["prediction"] is None
    assert mn["model_coverage"] == "OUTSIDE_TRAINING_FOOTPRINT"
    assert mn["status"] in ["EVIDENCE_ONLY_NO_PREDICTION", "OUT_OF_COVERAGE"]


def test_05_isolated_pipeline_failure_preserves_other_minerals():
    """If one mineral's pipeline throws an unhandled exception, the other 3 still succeed."""
    from backend.app import mineral_service
    original_analyze = mineral_service.analyze_location_for_mineral

    def faulty_analyze(*args, **kwargs):
        mineral = kwargs.get("mineral_name") or kwargs.get("mineral")
        if not mineral and len(args) >= 4:
            mineral = args[3]
        if mineral == "Coal":
            raise RuntimeError("Simulated transient raster read failure for Coal")
        return original_analyze(*args, **kwargs)

    with patch("backend.app.mineral_service.analyze_location_for_mineral", side_effect=faulty_analyze):
        res = analyze_all_minerals_for_location(
            lat=21.9048,
            lon=80.1849,
            location_name="Fault Isolation Test",
            radius_km=10.0
        )

    assert res["status"] == "PARTIAL_SUCCESS"
    assert res["minerals"]["Coal"]["status"] == "ERROR"
    assert "Simulated transient raster read failure" in res["minerals"]["Coal"]["message"]

    # The other three must still be valid and successful
    for ok_min in ["Manganese", "Iron Ore", "Bauxite"]:
        assert res["minerals"][ok_min]["status"] in ["SUCCESS", "EVIDENCE_ONLY_NO_PREDICTION"]
        assert "evidence_favorability_index" in res["minerals"][ok_min]

    # Comparison summary must reflect the error cleanly
    coal_summary = [r for r in res["comparison_summary"] if r["mineral"] == "Coal"][0]
    assert coal_summary["ai_prediction_status"] == "UNAVAILABLE_PIPELINE_ERROR"
    assert "Pipeline evaluation error" in coal_summary["main_explanation"]


def test_06_analyze_endpoint_all_alias():
    """POST /analyze with mineral='All' correctly delegates to multi-mineral analysis."""
    payload = {
        "location_name": "Panchpatmali Bauxite Deposit",
        "latitude": 18.82,
        "longitude": 83.02,
        "mineral": "All",
        "radius_km": 10.0
    }
    resp = client.post("/analyze", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert "minerals" in data
    assert len(data["minerals"]) == 4
    assert "comparison_summary" in data


def test_07_null_scores_not_replaced_with_zero():
    """Missing scores must be explicitly None/null, never replaced with numeric 0."""
    payload = {
        "location_name": "Indian Ocean Off Coverage",
        "latitude": 5.0,
        "longitude": 80.0,
        "radius_km": 10.0
    }
    resp = client.post("/analyze-all", json=payload)
    assert resp.status_code == 200
    minerals = resp.json()["minerals"]
    for m in ["Coal", "Manganese", "Iron Ore", "Bauxite"]:
        item = minerals[m]
        assert item["prediction"] is None, f"{m} prediction must be None outside coverage, not {item['prediction']}"
        # If favorability is not computable, it should be null/None, not 0
        if item["status"] in ["OUTSIDE_INDIA_TERRITORY", "INSUFFICIENT_DATA", "OUT_OF_COVERAGE"]:
            assert item["evidence_favorability_index"] is None
            assert item["evidence_index"] is None
