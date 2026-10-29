import glob
import torch
import numpy as np
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
c_mng = np.array(cfg['centroids']['manganese'])

# Original dark shiny manganese
f = glob.glob('data/test/manganese/*.*')[0]
base = Image.open(f)
dark_shiny = ImageEnhance.Brightness(base).enhance(0.72)
draw = ImageDraw.Draw(dark_shiny)
draw.ellipse([80, 80, 88, 85], fill=(220, 230, 240))

t = load_and_preprocess(dark_shiny)
with torch.no_grad():
    f256, h, logits = ext(t)
h_vec = h.squeeze().numpy()
logits_vec = logits.squeeze().numpy()

alpha = np.dot(h_vec, c_mng) / np.dot(c_mng, c_mng)
h_proj = alpha * c_mng
d_perp = np.linalg.norm(h_vec - h_proj)
raw_euc = np.linalg.norm(h_vec - c_mng)

print(f"Dark shiny Manganese: alpha = {alpha:.4f}, d_perp = {d_perp:.4f}, raw_euc = {raw_euc:.4f}")
print(f"Norm(h) = {np.linalg.norm(h_vec):.2f}, Norm(c_mng) = {np.linalg.norm(c_mng):.2f}")
print(f"Logits = {logits_vec}, Softmax = {torch.softmax(logits, dim=-1).squeeze().numpy()}")
