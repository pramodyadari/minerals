import numpy as np
import matplotlib.pyplot as plt
import rasterio
import os

# Load prospectivity map
map_data = np.load(
    "data/processed/prospectivity_map.npy"
)

print("Map shape:", map_data.shape)
print("Minimum value:", map_data.min())
print("Maximum value:", map_data.max())

# Create output folder
os.makedirs("outputs", exist_ok=True)

# Create map
plt.figure(figsize=(10, 8))

plt.imshow(
    map_data,
    cmap="RdYlGn",
    vmin=0,
    vmax=1
)

plt.colorbar(
    label="Manganese Prospectivity"
)

plt.title(
    "Manganese Mineral Prospectivity Map"
)

plt.xlabel("Pixel Column")
plt.ylabel("Pixel Row")

plt.tight_layout()

# Save image
plt.savefig(
    "outputs/manganese_prospectivity_map.png",
    dpi=200
)

plt.close()

print("PNG map saved successfully!")
print(
    "File: outputs/manganese_prospectivity_map.png"
)