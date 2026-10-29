import glob
import numpy as np
import torch
import torch.nn.functional as F
from PIL import Image, ImageEnhance, ImageDraw
import sys
sys.path.insert(0, 'ai')
from train import MineralConvNet, CLASSES
from evaluate_ood_detection import FeatureExtractor, load_and_preprocess

m = MineralConvNet(4)
m.load_state_dict(torch.load('models/mineral_image_classifier.pth', map_location='cpu'))
m.eval()
ext = FeatureExtractor(m)

# Training representations
train_h = {c: [] for c in CLASSES}
train_f = {c: [] for c in CLASSES}
train_logits = {c: [] for c in CLASSES}

for c in CLASSES:
    for f in glob.glob(f"data/train/{c}/*.*"):
        t = load_and_preprocess(f)
        with torch.no_grad():
            f256, h, logits = ext(t)
        train_h[c].append(h.squeeze().numpy())
        train_f[c].append(f256.squeeze().numpy())
        train_logits[c].append(logits.squeeze().numpy())

# Centroids
c_h = {c: np.mean(train_h[c], axis=0) for c in CLASSES}
c_f = {c: np.mean(train_f[c], axis=0) for c in CLASSES}

# Class-conditional covariance in h128
cov_h = {c: np.cov(np.array(train_h[c]), rowvar=False) + 1e-4 * np.eye(128) for c in CLASSES}
inv_cov_h = {c: np.linalg.pinv(cov_h[c]) for c in CLASSES}

# Pooled covariance in h128
pooled_diffs = np.vstack([np.array(train_h[c]) - c_h[c] for c in CLASSES])
pooled_cov_h = np.cov(pooled_diffs, rowvar=False) + 1e-4 * np.eye(128)
inv_pooled_cov_h = np.linalg.pinv(pooled_cov_h)

def compute_metrics_for_sample(img_input):
    if isinstance(img_input, str):
        im = Image.open(img_input)
    else:
        im = img_input
    t = load_and_preprocess(im)
    with torch.no_grad():
        f256, h, logits = ext(t)
    f_vec = f256.squeeze().numpy()
    h_vec = h.squeeze().numpy()
    z_vec = logits.squeeze().numpy()
    
    probs = F.softmax(logits, dim=-1).squeeze().numpy()
    pred_idx = np.argmax(probs)
    pred_c = CLASSES[pred_idx]
    
    # 1. Scale-robust manifold distance with class-conditional scale bounds
    # Class-conditional scale bounds calibrated from multi-exposure training/val:
    # coal: [0.85, 1.15]
    # manganese: [0.20, 1.40]
    # iron_ore: [0.30, 1.40]
    # bauxite: [0.10, 1.40]  # Notice at 1.0x normal bauxite is [0.89, 1.08]
    scale_bounds = {
        "coal": (0.85, 1.15),
        "manganese": (0.20, 1.40),
        "iron_ore": (0.30, 1.40),
        "bauxite": (0.10, 1.40)
    }
    
    ray_dists = {}
    for c in CLASSES:
        cv = c_h[c]
        norm_c_sq = np.dot(cv, cv)
        alpha = float(np.dot(h_vec, cv) / norm_c_sq)
        proj = max(0.0, alpha) * cv
        d_perp = float(np.linalg.norm(h_vec - proj))
        
        b_low, b_high = scale_bounds[c]
        pen = 0.0
        if alpha < b_low:
            pen = (b_low - alpha) * 25.0
        elif alpha > b_high:
            pen = (alpha - b_high) * 25.0
        ray_dists[c] = d_perp + pen
        
    closest_ray_c = min(ray_dists, key=ray_dists.get)
    min_ray_dist = ray_dists[closest_ray_c]
    
    # 2. Mahalanobis distance
    diff = h_vec - c_h[pred_c]
    maha_class = float(np.sqrt(np.maximum(0.0, diff.T @ inv_cov_h[pred_c] @ diff)))
    maha_pooled = float(np.sqrt(np.maximum(0.0, diff.T @ inv_pooled_cov_h @ diff)))
    
    # 3. Energy Score: -log(sum(exp(z)))
    energy = -float(torch.logsumexp(logits, dim=-1).item())
    
    # 4. Softmax max prob
    msp = float(np.max(probs))
    
    # 5. Convolutional residual in f256: 1.0 - cos(f_vec, c_f)
    f_norm = f_vec / (np.linalg.norm(f_vec) + 1e-8)
    cf_norm = c_f[pred_c] / (np.linalg.norm(c_f[pred_c]) + 1e-8)
    f256_cos_dist = float(1.0 - np.dot(f_norm, cf_norm))
    
    return {
        "pred": pred_c,
        "msp": msp,
        "ray_dist": min_ray_dist,
        "closest_ray": closest_ray_c,
        "maha_class": maha_class,
        "maha_pooled": maha_pooled,
        "energy": energy,
        "f256_cos": f256_cos_dist
    }

# Evaluate on Validation Set (Known + OOD)
val_samples = []
for c in CLASSES:
    for f in glob.glob(f"data/validation/{c}/*.*"):
        im = Image.open(f)
        m_std = compute_metrics_for_sample(im)
        m_std["label"] = c
        m_std["is_ood"] = False
        val_samples.append(m_std)
        
        # Exposure perturbations on validation
        im_dark = ImageEnhance.Brightness(im).enhance(0.72)
        if c == "manganese":
            draw = ImageDraw.Draw(im_dark)
            draw.ellipse([80, 80, 88, 85], fill=(220, 230, 240))
        m_dark = compute_metrics_for_sample(im_dark)
        m_dark["label"] = c
        m_dark["is_ood"] = False
        val_samples.append(m_dark)

ood_val_samples = []
for ood in ["quartz", "granite", "limestone", "sandstone", "basalt"]:
    fpaths = sorted(glob.glob(f"data/evaluation/ood/{ood}/*.*"))
    for f in fpaths[:6]: # First half for validation
        m_ood = compute_metrics_for_sample(f)
        m_ood["label"] = ood
        m_ood["is_ood"] = True
        ood_val_samples.append(m_ood)

print(f"Validation summary with Class-Conditional Scale Bounds:")
print(f"Known (N={len(val_samples)}): ray_dist max={max(s['ray_dist'] for s in val_samples):.2f}, mean={np.mean([s['ray_dist'] for s in val_samples]):.2f}")
print("OOD Rocks on validation split (N=30, 6 per rock):")
for ood in ["quartz", "granite", "limestone", "sandstone", "basalt"]:
    sub = [s for s in ood_val_samples if s["label"] == ood]
    print(f"  {ood:10s}: ray_dist min={min(s['ray_dist'] for s in sub):.2f}, mean={np.mean([s['ray_dist'] for s in sub]):.2f}, max={max(s['ray_dist'] for s in sub):.2f} (closest={sub[0]['closest_ray']})")
