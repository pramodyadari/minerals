import os
import sys
import glob
import json
import hashlib
import numpy as np
from PIL import Image

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def compute_sha256(filepath):
    with open(filepath, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()

def compute_dhash(image, hash_size=8):
    """Computes difference hash for perceptual near-duplicate detection."""
    resized = image.convert("L").resize((hash_size + 1, hash_size), Image.Resampling.BILINEAR)
    pixels = np.array(resized, dtype=np.float32)
    diff = pixels[:, 1:] > pixels[:, :-1]
    return "".join(["1" if b else "0" for b in diff.flatten()])

def audit_all_images():
    print("Auditing all images across workspace...")
    records = []
    
    # Track files
    scanned_paths = set()
    
    # 1. Dataset splits
    split_dirs = [
        ("train", "data/train"),
        ("validation", "data/validation"),
        ("test", "data/test"),
        ("evaluation_known", "data/evaluation/known"),
        ("evaluation_ood", "data/evaluation/ood"),
        ("uploads", "data/uploads")
    ]
    
    for split_name, rel_dir in split_dirs:
        full_dir = os.path.join(BASE_DIR, rel_dir)
        if not os.path.exists(full_dir):
            continue
        for root, _, files in os.walk(full_dir):
            for file in files:
                ext = os.path.splitext(file)[1].lower()
                full_path = os.path.join(root, file)
                rel_path = os.path.relpath(full_path, BASE_DIR)
                
                # Exclude hidden files or logs
                if file.startswith(".") or ext in [".json", ".db", ".txt", ".csv"]:
                    continue
                
                file_size = os.path.getsize(full_path)
                sha256 = compute_sha256(full_path)
                
                is_corrupt = False
                dims = [0, 0]
                img_format = "UNKNOWN"
                mode = "UNKNOWN"
                dhash_val = None
                mean_rgb = [0.0, 0.0, 0.0]
                std_rgb = [0.0, 0.0, 0.0]
                
                try:
                    with Image.open(full_path) as im:
                        dims = [im.size[0], im.size[1]]
                        img_format = im.format
                        mode = im.mode
                        dhash_val = compute_dhash(im)
                        arr = np.array(im.convert("RGB"), dtype=np.float32)
                        mean_rgb = [round(float(x), 2) for x in arr.mean(axis=(0, 1))]
                        std_rgb = [round(float(x), 2) for x in arr.std(axis=(0, 1))]
                except Exception:
                    is_corrupt = True
                
                # Determine class from folder if in known directory
                target_class = "unknown"
                for c in ["coal", "manganese", "iron_ore", "bauxite", "quartz", "granite", "limestone", "sandstone", "basalt"]:
                    if f"/{c}" in rel_path.replace("\\", "/").lower() or f"\\{c}" in rel_path.lower():
                        target_class = c
                        break
                
                # Classify source type
                if is_corrupt:
                    source_type = "CORRUPT_FIXTURE"
                    verification_status = "UNREADABLE"
                elif split_name in ["train", "validation", "test"] or "evaluation/known" in rel_path.replace("\\", "/"):
                    source_type = "SYNTHETIC_TEXTURE_PATCH"
                    verification_status = "SYNTHETIC_REFERENCE_ONLY"
                elif "evaluation/ood" in rel_path.replace("\\", "/"):
                    source_type = "OOD_REFERENCE_LITHOLOGY"
                    verification_status = "UNSUPPORTED_ROCK_BENCHMARK"
                elif split_name == "uploads":
                    if dims == [224, 224] and std_rgb[0] == 0.0:
                        source_type = "TEST_FIXTURE_SOLID_BLOCK"
                        verification_status = "SYNTHETIC_TEST_BLOCK"
                    elif dims[0] > 500 or dims[1] > 500:
                        source_type = "UNVERIFIED_FIELD_PHOTO"
                        verification_status = "UNVERIFIED_USER_UPLOAD"
                    else:
                        source_type = "TEST_FIXTURE_API_UPLOAD"
                        verification_status = "UNVERIFIED_TEST_FIXTURE"
                else:
                    source_type = "UNCLASSIFIED"
                    verification_status = "UNVERIFIED"

                records.append({
                    "relative_path": rel_path.replace("\\", "/"),
                    "filename": file,
                    "sha256": sha256,
                    "file_size_bytes": file_size,
                    "split_source": split_name,
                    "inferred_or_assigned_class": target_class,
                    "source_type": source_type,
                    "verification_status": verification_status,
                    "is_corrupt": is_corrupt,
                    "dimensions": dims,
                    "format": img_format,
                    "mode": mode,
                    "dhash": dhash_val,
                    "mean_rgb": mean_rgb,
                    "std_rgb": std_rgb
                })
    
    print(f"Total files audited: {len(records)}")
    
    # Duplicate grouping
    hash_groups = {}
    for r in records:
        h = r["sha256"]
        if h not in hash_groups:
            hash_groups[h] = []
        hash_groups[h].append(r["relative_path"])
        
    print(f"Total unique content hashes: {len(hash_groups)}")
    
    # Summary by source_type
    summary_by_type = {}
    for r in records:
        st = r["source_type"]
        summary_by_type[st] = summary_by_type.get(st, 0) + 1
    
    print("\nBreakdown by Source Type:")
    for st, count in summary_by_type.items():
        print(f"  {st}: {count}")

    # Breakdown of field photos
    field_photos = [r for r in records if r["source_type"] == "UNVERIFIED_FIELD_PHOTO"]
    unique_field_hashes = set(r["sha256"] for r in field_photos)
    print(f"\nUnique Field Photograph Hashes: {len(unique_field_hashes)}")
    for fh in unique_field_hashes:
        matches = [r for r in field_photos if r["sha256"] == fh]
        first = matches[0]
        print(f"  Hash {fh[:12]}... (Count: {len(matches)}): {first['filename']} ({first['dimensions'][0]}x{first['dimensions'][1]}, {first['format']})")

    manifest = {
        "title": "AI Mineral Intelligence — Specimen Dataset Manifest",
        "generated_at": "2026-10-29T19:53:00Z",
        "total_files_indexed": len(records),
        "total_unique_hashes": len(hash_groups),
        "summary_by_source_type": summary_by_type,
        "records": records
    }
    
    manifest_path = os.path.join(BASE_DIR, "data", "dataset_manifest.json")
    with open(manifest_path, "w") as fp:
        json.dump(manifest, fp, indent=2)
    print(f"\nManifest saved to: {manifest_path}")

if __name__ == "__main__":
    audit_all_images()

