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

with open('models/mineral_classifier_ood_config.json') as f:
    import json
    cfg = json.load(f)
c_h = {c: np.array(cfg['centroids'][c]) for c in CLASSES}

scale_bounds = {
    "coal": (0.85, 1.15),
    "manganese": (0.20, 1.40),
    "iron_ore": (0.30, 1.40),
    "bauxite": (0.10, 1.40)
}

def eval_s(im, c_true):
    t = load_and_preprocess(im)
    with torch.no_grad():
        _, h, _ = ext(t)
    h_vec = h.squeeze().numpy()
    
    cv = c_h[c_true]
    norm_c_sq = np.dot(cv, cv)
    alpha = float(np.dot(h_vec, cv) / norm_c_sq)
    proj = max(0.0, alpha) * cv
    d_perp = float(np.linalg.norm(h_vec - proj))
    
    b_low, b_high = scale_bounds[c_true]
    pen = 0.0
    if alpha < b_low:
        pen = (b_low - alpha) * 25.0
    elif alpha > b_high:
        pen = (alpha - b_high) * 25.0
    return d_perp + pen, alpha, d_perp, pen

for c in CLASSES:
    fpaths = glob.glob(f"data/validation/{c}/*.*")
    for f in fpaths:
        base = Image.open(f)
        d_std, a_std, dp_std, p_std = eval_s(base, c)
        if d_std > 3.0:
            print(f"Standard {c} {f}: d={d_std:.2f}, alpha={a_std:.2f}, d_perp={dp_std:.2f}, pen={p_std:.2f}")
            
        im_dark = ImageEnhance.Brightness(base).enhance(0.72)
        if c == "manganese":
            draw = ImageDraw.Draw(im_dark)
            draw.ellipse([80, 80, 88, 85], fill=(220, 230, 240))
        d_dark, a_dark, dp_dark, p_dark = eval_s(im_dark, c)
        if d_dark > 3.0:
            print(f"Dark/pert {c} {f}: d={d_dark:.2f}, alpha={a_dark:.2f}, d_perp={dp_dark:.2f}, pen={p_dark:.2f}")
