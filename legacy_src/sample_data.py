import numpy as np
import os

# Load satellite features
data = np.load("data/processed/satellite_features.npy")

print("Original shape:", data.shape)

# Change shape:
# 10 features × height × width
# becomes
# pixels × 10 features
pixels = data.reshape(data.shape[0], -1).T

print("Pixel dataset shape:", pixels.shape)

# Remove pixels containing invalid values
valid = np.all(np.isfinite(pixels), axis=1)
pixels = pixels[valid]

print("Valid pixels:", pixels.shape)

# Take a random sample
np.random.seed(42)

sample_size = 50000

if len(pixels) > sample_size:
    indices = np.random.choice(
        len(pixels),
        sample_size,
        replace=False
    )
    sample = pixels[indices]
else:
    sample = pixels

print("Sample shape:", sample.shape)

# Save sample
os.makedirs("data/processed", exist_ok=True)

np.save(
    "data/processed/ml_sample.npy",
    sample
)

print("Sample saved successfully!")