import glob
import io
import json
import numpy as np
import torch
from PIL import Image, ImageEnhance, ImageDraw
import sys
sys.path.insert(0, '.')
from backend.app.vision_service import classify_specimen_image, compute_scale_robust_distance, get_ood_config

cfg = get_ood_config()
c_mng = np.array(cfg['centroids']['manganese'])
bounds_mng = cfg['scale_bounds']['manganese']

print("Scale bounds for manganese:", bounds_mng)

f = glob.glob('data/test/manganese/*.*')[0]
base = Image.open(f)
print("Base image size:", base.size, base.mode)

for factor in [0.50, 0.55, 0.60, 0.65, 0.68, 0.70, 0.72, 0.75]:
    im = ImageEnhance.Brightness(base).enhance(factor)
    draw = ImageDraw.Draw(im)
    draw.ellipse([80, 80, 88, 85], fill=(220, 230, 240))
    buf = io.BytesIO()
    im.save(buf, format='JPEG')
    res = classify_specimen_image(buf.getvalue())
    dist = res.get('feature_distance')
    supp = res.get('is_supported_mineral')
    cand = res.get('closest_candidate_mineral')
    probs = res.get('raw_model_prediction', {}).get('raw_probabilities_pct')
    print(f"Factor {factor:.2f}: dist={dist}, supp={supp}, cand={cand}, probs={probs}")
