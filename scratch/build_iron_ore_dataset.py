import os
import sys
import json
import math
import rasterio
from rasterio.windows import Window
from rasterio.enums import Resampling
import numpy as np
import csv

APP_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "backend", "app")
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if APP_DIR not in sys.path:
    sys.path.insert(0, APP_DIR)

from raster_ingestion_service import wgs84_to_utm, utm_to_wgs84

geotiff_dir = os.path.join(PROJECT_ROOT, "data", "cache", "sentinel2", "S2A_MSIL2A_20261010T045231_N0513_R076_T45QUE_20261010T095406")

band_files = {
    "B02": os.path.join(geotiff_dir, "S2A_MSIL2A_20261010T045231_N0513_R076_T45QUE_20261010T095406_B02.tif"),
    "B03": os.path.join(geotiff_dir, "S2A_MSIL2A_20261010T045231_N0513_R076_T45QUE_20261010T095406_B03.tif"),
    "B04": os.path.join(geotiff_dir, "S2A_MSIL2A_20261010T045231_N0513_R076_T45QUE_20261010T095406_B04.tif"),
    "B08": os.path.join(geotiff_dir, "S2A_MSIL2A_20261010T045231_N0513_R076_T45QUE_20261010T095406_B08.tif"),
    "B11": os.path.join(geotiff_dir, "S2A_MSIL2A_20261010T045231_N0513_R076_T45QUE_20261010T095406_B11.tif"),
    "B12": os.path.join(geotiff_dir, "S2A_MSIL2A_20261010T045231_N0513_R076_T45QUE_20261010T095406_B12.tif"),
    "SCL": os.path.join(geotiff_dir, "S2A_MSIL2A_20261010T045231_N0513_R076_T45QUE_20261010T095406_SCL.tif"),
}

# 1. Authoritative Positive Occurrences in Singhbhum-North Odisha (Tile T45QUE)
positive_deposits = [
    {
        "deposit_id": "kiriburu",
        "name": "Kiriburu Iron Mine",
        "operator": "Steel Authority of India Limited (SAIL)",
        "lat": 22.0900, "lon": 85.3400,
        "radius_m": 800,
        "source": "GSI Quadrangle Sheet 73F/8 / SAIL Lease Baseline",
        "geological_formation": "Banded Hematite Jasper / IOG Massive Hematite"
    },
    {
        "deposit_id": "gua",
        "name": "Gua Iron Ore Mine",
        "operator": "SAIL IISCO Steel Plant Division",
        "lat": 22.2100, "lon": 85.3800,
        "radius_m": 800,
        "source": "GSI Memoir Vol. 112 / SAIL Mining Lease Atlas",
        "geological_formation": "Banded Hematite Jasper / Blue Dust & Hard Ore"
    },
    {
        "deposit_id": "bolani",
        "name": "Bolani Iron Ore Mine",
        "operator": "SAIL Raw Materials Division",
        "lat": 22.1000, "lon": 85.3100,
        "radius_m": 800,
        "source": "IBM National Mineral Inventory (2023) / GSI Memoir",
        "geological_formation": "Iron Ore Group Synclinorium Crest"
    },
    {
        "deposit_id": "noamundi",
        "name": "Noamundi Iron Ore Mine",
        "operator": "Tata Steel Limited",
        "lat": 22.1500, "lon": 85.5000,
        "radius_m": 1200,
        "source": "GSI Memoir Vol. 112 / IBM Indian Mineral Year Book",
        "geological_formation": "Banded Hematite Jasper (BHJ) / Laminated Hematite"
    },
    {
        "deposit_id": "joda_east",
        "name": "Joda East Iron Mine",
        "operator": "Tata Steel Limited",
        "lat": 22.0200, "lon": 85.4300,
        "radius_m": 1000,
        "source": "IBM Mining Lease Atlas / Odisha DGM Records",
        "geological_formation": "Banded Hematite Jasper (BHJ) / Supergene Ore"
    }
]

# 2. Defensible Background Reference Sectors (Singhbhum Granite Batholith & Non-IOG Basins)
# Strictly unmineralized Archean TTG granites and Quaternary alluvium
background_sectors = [
    {
        "sector_id": "singhbhum_granite_central",
        "name": "Singhbhum Granite Batholith (Champua North)",
        "lat": 22.1200, "lon": 85.7200,
        "radius_m": 2500,
        "source": "GSI Memoir Vol. 114 (Archean Granite Crystalline Basement)",
        "geological_formation": "Singhbhum Granite Phase II (Unaltered TTG Suite)"
    },
    {
        "sector_id": "singhbhum_granite_south",
        "name": "Singhbhum Granite Batholith (Karanjia Sector)",
        "lat": 21.9000, "lon": 85.8000,
        "radius_m": 2500,
        "source": "GSI Memoir Vol. 114 (Archean Granite Crystalline Basement)",
        "geological_formation": "Singhbhum Granite Phase III (Coarse Granodiorite)"
    },
    {
        "sector_id": "singhbhum_granite_north",
        "name": "Singhbhum Granite Batholith (Chaibasa South Plains)",
        "lat": 22.4200, "lon": 85.7500,
        "radius_m": 2500,
        "source": "GSI Quadrangle Sheet 73F (Biotite Granite)",
        "geological_formation": "Singhbhum Granite / Alluvial Soil Cover"
    }
]

def extract_samples():
    print("Opening Sentinel-2 L2A GeoTIFFs...")
    srcs = {b: rasterio.open(f) for b, f in band_files.items()}
    scl_src = srcs["SCL"]
    inv_t = ~scl_src.transform
    
    samples = []
    
    # Extract Positives
    print("\n--- EXTRACTING POSITIVE MINE SAMPLES ---")
    for dep in positive_deposits:
        zone, easting, northing = wgs84_to_utm(dep["lat"], dep["lon"], zone=45)
        col_c, row_c = inv_t * (easting, northing)
        col_c, row_c = int(round(col_c)), int(round(row_c))
        radius_px = int(math.ceil(dep["radius_m"] / 20.0))
        
        c_min = max(0, col_c - radius_px)
        c_max = min(scl_src.width, col_c + radius_px + 1)
        r_min = max(0, row_c - radius_px)
        r_max = min(scl_src.height, row_c + radius_px + 1)
        
        win = Window(c_min, r_min, c_max - c_min, r_max - r_min)
        scl_arr = scl_src.read(1, window=win)
        
        # Read all bands on common 20m grid
        band_data = {}
        for b_name, b_src in srcs.items():
            if b_name == "SCL":
                continue
            arr = b_src.read(
                1,
                window=Window(
                    int(c_min * (20.0 / b_src.res[0])),
                    int(r_min * (20.0 / b_src.res[1])),
                    int((c_max - c_min) * (20.0 / b_src.res[0])),
                    int((r_max - r_min) * (20.0 / b_src.res[1]))
                ),
                out_shape=(win.height, win.width),
                resampling=Resampling.bilinear
            )
            band_data[b_name] = np.clip(arr.astype(np.float32) / 10000.0, 0.0, 1.0)
            
        y_idx, x_idx = np.ogrid[:win.height, :win.width]
        dist_px = np.sqrt((x_idx - (col_c - c_min))**2 + (y_idx - (row_c - r_min))**2)
        circle_mask = (dist_px <= radius_px)
        
        valid_mask = np.isin(scl_arr, [4, 5, 7]) & circle_mask
        n_valid = int(np.sum(valid_mask))
        
        print(f"  Deposit {dep['name']}: {n_valid} valid cloud-free pixels in {dep['radius_m']}m radius.")
        
        valid_rows, valid_cols = np.where(valid_mask)
        for r_p, c_p in zip(valid_rows, valid_cols):
            # Compute real coordinates
            abs_col = c_min + c_p
            abs_row = r_min + r_p
            x_utm, y_utm = scl_src.transform * (abs_col + 0.5, abs_row + 0.5)
            p_lat, p_lon = utm_to_wgs84(45, x_utm, y_utm)
            
            b02 = float(band_data["B02"][r_p, c_p])
            b03 = float(band_data["B03"][r_p, c_p])
            b04 = float(band_data["B04"][r_p, c_p])
            b08 = float(band_data["B08"][r_p, c_p])
            b11 = float(band_data["B11"][r_p, c_p])
            b12 = float(band_data["B12"][r_p, c_p])
            
            ndvi = (b08 - b04) / (b08 + b04 + 1e-6)
            ndwi = (b03 - b08) / (b03 + b08 + 1e-6)
            clay = b11 / (b12 + 1e-6)
            fe_ox = b04 / (b02 + 1e-6)
            
            samples.append({
                "deposit_id": dep["deposit_id"],
                "deposit_name": dep["name"],
                "latitude": round(p_lat, 6),
                "longitude": round(p_lon, 6),
                "easting": round(x_utm, 2),
                "northing": round(y_utm, 2),
                "mineral": "iron_ore",
                "label": 1,
                "is_background": 0,
                "formation": dep["geological_formation"],
                "B02": round(b02, 5),
                "B03": round(b03, 5),
                "B04": round(b04, 5),
                "B08": round(b08, 5),
                "B11": round(b11, 5),
                "B12": round(b12, 5),
                "NDVI": round(float(ndvi), 5),
                "NDWI": round(float(ndwi), 5),
                "clay_ratio": round(float(clay), 5),
                "iron_oxide_ratio": round(float(fe_ox), 5)
            })

    # Extract Background Pseudo-Absences
    print("\n--- EXTRACTING BACKGROUND PSEUDO-ABSENCES (Singhbhum Granite Basement) ---")
    np.random.seed(42)
    for sec in background_sectors:
        zone, easting, northing = wgs84_to_utm(sec["lat"], sec["lon"], zone=45)
        col_c, row_c = inv_t * (easting, northing)
        col_c, row_c = int(round(col_c)), int(round(row_c))
        radius_px = int(math.ceil(sec["radius_m"] / 20.0))
        
        c_min = max(0, col_c - radius_px)
        c_max = min(scl_src.width, col_c + radius_px + 1)
        r_min = max(0, row_c - radius_px)
        r_max = min(scl_src.height, row_c + radius_px + 1)
        
        win = Window(c_min, r_min, c_max - c_min, r_max - r_min)
        scl_arr = scl_src.read(1, window=win)
        
        band_data = {}
        for b_name, b_src in srcs.items():
            if b_name == "SCL":
                continue
            arr = b_src.read(
                1,
                window=Window(
                    int(c_min * (20.0 / b_src.res[0])),
                    int(r_min * (20.0 / b_src.res[1])),
                    int((c_max - c_min) * (20.0 / b_src.res[0])),
                    int((r_max - r_min) * (20.0 / b_src.res[1]))
                ),
                out_shape=(win.height, win.width),
                resampling=Resampling.bilinear
            )
            band_data[b_name] = np.clip(arr.astype(np.float32) / 10000.0, 0.0, 1.0)
            
        y_idx, x_idx = np.ogrid[:win.height, :win.width]
        dist_px = np.sqrt((x_idx - (col_c - c_min))**2 + (y_idx - (row_c - r_min))**2)
        circle_mask = (dist_px <= radius_px)
        valid_mask = np.isin(scl_arr, [4, 5, 7]) & circle_mask
        
        valid_rows, valid_cols = np.where(valid_mask)
        # Sample uniformly up to 600 points per background sector
        n_available = len(valid_rows)
        sample_size = min(600, n_available)
        chosen_indices = np.random.choice(n_available, size=sample_size, replace=False)
        
        print(f"  Sector {sec['name']}: sampled {sample_size} valid cloud-free pixels (from {n_available} valid).")
        
        for idx_chosen in chosen_indices:
            r_p = valid_rows[idx_chosen]
            c_p = valid_cols[idx_chosen]
            
            abs_col = c_min + c_p
            abs_row = r_min + r_p
            x_utm, y_utm = scl_src.transform * (abs_col + 0.5, abs_row + 0.5)
            p_lat, p_lon = utm_to_wgs84(45, x_utm, y_utm)
            
            b02 = float(band_data["B02"][r_p, c_p])
            b03 = float(band_data["B03"][r_p, c_p])
            b04 = float(band_data["B04"][r_p, c_p])
            b08 = float(band_data["B08"][r_p, c_p])
            b11 = float(band_data["B11"][r_p, c_p])
            b12 = float(band_data["B12"][r_p, c_p])
            
            ndvi = (b08 - b04) / (b08 + b04 + 1e-6)
            ndwi = (b03 - b08) / (b03 + b08 + 1e-6)
            clay = b11 / (b12 + 1e-6)
            fe_ox = b04 / (b02 + 1e-6)
            
            samples.append({
                "deposit_id": sec["sector_id"],
                "deposit_name": sec["name"],
                "latitude": round(p_lat, 6),
                "longitude": round(p_lon, 6),
                "easting": round(x_utm, 2),
                "northing": round(y_utm, 2),
                "mineral": "iron_ore",
                "label": 0,
                "is_background": 1,
                "formation": sec["geological_formation"],
                "B02": round(b02, 5),
                "B03": round(b03, 5),
                "B04": round(b04, 5),
                "B08": round(b08, 5),
                "B11": round(b11, 5),
                "B12": round(b12, 5),
                "NDVI": round(float(ndvi), 5),
                "NDWI": round(float(ndwi), 5),
                "clay_ratio": round(float(clay), 5),
                "iron_oxide_ratio": round(float(fe_ox), 5)
            })

    for s in srcs.values():
        s.close()
        
    positives = [s for s in samples if s["label"] == 1]
    negatives = [s for s in samples if s["label"] == 0]
    print(f"\nTotal Curated Observations: {len(samples)}")
    print(f"  Positive Mine Samples: {len(positives)}")
    print(f"  Background Pseudo-Absences: {len(negatives)}")
    
    # Deposit breakdown
    deposit_counts = {}
    for s in samples:
        dname = s["deposit_name"]
        deposit_counts[dname] = deposit_counts.get(dname, 0) + 1
    print("\nBreakdown by Deposit/Sector:")
    for dname, cnt in deposit_counts.items():
        print(f"  {dname}: {cnt}")
        
    out_csv = os.path.join(PROJECT_ROOT, "data", "curated", "iron_ore_training_curated.csv")
    os.makedirs(os.path.dirname(out_csv), exist_ok=True)
    fieldnames = list(samples[0].keys())
    with open(out_csv, "w", newline="", encoding="utf-8") as f_out:
        writer = csv.DictWriter(f_out, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(samples)
    print(f"\nSaved curated dataset to: {out_csv}")
    
    # Feature comparison
    cols = ["B04", "B02", "iron_oxide_ratio", "clay_ratio", "NDVI"]
    print("\nFeature Comparison: Positive (Iron Ore Mines) vs Background (Granite Basement):")
    for col in cols:
        pos_vals = [s[col] for s in positives]
        neg_vals = [s[col] for s in negatives]
        print(f"  {col:18s} | Pos Mean: {np.mean(pos_vals):.4f} (std: {np.std(pos_vals):.4f}) | Neg Mean: {np.mean(neg_vals):.4f} (std: {np.std(neg_vals):.4f})")

if __name__ == "__main__":
    extract_samples()

