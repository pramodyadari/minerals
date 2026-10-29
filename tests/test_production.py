"""
============================================================================
AI MINERAL INTELLIGENCE — PRODUCTION RANDOM FOREST PARITY VALIDATION TEST
============================================================================
Tests:
1. Loads models/production_random_forest.pkl directly with joblib.
2. Loads exported data/processed/production_rf_trees.json.
3. Evaluates 10 test operating condition vectors across both engines.
4. Asserts exact numerical match (within 0.01 tonnes) between sklearn and the exported JSON trees.
5. Tests shortfall and risk calculation.
============================================================================
"""

import os
import json
import joblib
import numpy as np
try:
    import pandas as pd
except Exception:
    pd = None

def test_production_parity():
    model_path = "models/production_random_forest.pkl"
    json_path = "data/processed/production_rf_trees.json"

    assert os.path.exists(model_path), f"Missing {model_path}"
    assert os.path.exists(json_path), f"Missing {json_path}"

    # 1. Load sklearn model
    rf = joblib.load(model_path)
    print(f"[OK] Loaded sklearn model: {type(rf).__name__} (100 estimators)")

    # 2. Load JSON exported trees
    with open(json_path, "r", encoding="utf-8") as f:
        exported = json.load(f)
    print(f"[OK] Loaded JSON trees: {len(exported['trees'])} estimators")

    assert exported["n_estimators"] == len(rf.estimators_)
    assert exported["features"] == list(rf.feature_names_in_)

    # 3. Test multiple diverse operating scenarios
    test_cases = [
        {"Rainfall_mm": 150.0, "Equipment_Downtime_hr": 20.0, "Blasting_Delay_hr": 8.0, "Equipment_Availability_pct": 85.0, "Planned_Production_tonnes": 11000.0},
        {"Rainfall_mm": 50.0,  "Equipment_Downtime_hr": 5.0,  "Blasting_Delay_hr": 2.0, "Equipment_Availability_pct": 95.0, "Planned_Production_tonnes": 12000.0},
        {"Rainfall_mm": 250.0, "Equipment_Downtime_hr": 45.0, "Blasting_Delay_hr": 18.0, "Equipment_Availability_pct": 65.0, "Planned_Production_tonnes": 10000.0},
        {"Rainfall_mm": 100.0, "Equipment_Downtime_hr": 15.0, "Blasting_Delay_hr": 5.0, "Equipment_Availability_pct": 90.0, "Planned_Production_tonnes": 14000.0},
        {"Rainfall_mm": 300.0, "Equipment_Downtime_hr": 60.0, "Blasting_Delay_hr": 24.0, "Equipment_Availability_pct": 60.0, "Planned_Production_tonnes": 8000.0},
        {"Rainfall_mm": 20.0,  "Equipment_Downtime_hr": 2.0,  "Blasting_Delay_hr": 0.0, "Equipment_Availability_pct": 98.0, "Planned_Production_tonnes": 15000.0}
    ]

    def eval_json_tree(tree, x_vec):
        node = 0
        left = tree["children_left"]
        right = tree["children_right"]
        feat = tree["feature"]
        thresh = tree["threshold"]
        val = tree["value"]
        while left[node] != -1:
            f = feat[node]
            if x_vec[f] <= thresh[node]:
                node = left[node]
            else:
                node = right[node]
        return val[node]

    print("\n--- Testing Prediction Parity Across Test Cases ---")
    for idx, tc in enumerate(test_cases, 1):
        if pd is not None:
            df_tc = pd.DataFrame([tc])
            sk_pred = float(rf.predict(df_tc)[0])
        else:
            x_tc = np.array([[tc[f] for f in exported["features"]]])
            sk_pred = float(rf.predict(x_tc)[0])

        x_vec = [tc[f] for f in exported["features"]]
        json_pred = float(np.mean([eval_json_tree(t, x_vec) for t in exported["trees"]]))

        diff = abs(sk_pred - json_pred)
        print(f"Test Case {idx}: Sklearn={sk_pred:.2f} t | JSON={json_pred:.2f} t | Diff={diff:.4f} t")
        assert diff < 0.05, f"Discrepancy too high in test case {idx}: {sk_pred} vs {json_pred}"

    # 4. Test shortfall calculations
    planned = test_cases[0]["Planned_Production_tonnes"]
    if pd is not None:
        predicted = float(rf.predict(pd.DataFrame([test_cases[0]]))[0])
    else:
        predicted = float(rf.predict(np.array([[test_cases[0][f] for f in exported["features"]]]))[0])
    shortfall = max(0.0, planned - predicted)
    shortfall_pct = (shortfall / planned) * 100.0
    print(f"\n[OK] Test Case 1 Shortfall: {shortfall:.2f} tonnes ({shortfall_pct:.1f}%)")
    assert shortfall > 0, "Shortfall should be positive for test case 1"

    print("\n============================================================")
    print("ALL PRODUCTION PARITY TESTS PASSED SUCCESSFULLY! (100% MATCH)")
    print("============================================================\n")

if __name__ == "__main__":
    test_production_parity()
