import os, numpy as np, torch, torch.nn.functional as F
from PIL import Image
import sys
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from backend.app.vision_service import get_model, get_ood_config, compute_scale_robust_distance, CLASSES, CLASS_DISPLAY
from scratch.test_segmenter import segment_rock_specimen

p = 'data/uploads/20261026_161612_c31314697563_2a95d3e8-610f-4bff-9bc7-c9700e76d534.png'
im = Image.open(p).convert('RGB')
crop, diag = segment_rock_specimen(im)

model = get_model()
ood_cfg = get_ood_config()
centroids = ood_cfg['centroids']
scale_bounds = ood_cfg['scale_bounds']
tau = float(ood_cfg.get('rejection_threshold_tau', 5.0))

mean = np.array([0.485, 0.456, 0.406], dtype=np.float32)
std = np.array([0.229, 0.224, 0.225], dtype=np.float32)

def eval_one(img_in, label):
    arr = (np.array(img_in.resize((224, 224)), dtype=np.float32) / 255.0 - mean) / std
    tensor = torch.from_numpy(arr).permute(2, 0, 1).unsqueeze(0).float()
    with torch.no_grad():
        f256 = torch.flatten(model.features(tensor), 1)
        h128 = model.classifier[2](model.classifier[1](f256))
        logits = model.classifier[4](h128).squeeze(0)
        probs = F.softmax(logits, dim=0).cpu().numpy()
        h_vec = h128.squeeze(0).cpu().numpy()
    
    print(f'=== {label} ===')
    for i, c in enumerate(CLASSES):
        print(f'  {CLASS_DISPLAY[c]}: prob={probs[i]*100:.2f}%, logit={logits[i].item():.2f}')
    
    dists = {}
    for c in CLASSES:
        dist, alpha, d_perp = compute_scale_robust_distance(h_vec, np.array(centroids[c]), scale_bounds.get(c))
        dists[c] = (dist, alpha, d_perp)
        print(f'  Dist to {CLASS_DISPLAY[c]}: {dist:.4f} (alpha={alpha:.3f}, d_perp={d_perp:.3f})')
    best_c = min(dists, key=lambda k: dists[k][0])
    status = "OUT_OF_DISTRIBUTION" if dists[best_c][0] > tau else "ACCEPTED"
    print(f'  Closest Candidate: {CLASS_DISPLAY[best_c]}, Distance: {dists[best_c][0]:.4f}')
    print(f'  OOD Status: {status}')

eval_one(im, 'MANGANESE UPLOAD ORIGINAL')
eval_one(crop, 'MANGANESE UPLOAD CROPPED')

