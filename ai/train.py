"""
AI Mineral Intelligence — Pure PyTorch 4-Class CNN Training Pipeline (Section 5)
Classes: Coal, Manganese, Iron Ore, Bauxite
Features:
  - Dataset loader built with PIL and native torch tensors (no C++ torchvision ops needed).
  - Deep 4-stage Convolutional Neural Network with BatchNorm, Dropout & Global Average Pooling.
  - Automatic audit using dataset_validator.py before training.
  - Checkpoints best model weights based on validation loss / accuracy.
  - Saves weights -> models/mineral_image_classifier.pth.
  - Saves training configuration & history -> models/mineral_image_classifier_metadata.json.
"""

import os
import json
import time
import random
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader
from PIL import Image

from dataset_validator import audit_dataset

CLASSES = ["coal", "manganese", "iron_ore", "bauxite"]
CLASS_TO_IDX = {c: i for i, c in enumerate(CLASSES)}
IDX_TO_CLASS = {i: c for i, c in enumerate(CLASSES)}

MODEL_PATH = "models/mineral_image_classifier.pth"
METADATA_PATH = "models/mineral_image_classifier_metadata.json"

class MineralDataset(Dataset):
    def __init__(self, data_dir, split="train", augment=False):
        self.split_dir = os.path.join(data_dir, split)
        self.augment = augment
        self.samples = []
        
        for cls_name in CLASSES:
            cls_folder = os.path.join(self.split_dir, cls_name)
            if not os.path.exists(cls_folder):
                continue
            for fname in os.listdir(cls_folder):
                if fname.lower().endswith(('.jpg', '.jpeg', '.png')):
                    self.samples.append((os.path.join(cls_folder, fname), CLASS_TO_IDX[cls_name]))
                    
    def __len__(self):
        return len(self.samples)
        
    def __getitem__(self, idx):
        fpath, label = self.samples[idx]
        with Image.open(fpath) as img:
            img = img.convert("RGB").resize((224, 224))
            
            # Simple data augmentations for training
            if self.augment:
                if random.random() > 0.5:
                    img = img.transpose(Image.FLIP_LEFT_RIGHT)
                if random.random() > 0.5:
                    img = img.transpose(Image.FLIP_TOP_BOTTOM)
                    
            arr = np.array(img, dtype=np.float32) / 255.0  # (224, 224, 3)
            
            # Standard ImageNet normalization: (x - mean) / std
            mean = np.array([0.485, 0.456, 0.406], dtype=np.float32)
            std = np.array([0.229, 0.224, 0.225], dtype=np.float32)
            arr = (arr - mean) / std
            
            tensor = torch.from_numpy(arr).permute(2, 0, 1)  # (3, 224, 224)
            return tensor, label

class MineralConvNet(nn.Module):
    """
    4-Stage Deep Convolutional Neural Network for Mineral Specimen Classification.
    """
    def __init__(self, num_classes=4):
        super(MineralConvNet, self).__init__()
        
        self.features = nn.Sequential(
            # Block 1: 3 -> 32
            nn.Conv2d(3, 32, kernel_size=3, padding=1),
            nn.BatchNorm2d(32),
            nn.ReLU(inplace=True),
            nn.Conv2d(32, 32, kernel_size=3, padding=1),
            nn.BatchNorm2d(32),
            nn.ReLU(inplace=True),
            nn.MaxPool2d(2, 2),  # 112x112
            
            # Block 2: 32 -> 64
            nn.Conv2d(32, 64, kernel_size=3, padding=1),
            nn.BatchNorm2d(64),
            nn.ReLU(inplace=True),
            nn.Conv2d(64, 64, kernel_size=3, padding=1),
            nn.BatchNorm2d(64),
            nn.ReLU(inplace=True),
            nn.MaxPool2d(2, 2),  # 56x56
            
            # Block 3: 64 -> 128
            nn.Conv2d(64, 128, kernel_size=3, padding=1),
            nn.BatchNorm2d(128),
            nn.ReLU(inplace=True),
            nn.Conv2d(128, 128, kernel_size=3, padding=1),
            nn.BatchNorm2d(128),
            nn.ReLU(inplace=True),
            nn.MaxPool2d(2, 2),  # 28x28
            
            # Block 4: 128 -> 256
            nn.Conv2d(128, 256, kernel_size=3, padding=1),
            nn.BatchNorm2d(256),
            nn.ReLU(inplace=True),
            nn.Conv2d(256, 256, kernel_size=3, padding=1),
            nn.BatchNorm2d(256),
            nn.ReLU(inplace=True),
            nn.AdaptiveAvgPool2d((1, 1))  # 1x1
        )
        
        self.classifier = nn.Sequential(
            nn.Dropout(p=0.4),
            nn.Linear(256, 128),
            nn.ReLU(inplace=True),
            nn.Dropout(p=0.2),
            nn.Linear(128, num_classes)
        )
        
    def forward(self, x):
        x = self.features(x)
        x = torch.flatten(x, 1)
        x = self.classifier(x)
        return x

def train_model(data_dir="data", num_epochs=12, batch_size=16, lr=0.001):
    print("=" * 60)
    print("AI MINERAL SPECIMEN CLASSIFIER — TRAINING PIPELINE")
    print("=" * 60)

    # 1. Dataset Audit
    print("\n[Step 1/4] Auditing Dataset Integrity...")
    audit = audit_dataset(data_dir)
    if not audit["valid"]:
        raise ValueError(f"Dataset audit failed: {audit['errors']}")
    print(f"  Train samples: {sum(audit['splits']['train'].values())}")
    print(f"  Val samples:   {sum(audit['splits']['validation'].values())}")
    print(f"  Test samples:  {sum(audit['splits']['test'].values())}")
    print("  Data leakage: None. Zero overlap across splits.")

    # 2. Data Loaders
    print("\n[Step 2/4] Initializing Preprocessing & Augmentations...")
    train_ds = MineralDataset(data_dir, split="train", augment=True)
    val_ds = MineralDataset(data_dir, split="validation", augment=False)
    
    train_loader = DataLoader(train_ds, batch_size=batch_size, shuffle=True)
    val_loader = DataLoader(val_ds, batch_size=batch_size, shuffle=False)

    device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
    print(f"  Compute device: {device}")

    # 3. Model Architecture
    print("\n[Step 3/4] Initializing MineralConvNet Architecture...")
    model = MineralConvNet(num_classes=len(CLASSES)).to(device)

    criterion = nn.CrossEntropyLoss()
    optimizer = optim.AdamW(model.parameters(), lr=lr, weight_decay=1e-4)
    scheduler = optim.lr_scheduler.StepLR(optimizer, step_size=4, gamma=0.5)

    best_val_acc = 0.0
    best_weights = None
    training_history = []
    start_time = time.time()

    # 4. Training Loop
    print("\n[Step 4/4] Executing Training & Validation...")
    for epoch in range(num_epochs):
        model.train()
        train_loss, train_correct, train_total = 0.0, 0, 0
        
        for inputs, labels in train_loader:
            inputs, labels = inputs.to(device), labels.to(device)
            optimizer.zero_grad()
            outputs = model(inputs)
            loss = criterion(outputs, labels)
            loss.backward()
            optimizer.step()
            
            train_loss += loss.item() * inputs.size(0)
            _, preds = torch.max(outputs, 1)
            train_correct += torch.sum(preds == labels.data).item()
            train_total += inputs.size(0)
            
        scheduler.step()
        
        # Validation Phase
        model.eval()
        val_loss, val_correct, val_total = 0.0, 0, 0
        with torch.no_grad():
            for inputs, labels in val_loader:
                inputs, labels = inputs.to(device), labels.to(device)
                outputs = model(inputs)
                loss = criterion(outputs, labels)
                val_loss += loss.item() * inputs.size(0)
                _, preds = torch.max(outputs, 1)
                val_correct += torch.sum(preds == labels.data).item()
                val_total += inputs.size(0)

        epoch_train_acc = (train_correct / train_total) * 100
        epoch_val_acc = (val_correct / val_total) * 100
        
        record = {
            "epoch": epoch + 1,
            "train_loss": round(train_loss / train_total, 4),
            "train_acc": round(epoch_train_acc, 2),
            "validation_loss": round(val_loss / val_total, 4),
            "validation_acc": round(epoch_val_acc, 2)
        }
        training_history.append(record)
        
        print(f"  Epoch {epoch+1:02d}/{num_epochs:02d} | Train Acc: {record['train_acc']:.1f}% Loss: {record['train_loss']:.4f} | Val Acc: {record['validation_acc']:.1f}% Loss: {record['validation_loss']:.4f}")

        if epoch_val_acc >= best_val_acc:
            best_val_acc = epoch_val_acc
            best_weights = model.state_dict().copy()

    time_elapsed = time.time() - start_time
    print(f"\nTraining completed in {time_elapsed:.1f}s. Best Validation Accuracy: {best_val_acc:.2f}%")

    os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)
    if best_weights is not None:
        model.load_state_dict(best_weights)
    torch.save(model.state_dict(), MODEL_PATH)
    print(f"Saved trained weights -> {MODEL_PATH}")

    metadata = {
        "model_architecture": "MineralConvNet",
        "task": "4-Class Mineral Specimen Image Classification",
        "classes": CLASSES,
        "class_to_idx": CLASS_TO_IDX,
        "input_dimensions": [3, 224, 224],
        "best_validation_accuracy_pct": round(best_val_acc, 2),
        "total_training_epochs": num_epochs,
        "batch_size": batch_size,
        "learning_rate": lr,
        "trained_timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "training_history": training_history,
        "framework": f"PyTorch {torch.__version__}",
        "disclaimer": "Specimen surface visual classification only. Does not prove underground mineral occurrence."
    }

    with open(METADATA_PATH, "w") as fp:
        json.dump(metadata, fp, indent=2)
    print(f"Saved model metadata -> {METADATA_PATH}")

    return metadata

if __name__ == "__main__":
    train_model()
