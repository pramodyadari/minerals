"""
Test Suite: tests/test_terrain_integration.py
Phase 3 — Real Terrain Data Integration & Iron Ore Readiness

Verifies:
1. Real Copernicus GLO-30 DEM tile discovery, coordinate systems, and vertical datum (EGM2008).
2. Spatially aligned 3-band GeoTIFF (Elevation, Slope, TPI) reprojected to EPSG:32645.
3. Terrain audit report schema, geomorphic metrics, and quality checks.
4. Point coordinate queries with geodetic slope and Topographic Position Index (TPI).
5. Robust out-of-bounds and missing-data failure modes (zero fabrication).
6. FastAPI endpoints: /evidence/processed, /api/mineral/iron-ore/terrain, /api/mineral/iron-ore/evaluation, /api/mineral/iron-ore/gsi-contract.
7. Strict scientific integrity: Iron Ore AI prospectivity scores remain null.
8. Non-regression for Manganese, Coal, and Bauxite.
"""

import os
import sys
import json
import math
import pytest
import numpy as np

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from fastapi.testclient import TestClient
from backend.app.main import app
from terrain_evidence import (
    TerrainEvidenceEngine,
    get_terrain_engine,
    query_terrain_at_coordinate,
    calculate_terrain_evidence,
    get_terrain_status,
    get_iron_ore_terrain_audit
)
from backend.app.gsi_data_contract import get_gsi_contract_validator
from backend.app.mineral_service import analyze_location_for_mineral

client = TestClient(app)


class TestCopernicusDEMDataIntegrity:
    """Validates real Copernicus GLO-30 DEM files on disk."""

    def test_01_dem_file_existence_and_properties(self):
        """Verifies Copernicus GLO-30 DEM tile exists with genuine properties."""
        dem_file = os.path.join(PROJECT_ROOT, "data", "dem", "Copernicus_DSM_COG_10_N22_00_E085_00_DEM.tif")
        assert os.path.exists(dem_file), "Raw Copernicus DEM tile must exist in data/dem/"
        assert os.path.getsize(dem_file) == 44882091, "Copernicus DEM file size must match authoritative 44.88 MB"

        import rasterio
        with rasterio.open(dem_file) as src:
            assert str(src.crs) == "EPSG:4326"
            assert src.shape == (3600, 3600)
            assert abs(src.res[0] - (1.0 / 3600.0)) < 1e-6
            assert src.bounds.left < 85.01 and src.bounds.right > 85.99
            assert src.bounds.bottom < 22.01 and src.bounds.top > 22.99

    def test_02_aligned_utm45n_geotiff_properties(self):
        """Verifies 3-band aligned GeoTIFF in EPSG:32645."""
        aligned_file = os.path.join(PROJECT_ROOT, "data", "dem", "noamundi_10km_copernicus_dem_utm45n.tif")
        assert os.path.exists(aligned_file), "Aligned GeoTIFF must exist"

        import rasterio
        with rasterio.open(aligned_file) as src:
            assert "32645" in str(src.crs)
            assert src.count == 3
            assert src.shape == (1000, 1000)
            assert src.res == (20.0, 20.0)

            elev = src.read(1)
            slope = src.read(2)
            tpi = src.read(3)

            # Elevations in Singhbhum craton must lie in reasonable range 300m - 1000m
            assert 300.0 < np.min(elev) < 400.0
            assert 800.0 < np.max(elev) < 1000.0

            # Slope range in degrees
            assert 0.0 <= np.min(slope)
            assert 40.0 < np.max(slope) < 90.0

            # TPI must have both positive (ridges) and negative (valleys)
            assert np.min(tpi) < -20.0
            assert np.max(tpi) > 20.0

    def test_03_terrain_audit_json_schema_and_metrics(self):
        """Verifies iron_ore_terrain_audit.json contains complete provenance and metrics."""
        audit_data = get_iron_ore_terrain_audit(PROJECT_ROOT)
        assert "audit_metadata" in audit_data
        assert "dataset_provenance" in audit_data
        assert "terrain_geomorphic_metrics" in audit_data
        assert "scientific_guardrails" in audit_data

        prov = audit_data["dataset_provenance"]
        assert prov["product_name"] == "Copernicus Digital Elevation Model (GLO-30 Public)"
        assert prov["raw_vertical_datum"] == "EGM2008 (Earth Gravitational Model 2008 geoid)"
        assert "aws.amazon.com" in prov["source_url"] or "copernicus-dem-30m" in prov["source_url"]

        metrics = audit_data["terrain_geomorphic_metrics"]
        elev_stats = metrics["elevation_m"]
        assert 350.0 < elev_stats["min"] < 400.0
        assert 850.0 < elev_stats["max"] < 950.0
        assert 450.0 < elev_stats["mean"] < 520.0
        assert abs(elev_stats["pit_centroid_elevation"] - 532.9) < 1.0


class TestTerrainEvidenceEngineProcessing:
    """Validates terrain processing engine logic and edge handling."""

    def test_04_noamundi_point_query_elevation_and_tpi(self):
        """Point query at Noamundi returns genuine elevation, slope, and TPI."""
        res = query_terrain_at_coordinate(lat=22.15, lon=85.50)
        assert res["available"] is True
        assert res["status"] == "AVAILABLE"
        assert abs(res["elevation_m"] - 532.9) < 1.0
        assert res["slope_deg"] > 0.0
        assert res["tpi_m"] is not None
        assert res["vertical_datum"] == "EGM2008"

    def test_05_kiriburu_crest_elevation_and_tpi(self):
        """Kiriburu ridge summit exhibits high elevation (>650m) and positive TPI."""
        res = query_terrain_at_coordinate(lat=22.0667, lon=85.25)
        assert res["available"] is True
        assert res["elevation_m"] > 650.0
        assert res["tpi_m"] > 5.0  # Ridge crest

    def test_06_out_of_bounds_honest_rejection(self):
        """Coordinates outside the DEM extent return OUT_OF_BOUNDS without data fabrication."""
        res = query_terrain_at_coordinate(lat=100.0, lon=200.0)
        assert res["available"] is False
        assert res["status"] == "INVALID_COORDINATES"

        # Coordinates far west in Gujarat (outside Singhbhum DEM)
        res_guj = query_terrain_at_coordinate(lat=22.50, lon=70.00)
        assert res_guj["available"] is False
        assert res_guj["status"] == "OUT_OF_BOUNDS"
        assert res_guj.get("elevation_m") is None


class TestApiIntegrationAndGuardrails:
    """Validates API endpoints expose terrain evidence while retaining null AI predictions."""

    def test_07_evidence_processed_endpoint_includes_terrain_evidence(self):
        """GET /evidence/processed for Noamundi returns authentic terrain_evidence block."""
        resp = client.get("/evidence/processed?latitude=22.15&longitude=85.50&mineral=Iron%20Ore&radius_km=10.0")
        assert resp.status_code == 200
        data = resp.json()

        assert "terrain_evidence" in data
        te = data["terrain_evidence"]
        assert te["status"] == "VERIFIED_ACTIVE"
        assert te["dataset"] == "Copernicus Digital Elevation Model (GLO-30 Public)"
        assert te["vertical_datum"] == "EGM2008 (Earth Gravitational Model 2008 geoid)"
        assert te["elevation_stats"]["pit_centroid_elevation_m"] == 532.9
        assert te["slope_stats"]["mean_slope_deg"] > 0.0
        assert te["topographic_position_index"]["neighbourhood_window_m"] == 500.0

        # AI score must remain strictly null
        assert data["model_availability"]["ai_prospectivity_score"] is None
        assert data["model_availability"]["model_confidence"] is None

    def test_08_api_iron_ore_terrain_endpoint(self):
        """GET /api/mineral/iron-ore/terrain returns 200 with terrain audit."""
        resp = client.get("/api/mineral/iron-ore/terrain")
        assert resp.status_code == 200
        data = resp.json()
        assert data["audit_metadata"]["status"] == "VERIFIED_REAL_DEM_INTEGRATED"
        assert "terrain_geomorphic_metrics" in data

    def test_09_api_iron_ore_evaluation_includes_terrain(self):
        """GET /api/mineral/iron-ore/evaluation returns measured_terrain_evidence with null score."""
        resp = client.get("/api/mineral/iron-ore/evaluation?lat=22.15&lon=85.50&radius_km=10.0")
        assert resp.status_code == 200
        data = resp.json()
        assert "measured_terrain_evidence" in data
        assert data["measured_terrain_evidence"]["status"] == "VERIFIED_ACTIVE"
        assert data["model_availability"]["ai_prospectivity_score"] is None

    def test_10_gsi_contract_endpoint(self):
        """GET /api/mineral/iron-ore/gsi-contract returns 200 with technical ingestion specifications."""
        resp = client.get("/api/mineral/iron-ore/gsi-contract")
        assert resp.status_code == 200
        data = resp.json()
        assert "aeromagnetic_grid_requirements" in data or "aeromagnetic_grid_contract" in data
        assert "geological_vector_requirements" in data or "geological_vector_contract" in data

    def test_11_iron_ore_analyze_endpoint_withholds_prediction(self):
        """POST /analyze for Iron Ore at Noamundi maintains null prediction and unavailable grid."""
        payload = {
            "location_name": "Noamundi Mining Sector",
            "latitude": 22.1500,
            "longitude": 85.5000,
            "mineral": "Iron Ore",
            "radius_km": 10.0
        }
        resp = client.post("/analyze", json=payload)
        assert resp.status_code == 200
        data = resp.json()

        assert data["mineral"] == "Iron Ore"
        assert data["prediction"] is None
        assert data["confidence_score"] is None
        assert data["model_coverage"] == "NO_MODEL_FOR_COMMODITY"
        assert data["prediction_availability"] == "UNAVAILABLE_NO_MODEL"
        assert data["prospectivity_grid"]["status"] == "UNAVAILABLE"

    def test_12_non_regression_manganese_coal_bauxite(self):
        """Manganese inside T44QMK remains active while Coal and Bauxite remain protected."""
        res_mn = analyze_location_for_mineral(
            location_name="Balaghat Sector",
            lat=21.9048,
            lon=80.1849,
            mineral_name="Manganese",
            radius_km=10.0
        )
        assert res_mn["mineral"] == "Manganese"
        assert res_mn["prediction_availability"] == "AVAILABLE"
        assert res_mn["prediction"] is not None

        for other_m in ["Coal", "Bauxite"]:
            res_other = analyze_location_for_mineral(
                location_name="Test Location",
                lat=22.1500,
                lon=85.5000,
                mineral_name=other_m,
                radius_km=10.0
            )
            assert res_other["prediction"] is None
            assert res_other["model_coverage"] == "NO_MODEL_FOR_COMMODITY"
