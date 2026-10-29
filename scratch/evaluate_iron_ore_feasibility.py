import os
import sys
import csv
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    roc_auc_score, average_precision_score, confusion_matrix
)
from sklearn.model_selection import StratifiedKFold, GroupKFold

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
csv_path = os.path.join(PROJECT_ROOT, "data", "training", "iron_ore_training.csv")

with open(csv_path, "r", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    rows = list(reader)

feature_cols = ["B02", "B03", "B04", "B08", "B11", "B12", "NDVI", "NDWI", "clay_ratio", "iron_oxide_ratio"]

# Balanced dataset: sample equal positives per deposit
positives = [r for r in rows if r["label"] == "1"]
negatives = [r for r in rows if r["label"] == "0"]

print(f"Total Positives: {len(positives)}, Total Negatives: {len(negatives)}")

# Subsample positives to match negatives (~1800 positives, ~360 per deposit)
np.random.seed(42)
deposits = set(r["deposit_name"] for r in positives)
balanced_positives = []
target_per_dep = len(negatives) // len(deposits)

for dep in deposits:
    dep_rows = [r for r in positives if r["deposit_name"] == dep]
    chosen = np.random.choice(len(dep_rows), size=min(target_per_dep, len(dep_rows)), replace=False)
    for idx in chosen:
        balanced_positives.append(dep_rows[idx])

dataset = balanced_positives + negatives
np.random.shuffle(dataset)

print(f"Balanced Dataset: {len(dataset)} samples ({len(balanced_positives)} positive, {len(negatives)} negative)")

X = np.array([[float(r[col]) for col in feature_cols] for r in dataset])
y = np.array([int(r["label"]) for r in dataset])
groups = np.array([r["deposit_name"] for r in dataset])

# 1. Standard Stratified Cross-Validation (Random Split)
skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
accs, recs, precs, f1s, aucs, praucs = [], [], [], [], [], []

for train_idx, test_idx in skf.split(X, y):
    clf = RandomForestClassifier(n_estimators=100, random_state=42, n_jobs=-1)
    clf.fit(X[train_idx], y[train_idx])
    preds = clf.predict(X[test_idx])
    probs = clf.predict_proba(X[test_idx])[:, 1]
    
    accs.append(accuracy_score(y[test_idx], preds))
    precs.append(precision_score(y[test_idx], preds, zero_division=0))
    recs.append(recall_score(y[test_idx], preds, zero_division=0))
    f1s.append(f1_score(y[test_idx], preds, zero_division=0))
    aucs.append(roc_auc_score(y[test_idx], probs))
    praucs.append(average_precision_score(y[test_idx], probs))

print("\n--- RANDOM STRATIFIED 5-FOLD CV ---")
print(f"  Accuracy:  {np.mean(accs):.4f} +/- {np.std(accs):.4f}")
print(f"  Precision: {np.mean(precs):.4f} +/- {np.std(precs):.4f}")
print(f"  Recall:    {np.mean(recs):.4f} +/- {np.std(recs):.4f}")
print(f"  F1 Score:  {np.mean(f1s):.4f} +/- {np.std(f1s):.4f}")
print(f"  ROC-AUC:   {np.mean(aucs):.4f} +/- {np.std(aucs):.4f}")
print(f"  PR-AUC:    {np.mean(praucs):.4f} +/- {np.std(praucs):.4f}")

# 2. Spatially Blocked Validation (Group / Geographic Block Validation)
# Block by geographic deposit / sector to prevent spatial leakage
gkf = GroupKFold(n_splits=min(5, len(set(groups))))
sp_accs, sp_recs, sp_precs, sp_f1s, sp_aucs, sp_praucs = [], [], [], [], [], []

print("\n--- SPATIALLY BLOCKED (LEAVE-GROUP-OUT) CV ---")
for fold, (train_idx, test_idx) in enumerate(gkf.split(X, y, groups=groups)):
    test_groups = set(groups[test_idx])
    clf = RandomForestClassifier(n_estimators=100, random_state=42, n_jobs=-1)
    clf.fit(X[train_idx], y[train_idx])
    preds = clf.predict(X[test_idx])
    probs = clf.predict_proba(X[test_idx])[:, 1]
    
    acc = accuracy_score(y[test_idx], preds)
    prec = precision_score(y[test_idx], preds, zero_division=0)
    rec = recall_score(y[test_idx], preds, zero_division=0)
    f1 = f1_score(y[test_idx], preds, zero_division=0)
    
    # If test fold has only one class, AUC is undefined
    has_both = len(set(y[test_idx])) > 1
    auc = roc_auc_score(y[test_idx], probs) if has_both else None
    prauc = average_precision_score(y[test_idx], probs) if has_both else None
    
    sp_accs.append(acc)
    sp_precs.append(prec)
    sp_recs.append(rec)
    sp_f1s.append(f1)
    if auc is not None:
        sp_aucs.append(auc)
    if prauc is not None:
        sp_praucs.append(prauc)
        
    print(f"  Fold {fold+1} (Held-out: {test_groups}): Acc={acc:.4f}, Prec={prec:.4f}, Rec={rec:.4f}, F1={f1:.4f}")

print(f"\nSpatially Blocked Overall:")
print(f"  Accuracy:  {np.mean(sp_accs):.4f} +/- {np.std(sp_accs):.4f}")
print(f"  Precision: {np.mean(sp_precs):.4f} +/- {np.std(sp_precs):.4f}")
print(f"  Recall:    {np.mean(sp_recs):.4f} +/- {np.std(sp_recs):.4f}")
print(f"  F1 Score:  {np.mean(sp_f1s):.4f} +/- {np.std(sp_f1s):.4f}")
if sp_aucs:
    print(f"  ROC-AUC:   {np.mean(sp_aucs):.4f} +/- {np.std(sp_aucs):.4f}")
if sp_praucs:
    print(f"  PR-AUC:    {np.mean(sp_praucs):.4f} +/- {np.std(sp_praucs):.4f}")

# Train full model on balanced dataset to inspect feature importances
full_clf = RandomForestClassifier(n_estimators=100, random_state=42, n_jobs=-1)
full_clf.fit(X, y)
print("\nFeature Importances:")
for col, imp in sorted(zip(feature_cols, full_clf.feature_importances_), key=lambda x: -x[1]):
    print(f"  {col:18s}: {imp:.4f}")
