#!/usr/bin/env python3
"""
Candidate Mineral Specimen Classifier Fine-Tuning Pipeline
Trains/fine-tunes a candidate model using:
1. Baseline CNN initialization (transfer learning from validated features).
2. Realistic domain augmentations:
   - Specular hotspot simulation (vitreous luster under flash).
   - Luminance and contrast scaling (lighting domain shifts).
   - Rotations and flips (pose invariance).
3. Discriminative layer-wise learning rates (backbone frozen or low LR, head fine-tuned).
4. Validation-based checkpoint selection & manifold calibration.
5. Strict isolation: saves to models/candidate_mineral_fine_tuned.pth (NEVER overwriting production).
"""

import os
import sys
import json
import time
import random
import copy
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader
from PIL import Image

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from ai.train import MineralConvNet, CLASSES, CLASS_TO_IDX

CANDIDATE_MODEL_PATH = os.path.join(BASE_DIR, "models", "candidate_mineral_fine_tuned.pth")
CANDIDATE_METADATA_PATH = os.path.join(BASE_DIR, "models", "candidate_mineral_metadata.json")
CANDIDATE_OOD_CONFIG_PATH = os.path.join(BASE_DIR, "models", "candidate_mineral_ood_config.json")


class FineTuningMineralDataset(Dataset):
    """
    Dataset loader for fine-tuning with realistic geological lighting & luster augmentations.
    """
    def __init__(self, data_dir: str, split: str = "train", augment: bool = False, seed: int = 42):
        self.split_dir = os.path.join(data_dir, split)
        self.augment = augment
        self.samples = []
        random.seed(seed)
        np.random.seed(seed)

        for cls_name in CLASSES:
            cls_folder = os.path.join(self.split_dir, cls_name)
            if not os.path.exists(cls_folder):
                continue
            for fname in sorted(os.listdir(cls_folder)):
                if fname.lower().endswith((".jpg", ".jpeg", ".png", ".webp")):
                    self.samples.append((os.path.join(cls_folder, fname), CLASS_TO_IDX[cls_name]))

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, idx):
        fpath, label = self.samples[idx]
        with Image.open(fpath) as img:
            img = img.convert("RGB").resize((224, 224))

            arr = np.array(img, dtype=np.float32)

            if self.augment:
                # 1. Random Flips & Orthogonal Rotations
                if random.random() > 0.5:
                    arr = np.fliplr(arr)
                if random.random() > 0.5:
                    arr = np.flipud(arr)
                k_rot = random.choice([0, 1, 2, 3])
                if k_rot > 0:
                    arr = np.rot90(arr, k_rot)

                # 2. Exposure & Contrast Scaling
                # Simulates bright camera flashes or shadowed lighting
                exposure = random.uniform(0.70, 1.30)
                contrast = random.uniform(0.75, 1.25)
                arr = (arr - 128.0) * contrast + 128.0
                arr = arr * exposure
                arr = np.clip(arr, 0.0, 255.0)

                # 3. Specular Reflection / Luster Highlight Simulation (25% chance)
                # Adds a localized specular Gaussian reflection to simulate vitreous/metallic surfaces
                if random.random() < 0.25:
                    cx = random.randint(40, 184)
                    cy = random.randint(40, 184)
                    sigma = random.uniform(15.0, 35.0)
                    intensity = random.uniform(80.0, 180.0)
                    y_grid, x_grid = np.ogrid[:224, :224]
                    dist_sq = (x_grid - cx) ** 2 + (y_grid - cy) ** 2
                    specular = intensity * np.exp(-dist_sq / (2.0 * sigma ** 2))
                    arr = np.clip(arr + specular[:, :, np.newaxis], 0.0, 255.0)

            # Normalization matching exact production pipeline
            arr = arr / 255.0
            mean = np.array([0.485, 0.456, 0.406], dtype=np.float32)
            std = np.array([0.229, 0.224, 0.225], dtype=np.float32)
            arr = (arr - mean) / std

            tensor = torch.from_numpy(arr).permute(2, 0, 1).float()
            return tensor, label


def train_candidate_model(epochs: int = 15, batch_size: int = 16, lr_backbone: float = 2e-5, lr_head: float = 2e-4, seed: int = 42):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)

    device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
    print(f"Candidate Fine-Tuning on: {device}")

    # 1. Datasets & Loaders
    train_ds = FineTuningMineralDataset("data", split="train", augment=True, seed=seed)
    val_ds = FineTuningMineralDataset("data", split="validation", augment=False, seed=seed)

    train_loader = DataLoader(train_ds, batch_size=batch_size, shuffle=True, drop_last=False)
    val_loader = DataLoader(val_ds, batch_size=batch_size, shuffle=False)

    print(f"Loaded: {len(train_ds)} train samples, {len(val_ds)} validation samples.")

    # 2. Model Initialization (Warm-start from production baseline checkpoint)
    baseline_path = os.path.join(BASE_DIR, "models", "mineral_image_classifier.pth")
    model = MineralConvNet(num_classes=len(CLASSES))

    if os.path.exists(baseline_path):
        print(f"Warm-starting from baseline weights: {baseline_path}")
        state = torch.load(baseline_path, map_location="cpu")
        model.load_state_dict(state)
    else:
        print("Warning: Baseline checkpoint not found; initializing from scratch.")

    model = model.to(device)

    # 3. Discriminative Optimizer & Scheduler
    optimizer = optim.AdamW([
        {"params": model.features.parameters(), "lr": lr_backbone, "weight_decay": 1e-4},
        {"params": model.classifier.parameters(), "lr": lr_head, "weight_decay": 1e-3}
    ])
    scheduler = optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=epochs, eta_min=1e-6)
    criterion = nn.CrossEntropyLoss()

    best_val_acc = 0.0
    best_val_loss = float("inf")
    best_weights = copy.deepcopy(model.state_dict())
    training_history = []

    print("\nStarting Candidate Fine-Tuning:")
    for epoch in range(1, epochs + 1):
        model.train()
        train_loss = 0.0
        train_correct = 0

        for inputs, targets in train_loader:
            inputs, targets = inputs.to(device), targets.to(device)
            optimizer.zero_grad()
            outputs = model(inputs)
            loss = criterion(outputs, targets)
            loss.backward()
            optimizer.step()

            train_loss += loss.item() * inputs.size(0)
            preds = outputs.argmax(dim=1)
            train_correct += (preds == targets).sum().item()

        scheduler.step()

        # Validation phase
        model.eval()
        val_loss = 0.0
        val_correct = 0
        with torch.no_grad():
            for inputs, targets in val_loader:
                inputs, targets = inputs.to(device), targets.to(device)
                outputs = model(inputs)
                loss = criterion(outputs, targets)
                val_loss += loss.item() * inputs.size(0)
                preds = outputs.argmax(dim=1)
                val_correct += (preds == targets).sum().item()

        epoch_train_loss = train_loss / len(train_ds)
        epoch_train_acc = (train_correct / len(train_ds)) * 100.0
        epoch_val_loss = val_loss / len(val_ds)
        epoch_val_acc = (val_correct / len(val_ds)) * 100.0

        training_history.append({
            "epoch": epoch,
            "train_loss": round(epoch_train_loss, 4),
            "train_acc_pct": round(epoch_train_acc, 2),
            "val_loss": round(epoch_val_loss, 4),
            "val_acc_pct": round(epoch_val_acc, 2)
        })

        print(f"Epoch {epoch:02d}/{epochs:02d} | Train Loss: {epoch_train_loss:.4f}, Acc: {epoch_train_acc:.1f}% | Val Loss: {epoch_val_loss:.4f}, Acc: {epoch_val_acc:.1f}%")

        if epoch_val_acc >= best_val_acc and epoch_val_loss < best_val_loss:
            best_val_acc = epoch_val_acc
            best_val_loss = epoch_val_loss
            best_weights = copy.deepcopy(model.state_dict())

    # 4. Save Candidate Checkpoint (Strictly in candidate path)
    torch.save(best_weights, CANDIDATE_MODEL_PATH)
    print(f"\nCandidate checkpoint saved to: {CANDIDATE_MODEL_PATH}")

    # 5. Extract Feature Centroids and Manifold Bounds on Validation Data
    model.load_state_dict(best_weights)
    model.eval()

    embeddings_by_class = {c: [] for c in CLASSES}
    with torch.no_grad():
        for inputs, targets in val_loader:
            inputs = inputs.to(device)
            f256 = torch.flatten(model.features(inputs), 1)
            h128 = model.classifier[2](model.classifier[1](f256))
            h_np = h128.cpu().numpy()
            for i, t in enumerate(targets):
                cls_name = CLASSES[t.item()]
                embeddings_by_class[cls_name].append(h_np[i])

    centroids = {}
    scale_bounds = {}
    for c in CLASSES:
        embs = np.array(embeddings_by_class[c], dtype=np.float32)
        c_vec = np.mean(embs, axis=0)
        norm_c = float(np.linalg.norm(c_vec))
        if norm_c > 0:
            c_vec = c_vec / norm_c
        centroids[c] = [float(x) for x in c_vec]

        # Calculate scale bounds
        alphas = []
        for vec in embs:
            norm_sq = float(np.dot(c_vec, c_vec) + 1e-8)
            alpha = float(np.dot(vec, c_vec) / norm_sq)
            alphas.append(alpha)
        alphas = np.array(alphas)
        scale_bounds[c] = [round(float(np.min(alphas) * 0.85), 2), round(float(np.max(alphas) * 1.15), 2)]

    candidate_ood_cfg = {
        "model_architecture": "CandidateMineralNet (Fine-Tuned)",
        "method": "Class-Conditional Scale-Robust Manifold Ray Distance",
        "supported_classes": CLASSES,
        "feature_dim": 128,
        "rejection_threshold_tau": 5.0,
        "scale_penalty_weight": 25.0,
        "scale_bounds": scale_bounds,
        "centroids": centroids
    }

    with open(CANDIDATE_OOD_CONFIG_PATH, "w") as fp:
        json.dump(candidate_ood_cfg, fp, indent=2)
    print(f"Candidate OOD config saved to: {CANDIDATE_OOD_CONFIG_PATH}")

    metadata = {
        "candidate_name": "CandidateMineralNet",
        "training_timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "base_model": "MineralConvNet (Warm-Started)",
        "epochs": epochs,
        "batch_size": batch_size,
        "best_val_loss": round(best_val_loss, 4),
        "best_val_acc_pct": round(best_val_acc, 2),
        "training_history": training_history
    }
    with open(CANDIDATE_METADATA_PATH, "w") as fp:
        json.dump(metadata, fp, indent=2)

    return metadata


if __name__ == "__main__":
    train_candidate_model()

