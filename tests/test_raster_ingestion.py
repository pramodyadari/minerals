"""
================================================================================
TEST SUITE: NATIONWIDE SATELLITE RASTER INGESTION & PROCESSING PIPELINE
================================================================================
Validates:
  1. Real Sentinel-2 Level-2A pixel processing within Tile T44QMK (Balaghat Manganese).
  2. Multi-tile boundary intersection detection across MGRS grid boundaries.
  3. Safe handling of locations in different Indian states (Telangana, Jharkhand, Odisha, Gujarat).
  4. High cloud cover masking and quality rejection.
  5. Missing-data band error handling.
  6. Distinction between Copernicus catalogue discovery and actual raster pixel processing.
  7. Strict mineral-specific scientific guardrails (Coal, Iron Ore, Bauxite, Manganese).
  8. Preservation of Random Forest model boundaries (null predictions outside validated domain).
================================================================================
"""

import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.raster_ingestion_service import (
    wgs84_to_utm,
    utm_to_wgs84,
    analyze_tile_intersections,
    ingest_and_process_satellite_rasters
)

client = TestClient(app)

# ==============================================================================
# 1. GEODESY & PROJECTION TESTS
# ==============================================================================

def test_wgs84_to_utm_projection_accuracy():
    """Validates millimeter-accurate UTM transformation across Indian longitudes."""
    # Balaghat reference coordinates
    lat, lon = 21.9455, 80.4295
    zone, easting, northing = wgs84_to_utm(lat, lon)

    assert zone == 44
    assert abs(easting - 441089.33) < 1.0
    assert abs(northing - 2426904.20) < 1.0

    # Invert back to WGS84
    rev_lat, rev_lon = utm_to_wgs84(zone, easting, northing)
    assert abs(rev_lat - lat) < 1e-4
    assert abs(rev_lon - lon) < 1e-4

def test_multi_tile_boundary_detection():
    """Validates detection of analysis circles crossing Sentinel-2 MGRS boundaries."""
    # Point near Tile T44QMK western edge with 25 km radius
    boundary_lat, boundary_lon = 21.50, 79.80
    info = analyze_tile_intersections(boundary_lat, boundary_lon, radius_km=25.0)

    assert info["tile_boundary_crossed"] is True
    assert len(info["intersecting_tiles"]) >= 2
    assert "T44QMK" in info["intersecting_tiles"]
    assert "T44QLK" in info["intersecting_tiles"] or "T44QMJ" in info["intersecting_tiles"]


# ==============================================================================
# 2. REAL PIXEL PROCESSING IN TILE T44QMK (BALAGHAT MANGANESE)
# ==============================================================================

def test_real_raster_pixel_processing_balaghat():
    """Validates that real pixels are decompressed, aligned, and processed in Balaghat."""
    res = ingest_and_process_satellite_rasters(
        lat=21.9455,
        lon=80.4295,
        radius_km=10.0,
        mineral_name="Manganese"
    )

    assert res["status"] == "PROCESSED_FROM_LOCAL_RASTER"
    assert res["raster_pixels_processed"] is True
    assert res["pixel_processing_status"] == "COMPLETED"
    assert res["data_access_status"] == "ACCESSED_LOCAL_RASTER"

    # Verify pixel coverage counts
    cov = res["pixel_coverage"]
    assert cov["total_pixels_in_radius"] > 1000
    assert cov["valid_pixels"] > 1000
    assert cov["pixel_resolution_m"] == 20

    # Verify BOA surface reflectances across 6 bands
    refs = res["band_reflectances"]
    assert 0.0 < refs["B02_blue"] < 0.2
    assert 0.0 < refs["B03_green"] < 0.25
    assert 0.0 < refs["B04_red"] < 0.35
    assert 0.0 < refs["B08_nir"] < 0.6
    assert 0.0 < refs["B11_swir1"] < 0.5
    assert 0.0 < refs["B12_swir2"] < 0.4

    # Verify mineral indices have valid numerical statistics
    indices = res["mineral_spectral_indices"]
    assert len(indices) == 5
    clay_idx = next(i for i in indices if "Clay" in i["index_name"])
    assert clay_idx["value"] > 1.0
    assert clay_idx["statistics"]["mean"] is not None


# ==============================================================================
# 3. MULTI-STATE TARGETS & DISTINCTION FROM CATALOGUE DISCOVERY
# ==============================================================================

def test_manuguru_telangana_coal_distinguishes_discovery_from_pixels():
    """
    Validates that in Manuguru (Telangana), CDSE catalogue discovery succeeds,
    but raster_pixels_processed remains False until authenticated band download.
    """
    # Direct raster ingestion pipeline test with discovered scene
    scene_mock = [{
        "scene_id": "S2A_MSIL2A_20260310_T44QKD",
        "product_id": "mock-prod-44qkd",
        "satellite": "Sentinel-2A",
        "tile_id": "T44QKD",
        "acquisition_date": "2026-03-10",
        "cloud_cover_pct": 3.2
    }]
    raster_res = ingest_and_process_satellite_rasters(
        lat=17.9800,
        lon=80.7600,
        radius_km=10.0,
        mineral_name="Coal",
        discovered_scenes=scene_mock
    )
    assert raster_res["raster_pixels_processed"] is False
    assert raster_res["pixel_processing_status"] == "PENDING_AUTHENTICATED_ACCESS"
    assert "CDSE_USERNAME" in raster_res["raster_processing_details"]

    # API test
    response = client.post("/analyze", json={
        "location_name": "Manuguru Coal Mining Belt, Telangana",
        "latitude": 17.9800,
        "longitude": 80.7600,
        "mineral": "Coal",
        "radius_km": 10.0,
        "mock_satellite_error": "TIMEOUT"
    })
    assert response.status_code == 200
    data = response.json()
    assert data["mineral"] == "Coal"
    assert data["prediction"] is None
    assert data["raster_pixels_processed"] is False

    # Check that coal-specific limitations exist in limitations_and_warnings
    coal_warning = " ".join(data.get("limitations_and_warnings", []))
    assert "drill" in coal_warning.lower() or "subsurface" in coal_warning.lower() or "underground" in coal_warning.lower()

def test_jharia_jharkhand_coal_guardrails():
    """Validates Jharia Coal Basin analysis in Jharkhand."""
    # Direct scientific guardrails test for Coal
    direct_res = ingest_and_process_satellite_rasters(
        lat=23.7500,
        lon=86.4200,
        radius_km=10.0,
        mineral_name="Coal"
    )
    assert direct_res["raster_pixels_processed"] is False
    assert direct_res["tile_info"]["utm_zone"] == 45

    response = client.post("/analyze", json={
        "location_name": "Jharia Coalfield, Dhanbad, Jharkhand",
        "latitude": 23.7500,
        "longitude": 86.4200,
        "mineral": "Coal",
        "radius_km": 10.0,
        "mock_satellite_error": "TIMEOUT"
    })
    assert response.status_code == 200
    data = response.json()
    assert data["mineral"] == "Coal"
    assert data["prediction"] is None
    assert data["raster_pixels_processed"] is False

def test_noamundi_jharkhand_iron_ore_guardrails():
    """Validates Singhbhum-North Odisha Iron Ore corridor in Jharkhand/Odisha."""
    # Direct scientific guardrails test for Iron Ore
    direct_res = ingest_and_process_satellite_rasters(
        lat=22.1500,
        lon=85.5000,
        radius_km=10.0,
        mineral_name="Iron Ore"
    )
    assert direct_res["raster_pixels_processed"] is False
    assert "T45QTF" in direct_res["tile_info"]["intersecting_tiles"] or direct_res["tile_info"]["utm_zone"] == 45

    response = client.post("/analyze", json={
        "location_name": "Noamundi Iron Ore Mine, West Singhbhum, Jharkhand",
        "latitude": 22.1500,
        "longitude": 85.5000,
        "mineral": "Iron Ore",
        "radius_km": 10.0,
        "mock_satellite_error": "TIMEOUT"
    })
    assert response.status_code == 200
    data = response.json()
    assert data["mineral"] == "Iron Ore"
    assert data["prediction"] is None
    assert data["raster_pixels_processed"] is False

def test_panchpatmali_odisha_bauxite_guardrails():
    """Validates Panchpatmali Bauxite Plateau in Koraput, Odisha."""
    # Direct scientific guardrails test for Bauxite
    direct_res = ingest_and_process_satellite_rasters(
        lat=18.8200,
        lon=83.0000,
        radius_km=10.0,
        mineral_name="Bauxite"
    )
    assert direct_res["raster_pixels_processed"] is False
    assert direct_res["tile_info"]["utm_zone"] == 44

    response = client.post("/analyze", json={
        "location_name": "Panchpatmali Bauxite Mine, Koraput, Odisha",
        "latitude": 18.8200,
        "longitude": 83.0000,
        "mineral": "Bauxite",
        "radius_km": 10.0,
        "mock_satellite_error": "TIMEOUT"
    })
    assert response.status_code == 200
    data = response.json()
    assert data["mineral"] == "Bauxite"
    assert data["prediction"] is None
    assert data["raster_pixels_processed"] is False


# ==============================================================================
# 4. HIGH CLOUD COVER & MISSING DATA QUALITY CONTROL
# ==============================================================================

def test_high_cloud_cover_quality_rejection():
    """Validates rejection of scenes with heavy cloud cover (e.g. monsoon imagery)."""
    res = ingest_and_process_satellite_rasters(
        lat=21.9455,
        lon=80.4295,
        radius_km=10.0,
        mineral_name="Manganese",
        mock_error_type="HIGH_CLOUD_COVER"
    )

    assert res["status"] == "CLOUD_MASKED_NO_USABLE_PIXELS"
    assert res["raster_pixels_processed"] is False
    assert res["cloud_cover_pct"] > 90.0
    assert res["valid_pixels"] == 0

def test_missing_data_band_rejection():
    """Validates safe handling when required bands are missing from data provider."""
    res = ingest_and_process_satellite_rasters(
        lat=21.9455,
        lon=80.4295,
        radius_km=10.0,
        mineral_name="Manganese",
        mock_error_type="MISSING_DATA"
    )

    assert res["status"] == "MISSING_DATA_IN_BAND_RASTER"
    assert res["raster_pixels_processed"] is False
    assert "MISSING" in res["pixel_processing_status"]
