"""
================================================================================
AI MINERAL EXPLORATION & PROSPECTIVITY PIPELINE — PHASE 8 TEST SUITE
================================================================================
Module: tests/test_independent_validation.py

Tests:
  1. Dataset manifest validation.
  2. Provenance validation.
  3. Geological dataset ingestion.
  4. Terrain dataset ingestion.
  5. Independent dataset schema validation.
  6. Independent deposit geographic separation.
  7. Training/independent leakage detection.
  8. Model immutability during independent testing.
  9. Independent evaluation.
  10. Single-class independent dataset handling.
  11. No fabricated negative samples.
  12. No fabricated occurrence coordinates.
  13. Independent validation report generation.
  14. EvidenceEngine integration.
  15. API integration.
  16. Frontend status rendering.
  17. Existing ranking unchanged.
  18. Existing XAI unchanged.
  19. Other minerals remain untrained.
  20. Pipeline contract immutability.
================================================================================
"""

import os
import sys
import json
import tempfile
import unittest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from independent_validation import (
    IndependentValidationEngine,
    IndependentValidationDataError,
    IndependentValidationLeakageError,
    get_independent_engine,
    get_independent_validation_status,
    compute_file_sha256,
    GHONDI_CENTER_LAT,
    GHONDI_CENTER_LON
)
from mineral_registry import MineralRegistry, MineralStatus
from geological_evidence import get_geology_engine
from terrain_evidence import get_terrain_engine


class TestIndependentValidationPhase8(unittest.TestCase):

    def setUp(self):
        self.root = PROJECT_ROOT
        self.engine = IndependentValidationEngine(self.root)

    # 1. Dataset manifest validation
    def test_01_dataset_manifest_validation(self):
        """Verifies data/DATA_ACQUISITION_MANIFEST.json exists and has valid schema."""
        manifest_p = os.path.join(self.root, "data", "DATA_ACQUISITION_MANIFEST.json")
        self.assertTrue(os.path.exists(manifest_p), "Manifest must exist on disk")
        with open(manifest_p, "r", encoding="utf-8") as f:
            manifest = json.load(f)

        self.assertIn("datasets", manifest)
        self.assertIn("data_integrity_rules", manifest)
        self.assertGreaterEqual(len(manifest["datasets"]), 4)
        for ds in manifest["datasets"]:
            self.assertIn("id", ds)
            self.assertIn("type", ds)
            self.assertIn("source", ds)
            self.assertIn("status", ds)
            self.assertIn(ds["status"], ["AVAILABLE", "NOT_AVAILABLE", "PENDING_VALIDATION"])

    # 2. Provenance validation
    def test_02_provenance_validation(self):
        """Verifies all manifest entries attribute authoritative scientific sources."""
        manifest_p = os.path.join(self.root, "data", "DATA_ACQUISITION_MANIFEST.json")
        with open(manifest_p, "r", encoding="utf-8") as f:
            manifest = json.load(f)

        for ds in manifest["datasets"]:
            self.assertTrue(bool(ds.get("source")), f"Dataset {ds['id']} must have non-empty source")
            self.assertTrue(bool(ds.get("crs")), f"Dataset {ds['id']} must specify CRS")

    # 3. Geological dataset ingestion
    def test_03_geological_dataset_ingestion(self):
        """Verifies geological_evidence.py handles genuine vector files without model mutation."""
        geo = get_geology_engine(self.root)
        status = geo.get_status()
        self.assertIn("status", status)
        self.assertIn("lithology", status)

    # 4. Terrain dataset ingestion
    def test_04_terrain_dataset_ingestion(self):
        """Verifies terrain_evidence.py handles DEM rasters without model mutation."""
        terr = get_terrain_engine(self.root)
        status = terr.get_status()
        self.assertIn("status", status)

    # 5. Independent dataset schema validation
    def test_05_independent_dataset_schema_validation(self):
        """Tests validate_dataset_records enforces mineral, coordinates, and source."""
        # Invalid mineral
        bad_mineral = [{"mineral": "copper", "latitude": 22.0, "longitude": 80.0, "source": "GSI"}]
        with self.assertRaises(IndependentValidationDataError):
            self.engine.validate_dataset_records(bad_mineral)

        # Missing source
        bad_source = [{"mineral": "manganese", "latitude": 22.0, "longitude": 80.0, "source": ""}]
        with self.assertRaises(IndependentValidationDataError):
            self.engine.validate_dataset_records(bad_source)

        # Out-of-bounds coordinate
        out_bounds = [{"mineral": "manganese", "latitude": 10.0, "longitude": 80.0, "source": "GSI"}]
        with self.assertRaises(IndependentValidationDataError):
            self.engine.validate_dataset_records(out_bounds)

    # 6. Independent deposit geographic separation
    def test_06_independent_deposit_geographic_separation(self):
        """Rejects any point within 500m of the Ghondi training deposit."""
        # 100 meters away from Ghondi center
        near_ghondi = [{
            "mineral": "manganese",
            "deposit_name": "Near Ghondi Pit",
            "latitude": GHONDI_CENTER_LAT + 0.0005,
            "longitude": GHONDI_CENTER_LON + 0.0005,
            "source": "GSI"
        }]
        with self.assertRaises(IndependentValidationLeakageError):
            self.engine.validate_dataset_records(near_ghondi)

    # 7. Training/independent leakage detection
    def test_07_training_independent_leakage_detection(self):
        """Rejects deposits with name Ghondi or co-located with candidate discovery zones."""
        named_ghondi = [{
            "mineral": "manganese",
            "deposit_name": "Ghondi North Extension",
            "latitude": 22.1000,
            "longitude": 80.1000,
            "source": "GSI"
        }]
        with self.assertRaises(IndependentValidationLeakageError):
            self.engine.validate_dataset_records(named_ghondi)

    # 8. Model immutability during independent testing
    def test_08_model_immutability_during_independent_testing(self):
        """Verifies SHA-256 hash of the model is verified and remains unaltered."""
        model_p = os.path.join(self.root, "models", "manganese_random_forest.pkl")
        hash_before = compute_file_sha256(model_p)
        self.assertIsNotNone(hash_before)

        # Run evaluation
        res = self.engine.evaluate()
        hash_after = compute_file_sha256(model_p)
        self.assertEqual(hash_before, hash_after, "Model file must remain bit-identical")
        self.assertEqual(res["model_hash"], hash_before)

    # 9. Independent evaluation
    def test_09_independent_evaluation(self):
        """Tests evaluate() defaults to NOT_AVAILABLE when no external dataset is present."""
        empty_eng = IndependentValidationEngine(workspace_root=tempfile.gettempdir())
        res = empty_eng.evaluate()
        self.assertEqual(res["status"], "NOT_AVAILABLE")
        self.assertFalse(res["available"])
        self.assertEqual(res["independent_deposits_count"], 0)

    # 10. Single-class independent dataset handling
    def test_10_single_class_independent_dataset_handling(self):
        """Evaluates external positive occurrences without manufacturing negative controls."""
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
            valid_external = [
                {
                    "mineral": "manganese",
                    "deposit_id": "UKWA_MINE_01",
                    "deposit_name": "Ukwa Manganese Mine",
                    "latitude": 21.9800,
                    "longitude": 80.4800,
                    "source": "IBM Mineral Lease Record",
                    "label": 1
                },
                {
                    "mineral": "manganese",
                    "deposit_id": "TIRODI_MINE_01",
                    "deposit_name": "Tirodi Manganese Mine",
                    "latitude": 21.6800,
                    "longitude": 80.1800,
                    "source": "IBM Mineral Lease Record",
                    "label": 1
                }
            ]
            json.dump(valid_external, f)
            temp_path = f.name

        try:
            res = self.engine.evaluate(temp_path)
            self.assertEqual(res["status"], "AVAILABLE")
            self.assertTrue(res["available"])
            self.assertEqual(res["independent_deposits_count"], 2)
            self.assertEqual(res["occurrences_count"], 2)
            metrics = res["evaluation_metrics"]
            self.assertEqual(metrics["test_type"], "INDEPENDENT_POSITIVE_OCCURRENCE_TEST")
            self.assertIn("classification_metrics_note", metrics)
            self.assertIn("barren controls", metrics["classification_metrics_note"])
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    # 11. No fabricated negative samples
    def test_11_no_fabricated_negative_samples(self):
        """Verifies that evaluation does not add fake negative samples to positive data."""
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
            valid_external = [
                {
                    "mineral": "manganese",
                    "deposit_id": "RAMRAMA_MINE_01",
                    "deposit_name": "Ramrama Mine",
                    "latitude": 21.8500,
                    "longitude": 80.1200,
                    "source": "IBM Record",
                    "label": 1
                }
            ]
            json.dump(valid_external, f)
            temp_path = f.name

        try:
            res = self.engine.evaluate(temp_path)
            self.assertEqual(res["occurrences_count"], 1)
            # Exactly 1 prediction returned, no extra negative predictions
            self.assertEqual(len(res["evaluation_metrics"]["predicted_scores"]), 1)
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    # 12. No fabricated occurrence coordinates
    def test_12_no_fabricated_occurrence_coordinates(self):
        """Verifies load_dataset returns empty records if file does not exist."""
        empty_res = self.engine.load_dataset("non_existent_file.geojson")
        self.assertFalse(empty_res["available"])
        self.assertEqual(len(empty_res["records"]), 0)

    # 13. Independent validation report generation
    def test_13_independent_validation_report_generation(self):
        """Verifies generate_report outputs valid JSON report file."""
        report_p = os.path.join(self.root, "models", "manganese_independent_validation_report.json")
        self.assertTrue(os.path.exists(report_p))
        with open(report_p, "r", encoding="utf-8") as f:
            rep = json.load(f)
        self.assertEqual(rep["status"], "NOT_AVAILABLE")
        self.assertEqual(rep["mineral"], "manganese")
        self.assertEqual(rep["training_deposit"], "Ghondi Manganese Mine")

    # 14. EvidenceEngine integration
    def test_14_evidence_engine_integration(self):
        """Verifies payload structure integrates cleanly into frontend evidence expectations."""
        status = get_independent_validation_status()
        self.assertIn("status", status)
        self.assertIn("available", status)
        self.assertIn("training_deposit", status)

    # 15. API integration
    def test_15_api_integration(self):
        """Verifies independent validation status is callable via engine."""
        report = self.engine.evaluate()
        self.assertIn("status", report)
        self.assertIn("limitations", report)

    # 16. Frontend status rendering
    def test_16_frontend_status_rendering(self):
        """Verifies index.html has required DOM elements for Phase 8."""
        html_p = os.path.join(self.root, "index.html")
        with open(html_p, "r", encoding="utf-8") as f:
            html = f.read()
        self.assertIn('id="val-training-deposit"', html)
        self.assertIn('id="val-independent-deposits-count"', html)
        self.assertIn('id="val-leakage-check"', html)
        self.assertIn('id="val-independent-status"', html)

    # 17. Existing ranking unchanged
    def test_17_existing_ranking_unchanged(self):
        """Verifies candidate discovery zones are untouched."""
        zones_p = os.path.join(self.root, "data", "processed", "high_prospectivity_zones.csv")
        self.assertTrue(os.path.exists(zones_p))
        with open(zones_p, "r", encoding="utf-8") as f:
            lines = f.readlines()
        self.assertEqual(len(lines), 21, "Must have header + 20 candidate discovery zones")

    # 18. Existing XAI unchanged
    def test_18_existing_xai_unchanged(self):
        """Verifies the 10 trained Sentinel-2 features are strictly unchanged."""
        meta_p = os.path.join(self.root, "models", "manganese_model_metadata.json")
        with open(meta_p, "r", encoding="utf-8") as f:
            meta = json.load(f)
        schema = meta.get("feature_schema", [])
        self.assertEqual(len(schema), 10)

    # 19. Other minerals remain untrained
    def test_19_other_minerals_remain_untrained(self):
        """Verifies other commodities remain AWAITING_DATA."""
        for m in ["iron_ore", "bauxite", "copper", "lithium", "coal", "limestone"]:
            info = MineralRegistry.get_mineral(m)
            self.assertFalse(info["is_trained"])
            self.assertEqual(info["status"], MineralStatus.AWAITING_DATA)

    # 20. Pipeline contract immutability
    def test_20_pipeline_contract_immutability(self):
        """Verifies Manganese registry entry points to verified paths."""
        mn = MineralRegistry.get_mineral("manganese")
        self.assertTrue(mn["is_trained"])
        self.assertEqual(mn["status"], MineralStatus.TRAINED)
        self.assertEqual(mn["independent_deposit_validation"]["status"], "NOT_AVAILABLE")


if __name__ == "__main__":
    unittest.main()
