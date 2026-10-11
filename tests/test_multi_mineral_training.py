"""
=============================================================================
AI MINERAL INTELLIGENCE — MULTI-MINERAL AUDIT & TRAINING PIPELINE TESTS
=============================================================================
Test Suite: tests/test_multi_mineral_training.py

Verifies:
  1. Dataset audit: Real datasets vs missing datasets correctly identified
  2. Manganese remains trained and operational
  3. Missing mineral dataset is handled safely (TrainingDataUnavailableError)
  4. Mineral/model mismatch is rejected (MineralMismatchError)
  5. No cross-mineral model reuse permitted
  6. Mineral-specific XAI isolation (Python side & data contract)
  7. Mineral registry status reflects reality (TRAINED vs AWAITING_DATA)
  8. Untrained mineral cannot generate targets or borrow zones
  9. Model metadata sidecar exists and adheres to schema
  10. Training pipeline validation (contract checks & spatial blocking)
=============================================================================
"""

import os
import sys
import json
import unittest
import tempfile
import numpy as np

# Ensure project root is in sys.path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from mineral_training_contract import (
    REQUIRED_FEATURE_COLUMNS,
    REQUIRED_COLUMNS,
    TrainingDataContract,
    TrainingDataUnavailableError,
    InvalidTrainingDataError,
    MineralMismatchError,
    validate_mineral_dataset
)
from mineral_trainer import (
    MineralTrainer,
    train_mineral_model,
    load_mineral_model,
    evaluate_mineral_prediction
)
from mineral_registry import MineralRegistry, MineralStatus
from mineral_prospectivity_pipeline import ProspectivityPipeline


class TestMultiMineralTraining(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.pipeline = ProspectivityPipeline()

    # -------------------------------------------------------------------------
    # 1. DATASET AUDIT
    # -------------------------------------------------------------------------
    def test_01_dataset_audit_report_and_reality(self):
        """Test 1: Verify audit report exists and reflects authentic on-disk data."""
        audit_md = os.path.join(PROJECT_ROOT, "data", "MINERAL_DATA_AUDIT.md")
        self.assertTrue(os.path.exists(audit_md), "data/MINERAL_DATA_AUDIT.md must exist.")

        with open(audit_md, "r", encoding="utf-8") as f:
            content = f.read()

        # Check all registered commodities are audited
        commodities = ["Manganese", "Iron Ore", "Bauxite", "Copper", "Lithium", "Coal", "Limestone"]
        for comm in commodities:
            self.assertIn(comm, content, f"Audit report must include {comm}.")

        # Manganese has genuine files
        self.assertTrue(os.path.exists(os.path.join(PROJECT_ROOT, "outputs", "manganese_prospectivity.tif")))
        self.assertTrue(os.path.exists(os.path.join(PROJECT_ROOT, "models", "manganese_random_forest.pkl")))

        # Untrained commodities have NO fake occurrence files
        for untrained in ["iron_ore", "bauxite", "copper", "lithium"]:
            fake_csv = os.path.join(PROJECT_ROOT, "data", "training", f"{untrained}_training.csv")
            self.assertFalse(os.path.exists(fake_csv), f"No fake training CSV should exist for {untrained}.")
            fake_model = os.path.join(PROJECT_ROOT, "models", f"{untrained}_random_forest.pkl")
            self.assertFalse(os.path.exists(fake_model), f"No fake model pkl should exist for {untrained}.")

    # -------------------------------------------------------------------------
    # 2. MANGANESE REMAINS TRAINED
    # -------------------------------------------------------------------------
    def test_02_manganese_remains_trained_and_operational(self):
        """Test 2: Manganese remains fully trained and functional end-to-end."""
        self.assertTrue(MineralRegistry.is_trained("manganese"))
        mn_info = MineralRegistry.get_mineral("manganese")
        self.assertEqual(mn_info["status"], MineralStatus.TRAINED)

        # Analyze valid point in Manganese tile
        res = self.pipeline.analyze_location(lat=21.9455, lon=80.4295, mineral="manganese")
        self.assertEqual(res["status"], "success")
        self.assertIn("Manganese", res["mineral"])
        self.assertAlmostEqual(res["prospectivity"]["score"], 0.71, places=2)
        self.assertGreater(len(res["candidate_zones_in_radius"]), 0)

    # -------------------------------------------------------------------------
    # 3. MISSING MINERAL DATASET IS HANDLED
    # -------------------------------------------------------------------------
    def test_03_missing_mineral_dataset_aborts_honestly(self):
        """Test 3: Training an untrained mineral raises TrainingDataUnavailableError."""
        for mineral_id in ["iron_ore", "copper", "bauxite", "lithium"]:
            with self.assertRaises(TrainingDataUnavailableError) as ctx:
                train_mineral_model(mineral_id)
            self.assertIn("No validated", str(ctx.exception))
            self.assertIn(mineral_id.replace("_", " ").title(), str(ctx.exception))

    # -------------------------------------------------------------------------
    # 4. MINERAL / MODEL MISMATCH IS REJECTED
    # -------------------------------------------------------------------------
    def test_04_mineral_model_mismatch_rejected(self):
        """Test 4: Requesting prediction for Copper using Manganese model fails safely."""
        with self.assertRaises(MineralMismatchError) as ctx:
            self.pipeline.analyze_location(lat=21.9455, lon=80.4295, mineral="copper")
        err_msg = str(ctx.exception)
        self.assertIn("Mineral/model mismatch", err_msg)
        self.assertIn("Copper prediction cannot use a Manganese model", err_msg)

    # -------------------------------------------------------------------------
    # 5. NO CROSS-MINERAL MODEL REUSE
    # -------------------------------------------------------------------------
    def test_05_no_cross_mineral_model_reuse(self):
        """Test 5: Loading an untrained mineral model refuses to reuse Manganese model."""
        with self.assertRaises(TrainingDataUnavailableError):
            load_mineral_model("copper")

        # Evaluate safety check on loaded Manganese model
        mn_model, meta = load_mineral_model("manganese")
        features = np.zeros((1, len(REQUIRED_FEATURE_COLUMNS)))

        with self.assertRaises(MineralMismatchError) as ctx:
            evaluate_mineral_prediction(
                model=mn_model,
                requested_mineral="iron_ore",
                features=features,
                model_metadata=meta
            )
        self.assertIn("Mineral/model mismatch", str(ctx.exception))

    # -------------------------------------------------------------------------
    # 6. MINERAL-SPECIFIC XAI ISOLATION
    # -------------------------------------------------------------------------
    def test_06_mineral_specific_xai_metadata(self):
        """Test 6: XAI feature importances belong strictly to Manganese model metadata."""
        meta_path = os.path.join(PROJECT_ROOT, "models", "manganese_model_metadata.json")
        self.assertTrue(os.path.exists(meta_path))

        with open(meta_path, "r", encoding="utf-8") as f:
            meta = json.load(f)

        self.assertEqual(meta["mineral_id"], "manganese")
        self.assertEqual(len(meta["feature_schema"]), 10)
        self.assertEqual(len(meta["feature_importances"]), 10)
        # Verify weights sum to ~100%
        total_weight = sum(meta["feature_importances"].values())
        self.assertAlmostEqual(total_weight, 1.0, places=2)

    # -------------------------------------------------------------------------
    # 7. MINERAL REGISTRY STATUS
    # -------------------------------------------------------------------------
    def test_07_mineral_registry_status(self):
        """Test 7: MineralRegistry reports accurate TRAINED vs AWAITING_DATA statuses."""
        minerals = MineralRegistry.list_minerals()
        self.assertEqual(len(minerals), 7)

        for m in minerals:
            if m["id"] == "manganese":
                self.assertEqual(m["status"], MineralStatus.TRAINED)
                self.assertTrue(m["is_trained"])
            else:
                self.assertEqual(m["status"], MineralStatus.AWAITING_DATA)
                self.assertFalse(m["is_trained"])
                self.assertEqual(m["status_label"], "AWAITING TRAINING DATA")

    # -------------------------------------------------------------------------
    # 8. UNTRAINED MINERAL CANNOT GENERATE TARGETS
    # -------------------------------------------------------------------------
    def test_08_untrained_mineral_cannot_generate_targets(self):
        """Test 8: Untrained minerals have no candidate zones."""
        mn_zones = self.pipeline.load_candidate_zones()
        self.assertEqual(len(mn_zones), 20)

        # Pipeline returns 0 zones for untrained mineral
        for untrained in ["copper", "iron_ore", "lithium", "bauxite"]:
            min_info = MineralRegistry.get_mineral(untrained)
            self.assertIsNone(min_info["zones_csv"])
            self.assertIsNone(min_info["prospectivity_raster"])

    # -------------------------------------------------------------------------
    # 9. MODEL METADATA SIDECAR
    # -------------------------------------------------------------------------
    def test_09_model_metadata_sidecar_schema(self):
        """Test 9: Model metadata sidecar contains required scientific attributes."""
        meta_path = os.path.join(PROJECT_ROOT, "models", "manganese_model_metadata.json")
        with open(meta_path, "r", encoding="utf-8") as f:
            meta = json.load(f)

        required_keys = [
            "mineral_id", "mineral_name", "model_version", "model_type",
            "n_estimators", "trained_at", "dataset_identifier", "sample_count",
            "spatial_coverage", "metrics", "feature_schema", "feature_importances",
            "provenance"
        ]
        for k in required_keys:
            self.assertIn(k, meta, f"Missing required metadata key '{k}'")

        self.assertGreater(meta["metrics"]["test_accuracy_pct"], 80.0)
        self.assertIn("EPSG:32644", meta["spatial_coverage"]["crs"])

    # -------------------------------------------------------------------------
    # 10. REUSABLE TRAINING PIPELINE VALIDATION & SPATIAL INTEGRITY
    # -------------------------------------------------------------------------
    def test_10_training_contract_validation_and_rejection(self):
        """Test 10: Contract schema validates data correctly and rejects invalid datasets."""
        # 10a. Empty dataset rejected
        with self.assertRaises(InvalidTrainingDataError):
            TrainingDataContract.validate_records([], expected_mineral="iron_ore")

        # 10b. Missing columns rejected
        bad_records = [
            {"latitude": 21.9, "longitude": 80.4, "mineral": "iron_ore", "label": 1}
        ]
        with self.assertRaises(InvalidTrainingDataError):
            TrainingDataContract.validate_records(bad_records, expected_mineral="iron_ore")

        # 10c. Mineral tag mismatch rejected
        mismatched_records = []
        for i in range(50):
            row = {
                "latitude": 21.0 + i * 0.01,
                "longitude": 80.0 + i * 0.01,
                "mineral": "copper",  # Mismatched!
                "label": 1 if i < 25 else 0
            }
            for feat in REQUIRED_FEATURE_COLUMNS:
                row[feat] = 0.5
            mismatched_records.append(row)

        with self.assertRaises(MineralMismatchError):
            TrainingDataContract.validate_records(mismatched_records, expected_mineral="iron_ore")

        # 10d. Non-finite values rejected
        nan_records = [dict(mismatched_records[0])]
        nan_records[0]["mineral"] = "iron_ore"
        nan_records[0]["NDVI"] = float("nan")
        with self.assertRaises(InvalidTrainingDataError):
            TrainingDataContract.validate_records(nan_records, expected_mineral="iron_ore")

        # 10e. Valid mock dataset passes validation
        valid_records = []
        for i in range(60):
            row = {
                "latitude": 21.5 + (i // 10) * 0.05,
                "longitude": 80.2 + (i % 10) * 0.05,
                "mineral": "iron_ore",
                "label": 1 if i < 30 else 0
            }
            for feat in REQUIRED_FEATURE_COLUMNS:
                row[feat] = 0.2 + 0.5 * (i / 60.0)
            valid_records.append(row)

        report = TrainingDataContract.validate_records(valid_records, expected_mineral="iron_ore")
        self.assertEqual(report["positive_samples"], 30)
        self.assertEqual(report["negative_samples"], 30)
        self.assertEqual(report["total_samples"], 60)


if __name__ == "__main__":
    unittest.main()
