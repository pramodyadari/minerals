import glob
import os
import sys
sys.path.insert(0, os.path.abspath('.'))
import json
from ai.predict import predict_image

files = glob.glob('data/test/*.*') + glob.glob('data/test/*/*.*') + glob.glob('data/validation/*/*.*') + glob.glob('data/train/*/*.*') + glob.glob('data/evaluation/*/*.*') + glob.glob('data/evaluation/*/*/*.*')
print(f"Total files found: {len(files)}")

for f in files:
    if f.lower().endswith(('.jpg', '.png', '.jpeg', '.webp')):
        try:
            res = predict_image(f)
            if res.get('status') == 'SUCCESS':
                dist = res.get('feature_distance')
                cand = res.get('closest_candidate_mineral')
                supp = res.get('is_supported_mineral')
                pred = res.get('predicted_mineral')
                if dist is not None and (dist > 4.5 or not supp):
                    print(f"{f}: dist={dist:.2f}, supp={supp}, pred={pred}, cand={cand}")
        except Exception as e:
            print(f"Error on {f}: {e}")
