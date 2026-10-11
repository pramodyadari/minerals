import numpy as np
import os

# Load satellite samples
X = np.load("data/processed/ml_sample.npy")

# Load mine labels
labels = np.load("data/processed/mine_labels.npy")

print("Satellite sample shape:", X.shape)
print("Label image shape:", labels.shape)

# ------------------------------------------------
# For this first prototype:
# use the known mine area as positive examples
# ------------------------------------------------

# Find coordinates of labelled mine pixels
mine_pixels = np.argwhere(labels == 1)

print("Known mine pixels:", len(mine_pixels))

# Get their feature values
mine_features = []

# Load full feature data
features = np.load("data/processed/satellite_features.npy")

for row, col in mine_pixels:
    mine_features.append(features[:, row, col])

mine_features = np.array(mine_features)

# Positive labels
y_mine = np.ones(len(mine_features), dtype=np.uint8)

print("Positive samples:", mine_features.shape)

# ------------------------------------------------
# Create background samples
# ------------------------------------------------

np.random.seed(42)

background_count = len(mine_features)

rows = np.random.randint(0, labels.shape[0], background_count)
cols = np.random.randint(0, labels.shape[1], background_count)

background_features = []

for row, col in zip(rows, cols):

    # Don't select known mine pixels
    if labels[row, col] == 1:
        continue

    background_features.append(features[:, row, col])

background_features = np.array(background_features)

# Background labels
y_background = np.zeros(len(background_features), dtype=np.uint8)

print("Background samples:", background_features.shape)

# ------------------------------------------------
# Combine training data
# ------------------------------------------------

X_train = np.vstack([
    mine_features,
    background_features
])

y_train = np.concatenate([
    y_mine,
    y_background
])

print("Final training data:", X_train.shape)
print("Final labels:", y_train.shape)

# ------------------------------------------------
# Save training dataset
# ------------------------------------------------

os.makedirs("data/processed", exist_ok=True)

np.save("data/processed/X_train.npy", X_train)
np.save("data/processed/y_train.npy", y_train)

print("Training dataset saved successfully!")