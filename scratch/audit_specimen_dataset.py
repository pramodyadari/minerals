import os
import glob
import hashlib
from PIL import Image
import numpy as np

splits = ["train", "validation", "test"]
classes = ["coal", "manganese", "iron_ore", "bauxite"]

print("=== SPECIMEN DATASET AUDIT ===")
all_hashes = {}
duplicate_count = 0
cross_split_leakage = []

for split in splits:
    for cls in classes:
        files = glob.glob(f"data/{split}/{cls}/*.*")
        print(f"{split}/{cls}: {len(files)} files")
        for f in files:
            with open(f, "rb") as fp:
                data = fp.read()
            h = hashlib.md5(data).hexdigest()
            # Also calculate normalized image array hash to detect re-encodings of identical pixels
            try:
                im = Image.open(f).convert("RGB")
                im_bytes = im.tobytes()
                im_h = hashlib.md5(im_bytes).hexdigest()
            except Exception as e:
                im_h = None
            
            if h in all_hashes:
                prev = all_hashes[h]
                if prev["split"] != split:
                    cross_split_leakage.append((f, prev["file"], "exact_file_md5"))
            elif im_h in all_hashes:
                prev = all_hashes[im_h]
                if prev["split"] != split:
                    cross_split_leakage.append((f, prev["file"], "identical_pixels"))
            all_hashes[h] = {"split": split, "class": cls, "file": f}
            if im_h:
                all_hashes[im_h] = {"split": split, "class": cls, "file": f}

print(f"\nTotal unique file hashes tracked: {len(all_hashes)}")
print(f"Cross-split leakage instances detected: {len(cross_split_leakage)}")
for c in cross_split_leakage:
    print(f"  Leakage: {c[0]} <-> {c[1]} ({c[2]})")

print("\n=== OOD DATASET AUDIT ===")
ood_classes = ["quartz", "granite", "limestone", "sandstone", "basalt"]
for ood in ood_classes:
    files = glob.glob(f"data/evaluation/ood/{ood}/*.*")
    print(f"data/evaluation/ood/{ood}: {len(files)} files")

# Check image properties (dimensions, means, stds, synthetic indicators)
print("\n=== SPECIMEN IMAGE CHARACTERISTICS ===")
for cls in classes:
    files = glob.glob(f"data/train/{cls}/*.*")
    if files:
        f = files[0]
        im = Image.open(f)
        arr = np.array(im)
        print(f"Sample train/{cls}: {f}, size: {im.size}, format: {im.format}, min: {arr.min()}, max: {arr.max()}, mean: {arr.mean():.1f}")
