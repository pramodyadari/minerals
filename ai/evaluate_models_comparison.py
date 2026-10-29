"""
AI Mineral Intelligence — Fair Model Comparison & Scientific Evaluation (Phase 3)
Evaluates:
  1. Baseline MineralConvNet (models/mineral_image_classifier_baseline_cnn.pth)
  2. Improved MineralResNet18 (models/mineral_resnet18.pth)
On the untouched held-out test set (data/test) and real-world field photographs.
Computes:
  - Accuracy and Balanced Accuracy
  - Per-class Precision, Recall, and F1-Score
  - Macro-F1 and Weighted-F1
  - 4x4 Confusion Matrix
  - Real photograph behavior on disputed Coal & Manganese samples.
"""

import os
import sys
import time
import json
import numpy as np
import torch
import torch.nn.functional as F
from PIL import Image

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from ai.train import MineralConvNet, CLASSES, CLASS_TO_IDX, IDX_TO_CLASS
from ai.train_improved import MineralResNet18

CLASS_DISPLAY = {
    "coal": "Coal",
    "manganese": "Manganese",
    "iron_ore": "Iron Ore",
    "bauxite": "Bauxite"
}

def load_image_tensor(img_path):
    with Image.open(img_path) as im:
        rgb = im.convert("RGB").resize((224, 224), Image.BILINEAR)
        arr = np.array(rgb, dtype=np.float32) / 255.0
        mean = np.array([0.485, 0.456, 0.406], dtype=np.float32)
        std = np.array([0.229, 0.224, 0.225], dtype=np.float32)
        arr = (arr - mean) / std
        return torch.from_numpy(arr).permute(2, 0, 1).unsqueeze(0).float()

def evaluate_model_on_test_set(model, model_type="resnet18", test_dir="data/test"):
    device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
    model = model.to(device)
    model.eval()

    y_true = []
    y_pred = []
    probabilities = []

    samples_by_class = {c: [] for c in CLASSES}
    for cls in CLASSES:
        folder = os.path.join(BASE_DIR, test_dir, cls)
        for fname in sorted(os.listdir(folder)):
            if fname.lower().endswith(('.jpg', '.jpeg', '.png')):
                samples_by_class[cls].append(os.path.join(folder, fname))

    with torch.no_grad():
        for cls_idx, cls in enumerate(CLASSES):
            for fpath in samples_by_class[cls]:
                t = load_image_tensor(fpath).to(device)
                if model_type == "resnet18":
                    _, _, logits = model.extract_features(t)
                else:
                    f256 = torch.flatten(model.features(t), 1)
                    h128 = model.classifier[2](model.classifier[1](f256))
                    logits = model.classifier[4](h128)
                
                probs = F.softmax(logits, dim=1).squeeze(0).cpu().numpy()
                pred_idx = int(probs.argmax())
                
                y_true.append(cls_idx)
                y_pred.append(pred_idx)
                probabilities.append(probs)

    y_true = np.array(y_true)
    y_pred = np.array(y_pred)
    total = len(y_true)

    # 1. Confusion Matrix
    cm = np.zeros((len(CLASSES), len(CLASSES)), dtype=int)
    for t, p in zip(y_true, y_pred):
        cm[t, p] += 1

    # 2. Per-class Precision, Recall, F1
    per_class = {}
    recalls = []
    precisions = []
    f1s = []
    support = []

    for idx, cls in enumerate(CLASSES):
        tp = cm[idx, idx]
        fn = cm[idx, :].sum() - tp
        fp = cm[:, idx].sum() - tp
        prec = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        rec = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = (2 * prec * rec) / (prec + rec) if (prec + rec) > 0 else 0.0
        sup = int(cm[idx, :].sum())

        per_class[cls] = {
            "display_name": CLASS_DISPLAY[cls],
            "support": sup,
            "precision": round(float(prec), 4),
            "recall": round(float(rec), 4),
            "f1_score": round(float(f1), 4),
        }
        precisions.append(prec)
        recalls.append(rec)
        f1s.append(f1)
        support.append(sup)

    accuracy = float((y_true == y_pred).sum() / total)
    balanced_acc = float(np.mean(recalls))
    macro_f1 = float(np.mean(f1s))
    weights = np.array(support) / total
    weighted_f1 = float(np.sum(np.array(f1s) * weights))

    return {
        "total_samples": total,
        "accuracy_pct": round(accuracy * 100, 2),
        "balanced_accuracy_pct": round(balanced_acc * 100, 2),
        "macro_f1": round(macro_f1, 4),
        "weighted_f1": round(weighted_f1, 4),
        "confusion_matrix": cm.tolist(),
        "per_class_metrics": per_class,
    }

def evaluate_field_photographs(model, model_type="resnet18"):
    device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
    model = model.to(device)
    model.eval()

    field_samples = [
        {
            "name": "Disputed Bituminous Coal Upload",
            "path": os.path.join(BASE_DIR, "data", "uploads", "20261029_125012_70df91e2acfb_Bituminous_Coal.jpg"),
            "expected_mineral": "Coal",
            "ground_truth_status": "Observed specimen photo supplied as Coal (vitreous luster, white card background)"
        },
        {
            "name": "Dark Shiny Manganese Upload",
            "path": os.path.join(BASE_DIR, "data", "uploads", "20261029_124929_c31314697563_2a95d3e8-610f-4bff-9bc7-c9700e76d534.png"),
            "expected_mineral": "Manganese",
            "ground_truth_status": "Observed specimen photo supplied as Manganese (metallic specular luster)"
        },
        {
            "name": "Manganese Dark Shiny Test Fixture",
            "path": os.path.join(BASE_DIR, "data", "test", "manganese_dark_shiny_test.jpg"),
            "expected_mineral": "Manganese",
            "ground_truth_status": "Dark body with specular highlights test fixture"
        }
    ]

    results = []
    with torch.no_grad():
        for item in field_samples:
            p = item["path"]
            if not os.path.exists(p):
                continue
            t = load_image_tensor(p).to(device)
            if model_type == "resnet18":
                f, h128, logits = model.extract_features(t)
            else:
                f256 = torch.flatten(model.features(t), 1)
                h128 = model.classifier[2](model.classifier[1](f256))
                logits = model.classifier[4](h128)
            
            probs = F.softmax(logits, dim=1).squeeze(0).cpu().numpy()
            pred_idx = int(probs.argmax())
            pred_cls = CLASSES[pred_idx]
            
            probs_pct = {CLASS_DISPLAY[c]: round(float(probs[i]) * 100, 2) for i, c in enumerate(CLASSES)}
            results.append({
                "sample_name": item["name"],
                "file_path": os.path.relpath(p, BASE_DIR),
                "expected_mineral": item["expected_mineral"],
                "predicted_class": pred_cls,
                "predicted_mineral": CLASS_DISPLAY[pred_cls],
                "confidence_pct": round(float(probs[pred_idx]) * 100, 2),
                "probabilities": probs_pct,
                "ground_truth_status": item["ground_truth_status"]
            })

    return results

def run_comparison():
    print("=" * 80)
    print("PHASE 3: FAIR MODEL COMPARISON — BASELINE CNN vs IMPROVED RESNET-18")
    print("=" * 80)

    # 1. Load Baseline CNN
    baseline_weights = os.path.join(BASE_DIR, "models", "mineral_image_classifier_baseline_cnn.pth")
    if not os.path.exists(baseline_weights):
        baseline_weights = os.path.join(BASE_DIR, "models", "mineral_image_classifier.pth")
    baseline_model = MineralConvNet(num_classes=len(CLASSES))
    baseline_model.load_state_dict(torch.load(baseline_weights, map_location="cpu"))
    print(f"Loaded Baseline Model: MineralConvNet from {os.path.relpath(baseline_weights, BASE_DIR)}")

    # 2. Load Improved ResNet-18
    resnet_weights = os.path.join(BASE_DIR, "models", "mineral_resnet18.pth")
    resnet_model = MineralResNet18(num_classes=len(CLASSES))
    resnet_model.load_state_dict(torch.load(resnet_weights, map_location="cpu"))
    print(f"Loaded Improved Model: MineralResNet18 from {os.path.relpath(resnet_weights, BASE_DIR)}")

    # 3. Evaluate Both on Touched/Untouched Test Set
    baseline_eval = evaluate_model_on_test_set(baseline_model, model_type="convnet")
    resnet_eval = evaluate_model_on_test_set(resnet_model, model_type="resnet18")

    # 4. Evaluate on Field Photographs
    baseline_field = evaluate_field_photographs(baseline_model, model_type="convnet")
    resnet_field = evaluate_field_photographs(resnet_model, model_type="resnet18")

    # 5. Print Comparison Table
    print("\n" + "=" * 80)
    print("TEST SET CLASSIFICATION METRICS (Untouched Test Split, N=40):")
    print("=" * 80)
    print(f"{'Metric':32s} | {'Baseline MineralConvNet':24s} | {'Improved MineralResNet18':24s}")
    print("-" * 86)
    print(f"{'Overall Accuracy':32s} | {baseline_eval['accuracy_pct']:22.2f}% | {resnet_eval['accuracy_pct']:22.2f}%")
    print(f"{'Balanced Accuracy':32s} | {baseline_eval['balanced_accuracy_pct']:22.2f}% | {resnet_eval['balanced_accuracy_pct']:22.2f}%")
    print(f"{'Macro-F1 Score':32s} | {baseline_eval['macro_f1']:24.4f} | {resnet_eval['macro_f1']:24.4f}")
    print(f"{'Weighted-F1 Score':32s} | {baseline_eval['weighted_f1']:24.4f} | {resnet_eval['weighted_f1']:24.4f}")
    print("-" * 86)

    print("\nPER-CLASS METRICS COMPARISON (Precision / Recall / F1):")
    print("-" * 86)
    for cls in CLASSES:
        b_m = baseline_eval["per_class_metrics"][cls]
        r_m = resnet_eval["per_class_metrics"][cls]
        d_name = CLASS_DISPLAY[cls]
        print(f"Class: {d_name:10s} (N={b_m['support']})")
        print(f"  Baseline:  Prec={b_m['precision']:.4f}, Rec={b_m['recall']:.4f}, F1={b_m['f1_score']:.4f}")
        print(f"  ResNet-18: Prec={r_m['precision']:.4f}, Rec={r_m['recall']:.4f}, F1={r_m['f1_score']:.4f}")

    print("\n" + "=" * 80)
    print("FIELD PHOTOGRAPH PREDICTIONS (Real Photographic Generalization):")
    print("=" * 80)
    for b_item, r_item in zip(baseline_field, resnet_field):
        print(f"\nSpecimen: {b_item['sample_name']}")
        print(f"  Ground Truth: {b_item['ground_truth_status']}")
        print(f"  Baseline ConvNet:  Predicted={b_item['predicted_mineral']:10s} ({b_item['confidence_pct']:.2f}%) | Probs: {b_item['probabilities']}")
        print(f"  Improved ResNet18: Predicted={r_item['predicted_mineral']:10s} ({r_item['confidence_pct']:.2f}%) | Probs: {r_item['probabilities']}")

    report = {
        "task": "Phase 3 Fair Model Evaluation & Comparison",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "test_set_split": "data/test (10 Coal, 10 Manganese, 10 Iron Ore, 10 Bauxite)",
        "baseline_model": {
            "name": "MineralConvNet",
            "checkpoint": baseline_weights,
            "metrics": baseline_eval,
            "field_photograph_results": baseline_field
        },
        "improved_model": {
            "name": "MineralResNet18",
            "checkpoint": resnet_weights,
            "metrics": resnet_eval,
            "field_photograph_results": resnet_field
        }
    }

    report_path = os.path.join(BASE_DIR, "models", "model_comparison_report.json")
    with open(report_path, "w") as fp:
        json.dump(report, fp, indent=2)
    print(f"\nFull comparison report saved -> {report_path}")

if __name__ == "__main__":
    run_comparison()

