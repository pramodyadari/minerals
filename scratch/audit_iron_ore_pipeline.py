import os
import sys
import json
import math
import rasterio
from rasterio.windows import Window
import numpy as np

# Ensure backend/app is importable
APP_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "backend", "app")
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if APP_DIR not in sys.path:
    sys.path.insert(0, APP_DIR)

from raster_ingestion_service import wgs84_to_utm, utm_to_wgs84

geotiff_dir = os.path.join(PROJECT_ROOT, "data", "cache", "sentinel2", "S2A_MSIL2A_20261010T045231_N0513_R076_T45QUE_20261010T095406")

deposits = [
    {"name": "Noamundi Iron Ore Mine (Tata Steel)", "lat": 22.1500, "lon": 85.5000, "source": "GSI Memoir Vol. 112 / IBM NMI 2023"},
    {"name": "Joda East Iron Mine (Tata Steel)", "lat": 22.0200, "lon": 85.4300, "source": "IBM Mining Lease Atlas & Odisha DGM"},
    {"name": "Kiriburu Iron Mine (SAIL)", "lat": 22.0900, "lon": 85.3400, "source": "SAIL Lease Baseline / GSI Sheet 73F/8"},
    {"name": "Gua Iron Ore Mine (SAIL)", "lat": 22.2100, "lon": 85.3800, "source": "SAIL IISCO Division / GSI Record"},
    {"name": "Bolani Iron Ore Mine (SAIL)", "lat": 22.1000, "lon": 85.3100, "source": "SAIL Raw Materials Division / IBM NMI"}
]

scl_path = os.path.join(geotiff_dir, "S2A_MSIL2A_20261010T045231_N0513_R076_T45QUE_20261010T095406_SCL.tif")

print("=" * 80)
print("AUDIT: AUTHORITATIVE IRON ORE OCCURRENCES IN TILE T45QUE")
print("=" * 80)

with rasterio.open(scl_path) as scl_src:
    print(f"SCL Raster: {scl_src.width} x {scl_src.height}, Res: {scl_src.res}, CRS: {scl_src.crs}")
    inv_t = ~scl_src.transform
    
    for dep in deposits:
        zone, easting, northing = wgs84_to_utm(dep["lat"], dep["lon"], zone=45)
        col, row = inv_t * (easting, northing)
        col, row = int(round(col)), int(round(row))
        
        # Check if inside tile
        if not (0 <= col < scl_src.width and 0 <= row < scl_src.height):
            print(f"OUT OF BOUNDS: {dep['name']}")
            continue
            
        # 1 km window: 50 x 50 pixels (at 20m)
        win = Window(col - 25, row - 25, 50, 50)
        scl_win = scl_src.read(1, window=win)
        
        valid_mask = np.isin(scl_win, [4, 5, 7])
        cloud_mask = np.isin(scl_win, [8, 9, 10])
        shadow_mask = (scl_win == 3)
        valid_count = int(np.sum(valid_mask))
        total_count = scl_win.size
        valid_pct = round(100.0 * valid_count / total_count, 2)
        
        center_scl = scl_win[25, 25]
        
        print(f"\nDeposit: {dep['name']}")
        print(f"  Coordinates: Lat {dep['lat']:.4f} N, Lon {dep['lon']:.4f} E (UTM: E {easting:.1f}, N {northing:.1f})")
        print(f"  Raster Pixel: Row {row}, Col {col} | Center SCL class: {center_scl}")
        print(f"  1 km Window Coverage: {valid_count}/{total_count} valid ({valid_pct}%)")
        print(f"  Clouds: {int(np.sum(cloud_mask))} ({round(100.0*np.sum(cloud_mask)/total_count, 1)}%), Shadows: {int(np.sum(shadow_mask))} ({round(100.0*np.sum(shadow_mask)/total_count, 1)}%)")
        print(f"  Source: {dep['source']}")
