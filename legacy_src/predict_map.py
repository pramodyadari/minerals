import numpy as np
import rasterio
import joblib
import os

# --------------------------------
# 1. Load trained Random Forest
# --------------------------------
model = joblib.load("models/manganese_random_forest.pkl")

print("Model loaded successfully!")

# --------------------------------
# 2. Load satellite features
# --------------------------------
features = np.load(
    "data/processed/satellite_features.npy",
    mmap_mode="r"
)

print("Feature shape:", features.shape)

n_features, height, width = features.shape

# --------------------------------
# 3. Prepare output map
# --------------------------------
prospectivity = np.zeros(
    (height, width),
    dtype=np.float32
)

# --------------------------------
# 4. Predict in chunks
# --------------------------------
chunk_size = 250000

for start in range(0, height * width, chunk_size):

    end = min(start + chunk_size, height * width)

    pixel_data = features.reshape(
        n_features, -1
    )[:, start:end].T

    probabilities = model.predict_proba(
        pixel_data
    )[:, 1]

    prospectivity.reshape(-1)[start:end] = probabilities

    print(
        "Processed:",
        end,
        "/",
        height * width
    )

# --------------------------------
# 5. Save NumPy result
# --------------------------------
os.makedirs("data/processed", exist_ok=True)

np.save(
    "data/processed/prospectivity_map.npy",
    prospectivity
)

print("Prospectivity map saved successfully!")

# --------------------------------
# 6. Save GeoTIFF map
# --------------------------------
reference_file = (
    "data/raw/"
    "T44QMK_20260621T050649_B04_20m.jp2"
)

with rasterio.open(reference_file) as src:

    profile = src.profile.copy()

    profile.update(
        driver="GTiff",
        dtype=rasterio.float32,
        count=1,
        compress="lzw"
    )

    with rasterio.open(
        "outputs/manganese_prospectivity.tif",
        "w",
        **profile
    ) as dst:

        dst.write(
            prospectivity,
            1
        )

print("GeoTIFF map saved successfully!")
print(
    "File: outputs/manganese_prospectivity.tif"
)