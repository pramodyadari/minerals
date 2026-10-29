"""
Experimental training of MineralConvNet with train-only augmentations
to see if it maintains 0% OOD FAR while improving feature robustness.
"""
import os
import sys
import time
import random
import json
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from ai.train import MineralConvNet, CLASSES, CLASS_TO_IDX
from ai.train_improved import MineralDataset, set_seed

def experiment_convnet_augmented():
    set_seed(42)
    device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
    model = MineralConvNet(num_classes=4).to(device)

    train_ds = MineralDataset("data", split="train", augment=True)
    val_ds = MineralDataset("data", split="validation", augment=False)
    test_ds = MineralDataset("data", split="test", augment=False)

    train_loader = DataLoader(train_ds, batch_size=16, shuffle=True)
    val_loader = DataLoader(val_ds, batch_size=16, shuffle=False)
    test_loader = DataLoader(test_ds, batch_size=16, shuffle=False)

    criterion = nn.CrossEntropyLoss()
    optimizer = optim.AdamW(model.parameters(), lr=1e-3, weight_decay=1e-4)
    scheduler = optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=15, eta_min=1e-5)

    best_val_acc = 0.0
    best_weights = None

    print("Training MineralConvNet with data augmentations for 15 epochs...", flush=True)
    for epoch in range(15):
        model.train()
        train_loss, train_correct, train_total = 0.0, 0, 0
        for x, y in train_loader:
            x, y = x.to(device), y.to(device)
            optimizer.zero_grad()
            out = model(x)
            loss = criterion(out, y)
            loss.backward()
            optimizer.step()
            train_loss += loss.item() * x.size(0)
            _, preds = torch.max(out, 1)
            train_correct += torch.sum(preds == y).item()
            train_total += x.size(0)

        scheduler.step()

        model.eval()
        val_loss, val_correct, val_total = 0.0, 0, 0
        with torch.no_grad():
            for x, y in val_loader:
                x, y = x.to(device), y.to(device)
                out = model(x)
                loss = criterion(out, y)
                val_loss += loss.item() * x.size(0)
                _, preds = torch.max(out, 1)
                val_correct += torch.sum(preds == y).item()
                val_total += x.size(0)

        val_acc = (val_correct / val_total) * 100
        print(f"Epoch {epoch+1:02d}/15 | Train Acc: {(train_correct/train_total)*100:6.2f}% | Val Acc: {val_acc:6.2f}% | Val Loss: {val_loss/val_total:.4f}", flush=True)
        if val_acc >= best_val_acc:
            best_val_acc = val_acc
            best_weights = model.state_dict().copy()

    model.load_state_dict(best_weights)
    torch.save(model.state_dict(), "models/mineral_convnet_augmented.pth")
    print(f"Saved augmented ConvNet -> models/mineral_convnet_augmented.pth (Best Val Acc: {best_val_acc:.2f}%)", flush=True)

if __name__ == "__main__":
    experiment_convnet_augmented()

