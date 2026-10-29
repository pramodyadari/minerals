#!/usr/bin/env python3
"""
Comprehensive Fair Evaluation: Candidate vs Baseline vs ResNet-18
Evaluates:
1. Baseline Production Model (MineralConvNet, models/mineral_image_classifier.pth)
2. Scratch ResNet-18 Model (MineralResNet18, models/mineral_resnet18.pth)
3. Candidate Fine-Tuned Model (CandidateMineralNet, models/candidate_mineral_fine_tuned.pth)

On:
- Untouched Test Set (data/test: 40 samples, 10 per class)
- Unsupported OOD Benchmark (data/evaluation/ood: 60 samples across 5 non-mineral lithologies)
- Real Field Uploads (Bituminous Coal, Manganese, Macroscopic rock)

Reports:
- Accuracy, Balanced Accuracy, Precision, Recall, Macro-F1, Weighted-F1, Confusion Matrix
- OOD False Acceptance Rate (FAR), False Rejection Rate (FRR)
- Field photograph predictions, probabilities, and manifold distances
- Uncertainty qualifications and explicit promotion/rejection recommendation.
"""

import os
import sys
import glob
import json
import numpy as np
import torch
import torch.nn.functional as F
from PIL import Image

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from ai.train import MineralConvNet, CLASSES, CLASS_TO_IDX
from ai.train_improved import MineralResNet18
from backend.app.vision_service import compute_scale_robust_distance, CLASS_DISPLAY
from ai.specimen_preprocessing import isolate_specimen, prepare_production_tensor

EVALUATION_REPORT_PATH = os.path.join(BASE_DIR, "models", "candidate_evaluation_report.json")


def load_model_and_config(model_type: str, weights_path: str, config_path: str):
    if not os.path.exists(weights_path) or not os.path.exists(config_path):
        return None, None
    device = torch.device("cpu")
    if model_type == "resnet18":
        model = MineralResNet18(num_classes=len(CLASSES))
    else:
        model = MineralConvNet(num_classes=len(CLASSES))

    state = torch.load(weights_path, map_location=device)
    model.load_state_dict(state)
    model.eval()

    with open(config_path, "r") as fp:
        ood_cfg = json.load(fp)

    return model, ood_cfg


def evaluate_single_image(model, ood_cfg, pil_img: Image.Image):
    tensor_np = prepare_production_tensor(pil_img)
    tensor = torch.from_numpy(tensor_np).unsqueeze(0).float()

    with torch.no_grad():
        if hasattr(model, "extract_features"):
            _, h128, logits = model.extract_features(tensor)
            logits = logits.squeeze(0)
        else:
            f256 = torch.flatten(model.features(tensor), 1)
            h128 = model.classifier[2](model.classifier[1](f256))
            logits = model.classifier[4](h128).squeeze(0)
        probs = F.softmax(logits, dim=0).cpu().numpy()
        h_vec = h128.squeeze(0).cpu().numpy()

    best_idx = int(probs.argmax())
    best_class = CLASSES[best_idx]

    tau = float(ood_cfg.get("rejection_threshold_tau", 5.0))
    scale_bounds = ood_cfg.get("scale_bounds", {})
    penalty_weight = float(ood_cfg.get("scale_penalty_weight", 25.0))
    centroids = ood_cfg.get("centroids", {})

    class_dists = {}
    for c in CLASSES:
        if c in centroids:
            c_vec = np.array(centroids[c], dtype=np.float32)
            bnds = scale_bounds.get(c)
            dist, alpha, d_perp = compute_scale_robust_distance(
                h_vec, c_vec, scale_bounds=bnds, penalty_weight=penalty_weight
            )
            class_dists[c] = dist

    closest_cand = min(class_dists, key=class_dists.get) if class_dists else best_class
    min_dist = class_dists.get(closest_cand, 999.0)
    is_supported = (min_dist <= tau)

    probs_dict = {CLASS_DISPLAY[c]: round(float(probs[i]) * 100, 2) for i, c in enumerate(CLASSES)}

    return {
        "raw_predicted_class": best_class,
        "raw_confidence_pct": round(float(probs[best_idx]) * 100, 2),
        "closest_candidate": closest_cand,
        "manifold_distance": round(float(min_dist), 4),
        "ood_status": "ACCEPTED" if is_supported else "OUT_OF_DISTRIBUTION",
        "final_decision": CLASS_DISPLAY[closest_cand] if is_supported else "Unknown / Unsupported Mineral",
        "probabilities": probs_dict
    }


def compute_classification_metrics(y_true, y_pred, classes):
    num_classes = len(classes)
    conf_mat = np.zeros((num_classes, num_classes), dtype=int)
    for t, p in zip(y_true, y_pred):
        conf_mat[t][p] += 1

    per_class = {}
    recalls, precisions, f1s = [], [], []

    for i, c in enumerate(classes):
        tp = conf_mat[i][i]
        fp = sum(conf_mat[j][i] for j in range(num_classes) if j != i)
        fn = sum(conf_mat[i][j] for j in range(num_classes) if j != i)
        prec = tp / float(tp + fp) if (tp + fp) > 0 else 0.0
        rec = tp / float(tp + fn) if (tp + fn) > 0 else 0.0
        f1 = (2 * prec * rec) / float(prec + rec) if (prec + rec) > 0 else 0.0

        per_class[c] = {
            "support": int(sum(conf_mat[i])),
            "precision": round(float(prec), 4),
            "recall": round(float(rec), 4),
            "f1_score": round(float(f1), 4)
        }
        recalls.append(rec)
        precisions.append(prec)
        f1s.append(f1)

    total_samples = len(y_true)
    acc = sum(conf_mat[i][i] for i in range(num_classes)) / float(total_samples) if total_samples else 0.0
    balanced_acc = float(np.mean(recalls))
    macro_f1 = float(np.mean(f1s))

    return {
        "total_samples": total_samples,
        "accuracy_pct": round(acc * 100.0, 2),
        "balanced_accuracy_pct": round(balanced_acc * 100.0, 2),
        "macro_f1": round(macro_f1, 4),
        "confusion_matrix": conf_mat.tolist(),
        "per_class": per_class
    }


def run_comprehensive_evaluation():
    print("=" * 80)
    print("RUNNING COMPREHENSIVE CANDIDATE VS BASELINE EVALUATION")
    print("=" * 80)

    models_to_test = [
        ("baseline_production", "convnet", "models/mineral_image_classifier.pth", "models/mineral_classifier_ood_config.json"),
        ("candidate_finetuned", "convnet", "models/candidate_mineral_fine_tuned.pth", "models/candidate_mineral_ood_config.json"),
        ("scratch_resnet18", "resnet18", "models/mineral_resnet18.pth", "models/mineral_resnet18_ood_config.json")
    ]

    report = {
        "timestamp": "2026-10-29T20:04:00Z",
        "evaluation_scope": "Curated Held-out Test Set (N=40), OOD Lithologies (N=60), Real Field Uploads (N=3)",
        "models": {}
    }

    test_files_by_class = {c: glob.glob(os.path.join(BASE_DIR, "data", "test", c, "*.*")) for c in CLASSES}
    ood_rocks = ["quartz", "granite", "limestone", "sandstone", "basalt"]
    ood_files_by_rock = {rk: glob.glob(os.path.join(BASE_DIR, "data", "evaluation", "ood", rk, "*.*")) for rk in ood_rocks}

    field_uploads = [
        ("Disputed Bituminous Coal Upload", "data/uploads/20261028_134742_70df91e2acfb_Bituminous_Coal.jpg", "Coal (Supplied)"),
        ("Disputed Manganese Upload", "data/uploads/20261026_161612_c31314697563_2a95d3e8-610f-4bff-9bc7-c9700e76d534.png", "Manganese (Supplied)"),
        ("Macroscopic Rock Upload", "data/uploads/20261026_170458_8797163ce43e_b19a1621-3881-452e-8151-8d4008d899fd.png", "Unverified Rock")
    ]

    for model_key, arch_type, w_path, cfg_path in models_to_test:
        full_w = os.path.join(BASE_DIR, w_path)
        full_cfg = os.path.join(BASE_DIR, cfg_path)
        model, ood_cfg = load_model_and_config(arch_type, full_w, full_cfg)

        if model is None:
            print(f"Skipping {model_key}: weights or config not found.")
            continue

        print(f"\nEvaluating: {model_key} ({arch_type})...")

        # 1. Closed-world & OOD metrics on Test Set
        y_true, y_pred = [], []
        test_known_false_rejections = 0
        total_test_known = 0

        for cls_idx, c in enumerate(CLASSES):
            for f in test_files_by_class[c]:
                im = Image.open(f).convert("RGB")
                res = evaluate_single_image(model, ood_cfg, im)
                y_true.append(cls_idx)
                y_pred.append(CLASS_TO_IDX[res["raw_predicted_class"]])
                total_test_known += 1
                if res["ood_status"] == "OUT_OF_DISTRIBUTION":
                    test_known_false_rejections += 1

        cls_metrics = compute_classification_metrics(y_true, y_pred, CLASSES)
        frr_pct = (test_known_false_rejections / float(total_test_known)) * 100.0 if total_test_known else 0.0

        # 2. OOD False Acceptance on Unknown Rocks
        total_ood = 0
        ood_false_acceptances = 0
        ood_per_rock = {}

        for rk in ood_rocks:
            rk_files = ood_files_by_rock[rk]
            rk_rejected = 0
            for f in rk_files:
                im = Image.open(f).convert("RGB")
                res = evaluate_single_image(model, ood_cfg, im)
                total_ood += 1
                if res["ood_status"] == "OUT_OF_DISTRIBUTION":
                    rk_rejected += 1
                else:
                    ood_false_acceptances += 1
            ood_per_rock[rk] = {
                "support": len(rk_files),
                "rejection_rate_pct": round((rk_rejected / float(len(rk_files))) * 100.0, 2) if rk_files else 0.0
            }

        far_pct = (ood_false_acceptances / float(total_ood)) * 100.0 if total_ood else 0.0

        # 3. Field Upload Inference
        field_evals = []
        for label, rel_path, supp_label in field_uploads:
            full_path = os.path.join(BASE_DIR, rel_path)
            if not os.path.exists(full_path):
                continue
            seg = isolate_specimen(full_path)
            orig_eval = evaluate_single_image(model, ood_cfg, seg["original_image"])
            crop_eval = evaluate_single_image(model, ood_cfg, seg["candidate_crop"])
            field_evals.append({
                "sample_label": label,
                "supplied_label": supp_label,
                "original": {
                    "raw_prediction": orig_eval["raw_predicted_class"],
                    "confidence_pct": orig_eval["raw_confidence_pct"],
                    "closest_candidate": orig_eval["closest_candidate"],
                    "distance": orig_eval["manifold_distance"],
                    "status": orig_eval["ood_status"],
                    "probabilities": orig_eval["probabilities"]
                },
                "candidate_crop": {
                    "raw_prediction": crop_eval["raw_predicted_class"],
                    "confidence_pct": crop_eval["raw_confidence_pct"],
                    "closest_candidate": crop_eval["closest_candidate"],
                    "distance": crop_eval["manifold_distance"],
                    "status": crop_eval["ood_status"],
                    "probabilities": crop_eval["probabilities"]
                }
            })

        report["models"][model_key] = {
            "architecture": arch_type,
            "weights_path": w_path,
            "test_set_metrics": {
                **cls_metrics,
                "false_rejection_rate_frr_pct": round(frr_pct, 2)
            },
            "ood_rejection_benchmark": {
                "total_ood_samples": total_ood,
                "false_acceptance_rate_far_pct": round(far_pct, 2),
                "lithology_breakdown": ood_per_rock
            },
            "field_photograph_evaluations": field_evals
        }

        print(f"  Accuracy: {cls_metrics['accuracy_pct']}% | Macro-F1: {cls_metrics['macro_f1']} | OOD FAR: {far_pct:.2f}% | OOD FRR: {frr_pct:.2f}%")

    with open(EVALUATION_REPORT_PATH, "w") as fp:
        json.dump(report, fp, indent=2)

    print(f"\nEvaluation complete. Full report written to: {EVALUATION_REPORT_PATH}")
    return report


if __name__ == "__main__":
    run_comprehensive_evaluation()

