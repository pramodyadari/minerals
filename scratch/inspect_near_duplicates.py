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
near_duplicates = []
for i in range(len(unique_records)):
    for j in range(i + 1, len(unique_records)):
        r1 = unique_records[i]
        r2 = unique_records[j]
        dist = hamming_distance(r1["dhash"], r2["dhash"])
        if dist <= 2:
            near_duplicates.append((dist, r1, r2))

print(f"Total near-duplicate pairs with dHash dist <= 2: {len(near_duplicates)}")
for dist, r1, r2 in near_duplicates[:25]:
    print(f"Dist {dist}: {r1['relative_path']} ({r1['split_source']}, {r1['inferred_or_assigned_class']}) <--> {r2['relative_path']} ({r2['split_source']}, {r2['inferred_or_assigned_class']})")

