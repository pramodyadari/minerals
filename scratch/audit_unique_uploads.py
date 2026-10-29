import os
import glob
import hashlib
import sys

sys.path.insert(0, os.path.abspath('.'))
from backend.app.vision_service import classify_specimen_image

files = glob.glob('data/uploads/*.*')
by_hash = {}
for f in files:
    with open(f, 'rb') as fp:
        data = fp.read()
    h = hashlib.sha256(data).hexdigest()
    if h not in by_hash:
        by_hash[h] = f

print(f"=== AUDIT OF ALL {len(by_hash)} UNIQUE UPLOADS ===")
print(f"{'Filename':35s} | {'Status':16s} | {'Predicted':22s} | {'Nearest Cand':14s} | {'Dist':6s} | {'Probabilities'}")
print("-" * 125)
for h, f in by_hash.items():
    try:
        with open(f, 'rb') as fp:
            data = fp.read()
        res = classify_specimen_image(data)
        fname = os.path.basename(f)
        status = res.get('identification_status') or res.get('status')
        pred = res.get('predicted_mineral') or '-'
        cand = res.get('closest_candidate') or '-'
        dist = f"{res.get('feature_distance'):.2f}" if res.get('feature_distance') is not None else '-'
        probs = res.get('class_probabilities_pct') or {}
        p_str = ' '.join(f"{k[:4]}:{v:.0f}%" for k, v in probs.items())
        print(f"{fname[:35]:35s} | {str(status):16s} | {pred[:22]:22s} | {str(cand)[:14]:14s} | {dist:6s} | {p_str}")
    except Exception as e:
        print(f"{os.path.basename(f)[:35]:35s} | ERROR: {e}")

