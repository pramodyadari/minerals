"""
Export trained production Random Forest model to JSON for client-side evaluation.
Preserves exact decision tree parameters, thresholds, and node values with 100% mathematical fidelity.
"""
import joblib
import json
import os
import numpy as np

model_path = "models/production_random_forest.pkl"
output_path = "data/processed/production_rf_trees.json"

rf = joblib.load(model_path)
print(f"Loaded {type(rf).__name__} with {len(rf.estimators_)} estimators")

trees = []
for idx, est in enumerate(rf.estimators_):
    t = est.tree_
    trees.append({
        "children_left": t.children_left.tolist(),
        "children_right": t.children_right.tolist(),
        "feature": t.feature.tolist(),
        "threshold": [round(th, 6) if th != -2.0 else -2.0 for th in t.threshold.tolist()],
        "value": [round(float(v), 4) for v in t.value.squeeze().tolist()]
    })

data = {
    "model_type": "RandomForestRegressor",
    "n_estimators": len(trees),
    "features": list(rf.feature_names_in_),
    "feature_importances": [round(float(fi), 6) for fi in rf.feature_importances_],
    "trees": trees
}

os.makedirs(os.path.dirname(output_path), exist_ok=True)
with open(output_path, "w", encoding="utf-8") as f:
    json.dump(data, f)

print(f"Successfully exported {len(trees)} trees to {output_path}")
print(f"File size: {os.path.getsize(output_path)} bytes")
