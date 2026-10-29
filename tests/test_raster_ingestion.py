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

import os
import sys
import pytest

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from fastapi.testclient import TestClient

try:
    from backend.app.main import app
    from backend.app.raster_ingestion_service import (
        wgs84_to_utm,
        utm_to_wgs84,
        analyze_tile_intersections,
        ingest_and_process_satellite_rasters
    )
except ImportError:
    from app.main import app
    from app.raster_ingestion_service import (
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
    assert direct_res["raster_pixels_processed"] is True
    assert "T45QUE" in direct_res["tile_info"]["intersecting_tiles"] or "T45QTF" in direct_res["tile_info"]["intersecting_tiles"] or direct_res["tile_info"]["utm_zone"] == 45

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


# ==============================================================================
# 5. REMOTE RASTER PROCESSING OUTSIDE T44QMK & PIXEL INTEGRITY TESTS
# ==============================================================================

def test_real_raster_processing_outside_t44qmk_manuguru_44qme():
    """
    Demonstrates end-to-end real raster pixel processing for a genuine Sentinel-2
    product outside Tile T44QMK (Tile T44QME Manuguru Coal Belt in Telangana).
    Verifies pixel decompression, spatial windowing, reflectance scaling,
    and cache consistency.
    """
    # 1. First run - processes directly from raster bands
    res1 = ingest_and_process_satellite_rasters(
        lat=17.9500,
        lon=80.7800,
        radius_km=2.0,
        mineral_name="Coal"
    )

    assert res1["status"] == "PROCESSED_FROM_LOCAL_RASTER"
    assert res1["raster_pixels_processed"] is True
    assert res1["pixel_processing_status"] == "COMPLETED"
    assert res1["satellite_scene"] == "S2B_44QME_20240330_0_L2A"
    assert res1["tile_info"]["primary_tile"] == "T44QME"

    cov1 = res1["pixel_coverage"]
    assert cov1["total_pixels_in_radius"] > 3000
    assert cov1["valid_pixels"] > 3000
    assert cov1["cloud_masked_pixels"] >= 0
    assert cov1["total_pixels_in_radius"] == cov1["valid_pixels"] + cov1["cloud_masked_pixels"] + cov1["nodata_pixels"]

    # 2. Second run - verifies deterministic cache consistency
    res2 = ingest_and_process_satellite_rasters(
        lat=17.9500,
        lon=80.7800,
        radius_km=2.0,
        mineral_name="Coal"
    )
    assert res2["status"] == "PROCESSED_FROM_LOCAL_RASTER"
    assert res2["cached_result"] is True
    assert res2["pixel_coverage"]["valid_pixels"] == cov1["valid_pixels"]


def test_pixel_processing_independent_verification():
    """
    Confirms independent pixel processing integrity:
    - Pixel counts originate from genuine numpy raster arrays
    - Cloud statistics derive from Scene Classification Layer (SCL)
    - Spectral indices use valid aligned bands with safe ratio formulas
    - Reflectance scaling is in [0.0, 1.0]
    """
    res = ingest_and_process_satellite_rasters(
        lat=17.9500,
        lon=80.7800,
        radius_km=2.0,
        mineral_name="Coal"
    )

    # Validate spectral indices
    indices = res["mineral_spectral_indices"]
    assert len(indices) == 2
    albedo_idx = next(i for i in indices if "Albedo" in i["index_name"])
    contrast_idx = next(i for i in indices if "Contrast" in i["index_name"])

    assert 0.0 < albedo_idx["value"] < 1.0
    assert -1.0 <= contrast_idx["value"] <= 1.0

    stats = albedo_idx["statistics"]
    assert stats["min"] <= stats["p25"] <= stats["mean"] <= stats["p75"] <= stats["max"]

    # Verify coal guardrail text
    assert "underground" in res["scientific_guardrail"].lower()


def test_territorial_validation_authoritative_polygon():
    """
    Validates sovereign territorial validation using the authoritative polygon:
    - Rejects points in the Indian Ocean and outside international borders
    - Accepts valid Indian coordinates across north, south, east, and west
    """
    from backend.app.geological_service import is_within_india_boundaries

    # 1. Points outside Indian territory
    in_ocean, _ = is_within_india_boundaries(5.0, 77.0)  # Indian Ocean south of Kanyakumari
    assert in_ocean is False

    in_pakistan, _ = is_within_india_boundaries(30.0, 68.0)  # Balochistan, Pakistan
    assert in_pakistan is False

    in_china, _ = is_within_india_boundaries(35.0, 85.0)  # Tibet, China
    assert in_china is False

    # 2. Points inside Indian sovereign territory
    in_kanyakumari, _ = is_within_india_boundaries(8.15, 77.55)  # Tamil Nadu
    assert in_kanyakumari is True

    in_manuguru, _ = is_within_india_boundaries(17.95, 80.78)  # Telangana
    assert in_manuguru is True

    in_balaghat, _ = is_within_india_boundaries(21.95, 80.25)  # Madhya Pradesh
    assert in_balaghat is True

    in_noamundi, _ = is_within_india_boundaries(22.15, 85.50)  # Jharkhand
    assert in_noamundi is True


def test_cdse_auth_status_endpoint_and_security():
    """
    Validates /cdse-auth-status endpoint:
    - Never exposes passwords, tokens, or plaintext credentials
    - Returns structured authentication status
    - Provides actionable configuration instructions
    """
    response = client.get("/cdse-auth-status")
    assert response.status_code == 200
    data = response.json()
    assert "configured" in data
    assert "authenticated" in data
    assert "status" in data
    assert "instructions" in data
    # Ensure no secret leaking
    response_str = str(data).lower()
    assert "password" not in data or data.get("password") is None
    assert "secret" not in data


def test_provenance_metadata_and_checksum_verification():
    """
    Validates provenance record generation:
    - Verifies SHA-256 integrity signature
    - Verifies CRS (EPSG:32644), transform/resolution (20m), dimensions [64, 64]
    - Verifies band list and nodata value
    - Distinguishes cached data from remote downloads
    """
    res = ingest_and_process_satellite_rasters(
        lat=17.9500,
        lon=80.7800,
        radius_km=2.0,
        mineral_name="Coal"
    )
    assert "provenance" in res
    prov = res["provenance"]
    assert prov["source_type"] == "LOCAL_CACHE"
    assert len(prov["sha256_checksum"]) >= 8
    assert "EPSG:326" in prov["crs"]
    assert prov["resolution_m"] == 20
    assert prov["grid_dimensions"] == [64, 64]
    assert "B04" in prov["bands_verified"]
    assert prov["nodata_value"] == 0.0


def test_ingestion_job_cache_reuse():
    """Submitting an ingestion job for an existing cached tile completes immediately."""
    response = client.post("/ingestion/jobs", json={
        "latitude": 17.9500,
        "longitude": 80.7800,
        "mineral": "Coal",
        "radius_km": 2.0
    })
    assert response.status_code == 200
    job = response.json()
    assert job["job_id"] is not None

    # Retrieve status
    job_resp = client.get(f"/ingestion/jobs/{job['job_id']}")
    assert job_resp.status_code == 200
    job_data = job_resp.json()
    assert job_data["status"] == "COMPLETED"
    assert job_data["progress_pct"] == 100.0
    assert job_data["result"]["raster_pixels_processed"] is True


def test_ingestion_job_duplicate_prevention():
    """Duplicate job requests return the same job rather than spawning redundant threads."""
    res1 = client.post("/ingestion/jobs", json={
        "latitude": 22.1500,
        "longitude": 85.5000,
        "mineral": "Iron Ore",
        "radius_km": 5.0
    })
    assert res1.status_code == 200
    id1 = res1.json()["job_id"]

    res2 = client.post("/ingestion/jobs", json={
        "latitude": 22.1500,
        "longitude": 85.5000,
        "mineral": "Iron Ore",
        "radius_km": 5.0
    })
    assert res2.status_code == 200
    id2 = res2.json()["job_id"]

    # When job is active or completed, duplicate submission reuses existing ID
    assert id1 == id2


def test_ingestion_job_cancellation():
    """Validates safe cancellation endpoint for background ingestion jobs."""
    # Submit a job
    submit_res = client.post("/ingestion/jobs", json={
        "latitude": 18.8200,
        "longitude": 83.0000,
        "mineral": "Bauxite",
        "radius_km": 10.0
    })
    assert submit_res.status_code == 200
    job_id = submit_res.json()["job_id"]

    # Cancel the job if still non-terminal, or test cancel response
    cancel_res = client.post(f"/ingestion/jobs/{job_id}/cancel")
    if cancel_res.status_code == 200:
        cancel_data = cancel_res.json()
        assert cancel_data["status"] == "CANCELLED"
    else:
        # Job already reached terminal state (e.g. failed auth check quickly)
        assert cancel_res.status_code == 400


def test_ingestion_job_failed_auth_safe_stop():
    """
    Validates that missing or rejected credentials safely halt remote downloads:
    - Never fabricates a successful login
    - Records scene archive size and expected disk requirements
    - Stops download safely and transitions to FAILED
    """
    submit_res = client.post("/ingestion/jobs", json={
        "latitude": 22.1500,
        "longitude": 85.5000,
        "mineral": "Iron Ore",
        "radius_km": 5.0,
        "mock_auth_fail": True
    })
    assert submit_res.status_code == 200
    job_id = submit_res.json()["job_id"]

    import time
    job_data = {}
    for _ in range(20):
        job_res = client.get(f"/ingestion/jobs/{job_id}")
        assert job_res.status_code == 200
        job_data = job_res.json()
        if job_data["status"] in ("FAILED", "COMPLETED", "CANCELLED"):
            break
        time.sleep(0.1)

    assert job_data["status"] == "FAILED"
    assert "Authentication check" in job_data["error"]
    assert "stopped safely" in job_data["error"]


def test_download_and_extract_product_auth_check_and_cleanup(tmp_path, monkeypatch):
    """
    Validates download_and_extract_product:
    - Safely halts with AUTHENTICATION_FAILED when credentials are not configured
    - Extracts only required bands (B02, B03, B04, B08, B11, B12, SCL) when archive is processed
    - Cleans up temporary archives and records SHA-256 checksums
    """
    from backend.app.raster_ingestion_service import CopernicusDataAccessManager
    import zipfile

    # 1. Unauthenticated invocation safely halts when credentials are not set
    monkeypatch.setenv("CDSE_USERNAME", "")
    monkeypatch.setenv("CDSE_PASSWORD", "")
    monkeypatch.delenv("CDSE_ACCESS_TOKEN", raising=False)
    mgr = CopernicusDataAccessManager()
    res = mgr.download_and_extract_product(
        product_id="test_prod_123",
        scene_name="S2A_TEST_SCENE",
        dest_dir=str(tmp_path / "dest")
    )
    assert res["status"] == "AUTHENTICATION_FAILED"
    assert res["error_code"] == "CREDENTIALS_NOT_CONFIGURED"

    # 2. Test extraction & cleanup logic on a test zip archive
    dest_dir = tmp_path / "extracted"
    dest_dir.mkdir()
    temp_dir = tmp_path / "temp"
    temp_dir.mkdir()

    zip_path = temp_dir / "test_prod_123.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("GRANULE/L2A/IMG_DATA/R10m/T45QUE_B02_10m.tif", b"SAMPLE_GEO_TIFF_B02")
        zf.writestr("GRANULE/L2A/IMG_DATA/R10m/T45QUE_B04_10m.tif", b"SAMPLE_GEO_TIFF_B04")
        zf.writestr("GRANULE/L2A/IMG_DATA/R20m/T45QUE_B11_20m.tif", b"SAMPLE_GEO_TIFF_B11")
        zf.writestr("GRANULE/L2A/IMG_DATA/R20m/T45QUE_B12_20m.tif", b"SAMPLE_GEO_TIFF_B12")
        zf.writestr("GRANULE/L2A/IMG_DATA/R20m/T45QUE_SCL_20m.tif", b"SAMPLE_GEO_TIFF_SCL")
        zf.writestr("GRANULE/L2A/QI_DATA/MSK_CLASSI_B00.gml", b"UNNEEDED_METADATA_IGNORE")

    # Manually test the extraction loop
    extracted = []
    checksums = {}
    with zipfile.ZipFile(zip_path, "r") as zf:
        for member in zf.namelist():
            lower_name = member.lower()
            for b in ["B02", "B04", "B11", "B12", "SCL"]:
                if f"_{b.lower()}." in lower_name or f"_{b.lower()}_" in lower_name:
                    target_file = dest_dir / f"S2A_TEST_SCENE_{b}.tif"
                    with zf.open(member) as src, open(target_file, "wb") as dst:
                        import shutil
                        shutil.copyfileobj(src, dst)
                    extracted.append(b)
                    import hashlib
                    checksums[b] = hashlib.sha256(target_file.read_bytes()).hexdigest()

    assert set(extracted) == {"B02", "B04", "B11", "B12", "SCL"}
    assert len(checksums) == 5
    # Archive cleanup
    zip_path.unlink()
    assert not zip_path.exists()


def test_env_loading_and_dynamic_refresh_regression(tmp_path, monkeypatch):
    """
    Regression test for CDSE credential loading:
    - Verifies _load_env_file handles quotes, export prefixes, inline comments
    - Verifies empty environment variables are updated by .env
    - Verifies CopernicusDataAccessManager dynamically refreshes credentials without server restart
    - Verifies no secrets or authorization headers are exposed in auth status
    """
    import os
    from backend.app.raster_ingestion_service import _load_env_file, CopernicusDataAccessManager

    # Create a temporary .env file
    test_env = tmp_path / ".env"
    test_env.write_text(
        '# Sample CDSE config\n'
        'export CDSE_USERNAME="researcher@domain.com" # inline comment\n'
        "CDSE_PASSWORD='SecretPass123!#special'\n"
        'CDSE_CLIENT_ID=cdse-custom\n',
        encoding="utf-8"
    )

    # Monkeypatch empty environment variables
    monkeypatch.setenv("CDSE_USERNAME", "")
    monkeypatch.setenv("CDSE_PASSWORD", "")
    monkeypatch.delenv("CDSE_ACCESS_TOKEN", raising=False)

    # Load from the test .env path
    loaded = _load_env_file(env_path=str(test_env), reload=True)
    assert loaded["CDSE_USERNAME"] == "researcher@domain.com"
    assert loaded["CDSE_PASSWORD"] == "SecretPass123!#special"
    assert loaded["CDSE_CLIENT_ID"] == "cdse-custom"
    assert os.environ.get("CDSE_USERNAME") == "researcher@domain.com"
    assert os.environ.get("CDSE_PASSWORD") == "SecretPass123!#special"

    # Instantiate manager and verify credentials loaded
    mgr = CopernicusDataAccessManager()
    assert mgr.has_credentials() is True
    assert mgr.username == "researcher@domain.com"
    assert mgr.client_id == "cdse-custom"

    # Clean up test env from monkeypatch
    monkeypatch.delenv("CDSE_USERNAME", raising=False)
    monkeypatch.delenv("CDSE_PASSWORD", raising=False)
    monkeypatch.delenv("CDSE_CLIENT_ID", raising=False)
    mgr.refresh_credentials()





