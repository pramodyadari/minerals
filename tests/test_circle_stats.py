import os
import time
import rasterio
import rasterio.windows
from rasterio.windows import from_bounds
import numpy as np

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TIF_PATH = os.path.join(BASE_DIR, 'outputs', 'manganese_prospectivity.tif')
if not os.path.exists(TIF_PATH):
    TIF_PATH = 'outputs/manganese_prospectivity.tif'

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
    # Read with optional decimation if large, e.g. step of 5 (100m) or full resolution
    data = src.read(1, window=win)
    
    # Generate coordinates for circular mask
    # Win transform
    win_transform = rasterio.windows.transform(win, src.transform)
    # Compute row and col meshgrid or sample
    rows, cols = data.shape
    # xs = left + (col + 0.5) * 20
    # ys = top - (row + 0.5) * 20
    # Vectorized circular mask:
    x_coords = np.linspace(left, right, cols)
    y_coords = np.linspace(top, bottom, rows)
    xx, yy = np.meshgrid(x_coords, y_coords)
    dist_sq = (xx - easting)**2 + (yy - northing)**2
    mask = dist_sq <= (radius_m ** 2)
    
    circle_data = data[mask]
    print(f"Inside circular radius 25km: count={len(circle_data)}")
    print(f"Max: {float(circle_data.max()) * 100:.2f}%")
    print(f"Mean: {float(circle_data.mean()) * 100:.2f}%")
    print(f"Min: {float(circle_data.min()) * 100:.2f}%")

    assert len(circle_data) > 4000000, f"Expected >4M circular pixels, got {len(circle_data)}"
    assert circle_data.max() == 1.0, f"Expected max 1.0, got {circle_data.max()}"
    assert 0.25 <= circle_data.mean() <= 0.35, f"Expected mean between 0.25 and 0.35, got {circle_data.mean()}"
    print("[OK] test_circle_stats passed successfully!")
