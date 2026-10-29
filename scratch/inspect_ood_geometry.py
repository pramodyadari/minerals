import os
import sys
import glob
import numpy as np
import torch
from PIL import Image

sys.path.insert(0, ".")
from ai.train import MineralConvNet, CLASSES
from ai.evaluate_ood_detection import FeatureExtractor, load_and_preprocess, compute_class_centroids

device = torch.device("cpu")
base_model = MineralConvNet(num_classes=len(CLASSES))
base_model.load_state_dict(torch.load("models/mineral_image_classifier.pth", map_location=device))
base_model.eval()
extractor = FeatureExtractor(base_model)
extractor.eval()

centroids, variances = compute_class_centroids(extractor, device, data_dir="data")

print("Checking Basalt samples:")
basalt_files = glob.glob("data/evaluation/ood/basalt/*.*")
for f in basalt_files[:5]:
    t = load_and_preprocess(f)
    with torch.no_grad():
        f256, h128, logits = extractor(t)
    probs = torch.softmax(logits, dim=-1).squeeze().numpy()
    h = h128.squeeze().numpy()
    pred_idx = np.argmax(probs)
    print(f"Basalt {os.path.basename(f)}: pred={CLASSES[pred_idx]} prob={probs[pred_idx]:.4f} logits={logits.squeeze().numpy()} h_norm={np.linalg.norm(h):.2f}")

print("\nChecking Sandstone samples:")
sandstone_files = glob.glob("data/evaluation/ood/sandstone/*.*")
for f in sandstone_files[:5]:
    t = load_and_preprocess(f)
    with torch.no_grad():
        f256, h128, logits = extractor(t)
    probs = torch.softmax(logits, dim=-1).squeeze().numpy()
    h = h128.squeeze().numpy()
    pred_idx = np.argmax(probs)
    print(f"Sandstone {os.path.basename(f)}: pred={CLASSES[pred_idx]} prob={probs[pred_idx]:.4f} logits={logits.squeeze().numpy()} h_norm={np.linalg.norm(h):.2f}")

print("\nChecking Genuine Coal samples:")
coal_files = glob.glob("data/test/coal/*.*")
for f in coal_files[:3]:
    t = load_and_preprocess(f)
    with torch.no_grad():
        f256, h128, logits = extractor(t)
    probs = torch.softmax(logits, dim=-1).squeeze().numpy()
    h = h128.squeeze().numpy()
    pred_idx = np.argmax(probs)
    print(f"Coal {os.path.basename(f)}: pred={CLASSES[pred_idx]} prob={probs[pred_idx]:.4f} logits={logits.squeeze().numpy()} h_norm={np.linalg.norm(h):.2f}")

print("\nChecking Genuine Bauxite samples:")
bauxite_files = glob.glob("data/test/bauxite/*.*")
for f in bauxite_files[:3]:
    t = load_and_preprocess(f)
    with torch.no_grad():
        f256, h128, logits = extractor(t)
    probs = torch.softmax(logits, dim=-1).squeeze().numpy()
    h = h128.squeeze().numpy()
    pred_idx = np.argmax(probs)
    print(f"Bauxite {os.path.basename(f)}: pred={CLASSES[pred_idx]} prob={probs[pred_idx]:.4f} logits={logits.squeeze().numpy()} h_norm={np.linalg.norm(h):.2f}")
