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

# Centroids
with open('models/mineral_classifier_ood_config.json') as f:
    import json
    cfg = json.load(f)
centroids = {c: np.array(cfg['centroids'][c]) for c in CLASSES}

print(f"{'Class':10s} | {'Factor':6s} | {'alpha_min':9s} | {'alpha_mean':10s} | {'alpha_max':9s} | {'d_perp_max':10s}")
print("-" * 65)

for c in CLASSES:
    fpaths = glob.glob(f"data/validation/{c}/*.*")
    c_vec = centroids[c]
    norm_c_sq = np.dot(c_vec, c_vec)
    for factor in [0.70, 0.75, 0.85, 1.00, 1.20]:
        alphas = []
        d_perps = []
        for f in fpaths:
            base = Image.open(f)
            mod = ImageEnhance.Brightness(base).enhance(factor)
            if factor <= 0.75 and c == "manganese":
                draw = ImageDraw.Draw(mod)
                draw.ellipse([80, 80, 88, 85], fill=(220, 230, 240))
            t = load_and_preprocess(mod)
            with torch.no_grad():
                _, h, _ = ext(t)
            h_vec = h.squeeze().numpy()
            alpha = np.dot(h_vec, c_vec) / norm_c_sq
            proj = alpha * c_vec
            d_perp = np.linalg.norm(h_vec - proj)
            alphas.append(alpha)
            d_perps.append(d_perp)
        print(f"{c:10s} | {factor:6.2f} | {np.min(alphas):9.4f} | {np.mean(alphas):10.4f} | {np.max(alphas):9.4f} | {np.max(d_perps):10.4f}")
