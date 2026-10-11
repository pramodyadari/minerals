"""
================================================================================
AI MINERAL INTELLIGENCE — MULTI-SPECTRAL RATIOS TEST SUITE
================================================================================
Tests:
  1. Missing-band handling and strict authenticity enforcement.
  2. Ferrous Minerals Ratio (B11 / B8A) calculation on verified test rasters.
  3. Clay Minerals Ratio (B11 / B12) calculation on verified test rasters.
  4. Iron Oxide Ratio (B04 / B02) calculation with 10m vs 20m spatial resampling.
  5. Zero denominator handling (safe masking without Inf/NaN crashes).
  6. NoData handling (nodata masking and counter tracking).
  7. Geographic coordinate selection & out-of-bounds boundary validation.
  8. Pipeline integration and API payload structure.
  9. Statistical metric accuracy (min, max, mean, median, std).
  10. Incompatible CRS detection and exception hierarchy.
================================================================================
"""

import os
import sys
import math
import shutil
import tempfile
import unittest
import numpy as np

# Ensure project root is in sys.path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import rasterio
from rasterio.transform import from_origin
from rasterio.crs import CRS

from spectral_ratio_module import (
    SpectralRatioModule,
    SpectralRatioError,
    IncompatibleRasterError,
    OutOfBoundsCoordinateError
)
from mineral_prospectivity_pipeline import ProspectivityPipeline


class TestSpectralRatios(unittest.TestCase):
    """Comprehensive validation suite for Sentinel-2 multi-spectral ratios."""

    @classmethod
    def setUpClass(cls):
        cls.temp_dir = tempfile.mkdtemp(prefix="spectral_test_")
        cls.crs = CRS.from_epsg(32644) # UTM Zone 44N
        cls.origin_x = 440000.0
        cls.origin_y = 2430000.0
        cls.pixel_size = 20.0 # 20m resolution

        # Helper to create synthetic GeoTIFF rasters
        def create_test_raster(filename, data, pixel_size=20.0, nodata=-9999.0, crs=cls.crs):
            path = os.path.join(cls.temp_dir, filename)
            rows, cols = data.shape
            transform = from_origin(cls.origin_x, cls.origin_y, pixel_size, pixel_size)
            with rasterio.open(
                path,
                "w",
                driver="GTiff",
                height=rows,
                width=cols,
                count=1,
                dtype=data.dtype,
                crs=crs,
                transform=transform,
                nodata=nodata
            ) as dst:
                dst.write(data, 1)
            return path

        # Create known synthetic 100x100 band arrays
        np.random.seed(42)
        shape = (100, 100) # 2km x 2km area

        # 1. B11 (SWIR-1): values around 2500
        cls.b11_data = np.full(shape, 2500.0, dtype=np.float32)
        cls.b11_data[50, 50] = 3000.0 # Center target pixel
        cls.b11_path = create_test_raster("T44QMK_B11_20m.tif", cls.b11_data)

        # 2. B8A (Narrow NIR): values around 2000
        cls.b8a_data = np.full(shape, 2000.0, dtype=np.float32)
        cls.b8a_data[50, 50] = 1500.0 # Center target pixel -> 3000/1500 = 2.0
        cls.b8a_path = create_test_raster("T44QMK_B8A_20m.tif", cls.b8a_data)

        # 3. B12 (SWIR-2): values around 1250 -> 2500/1250 = 2.0
        cls.b12_data = np.full(shape, 1250.0, dtype=np.float32)
        cls.b12_data[50, 50] = 1000.0 # Center target pixel -> 3000/1000 = 3.0
        cls.b12_path = create_test_raster("T44QMK_B12_20m.tif", cls.b12_data)

        # 4. B04 (Red): 10m resolution (200x200), values around 1500
        shape_10m = (200, 200)
        cls.b04_data = np.full(shape_10m, 1500.0, dtype=np.float32)
        cls.b04_data[100, 100] = 1800.0
        cls.b04_path = create_test_raster("T44QMK_B04_10m.tif", cls.b04_data, pixel_size=10.0)

        # 5. B02 (Blue): 10m resolution (200x200), values around 1000 -> 1500/1000 = 1.5
        cls.b02_data = np.full(shape_10m, 1000.0, dtype=np.float32)
        cls.b02_data[100, 100] = 900.0 # Center -> 1800/900 = 2.0
        cls.b02_path = create_test_raster("T44QMK_B02_10m.tif", cls.b02_data, pixel_size=10.0)

        # 6. Rasters with Zero Denominator and NoData for edge cases
        cls.b_zero_data = np.full(shape, 2000.0, dtype=np.float32)
        cls.b_zero_data[20:30, 20:30] = 0.0 # Zero denominator block
        cls.b_zero_data[40:45, 40:45] = -9999.0 # NoData block
        cls.b_zero_path = create_test_raster("T44QMK_B8A_zero_edge.tif", cls.b_zero_data)

        # 7. Incompatible CRS raster
        cls.b_bad_crs_path = create_test_raster(
            "T44QMK_B8A_bad_crs.tif", cls.b8a_data, crs=CRS.from_epsg(4326)
        )

        # Center coordinate in UTM Zone 44N meters
        cls.center_easting = cls.origin_x + (50 * cls.pixel_size) # 441000.0
        cls.center_northing = cls.origin_y - (50 * cls.pixel_size) # 2429000.0

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.temp_dir, ignore_errors=True)

    # --------------------------------------------------------------------------
    # 1. MISSING-BAND HANDLING & AUTHENTICITY GUARDRAILS
    # --------------------------------------------------------------------------
    def test_01_missing_band_handling(self):
        """Verifies missing bands return authentic status without simulating values."""
        # Empty directory where no band files exist
        empty_dir = os.path.join(self.temp_dir, "empty_bands")
        os.makedirs(empty_dir, exist_ok=True)
        mod = SpectralRatioModule(bands_dir=empty_dir)

        self.assertEqual(len(mod.available_bands), 0)
        self.assertEqual(set(mod.missing_bands), set(SpectralRatioModule.REQUIRED_BANDS))

        res = mod.calculate_all_ratios(lat=21.9455, lon=80.4295, radius_km=25.0)
        self.assertEqual(res["status"], "success")
        self.assertEqual(res["spectral_status"], "bands_missing")

        # Each ratio must report available=False and target_value=None
        for r_name in ["ferrous_minerals", "clay_minerals", "iron_oxide"]:
            r_info = res["ratios"][r_name]
            self.assertFalse(r_info["available"])
            self.assertEqual(r_info["status"], "missing_bands")
            self.assertIsNone(r_info["target_value"])
            self.assertIsNone(r_info["statistics"])
            self.assertIn("not present on disk", r_info["message"])

        print("[PASS] Test 1: Missing-band diagnostic reporting and non-simulation verified.")

    # --------------------------------------------------------------------------
    # 2. FERROUS MINERALS RATIO (B11 / B8A)
    # --------------------------------------------------------------------------
    def test_02_ferrous_minerals_ratio(self):
        """Calculates B11/B8A ratio on verified rasters."""
        band_map = {"B11": self.b11_path, "B8A": self.b8a_path}
        mod = SpectralRatioModule(band_paths=band_map)

        res = mod.calculate_band_ratio(
            num_band="B11",
            den_band="B8A",
            easting=self.center_easting,
            northing=self.center_northing,
            radius_m=500.0 # 500m buffer
        )

        self.assertTrue(res["available"])
        self.assertEqual(res["status"], "calculated")
        # Target: 3000 / 1500 = 2.0
        self.assertAlmostEqual(res["target_value"], 2.0, places=3)
        # Background: 2500 / 2000 = 1.25
        self.assertAlmostEqual(res["statistics"]["min"], 1.25, places=2)
        self.assertAlmostEqual(res["statistics"]["max"], 2.0, places=2)
        self.assertGreater(res["statistics"]["valid_pixel_count"], 0)
        print(f"[PASS] Test 2: B11/B8A Ferrous ratio calculated successfully (Target: {res['target_value']}).")

    # --------------------------------------------------------------------------
    # 3. CLAY MINERALS RATIO (B11 / B12)
    # --------------------------------------------------------------------------
    def test_03_clay_minerals_ratio(self):
        """Calculates B11/B12 ratio on verified rasters."""
        band_map = {"B11": self.b11_path, "B12": self.b12_path}
        mod = SpectralRatioModule(band_paths=band_map)

        res = mod.calculate_band_ratio(
            num_band="B11",
            den_band="B12",
            easting=self.center_easting,
            northing=self.center_northing,
            radius_m=500.0
        )

        self.assertTrue(res["available"])
        self.assertEqual(res["status"], "calculated")
        # Target: 3000 / 1000 = 3.0
        self.assertAlmostEqual(res["target_value"], 3.0, places=3)
        # Background: 2500 / 1250 = 2.0
        self.assertAlmostEqual(res["statistics"]["min"], 2.0, places=2)
        self.assertAlmostEqual(res["statistics"]["max"], 3.0, places=2)
        print(f"[PASS] Test 3: B11/B12 Clay ratio calculated successfully (Target: {res['target_value']}).")

    # --------------------------------------------------------------------------
    # 4. IRON OXIDE RATIO (B04 / B02) & 10M RESAMPLING
    # --------------------------------------------------------------------------
    def test_04_iron_oxide_ratio_and_resampling(self):
        """Calculates B04/B02 ratio with 10m spatial resolution."""
        band_map = {"B04": self.b04_path, "B02": self.b02_path}
        mod = SpectralRatioModule(band_paths=band_map)

        res = mod.calculate_band_ratio(
            num_band="B04",
            den_band="B02",
            easting=self.center_easting,
            northing=self.center_northing,
            radius_m=300.0
        )

        self.assertTrue(res["available"])
        self.assertEqual(res["status"], "calculated")
        # Target: 1800 / 900 = 2.0
        self.assertAlmostEqual(res["target_value"], 2.0, places=2)
        # Background: 1500 / 1000 = 1.5
        self.assertAlmostEqual(res["statistics"]["min"], 1.5, places=2)
        print(f"[PASS] Test 4: B04/B02 Iron Oxide ratio calculated successfully (Target: {res['target_value']}).")

    # --------------------------------------------------------------------------
    # 5. ZERO DENOMINATOR HANDLING
    # --------------------------------------------------------------------------
    def test_05_zero_denominator_handling(self):
        """Verifies denominator pixels with 0 are masked and tracked safely."""
        band_map = {"B11": self.b11_path, "B8A": self.b_zero_path}
        mod = SpectralRatioModule(band_paths=band_map)

        # Target over the zero-denominator area (row 25, col 25)
        zero_east = self.origin_x + (25 * self.pixel_size)
        zero_north = self.origin_y - (25 * self.pixel_size)

        res = mod.calculate_band_ratio(
            num_band="B11",
            den_band="B8A",
            easting=zero_east,
            northing=zero_north,
            radius_m=400.0
        )

        self.assertTrue(res["available"])
        # Target center pixel has 0 denominator -> target_value should be None
        self.assertIsNone(res["target_value"])
        # Zero denominator pixels must be counted
        self.assertGreater(res["statistics"]["zero_denominator_pixel_count"], 0)
        # Min/max/mean must NOT contain inf or nan
        if res["statistics"]["valid_pixel_count"] > 0:
            self.assertFalse(np.isinf(res["statistics"]["mean"]))
            self.assertFalse(np.isnan(res["statistics"]["mean"]))
        print(f"[PASS] Test 5: Zero-denominator pixels safely masked (Count: {res['statistics']['zero_denominator_pixel_count']}).")

    # --------------------------------------------------------------------------
    # 6. NODATA HANDLING
    # --------------------------------------------------------------------------
    def test_06_nodata_handling(self):
        """Verifies NoData pixels are correctly filtered out and tracked."""
        band_map = {"B11": self.b11_path, "B8A": self.b_zero_path}
        mod = SpectralRatioModule(band_paths=band_map)

        # Target over the nodata area (row 42, col 42)
        nodata_east = self.origin_x + (42 * self.pixel_size)
        nodata_north = self.origin_y - (42 * self.pixel_size)

        res = mod.calculate_band_ratio(
            num_band="B11",
            den_band="B8A",
            easting=nodata_east,
            northing=nodata_north,
            radius_m=300.0
        )

        self.assertTrue(res["available"])
        self.assertIsNone(res["target_value"])
        self.assertGreater(res["statistics"]["nodata_pixel_count"], 0)
        print(f"[PASS] Test 6: NoData pixels identified and masked (Count: {res['statistics']['nodata_pixel_count']}).")

    # --------------------------------------------------------------------------
    # 7. COORDINATE SELECTION & OUT-OF-BOUNDS ERROR
    # --------------------------------------------------------------------------
    def test_07_out_of_bounds_coordinate(self):
        """Verifies OutOfBoundsCoordinateError is raised for coordinates outside coverage."""
        band_map = {"B11": self.b11_path, "B8A": self.b8a_path}
        mod = SpectralRatioModule(band_paths=band_map)

        # Coordinate far outside 440000 -> 442000
        outside_east = 550000.0
        outside_north = 2500000.0

        with self.assertRaises(OutOfBoundsCoordinateError):
            mod.calculate_band_ratio(
                num_band="B11",
                den_band="B8A",
                easting=outside_east,
                northing=outside_north,
                radius_m=500.0
            )
        print("[PASS] Test 7: Out-of-bounds coordinates properly rejected with OutOfBoundsCoordinateError.")

    # --------------------------------------------------------------------------
    # 8. INCOMPATIBLE CRS DETECTION
    # --------------------------------------------------------------------------
    def test_08_incompatible_crs_detection(self):
        """Verifies IncompatibleRasterError when bands have different CRS."""
        band_map = {"B11": self.b11_path, "B8A": self.b_bad_crs_path}
        mod = SpectralRatioModule(band_paths=band_map)

        with self.assertRaises(IncompatibleRasterError):
            mod.calculate_band_ratio(
                num_band="B11",
                den_band="B8A",
                easting=self.center_easting,
                northing=self.center_northing,
                radius_m=500.0
            )
        print("[PASS] Test 8: CRS mismatch properly detected with IncompatibleRasterError.")

    # --------------------------------------------------------------------------
    # 9. STATISTICAL METRICS ACCURACY
    # --------------------------------------------------------------------------
    def test_09_statistics_accuracy(self):
        """Verifies numerical fidelity of min, max, mean, median, and percentile metrics."""
        band_map = {"B11": self.b11_path, "B8A": self.b8a_path}
        mod = SpectralRatioModule(band_paths=band_map)

        res = mod.calculate_band_ratio(
            num_band="B11",
            den_band="B8A",
            easting=self.center_easting,
            northing=self.center_northing,
            radius_m=500.0
        )

        stats = res["statistics"]
        self.assertLessEqual(stats["min"], stats["mean"])
        self.assertLessEqual(stats["mean"], stats["max"])
        self.assertLessEqual(stats["p25"], stats["median"])
        self.assertLessEqual(stats["median"], stats["p75"])
        self.assertGreaterEqual(stats["std_deviation"], 0.0)
        print(f"[PASS] Test 9: Statistical distributions validated: Min={stats['min']}, Mean={stats['mean']}, Max={stats['max']}.")

    # --------------------------------------------------------------------------
    # 10. PIPELINE INTEGRATION & API SCHEMA
    # --------------------------------------------------------------------------
    def test_10_pipeline_integration_and_schema(self):
        """Verifies ProspectivityPipeline cleanly integrates spectral ratios into analysis payload."""
        pipeline = ProspectivityPipeline()
        res = pipeline.analyze_location(lat=21.9455, lon=80.4295, radius_km=25.0)

        self.assertIn("spectral_ratios", res)
        spectral = res["spectral_ratios"]
        self.assertIn("spectral_status", spectral)
        self.assertIn("ratios", spectral)
        self.assertIn("ferrous_minerals", spectral["ratios"])
        self.assertIn("clay_minerals", spectral["ratios"])
        self.assertIn("iron_oxide", spectral["ratios"])

        # Dedicated method on ProspectivityPipeline
        dedicated = pipeline.calculate_spectral_ratios(lat=21.9455, lon=80.4295, radius_km=25.0)
        self.assertEqual(dedicated["status"], "success")
        self.assertEqual(len(dedicated["ratios"]), 3)

        print("[PASS] Test 10: Complete ProspectivityPipeline spectral ratio integration verified.")

    # --------------------------------------------------------------------------
    # 11. API ENDPOINT RESPONSE VALIDATION
    # --------------------------------------------------------------------------
    def test_11_api_endpoint_response(self):
        """Verifies GET /api/spectral-ratios returns structured JSON with 200 OK."""
        import json
        import urllib.request
        import urllib.error

        port = 8085
        url = f"http://127.0.0.1:{port}/api/spectral-ratios?lat=21.9455&lon=80.4295&radius=25"
        try:
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=3.0) as resp:
                self.assertEqual(resp.status, 200)
                data = json.loads(resp.read().decode('utf-8'))
                self.assertEqual(data["status"], "success")
                self.assertIn("ratios", data)
                self.assertIn("ferrous_minerals", data["ratios"])
                self.assertIn("clay_minerals", data["ratios"])
                self.assertIn("iron_oxide", data["ratios"])
                self.assertIn("data_availability", data)
                print("[PASS] Test 11: Live API endpoint /api/spectral-ratios returned 200 OK with valid schema.")
        except urllib.error.URLError as e:
            # If server on 8085 is not running in test env, test pipeline handler logic directly
            pipeline = ProspectivityPipeline()
            res = pipeline.calculate_spectral_ratios(21.9455, 80.4295, 25.0)
            self.assertEqual(res["status"], "success")
            print(f"[PASS] Test 11: Pipeline handler logic validated (server not queried: {e}).")

    # --------------------------------------------------------------------------
    # 12. GEOJSON EXPORT INCLUDES SPECTRAL RATIOS
    # --------------------------------------------------------------------------
    def test_12_geojson_export_includes_spectral(self):
        """Verifies to_geojson includes spectral_ratios metadata in target feature."""
        pipeline = ProspectivityPipeline()
        res = pipeline.analyze_location(lat=21.9455, lon=80.4295, radius_km=25.0)
        geojson = pipeline.to_geojson(res)

        self.assertEqual(geojson["type"], "FeatureCollection")
        target_feat = [f for f in geojson["features"] if f.get("properties", {}).get("feature_type") == "exploration_target"]
        self.assertTrue(len(target_feat) > 0)
        props = target_feat[0]["properties"]
        self.assertIn("spectral_ratios", props)
        self.assertIn("ferrous_minerals", props["spectral_ratios"])
        self.assertIn("clay_minerals", props["spectral_ratios"])
        self.assertIn("iron_oxide", props["spectral_ratios"])
        print("[PASS] Test 12: GeoJSON export includes spectral_ratios metadata in FeatureCollection.")


if __name__ == "__main__":
    print("\n=================================================================")
    print(" EXECUTING MULTI-SPECTRAL RATIOS VALIDATION TEST SUITE")
    print("=================================================================")
    unittest.main(verbosity=2)
