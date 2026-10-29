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

# Centroids for f256
train_f256 = {c: [] for c in CLASSES}
for c in CLASSES:
    for f in glob.glob(f"data/train/{c}/*.*"):
        t = load_and_preprocess(f)
        with torch.no_grad():
            f256, _, _ = ext(t)
        train_f256[c].append(f256.squeeze().numpy())

c_f256 = {c: np.mean(train_f256[c], axis=0) for c in CLASSES}
c_f256_unit = {c: c_f256[c] / np.linalg.norm(c_f256[c]) for c in CLASSES}

def get_cos_f256(img):
    t = load_and_preprocess(img)
    with torch.no_grad():
        f256, h, logits = ext(t)
    f_vec = f256.squeeze().numpy()
    f_unit = f_vec / (np.linalg.norm(f_vec) + 1e-8)
    
    # Candidate class from logits
    pred_idx = np.argmax(logits.squeeze().numpy())
    pred_c = CLASSES[pred_idx]
    
    cos_dist = float(1.0 - np.dot(f_unit, c_f256_unit[pred_c]))
    return pred_c, cos_dist

print("=== Normal Test Samples ===")
for c in CLASSES:
    dists = [get_cos_f256(f)[1] for f in glob.glob(f"data/test/{c}/*.*")]
    print(f"  {c:10s} (N={len(dists)}): min={min(dists):.6f}, max={max(dists):.6f}, mean={np.mean(dists):.6f}")

print("\n=== Dark Shiny Manganese (Reproducing Bug) ===")
base = Image.open(glob.glob("data/test/manganese/*.*")[0])
dark_shiny = ImageEnhance.Brightness(base).enhance(0.72)
draw = ImageDraw.Draw(dark_shiny)
draw.ellipse([80, 80, 88, 85], fill=(220, 230, 240))
_, ds_cos = get_cos_f256(dark_shiny)
print(f"  Dark shiny Manganese cos dist in f256: {ds_cos:.6f}")

print("\n=== Other Exposure Perturbations on Test Set ===")
for c in CLASSES:
    dists = []
    for f in glob.glob(f"data/test/{c}/*.*"):
        im = Image.open(f)
        for factor in [0.75, 0.85, 1.20]:
            mod = ImageEnhance.Brightness(im).enhance(factor)
            dists.append(get_cos_f256(mod)[1])
    print(f"  {c:10s} perturbed: min={min(dists):.6f}, max={max(dists):.6f}")

print("\n=== OOD Rocks ===")
for ood in ["quartz", "granite", "limestone", "sandstone", "basalt"]:
    dists = [get_cos_f256(f)[1] for f in glob.glob(f"data/evaluation/ood/{ood}/*.*")]
    print(f"  {ood:10s} (N={len(dists)}): min={min(dists):.6f}, max={max(dists):.6f}, mean={np.mean(dists):.6f}")
