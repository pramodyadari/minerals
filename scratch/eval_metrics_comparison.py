import glob
import sys
import os
import torch
import numpy as np
from PIL import Image, ImageEnhance, ImageDraw

sys.path.insert(0, 'ai')
from train import MineralConvNet, CLASSES

m = MineralConvNet(4)
m.load_state_dict(torch.load('models/mineral_image_classifier.pth', map_location='cpu'))
m.eval()

mean = np.array([0.485, 0.456, 0.406], dtype=np.float32)
std = np.array([0.229, 0.224, 0.225], dtype=np.float32)

def extract(im):
    arr = (np.array(im.convert('RGB').resize((224, 224)), dtype=np.float32)/255.0 - mean)/std
    t = torch.from_numpy(arr).permute(2,0,1).unsqueeze(0)
    with torch.no_grad():
        f256 = torch.flatten(m.features(t), 1)
        h128 = m.classifier[2](m.classifier[1](f256))
        logits = m.classifier[4](h128)
        probs = torch.softmax(logits, dim=1).squeeze(0).numpy()
    return f256.squeeze(0).numpy(), h128.squeeze(0).numpy(), logits.squeeze(0).numpy(), probs

with open('models/mineral_classifier_ood_config.json') as f:
    import json
    cfg = json.load(f)

raw_centroids = {c: np.array(cfg['centroids'][c]) for c in CLASSES}
norm_centroids = {c: raw_centroids[c] / (np.linalg.norm(raw_centroids[c]) + 1e-8) for c in CLASSES}

def calc_metrics(h, logits):
    norm_h = h / (np.linalg.norm(h) + 1e-8)
    # Cosine distance to each centroid
    cos_dists = {c: 1.0 - float(np.dot(norm_h, norm_centroids[c])) for c in CLASSES}
    closest_c = min(cos_dists, key=cos_dists.get)
    min_cos_dist = cos_dists[closest_c]
    
    # Perpendicular distance to closest centroid ray
    c_vec = raw_centroids[closest_c]
    norm_c = c_vec / (np.linalg.norm(c_vec) + 1e-8)
    h_proj = np.dot(h, norm_c) * norm_c
    h_perp = np.linalg.norm(h - h_proj)
    
    # Raw Euclidean distance to closest centroid
    raw_dists = {c: float(np.linalg.norm(h - raw_centroids[c])) for c in CLASSES}
    min_raw_dist = min(raw_dists.values())
    
    # Logit margin
    s_logits = np.sort(logits)
    margin = float(s_logits[-1] - s_logits[-2])
    
    # Energy
    energy = -float(np.log(np.sum(np.exp(logits))))
    
    # Softmax max prob
    exp_l = np.exp(logits - np.max(logits))
    probs = exp_l / np.sum(exp_l)
    max_prob = float(np.max(probs))
    pred_c = CLASSES[np.argmax(probs)]
    
    return {
        'pred_class': pred_c,
        'max_prob': max_prob,
        'min_cos_dist': min_cos_dist,
        'h_perp': float(h_perp),
        'min_raw_dist': min_raw_dist,
        'margin': margin,
        'energy': energy,
        'norm_h': float(np.linalg.norm(h))
    }

print('=== 1. Standard Test Samples (40 samples) ===')
std_known = []
for c in CLASSES:
    for f in glob.glob(f'data/test/{c}/*.*'):
        _, h, l, _ = extract(Image.open(f))
        res = calc_metrics(h, l)
        res['class'] = c
        std_known.append(res)
print(f"Count: {len(std_known)}")
for c in CLASSES:
    sub = [s for s in std_known if s['class'] == c]
    print(f"  {c:10s}: RawDist max={max(s['min_raw_dist'] for s in sub):.2f}, CosDist max={max(s['min_cos_dist'] for s in sub):.4f}, PerpDist max={max(s['h_perp'] for s in sub):.2f}")

print('\n=== 2. Exposure & Specular Perturbations (40 samples x 4 factors = 160 samples) ===')
pert_known = []
for c in CLASSES:
    for f in glob.glob(f'data/test/{c}/*.*'):
        base = Image.open(f)
        for factor in [0.70, 0.80, 0.90, 1.20]:
            mod = ImageEnhance.Brightness(base).enhance(factor)
            if factor == 0.70:
                draw = ImageDraw.Draw(mod)
                draw.ellipse([80, 80, 88, 85], fill=(220, 230, 240))
            _, h, l, _ = extract(mod)
            res = calc_metrics(h, l)
            res['class'] = c
            res['factor'] = factor
            pert_known.append(res)
print(f"Count: {len(pert_known)}")
for c in CLASSES:
    sub = [s for s in pert_known if s['class'] == c]
    print(f"  {c:10s}: RawDist max={max(s['min_raw_dist'] for s in sub):.2f}, CosDist max={max(s['min_cos_dist'] for s in sub):.4f}, PerpDist max={max(s['h_perp'] for s in sub):.2f}")

print('\n=== 3. Out-of-Distribution Samples (60 samples + noise + white) ===')
ood_samples = []
for ood in ['quartz', 'granite', 'limestone', 'sandstone', 'basalt']:
    for f in glob.glob(f'data/evaluation/ood/{ood}/*.*'):
        _, h, l, _ = extract(Image.open(f))
        res = calc_metrics(h, l)
        res['rock'] = ood
        ood_samples.append(res)

for name, raw in [('uniform_white', np.ones((224,224,3), dtype=np.uint8)*245), ('noise', np.clip(np.random.normal(128,40,(224,224,3)),0,255).astype(np.uint8))]:
    _, h, l, _ = extract(Image.fromarray(raw))
    res = calc_metrics(h, l)
    res['rock'] = name
    ood_samples.append(res)

print(f"Count: {len(ood_samples)}")
for rock in ['quartz', 'granite', 'limestone', 'sandstone', 'basalt', 'uniform_white', 'noise']:
    sub = [s for s in ood_samples if s['rock'] == rock]
    print(f"  {rock:14s}: RawDist min={min(s['min_raw_dist'] for s in sub):.2f}, CosDist min={min(s['min_cos_dist'] for s in sub):.4f}, PerpDist min={min(s['h_perp'] for s in sub):.2f}, Pred={sub[0]['pred_class']}")
