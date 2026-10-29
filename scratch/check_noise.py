import numpy as np
import torch
import sys
sys.path.insert(0, 'ai')
from train import MineralConvNet, CLASSES
from evaluate_ood_detection import FeatureExtractor, load_and_preprocess
from PIL import Image

m = MineralConvNet(4)
m.load_state_dict(torch.load('models/mineral_image_classifier.pth', map_location='cpu'))
m.eval()
ext = FeatureExtractor(m)

noise_arr = np.clip(np.random.normal(128, 40, (224, 224, 3)), 0, 255).astype(np.uint8)
t = load_and_preprocess(Image.fromarray(noise_arr))
with torch.no_grad():
    f256, h, logits = ext(t)
probs = torch.softmax(logits, dim=-1).squeeze().numpy()
print(f"Noise probs: {probs}")
print(f"Noise h norm: {np.linalg.norm(h.numpy()):.2f}")
print(f"Noise f256 norm: {np.linalg.norm(f256.numpy()):.2f}")
