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

# Calibrated class-conditional scale bounds
scale_bounds = {
    "coal": (0.85, 1.15),
    "manganese": (0.20, 1.40),
    "iron_ore": (0.30, 1.40),
    "bauxite": (0.10, 1.40)
}

def evaluate_detector(img_input, tau=5.00):
    if isinstance(img_input, str):
        im = Image.open(img_input)
    else:
        im = img_input
    t = load_and_preprocess(im)
    with torch.no_grad():
        _, h, logits = ext(t)
    h_vec = h.squeeze().numpy()
    probs = torch.softmax(logits, dim=-1).squeeze().numpy()
    top_pred_idx = int(np.argmax(probs))
    top_pred_cls = CLASSES[top_pred_idx]
    
    dists = {}
    alphas = {}
    d_perps = {}
    for c in CLASSES:
        cv = c_h[c]
        norm_c_sq = float(np.dot(cv, cv) + 1e-8)
        alpha = float(np.dot(h_vec, cv) / norm_c_sq)
        proj = max(0.0, alpha) * cv
        d_perp = float(np.linalg.norm(h_vec - proj))
        
        b_low, b_high = scale_bounds[c]
        pen = 0.0
        if alpha < b_low:
            pen = (b_low - alpha) * 25.0
        elif alpha > b_high:
            pen = (alpha - b_high) * 25.0
            
        dists[c] = float(d_perp + pen)
        alphas[c] = alpha
        d_perps[c] = d_perp
        
    closest_c = min(dists, key=dists.get)
    min_dist = dists[closest_c]
    is_accepted = bool(min_dist <= tau)
    
    return {
        "pred_cls": top_pred_cls,
        "closest_c": closest_c,
        "confidence": float(probs[top_pred_idx]),
        "min_dist": min_dist,
        "is_accepted": is_accepted,
        "alpha": alphas[closest_c],
        "d_perp": d_perps[closest_c]
    }

print("=" * 70)
print("EVALUATION ON HELD-OUT TEST SET WITH CLASS-CONDITIONAL SCALE BOUNDS")
print("=" * 70)

# 1. Standard Test Set (40 samples)
test_known = []
for c in CLASSES:
    fpaths = sorted(glob.glob(f"data/test/{c}/*.*"))
    for f in fpaths:
        r = evaluate_detector(f)
        r["true_cls"] = c
        r["is_ood"] = False
        test_known.append(r)

fr_std = sum(1 for s in test_known if not s["is_accepted"])
print(f"Standard Test Known (N={len(test_known)}): False Rejections = {fr_std} ({fr_std/len(test_known)*100:.2f}%)")
for c in CLASSES:
    c_samples = [s for s in test_known if s["true_cls"] == c]
    c_fr = sum(1 for s in c_samples if not s["is_accepted"])
    c_max_d = max(s["min_dist"] for s in c_samples)
    print(f"  {c:10s} (N={len(c_samples)}): FR={c_fr}, max_dist={c_max_d:.2f}")

# 2. Dark shiny Manganese specimen (reproducing bug)
base_mng = Image.open(glob.glob("data/test/manganese/*.*")[0])
dark_shiny = ImageEnhance.Brightness(base_mng).enhance(0.72)
draw = ImageDraw.Draw(dark_shiny)
draw.ellipse([80, 80, 88, 85], fill=(220, 230, 240))
r_ds = evaluate_detector(dark_shiny)
print(f"\nDark Shiny Manganese Bug Specimen:")
print(f"  Pred={r_ds['pred_cls']}, Conf={r_ds['confidence']*100:.2f}%, Dist={r_ds['min_dist']:.2f}, Accepted={r_ds['is_accepted']}")

# 3. Exposure Perturbations on Test Set (120 samples: 0.75x, 0.85x, 1.20x)
test_pert = []
for c in CLASSES:
    for f in glob.glob(f"data/test/{c}/*.*"):
        im = Image.open(f)
        for factor in [0.75, 0.85, 1.20]:
            mod = ImageEnhance.Brightness(im).enhance(factor)
            r = evaluate_detector(mod)
            r["true_cls"] = c
            test_pert.append(r)
fr_pert = sum(1 for s in test_pert if not s["is_accepted"])
print(f"\nExposure Perturbations on Test Set (N={len(test_pert)}): False Rejections = {fr_pert} ({fr_pert/len(test_pert)*100:.2f}%)")

# 4. Held-out OOD Test Set (last 6 of each rock, N=30)
test_ood = []
for ood in ["quartz", "granite", "limestone", "sandstone", "basalt"]:
    fpaths = sorted(glob.glob(f"data/evaluation/ood/{ood}/*.*"))
    for f in fpaths[6:]: # Second half (held-out test split)
        r = evaluate_detector(f)
        r["true_cls"] = ood
        test_ood.append(r)

print(f"\nHeld-out OOD Rocks Test Set (N={len(test_ood)}):")
for ood in ["quartz", "granite", "limestone", "sandstone", "basalt"]:
    sub = [s for s in test_ood if s["true_cls"] == ood]
    rej = sum(1 for s in sub if not s["is_accepted"])
    fa = len(sub) - rej
    print(f"  {ood:10s} (N={len(sub)}): Rejected={rej}/{len(sub)} ({rej/len(sub)*100:.1f}%), FA={fa}, min_dist={min(s['min_dist'] for s in sub):.2f}, mean_dist={np.mean([s['min_dist'] for s in sub]):.2f}")

# 5. Synthetic Extremes
r_w = evaluate_detector(Image.fromarray(np.ones((224, 224, 3), dtype=np.uint8) * 245))
print(f"\nUniform White: Dist={r_w['min_dist']:.2f}, Accepted={r_w['is_accepted']}")
r_n = evaluate_detector(Image.fromarray(np.clip(np.random.normal(128, 40, (224, 224, 3)), 0, 255).astype(np.uint8)))
print(f"Gaussian Noise: Dist={r_n['min_dist']:.2f}, Accepted={r_n['is_accepted']}")
