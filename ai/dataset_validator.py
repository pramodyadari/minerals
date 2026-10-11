"""
AI Mineral Intelligence — Dataset Integrity & Leakage Auditor (Section 5)
Verifies:
  1. Required directory layout exists for all 4 classes across train/val/test splits.
  2. Corrupted / unreadable image detection.
  3. Class distribution and severe imbalance detection.
  4. Cross-split hash deduplication (preventing data leakage).
"""

import os
import hashlib
from PIL import Image

CLASSES = ["coal", "manganese", "iron_ore", "bauxite"]
SPLITS = ["train", "validation", "test"]

def audit_dataset(root_dir="data"):
    report = {
        "root_dir": root_dir,
        "valid": True,
        "splits": {},
        "corrupted_images": [],
        "leakage_detected": False,
        "leakage_pairs": [],
        "errors": []
    }
    
    seen_hashes = {}  # hash -> (split, cls, filename)
    
    for split in SPLITS:
        split_path = os.path.join(root_dir, split)
        report["splits"][split] = {}
        
        if not os.path.exists(split_path):
            report["valid"] = False
            report["errors"].append(f"Missing split directory: {split_path}")
            continue
            
        for cls in CLASSES:
            cls_path = os.path.join(split_path, cls)
            if not os.path.exists(cls_path):
                report["valid"] = False
                report["errors"].append(f"Missing class directory: {cls_path}")
                report["splits"][split][cls] = 0
                continue
                
            files = [f for f in os.listdir(cls_path) if f.lower().endswith(('.jpg', '.jpeg', '.png', '.webp'))]
            valid_count = 0
            
            for fname in files:
                fpath = os.path.join(cls_path, fname)
                try:
                    with Image.open(fpath) as im:
                        im.verify()
                    # Check readability
                    with Image.open(fpath) as im:
                        im.load()
                        
                    # Hash check for data leakage
                    with open(fpath, "rb") as fp:
                        file_hash = hashlib.sha256(fp.read()).hexdigest()
                        
                    if file_hash in seen_hashes:
                        prev_split, prev_cls, prev_name = seen_hashes[file_hash]
                        if prev_split != split:
                            report["leakage_detected"] = True
                            report["leakage_pairs"].append({
                                "hash": file_hash,
                                "file1": f"{prev_split}/{prev_cls}/{prev_name}",
                                "file2": f"{split}/{cls}/{fname}"
                            })
                    else:
                        seen_hashes[file_hash] = (split, cls, fname)
                        
                    valid_count += 1
                except Exception as err:
                    report["valid"] = False
                    report["corrupted_images"].append({"file": fpath, "error": str(err)})
                    
            report["splits"][split][cls] = valid_count
            
    # Check severe class imbalance in train split
    if "train" in report["splits"]:
        counts = list(report["splits"]["train"].values())
        if counts and min(counts) > 0:
            ratio = max(counts) / min(counts)
            report["imbalance_ratio"] = round(ratio, 2)
            if ratio > 4.0:
                report["errors"].append(f"Severe class imbalance detected: max/min ratio {ratio:.2f}")
                report["valid"] = False
        else:
            report["imbalance_ratio"] = None
            if any(c == 0 for c in counts):
                report["errors"].append("One or more classes have 0 training samples.")
                report["valid"] = False
                
    return report

if __name__ == "__main__":
    rep = audit_dataset("data")
    print(f"Dataset Audit Complete: Valid = {rep['valid']}")
    print("Class Distribution per Split:")
    for s, c_dict in rep["splits"].items():
        print(f"  {s.upper()}: {c_dict}")
    if rep["corrupted_images"]:
        print(f"Corrupted Images: {len(rep['corrupted_images'])}")
    if rep["leakage_detected"]:
        print(f"DATA LEAKAGE DETECTED: {len(rep['leakage_pairs'])} pairs")
    else:
        print("Data Leakage Check: PASS (Zero overlap between train, val, test)")
