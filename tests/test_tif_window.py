import os
import time
import rasterio
from rasterio.windows import from_bounds

# Robust path resolution
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TIF_PATH = os.path.join(BASE_DIR, 'outputs', 'manganese_prospectivity.tif')
if not os.path.exists(TIF_PATH):
    TIF_PATH = 'outputs/manganese_prospectivity.tif'

t0 = time.time()
with rasterio.open(TIF_PATH) as src:
    easting = 441089.328
    northing = 2426904.204
    radius_m = 25000 # 25km
    
    # Bounding box clamped to raster bounds
    left = max(src.bounds.left, easting - radius_m)
    right = min(src.bounds.right, easting + radius_m)
    bottom = max(src.bounds.bottom, northing - radius_m)
    top = min(src.bounds.top, northing + radius_m)
    
    win = from_bounds(left, bottom, right, top, transform=src.transform)
    data = src.read(1, window=win)
    
    # Exact mine pixel
    py, px = src.index(easting, northing)
    mine_val = src.read(1, window=((py, py+1), (px, px+1)))[0,0]

print(f"Extraction took {time.time() - t0:.4f}s")
print("Window shape:", data.shape)
print("Mine pixel value:", mine_val)
print(f"Max: {data.max() * 100:.1f}%")
print(f"Mean: {data.mean() * 100:.1f}%")
print(f"Min: {data.min() * 100:.1f}%")

assert abs(mine_val - 0.71) < 0.02, f"Expected mine pixel ~0.71, got {mine_val}"
assert data.shape[0] > 0 and data.shape[1] > 0, "Window shape must be positive"
print("[OK] test_tif_window validation passed successfully!")
