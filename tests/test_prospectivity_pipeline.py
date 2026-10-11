"""
================================================================================
AI MINERAL EXPLORATION — PROSPECTIVITY PIPELINE COMPREHENSIVE TEST SUITE
================================================================================
Validates all 10 core requirements:
  1. Valid coordinates
  2. Invalid coordinates
  3. Out-of-bounds coordinates
  4. NoData pixel handling
  5. Raster bounds and spatial metadata
  6. Coordinate transformation (WGS84 <-> UTM Zone 44N)
  7. Window extraction & radial mask buffer
  8. Prospectivity score calculation & statistics
  9. Mineral potential classification bands
  10. Pipeline API / Script JSON output and candidate zones ranking
================================================================================
"""

import os
import sys
import math
import json
import subprocess
import unittest
import numpy as np

# Ensure project root is in sys.path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from mineral_prospectivity_pipeline import (
    ProspectivityPipeline,
    PipelineError,
    RasterNotFoundError,
    InvalidCoordinateError,
    CRSMismatchError,
    OutOfBoundsError,
    NoDataError,
    analyze_location
)


class TestMineralProspectivityPipeline(unittest.TestCase):
    """Authoritative test suite for Sentinel-2 Manganese Prospectivity Pipeline."""

    @classmethod
    def setUpClass(cls):
        cls.tif_path = os.path.join(PROJECT_ROOT, "outputs", "manganese_prospectivity.tif")
        cls.pipeline = ProspectivityPipeline(cls.tif_path)
        cls.ghondi_lat = 21.9455
        cls.ghondi_lon = 80.4295
        cls.ghondi_easting = 441089.328
        cls.ghondi_northing = 2426904.204

    # --------------------------------------------------------------------------
    # 1. RASTER BOUNDS & METADATA
    # --------------------------------------------------------------------------
    def test_01_raster_bounds_and_metadata(self):
        """Verifies raster existence, CRS EPSG:32644, 20m resolution, and tile bounds."""
        meta = self.pipeline.validate_raster()
        self.assertTrue(meta["valid"])
        self.assertEqual(meta["width"], 5490)
        self.assertEqual(meta["height"], 5490)
        self.assertEqual(meta["count"], 1)
        self.assertIn("32644", meta["crs"])
        self.assertEqual(meta["bounds"]["left"], 399960.0)
        self.assertEqual(meta["bounds"]["right"], 509760.0)
        self.assertEqual(meta["bounds"]["bottom"], 2390220.0)
        self.assertEqual(meta["bounds"]["top"], 2500020.0)
        self.assertEqual(meta["pixel_size_x"], 20.0)
        self.assertEqual(meta["pixel_size_y"], 20.0)
        print("\n[PASS] Test 1: Raster bounds and metadata verified successfully.")

    # --------------------------------------------------------------------------
    # 2. COORDINATE TRANSFORMATION
    # --------------------------------------------------------------------------
    def test_02_coordinate_transformation(self):
        """Tests forward WGS84 -> UTM 44N and reverse UTM 44N -> WGS84 transforms."""
        # Forward
        lat, lon, easting, northing = self.pipeline.parse_and_transform_coordinates(
            lat=self.ghondi_lat, lon=self.ghondi_lon
        )
        self.assertAlmostEqual(easting, self.ghondi_easting, delta=1.0)
        self.assertAlmostEqual(northing, self.ghondi_northing, delta=1.0)

        # Reverse
        rev_lat, rev_lon, rev_east, rev_north = self.pipeline.parse_and_transform_coordinates(
            easting=self.ghondi_easting, northing=self.ghondi_northing
        )
        self.assertAlmostEqual(rev_lat, self.ghondi_lat, delta=0.0001)
        self.assertAlmostEqual(rev_lon, self.ghondi_lon, delta=0.0001)
        print("[PASS] Test 2: Sub-meter coordinate transformation verified.")

    # --------------------------------------------------------------------------
    # 3. VALID COORDINATES ANALYSIS
    # --------------------------------------------------------------------------
    def test_03_valid_coordinates_analysis(self):
        """Tests analysis of valid coordinates at known Ghondi mine pixel."""
        res = self.pipeline.analyze_location(lat=self.ghondi_lat, lon=self.ghondi_lon, radius_km=25.0)
        self.assertEqual(res["status"], "success")
        self.assertEqual(res["target"]["raster_row"], 3655)
        self.assertEqual(res["target"]["raster_col"], 2056)
        
        # Mine pixel is known to have model score ~0.71 (71.0%)
        prosp = res["prospectivity"]
        self.assertAlmostEqual(prosp["score"], 0.71, delta=0.01)
        self.assertEqual(prosp["classification"], "Moderate")
        print(f"[PASS] Test 3: Valid coordinates analysis returned pixel value {prosp['score']} ({prosp['percent']}%).")

    # --------------------------------------------------------------------------
    # 4. INVALID COORDINATES
    # --------------------------------------------------------------------------
    def test_04_invalid_coordinates(self):
        """Tests that mathematically out-of-range or non-numeric coordinates raise InvalidCoordinateError."""
        # Non-numeric
        with self.assertRaises(InvalidCoordinateError):
            self.pipeline.parse_and_transform_coordinates(lat="invalid", lon=80.0)

        # Latitude out of range
        with self.assertRaises(InvalidCoordinateError):
            self.pipeline.parse_and_transform_coordinates(lat=95.0, lon=80.0)

        with self.assertRaises(InvalidCoordinateError):
            self.pipeline.parse_and_transform_coordinates(lat=-95.0, lon=80.0)

        # Longitude out of range
        with self.assertRaises(InvalidCoordinateError):
            self.pipeline.parse_and_transform_coordinates(lat=21.0, lon=195.0)

        # No coords supplied
        with self.assertRaises(InvalidCoordinateError):
            self.pipeline.parse_and_transform_coordinates()

        print("[PASS] Test 4: Invalid coordinates properly rejected with InvalidCoordinateError.")

    # --------------------------------------------------------------------------
    # 5. OUT-OF-BOUNDS COORDINATES
    # --------------------------------------------------------------------------
    def test_05_out_of_bounds_coordinates(self):
        """Tests that coordinates outside Sentinel-2 tile footprint raise OutOfBoundsError."""
        # Location in Arabian Sea / Mumbai area (far outside tile)
        with self.assertRaises(OutOfBoundsError):
            self.pipeline.analyze_location(lat=18.9, lon=72.8, radius_km=25.0)

        # Coordinates slightly west of tile left boundary (easting < 399960)
        with self.assertRaises(OutOfBoundsError):
            self.pipeline.analyze_location(easting=350000.0, northing=2426904.0, radius_km=25.0)

        print("[PASS] Test 5: Out-of-bounds coordinates properly rejected with OutOfBoundsError.")

    # --------------------------------------------------------------------------
    # 6. NODATA & MASKING BEHAVIOR
    # --------------------------------------------------------------------------
    def test_06_nodata_and_missing_raster(self):
        """Tests behavior with missing GeoTIFF file and NoData checking."""
        # Missing raster
        bad_pipeline = ProspectivityPipeline("nonexistent_mineral_file.tif")
        with self.assertRaises(RasterNotFoundError):
            bad_pipeline.validate_raster()

        # Classification of None / NaN
        self.assertEqual(ProspectivityPipeline.classify_prospectivity(None), "No Data")
        self.assertEqual(ProspectivityPipeline.classify_prospectivity(float("nan")), "No Data")

        print("[PASS] Test 6: Missing file and NoData exceptions validated.")

    # --------------------------------------------------------------------------
    # 7. WINDOW EXTRACTION & RADIAL BUFFER
    # --------------------------------------------------------------------------
    def test_07_window_extraction(self):
        """Tests configurable surrounding radius extraction (10km, 25km)."""
        res_10k = self.pipeline.analyze_location(lat=self.ghondi_lat, lon=self.ghondi_lon, radius_km=10.0)
        res_25k = self.pipeline.analyze_location(lat=self.ghondi_lat, lon=self.ghondi_lon, radius_km=25.0)

        # Pixel counts should scale approximately with radius squared
        count_10k = res_10k["radial_analysis"]["sampled_pixels"]
        count_25k = res_25k["radial_analysis"]["sampled_pixels"]

        # pi * (10000/20)^2 = ~785,398 pixels
        # pi * (25000/20)^2 = ~4,908,738 pixels
        self.assertTrue(700000 < count_10k < 850000)
        self.assertTrue(4500000 < count_25k < 5200000)
        self.assertGreater(count_25k, count_10k)
        print(f"[PASS] Test 7: Window extraction verified: 10km={count_10k:,} px, 25km={count_25k:,} px.")

    # --------------------------------------------------------------------------
    # 8. STATISTICAL CALCULATIONS
    # --------------------------------------------------------------------------
    def test_08_prospectivity_statistics(self):
        """Validates minimum, maximum, mean, std, median, and high-potential hectare calculations."""
        res = self.pipeline.analyze_location(lat=self.ghondi_lat, lon=self.ghondi_lon, radius_km=25.0)
        rad = res["radial_analysis"]

        self.assertGreaterEqual(rad["max_percent"], rad["mean_percent"])
        self.assertGreaterEqual(rad["mean_percent"], rad["min_percent"])
        self.assertGreaterEqual(rad["min_percent"], 0.0)
        self.assertLessEqual(rad["max_percent"], 100.0)
        self.assertGreater(rad["high_potential_pixels"], 0)
        self.assertGreater(rad["high_potential_hectares"], 0.0)
        print(f"[PASS] Test 8: Statistics verified: Min={rad['min_percent']}%, Mean={rad['mean_percent']}%, Max={rad['max_percent']}%.")

    # --------------------------------------------------------------------------
    # 9. CLASSIFICATION BANDS
    # --------------------------------------------------------------------------
    def test_09_classification_bands(self):
        """Verifies standard scientific classification band mappings."""
        classify = ProspectivityPipeline.classify_prospectivity
        
        self.assertEqual(classify(0.95), "Very High")
        self.assertEqual(classify(95.0), "Very High")
        self.assertEqual(classify(0.90), "Very High")
        
        self.assertEqual(classify(0.85), "High")
        self.assertEqual(classify(75.0), "High")
        
        self.assertEqual(classify(0.65), "Moderate")
        self.assertEqual(classify(50.0), "Moderate")
        
        self.assertEqual(classify(0.35), "Low")
        self.assertEqual(classify(25.0), "Low")
        
        self.assertEqual(classify(0.15), "Very Low")
        self.assertEqual(classify(5.0), "Very Low")
        print("[PASS] Test 9: All 5 prospectivity classification bands mapped correctly.")

    # --------------------------------------------------------------------------
    # 10. CANDIDATE ZONES & CLI OUTPUT
    # --------------------------------------------------------------------------
    def test_10_candidate_zones_and_cli_output(self):
        """Verifies candidate zones proximity search and CLI JSON output execution."""
        # 1. Proximity search
        res = self.pipeline.analyze_location(lat=self.ghondi_lat, lon=self.ghondi_lon, radius_km=25.0)
        zones = res["candidate_zones_in_radius"]
        self.assertEqual(res["nearby_zones_count"], len(zones))
        self.assertGreaterEqual(len(zones), 1)
        
        # Verify nearest zone is sorted by distance ascending
        for i in range(len(zones) - 1):
            self.assertLessEqual(zones[i]["distance_km"], zones[i + 1]["distance_km"])

        # 2. CLI Invocation with JSON flag
        python_exe = sys.executable
        cli_script = os.path.join(PROJECT_ROOT, "mineral_prospectivity_pipeline.py")
        cmd = [python_exe, cli_script, "--lat", str(self.ghondi_lat), "--lon", str(self.ghondi_lon), "--radius", "25", "--json"]
        
        proc = subprocess.run(cmd, capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0)
        cli_data = json.loads(proc.stdout)
        self.assertEqual(cli_data["status"], "success")
        self.assertAlmostEqual(cli_data["prospectivity"]["score"], 0.71, delta=0.01)

        print("[PASS] Test 10: Candidate zones ranking and CLI JSON execution verified.")

    # --------------------------------------------------------------------------
    # 11. GEOJSON EXPORT & SPATIAL VALIDITY
    # --------------------------------------------------------------------------
    def test_11_geojson_export(self):
        """Verifies industry-standard GIS GeoJSON FeatureCollection generation."""
        res = self.pipeline.analyze_location(lat=self.ghondi_lat, lon=self.ghondi_lon, radius_km=25.0)
        geojson = self.pipeline.to_geojson(res)

        self.assertEqual(geojson["type"], "FeatureCollection")
        self.assertIn("features", geojson)
        self.assertGreaterEqual(len(geojson["features"]), 2)

        # Check target feature
        target_f = geojson["features"][0]
        self.assertEqual(target_f["geometry"]["type"], "Point")
        self.assertEqual(target_f["geometry"]["coordinates"], [self.ghondi_lon, self.ghondi_lat])
        self.assertEqual(target_f["properties"]["classification"], "Moderate")

        # Check buffer polygon feature
        buffer_f = geojson["features"][1]
        self.assertEqual(buffer_f["geometry"]["type"], "Polygon")
        self.assertEqual(len(buffer_f["geometry"]["coordinates"][0]), 65)

        print("[PASS] Test 11: GIS GeoJSON FeatureCollection verified.")



if __name__ == "__main__":
    print("\n=================================================================")
    print(" EXECUTING COMPREHENSIVE AI MINERAL PROSPECTIVITY TEST SUITE")
    print("=================================================================")
    unittest.main(verbosity=2)
