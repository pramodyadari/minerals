import glob
import numpy as np
import torch
from PIL import Image, ImageEnhance, ImageDraw
import sys
sys.path.insert(0, 'ai')
from train import MineralConvNet, CLASSES
from evaluate_ood_detection import FeatureExtractor, load_and_preprocess

m = MineralConvNet(4)
m.load_state_dict(torch.load('models/mineral_image_classifier.pth', map_location='cpu'))
m.eval()
ext = FeatureExtractor(m)

# Load training data to compute class-specific stats
train_h = {c: [] for c in CLASSES}
for c in CLASSES:
    for f in glob.glob(f"data/train/{c}/*.*"):
        t = load_and_preprocess(f)
        with torch.no_grad():
            _, h, _ = ext(t)
        train_h[c].append(h.squeeze().numpy())

centroids = {c: np.mean(train_h[c], axis=0) for c in CLASSES}

# Let's inspect class-specific alpha bounds and perpendicular variance
class_stats = {}
for c in CLASSES:
    c_vec = centroids[c]
    norm_c_sq = np.dot(c_vec, c_vec)
    alphas = []
    d_perps = []
    perp_vecs = []
    for h in train_h[c]:
        alpha = np.dot(h, c_vec) / norm_c_sq
        proj = alpha * c_vec
        perp = h - proj
        alphas.append(alpha)
        d_perps.append(np.linalg.norm(perp))
        perp_vecs.append(perp)
    
    # Also evaluate on validation set to see natural spread
    val_alphas = []
    val_d_perps = []
    for f in glob.glob(f"data/validation/{c}/*.*"):
        t = load_and_preprocess(f)
        with torch.no_grad():
            _, h, _ = ext(t)
        h_vec = h.squeeze().numpy()
        a = np.dot(h_vec, c_vec) / norm_c_sq
        p = np.linalg.norm(h_vec - a * c_vec)
        val_alphas.append(a)
        val_d_perps.append(p)
        
    class_stats[c] = {
        "train_alpha_range": (min(alphas), max(alphas)),
        "val_alpha_range": (min(val_alphas), max(val_alphas)),
        "train_dperp_max": max(d_perps),
        "val_dperp_max": max(val_d_perps),
        "perp_std": np.std(d_perps)
    }

print("Class Statistics (Train & Val):")
for c, s in class_stats.items():
    print(f"  {c:10s}: Train alpha=[{s['train_alpha_range'][0]:.3f}, {s['train_alpha_range'][1]:.3f}] | Val alpha=[{s['val_alpha_range'][0]:.3f}, {s['val_alpha_range'][1]:.3f}] | Val d_perp max={s['val_dperp_max']:.3f}")
