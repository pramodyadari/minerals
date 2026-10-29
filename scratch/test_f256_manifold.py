import os
import sys
import glob
import numpy as np
import torch
from PIL import Image, ImageEnhance, ImageDraw

sys.path.insert(0, ".")
from ai.train import MineralConvNet, CLASSES
from ai.evaluate_ood_detection import FeatureExtractor, load_and_preprocess

device = torch.device("cpu")
base_model = MineralConvNet(num_classes=len(CLASSES))
base_model.load_state_dict(torch.load("models/mineral_image_classifier.pth", map_location=device))
base_model.eval()
extractor = FeatureExtractor(base_model)
extractor.eval()

# Compute centroids for both f256 and h128
train_f256 = {c: [] for c in CLASSES}
train_h128 = {c: [] for c in CLASSES}
for cls in CLASSES:
    for f in glob.glob(f"data/train/{cls}/*.*"):
        t = load_and_preprocess(f)
        with torch.no_grad():
            f256, h128, _ = extractor(t)
        train_f256[cls].append(f256.squeeze().numpy())
        train_h128[cls].append(h128.squeeze().numpy())

c_f256 = {c: np.mean(train_f256[c], axis=0) for c in CLASSES}
c_h128 = {c: np.mean(train_h128[c], axis=0) for c in CLASSES}

def manifold_ray_dist(vec, c_vec, min_alpha=0.35, max_alpha=1.80, pen_weight=8.0):
    norm_c_sq = float(np.dot(c_vec, c_vec) + 1e-8)
    alpha = float(np.dot(vec, c_vec) / norm_c_sq)
    proj = max(0.0, alpha) * c_vec
    d_perp = float(np.linalg.norm(vec - proj))
    rad_pen = 0.0
    if alpha < min_alpha:
        rad_pen = (min_alpha - alpha) * pen_weight
    elif alpha > max_alpha:
        rad_pen = (alpha - max_alpha) * pen_weight
    return d_perp + rad_pen, alpha, d_perp

def eval_tensor(t):
    with torch.no_grad():
        f256, h128, logits = extractor(t)
    f_vec = f256.squeeze().numpy()
    h_vec = h128.squeeze().numpy()
    
    # Distance in h128
    d_h128_list = [manifold_ray_dist(h_vec, c_h128[c]) for c in CLASSES]
    min_idx_h = int(np.argmin([d[0] for d in d_h128_list]))
    d_h128 = d_h128_list[min_idx_h][0]
    
    # Distance in f256 (for the candidate class or min over classes)
    d_f256_list = [manifold_ray_dist(f_vec, c_f256[c]) for c in CLASSES]
    min_idx_f = int(np.argmin([d[0] for d in d_f256_list]))
    d_f256 = d_f256_list[min_idx_f][0]
    d_f256_cand = d_f256_list[min_idx_h][0]

    return {
        "candidate": CLASSES[min_idx_h],
        "d_h128": d_h128,
        "d_f256": d_f256,
        "d_f256_cand": d_f256_cand,
        "alpha_h": d_h128_list[min_idx_h][1],
        "alpha_f": d_f256_list[min_idx_h][1]
    }

print("Comparing d_h128 and d_f256 across all groups:")
groups = {
    "val_known": [load_and_preprocess(f) for c in CLASSES for f in glob.glob(f"data/validation/{c}/*.*")],
    "test_known": [load_and_preprocess(f) for c in CLASSES for f in glob.glob(f"data/test/{c}/*.*")],
    "ood_quartz": [load_and_preprocess(f) for f in glob.glob("data/evaluation/ood/quartz/*.*")],
    "ood_granite": [load_and_preprocess(f) for f in glob.glob("data/evaluation/ood/granite/*.*")],
    "ood_limestone": [load_and_preprocess(f) for f in glob.glob("data/evaluation/ood/limestone/*.*")],
    "ood_sandstone": [load_and_preprocess(f) for f in glob.glob("data/evaluation/ood/sandstone/*.*")],
    "ood_basalt": [load_and_preprocess(f) for f in glob.glob("data/evaluation/ood/basalt/*.*")],
}

# Dark shiny test set for all 4 classes
dark_shiny_all = []
for c in CLASSES:
    for f in glob.glob(f"data/test/{c}/*.*"):
        im = Image.open(f)
        d = ImageEnhance.Brightness(im).enhance(0.72)
        draw = ImageDraw.Draw(d)
        draw.ellipse([80, 80, 88, 85], fill=(220, 230, 240))
        dark_shiny_all.append(load_and_preprocess(d))
groups["dark_shiny_known_4cls"] = dark_shiny_all

for gname, tensors in groups.items():
    res = [eval_tensor(t) for t in tensors]
    h_vals = [r["d_h128"] for r in res]
    f_vals = [r["d_f256_cand"] for r in res]
    print(f"{gname:22s} | h128: min={np.min(h_vals):6.2f}, mean={np.mean(h_vals):6.2f}, max={np.max(h_vals):6.2f} | f256: min={np.min(f_vals):6.2f}, mean={np.mean(f_vals):6.2f}, max={np.max(f_vals):6.2f}")
