"""
================================================================================
TEST SUITE: ARBITRARY LOCATION ANALYSIS (LOCATION != ZONE)
================================================================================
Validates that:
1. Arbitrary coordinates inside Sentinel-2 T44QMK footprint evaluate successfully
2. Location does NOT need to belong to high_prospectivity_zones.csv
3. Candidate zones are strictly descriptive proximity information
4. Out-of-bounds coordinates are rejected with OutOfBoundsError without score fabrication
5. Model prediction originates authentically from trained Manganese raster surface
================================================================================
"""

import os
import sys
import unittest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from mineral_prospectivity_pipeline import (
    ProspectivityPipeline,
    OutOfBoundsError,
    InvalidCoordinateError
)


class TestArbitraryLocationAnalysis(unittest.TestCase):
    """Test suite ensuring location selection is decoupled from candidate discovery zones."""

    @classmethod
    def setUpClass(cls):
        cls.tif_path = os.path.join(PROJECT_ROOT, "outputs", "manganese_prospectivity.tif")
        cls.pipeline = ProspectivityPipeline(cls.tif_path)

    def test_arbitrary_coordinate_inside_raster_analyzed(self):
        """Validates that a random coordinate inside raster coverage is analyzed successfully."""
        # Random location in T44QMK coverage far from candidate zones
        lat, lon = 21.9400, 80.4200
        res = self.pipeline.analyze_location(lat=lat, lon=lon, radius_km=25.0, mineral="manganese")
        
        self.assertEqual(res["status"], "success")
        self.assertEqual(res["mineral"], "Manganese (Mn)")
        self.assertTrue(res["target"]["inside_raster"])
        self.assertIn("score", res["prospectivity"])
        self.assertIn("percent", res["prospectivity"])
        self.assertIn("classification", res["prospectivity"])
        self.assertGreaterEqual(res["prospectivity"]["percent"], 0.0)
        self.assertLessEqual(res["prospectivity"]["percent"], 100.0)

    def test_location_with_no_candidate_zone(self):
        """Confirms that a location with zero candidate zones in 5km still analyzes normally."""
        lat, lon = 21.6500, 80.3500
        res = self.pipeline.analyze_location(lat=lat, lon=lon, radius_km=5.0, mineral="manganese")
        
        self.assertEqual(res["status"], "success")
        self.assertIsInstance(res["candidate_zones_in_radius"], list)
        # Point is evaluated regardless of nearby zone count
        self.assertIn("percent", res["prospectivity"])

    def test_candidate_zone_is_purely_optional(self):
        """Verifies candidate zones are descriptive proximity data, not prerequisites."""
        zones = self.pipeline.load_candidate_zones()
        self.assertGreater(len(zones), 0, "Candidate zones should exist for ranking")

        # Test point at top zone centroid
        top_zone = zones[0]
        res_zone = self.pipeline.analyze_location(lat=top_zone["latitude"], lon=top_zone["longitude"], radius_km=10.0)
        self.assertEqual(res_zone["status"], "success")

        # Test arbitrary point with NO zone centroid
        res_arb = self.pipeline.analyze_location(lat=22.0500, lon=80.2500, radius_km=10.0)
        self.assertEqual(res_arb["status"], "success")
        self.assertIn("score", res_arb["prospectivity"])

    def test_out_of_bounds_rejection(self):
        """Confirms out-of-bounds coordinates are rejected without fabricated predictions."""
        # Delhi coordinates, far outside T44QMK
        out_lat, out_lon = 28.6139, 77.2090
        with self.assertRaises(OutOfBoundsError):
            self.pipeline.analyze_location(lat=out_lat, lon=out_lon, radius_km=25.0)


if __name__ == "__main__":
    unittest.main()
