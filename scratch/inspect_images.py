import os
import glob
from PIL import Image
import numpy as np

for folder in ["data/evaluation/ood/basalt", "data/evaluation/ood/sandstone", "data/train/coal", "data/train/bauxite"]:
    files = glob.glob(f"{folder}/*.*")
    print(f"\nFolder: {folder} ({len(files)} files)")
    for f in files[:3]:
        im = Image.open(f)
        arr = np.array(im)
        print(f"  {os.path.basename(f)}: size={im.size}, mode={im.mode}, mean_rgb={arr.mean(axis=(0,1)).round(1)}, std_rgb={arr.std(axis=(0,1)).round(1)}")
