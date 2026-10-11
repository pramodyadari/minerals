"""
AI Mineral Intelligence — Independent Test Evaluation & Metrics (Section 5)
Computes:
  - Overall Test Accuracy
  - Per-class Precision, Recall, F1-score
  - Confusion Matrix (4x4)
  - Macro and Weighted Averages
Saves evaluation report to models/evaluation_report.json.
"""

import os
import json
import torch
import numpy as np
from torch.utils.data import DataLoader

from train import MineralDataset, MineralConvNet, CLASSES, CLASS_TO_IDX, IDX_TO_CLASS, MODEL_PATH

EVAL_REPORT_PATH = "models/evaluation_report.json"

def evaluate_model(data_dir="data", model_path=MODEL_PATH):
    print("=" * 60)
    print("AI MINERAL SPECIMEN CLASSIFIER — INDEPENDENT EVALUATION")
    print("=" * 60)

    test_ds = MineralDataset(data_dir, split="test", augment=False)
    test_loader = DataLoader(test_ds, batch_size=16, shuffle=False)

    num_classes = len(CLASSES)
    device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")

    model = MineralConvNet(num_classes=num_classes)
    if not os.path.exists(model_path):
        raise FileNotFoundError(f"Model file not found at {model_path}. Please run train.py first.")

    model.load_state_dict(torch.load(model_path, map_location=device))
    model = model.to(device)
    model.eval()

    y_true = []
    y_pred = []

    with torch.no_grad():
        for inputs, labels in test_loader:
            inputs = inputs.to(device)
            outputs = model(inputs)
            _, preds = torch.max(outputs, 1)
            y_true.extend(labels.cpu().numpy().tolist())
            y_pred.extend(preds.cpu().numpy().tolist())

    y_true = np.array(y_true)
    y_pred = np.array(y_pred)

    total_samples = len(y_true)
    overall_acc = float(np.mean(y_true == y_pred))

    # Confusion Matrix (4x4)
    cm = np.zeros((num_classes, num_classes), dtype=int)
    for t, p in zip(y_true, y_pred):
        cm[t, p] += 1

    per_class_metrics = {}
    precisions = []
    recalls = []
    f1s = []

    for i in range(num_classes):
        cls_name = IDX_TO_CLASS[i]
        tp = int(cm[i, i])
        fp = int(np.sum(cm[:, i]) - tp)
        fn = int(np.sum(cm[i, :]) - tp)
        support = int(np.sum(cm[i, :]))

        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = (2 * precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0

        precisions.append(precision)
        recalls.append(recall)
        f1s.append(f1)

        per_class_metrics[cls_name] = {
            "precision": round(float(precision), 4),
            "recall": round(float(recall), 4),
            "f1_score": round(float(f1), 4),
            "support": support
        }

    report = {
        "evaluation_split": "test",
        "total_test_samples": total_samples,
        "overall_accuracy_pct": round(overall_acc * 100, 2),
        "macro_avg": {
            "precision": round(float(np.mean(precisions)), 4),
            "recall": round(float(np.mean(recalls)), 4),
            "f1_score": round(float(np.mean(f1s)), 4)
        },
        "per_class_metrics": per_class_metrics,
        "confusion_matrix": {
            "classes": [IDX_TO_CLASS[i] for i in range(num_classes)],
            "matrix": cm.tolist()
        },
        "integrity_notice": "Independent test set evaluation. Does not substitute subsurface drilling or geophysical surveys."
    }

    os.makedirs(os.path.dirname(EVAL_REPORT_PATH), exist_ok=True)
    with open(EVAL_REPORT_PATH, "w") as fp:
        json.dump(report, fp, indent=2)

    print(f"\nOverall Test Accuracy: {report['overall_accuracy_pct']:.2f}%")
    print(f"Macro Precision:       {report['macro_avg']['precision']:.4f}")
    print(f"Macro Recall:          {report['macro_avg']['recall']:.4f}")
    print(f"Macro F1-Score:        {report['macro_avg']['f1_score']:.4f}\n")
    print("Per-Class Metrics:")
    for cls, m in per_class_metrics.items():
        print(f"  {cls:12s} | Prec: {m['precision']:.3f} | Rec: {m['recall']:.3f} | F1: {m['f1_score']:.3f} | Support: {m['support']}")

    print("\nConfusion Matrix (Rows = Ground Truth, Cols = Prediction):")
    header = "             " + "  ".join([f"{IDX_TO_CLASS[i][:6]:>6}" for i in range(num_classes)])
    print(header)
    for i in range(num_classes):
        row_str = f"{IDX_TO_CLASS[i][:11]:12s} " + "  ".join([f"{cm[i, j]:6d}" for j in range(num_classes)])
        print(row_str)

    print(f"\nSaved evaluation metrics -> {EVAL_REPORT_PATH}")
    return report

if __name__ == "__main__":
    evaluate_model()
