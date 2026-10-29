import glob
import io
import os
import sys
sys.path.insert(0, os.path.abspath('.'))
import numpy as np
import torch
from PIL import Image, ImageEnhance, ImageDraw, ImageFilter
from backend.app.vision_service import classify_specimen_image

print("Searching for synthetic or perturbed specimens where closest candidate is Manganese and distance ~ 9.99...")

# Check basalt with metallic highlights
for f in glob.glob("data/evaluation/ood/basalt/*.*")[:5]:
    im = Image.open(f)
    for factor in [0.8, 1.0, 1.2]:
        mod = ImageEnhance.Brightness(im).enhance(factor)
        buf = io.BytesIO()
        mod.save(buf, format="JPEG")
        res = classify_specimen_image(buf.getvalue())
        d = res.get("feature_distance")
        cand = res.get("closest_candidate_mineral")
        if cand == "Manganese" and abs(d - 9.99) < 0.2:
            print(f"Basalt {f} factor {factor}: dist={d}, cand={cand}, res={res.get('verification_status')}")

# Check manganese with varied surface/lighting
for f in glob.glob("data/test/manganese/*.*"):
    base = Image.open(f)
    for b in [0.5, 0.6, 0.7, 0.8, 0.9]:
        for c_factor in [0.8, 1.0, 1.2, 1.4]:
            im = ImageEnhance.Brightness(base).enhance(b)
            im = ImageEnhance.Contrast(im).enhance(c_factor)
            buf = io.BytesIO()
            im.save(buf, format="JPEG")
            res = classify_specimen_image(buf.getvalue())
            d = res.get("feature_distance")
            cand = res.get("closest_candidate_mineral")
            if cand == "Manganese" and abs(d - 9.99) < 0.2:
                print(f"Manganese {f} b={b} c={c_factor}: dist={d}, cand={cand}, res={res.get('verification_status')}")
