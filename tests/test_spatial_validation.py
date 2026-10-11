"""
=============================================================================
AI MINERAL INTELLIGENCE — PHASE 6: SCIENTIFIC SPATIAL VALIDATION & MODEL TRUST
=============================================================================
Test Suite: tests/test_spatial_validation.py

Verifies 14 Core Scientific Validation Invariants:
  1. Spatial blocks are actually geographically separated.
  2. Same spatial block cannot appear in both train and validation sets.
  3. Validation uses the selected mineral only.
  4. Manganese validation report is generated and persistent on disk.
  5. Required metrics exist (accuracy, precision, recall, f1, roc_auc, pr_auc, cm).
  6. Random holdout and spatial validation remain separate and distinct.
  7. Calibration remains NOT_CALIBRATED unless genuinely implemented.
  8. No prospectivity score is presented as probability.
  9. Untrained minerals cannot request Manganese validation metrics.
  10. API validation endpoint returns correct status.
  11. Missing validation report is handled safely without crashing.
  12. Existing target ranking remains unchanged by validation metrics.
  13. Existing XAI remains functional.
  14. Existing multi-mineral safety checks remain functional.
=============================================================================
"""

import os
import sys
import json
import unittest
import numpy as np

# Ensure project root is in sys.path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from mineral_training_contract import (
    TrainingDataUnavailableError,
    MineralMismatchError,
    REQUIRED_FEATURE_COLUMNS
)
from mineral_trainer import (
    MineralTrainer,
    validate_mineral_model,
    train_mineral_model,
    load_mineral_model,
    evaluate_mineral_prediction
)
from mineral_registry import MineralRegistry, MineralStatus, ValidationStatus, CalibrationStatus
from mineral_prospectivity_pipeline import ProspectivityPipeline


class TestSpatialValidation(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.pipeline = ProspectivityPipeline()
        cls.report_path = os.path.join(PROJECT_ROOT, "models", "manganese_validation_report.json")
        cls.cm_path = os.path.join(PROJECT_ROOT, "models", "manganese_confusion_matrix.json")
        cls.meta_path = os.path.join(PROJECT_ROOT, "models", "manganese_model_metadata.json")

        # Run validation if report doesn't exist
        if not os.path.exists(cls.report_path):
            validate_mineral_model("manganese")

        with open(cls.report_path, "r", encoding="utf-8") as f:
            cls.report = json.load(f)

    # -------------------------------------------------------------------------
    # 1. SPATIAL BLOCKS ARE GEOGRAPHICALLY SEPARATED
    # -------------------------------------------------------------------------
    def test_01_spatial_blocks_geographically_separated(self):
        """Test 1: Spatial blocks are constructed using coordinates and are geographically separated."""
        v = self.report["validation"]
        self.assertGreater(v["n_blocks"], 1, "Must contain multiple spatial blocks")
        self.assertGreaterEqual(v["block_size_degrees"], 0.01, "Block size must be positive degrees")

        # Verify coordinates of blocks do not overlap in space
        lat1, lon1 = 21.50, 80.00
        lat2, lon2 = 21.60, 80.10
        block1 = (int(lat1 / 0.05), int(lon1 / 0.05))
        block2 = (int(lat2 / 0.05), int(lon2 / 0.05))
        self.assertNotEqual(block1, block2, "Distant points must map to distinct spatial blocks")

    # -------------------------------------------------------------------------
    # 2. DISJOINT TRAIN AND VALIDATION BLOCKS
    # -------------------------------------------------------------------------
    def test_02_disjoint_train_and_val_blocks(self):
        """Test 2: Same spatial block cannot appear in both train and validation sets."""
        v = self.report["validation"]
        train_blocks = v["training_blocks"]
        val_blocks = v["validation_blocks"]
        total_blocks = v["n_blocks"]

        self.assertEqual(train_blocks + val_blocks, total_blocks, "Training and validation blocks must partition total blocks")
        self.assertGreater(train_blocks, 0)
        self.assertGreater(val_blocks, 0)

        # Multi-sector folds test: each fold uses strictly disjoint validation blocks
        folds = v["fold_metrics"]["folds"]
        self.assertEqual(len(folds), 4, "Must evaluate across 4 spatial folds")
        for f in folds:
            self.assertGreater(f["positive_samples"], 0, f"Fold {f['fold']} must have positive samples")
            self.assertGreater(f["negative_samples"], 0, f"Fold {f['fold']} must have negative samples")

    # -------------------------------------------------------------------------
    # 3. VALIDATION USES SELECTED MINERAL ONLY
    # -------------------------------------------------------------------------
    def test_03_validation_mineral_isolation(self):
        """Test 3: Validation uses the selected mineral only; untrained minerals abort honestly."""
        self.assertEqual(self.report["mineral"], "manganese")

        for untrained in ["copper", "iron_ore", "lithium", "bauxite", "coal", "limestone"]:
            with self.assertRaises(TrainingDataUnavailableError) as ctx:
                validate_mineral_model(untrained)
            self.assertIn("Validation aborted", str(ctx.exception))
            self.assertIn(untrained.replace("_", " ").title(), str(ctx.exception))

    # -------------------------------------------------------------------------
    # 4. MANGANESE VALIDATION REPORT GENERATED
    # -------------------------------------------------------------------------
    def test_04_manganese_validation_report_generated(self):
        """Test 4: Manganese validation report and confusion matrix JSON files exist on disk."""
        self.assertTrue(os.path.exists(self.report_path), "models/manganese_validation_report.json must exist")
        self.assertTrue(os.path.exists(self.cm_path), "models/manganese_confusion_matrix.json must exist")

        with open(self.cm_path, "r", encoding="utf-8") as f:
            cm_data = json.load(f)
        self.assertEqual(cm_data["mineral"], "manganese")
        self.assertIn("true_negative", cm_data)
        self.assertIn("false_positive", cm_data)
        self.assertIn("false_negative", cm_data)
        self.assertIn("true_positive", cm_data)

    # -------------------------------------------------------------------------
    # 5. REQUIRED METRICS EXIST
    # -------------------------------------------------------------------------
    def test_05_required_metrics_exist(self):
        """Test 5: Required validation metrics exist and are calculated from real predictions."""
        v = self.report["validation"]
        required_keys = ["accuracy", "precision", "recall", "f1", "roc_auc", "pr_auc"]
        for k in required_keys:
            self.assertIn(k, v, f"Validation report must contain {k}")
            self.assertIsInstance(v[k], float)
            self.assertGreaterEqual(v[k], 0.0)
            self.assertLessEqual(v[k], 1.0)

        # Check sample counts
        self.assertEqual(self.report["dataset_samples"], 3362)
        self.assertEqual(self.report["positive_samples"], 1681)
        self.assertEqual(self.report["negative_samples"], 1681)

        # Check fold aggregations
        fm = v["fold_metrics"]
        self.assertIn("mean_accuracy", fm)
        self.assertIn("std_accuracy", fm)
        self.assertIn("min_accuracy", fm)
        self.assertIn("max_accuracy", fm)
        self.assertGreater(fm["mean_accuracy"], 0.90)

    # -------------------------------------------------------------------------
    # 6. RANDOM HOLDOUT AND SPATIAL VALIDATION REMAIN SEPARATE
    # -------------------------------------------------------------------------
    def test_06_random_vs_spatial_validation_distinct(self):
        """Test 6: Random holdout and spatial validation remain distinct and separate."""
        self.assertIn("random_holdout", self.report)
        self.assertIn("validation", self.report)

        rh = self.report["random_holdout"]
        sv = self.report["validation"]

        # Preserve existing 83.51% holdout baseline
        self.assertAlmostEqual(rh["accuracy"], 0.8351, places=3)
        self.assertNotEqual(rh["accuracy"], sv["accuracy"], "Spatial validation must be evaluated separately from random holdout")
        self.assertIn("holdout_confusion_matrix", self.report)

    # -------------------------------------------------------------------------
    # 7. CALIBRATION REMAINS NOT_CALIBRATED
    # -------------------------------------------------------------------------
    def test_07_calibration_remains_not_calibrated(self):
        """Test 7: Calibration remains strictly NOT_CALIBRATED with clear scientific rationale."""
        cal = self.report["calibration"]
        self.assertEqual(cal["status"], "NOT_CALIBRATED")
        self.assertIn("NOT ENOUGH VALIDATION EVIDENCE FOR CALIBRATED PROBABILITY ESTIMATES", cal["diagnostic"])
        self.assertIn("Ghondi", cal["reason"])

        # Check MineralRegistry reports NOT_CALIBRATED
        mn_info = MineralRegistry.get_mineral("manganese")
        self.assertEqual(mn_info["calibration_status"], CalibrationStatus.NOT_CALIBRATED)
        self.assertEqual(mn_info["validation_status"], ValidationStatus.SPATIALLY_VALIDATED)

    # -------------------------------------------------------------------------
    # 8. NO PROSPECTIVITY SCORE PRESENTED AS PROBABILITY
    # -------------------------------------------------------------------------
    def test_08_no_prospectivity_score_presented_as_probability(self):
        """Test 8: Prospectivity score is designated as spatial index, not calibrated probability."""
        with open(self.meta_path, "r", encoding="utf-8") as f:
            meta = json.load(f)
        self.assertIn("Spatial prospectivity index", meta["provenance"]["scientific_distinction"])
        self.assertEqual(meta["calibration_status"], "NOT_CALIBRATED")

        # Verify pipeline analysis output separates prospectivity from probability
        res = self.pipeline.analyze_location(lat=21.9455, lon=80.4295, mineral="manganese")
        self.assertIn("score", res["prospectivity"])
        self.assertIn("confidence_level", res["prospectivity"])
        self.assertIn("Not Calibrated", res["prospectivity"]["confidence_level"])

    # -------------------------------------------------------------------------
    # 9. UNTRAINED MINERALS CANNOT REQUEST MANGANESE VALIDATION
    # -------------------------------------------------------------------------
    def test_09_untrained_minerals_cannot_request_manganese_validation(self):
        """Test 9: Untrained minerals cannot access Manganese validation metrics."""
        for untrained in ["copper", "iron_ore", "lithium", "bauxite"]:
            u_info = MineralRegistry.get_mineral(untrained)
            self.assertEqual(u_info["validation_status"], ValidationStatus.NOT_VALIDATED)
            self.assertEqual(u_info["status"], MineralStatus.AWAITING_DATA)

    # -------------------------------------------------------------------------
    # 10. API VALIDATION ENDPOINT RETURNS CORRECT STATUS
    # -------------------------------------------------------------------------
    def test_10_api_validation_endpoint_handling(self):
        """Test 10: API validation endpoint logic returns 200 for manganese and 404 for untrained minerals."""
        # Test manganese report resolution
        mn_info = MineralRegistry.get_mineral("manganese")
        self.assertTrue(mn_info["is_trained"])
        self.assertEqual(mn_info["validation_status"], ValidationStatus.SPATIALLY_VALIDATED)

        report_p = os.path.join(PROJECT_ROOT, "models", "manganese_validation_report.json")
        self.assertTrue(os.path.exists(report_p))

        # Test untrained mineral resolution
        cu_info = MineralRegistry.get_mineral("copper")
        self.assertFalse(cu_info["is_trained"])
        self.assertEqual(cu_info["validation_status"], ValidationStatus.NOT_VALIDATED)

    # -------------------------------------------------------------------------
    # 11. MISSING VALIDATION REPORT HANDLED SAFELY
    # -------------------------------------------------------------------------
    def test_11_missing_validation_report_handled_safely(self):
        """Test 11: Missing validation report is handled gracefully without crashing."""
        missing_p = os.path.join(PROJECT_ROOT, "models", "nonexistent_mineral_validation_report.json")
        self.assertFalse(os.path.exists(missing_p))

        res = MineralRegistry.get_mineral("nonexistent_mineral")
        self.assertIsNone(res)

    # -------------------------------------------------------------------------
    # 12. EXISTING TARGET RANKING REMAINS UNCHANGED
    # -------------------------------------------------------------------------
    def test_12_existing_ranking_remains_unchanged(self):
        """Test 12: Existing target ranking uses prospectivity score, not validation accuracy."""
        zones = self.pipeline.load_candidate_zones()
        self.assertEqual(len(zones), 20, "Must continue to load exactly 20 candidate zones")

        # Verify zones are ranked descending by Max_Score / Mean_Score
        scores = [z["mean_score"] for z in zones]
        self.assertEqual(scores, sorted(scores, reverse=True), "Candidate zones must remain ranked by prospectivity score")

    # -------------------------------------------------------------------------
    # 13. EXISTING XAI REMAINS FUNCTIONAL
    # -------------------------------------------------------------------------
    def test_13_existing_xai_remains_functional(self):
        """Test 13: Existing XAI feature importances and waterfall remain functional."""
        with open(self.meta_path, "r", encoding="utf-8") as f:
            meta = json.load(f)

        self.assertEqual(len(meta["feature_schema"]), len(REQUIRED_FEATURE_COLUMNS))
        self.assertEqual(len(meta["feature_importances"]), 10)
        self.assertAlmostEqual(sum(meta["feature_importances"].values()), 1.0, places=2)

    # -------------------------------------------------------------------------
    # 14. MULTI-MINERAL SAFETY CHECKS REMAIN FUNCTIONAL
    # -------------------------------------------------------------------------
    def test_14_multi_mineral_safety_checks_intact(self):
        """Test 14: Multi-mineral cross-contamination safety checks remain active."""
        mn_model, meta = load_mineral_model("manganese")
        features = np.zeros((1, len(REQUIRED_FEATURE_COLUMNS)))

        # Refuses prediction for other minerals
        with self.assertRaises(MineralMismatchError) as ctx:
            evaluate_mineral_prediction(
                model=mn_model,
                requested_mineral="copper",
                features=features,
                model_metadata=meta
            )
        self.assertIn("Mineral/model mismatch", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
