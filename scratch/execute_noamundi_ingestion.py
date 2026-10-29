"""
Controlled Noamundi (T45QUE) Sentinel-2 L2A Ingestion, Verification, and Processing
Follows strict scientific data acquisition and verification standards.
"""

import os
import sys
import time
import json
import shutil
import hashlib
import zipfile
import urllib.request
import numpy as np
import rasterio
from rasterio.enums import Resampling

# Ensure backend/app is importable
APP_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "backend", "app")
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if APP_DIR not in sys.path:
    sys.path.insert(0, APP_DIR)

from raster_ingestion_service import (
    CopernicusDataAccessManager,
    wgs84_to_utm,
    utm_to_wgs84,
    process_spectral_indices_for_mineral,
    MASKED_SCL_CLASSES,
    SCL_NO_DATA,
    SCL_CLOUD_SHADOW,
    SCL_CLOUD_MEDIUM_PROB,
    SCL_CLOUD_HIGH_PROB,
    SCL_THIN_CIRRUS,
    SCL_SNOW_ICE,
    SCL_BARE_SOIL,
    SCL_VEGETATION
)

def main():
    print("=" * 80)
    print("AI MINERAL EXPLORATION - CONTROLLED NOAMUNDI (T45QUE) INGESTION PIPELINE")
    print("=" * 80)

    # 1. Inspect existing state and output directories
    print("\n[Step 1] Inspecting existing directories and architecture...")
    dest_cache_root = os.path.join(PROJECT_ROOT, "data", "cache", "sentinel2")
    temp_dir = os.path.join(PROJECT_ROOT, "data", "cache", "temp_extract")
    processed_dir = os.path.join(PROJECT_ROOT, "data", "cache", "processed")
    os.makedirs(dest_cache_root, exist_ok=True)
    os.makedirs(temp_dir, exist_ok=True)
    os.makedirs(processed_dir, exist_ok=True)
    print(f"  Raster cache root: {dest_cache_root}")
    print(f"  Temp directory:    {temp_dir}")
    print(f"  Processed cache:   {processed_dir}")

    # 2. Test CDSE authentication without printing secrets
    print("\n[Step 2] Testing CDSE authentication safely...")
    mgr = CopernicusDataAccessManager()
    if not mgr.has_credentials():
        print("ERROR: CDSE credentials not configured in environment or .env.")
        sys.exit(1)
    
    auth_check = mgr.verify_authentication(timeout_sec=30.0)
    if not auth_check.get("authenticated"):
        print(f"ERROR: Authentication failed: {auth_check.get('message')}")
        sys.exit(1)
    print("  Authentication Status: AUTHENTICATED_OK (Secrets preserved, token verified)")

    # 3. Live Catalogue Product Verification
    print("\n[Step 3] Re-verifying Noamundi product in live CDSE catalogue...")
    target_uuid = "15cf3fdd-a44e-4f23-9c64-bbe5a300676e"
    target_scene_name = "S2A_MSIL2A_20261010T045231_N0513_R076_T45QUE_20261010T095406"
    expected_content_length = 1170660578

    token = mgr.obtain_access_token(timeout_sec=30.0)
    cat_url = f"https://catalogue.dataspace.copernicus.eu/odata/v1/Products({target_uuid})?%24expand=Attributes"
    req_meta = urllib.request.Request(cat_url, headers={"User-Agent": "AI-Mineral-Exploration-System/2.0"})
    with urllib.request.urlopen(req_meta, timeout=30) as resp:
        meta = json.loads(resp.read().decode())
        attrs = {a.get("Name"): a.get("Value") for a in meta.get("Attributes", [])}
    
    prod_name = meta.get("Name", "")
    prod_online = meta.get("Online", False)
    content_len = meta.get("ContentLength", 0)
    acq_date = meta.get("ContentDate", {}).get("Start", "")
    cloud_cover = attrs.get("cloudCover", None)
    footprint = meta.get("GeoFootprint", {})

    print(f"  Product UUID:     {target_uuid}")
    print(f"  Product Name:     {prod_name}")
    print(f"  Acquisition Time: {acq_date}")
    print(f"  Cloud Cover:      {cloud_cover}%")
    print(f"  Online Status:    {prod_online}")
    print(f"  Content Length:   {content_len:,} bytes ({round(content_len / (1024**2), 2)} MB)")
    print(f"  Footprint Type:   {footprint.get('type')}")
    
    if not prod_online:
        print("ERROR: Product is not online in CDSE catalogue.")
        sys.exit(1)

    # 4. Check free disk space and destination safety
    print("\n[Step 4] Checking free disk space and destination directory...")
    total, used, free = shutil.disk_usage(PROJECT_ROOT)
    free_gb = free / (1024**3)
    needed_gb = (content_len * 2) / (1024**3) # archive + extracted
    print(f"  Free disk space:    {free_gb:.2f} GB")
    print(f"  Required space:    ~{needed_gb:.2f} GB")
    if free_gb < 5.0:
        print(f"ERROR: Insufficient free disk space ({free_gb:.2f} GB < 5.0 GB safety margin).")
        sys.exit(1)
    
    dest_scene_dir = os.path.join(dest_cache_root, target_scene_name)
    print(f"  Destination path:   {dest_scene_dir}")
    if os.path.exists(dest_scene_dir) and any(os.listdir(dest_scene_dir)):
        print("  NOTICE: Destination exists. Existing files will be checked.")
    else:
        os.makedirs(dest_scene_dir, exist_ok=True)
        print("  Destination verified clean (no overwrite of existing scenes).")

    # 5. Controlled Streaming Download (Exactly ONE controlled download)
    print("\n[Step 5] Initiating exactly ONE controlled streaming download from CDSE...")
    final_zip_path = os.path.join(temp_dir, f"{target_uuid}.zip")
    tmp_zip_path = os.path.join(temp_dir, f"{target_uuid}.zip.tmp")

    if os.path.exists(final_zip_path) and os.path.getsize(final_zip_path) == content_len:
        print(f"  Verified existing complete archive found at {final_zip_path} ({os.path.getsize(final_zip_path):,} bytes). Skipping re-download.")
    else:
        # Use direct download host
        download_url = f"https://download.dataspace.copernicus.eu/odata/v1/Products({target_uuid})/$value"
        print(f"  Streaming from: {download_url}")
        
        # Remove any partial or stale files
        if os.path.exists(tmp_zip_path):
            os.remove(tmp_zip_path)

        t_start = time.time()
        import subprocess
        # Use curl for high-performance streaming with keepalive and buffer management
        curl_cmd = [
            "curl.exe",
            "-s", "-S", "--fail",
            "-H", f"Authorization: Bearer {token}",
            "-H", "User-Agent: AI-Mineral-Exploration-System/2.0",
            "-o", tmp_zip_path,
            download_url
        ]
        
        print("  Starting controlled download process...")
        proc = subprocess.Popen(curl_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        
        last_log = time.time()
        while proc.poll() is None:
            time.sleep(2.0)
            now = time.time()
            if now - last_log >= 10.0:
                cur_sz = os.path.getsize(tmp_zip_path) if os.path.exists(tmp_zip_path) else 0
                pct = (cur_sz / content_len) * 100.0
                mb_done = cur_sz / (1024**2)
                mb_total = content_len / (1024**2)
                rate = mb_done / max(1e-3, now - t_start)
                print(f"    Progress: {mb_done:.1f}/{mb_total:.1f} MB ({pct:.1f}%) @ {rate:.2f} MB/s")
                last_log = now

        stdout, stderr = proc.communicate()
        if proc.returncode != 0:
            print(f"ERROR: curl download failed with exit code {proc.returncode}")
            if os.path.exists(tmp_zip_path):
                os.remove(tmp_zip_path)
            sys.exit(1)

        dl_sz = os.path.getsize(tmp_zip_path) if os.path.exists(tmp_zip_path) else 0
        if dl_sz != content_len:
            print(f"ERROR: Incomplete download! Size {dl_sz} != {content_len}")
            if os.path.exists(tmp_zip_path):
                os.remove(tmp_zip_path)
            sys.exit(1)

        if os.path.exists(final_zip_path):
            os.remove(final_zip_path)
        os.replace(tmp_zip_path, final_zip_path)
        elapsed = time.time() - t_start
        print(f"  Download completed successfully in {elapsed:.1f}s ({round(dl_sz / (1024**2), 2)} MB) @ {dl_sz / (1024**2) / elapsed:.2f} MB/s.")

    # 6. Verify download completion and archive integrity before extraction
    print("\n[Step 6] Verifying archive integrity before extraction...")
    downloaded_size = os.path.getsize(final_zip_path)
    print(f"  Archive path:       {final_zip_path}")
    print(f"  Archive size:       {downloaded_size:,} bytes")
    if downloaded_size != content_len:
        print(f"ERROR: Size mismatch! Expected {content_len:,} bytes, got {downloaded_size:,} bytes.")
        sys.exit(1)
    
    print("  Calculating SHA-256 of downloaded archive...")
    t_hstart = time.time()
    hasher = hashlib.sha256()
    with open(final_zip_path, "rb") as f_zip:
        while True:
            b_chunk = f_zip.read(16 * 1024 * 1024)
            if not b_chunk:
                break
            hasher.update(b_chunk)
    zip_sha256 = hasher.hexdigest()
    print(f"  Archive SHA-256:    {zip_sha256} (computed in {time.time()-t_hstart:.1f}s)")

    print("  Testing ZIP archive internal CRC32 checksums...")
    with zipfile.ZipFile(final_zip_path, "r") as zf:
        first_bad_file = zf.testzip()
        if first_bad_file is not None:
            print(f"ERROR: Archive corrupted! First bad file: {first_bad_file}")
            sys.exit(1)
        namelist = zf.namelist()
        print(f"  Archive integrity test PASSED: 100% of {len(namelist)} members verified valid CRC32.")

    # 7. Extract and verify B02, B03, B04, B08, B11, B12, and SCL at native resolutions
    print("\n[Step 7] Extracting required spectral bands at native resolutions...")
    # Native specifications:
    # 10m: B02, B03, B04, B08 (from R10m)
    # 20m: B11, B12, SCL (from R20m)
    band_targets = {
        "B02": {"res_group": "R10m", "native_res_m": 10, "expected_shape": (10980, 10980)},
        "B03": {"res_group": "R10m", "native_res_m": 10, "expected_shape": (10980, 10980)},
        "B04": {"res_group": "R10m", "native_res_m": 10, "expected_shape": (10980, 10980)},
        "B08": {"res_group": "R10m", "native_res_m": 10, "expected_shape": (10980, 10980)},
        "B11": {"res_group": "R20m", "native_res_m": 20, "expected_shape": (5490, 5490)},
        "B12": {"res_group": "R20m", "native_res_m": 20, "expected_shape": (5490, 5490)},
        "SCL": {"res_group": "R20m", "native_res_m": 20, "expected_shape": (5490, 5490)},
    }

    extracted_records = {}

    with zipfile.ZipFile(final_zip_path, "r") as zf:
        namelist = zf.namelist()
        
        for band_code, spec in band_targets.items():
            res_group = spec["res_group"]
            # Look for member containing res_group and band_code
            matching_members = [
                m for m in namelist
                if res_group in m and (
                    f"_{band_code}_" in m or f"_{band_code}." in m or m.endswith(f"_{band_code}.jp2") or m.endswith(f"_{band_code}.tif")
                )
            ]
            if not matching_members:
                # Fallback search
                matching_members = [
                    m for m in namelist
                    if (f"_{band_code}_10m" in m or f"_{band_code}_20m" in m or f"_{band_code}." in m)
                ]

            if not matching_members:
                print(f"ERROR: Could not locate native band {band_code} ({res_group}) in archive.")
                sys.exit(1)

            chosen_member = matching_members[0]
            print(f"  Found {band_code} ({res_group}): {chosen_member}")
            
            # Extract to temporary native file
            ext = os.path.splitext(chosen_member)[1].lower()
            tmp_native_path = os.path.join(dest_scene_dir, f"{target_scene_name}_{band_code}_native{ext}")
            with zf.open(chosen_member) as src_f, open(tmp_native_path, "wb") as dst_f:
                shutil.copyfileobj(src_f, dst_f)

            # Compute SHA-256 of extracted raw band
            with open(tmp_native_path, "rb") as f_raw:
                raw_sha256 = hashlib.sha256(f_raw.read()).hexdigest()

            # Read with rasterio and verify native resolution, shape, CRS
            with rasterio.open(tmp_native_path) as src_r:
                arr = src_r.read(1)
                crs = str(src_r.crs)
                transform = src_r.transform
                res_x, res_y = abs(transform[0]), abs(transform[4])
                width, height = src_r.width, src_r.height
                dtype_name = str(src_r.dtypes[0])

            print(f"    Verification for {band_code}:")
            print(f"      Dimensions:   {width} x {height} (expected {spec['expected_shape'][1]} x {spec['expected_shape'][0]})")
            print(f"      Resolution:   {res_x:.1f}m x {res_y:.1f}m (expected {spec['native_res_m']}m)")
            print(f"      CRS:          {crs}")
            print(f"      Data Type:    {dtype_name}")
            print(f"      Value Range:  min={np.nanmin(arr)}, max={np.nanmax(arr)}, mean={np.nanmean(arr):.2f}")
            print(f"      Raw SHA-256:  {raw_sha256}")

            assert width == spec["expected_shape"][1] and height == spec["expected_shape"][0], f"Dimension mismatch for {band_code}"
            assert abs(res_x - spec["native_res_m"]) < 0.1, f"Resolution mismatch for {band_code}"
            assert "32645" in crs or "UTM zone 45N" in crs, f"CRS mismatch for {band_code} ({crs})"

            # Now create a standard GeoTIFF (.tif) with standard tags for compatibility with GeoTIFFRasterReader
            final_tif_path = os.path.join(dest_scene_dir, f"{target_scene_name}_{band_code}.tif")
            tif_profile = {
                "driver": "GTiff",
                "height": height,
                "width": width,
                "count": 1,
                "dtype": dtype_name,
                "crs": crs,
                "transform": transform,
                "compress": "deflate",
                "nodata": 0
            }
            with rasterio.open(final_tif_path, "w", **tif_profile) as dst_tif:
                dst_tif.write(arr, 1)

            # Checksum of final geotiff
            with open(final_tif_path, "rb") as f_tif:
                tif_sha256 = hashlib.sha256(f_tif.read()).hexdigest()

            # Clean up tmp_native_path
            if os.path.exists(tmp_native_path):
                os.remove(tmp_native_path)

            extracted_records[band_code] = {
                "archive_member": chosen_member,
                "native_resolution_m": spec["native_res_m"],
                "width": width,
                "height": height,
                "crs": crs,
                "transform": [transform[i] for i in range(6)],
                "dtype": dtype_name,
                "geotiff_path": final_tif_path,
                "geotiff_sha256": tif_sha256,
                "min": float(np.nanmin(arr)),
                "max": float(np.nanmax(arr)),
                "mean": float(np.nanmean(arr))
            }

    print("\n  All 7 spectral bands successfully extracted, verified, and saved as GeoTIFFs.")

    # 8. Record provenance and compute valid pixels, cloud/shadow masking, and spectral ratios
    print("\n[Step 8] Processing valid pixels around Noamundi (22.15°N, 85.50°E, radius 10.0 km)...")
    lat, lon, radius_km = 22.15, 85.50, 10.0
    zone, easting, northing = wgs84_to_utm(lat, lon, zone=45)
    radius_m = radius_km * 1000.0
    grid_size = 128 # 128x128 pixel extraction window

    print(f"  Query Location: Lat {lat:.4f}°N, Lon {lon:.4f}°E")
    print(f"  UTM Zone {zone}N Coordinates: Easting={easting:.1f}m, Northing={northing:.1f}m")
    print(f"  Exploration Radius: {radius_km} km ({radius_m:.1f} m)")

    # Read window arrays for all bands using rasterio for exact georeferencing
    band_cubes_window = {}
    
    # Calculate bounding box in UTM
    min_x = easting - radius_m
    max_x = easting + radius_m
    min_y = northing - radius_m
    max_y = northing + radius_m

    for band_code, rec in extracted_records.items():
        tif_path = rec["geotiff_path"]
        with rasterio.open(tif_path) as r_src:
            # Window in pixel coordinates
            inv_trans = ~r_src.transform
            col_min, row_max = inv_trans * (min_x, min_y)
            col_max, row_min = inv_trans * (max_x, max_y)

            c_start = int(max(0, min(r_src.width - 1, np.floor(col_min))))
            c_end = int(max(1, min(r_src.width, np.ceil(col_max))))
            r_start = int(max(0, min(r_src.height - 1, np.floor(row_min))))
            r_end = int(max(1, min(r_src.height, np.ceil(row_max))))

            window = rasterio.windows.Window(c_start, r_start, c_end - c_start, r_end - r_start)
            # Read and resample to common grid_size x grid_size
            data = r_src.read(
                1,
                window=window,
                out_shape=(grid_size, grid_size),
                resampling=Resampling.bilinear if band_code != "SCL" else Resampling.nearest
            ).astype(np.float32)

            if band_code == "SCL":
                band_cubes_window["SCL"] = data.astype(np.uint8)
            else:
                # BOA scaling: DN / 10000.0
                band_cubes_window[band_code] = np.clip(data / 10000.0, 0.0, 1.0)

    # Compute masks
    y_idx, x_idx = np.ogrid[:grid_size, :grid_size]
    cx = grid_size / 2.0
    cy = grid_size / 2.0
    circle_mask = ((x_idx - cx)**2 + (y_idx - cy)**2) <= (grid_size / 2.0)**2

    total_pixels_in_radius = int(np.sum(circle_mask))
    
    # SCL Masking: exclude NoData (0), Cloud Shadow (3), Cloud Med (8), Cloud High (9), Cirrus (10), Snow (11)
    scl_arr = band_cubes_window["SCL"]
    nodata_mask = (scl_arr == SCL_NO_DATA) & circle_mask
    cloud_shadow_mask = (scl_arr == SCL_CLOUD_SHADOW) & circle_mask
    cloud_mask = np.isin(scl_arr, [SCL_CLOUD_MEDIUM_PROB, SCL_CLOUD_HIGH_PROB, SCL_THIN_CIRRUS]) & circle_mask
    snow_mask = (scl_arr == SCL_SNOW_ICE) & circle_mask

    masked_pixels_total = nodata_mask | cloud_shadow_mask | cloud_mask | snow_mask
    valid_pixels_mask = circle_mask & (~masked_pixels_total)

    nodata_count = int(np.sum(nodata_mask))
    cloud_shadow_count = int(np.sum(cloud_shadow_mask))
    cloud_count = int(np.sum(cloud_mask))
    valid_count = int(np.sum(valid_pixels_mask))
    cloud_shadow_pct = round(((cloud_count + cloud_shadow_count) / max(1, total_pixels_in_radius)) * 100.0, 2)

    print(f"  Pixel Accounting:")
    print(f"    Total Pixels in Exploration Circle: {total_pixels_in_radius}")
    print(f"    Valid Cloud-Free Pixels:           {valid_count} ({round(valid_count/total_pixels_in_radius*100, 1)}%)")
    print(f"    Cloud Pixels Masked:               {cloud_count}")
    print(f"    Cloud Shadow Pixels Masked:        {cloud_shadow_count}")
    print(f"    NoData Pixels:                     {nodata_count}")
    print(f"    Total Cloud/Shadow Masking:        {cloud_shadow_pct}%")

    # Compute Iron Ore spectral indices
    spectral_res = process_spectral_indices_for_mineral("iron_ore", band_cubes_window, valid_pixels_mask)

    print("\n  Iron Ore Spectral Analysis Results:")
    print(f"    Band Center Reflectances: {spectral_res.get('band_center_reflectances')}")
    for idx_info in spectral_res.get("indices", []):
        print(f"    Index: {idx_info['index_name']}")
        print(f"      Formula:     {idx_info['formula']}")
        print(f"      Mean Value:  {idx_info['value']}")
        print(f"      Significance: {idx_info['significance']}")
        stats = idx_info.get("statistics", {})
        print(f"      Distribution: min={stats.get('min')}, median={stats.get('median')}, max={stats.get('max')}, std={stats.get('std')}")

    # Build Complete Provenance Record
    provenance_record = {
        "schema_version": "2.0.0",
        "provenance_type": "AUTHENTIC_REMOTE_CDSE_INGESTION",
        "execution_timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "target_location": {
            "name": "Noamundi Iron Belt, Jharkhand",
            "lat": lat,
            "lon": lon,
            "radius_km": radius_km,
            "utm_zone": zone,
            "center_easting": easting,
            "center_northing": northing
        },
        "satellite_product": {
            "uuid": target_uuid,
            "scene_name": target_scene_name,
            "platform": "Sentinel-2A",
            "instrument": "MSI",
            "processing_level": "Level-2A (Surface Reflectance)",
            "tile_id": "T45QUE",
            "acquisition_date": acq_date,
            "catalogue_cloud_cover_pct": cloud_cover,
            "archive_size_bytes": downloaded_size,
            "archive_sha256": zip_sha256,
            "cdse_download_url": f"https://download.dataspace.copernicus.eu/odata/v1/Products({target_uuid})/$value"
        },
        "extracted_bands": extracted_records,
        "pixel_processing": {
            "window_grid_size": [grid_size, grid_size],
            "total_pixels_in_circle": total_pixels_in_radius,
            "valid_cloud_free_pixels": valid_count,
            "cloud_pixels_masked": cloud_count,
            "cloud_shadow_pixels_masked": cloud_shadow_count,
            "nodata_pixels": nodata_count,
            "cloud_shadow_masking_pct": cloud_shadow_pct,
            "band_center_reflectances": spectral_res.get("band_center_reflectances"),
            "spectral_indices": spectral_res.get("indices")
        },
        "prediction_status": {
            "commodity": "Iron Ore",
            "prediction_availability": "UNAVAILABLE_NO_MODEL",
            "prediction_score": None,
            "confidence_score": None,
            "scientific_guardrail": spectral_res.get("scientific_guardrail"),
            "policy_statement": (
                "Iron Ore AI prospectivity predictions are withheld. "
                "In strict accordance with Phase 8 scientific integrity contracts, "
                "no AI prospectivity score may be output until an independent spatial model "
                "for Iron Ore is formally validated on external deposits."
            )
        }
    }

    # Save provenance in scene directory
    prov_file = os.path.join(dest_scene_dir, "provenance_manifest.json")
    with open(prov_file, "w") as f_prov:
        json.dump(provenance_record, f_prov, indent=2)
    print(f"\n  Provenance manifest written to: {prov_file}")

    # Also update processed cache so backend API immediately benefits
    cache_key = hashlib.sha256(
        f"{round(lat, 3)}_{round(lon, 3)}_{round(radius_km, 1)}_iron_ore".encode("utf-8")
    ).hexdigest()[:16]
    proc_cache_file = os.path.join(processed_dir, f"proc_{cache_key}.json")
    with open(proc_cache_file, "w") as f_proc:
        json.dump({
            "status": "COMPLETED",
            "raster_pixels_processed": True,
            "pixel_processing_status": "COMPLETED_GENUINE_RASTER",
            "data_access_status": "ACCESSED_AUTHENTIC_LOCAL_RASTER",
            "satellite_scene": target_scene_name,
            "tile_info": {
                "primary_tile": "T45QUE",
                "utm_zone": zone,
                "center_easting": easting,
                "center_northing": northing
            },
            "cloud_cover_pct": cloud_shadow_pct,
            "valid_pixels": valid_count,
            "total_pixels_in_radius": total_pixels_in_radius,
            "band_reflectances": spectral_res.get("band_center_reflectances"),
            "mineral_spectral_indices": spectral_res.get("indices"),
            "scientific_guardrail": spectral_res.get("scientific_guardrail"),
            "provenance": {
                "source_type": "AUTHENTIC_CDSE_REMOTE_INGESTION",
                "archive_sha256": zip_sha256,
                "scene_name": target_scene_name,
                "product_uuid": target_uuid,
                "crs": f"EPSG:326{zone}",
                "resolution_m": 10,
                "bands_verified": list(extracted_records.keys()),
                "checksums": {k: v["geotiff_sha256"] for k, v in extracted_records.items()},
                "nodata_value": 0.0
            }
        }, f_proc, indent=2)
    print(f"  Processed cache written to: {proc_cache_file}")

    # 9. Clean up temporary files only after successful verification
    print("\n[Step 9] Cleaning up temporary files after successful verification...")
    if os.path.exists(final_zip_path):
        os.remove(final_zip_path)
        print(f"  Removed temporary archive: {final_zip_path}")
    if os.path.exists(tmp_zip_path):
        os.remove(tmp_zip_path)
    print("  Temporary files cleaned up. Verified outputs preserved in cache.")

    # 10. Summary verification of prediction withholding
    print("\n[Step 10] Checking Iron Ore prospectivity prediction withholding...")
    print(f"  Prediction Availability: {provenance_record['prediction_status']['prediction_availability']}")
    print(f"  Prediction Score:        {provenance_record['prediction_status']['prediction_score']}")
    print(f"  Scientific Guardrail:    {provenance_record['prediction_status']['scientific_guardrail']}")
    print("\n" + "=" * 80)
    print("NOAMUNDI INGESTION & VERIFICATION PIPELINE FINISHED SUCCESSFULLY")
    print("=" * 80)

if __name__ == "__main__":
    main()
