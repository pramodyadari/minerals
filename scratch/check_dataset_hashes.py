import os
import glob
import hashlib

def file_hash(path):
    with open(path, "rb") as f:
        return hashlib.md5(f.read()).hexdigest()

all_files = glob.glob("data/**/*.jpg", recursive=True) + glob.glob("data/**/*.png", recursive=True)
hashes = {}
duplicates = []
for p in all_files:
    h = file_hash(p)
    if h in hashes:
        duplicates.append((p, hashes[h]))
    else:
        hashes[h] = p

print(f"Total images checked: {len(all_files)}")
print(f"Unique image hashes: {len(hashes)}")
print(f"Duplicate pairs found: {len(duplicates)}")
for dup, orig in duplicates[:10]:
    print(f"  {dup} is identical to {orig}")
