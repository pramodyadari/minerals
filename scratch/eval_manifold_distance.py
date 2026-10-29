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

# Compute reference vectors on train split
train_h = {c: [] for c in CLASSES}
for c in CLASSES:
    for f in glob.glob(f'data/train/{c}/*.*'):
        _, h, _, _ = extract(Image.open(f))
        train_h[c].append(h)

centroids = {c: np.mean(train_h[c], axis=0) for c in CLASSES}

def compute_manifold_distance(h, c_target):
    c_vec = centroids[c_target]
    norm_c_sq = float(np.dot(c_vec, c_vec) + 1e-8)
    alpha = float(np.dot(h, c_vec) / norm_c_sq)
    h_proj = max(0.0, alpha) * c_vec
    d_perp = float(np.linalg.norm(h - h_proj))
    
    # Scale bounds penalty
    rad_pen = 0.0
    if alpha < 0.35:
        rad_pen = (0.35 - alpha) * 10.0
    elif alpha > 1.80:
        rad_pen = (alpha - 1.80) * 10.0
        
    return d_perp + rad_pen, alpha, d_perp

# Let's test all test known samples (standard + perturbed)
print('--- Evaluating All Test Known Samples (Standard + Dark/Shiny + Bright) ---')
known_dists = []
for c in CLASSES:
    for f in glob.glob(f'data/test/{c}/*.*'):
        base = Image.open(f)
        for factor in [0.70, 0.72, 0.85, 1.00, 1.20]:
            mod = ImageEnhance.Brightness(base).enhance(factor)
            if factor <= 0.75:
                draw = ImageDraw.Draw(mod)
                draw.ellipse([80, 80, 88, 85], fill=(220, 230, 240))
            _, h, l, probs = extract(mod)
            pred_c = CLASSES[np.argmax(probs)]
            d_man, alpha, d_perp = compute_manifold_distance(h, pred_c)
            known_dists.append({'class': c, 'pred': pred_c, 'conf': float(probs.max()), 'd_man': d_man, 'factor': factor})

max_k = max(s['d_man'] for s in known_dists)
print(f"Total known test evaluations: {len(known_dists)}")
print(f"Max manifold distance for known minerals: {max_k:.2f}")

dark_shiny_mng = next(s for s in known_dists if s['class'] == 'manganese' and s['factor'] == 0.72)
print(f"Manganese dark shiny (factor=0.72): dist={dark_shiny_mng['d_man']:.2f}, conf={dark_shiny_mng['conf'] * 100:.2f}%")

print('\n--- Evaluating Out-of-Distribution Samples ---')
ood_dists = []
for ood in ['quartz', 'granite', 'limestone']:
    for f in glob.glob(f'data/evaluation/ood/{ood}/*.*'):
        _, h, l, probs = extract(Image.open(f))
        pred_c = CLASSES[np.argmax(probs)]
        d_man, alpha, d_perp = compute_manifold_distance(h, pred_c)
        ood_dists.append({'rock': ood, 'pred': pred_c, 'd_man': d_man})

for name, raw in [('white', np.ones((224,224,3), dtype=np.uint8)*245)]:
    _, h, l, probs = extract(Image.fromarray(raw))
    pred_c = CLASSES[np.argmax(probs)]
    d_man, alpha, d_perp = compute_manifold_distance(h, pred_c)
    ood_dists.append({'rock': name, 'pred': pred_c, 'd_man': d_man})

for rock in ['quartz', 'granite', 'limestone', 'white']:
    sub = [s for s in ood_dists if s['rock'] == rock]
    min_d = min(s['d_man'] for s in sub)
    mean_d = np.mean([s['d_man'] for s in sub])
    print(f"  {rock:10s}: min manifold distance = {min_d:.2f}, mean = {mean_d:.2f}")
