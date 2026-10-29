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

def eval_geo(h, logits):
    norm_h = h / (np.linalg.norm(h) + 1e-8)
    # Class predicted by model
    pred_idx = np.argmax(logits)
    pred_c = CLASSES[pred_idx]
    
    # Measures for predicted class:
    c_vec = raw_centroids[pred_c]
    norm_c = norm_centroids[pred_c]
    
    # 1. Cosine similarity & distance
    cos_sim = float(np.dot(norm_h, norm_c))
    cos_dist = float(1.0 - cos_sim)
    
    # 2. Perpendicular distance to class ray
    h_proj = np.dot(h, norm_c) * norm_c
    h_perp = float(np.linalg.norm(h - h_proj))
    
    # 3. Relative perpendicular distance (perpendicular distance divided by projected length): tan(theta)
    tan_theta = h_perp / (float(np.dot(h, norm_c)) + 1e-5)
    
    # 4. Energy score
    energy = -float(np.log(np.sum(np.exp(logits))))
    
    # 5. Logit margin
    s_l = np.sort(logits)
    margin = float(s_l[-1] - s_l[-2])
    
    # 6. Raw distance
    raw_dist = float(np.linalg.norm(h - c_vec))
    
    return {
        'pred_class': pred_c,
        'conf': float(torch.softmax(torch.tensor(logits), dim=0)[pred_idx]),
        'cos_sim': cos_sim,
        'cos_dist': cos_dist,
        'h_perp': h_perp,
        'tan_theta': tan_theta,
        'margin': margin,
        'energy': energy,
        'raw_dist': raw_dist,
        'norm_h': float(np.linalg.norm(h))
    }

print("=== 1. Normal Test Samples (40 samples) ===")
for c in CLASSES:
    fpaths = glob.glob(f'data/test/{c}/*.*')
    stats = [eval_geo(*extract(Image.open(f))[1:3]) for f in fpaths]
    print(f"  {c:10s}: RawDist max={max(s['raw_dist'] for s in stats):5.2f} | CosDist max={max(s['cos_dist'] for s in stats):.4f} | TanTheta max={max(s['tan_theta'] for s in stats):.4f} | Margin min={min(s['margin'] for s in stats):4.2f}")

print("\n=== 2. Exposure & Specular Perturbations (160 samples across 4 classes) ===")
for c in CLASSES:
    fpaths = glob.glob(f'data/test/{c}/*.*')
    stats = []
    for f in fpaths:
        base = Image.open(f)
        for factor in [0.70, 0.72, 0.75, 0.80, 0.85, 0.90, 1.20]:
            mod = ImageEnhance.Brightness(base).enhance(factor)
            if factor <= 0.75:
                draw = ImageDraw.Draw(mod)
                draw.ellipse([80, 80, 88, 85], fill=(220, 230, 240))
            stats.append(eval_geo(*extract(mod)[1:3]))
    print(f"  {c:10s}: RawDist max={max(s['raw_dist'] for s in stats):5.2f} | CosDist max={max(s['cos_dist'] for s in stats):.4f} | TanTheta max={max(s['tan_theta'] for s in stats):.4f} | Margin min={min(s['margin'] for s in stats):4.2f}")

print("\n=== 3. Out-of-Distribution Samples ===")
for ood in ['quartz', 'granite', 'limestone', 'sandstone', 'basalt']:
    fpaths = glob.glob(f'data/evaluation/ood/{ood}/*.*')
    stats = [eval_geo(*extract(Image.open(f))[1:3]) for f in fpaths]
    print(f"  {ood:10s}: RawDist min={min(s['raw_dist'] for s in stats):5.2f} | CosDist min={min(s['cos_dist'] for s in stats):.4f} | TanTheta min={min(s['tan_theta'] for s in stats):.4f} | Margin max={max(s['margin'] for s in stats):4.2f}")

white_stat = eval_geo(*extract(Image.fromarray(np.ones((224,224,3), dtype=np.uint8)*245))[1:3])
print(f"  {'white':10s}: RawDist min={white_stat['raw_dist']:5.2f} | CosDist min={white_stat['cos_dist']:.4f} | TanTheta min={white_stat['tan_theta']:.4f}")
noise_stat = eval_geo(*extract(Image.fromarray(np.clip(np.random.normal(128,40,(224,224,3)),0,255).astype(np.uint8)))[1:3])
print(f"  {'noise':10s}: RawDist min={noise_stat['raw_dist']:5.2f} | CosDist min={noise_stat['cos_dist']:.4f} | TanTheta min={noise_stat['tan_theta']:.4f}")
