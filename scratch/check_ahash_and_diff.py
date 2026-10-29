import os
from PIL import Image
import numpy as np

BASE_DIR = r"C:\Users\yadar\Downloads\ai_mineral_explo"
train_img_path = os.path.join(BASE_DIR, "data", "train", "iron_ore", "iron_ore_train_004.jpg")
test_img_path = os.path.join(BASE_DIR, "data", "test", "iron_ore", "iron_ore_test_004.jpg")

def ahash(img, size=8):
    resized = img.convert("L").resize((size, size), Image.Resampling.BILINEAR)
    arr = np.array(resized, dtype=np.float32)
    avg = arr.mean()
    return "".join(["1" if x > avg else "0" for x in arr.flatten()])

def phash(img, size=32, smaller_size=8):
    resized = img.convert("L").resize((size, size), Image.Resampling.BILINEAR)
    arr = np.array(resized, dtype=np.float32)
    # DCT approximation or simple frequency
    return ahash(img, size=smaller_size)

with Image.open(train_img_path) as im1, Image.open(test_img_path) as im2:
    ah1 = ahash(im1)
    ah2 = ahash(im2)
    h_dist_ahash = sum(c1 != c2 for c1, c2 in zip(ah1, ah2))
    print(f"aHash Train: {ah1}")
    print(f"aHash Test:  {ah2}")
    print(f"aHash Hamming Distance: {h_dist_ahash}")

    # Check pixel difference min, max, std
    arr1 = np.array(im1, dtype=np.float32)
    arr2 = np.array(im2, dtype=np.float32)
    diff = np.abs(arr1 - arr2)
    print(f"Pixel Diff Max: {diff.max()}")
    print(f"Pixel Diff Min: {diff.min()}")
    print(f"Pixel Diff Std: {diff.std()}")
    print(f"Pixel Diff Percentage > 10 intensity: {(diff > 10).mean() * 100:.2f}%")
    print(f"Pixel Diff Percentage > 25 intensity: {(diff > 25).mean() * 100:.2f}%")

