import glob
import numpy as np
import torch
import sys
sys.path.insert(0, 'ai')
from train import MineralConvNet, CLASSES
from evaluate_ood_detection import FeatureExtractor, load_and_preprocess

m = MineralConvNet(4)
m.load_state_dict(torch.load('models/mineral_image_classifier.pth', map_location='cpu'))
m.eval()
ext = FeatureExtractor(m)

# Load centroids
with open('models/mineral_classifier_ood_config.json') as f:
    import json
    cfg = json.load(f)
centroids = {c: np.array(cfg['centroids'][c]) for c in CLASSES}

print("=== Alpha range for Training Samples ===")
for c in CLASSES:
    alphas = []
    c_vec = centroids[c]
    norm_c_sq = np.dot(c_vec, c_vec)
    for f in glob.glob(f"data/train/{c}/*.*"):
        t = load_and_preprocess(f)
        with torch.no_grad():
            _, h, _ = ext(t)
        h_vec = h.squeeze().numpy()
        alpha = np.dot(h_vec, c_vec) / norm_c_sq
        alphas.append(alpha)
    print(f"  {c:10s} (N={len(alphas)}): min={np.min(alphas):.4f}, mean={np.mean(alphas):.4f}, max={np.max(alphas):.4f}, std={np.std(alphas):.4f}")

print("\n=== Alpha range for Normal Validation Samples ===")
for c in CLASSES:
    alphas = []
    c_vec = centroids[c]
    norm_c_sq = np.dot(c_vec, c_vec)
    for f in glob.glob(f"data/validation/{c}/*.*"):
        t = load_and_preprocess(f)
        with torch.no_grad():
            _, h, _ = ext(t)
        h_vec = h.squeeze().numpy()
        alpha = np.dot(h_vec, c_vec) / norm_c_sq
        alphas.append(alpha)
    print(f"  {c:10s} (N={len(alphas)}): min={np.min(alphas):.4f}, mean={np.mean(alphas):.4f}, max={np.max(alphas):.4f}, std={np.std(alphas):.4f}")

print("\n=== Alpha for OOD Rocks against closest candidate ===")
for ood in ["quartz", "granite", "limestone", "sandstone", "basalt"]:
    alphas = []
    closest_classes = []
    for f in glob.glob(f"data/evaluation/ood/{ood}/*.*"):
        t = load_and_preprocess(f)
        with torch.no_grad():
            _, h, logits = ext(t)
        h_vec = h.squeeze().numpy()
        best_alpha = None
        best_dist = 1e9
        best_c = None
        for c in CLASSES:
            c_vec = centroids[c]
            norm_c_sq = np.dot(c_vec, c_vec)
            a = np.dot(h_vec, c_vec) / norm_c_sq
            proj = a * c_vec
            d = np.linalg.norm(h_vec - proj)
            if d < best_dist:
                best_dist = d
                best_alpha = a
                best_c = c
        alphas.append(best_alpha)
        closest_classes.append(best_c)
    print(f"  {ood:10s} (N={len(alphas)}): closest={closest_classes[0]}, alpha min={np.min(alphas):.4f}, mean={np.mean(alphas):.4f}, max={np.max(alphas):.4f}")
