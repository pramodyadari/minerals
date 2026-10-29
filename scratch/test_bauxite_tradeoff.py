import glob
import numpy as np
import torch
from PIL import Image, ImageEnhance
import sys
sys.path.insert(0, 'ai')
from train import MineralConvNet, CLASSES
from evaluate_ood_detection import FeatureExtractor, load_and_preprocess, compute_scale_robust_distance

m = MineralConvNet(4)
m.load_state_dict(torch.load('models/mineral_image_classifier.pth', map_location='cpu'))
m.eval()
ext = FeatureExtractor(m)

with open('models/mineral_classifier_ood_config.json') as f:
    import json
    cfg = json.load(f)
c_bauxite = np.array(cfg['centroids']['bauxite'])

for high_b in [1.40, 1.45, 1.50, 1.55, 1.60]:
    b_bounds = [0.10, high_b]
    # Check Sandstone (N=12)
    s_dists = []
    for f in glob.glob("data/evaluation/ood/sandstone/*.*"):
        t = load_and_preprocess(f)
        with torch.no_grad():
            _, h, _ = ext(t)
        d, a, dp = compute_scale_robust_distance(h.squeeze().numpy(), c_bauxite, b_bounds, penalty_weight=25.0)
        s_dists.append(d)
        
    # Check Normal Bauxite (N=10)
    norm_b_dists = []
    for f in glob.glob("data/test/bauxite/*.*"):
        t = load_and_preprocess(f)
        with torch.no_grad():
            _, h, _ = ext(t)
        d, a, dp = compute_scale_robust_distance(h.squeeze().numpy(), c_bauxite, b_bounds, penalty_weight=25.0)
        norm_b_dists.append(d)
        
    # Check 1.20x Bauxite (N=10)
    bright_b_dists = []
    for f in glob.glob("data/test/bauxite/*.*"):
        im = ImageEnhance.Brightness(Image.open(f)).enhance(1.20)
        t = load_and_preprocess(im)
        with torch.no_grad():
            _, h, _ = ext(t)
        d, a, dp = compute_scale_robust_distance(h.squeeze().numpy(), c_bauxite, b_bounds, penalty_weight=25.0)
        bright_b_dists.append(d)
        
    print(f"Bauxite high_bound={high_b:.2f}:")
    print(f"  Sandstone (N=12) dists: min={min(s_dists):.2f}, mean={np.mean(s_dists):.2f}")
    print(f"  Normal Bauxite (N=10) dists: max={max(norm_b_dists):.2f}")
    print(f"  1.20x Bauxite (N=10) dists: min={min(bright_b_dists):.2f}, max={max(bright_b_dists):.2f}")
