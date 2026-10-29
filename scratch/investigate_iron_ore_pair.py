import os
import hashlib
from PIL import Image
import numpy as np

BASE_DIR = r"C:\Users\yadar\Downloads\ai_mineral_explo"
train_img_path = os.path.join(BASE_DIR, "data", "train", "iron_ore", "iron_ore_train_004.jpg")
test_img_path = os.path.join(BASE_DIR, "data", "test", "iron_ore", "iron_ore_test_004.jpg")

def compute_sha256(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()

def compute_dhash(image, hash_size=8):
    resized = image.convert("L").resize((hash_size + 1, hash_size), Image.Resampling.BILINEAR)
    pixels = np.array(resized, dtype=np.float32)
    diff = pixels[:, 1:] > pixels[:, :-1]
    return "".join(["1" if b else "0" for b in diff.flatten()])

def hamming_distance(h1, h2):
    return sum(c1 != c2 for c1, c2 in zip(h1, h2))

print("=== INVESTIGATING IRON ORE PAIR ===")
print("Train path:", train_img_path, "Exists:", os.path.exists(train_img_path))
print("Test path:", test_img_path, "Exists:", os.path.exists(test_img_path))

sha_train = compute_sha256(train_img_path)
sha_test = compute_sha256(test_img_path)
print("SHA256 Train:", sha_train)
print("SHA256 Test: ", sha_test)
print("Exact Match:", sha_train == sha_test)

with Image.open(train_img_path) as im_train, Image.open(test_img_path) as im_test:
    print(f"Train: size={im_train.size}, format={im_train.format}, mode={im_train.mode}")
    print(f"Test:  size={im_test.size}, format={im_test.format}, mode={im_test.mode}")
    
    dhash_tr = compute_dhash(im_train)
    dhash_te = compute_dhash(im_test)
    h_dist = hamming_distance(dhash_tr, dhash_te)
    print("dHash Train:", dhash_tr)
    print("dHash Test: ", dhash_te)
    print("dHash Hamming distance:", h_dist)
    
    arr_tr = np.array(im_train.convert("RGB"), dtype=np.float32)
    arr_te = np.array(im_test.convert("RGB"), dtype=np.float32)
    
    print("Train Mean RGB:", [round(x, 2) for x in arr_tr.mean(axis=(0,1))])
    print("Test Mean RGB: ", [round(x, 2) for x in arr_te.mean(axis=(0,1))])
    print("Train Std RGB: ", [round(x, 2) for x in arr_tr.std(axis=(0,1))])
    print("Test Std RGB:  ", [round(x, 2) for x in arr_te.std(axis=(0,1))])
    
    diff = np.abs(arr_tr - arr_te)
    mae = float(np.mean(diff))
    mse = float(np.mean((arr_tr - arr_te)**2))
    rmse = float(np.sqrt(mse))
    corr = float(np.corrcoef(arr_tr.flatten(), arr_te.flatten())[0, 1])
    print(f"Pixel Diff: MAE={mae:.2f}, RMSE={rmse:.2f}, Corr={corr:.4f}")

# Also compare all train iron_ore vs test_004 to see if 004 is an outlier or if the naming index reflects seeds
print("\n=== COMPARING ALL TEST IRON ORE VS TRAIN IRON ORE WITH SAME INDEX ===")
for i in range(10):
    tr_p = os.path.join(BASE_DIR, "data", "train", "iron_ore", f"iron_ore_train_{i:03d}.jpg")
    te_p = os.path.join(BASE_DIR, "data", "test", "iron_ore", f"iron_ore_test_{i:03d}.jpg")
    if os.path.exists(tr_p) and os.path.exists(te_p):
        with Image.open(tr_p) as im1, Image.open(te_p) as im2:
            dh1 = compute_dhash(im1)
            dh2 = compute_dhash(im2)
            dist = hamming_distance(dh1, dh2)
            arr1 = np.array(im1.convert("RGB"), dtype=np.float32)
            arr2 = np.array(im2.convert("RGB"), dtype=np.float32)
            c = float(np.corrcoef(arr1.flatten(), arr2.flatten())[0, 1])
            print(f"Index {i:03d}: dHash Dist={dist}, Pixel Corr={c:.4f}")

