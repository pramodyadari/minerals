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

# Let's inspect logits and feature properties for various samples
def analyze(name, im):
    f256, h, logits, probs = extract(im)
    norm_h = np.linalg.norm(h)
    norm_f = np.linalg.norm(f256)
    s_logits = np.sort(logits)
    margin = s_logits[-1] - s_logits[-2]
    top_c = CLASSES[np.argmax(logits)]
    print(f"{name:20s} | Top: {top_c:10s} ({probs.max()*100:6.2f}%) | Margin: {margin:5.2f} | Logits: {logits.round(2)} | ||h||={norm_h:5.2f} | ||f||={norm_f:5.2f}")

print("=== Genuine Minerals ===")
for c in CLASSES:
    f = glob.glob(f'data/test/{c}/*.*')[0]
    analyze(f"Normal {c}", Image.open(f))

print("\n=== Genuine Manganese with Darkness & Specular Glint ===")
base = Image.open(glob.glob('data/test/manganese/*.*')[0])
for factor in [0.70, 0.72, 0.75, 0.80, 0.90]:
    mod = ImageEnhance.Brightness(base).enhance(factor)
    draw = ImageDraw.Draw(mod)
    draw.ellipse([80, 80, 88, 85], fill=(220, 230, 240))
    analyze(f"Mng dark {factor:.2f}x", mod)

print("\n=== Out-of-Distribution Samples ===")
for ood in ['quartz', 'granite', 'limestone', 'sandstone', 'basalt']:
    f = glob.glob(f'data/evaluation/ood/{ood}/*.*')[0]
    analyze(f"OOD {ood}", Image.open(f))

analyze("Uniform White", Image.fromarray(np.ones((224,224,3), dtype=np.uint8)*245))
analyze("Uniform Gray", Image.fromarray(np.ones((224,224,3), dtype=np.uint8)*128))
analyze("Noise", Image.fromarray(np.clip(np.random.normal(128,40,(224,224,3)),0,255).astype(np.uint8)))
