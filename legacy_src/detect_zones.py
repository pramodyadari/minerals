import numpy as np
import rasterio
from rasterio.transform import xy
from rasterio.warp import transform
from scipy import ndimage
import pandas as pd
import os

print("Loading prospectivity map...")

prospectivity = np.load("data/processed/prospectivity_map.npy")

print("Map loaded:", prospectivity.shape)

# Use a higher threshold to reduce noise
threshold = 0.90

high = prospectivity >= threshold

print("High-prospectivity pixels:", np.sum(high))

# Group neighboring pixels into zones
structure = np.ones((3, 3), dtype=np.uint8)

zones, number_of_zones = ndimage.label(high, structure=structure)

print("Initial zones detected:", number_of_zones)

# Find bounding boxes efficiently
objects = ndimage.find_objects(zones)

reference_file = "data/raw/T44QMK_20260621T050649_B04_20m.jp2"

results = []

with rasterio.open(reference_file) as src:

    transform_matrix = src.transform
    crs = src.crs

    for zone_id, zone_slice in enumerate(objects, start=1):

        if zone_slice is None:
            continue

        rows_slice, cols_slice = zone_slice

        # Extract this small zone region
        zone_area = zones[zone_slice]

        rows, cols = np.where(zone_area == zone_id)

        pixel_count = len(rows)

        # Ignore very small zones
        if pixel_count < 50:
            continue

        # Convert local coordinates to full-image coordinates
        rows = rows + rows_slice.start
        cols = cols + cols_slice.start

        scores = prospectivity[rows, cols]

        mean_score = np.mean(scores)
        max_score = np.max(scores)

        center_row = int(np.mean(rows))
        center_col = int(np.mean(cols))

        x, y = xy(
            transform_matrix,
            center_row,
            center_col,
            offset="center"
        )

        lon, lat = transform(
            crs,
            "EPSG:4326",
            [x],
            [y]
        )

        results.append({
            "Zone_ID": zone_id,
            "Pixels": pixel_count,
            "Mean_Score": round(float(mean_score), 4),
            "Max_Score": round(float(max_score), 4),
            "Latitude": round(float(lat[0]), 6),
            "Longitude": round(float(lon[0]), 6)
        })

print("Useful zones found:", len(results))

# Sort by average prospectivity
results = sorted(
    results,
    key=lambda x: x["Mean_Score"],
    reverse=True
)

# Keep top 20 zones
results = results[:20]

os.makedirs("outputs", exist_ok=True)

df = pd.DataFrame(results)

df.to_csv(
    "outputs/high_prospectivity_zones.csv",
    index=False
)

print("\nTop High-Prospectivity Zones")
print("--------------------------------")

print(df.to_string(index=False))

print("\nZone results saved successfully!")

print("File: outputs/high_prospectivity_zones.csv")