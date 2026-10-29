import os
import sys
import glob
import numpy as np
import torch
import torch.nn.functional as F
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

# Collect training features for centroids, covariances, etc.
train_f256 = {c: [] for c in CLASSES}
train_h128 = {c: [] for c in CLASSES}
train_logits = {c: [] for c in CLASSES}

for cls in CLASSES:
    for f in glob.glob(f"data/train/{cls}/*.*"):
        t = load_and_preprocess(f)
        with torch.no_grad():
            f256, h128, logits = extractor(t)
        train_f256[cls].append(f256.squeeze().numpy())
        train_h128[cls].append(h128.squeeze().numpy())
        train_logits[cls].append(logits.squeeze().numpy())

# Centroids
c_h128 = {c: np.mean(train_h128[c], axis=0) for c in CLASSES}
c_f256 = {c: np.mean(train_f256[c], axis=0) for c in CLASSES}

# Normalized Centroids
c_h128_norm = {c: c_h128[c] / (np.linalg.norm(c_h128[c]) + 1e-8) for c in CLASSES}
c_f256_norm = {c: c_f256[c] / (np.linalg.norm(c_f256[c]) + 1e-8) for c in CLASSES}

# Empirical Covariance for Mahalanobis
# In h128 (dim 128) with 140 samples, tied covariance or regularized covariance
all_h128_centered = []
for c in CLASSES:
    all_h128_centered.append(np.array(train_h128[c]) - c_h128[c])
all_h128_centered = np.vstack(all_h128_centered)
cov_h128 = np.cov(all_h128_centered, rowvar=False) + 1e-3 * np.eye(128)
inv_cov_h128 = np.linalg.pinv(cov_h128)

def extract_all_metrics(img_tensor):
    with torch.no_grad():
        f256, h128, logits = extractor(img_tensor)
    f_vec = f256.squeeze().numpy()
    h_vec = h128.squeeze().numpy()
    z_vec = logits.squeeze().numpy()
    
    # 1. Manifold Ray Distance (current)
    min_ray_dist = 1e9
    min_ray_cls = None
    for c in CLASSES:
        c_vec = c_h128[c]
        norm_c_sq = float(np.dot(c_vec, c_vec) + 1e-8)
        alpha = float(np.dot(h_vec, c_vec) / norm_c_sq)
        h_proj = max(0.0, alpha) * c_vec
        d_perp = float(np.linalg.norm(h_vec - h_proj))
        rad_pen = 0.0
        if alpha < 0.35:
            rad_pen = (0.35 - alpha) * 8.0
        elif alpha > 1.80:
            rad_pen = (alpha - 1.80) * 8.0
        d_total = d_perp + rad_pen
        if d_total < min_ray_dist:
            min_ray_dist = d_total
            min_ray_cls = c

    # 2. Cosine Distance on h128: 1 - cos(h, c)
    h_norm = h_vec / (np.linalg.norm(h_vec) + 1e-8)
    cos_dists_h128 = [1.0 - float(np.dot(h_norm, c_h128_norm[c])) for c in CLASSES]
    min_cos_h128 = min(cos_dists_h128)

    # 3. Cosine Distance on f256: 1 - cos(f, c_f)
    f_norm = f_vec / (np.linalg.norm(f_vec) + 1e-8)
    cos_dists_f256 = [1.0 - float(np.dot(f_norm, c_f256_norm[c])) for c in CLASSES]
    min_cos_f256 = min(cos_dists_f256)

    # 4. Energy score: -T * log(sum(exp(z/T))) with T=1
    energy = -float(torch.logsumexp(logits, dim=-1).item())

    # 5. Mahalanobis distance on h128
    maha_dists = []
    for c in CLASSES:
        diff = h_vec - c_h128[c]
        d_m = float(np.sqrt(np.maximum(0.0, diff.T @ inv_cov_h128 @ diff)))
        maha_dists.append(d_m)
    min_maha_h128 = min(maha_dists)

    # 6. Max Softmax Probability
    probs = F.softmax(logits, dim=-1).squeeze().numpy()
    msp = float(np.max(probs))

    # 7. Logit Margin: z_(1) - z_(2)
    sorted_z = np.sort(z_vec)
    margin = float(sorted_z[-1] - sorted_z[-2])

    # 8. Feature norm ratio: norm(h_vec) / norm(c_h128[pred_class])
    pred_c = CLASSES[np.argmax(probs)]
    norm_ratio = float(np.linalg.norm(h_vec) / np.linalg.norm(c_h128[pred_c]))

    return {
        "pred": pred_c,
        "msp": msp,
        "ray_dist": min_ray_dist,
        "cos_h128": min_cos_h128,
        "cos_f256": min_cos_f256,
        "energy": energy,
        "maha_h128": min_maha_h128,
        "margin": margin,
        "norm_ratio": norm_ratio,
        "logits": z_vec
    }

# Test across groups
groups = {
    "val_known_std": [load_and_preprocess(f) for c in CLASSES for f in glob.glob(f"data/validation/{c}/*.*")],
    "test_known_std": [load_and_preprocess(f) for c in CLASSES for f in glob.glob(f"data/test/{c}/*.*")],
    "ood_quartz": [load_and_preprocess(f) for f in glob.glob("data/evaluation/ood/quartz/*.*")],
    "ood_granite": [load_and_preprocess(f) for f in glob.glob("data/evaluation/ood/granite/*.*")],
    "ood_limestone": [load_and_preprocess(f) for f in glob.glob("data/evaluation/ood/limestone/*.*")],
    "ood_sandstone": [load_and_preprocess(f) for f in glob.glob("data/evaluation/ood/sandstone/*.*")],
    "ood_basalt": [load_and_preprocess(f) for f in glob.glob("data/evaluation/ood/basalt/*.*")],
}

# Add dark/shiny manganese
dark_shiny_tensors = []
for f in glob.glob("data/test/manganese/*.*"):
    im = Image.open(f)
    d = ImageEnhance.Brightness(im).enhance(0.72)
    draw = ImageDraw.Draw(d)
    draw.ellipse([80, 80, 88, 85], fill=(220, 230, 240))
    dark_shiny_tensors.append(load_and_preprocess(d))
groups["manganese_dark_shiny"] = dark_shiny_tensors

print(f"{'Group':22s} | {'RayDist':10s} | {'Cos_h128':10s} | {'Cos_f256':10s} | {'Energy':10s} | {'Maha_h128':10s} | {'NormRatio':10s}")
print("-" * 90)

for gname, tensors in groups.items():
    metrics = [extract_all_metrics(t) for t in tensors]
    mean_ray = np.mean([m["ray_dist"] for m in metrics])
    mean_cosh = np.mean([m["cos_h128"] for m in metrics])
    mean_cosf = np.mean([m["cos_f256"] for m in metrics])
    mean_ene = np.mean([m["energy"] for m in metrics])
    mean_maha = np.mean([m["maha_h128"] for m in metrics])
    mean_nr = np.mean([m["norm_ratio"] for m in metrics])
    print(f"{gname:22s} | {mean_ray:10.3f} | {mean_cosh:10.5f} | {mean_cosf:10.5f} | {mean_ene:10.3f} | {mean_maha:10.3f} | {mean_nr:10.3f}")
