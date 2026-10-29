import glob
import os
import sys
sys.path.insert(0, os.path.abspath('.'))
import numpy as np
import torch
from PIL import Image
from backend.app.vision_service import compute_scale_robust_distance, get_ood_config, get_model, CLASSES

cfg = get_ood_config()
c_mng = np.array(cfg['centroids']['manganese'])
bounds_mng = cfg['scale_bounds']['manganese']
model = get_model()

ood_files = glob.glob('data/evaluation/ood/*/*.*')
mng_dists = []

for f in ood_files:
    rock = os.path.basename(os.path.dirname(f))
    im = Image.open(f).convert('RGB').resize((224, 224))
    mean = np.array([0.485, 0.456, 0.406], dtype=np.float32)
    std = np.array([0.229, 0.224, 0.225], dtype=np.float32)
    arr = (np.array(im, dtype=np.float32) / 255.0 - mean) / std
    t = torch.from_numpy(arr).permute(2,0,1).unsqueeze(0)
    with torch.no_grad():
        f256 = torch.flatten(model.features(t), 1)
        h128 = model.classifier[2](model.classifier[1](f256))
        h_vec = h128.squeeze().numpy()
    d, a, dp = compute_scale_robust_distance(h_vec, c_mng, bounds_mng)
    mng_dists.append((rock, d, a, dp))

print(f"{'Rock':12s} | {'Min Dist to Manganese':22s} | {'Mean Dist':10s} | {'Max Dist':10s}")
print("-" * 65)
for rock in ['quartz', 'granite', 'limestone', 'sandstone', 'basalt']:
    sub = [d for r, d, a, dp in mng_dists if r == rock]
    print(f"{rock:12s} | {min(sub):22.2f} | {np.mean(sub):10.2f} | {max(sub):10.2f}")
