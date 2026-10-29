"""
Phase 1 Independent Verification Script for Noamundi Sentinel-2 GeoTIFFs and Processing
"""

import os
import sys
import json
import hashlib
import numpy as np
import rasterio
from rasterio.enums import Resampling

APP_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "backend", "app")
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if APP_DIR not in sys.path:
    sys.path.insert(0, APP_DIR)

from raster_ingestion_service import (
    wgs84_to_utm,
    utm_to_wgs84,
    process_spectral_indices_for_mineral,
    MASKED_SCL_CLASSES,
    SCL_NO_DATA,
    SCL_SATURATED,
    SCL_DARK_FEATURE,
    SCL_CLOUD_SHADOW,
    SCL_VEGETATION,
    SCL_BARE_SOIL,
    SCL_WATER,
    SCL_UNCLASSIFIED,
    SCL_CLOUD_MEDIUM_PROB,
    SCL_CLOUD_HIGH_PROB,
    SCL_THIN_CIRRUS,
    SCL_SNOW_ICE,
)

scene_name = "S2A_MSIL2A_20261010T045231_N0513_R076_T45QUE_20261010T095406"
scene_dir = os.path.join(PROJECT_ROOT, "data", "cache", "sentinel2", scene_name)
prov_file = os.path.join(scene_dir, "provenance_manifest.json")
proc_file = os.path.join(PROJECT_ROOT, "data", "cache", "processed", "proc_bf888c33e2340e26.json")

print("=" * 80)
print("PHASE 1: INDEPENDENT VERIFICATION OF ACTUAL OUTPUTS")
print("=" * 80)

# 1 & 2: Inspect GeoTIFFs, CRS, transforms, dimensions, resolutions, data types, nodata
bands = ["B02", "B03", "B04", "B08", "B11", "B12", "SCL"]
expected_specs = {
    "B02": {"res": 10.0, "dim": (10980, 10980), "dtype": "uint16"},
    "B03": {"res": 10.0, "dim": (10980, 10980), "dtype": "uint16"},
    "B04": {"res": 10.0, "dim": (10980, 10980), "dtype": "uint16"},
    "B08": {"res": 10.0, "dim": (10980, 10980), "dtype": "uint16"},
    "B11": {"res": 20.0, "dim": (5490, 5490), "dtype": "uint16"},
    "B12": {"res": 20.0, "dim": (5490, 5490), "dtype": "uint16"},
    "SCL": {"res": 20.0, "dim": (5490, 5490), "dtype": "uint8"},
}

computed_checksums = {}
band_meta = {}

print("\n--- 1 & 2. GeoTIFF Files Inspection & Spatial Properties ---")
for b in bands:
    fname = f"{scene_name}_{b}.tif"
    fpath = os.path.join(scene_dir, fname)
    exists = os.path.exists(fpath)
    size_bytes = os.path.getsize(fpath) if exists else 0
    print(f"\nBand {b}:")
    print(f"  File: {fname}")
    print(f"  Exists: {exists}")
    print(f"  Size on disk: {size_bytes:,} bytes ({size_bytes / (1024**2):.2f} MB)")
    
    if not exists:
        print(f"  ERROR: {fname} missing!")
        continue

    # 3. Compute SHA-256
    hasher = hashlib.sha256()
    with open(fpath, "rb") as f:
        while chunk := f.read(16 * 1024 * 1024):
            hasher.update(chunk)
    sha256 = hasher.hexdigest()
    computed_checksums[b] = sha256
    print(f"  SHA-256: {sha256}")

    # Inspect raster metadata using rasterio
    with rasterio.open(fpath) as src:
        crs = src.crs.to_string()
        w, h = src.width, src.height
        bounds = src.bounds
        trans = src.transform
        res_x = abs(trans[0])
        res_y = abs(trans[4])
        dtype = str(src.dtypes[0])
        nodata = src.nodata
        band_count = src.count
        
        # Read a sample to inspect min/max/mean and nodata presence
        data_sample = src.read(1)
        valid_pixel_mask = (data_sample != nodata) if nodata is not None else np.ones_like(data_sample, dtype=bool)
        val_min = int(np.min(data_sample[valid_pixel_mask])) if np.any(valid_pixel_mask) else None
        val_max = int(np.max(data_sample[valid_pixel_mask])) if np.any(valid_pixel_mask) else None
        val_mean = float(np.mean(data_sample[valid_pixel_mask])) if np.any(valid_pixel_mask) else None

        band_meta[b] = {
            "crs": crs,
            "width": w,
            "height": h,
            "res_x": res_x,
            "res_y": res_y,
            "transform": [trans[i] for i in range(6)],
            "bounds": [bounds.left, bounds.bottom, bounds.right, bounds.top],
            "dtype": dtype,
            "nodata": nodata,
            "count": band_count,
            "min": val_min,
            "max": val_max,
            "mean": val_mean,
            "sha256": sha256
        }
        
        print(f"  CRS: {crs}")
        print(f"  Dimensions: {w} cols x {h} rows (Expected {expected_specs[b]['dim'][1]}x{expected_specs[b]['dim'][0]})")
        print(f"  Resolution: {res_x:.1f}m x {res_y:.1f}m (Expected {expected_specs[b]['res']}m)")
        print(f"  Geotransform: origin=({trans[2]:.1f}, {trans[5]:.1f}), pixel_size=({trans[0]:.1f}, {trans[4]:.1f})")
        print(f"  Bounds: left={bounds.left:.1f}, bottom={bounds.bottom:.1f}, right={bounds.right:.1f}, top={bounds.top:.1f}")
        print(f"  Data type: {dtype} (Expected {expected_specs[b]['dtype']})")
        print(f"  NoData value: {nodata}")
        print(f"  Value range: min={val_min}, max={val_max}, mean={val_mean:.2f}")

# 4. Inspect provenance_manifest.json and proc_bf888c33e2340e26.json
print("\n--- 4. Inspect Provenance Manifest & Processed Cache ---")
with open(prov_file, "r") as f:
    prov_data = json.load(f)

print(f"Provenance Manifest: {prov_file}")
print(f"  Schema version: {prov_data.get('schema_version')}")
print(f"  Provenance type: {prov_data.get('provenance_type')}")
print(f"  Execution timestamp UTC: {prov_data.get('execution_timestamp_utc')}")
print(f"  Product UUID: {prov_data.get('satellite_product', {}).get('uuid')}")
print(f"  Archive SHA-256: {prov_data.get('satellite_product', {}).get('archive_sha256')}")
print(f"  Archive Size Bytes: {prov_data.get('satellite_product', {}).get('archive_size_bytes')}")

print("\nVerifying Checksum Consistency against provenance_manifest.json:")
for b in bands:
    manifest_sha = prov_data.get("extracted_bands", {}).get(b, {}).get("geotiff_sha256")
    actual_sha = computed_checksums.get(b)
    matches = (manifest_sha == actual_sha)
    print(f"  Band {b}: {'MATCH' if matches else 'MISMATCH'}")
    if not matches:
        print(f"    Manifest: {manifest_sha}")
        print(f"    Actual:   {actual_sha}")

with open(proc_file, "r") as f:
    proc_data = json.load(f)

print(f"\nProcessed Cache: {proc_file}")
print(f"  Status: {proc_data.get('status')}")
print(f"  Data Access: {proc_data.get('data_access_status')}")
print(f"  Satellite Scene: {proc_data.get('satellite_scene')}")
print(f"  Cloud Cover %: {proc_data.get('cloud_cover_pct')}")
print(f"  Valid Pixels: {proc_data.get('valid_pixels')} / {proc_data.get('total_pixels_in_radius')}")

# 5 & 6. Recompute target-window pixel accounting, SCL class breakdown, and spectral indices
print("\n--- 5, 6 & 7. Recompute Window Pixel Accounting, SCL Masking & Spectral Ratios ---")
lat = 22.1500
lon = 85.5000
radius_km = 10.0
zone, easting, northing = wgs84_to_utm(lat, lon, zone=45)
radius_m = radius_km * 1000.0
grid_size = 128

min_x = easting - radius_m
max_x = easting + radius_m
min_y = northing - radius_m
max_y = northing + radius_m

print(f"Center Coordinate: {lat:.4f}°N, {lon:.4f}°E")
print(f"UTM Zone {zone}N: Easting {easting:.2f} m, Northing {northing:.2f} m")
print(f"Exploration Radius: {radius_km} km ({radius_m} m)")
print(f"Spatial Bounding Box: [{min_x:.1f}, {min_y:.1f}, {max_x:.1f}, {max_y:.1f}]")

band_cubes = {}
for b in bands:
    fpath = os.path.join(scene_dir, f"{scene_name}_{b}.tif")
    with rasterio.open(fpath) as src:
        inv_trans = ~src.transform
        col_min, row_max = inv_trans * (min_x, min_y)
        col_max, row_min = inv_trans * (max_x, max_y)
        c_start = int(max(0, min(src.width - 1, np.floor(col_min))))
        c_end = int(max(1, min(src.width, np.ceil(col_max))))
        r_start = int(max(0, min(src.height - 1, np.floor(row_min))))
        r_end = int(max(1, min(src.height, np.ceil(row_max))))
        window = rasterio.windows.Window(c_start, r_start, c_end - c_start, r_end - r_start)
        
        # SCL nearest neighbor; spectral bands bilinear
        r_method = Resampling.nearest if b == "SCL" else Resampling.bilinear
        data = src.read(1, window=window, out_shape=(grid_size, grid_size), resampling=r_method).astype(np.float32)
        if b == "SCL":
            band_cubes[b] = data.astype(np.uint8)
        else:
            # BOA Surface Reflectance scale factor: DN / 10000.0 (per Copernicus Sentinel-2 L2A Product Specification)
            band_cubes[b] = np.clip(data / 10000.0, 0.0, 1.0)

# Circular mask
y_idx, x_idx = np.ogrid[:grid_size, :grid_size]
cx, cy = grid_size / 2.0, grid_size / 2.0
circle_mask = ((x_idx - cx)**2 + (y_idx - cy)**2) <= (grid_size / 2.0)**2
total_pixels_circle = int(np.sum(circle_mask))

# Detailed SCL breakdown
scl = band_cubes["SCL"]
scl_circle = scl[circle_mask]

scl_class_names = {
    0: "No Data",
    1: "Saturated / Defective",
    2: "Dark Area Pixels",
    3: "Cloud Shadows",
    4: "Vegetation",
    5: "Not-Vegetated / Bare Soil",
    6: "Water",
    7: "Unclassified",
    8: "Cloud Medium Probability",
    9: "Cloud High Probability",
    10: "Thin Cirrus",
    11: "Snow / Ice"
}

print("\nSCL (Scene Classification Layer) Class Breakdown in Exploration Circle:")
class_counts = {}
for code, name in scl_class_names.items():
    cnt = int(np.sum(scl_circle == code))
    pct = (cnt / total_pixels_circle) * 100.0
    class_counts[code] = cnt
    if cnt > 0:
        print(f"  Code {code:2d} ({name:26s}): {cnt:5d} pixels ({pct:5.2f}%)")

# Masking logic
nodata_mask = (scl == SCL_NO_DATA) & circle_mask
cloud_shadow_mask = (scl == SCL_CLOUD_SHADOW) & circle_mask
cloud_med_mask = (scl == SCL_CLOUD_MEDIUM_PROB) & circle_mask
cloud_high_mask = (scl == SCL_CLOUD_HIGH_PROB) & circle_mask
cirrus_mask = (scl == SCL_THIN_CIRRUS) & circle_mask
snow_mask = (scl == SCL_SNOW_ICE) & circle_mask

all_cloud_mask = cloud_med_mask | cloud_high_mask | cirrus_mask
all_masked = nodata_mask | cloud_shadow_mask | all_cloud_mask | snow_mask
valid_mask = circle_mask & (~all_masked)

nodata_cnt = int(np.sum(nodata_mask))
cloud_shadow_cnt = int(np.sum(cloud_shadow_mask))
cloud_cnt = int(np.sum(all_cloud_mask))
snow_cnt = int(np.sum(snow_mask))
valid_cnt = int(np.sum(valid_mask))
cloud_shadow_pct = ((cloud_cnt + cloud_shadow_cnt) / total_pixels_circle) * 100.0

print(f"\nPixel Accounting Totals:")
print(f"  Total Pixels in Exploration Circle: {total_pixels_circle}")
print(f"  Valid Cloud-Free Pixels:           {valid_cnt:5d} ({valid_cnt / total_pixels_circle * 100:.2f}%)")
print(f"  Cloud Pixels Masked:               {cloud_cnt:5d} ({cloud_cnt / total_pixels_circle * 100:.2f}%)")
print(f"    - Medium Probability:            {int(np.sum(cloud_med_mask)):5d}")
print(f"    - High Probability:              {int(np.sum(cloud_high_mask)):5d}")
print(f"    - Thin Cirrus:                   {int(np.sum(cirrus_mask)):5d}")
print(f"  Cloud Shadow Pixels Masked:        {cloud_shadow_cnt:5d} ({cloud_shadow_cnt / total_pixels_circle * 100:.2f}%)")
print(f"  Snow / Ice Pixels Masked:          {snow_cnt:5d} ({snow_cnt / total_pixels_circle * 100:.2f}%)")
print(f"  NoData Pixels:                     {nodata_cnt:5d} ({nodata_cnt / total_pixels_circle * 100:.2f}%)")
print(f"  Combined Cloud + Shadow Mask:      {cloud_shadow_pct:.2f}%")

# Spatial distribution of valid pixels: quadrant analysis
print("\nSpatial Distribution of Valid Cloud-Free Pixels by Quadrant:")
center_row, center_col = grid_size // 2, grid_size // 2
nw_mask = valid_mask[:center_row, :center_col]
ne_mask = valid_mask[:center_row, center_col:]
sw_mask = valid_mask[center_row:, :center_col]
se_mask = valid_mask[center_row:, center_col:]

nw_circ = circle_mask[:center_row, :center_col]
ne_circ = circle_mask[:center_row, center_col:]
sw_circ = circle_mask[center_row:, :center_col]
se_circ = circle_mask[center_row:, center_col:]

print(f"  North-West (NW): {np.sum(nw_mask):4d} / {np.sum(nw_circ):4d} valid ({np.sum(nw_mask)/np.sum(nw_circ)*100:.1f}%)")
print(f"  North-East (NE): {np.sum(ne_mask):4d} / {np.sum(ne_circ):4d} valid ({np.sum(ne_mask)/np.sum(ne_circ)*100:.1f}%)")
print(f"  South-West (SW): {np.sum(sw_mask):4d} / {np.sum(sw_circ):4d} valid ({np.sum(sw_mask)/np.sum(sw_circ)*100:.1f}%)")
print(f"  South-East (SE): {np.sum(se_mask):4d} / {np.sum(se_circ):4d} valid ({np.sum(se_mask)/np.sum(se_circ)*100:.1f}%)")

# Spectral index computation and verification
print("\nSpectral Index Calculations on Valid Pixels:")
b02 = band_cubes["B02"]
b03 = band_cubes["B03"]
b04 = band_cubes["B04"]
b08 = band_cubes["B08"]
b11 = band_cubes["B11"]
b12 = band_cubes["B12"]

eps = 1e-6
# Ferric Iron Oxide Ratio: B04 / B02 (Red / Blue)
fe_ratio = np.where(valid_mask & (b02 > eps), b04 / b02, np.nan)
fe_vals = fe_ratio[~np.isnan(fe_ratio)]

# Ferrous Minerals Ratio: B11 / B08 (SWIR1 / NIR)
ferrous_ratio = np.where(valid_mask & (b08 > eps), b11 / b08, np.nan)
ferrous_vals = ferrous_ratio[~np.isnan(ferrous_ratio)]

# Al-OH Clay / Alteration Ratio: B11 / B12 (SWIR1 / SWIR2)
clay_ratio = np.where(valid_mask & (b12 > eps), b11 / b12, np.nan)
clay_vals = clay_ratio[~np.isnan(clay_ratio)]

# NDVI: (B08 - B04) / (B08 + B04)
sum_nir_red = b08 + b04
ndvi = np.where(valid_mask & (sum_nir_red > eps), (b08 - b04) / sum_nir_red, np.nan)
ndvi_vals = ndvi[~np.isnan(ndvi)]

print(f"\n1. Ferric Iron (Fe3+) Oxide Ratio (B04/B02):")
print(f"   Formula: B04 / B02 (Red: ~665 nm / Blue: ~490 nm)")
print(f"   Target: Hematite / Goethite absorption and gossan capping")
print(f"   Sample count: {len(fe_vals)}")
print(f"   Mean: {np.mean(fe_vals):.4f}")
print(f"   Median: {np.median(fe_vals):.4f}")
print(f"   Std: {np.std(fe_vals):.4f}")
print(f"   Min: {np.min(fe_vals):.4f}")
print(f"   Max: {np.max(fe_vals):.4f}")
print(f"   P25: {np.percentile(fe_vals, 25):.4f}, P75: {np.percentile(fe_vals, 75):.4f}, P90: {np.percentile(fe_vals, 90):.4f}")

print(f"\n2. Ferrous Iron (Fe2+) Silicate Ratio (B11/B08):")
print(f"   Formula: B11 / B08 (SWIR1: ~1610 nm / NIR: ~842 nm)")
print(f"   Target: Silicates / Country rocks in Banded Iron Formations (BIF)")
print(f"   Sample count: {len(ferrous_vals)}")
print(f"   Mean: {np.mean(ferrous_vals):.4f}")
print(f"   Median: {np.median(ferrous_vals):.4f}")
print(f"   Std: {np.std(ferrous_vals):.4f}")
print(f"   Min: {np.min(ferrous_vals):.4f}")
print(f"   Max: {np.max(ferrous_vals):.4f}")
print(f"   P25: {np.percentile(ferrous_vals, 25):.4f}, P75: {np.percentile(ferrous_vals, 75):.4f}, P90: {np.percentile(ferrous_vals, 90):.4f}")

print(f"\n3. Al-OH Clay Alteration Ratio (B11/B12):")
print(f"   Formula: B11 / B12 (SWIR1: ~1610 nm / SWIR2: ~2190 nm)")
print(f"   Sample count: {len(clay_vals)}")
print(f"   Mean: {np.mean(clay_vals):.4f}")
print(f"   Median: {np.median(clay_vals):.4f}")
print(f"   Std: {np.std(clay_vals):.4f}")

print(f"\n4. Normalized Difference Vegetation Index (NDVI):")
print(f"   Formula: (B08 - B04) / (B08 + B04)")
print(f"   Sample count: {len(ndvi_vals)}")
print(f"   Mean: {np.mean(ndvi_vals):.4f}")
print(f"   Median: {np.median(ndvi_vals):.4f}")
print(f"   Min: {np.min(ndvi_vals):.4f}")
print(f"   Max: {np.max(ndvi_vals):.4f}")

print("\n" + "=" * 80)
print("PHASE 1 VERIFICATION COMPLETE")
print("=" * 80)
