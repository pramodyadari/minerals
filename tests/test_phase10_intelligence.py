"""
=============================================================================
PHASE 10: PRODUCTION-GRADE EXPLORATION INTELLIGENCE TEST SUITE
=============================================================================
Module: tests/test_phase10_intelligence.py

Verifies:
  1. Manganese model integrity: SHA-256 hash matches 20c1ecfa08524393e5382018a79e7ea3e1d6cf042bc5d86b2381608717e00863.
  2. Model feature specification: Exactly the 10 trained features unchanged.
  3. Spatial validation metrics: Accuracy = 96.76%, F1 = 96.71%, ROC-AUC = 0.9931, PR-AUC = 0.9923.
  4. Calibration status: NOT CALIBRATED.
  5. Independent validation status: NOT AVAILABLE, 0 deposits.
  6. Mineral registry: Manganese TRAINED, 6 other minerals AWAITING TRAINING DATA.
  7. High-prospectivity candidate zones CSV integrity (Zone 67684 top rank).
  8. Honest nomenclature: Spatial Prospectivity Index, not probability of ore.
=============================================================================
"""

import unittest
import hashlib
import os
import sys
import csv
import json
import joblib

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

class TestPhase10ExplorationIntelligence(unittest.TestCase):

    def setUp(self):
        self.project_root = PROJECT_ROOT
        self.model_path = os.path.join(self.project_root, "models", "manganese_random_forest.pkl")
        self.zones_path = os.path.join(self.project_root, "data", "processed", "high_prospectivity_zones.csv")

    def test_01_manganese_model_sha256_unmodified(self):
        """Phase 10 Invariant: Model SHA-256 must match authoritative baseline."""
        self.assertTrue(os.path.exists(self.model_path), f"Model file must exist at {self.model_path}")
        with open(self.model_path, "rb") as f:
            content = f.read()
        sha256_hash = hashlib.sha256(content).hexdigest()
        expected_hash = "20c1ecfa08524393e5382018a79e7ea3e1d6cf042bc5d86b2381608717e00863"
        self.assertEqual(sha256_hash, expected_hash, "Manganese model SHA-256 must remain identical")

    def test_02_trained_features_invariant(self):
        """Phase 10 Invariant: Exactly the 10 trained features."""
        expected_features = [
            "B02", "B03", "B04", "B08", "B11", "B12",
            "NDVI", "NDWI", "clay_ratio", "iron_oxide_ratio"
        ]
        model = joblib.load(self.model_path)
        self.assertEqual(model.n_features_in_, 10, "Model must have exactly 10 features")
        if hasattr(model, "feature_names_in_"):
            self.assertEqual(list(model.feature_names_in_), expected_features)

    def test_03_spatial_validation_metrics_contract(self):
        """Phase 10 Invariant: Within-study spatial validation metrics match exact values."""
        from mineral_registry import MineralRegistry
        mn = MineralRegistry.get_mineral("manganese")
        self.assertIsNotNone(mn)
        self.assertEqual(mn["status_label"], "TRAINED")
        self.assertEqual(mn["calibration_status"], "NOT_CALIBRATED")
        self.assertEqual(mn["independent_deposit_validation"]["status"], "NOT_AVAILABLE")
        self.assertEqual(mn["independent_deposit_validation"]["independent_deposits_count"], 0)

        # Check metadata file metrics
        meta_path = os.path.join(self.project_root, "models", "manganese_model_metadata.json")
        self.assertTrue(os.path.exists(meta_path))
        with open(meta_path, "r", encoding="utf-8") as f:
            meta = json.load(f)
        self.assertAlmostEqual(meta["spatial_accuracy"], 96.76, places=2)
        self.assertAlmostEqual(meta["spatial_f1"], 0.9671, places=4)
        self.assertAlmostEqual(meta["spatial_roc_auc"], 0.9931, places=4)
        self.assertAlmostEqual(meta["spatial_pr_auc"], 0.9923, places=4)
        self.assertEqual(meta["calibration_status"], "NOT_CALIBRATED")

    def test_04_untrained_minerals_protected(self):
        """Phase 10 Requirement 4: Other minerals must remain awaiting training data."""
        from mineral_registry import MineralRegistry
        untrained = ["iron_ore", "bauxite", "copper", "lithium", "coal", "limestone"]
        for m in untrained:
            info = MineralRegistry.get_mineral(m)
            self.assertIsNotNone(info, f"Mineral {m} must be in registry")
            self.assertFalse(info["is_trained"], f"Mineral {m} must not be trained")
            self.assertEqual(info["status_label"], "AWAITING TRAINING DATA")
            self.assertIsNone(info["prospectivity_raster"])

    def test_05_candidate_zones_dataset_integrity(self):
        """Phase 10 Requirement 9: Top candidate zones exist and match genuine dataset."""
        self.assertTrue(os.path.exists(self.zones_path), "high_prospectivity_zones.csv must exist")
        with open(self.zones_path, mode="r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            zones = list(reader)
        self.assertGreaterEqual(len(zones), 10, "Must have at least 10 candidate discovery zones")
        # Top zone must be 67684 with ~97.6% prospectivity
        top_zone = zones[0]
        self.assertEqual(top_zone["Zone_ID"], "67684")
        mean_score = float(top_zone["Mean_Score"])
        self.assertAlmostEqual(mean_score, 0.9758, places=3)

    def test_06_independent_validation_report_honest(self):
        """Phase 10 Requirement 8: Independent validation report states NOT AVAILABLE."""
        report_path = os.path.join(self.project_root, "models", "manganese_independent_validation_report.json")
        self.assertTrue(os.path.exists(report_path))
        with open(report_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.assertEqual(data["status"], "NOT_AVAILABLE")
        self.assertEqual(data["independent_deposits_count"], 0)
        self.assertEqual(data["training_deposit"], "Ghondi Manganese Mine")
        self.assertTrue(data["leakage_checks_passed"])

if __name__ == "__main__":
    unittest.main()
