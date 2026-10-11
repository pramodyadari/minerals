import numpy as np
import rasterio
from rasterio.transform import rowcol
import os

# -----------------------------
# 1. Load satellite feature data
# -----------------------------
features = np.load("data/processed/satellite_features.npy")

print("Feature shape:", features.shape)

# -----------------------------
# 2. Get coordinate information
# -----------------------------
band_file = "data/raw/T44QMK_20260621T050649_B04_20m.jp2"

with rasterio.open(band_file) as src:
    transform = src.transform
    crs = src.crs
    height = src.height
    width = src.width

print("Satellite CRS:", crs)
print("Image size:", width, "x", height)

# -----------------------------
# 3. Known Ghondi mine location
# -----------------------------
mine_lat = 21.9455
mine_lon = 80.4295

# Convert latitude/longitude to image coordinates
from rasterio.warp import transform as coordinate_transform

x, y = coordinate_transform(
    "EPSG:4326",
    crs,
    [mine_lon],
    [mine_lat]
)

mine_x = x[0]
mine_y = y[0]

print("Mine projected X:", mine_x)
print("Mine projected Y:", mine_y)

# -----------------------------
# 4. Convert coordinates to pixel
# -----------------------------
row, col = rowcol(
    transform,
    mine_x,
    mine_y
)

print("Mine pixel row:", row)
print("Mine pixel column:", col)

# -----------------------------
# 5. Create labels
# -----------------------------
labels = np.zeros((height, width), dtype=np.uint8)

# Label a small area around the known mine location
radius = 20

row_start = max(0, row - radius)
row_end = min(height, row + radius + 1)

col_start = max(0, col - radius)
col_end = min(width, col + radius + 1)

labels[row_start:row_end, col_start:col_end] = 1

print("Mine training area created.")

# -----------------------------
# 6. Save labels
# -----------------------------
os.makedirs("data/processed", exist_ok=True)

np.save(
    "data/processed/mine_labels.npy",
    labels
)

print("Labels saved successfully!")
print("Label shape:", labels.shape)
print("Manganese-labelled pixels:", np.sum(labels == 1))