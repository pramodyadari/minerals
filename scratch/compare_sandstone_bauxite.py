import glob
import numpy as np
import torch
from PIL import Image, ImageEnhance
import sys
sys.path.insert(0, 'ai')
from train import MineralConvNet, CLASSES
from evaluate_ood_detection import FeatureExtractor, load_and_preprocess

m = MineralConvNet(4)
m.load_state_dict(torch.load('models/mineral_image_classifier.pth', map_location='cpu'))
m.eval()
ext = FeatureExtractor(m)

sandstone_files = glob.glob("data/evaluation/ood/sandstone/*.*")
bauxite_files = glob.glob("data/test/bauxite/*.*")

print("Sandstone metrics:")
for f in sandstone_files[:3]:
    im = Image.open(f)
    t = load_and_preprocess(im)
    with torch.no_grad():
        f256, h, logits = ext(t)
    arr = np.array(im.convert('RGB'), dtype=np.float32)
    rb_ratio = arr[:,:,0].mean() / (arr[:,:,2].mean() + 1e-5)
    rg_ratio = arr[:,:,0].mean() / (arr[:,:,1].mean() + 1e-5)
    print(f"  Sandstone {f}: logits={logits.squeeze().numpy().round(2)} ||f||={np.linalg.norm(f256.numpy()):.2f} R/B={rb_ratio:.2f} R/G={rg_ratio:.2f}")

print("\nBauxite bright (1.20x) metrics:")
for f in bauxite_files[:3]:
    im = Image.open(f)
    mod = ImageEnhance.Brightness(im).enhance(1.20)
    t = load_and_preprocess(mod)
    with torch.no_grad():
        f256, h, logits = ext(t)
    arr = np.array(mod.convert('RGB'), dtype=np.float32)
    rb_ratio = arr[:,:,0].mean() / (arr[:,:,2].mean() + 1e-5)
    rg_ratio = arr[:,:,0].mean() / (arr[:,:,1].mean() + 1e-5)
    print(f"  Bauxite 1.2x {f}: logits={logits.squeeze().numpy().round(2)} ||f||={np.linalg.norm(f256.numpy()):.2f} R/B={rb_ratio:.2f} R/G={rg_ratio:.2f}")

print("\nBauxite normal (1.00x) metrics:")
for f in bauxite_files[:3]:
    im = Image.open(f)
    t = load_and_preprocess(im)
    with torch.no_grad():
        f256, h, logits = ext(t)
    arr = np.array(im.convert('RGB'), dtype=np.float32)
    rb_ratio = arr[:,:,0].mean() / (arr[:,:,2].mean() + 1e-5)
    rg_ratio = arr[:,:,0].mean() / (arr[:,:,1].mean() + 1e-5)
    print(f"  Bauxite 1.0x {f}: logits={logits.squeeze().numpy().round(2)} ||f||={np.linalg.norm(f256.numpy()):.2f} R/B={rb_ratio:.2f} R/G={rg_ratio:.2f}")
