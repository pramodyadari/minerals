import os
import json
from collections import defaultdict

BASE_DIR = r"C:\Users\yadar\Downloads\ai_mineral_explo"
MANIFEST_PATH = os.path.join(BASE_DIR, "data", "dataset_manifest.json")

def hamming_distance(h1, h2):
    if not h1 or not h2 or len(h1) != len(h2):
        return 999
    return sum(c1 != c2 for c1, c2 in zip(h1, h2))

with open(MANIFEST_PATH, "r") as f:
    manifest = json.load(f)

records = manifest["records"]
sha_map = defaultdict(list)
for r in records:
    sha_map[r["sha256"]].append(r)

unique_records = [recs[0] for recs in sha_map.values() if recs[0].get("dhash")]

train_recs = [r for r in unique_records if r["split_source"] == "train"]
val_recs = [r for r in unique_records if r["split_source"] == "validation"]
test_recs = [r for r in unique_records if r["split_source"] == "test"]

print(f"Unique train records: {len(train_recs)}")
print(f"Unique val records: {len(val_recs)}")
print(f"Unique test records: {len(test_recs)}")

# Check train vs val
train_val_near = []
for tr in train_recs:
    for vr in val_recs:
        d = hamming_distance(tr["dhash"], vr["dhash"])
        if d <= 4:
            train_val_near.append((d, tr, vr))

# Check train vs test
train_test_near = []
for tr in train_recs:
    for te in test_recs:
        d = hamming_distance(tr["dhash"], te["dhash"])
        if d <= 4:
            train_test_near.append((d, tr, te))

# Check val vs test
val_test_near = []
for vr in val_recs:
    for te in test_recs:
        d = hamming_distance(vr["dhash"], te["dhash"])
        if d <= 4:
            val_test_near.append((d, vr, te))

print(f"Train vs Validation near duplicates (d <= 4): {len(train_val_near)}")
print(f"Train vs Test near duplicates (d <= 4): {len(train_test_near)}")
print(f"Validation vs Test near duplicates (d <= 4): {len(val_test_near)}")

if train_val_near:
    print("\nTrain vs Val near pairs:")
    for d, tr, vr in train_val_near[:5]:
        print(f"  d={d}: {tr['relative_path']} vs {vr['relative_path']}")

if train_test_near:
    print("\nTrain vs Test near pairs:")
    for d, tr, te in train_test_near[:5]:
        print(f"  d={d}: {tr['relative_path']} vs {te['relative_path']}")

