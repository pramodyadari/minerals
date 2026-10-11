import numpy as np
import rasterio
from rasterio.transform import xy
from rasterio.warp import transform

# Load prospectivity map
prospectivity = np.load(
    "data/processed/prospectivity_map.npy"
)

# Find top 10 pixels
flat = prospectivity.ravel()

top_indices = np.argsort(flat)[-10:][::-1]

# Open satellite image for coordinate information
reference_file = (
    "data/raw/"
    "T44QMK_20260621T050649_B04_20m.jp2"
)

with rasterio.open(reference_file) as src:

    transform_matrix = src.transform
    crs = src.crs

    print("Top 10 prospectivity hotspots:")
    print("--------------------------------")

    for rank, index in enumerate(top_indices, start=1):

        row, col = np.unravel_index(
            index,
            prospectivity.shape
        )

        score = prospectivity[row, col]

        # Pixel center coordinates in UTM
        x, y = xy(
            transform_matrix,
            row,
            col,
            offset="center"
        )

        # Convert UTM to latitude/longitude
        lon, lat = transform(
            crs,
            "EPSG:4326",
            [x],
            [y]
        )

        print(
            f"{rank}. "
            f"Score={score:.4f}, "
            f"Lat={lat[0]:.6f}, "
            f"Lon={lon[0]:.6f}"
        )