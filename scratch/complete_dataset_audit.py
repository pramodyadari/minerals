import os
import glob
import hashlib
import json
from collections import defaultdict
from PIL import Image
import numpy as np

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SPLITS = ["train", "validation", "test"]
CLASSES = ["coal", "manganese", "iron_ore", "bauxite"]
OOD_CLASSES = ["quartz", "granite", "limestone", "sandstone", "basalt"]

audit_data = {
    "splits": {},
    "ood": {},
    "file_hashes": {},
    "cross_split_leakage": [],
    "corrupt_files": [],
    "class_counts": defaultdict(lambda: defaultdict(int)),
    "image_dimensions": defaultdict(set),
    "image_formats": defaultdict(set),
    "color_statistics": {},
}

all_file_hashes = {}
pixel_hashes = {}

print("=" * 80)
print("PHASE 1: COMPREHENSIVE DATASET AUDIT")
print("=" * 80)

for split in SPLITS:
    audit_data["splits"][split] = {}
    for cls in CLASSES:
        folder = os.path.join(BASE_DIR, "data", split, cls)
        files = sorted(glob.glob(os.path.join(folder, "*.*")))
        audit_data["splits"][split][cls] = len(files)
        audit_data["class_counts"][split][cls] = len(files)
        
        means, stds = [], []
        for f in files:
            try:
                with open(f, "rb") as fp:
                    raw = fp.read()
                file_md5 = hashlib.md5(raw).hexdigest()
                
                with Image.open(f) as im:
                    fmt = im.format
                    sz = im.size
                    mode = im.mode
                    im_rgb = im.convert("RGB")
                    arr = np.array(im_rgb, dtype=np.float32)
                    pixel_md5 = hashlib.md5(im_rgb.tobytes()).hexdigest()
                    
                audit_data["image_dimensions"][f"{split}/{cls}"].add(sz)
                audit_data["image_formats"][f"{split}/{cls}"].add(fmt)
                means.append(arr.mean(axis=(0, 1)))
                stds.append(arr.std(axis=(0, 1)))
                
                # Check file hash duplicate
                if file_md5 in all_file_hashes:
                    prev = all_file_hashes[file_md5]
                    if prev["split"] != split:
                        audit_data["cross_split_leakage"].append({
                            "type": "exact_file_duplicate",
                            "file_1": f,
                            "split_1": split,
                            "file_2": prev["file"],
                            "split_2": prev["split"],
                        })
                else:
                    all_file_hashes[file_md5] = {"split": split, "class": cls, "file": f}
                    
                # Check pixel duplicate
                if pixel_md5 in pixel_hashes:
                    prev = pixel_hashes[pixel_md5]
                    if prev["split"] != split:
                        audit_data["cross_split_leakage"].append({
                            "type": "identical_pixels",
                            "file_1": f,
                            "split_1": split,
                            "file_2": prev["file"],
                            "split_2": prev["split"],
                        })
                else:
                    pixel_hashes[pixel_md5] = {"split": split, "class": cls, "file": f}
                    
            except Exception as e:
                audit_data["corrupt_files"].append({"file": f, "error": str(e)})

        if means:
            means = np.array(means)
            stds = np.array(stds)
            audit_data["color_statistics"][f"{split}/{cls}"] = {
                "mean_rgb": [round(float(x), 2) for x in means.mean(axis=0)],
                "std_rgb": [round(float(x), 2) for x in stds.mean(axis=0)],
            }

# Audit OOD dataset
ood_folder = os.path.join(BASE_DIR, "data", "evaluation", "ood")
for ood in OOD_CLASSES:
    files = glob.glob(os.path.join(ood_folder, ood, "*.*"))
    audit_data["ood"][ood] = len(files)
    means, stds = [], []
    for f in files:
        try:
            with Image.open(f) as im:
                im_rgb = im.convert("RGB")
                arr = np.array(im_rgb, dtype=np.float32)
                means.append(arr.mean(axis=(0, 1)))
                stds.append(arr.std(axis=(0, 1)))
        except Exception as e:
            audit_data["corrupt_files"].append({"file": f, "error": str(e)})
    if means:
        means = np.array(means)
        stds = np.array(stds)
        audit_data["color_statistics"][f"ood/{ood}"] = {
            "mean_rgb": [round(float(x), 2) for x in means.mean(axis=0)],
            "std_rgb": [round(float(x), 2) for x in stds.mean(axis=0)],
        }

print("\n1. SAMPLE COUNTS BY SPLIT & CLASS:")
print(f"{'Class':12s} | {'Train':8s} | {'Validation':10s} | {'Test':8s} | {'Total':8s}")
print("-" * 55)
for cls in CLASSES:
    tr = audit_data["splits"]["train"][cls]
    val = audit_data["splits"]["validation"][cls]
    te = audit_data["splits"]["test"][cls]
    tot = tr + val + te
    print(f"{cls:12s} | {tr:8d} | {val:10d} | {te:8d} | {tot:8d}")
total_tr = sum(audit_data["splits"]["train"].values())
total_val = sum(audit_data["splits"]["validation"].values())
total_te = sum(audit_data["splits"]["test"].values())
print("-" * 55)
print(f"{'TOTAL':12s} | {total_tr:8d} | {total_val:10d} | {total_te:8d} | {total_tr+total_val+total_te:8d}")

print("\n2. OOD EVALUATION SAMPLES:")
for ood, count in audit_data["ood"].items():
    print(f"  {ood:12s}: {count:3d} specimens")

print("\n3. DATA INTEGRITY & LEAKAGE CHECK:")
print(f"  Corrupt/unreadable files: {len(audit_data['corrupt_files'])}")
print(f"  Cross-split leakage instances: {len(audit_data['cross_split_leakage'])}")
if audit_data["cross_split_leakage"]:
    for lk in audit_data["cross_split_leakage"]:
        print(f"    LEAKAGE: {lk['file_1']} ({lk['split_1']}) matches {lk['file_2']} ({lk['split_2']})")
else:
    print("  Zero leakage detected across train, validation, and test splits.")

print("\n4. IMAGE FORMATS & DIMENSIONS:")
for k, dims in audit_data["image_dimensions"].items():
    fmts = audit_data["image_formats"][k]
    dim_str = ", ".join(f"{w}x{h}" for w, h in dims)
    fmt_str = ", ".join(fmts)
    print(f"  {k:20s}: Dimensions [{dim_str}], Format [{fmt_str}]")

print("\n5. COLOR & TEXTURE STATISTICAL PROFILES:")
for k, stats in audit_data["color_statistics"].items():
    print(f"  {k:20s}: Mean RGB={stats['mean_rgb']}, Std RGB={stats['std_rgb']}")

out_audit_path = os.path.join(BASE_DIR, "data", "audits", "specimen_dataset_audit.json")
os.makedirs(os.path.dirname(out_audit_path), exist_ok=True)

# Convert sets to lists for json serialization
json_serializable = dict(audit_data)
json_serializable["image_dimensions"] = {k: [list(dim) for dim in v] for k, v in audit_data["image_dimensions"].items()}
json_serializable["image_formats"] = {k: list(v) for k, v in audit_data["image_formats"].items()}

with open(out_audit_path, "w", encoding="utf-8") as fp:
    json.dump(json_serializable, fp, indent=2)
print(f"\nAudit saved to {out_audit_path}")

