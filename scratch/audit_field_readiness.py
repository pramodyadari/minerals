import os
import sys
import json
import hashlib
from collections import defaultdict
from PIL import Image
import numpy as np

BASE_DIR = r"C:\Users\yadar\Downloads\ai_mineral_explo"
MANIFEST_PATH = os.path.join(BASE_DIR, "data", "dataset_manifest.json")
FEEDBACK_PATH = os.path.join(BASE_DIR, "data", "feedback", "specimen_feedback_queue.jsonl")

def compute_sha256(filepath):
    with open(filepath, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()

def hamming_distance(h1, h2):
    if not h1 or not h2 or len(h1) != len(h2):
        return 999
    return sum(c1 != c2 for c1, c2 in zip(h1, h2))

def run_audit():
    with open(MANIFEST_PATH, "r") as f:
        manifest = json.load(f)
    
    records = manifest["records"]
    print(f"Loaded manifest with {len(records)} records.")
    
    # Task 1: Audit manifest against actual files and hashes
    missing_files = []
    hash_mismatches = []
    actual_files_on_disk = set()
    
    # Check all files in manifest
    for r in records:
        rel_path = r["relative_path"]
        abs_path = os.path.join(BASE_DIR, rel_path.replace("/", os.sep))
        if not os.path.exists(abs_path):
            missing_files.append(rel_path)
        else:
            actual_files_on_disk.add(os.path.normpath(abs_path))
            cur_sha = compute_sha256(abs_path)
            if cur_sha != r["sha256"]:
                hash_mismatches.append({"path": rel_path, "manifest_sha": r["sha256"], "disk_sha": cur_sha})
                
    # Check if there are image files on disk not in manifest
    unindexed_files = []
    search_dirs = [
        os.path.join(BASE_DIR, "data", d) for d in ["train", "validation", "test", "evaluation", "uploads"]
    ]
    for sdir in search_dirs:
        if not os.path.exists(sdir):
            continue
        for root, _, files in os.walk(sdir):
            for file in files:
                ext = os.path.splitext(file)[1].lower()
                if ext in [".json", ".db", ".txt", ".csv"] or file.startswith("."):
                    continue
                full_p = os.path.normpath(os.path.join(root, file))
                if full_p not in actual_files_on_disk:
                    unindexed_files.append(os.path.relpath(full_p, BASE_DIR))
                    
    print(f"Audit against disk:")
    print(f"  Missing files: {len(missing_files)}")
    print(f"  Hash mismatches: {len(hash_mismatches)}")
    print(f"  Unindexed files on disk: {len(unindexed_files)}")
    if unindexed_files:
        print(f"  Unindexed list: {unindexed_files[:10]} (total {len(unindexed_files)})")
        
    # Duplicate Content (Exact SHA256)
    sha_map = defaultdict(list)
    for r in records:
        sha_map[r["sha256"]].append(r)
        
    exact_duplicates = {h: recs for h, recs in sha_map.items() if len(recs) > 1}
    print(f"\nExact Duplicate Hashes: {len(exact_duplicates)} groups across {sum(len(v) for v in exact_duplicates.values())} files")
    
    # Near-duplicates (dhash distance <= 4)
    # Check within non-exact duplicates
    dhash_map = defaultdict(list)
    for r in records:
        if r.get("dhash"):
            dhash_map[r["dhash"]].append(r)
            
    # Check pair-wise near-identical across different hashes
    unique_records = [recs[0] for recs in sha_map.values() if recs[0].get("dhash")]
    near_duplicates = []
    for i in range(len(unique_records)):
        for j in range(i + 1, len(unique_records)):
            r1 = unique_records[i]
            r2 = unique_records[j]
            dist = hamming_distance(r1["dhash"], r2["dhash"])
            if dist <= 2:  # very close perceptual hash
                near_duplicates.append({
                    "file1": r1["relative_path"],
                    "file2": r2["relative_path"],
                    "hamming_distance": dist,
                    "class1": r1["inferred_or_assigned_class"],
                    "class2": r2["inferred_or_assigned_class"],
                    "split1": r1["split_source"],
                    "split2": r2["split_source"]
                })
    print(f"Near-duplicate pairs (different SHA256, dHash dist <= 2): {len(near_duplicates)}")

    # Split Leakage Analysis
    # Does any SHA-256 exist across multiple splits among train, validation, test?
    split_leakage_exact = []
    for h, recs in sha_map.items():
        splits = set(r["split_source"] for r in recs)
        # Check if train and (validation or test) share hash
        core_splits = splits.intersection({"train", "validation", "test"})
        if len(core_splits) > 1:
            split_leakage_exact.append({
                "sha256": h,
                "splits": list(splits),
                "files": [r["relative_path"] for r in recs]
            })
    print(f"\nCross-Split Exact Leakage (train/val/test): {len(split_leakage_exact)}")
    
    # Does any near-duplicate cross train/val/test?
    cross_split_near = [nd for nd in near_duplicates if len({nd["split1"], nd["split2"]}.intersection({"train", "validation", "test"})) > 1 and nd["split1"] != nd["split2"]]
    print(f"Cross-Split Near-Duplicate Leakage: {len(cross_split_near)}")

    # Feedback Queue Inspection (Task 2)
    feedback_entries = []
    if os.path.exists(FEEDBACK_PATH):
        with open(FEEDBACK_PATH, "r") as f:
            for line in f:
                if line.strip():
                    feedback_entries.append(json.loads(line))
    print(f"\nFeedback Queue Entries: {len(feedback_entries)}")
    verified_feedbacks = [e for e in feedback_entries if e.get("is_verified_ground_truth") is True]
    training_eligible = [e for e in feedback_entries if e.get("training_eligible") is True]
    quarantined = [e for e in feedback_entries if e.get("review_status") == "PENDING_GEOLOGICAL_VALIDATION"]
    print(f"  Verified Ground Truth: {len(verified_feedbacks)}")
    print(f"  Training Eligible: {len(training_eligible)}")
    print(f"  Pending / Quarantined: {len(quarantined)}")

if __name__ == "__main__":
    run_audit()

