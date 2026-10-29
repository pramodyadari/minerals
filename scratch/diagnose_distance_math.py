import os, sys
import numpy as np
import torch
import torch.nn.functional as F
from PIL import Image

sys.path.insert(0, os.path.abspath('.'))
from backend.app.vision_service import get_model, get_ood_config, CLASSES, CLASS_DISPLAY

model = get_model()
cfg = get_ood_config()
tau = cfg['rejection_threshold_tau']
pen_weight = cfg.get('scale_penalty_weight', 25.0)

mean = np.array([0.485, 0.456, 0.406], dtype=np.float32)
std = np.array([0.229, 0.224, 0.225], dtype=np.float32)

def evaluate_sample(img_path, label=""):
    print("=" * 105)
    print(f"SAMPLE: {img_path} ({label})")
    with Image.open(img_path) as im:
        rgb = im.convert('RGB').resize((224, 224))
        arr = (np.array(rgb, dtype=np.float32) / 255.0 - mean) / std
        t = torch.from_numpy(arr).permute(2,0,1).unsqueeze(0).float()
    
    with torch.no_grad():
        f256 = torch.flatten(model.features(t), 1)
        h128 = model.classifier[2](model.classifier[1](f256))
        logits = model.classifier[4](h128).squeeze(0).cpu().numpy()
        probs = F.softmax(torch.tensor(logits), dim=0).numpy()
        h_vec = h128.squeeze(0).cpu().numpy()

    h_norm = float(np.linalg.norm(h_vec))
    print(f"Embedding Norm ||h||: {h_norm:.4f} | Non-zero entries: {np.count_nonzero(h_vec)}/128")
    print("-" * 105)
    header = f"{'Class':10s} | {'Centroid_Norm':13s} | {'Alpha':8s} | {'Clamped':8s} | {'d_perp':8s} | {'Penalty':8s} | {'Dist':8s} | {'Tau':5s} | {'Decision':10s} | {'Softmax':7s}"
    print(header)
    print("-" * 105)
    for i, cls in enumerate(CLASSES):
        c_vec = np.array(cfg['centroids'][cls], dtype=np.float32)
        c_norm = float(np.linalg.norm(c_vec))
        norm_c_sq = float(np.dot(c_vec, c_vec) + 1e-8)
        alpha = float(np.dot(h_vec, c_vec) / norm_c_sq)
        is_clamped = "Yes(0.0)" if alpha < 0 else "No"
        h_proj = max(0.0, alpha) * c_vec
        d_perp = float(np.linalg.norm(h_vec - h_proj))
        
        sb = cfg['scale_bounds'][cls]
        pen = 0.0
        if alpha < sb[0]:
            pen = (sb[0] - alpha) * pen_weight
        elif alpha > sb[1]:
            pen = (alpha - sb[1]) * pen_weight
        
        total_d = d_perp + pen
        decision = "ACCEPT" if total_d <= tau else "REJECT"
        row = f"{CLASS_DISPLAY[cls]:10s} | {c_norm:13.4f} | {alpha:8.4f} | {is_clamped:8s} | {d_perp:8.4f} | {pen:8.4f} | {total_d:8.4f} | {tau:5.1f} | {decision:10s} | {probs[i]*100:6.2f}%"
        print(row)

evaluate_sample('data/uploads/20261026_161612_c31314697563_2a95d3e8-610f-4bff-9bc7-c9700e76d534.png', 'DISPUTED SPECIMEN')
evaluate_sample('data/test/manganese/manganese_test_000.jpg', 'VERIFIED MANGANESE REFERENCE')
evaluate_sample('data/validation/manganese/manganese_validation_000.jpg', 'VERIFIED MANGANESE VALIDATION')
evaluate_sample('data/evaluation/ood/basalt/basalt_000.jpg', 'BASALT OOD CONTROL #0')
evaluate_sample('data/evaluation/ood/basalt/basalt_002.jpg', 'BASALT OOD CONTROL #2')
