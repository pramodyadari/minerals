import glob
import numpy as np
from PIL import Image

for cls in ["coal", "manganese", "iron_ore", "bauxite"]:
    train_files = glob.glob(f"data/train/{cls}/*.*")
    val_files = glob.glob(f"data/validation/{cls}/*.*")
    test_files = glob.glob(f"data/test/{cls}/*.*")
    
    train_imgs = [np.array(Image.open(f)).astype(float) for f in train_files]
    val_imgs = [np.array(Image.open(f)).astype(float) for f in val_files]
    test_imgs = [np.array(Image.open(f)).astype(float) for f in test_files]
    
    # Check min pixel distance between any train and any val image
    min_dist_train_val = min(np.mean(np.abs(t - v)) for t in train_imgs for v in val_imgs)
    min_dist_train_test = min(np.mean(np.abs(t - te)) for t in train_imgs for te in test_imgs)
    print(f"Class {cls:10s}: min mean pixel diff train-val = {min_dist_train_val:.2f}, train-test = {min_dist_train_test:.2f}")
