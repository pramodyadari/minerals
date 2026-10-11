import rasterio
import glob
import os
import numpy as np

# Find satellite band files
files = {}

for file in glob.glob("data/raw/*.jp2"):
    name = os.path.basename(file)

    if "_B04_" in name:
        files["B04"] = file
    elif "_B05_" in name:
        files["B05"] = file
    elif "_B06_" in name:
        files["B06"] = file
    elif "_B8A_" in name:
        files["B8A"] = file
    elif "_B11_" in name:
        files["B11"] = file
    elif "_B12_" in name:
        files["B12"] = file

# Read the bands
bands = {}

for band_name, file in files.items():
    with rasterio.open(file) as src:
        bands[band_name] = src.read(1).astype("float32")

print("Bands loaded:")
for name in bands:
    print(name, bands[name].shape)

# Avoid division by zero
eps = 1e-10

# Calculate spectral indices/features
ndvi = (bands["B8A"] - bands["B04"]) / (
    bands["B8A"] + bands["B04"] + eps
)

ndmi = (bands["B8A"] - bands["B11"]) / (
    bands["B8A"] + bands["B11"] + eps
)

swir_ratio = bands["B11"] / (bands["B12"] + eps)

red_swir_ratio = bands["B04"] / (bands["B11"] + eps)

print("\nFeatures calculated successfully!")

print("NDVI range:", np.nanmin(ndvi), "to", np.nanmax(ndvi))
print("NDMI range:", np.nanmin(ndmi), "to", np.nanmax(ndmi))
print("SWIR ratio range:", np.nanmin(swir_ratio), "to", np.nanmax(swir_ratio))
print("Red/SWIR ratio range:", np.nanmin(red_swir_ratio), "to", np.nanmax(red_swir_ratio))
# Save calculated features
features = np.stack(
    [
        bands["B04"],
        bands["B05"],
        bands["B06"],
        bands["B8A"],
        bands["B11"],
        bands["B12"],
        ndvi,
        ndmi,
        swir_ratio,
        red_swir_ratio
    ],
    axis=0
)

np.save("data/processed/satellite_features.npy", features)

print("\nFeatures saved successfully!")
print("Saved file: data/processed/satellite_features.npy")
print("Feature shape:", features.shape)