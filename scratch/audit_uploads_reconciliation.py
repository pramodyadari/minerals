import os
import glob
import hashlib
import json
from collections import defaultdict
from PIL import Image
import numpy as np

BASE_DIR = r"C:\Users\yadar\Downloads\ai_mineral_explo"
UPLOADS_DIR = os.path.join(BASE_DIR, "data", "uploads")

def compute_sha256(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()

# 1. Map all reference hashes in data/train, data/test, data/validation, data/evaluation
reference_hashes = {}
search_dirs = [
    ("train", os.path.join(BASE_DIR, "data", "train")),
    ("validation", os.path.join(BASE_DIR, "data", "validation")),
    ("test", os.path.join(BASE_DIR, "data", "test")),
    ("evaluation", os.path.join(BASE_DIR, "data", "evaluation"))
]

for name, sdir in search_dirs:
    for root, _, files in os.walk(sdir):
        for f in files:
            ext = os.path.splitext(f)[1].lower()
            if ext in [".jpg", ".jpeg", ".png", ".webp", ".mpo"]:
                fp = os.path.join(root, f)
                h = compute_sha256(fp)
                rel = os.path.relpath(fp, BASE_DIR).replace("\\", "/")
                reference_hashes[h] = {"source": name, "path": rel}

# 2. Inspect all files in uploads
upload_files = []
for f in os.listdir(UPLOADS_DIR):
    fp = os.path.join(UPLOADS_DIR, f)
    if os.path.isfile(fp):
        upload_files.append(fp)

print(f"Total files in data/uploads: {len(upload_files)}")

sha_to_uploads = defaultdict(list)
for fp in upload_files:
    fname = os.path.basename(fp)
    size = os.path.getsize(fp)
    sha = compute_sha256(fp)
    
    is_corrupt = False
    dims = [0, 0]
    fmt = "UNKNOWN"
    std_rgb = [0.0, 0.0, 0.0]
    try:
        with Image.open(fp) as im:
            dims = list(im.size)
            fmt = im.format
            arr = np.array(im.convert("RGB"), dtype=np.float32)
            std_rgb = [float(x) for x in arr.std(axis=(0,1))]
    except Exception:
        is_corrupt = True

    sha_to_uploads[sha].append({
        "path": os.path.relpath(fp, BASE_DIR).replace("\\", "/"),
        "filename": fname,
        "size": size,
        "is_corrupt": is_corrupt,
        "dims": dims,
        "format": fmt,
        "std_rgb": std_rgb
    })

print(f"Unique SHA-256 hashes in data/uploads: {len(sha_to_uploads)}")

# 3. Classify files into exact categories:
# - Original user uploads (earliest timestamp among user macroscopic photos)
# - Exact duplicate copies (subsequent copies of user uploads or repeated test fixtures)
# - Test-generated API uploads (matching reference test/evaluation files, or small synthetic test files)
# - Corrupt test fixtures (is_corrupt == True or size < 100 bytes)
# - Solid-block test fixtures (std == 0)

classified_files = {
    "original_user_uploads": [],
    "duplicate_user_upload_copies": [],
    "test_generated_api_uploads_from_reference": [],
    "test_generated_api_uploads_small_synthetic": [],
    "corrupt_test_fixtures": [],
    "solid_block_test_fixtures": [],
    "other_or_unknown": []
}

# The 3 known unique macroscopic field photos:
KNOWN_USER_HASHES = {
    "70df91e2acfb562d95410d4e043bb1001807c1e9d8ae5898fd4e08ed11e1a1fb": "SPECIMEN_FIELD_COAL_001",
    "c31314697563e17891e7f9289e569e00bb2196e012d171736a50f8da579041ef": "SPECIMEN_FIELD_MANGANESE_001",
    "8797163ce43ed7b63d9caf65ffb1141ea48d79860fdd569b0bb113ab15a8777b": "SPECIMEN_FIELD_ROCK_001"
}

for sha, file_list in sha_to_uploads.items():
    # Sort by filename (which starts with timestamp YYYYMMDD_HHMMSS)
    file_list_sorted = sorted(file_list, key=lambda x: x["filename"])
    
    if sha in KNOWN_USER_HASHES:
        # Earliest is original user upload
        primary = file_list_sorted[0]
        primary["specimen_id"] = KNOWN_USER_HASHES[sha]
        classified_files["original_user_uploads"].append(primary)
        
        # Rest are exact duplicate upload copies
        for dup in file_list_sorted[1:]:
            dup["specimen_id"] = KNOWN_USER_HASHES[sha]
            dup["primary_reference"] = primary["path"]
            classified_files["duplicate_user_upload_copies"].append(dup)
            
    elif any(f["is_corrupt"] for f in file_list):
        for f in file_list:
            classified_files["corrupt_test_fixtures"].append(f)
            
    elif file_list[0]["dims"] == [224, 224] and all(s == 0.0 for s in file_list[0]["std_rgb"]):
        for f in file_list:
            classified_files["solid_block_test_fixtures"].append(f)
            
    elif sha in reference_hashes:
        # Uploads of test or evaluation reference images
        for f in file_list:
            f["matched_reference"] = reference_hashes[sha]["path"]
            classified_files["test_generated_api_uploads_from_reference"].append(f)
            
    elif file_list[0]["dims"] == [224, 224] or file_list[0]["dims"] == [64, 64]:
        for f in file_list:
            classified_files["test_generated_api_uploads_small_synthetic"].append(f)
            
    else:
        for f in file_list:
            classified_files["other_or_unknown"].append(f)

print("\n=== CLASSIFICATION SUMMARY ===")
for cat, files in classified_files.items():
    print(f"Category: {cat:45s} -> Count: {len(files)}")

if classified_files["other_or_unknown"]:
    print("\nOther / Unknown files:")
    for f in classified_files["other_or_unknown"]:
        print(f"  {f['filename']} (size={f['size']}, dims={f['dims']})")

