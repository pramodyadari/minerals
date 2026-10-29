import os
import glob
import numpy as np
from PIL import Image
import sys
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)
sys.path.insert(0, os.path.join(BASE_DIR, "scratch"))
from test_segmenter import segment_rock_specimen

test_dir = "data/test"
classes = ["coal", "manganese", "iron_ore", "bauxite"]

print("=== TESTING ON DATA/TEST (Texture Crops) ===")
for cls in classes:
    files = glob.glob(os.path.join(test_dir, cls, "*.*"))[:3]
    for f in files:
        im = Image.open(f).convert("RGB")
        _, diag = segment_rock_specimen(im)
        print(f"[{cls}] {os.path.basename(f)}: is_segmented={diag['is_segmented']}, quality={diag['segmentation_quality']}, notes={diag['notes']}")

print("\n=== TESTING ON DATA/EVALUATION (OOD Rocks) ===")
ood_rocks = ["quartz", "granite", "limestone", "sandstone", "basalt"]
for rk in ood_rocks:
    files = glob.glob(os.path.join("data/evaluation", rk, "*.*"))[:2]
    for f in files:
        im = Image.open(f).convert("RGB")
        _, diag = segment_rock_specimen(im)
        print(f"[{rk}] {os.path.basename(f)}: is_segmented={diag['is_segmented']}, quality={diag['segmentation_quality']}")
