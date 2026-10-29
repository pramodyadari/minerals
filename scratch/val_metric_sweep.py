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

# Compute class centroids and directional reference vectors on training split
train_h = {c: [] for c in CLASSES}
for c in CLASSES:
    for f in glob.glob(f'data/train/{c}/*.*'):
        _, h, _, _ = extract(Image.open(f))
        train_h[c].append(h)

centroids = {c: np.mean(train_h[c], axis=0) for c in CLASSES}
ref_dirs = {c: centroids[c] / (np.linalg.norm(centroids[c]) + 1e-8) for c in CLASSES}
ref_norms = {c: float(np.linalg.norm(centroids[c])) for c in CLASSES}

# Let's test multiple distance metric definitions:
# Metric 1: Scaled-Radial Distance (Perpendicular distance + radial penalty)
# d_perp = || h - (h . ref_dir) ref_dir ||
# Metric 2: Angular Distance (100 * (1 - cos(h, ref_dir)))
# Metric 3: Normalized Hypersphere Distance (10 * || h/||h|| - ref_dir ||)
# Metric 4: Energy-weighted manifold distance

def compute_distances(h, logits):
    norm_h = h / (np.linalg.norm(h) + 1e-8)
    h_len = np.linalg.norm(h)
    
    # Evaluate for all 4 classes
    dists = {}
    for c in CLASSES:
        dir_c = ref_dirs[c]
        cos_sim = float(np.dot(norm_h, dir_c))
        h_proj = np.dot(h, dir_c) * dir_c
        h_perp = float(np.linalg.norm(h - h_proj))
        
        # Hypersphere distance: sqrt(2 * (1 - cos_sim)) scaled by 10 for convenient scale
        hypersphere_d = float(np.sqrt(max(0.0, 2.0 * (1.0 - cos_sim))) * 10.0)
        
        # Perpendicular distance:
        perp_d = h_perp
        
        # Combined manifold distance: perp_d + radial deviation relative to typical range
        # If h_len is in reasonable range [0.3 * ref_norm, 1.8 * ref_norm], radial penalty is 0, else penalty
        radial_ratio = h_len / ref_norms[c]
        if radial_ratio < 0.4:
            rad_pen = (0.4 - radial_ratio) * 10.0
        elif radial_ratio > 1.8:
            rad_pen = (radial_ratio - 1.8) * 10.0
        else:
            rad_pen = 0.0
        combined_d = perp_d + rad_pen
        
        dists[c] = {
            'hypersphere_d': hypersphere_d,
            'perp_d': perp_d,
            'combined_d': combined_d,
            'cos_sim': cos_sim,
            'radial_ratio': radial_ratio
        }
    return dists

# Let's collect Validation Set:
# 1. Known Val Standard: 40 samples
# 2. Known Val Perturbed: 40 samples (dark shiny, bright, specular)
# 3. Unknown Val: 30 samples (Quartz, Granite, Limestone, White, Noise)

val_known = []
for c in CLASSES:
    for f in glob.glob(f'data/validation/{c}/*.*'):
        im = Image.open(f)
        _, h, l, probs = extract(im)
        d = compute_distances(h, l)
        val_known.append({'true_cls': c, 'h': h, 'logits': l, 'probs': probs, 'dists': d, 'is_ood': False, 'type': 'standard'})
        
        # Perturbed dark shiny:
        im_dark = ImageEnhance.Brightness(im).enhance(0.72)
        draw = ImageDraw.Draw(im_dark)
        draw.ellipse([80, 80, 88, 85], fill=(220, 230, 240))
        _, h_d, l_d, probs_d = extract(im_dark)
        d_d = compute_distances(h_d, l_d)
        val_known.append({'true_cls': c, 'h': h_d, 'logits': l_d, 'probs': probs_d, 'dists': d_d, 'is_ood': False, 'type': 'dark_shiny'})

val_unknown = []
for ood in ['quartz', 'granite', 'limestone']:
    for f in glob.glob(f'data/evaluation/ood/{ood}/*.*')[:6]:
        im = Image.open(f)
        _, h, l, probs = extract(im)
        d = compute_distances(h, l)
        val_unknown.append({'true_cls': ood, 'h': h, 'logits': l, 'probs': probs, 'dists': d, 'is_ood': True})

for name, raw in [('white', np.ones((224,224,3), dtype=np.uint8)*245), ('noise', np.clip(np.random.normal(128,40,(224,224,3)),0,255).astype(np.uint8))]:
    _, h, l, probs = extract(Image.fromarray(raw))
    d = compute_distances(h, l)
    val_unknown.append({'true_cls': name, 'h': h, 'logits': l, 'probs': probs, 'dists': d, 'is_ood': True})

print(f"Validation known samples: {len(val_known)} (40 standard + 40 dark/shiny)")
print(f"Validation unknown samples: {len(val_unknown)} (Quartz, Granite, Limestone, White, Noise)")

# Compare distributions for each metric
print("\n--- METRIC: Combined Manifold Distance (Perpendicular + Radial Bounds) ---")
for s in val_known[:6]:
    c = s['true_cls']
    print(f"Known {c:10s} ({s['type']:10s}): dist={s['dists'][c]['combined_d']:.2f}, perp={s['dists'][c]['perp_d']:.2f}, ratio={s['dists'][c]['radial_ratio']:.2f}")

print("\n--- OOD Samples ---")
for s in val_unknown:
    min_comb = min(s['dists'][c]['combined_d'] for c in CLASSES)
    min_perp = min(s['dists'][c]['perp_d'] for c in CLASSES)
    c_best = min(CLASSES, key=lambda c: s['dists'][c]['combined_d'])
    print(f"OOD {s['true_cls']:12s}: min_comb_dist={min_comb:5.2f} (closest={c_best}), min_perp={min_perp:5.2f}, ratio={s['dists'][c_best]['radial_ratio']:.2f}")
