import os
import glob
import hashlib

def get_hash(p):
    with open(p, "rb") as f:
        return hashlib.md5(f.read()).hexdigest()

known_eval = glob.glob("data/evaluation/known/**/*.jpg", recursive=True)
val_files = {get_hash(p): p for p in glob.glob("data/validation/**/*.jpg", recursive=True)}
test_files = {get_hash(p): p for p in glob.glob("data/test/**/*.jpg", recursive=True)}
train_files = {get_hash(p): p for p in glob.glob("data/train/**/*.jpg", recursive=True)}

print(f"Total evaluation/known files: {len(known_eval)}")
matched_val = 0
matched_test = 0
matched_train = 0
matched_none = 0

for p in known_eval:
    h = get_hash(p)
    if h in val_files:
        matched_val += 1
    elif h in test_files:
        matched_test += 1
    elif h in train_files:
        matched_train += 1
    else:
        matched_none += 1

print(f"Matched in validation: {matched_val}")
print(f"Matched in test: {matched_test}")
print(f"Matched in train: {matched_train}")
print(f"Matched none (new/unique): {matched_none}")
