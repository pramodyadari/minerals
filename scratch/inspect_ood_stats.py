import os
import glob
from PIL import Image
import numpy as np

BASE_DIR = r"C:\Users\yadar\Downloads\ai_mineral_explo"
ood_dir = os.path.join(BASE_DIR, "data", "evaluation", "ood")

for lith in os.listdir(ood_dir):
    lith_p = os.path.join(ood_dir, lith)
    if os.path.isdir(lith_p):
        files = glob.glob(os.path.join(lith_p, "*.*"))
        print(f"Lithology: {lith} ({len(files)} files)")
        if files:
            sample = files[0]
            with Image.open(sample) as im:
                arr = np.array(im)
                print(f"  Sample: {os.path.basename(sample)}, size={im.size}, mode={im.mode}, mean={arr.mean(axis=(0,1))}, std={arr.std(axis=(0,1))}")

