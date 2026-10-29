import os
import sys
sys.path.insert(0, os.path.abspath('.'))
from backend.app.vision_service import classify_specimen_image

print("Scanning for images where closest candidate is Manganese...")
for root, dirs, files in os.walk('.'):
    if any(ignore in root for ignore in ['node_modules', '.git', '.venv']):
        continue
    for f in files:
        if f.lower().endswith(('.jpg', '.jpeg', '.png', '.webp')):
            p = os.path.join(root, f)
            try:
                with open(p, 'rb') as fp:
                    data = fp.read()
                res = classify_specimen_image(data)
                dist = res.get('feature_distance')
                cand = res.get('closest_candidate_mineral')
                supp = res.get('is_supported_mineral')
                pred = res.get('predicted_mineral')
                if cand == 'Manganese':
                    print(f"{p}: dist={dist}, supp={supp}, pred={pred}")
            except Exception as e:
                pass
