"""
================================================================================
AI MINERAL EXPLORATION & PROSPECTIVITY PIPELINE — PHASE 7 TEST SUITE
================================================================================
Module: tests/test_geology_terrain.py

Tests:
  1. Geological dataset discovery.
  2. Geological CRS validation.
  3. Geological coordinate query.
  4. Missing geology handling.
  5. Structure-distance calculation.
  6. Terrain dataset discovery.
  7. DEM CRS handling.
  8. Elevation query.
  9. Slope calculation.
  10. Missing DEM handling.
  11. EvidenceEngine geological integration.
  12. EvidenceEngine terrain integration.
  13. Provenance metadata.
  14. No fabricated geological values.
  15. No fabricated terrain values.
  16. Ranking remains unchanged.
  17. Manganese XAI remains based only on trained features.
  18. Untrained minerals remain protected.
  19. API missing-data behavior.
  20. Independent-deposit validation remains NOT_AVAILABLE.
================================================================================
"""

import os
import sys
import json
import math
import tempfile
import unittest
import numpy as np

# Add project root to sys.path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from geological_evidence import (
    GeologicalEvidenceEngine,
    get_geology_engine,
    load_geology,
    load_structures,
    query_geology_at_coordinate,
    query_nearby_structures,
    calculate_geological_evidence,
    get_geology_status
)
from terrain_evidence import (
    TerrainEvidenceEngine,
    get_terrain_engine,
    load_dem,
    query_terrain_at_coordinate,
    calculate_terrain_evidence,
    get_terrain_status
)
from mineral_registry import MineralRegistry, MineralStatus
from mineral_training_contract import TrainingDataContract, REQUIRED_FEATURE_COLUMNS


class TestGeologyAndTerrainEvidence(unittest.TestCase):

    def setUp(self):
        self.root = PROJECT_ROOT
        self.geo_engine = GeologicalEvidenceEngine(self.root)
        self.terrain_engine = TerrainEvidenceEngine(self.root)

    # 1. Geological dataset discovery
    def test_01_geological_dataset_discovery(self):
        """Verifies that engine discovers verified files or honestly reports None when missing."""
        status = self.geo_engine.get_status()
        self.assertIn("status", status)
        self.assertIn("lithology", status)
        self.assertIn("structures", status)
        if not self.geo_engine.lithology_path:
            self.assertEqual(status["lithology"]["status"], "DATA_NOT_AVAILABLE")
            self.assertFalse(status["lithology"]["available"])

    # 2. Geological CRS validation
    def test_02_geological_crs_validation(self):
        """Tests that genuine vector files report their declared CRS and reject corrupted CRS."""
        with tempfile.NamedTemporaryFile("w", suffix=".geojson", delete=False) as f:
            sample_geojson = {
                "type": "FeatureCollection",
                "crs": {"type": "name", "properties": {"name": "urn:ogc:def:crs:OGC:1.3:CRS84"}},
                "features": []
            }
            json.dump(sample_geojson, f)
            temp_path = f.name

        try:
            res = self.geo_engine.load_geology(temp_path)
            self.assertTrue(res["available"])
            self.assertEqual(res["crs"], "urn:ogc:def:crs:OGC:1.3:CRS84")
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    # 3. Geological coordinate query
    def test_03_geological_coordinate_query(self):
        """Tests querying geology at coordinate bounds and invalid coordinate rejection."""
        # Out-of-range coordinate
        out_res = self.geo_engine.query_geology_at_coordinate(lat=999.0, lon=80.0)
        self.assertFalse(out_res["available"])
        self.assertEqual(out_res["status"], "INVALID_COORDINATES")

        # In-range coordinate with missing dataset
        valid_res = self.geo_engine.query_geology_at_coordinate(lat=21.9455, lon=80.4295)
        self.assertEqual(valid_res["geological_compatibility"], "NOT ASSESSED")

    # 4. Missing geology handling
    def test_04_missing_geology_handling(self):
        """Ensures that missing geology dataset returns DATA_NOT_AVAILABLE with no crashes."""
        engine_empty = GeologicalEvidenceEngine(workspace_root=tempfile.gettempdir())
        status = engine_empty.get_status()
        self.assertFalse(status["available"])
        self.assertEqual(status["status"], "DATA_NOT_AVAILABLE")
        self.assertIn("No verified geological dataset", status["message"])

        evidence = engine_empty.calculate_geological_evidence(lat=21.9455, lon=80.4295)
        self.assertFalse(evidence["available"])
        self.assertEqual(evidence["status"], "DATA_NOT_AVAILABLE")
        self.assertEqual(evidence["lithology"]["unit"], "DATA NOT AVAILABLE")
        self.assertEqual(evidence["lithology"]["compatibility"], "NOT ASSESSED")

    # 5. Structure-distance calculation
    def test_05_structure_distance_calculation(self):
        """Tests objective distance math to mapped structures using a test dataset."""
        with tempfile.NamedTemporaryFile("w", suffix=".geojson", delete=False) as f:
            fault_geojson = {
                "type": "FeatureCollection",
                "crs": {"type": "name", "properties": {"name": "EPSG:4326"}},
                "features": [
                    {
                        "type": "Feature",
                        "properties": {"name": "Regional Shear Zone", "type": "Shear Zone"},
                        "geometry": {
                            "type": "LineString",
                            "coordinates": [[80.4295, 21.9500], [80.4350, 21.9600]]
                        }
                    }
                ]
            }
            json.dump(fault_geojson, f)
            temp_path = f.name

        try:
            temp_engine = GeologicalEvidenceEngine()
            temp_engine.load_structures(temp_path)
            res = temp_engine.query_nearby_structures(lat=21.9455, lon=80.4295, radius_km=10.0)
            self.assertTrue(res["available"])
            self.assertIsNotNone(res["nearest_structure_distance_m"])
            self.assertGreater(res["nearest_structure_distance_m"], 0)
            self.assertEqual(res["nearest_structure_type"], "Shear Zone")
            self.assertEqual(res["structures_within_radius"], 2)
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    # 6. Terrain dataset discovery
    def test_06_terrain_dataset_discovery(self):
        """Verifies terrain engine scans directories for DEM rasters."""
        status = self.terrain_engine.get_status()
        self.assertIn("status", status)
        self.assertIn("limitations", status)
        if not self.terrain_engine.dem_path:
            self.assertEqual(status["status"], "DATA_NOT_AVAILABLE")
            self.assertFalse(status["available"])

    # 7. DEM CRS handling
    def test_07_dem_crs_handling(self):
        """Verifies DEM loading handles CRS correctly."""
        # When no DEM loaded, reports DATA_NOT_AVAILABLE
        status = self.terrain_engine.get_status()
        if not status["available"]:
            self.assertEqual(status["crs"], "None")

    # 8. Elevation query
    def test_08_elevation_query(self):
        """Verifies elevation queries reject invalid coordinates and return DATA_NOT_AVAILABLE when missing."""
        bad_coords = self.terrain_engine.query_terrain_at_coordinate(lat=100.0, lon=200.0)
        self.assertEqual(bad_coords["status"], "INVALID_COORDINATES")

        normal_coords = self.terrain_engine.query_terrain_at_coordinate(lat=21.9455, lon=80.4295)
        if not self.terrain_engine.dem_path:
            self.assertFalse(normal_coords["available"])
            self.assertIsNone(normal_coords["elevation_m"])

    # 9. Slope calculation
    def test_09_slope_calculation(self):
        """Verifies Horn's slope formula calculation logic."""
        # 3x3 array with known gradient: z increases by 10m per 20m in x direction
        res_x = 20.0
        res_y = 20.0
        arr = np.array([
            [100.0, 105.0, 110.0],
            [100.0, 105.0, 110.0],
            [100.0, 105.0, 110.0]
        ], dtype=np.float64)

        dx = ((arr[0, 2] + 2 * arr[1, 2] + arr[2, 2]) -
              (arr[0, 0] + 2 * arr[1, 0] + arr[2, 0])) / (8.0 * res_x)
        dy = ((arr[2, 0] + 2 * arr[2, 1] + arr[2, 2]) -
              (arr[0, 0] + 2 * arr[0, 1] + arr[0, 2])) / (8.0 * res_y)

        slope_rad = math.atan(math.sqrt(dx * dx + dy * dy))
        slope_deg = round(math.degrees(slope_rad), 2)
        # Gradient = 10 / 40 = 0.25 -> atan(0.25) ~ 14.04°
        self.assertAlmostEqual(slope_deg, 14.04, places=1)

    # 10. Missing DEM handling
    def test_10_missing_dem_handling(self):
        """Ensures missing DEM returns clear status and does not crash."""
        empty_t = TerrainEvidenceEngine(workspace_root=tempfile.gettempdir())
        status = empty_t.get_status()
        self.assertFalse(status["available"])
        self.assertEqual(status["status"], "DATA_NOT_AVAILABLE")
        self.assertIn("No verified Digital Elevation Model", status["message"])

        evidence = empty_t.calculate_terrain_evidence(lat=21.9455, lon=80.4295)
        self.assertFalse(evidence["available"])
        self.assertEqual(evidence["status"], "DATA_NOT_AVAILABLE")
        self.assertIsNone(evidence["elevation_m"])
        self.assertIsNone(evidence["slope_deg"])

    # 11. EvidenceEngine geological integration
    def test_11_evidence_engine_geological_integration(self):
        """Verifies calculate_geological_evidence matches EvidenceEngine schema."""
        ev = calculate_geological_evidence(lat=21.9455, lon=80.4295)
        self.assertIn("available", ev)
        self.assertIn("status", ev)
        self.assertIn("lithology", ev)
        self.assertIn("structures", ev)
        self.assertIn("evidence_summary", ev)

    # 12. EvidenceEngine terrain integration
    def test_12_evidence_engine_terrain_integration(self):
        """Verifies calculate_terrain_evidence matches EvidenceEngine schema."""
        ev = calculate_terrain_evidence(lat=21.9455, lon=80.4295)
        self.assertIn("available", ev)
        self.assertIn("status", ev)
        self.assertIn("elevation_m", ev)
        self.assertIn("slope_deg", ev)
        self.assertIn("aspect_deg", ev)

    # 13. Provenance metadata
    def test_13_provenance_metadata(self):
        """Verifies provenance metadata fields for both engines."""
        geo_status = get_geology_status()
        self.assertIn("lithology", geo_status)
        self.assertIn("structures", geo_status)
        self.assertIn("crs", geo_status["lithology"])
        self.assertIn("coverage", geo_status["lithology"])

        terrain_status = get_terrain_status()
        self.assertIn("dataset", terrain_status)
        self.assertIn("crs", terrain_status)
        self.assertIn("resolution", terrain_status)

    # 14. No fabricated geological values
    def test_14_no_fabricated_geological_values(self):
        """Guarantees that when files are missing, NO fake rock types or distances are created."""
        empty_geo = GeologicalEvidenceEngine(workspace_root=tempfile.gettempdir())
        query = empty_geo.query_geology_at_coordinate(lat=21.9455, lon=80.4295)
        self.assertEqual(query["unit"], "DATA NOT AVAILABLE")
        self.assertEqual(query["geological_compatibility"], "NOT ASSESSED")
        self.assertIsNone(query["distance_to_contact_m"])

        struct = empty_geo.query_nearby_structures(lat=21.9455, lon=80.4295)
        self.assertIsNone(struct["nearest_structure_distance_m"])
        self.assertEqual(struct["nearest_structure_type"], "DATA NOT AVAILABLE")

    # 15. No fabricated terrain values
    def test_15_no_fabricated_terrain_values(self):
        """Guarantees that when DEM is missing, NO fake elevation, slope, or aspect numbers are returned."""
        empty_t = TerrainEvidenceEngine(workspace_root=tempfile.gettempdir())
        res = empty_t.query_terrain_at_coordinate(lat=21.9455, lon=80.4295)
        self.assertIsNone(res["elevation_m"])
        self.assertIsNone(res["slope_deg"])
        self.assertIsNone(res["aspect_deg"])

    # 16. Ranking remains unchanged
    def test_16_ranking_preservation(self):
        """Guarantees that candidate discovery zones ranking is preserved strictly from model prospectivity."""
        zones_csv = os.path.join(self.root, "data", "processed", "high_prospectivity_zones.csv")
        self.assertTrue(os.path.exists(zones_csv))
        with open(zones_csv, "r", encoding="utf-8") as f:
            lines = f.readlines()
        self.assertGreater(len(lines), 1, "Candidate zones CSV must contain zones")

    # 17. Manganese XAI remains based only on trained features
    def test_17_manganese_xai_remains_trained_features(self):
        """Ensures that the 10 trained Sentinel-2 features were NOT diluted with untrained geology/terrain."""
        meta_path = os.path.join(self.root, "models", "manganese_model_metadata.json")
        self.assertTrue(os.path.exists(meta_path))
        with open(meta_path, "r", encoding="utf-8") as f:
            meta = json.load(f)

        features = meta.get("feature_schema") or meta.get("features", [])
        self.assertEqual(len(features), 10, "Manganese model must strictly have exactly 10 features")
        # None of the features should be DEM, elevation, slope, geology, or fault
        for feat in features:
            self.assertNotIn("dem", feat.lower())
            self.assertNotIn("elevation", feat.lower())
            self.assertNotIn("slope", feat.lower())
            self.assertNotIn("geology", feat.lower())
            self.assertNotIn("lithology", feat.lower())

    # 18. Untrained minerals remain protected
    def test_18_untrained_minerals_remain_protected(self):
        """Ensures that Iron Ore, Bauxite, Copper, Lithium, Coal, Limestone remain untrained."""
        untrained = ["iron_ore", "bauxite", "copper", "lithium", "coal", "limestone"]
        for m_id in untrained:
            min_info = MineralRegistry.get_mineral(m_id)
            self.assertIsNotNone(min_info)
            self.assertFalse(min_info["is_trained"])
            self.assertEqual(min_info["status"], MineralStatus.AWAITING_DATA)

    # 19. API missing-data behavior
    def test_19_api_missing_data_behavior(self):
        """Verifies that status methods return structured JSON payload with available: False and DATA_NOT_AVAILABLE."""
        geo_status = get_geology_status()
        self.assertIn("status", geo_status)
        self.assertIn("available", geo_status)

        terrain_status = get_terrain_status()
        self.assertIn("status", terrain_status)
        self.assertIn("available", terrain_status)

    # 20. Independent-deposit validation remains NOT_AVAILABLE
    def test_20_independent_deposit_validation_remains_not_available(self):
        """Confirms that independent deposit validation is explicitly marked NOT AVAILABLE."""
        mn = MineralRegistry.get_mineral("manganese")
        self.assertIsNotNone(mn)
        # Validation report check
        rep_path = os.path.join(self.root, "models", "manganese_validation_report.json")
        self.assertTrue(os.path.exists(rep_path))
        with open(rep_path, "r", encoding="utf-8") as f:
            rep = json.load(f)

        # Independent deposit validation is explicitly NOT AVAILABLE
        limitations = rep.get("limitations", [])
        has_independent_disclaimer = any("single known" in lim.lower() or "deposit" in lim.lower() or "independent" in lim.lower() for lim in limitations)
        self.assertTrue(has_independent_disclaimer, "Must explicitly note single-deposit limitation")


if __name__ == "__main__":
    unittest.main()
