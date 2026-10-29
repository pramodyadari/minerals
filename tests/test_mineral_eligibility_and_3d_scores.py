"""
Regression and validation test suite for Mineral-Specific Eligibility and 3D Score Integrity.
Ensures:
1. No hardcoded or fallback 40% scores are returned for unmodeled minerals.
2. Coal, Iron Ore, and Bauxite strictly return UNAVAILABLE status and grid=None.
3. Manganese outside Sentinel-2 Tile T44QMK strictly returns UNAVAILABLE status and grid=None.
4. Only Manganese inside Tile T44QMK produces a valid prediction and calibrated 3D grid.
5. All panels and 3D visualizers agree on score availability.
"""

import os
import sys
import pytest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.mineral_service import (
    analyze_location_for_mineral,
    get_prospectivity_3d_grid,
    is_within_tile,
)

client = TestClient(app)

# Coordinates
BALAGHAT_LAT = 21.9048
BALAGHAT_LON = 80.1849

OUTSIDE_TILE_LAT = 23.7500  # Jharia / Raniganj coal corridor
OUTSIDE_TILE_LON = 86.4200

BAUXITE_LAT = 18.8100  # Koraput bauxite belt
BAUXITE_LON = 82.7100

IRON_ORE_LAT = 18.7300  # Bailadila iron ore ridge
IRON_ORE_LON = 81.2500


class TestMineralSpecificEligibility:
    """Verifies each mineral is evaluated completely independently without score leakage."""

    def test_coal_model_eligibility_and_no_numeric_score(self):
        """Coal has no spatial ML model: must return UNAVAILABLE and no numeric score."""
        res = analyze_location_for_mineral(
            location_name="Jharia Coalfield",
            lat=OUTSIDE_TILE_LAT,
            lon=OUTSIDE_TILE_LON,
            mineral_name="Coal",
            radius_km=10.0
        )

        assert res["mineral"] == "Coal"
        assert res["prediction"] is None
        assert res["confidence_score"] is None
        assert res["model_coverage"] == "NO_MODEL_FOR_COMMODITY"
        assert res["prediction_availability"] == "UNAVAILABLE_NO_MODEL"
        assert res["overall_status"] in ("EVIDENCE_ONLY_NO_PREDICTION", "INSUFFICIENT_DATA")

        # 3D prospectivity grid must be explicit UNAVAILABLE, not a 40% synthetic profile
        grid = res["prospectivity_grid"]
        assert grid is not None
        assert grid["status"] == "UNAVAILABLE"
        assert grid["mineral"] == "Coal"
        assert grid["grid"] is None
        assert grid["is_calibrated"] is False
        assert "A validated spatial machine-learning model has not been trained" in grid["reason"]

    def test_iron_ore_model_eligibility_and_no_numeric_score(self):
        """Iron Ore has no spatial ML model: must return UNAVAILABLE and no numeric score."""
        res = analyze_location_for_mineral(
            location_name="Bailadila Range",
            lat=IRON_ORE_LAT,
            lon=IRON_ORE_LON,
            mineral_name="Iron Ore",
            radius_km=10.0
        )

        assert res["mineral"] == "Iron Ore"
        assert res["prediction"] is None
        assert res["model_coverage"] == "NO_MODEL_FOR_COMMODITY"
        assert res["prediction_availability"] == "UNAVAILABLE_NO_MODEL"

        grid = res["prospectivity_grid"]
        assert grid["status"] == "UNAVAILABLE"
        assert grid["grid"] is None
        assert grid["is_calibrated"] is False

    def test_bauxite_model_eligibility_and_no_numeric_score(self):
        """Bauxite has no spatial ML model: must return UNAVAILABLE and no numeric score."""
        res = analyze_location_for_mineral(
            location_name="Koraput Plateau",
            lat=BAUXITE_LAT,
            lon=BAUXITE_LON,
            mineral_name="Bauxite",
            radius_km=10.0
        )

        assert res["mineral"] == "Bauxite"
        assert res["prediction"] is None
        assert res["model_coverage"] == "NO_MODEL_FOR_COMMODITY"
        assert res["prediction_availability"] == "UNAVAILABLE_NO_MODEL"

        grid = res["prospectivity_grid"]
        assert grid["status"] == "UNAVAILABLE"
        assert grid["grid"] is None
        assert grid["is_calibrated"] is False

    def test_manganese_outside_tile_t44qmk_remains_unavailable(self):
        """Manganese outside Tile T44QMK cannot use the Balaghat model and must withhold scores."""
        assert not is_within_tile(OUTSIDE_TILE_LAT, OUTSIDE_TILE_LON)

        res = analyze_location_for_mineral(
            location_name="Outside Tile Location",
            lat=OUTSIDE_TILE_LAT,
            lon=OUTSIDE_TILE_LON,
            mineral_name="Manganese",
            radius_km=10.0
        )

        assert res["mineral"] == "Manganese"
        assert res["prediction"] is None
        assert res["model_coverage"] == "OUTSIDE_TRAINING_FOOTPRINT"
        assert res["prediction_availability"] == "UNAVAILABLE_UNVALIDATED_REGION"
        assert res["overall_status"] in ("EVIDENCE_ONLY_NO_PREDICTION", "INSUFFICIENT_DATA")

        grid = res["prospectivity_grid"]
        assert grid["status"] == "UNAVAILABLE"
        assert grid["grid"] is None
        assert grid["is_calibrated"] is False
        assert "Tile T44QMK" in grid["reason"]

    def test_manganese_inside_tile_t44qmk_produces_genuine_calibrated_output(self):
        """Manganese inside Tile T44QMK produces a valid prediction and calibrated 3D grid."""
        assert is_within_tile(BALAGHAT_LAT, BALAGHAT_LON)

        res = analyze_location_for_mineral(
            location_name="Balaghat Mine Corridor",
            lat=BALAGHAT_LAT,
            lon=BALAGHAT_LON,
            mineral_name="Manganese",
            radius_km=10.0
        )

        assert res["mineral"] == "Manganese"
        assert res["overall_status"] == "SUCCESS"
        assert res["model_coverage"] == "VALIDATED_ACTIVE"
        assert res["prediction_availability"] == "AVAILABLE"

        # Genuine prediction payload
        pred = res["prediction"]
        assert pred is not None
        assert "prospectivity_index" in pred
        assert isinstance(pred["prospectivity_index"], (int, float))
        assert 0.0 <= pred["prospectivity_index"] <= 100.0

        # Calibrated 3D grid
        grid = res["prospectivity_grid"]
        assert grid["status"] == "AVAILABLE"
        assert grid["is_calibrated"] is True
        assert grid["grid"] is not None
        assert len(grid["grid"]) > 0
        assert grid["mineral"] == "Manganese"
        assert "Tile T44QMK" in grid["source"]


class TestNoHardcoded40PercentInAPI:
    """Ensures POST /analyze does not emit 40% default or fallback scores."""

    @pytest.mark.parametrize("mineral", ["Coal", "Iron Ore", "Bauxite"])
    def test_unmodeled_minerals_via_api_have_null_prediction_and_unavailable_grid(self, mineral):
        payload = {
            "location_name": "Balaghat Sector",
            "latitude": BALAGHAT_LAT,
            "longitude": BALAGHAT_LON,
            "mineral": mineral,
            "radius_km": 10.0
        }
        resp = client.post("/analyze", json=payload)
        assert resp.status_code == 200
        data = resp.json()

        assert data["prediction"] is None
        assert data["prospectivity_grid"]["status"] == "UNAVAILABLE"
        assert data["prospectivity_grid"]["grid"] is None
        assert data["prospectivity_grid"]["is_calibrated"] is False

    def test_manganese_outside_tile_via_api(self):
        payload = {
            "location_name": "Out of Tile Sector",
            "latitude": OUTSIDE_TILE_LAT,
            "longitude": OUTSIDE_TILE_LON,
            "mineral": "Manganese",
            "radius_km": 10.0
        }
        resp = client.post("/analyze", json=payload)
        assert resp.status_code == 200
        data = resp.json()

        assert data["prediction"] is None
        assert data["model_coverage"] == "OUTSIDE_TRAINING_FOOTPRINT"
        assert data["prospectivity_grid"]["status"] == "UNAVAILABLE"
        assert data["prospectivity_grid"]["grid"] is None


class TestDirect3DGridFunction:
    """Verifies get_prospectivity_3d_grid directly returns no synthetic peaks."""

    def test_direct_grid_function_coal(self):
        grid = get_prospectivity_3d_grid(BALAGHAT_LAT, BALAGHAT_LON, mineral_name="Coal", is_calibrated=False)
        assert grid["status"] == "UNAVAILABLE"
        assert grid["grid"] is None
        assert grid["is_calibrated"] is False

    def test_direct_grid_function_uncalibrated_manganese(self):
        grid = get_prospectivity_3d_grid(OUTSIDE_TILE_LAT, OUTSIDE_TILE_LON, mineral_name="Manganese", is_calibrated=False)
        assert grid["status"] == "UNAVAILABLE"
        assert grid["grid"] is None
        assert grid["is_calibrated"] is False
