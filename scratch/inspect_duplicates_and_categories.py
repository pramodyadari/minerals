import os
import json
from collections import defaultdict

BASE_DIR = r"C:\Users\yadar\Downloads\ai_mineral_explo"
MANIFEST_PATH = os.path.join(BASE_DIR, "data", "dataset_manifest.json")

with open(MANIFEST_PATH, "r") as f:
    manifest = json.load(f)

records = manifest["records"]

# 1. Exact duplicate groups breakdown
sha_map = defaultdict(list)
for r in records:
    sha_map[r["sha256"]].append(r)

exact_dups = {h: recs for h, recs in sha_map.items() if len(recs) > 1}
print(f"=== EXACT DUPLICATE GROUPS ({len(exact_dups)}) ===")
for h, recs in sorted(exact_dups.items(), key=lambda x: len(x[1]), reverse=True):
    paths = [r["relative_path"] for r in recs]
    source_types = set(r["source_type"] for r in recs)
    classes = set(r["inferred_or_assigned_class"] for r in recs)
    splits = set(r["split_source"] for r in recs)
    print(f"Hash {h[:12]}... (Count: {len(recs)}):")
    print(f"  Sample path: {paths[0]}")
    print(f"  Source types: {source_types}")
    print(f"  Classes: {classes}")
    print(f"  Splits: {splits}")
    if len(paths) <= 5:
        print(f"  All paths: {paths}")
    print()

# 2. Source category and verification status breakdown
print("=== SOURCE CATEGORY & VERIFICATION STATUS BREAKDOWN ===")
cat_summary = defaultdict(lambda: defaultdict(int))
for r in records:
    cat_summary[r["source_type"]][r["verification_status"]] += 1

for st, vs_dict in sorted(cat_summary.items()):
    print(f"Source Type: {st}")
    for vs, cnt in sorted(vs_dict.items()):
        print(f"  {vs}: {cnt}")

# 3. Inferred Class by Source Type
print("\n=== INFERRED CLASS BY SOURCE TYPE ===")
class_by_source = defaultdict(lambda: defaultdict(int))
for r in records:
    class_by_source[r["source_type"]][r["inferred_or_assigned_class"]] += 1

for st, cls_dict in sorted(class_by_source.items()):
    print(f"Source Type: {st}")
    for c, cnt in sorted(cls_dict.items()):
        print(f"  {c}: {cnt}")

