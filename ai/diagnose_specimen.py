#!/usr/bin/env python3
"""
Diagnostic utility for mineral specimen classification and OOD manifold distance auditing.
Reproduces exact inference pipeline and reports:
- File hash (SHA-256), dimensions, color mode
- Preprocessing operations, tensor shapes, normalization parameters
- Model checkpoint path, weights hash, architecture
- Raw logits, softmax distribution, penultimate 128D embedding statistics
- Class-conditional manifold distances (alpha, d_perp, penalty, total)
- Rejection threshold and final decision
"""

import os
import sys
import json
import hashlib
import argparse
import numpy as np
import torch
import torch.nn.functional as F
from PIL import Image

# Ensure project root is in sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from backend.app.vision_service import (
    get_model,
    get_ood_config,
    compute_scale_robust_distance,
    build_specimen_classification_decision,
    CLASSES,
    CLASS_DISPLAY,
)


def diagnose_image(image_path: str) -> dict:
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"Specimen image not found at: {image_path}")

    # 1. Image metadata and hash
    with open(image_path, "rb") as fp:
        raw_bytes = fp.read()

    file_size_bytes = len(raw_bytes)
    sha256_hash = hashlib.sha256(raw_bytes).hexdigest()

    with Image.open(image_path) as pil_img:
        orig_width, orig_height = pil_img.size
        orig_mode = pil_img.mode
        orig_format = pil_img.format
        if hasattr(pil_img, "seek"):
            try:
                pil_img.seek(0)
            except Exception:
                pass
        img_rgb = pil_img.convert("RGB")
        resized_img = img_rgb.resize((224, 224))

    # 2. Preprocessing operations
    mean = np.array([0.485, 0.456, 0.406], dtype=np.float32)
    std = np.array([0.229, 0.224, 0.225], dtype=np.float32)
    arr_norm = (np.array(resized_img, dtype=np.float32) / 255.0 - mean) / std
    tensor = torch.from_numpy(arr_norm).permute(2, 0, 1).unsqueeze(0).float()

    # 3. Model checkpoint and weights inspection
    model_path = os.path.join(BASE_DIR, "models", "mineral_image_classifier.pth")
    with open(model_path, "rb") as fp:
        model_weights_sha256 = hashlib.sha256(fp.read()).hexdigest()

    model = get_model()
    ood_cfg = get_ood_config()

    # 4. Forward inference pass
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

    # 5. Embedding statistics
    emb_norm = float(np.linalg.norm(h_vec))
    emb_mean = float(np.mean(h_vec))
    emb_std = float(np.std(h_vec))
    emb_sparsity = float(np.mean(h_vec == 0.0))

    # 6. Manifold distance breakdown for each class
    tau = ood_cfg.get("rejection_threshold_tau", 5.0)
    pen_weight = ood_cfg.get("scale_penalty_weight", 25.0)
    centroids = ood_cfg.get("centroids", {})
    scale_bounds = ood_cfg.get("scale_bounds", {})

    class_distances = {}
    for cls in CLASSES:
        c_vec = np.array(centroids[cls], dtype=np.float32)
        sb = scale_bounds.get(cls, [0.1, 1.5])
        dist, alpha, d_perp = compute_scale_robust_distance(
            h_vec, c_vec, scale_bounds=sb, penalty_weight=pen_weight
        )
        
        # Calculate individual penalty
        pen = 0.0
        if alpha < sb[0]:
            pen = (sb[0] - alpha) * pen_weight
        elif alpha > sb[1]:
            pen = (alpha - sb[1]) * pen_weight

        class_distances[cls] = {
            "display_name": CLASS_DISPLAY[cls],
            "total_distance": round(dist, 4),
            "orthogonal_divergence_d_perp": round(d_perp, 4),
            "projection_scale_alpha": round(alpha, 4),
            "scale_penalty": round(pen, 4),
            "calibrated_scale_bounds": sb,
            "raw_logit": round(float(logits[CLASSES.index(cls)]), 4),
            "raw_softmax_prob_pct": round(float(probs[CLASSES.index(cls)]) * 100, 2),
        }

    # Closest candidate based on manifold distance
    sorted_by_dist = sorted(class_distances.items(), key=lambda kv: kv[1]["total_distance"])
    closest_cls, closest_meta = sorted_by_dist[0]
    min_dist = closest_meta["total_distance"]

    best_idx = int(probs.argmax())
    best_class = CLASSES[best_idx]
    confidence = float(probs[best_idx])
    probs_dict_pct = {
        CLASS_DISPLAY[c]: round(float(probs[i]) * 100, 2)
        for i, c in enumerate(CLASSES)
    }

    # Authoritative shared decision function
    authoritative_decision = build_specimen_classification_decision(
        best_class=best_class,
        confidence=confidence,
        min_dist=min_dist,
        rejection_threshold=tau,
        closest_candidate=closest_cls,
        probs_dict=probs_dict_pct,
    )
    is_accepted = authoritative_decision["accepted"]
    decision = "VERIFIED_IN_DOMAIN_PROVISIONAL" if is_accepted else "UNKNOWN / UNSUPPORTED MINERAL"

    final_decision_obj = dict(authoritative_decision)
    final_decision_obj["decision"] = decision
    final_decision_obj["accepted_confidence_pct"] = authoritative_decision["accepted_confidence"] or 0.0
    final_decision_obj["confidence_withheld"] = not is_accepted

    report = {
        "file_metadata": {
            "path": image_path,
            "size_bytes": file_size_bytes,
            "sha256": sha256_hash,
            "original_dimensions": [orig_width, orig_height],
            "original_mode": orig_mode,
            "original_format": orig_format,
        },
        "preprocessing": {
            "color_conversion": "Converted to RGB",
            "resize_target": [224, 224],
            "interpolation": "Bilinear",
            "mean_subtraction": [0.485, 0.456, 0.406],
            "std_division": [0.229, 0.224, 0.225],
            "tensor_shape": list(tensor.shape),
            "tensor_dtype": str(tensor.dtype),
        },
        "model_metadata": {
            "architecture": "MineralConvNet (3 Conv blocks, MaxPool, AdaptiveAvgPool2d(4,4), Dense(2048->256->128->4))",
            "checkpoint_path": model_path,
            "checkpoint_sha256": model_weights_sha256,
            "ood_config_path": os.path.join(BASE_DIR, "models", "mineral_classifier_ood_config.json"),
            "rejection_threshold_tau": tau,
            "scale_penalty_weight": pen_weight,
        },
        "intermediate_embedding_128D": {
            "norm_l2": round(emb_norm, 4),
            "mean": round(emb_mean, 4),
            "std": round(emb_std, 4),
            "sparsity_pct": round(emb_sparsity * 100, 2),
        },
        "class_evaluations": class_distances,
        "closest_candidate": {
            **authoritative_decision["nearest_candidate"],
            "threshold": tau,
            "feature_distance": min_dist,
        },
        "final_decision": final_decision_obj,
    }

    return report


def main():
    parser = argparse.ArgumentParser(description="Audit and diagnose mineral specimen inference")
    parser.add_argument("image_path", help="Path to the specimen image file to diagnose")
    parser.add_argument("--json", action="store_true", help="Print report as raw JSON")
    parser.add_argument("--compare-crop", action="store_true", help="Also evaluate and display specimen segmentation & crop comparison")
    args = parser.parse_args()

    report = diagnose_image(args.image_path)

    crop_report = None
    if args.compare_crop:
        from ai.compare_specimen_crop import compare_image_and_crop
        crop_report = compare_image_and_crop(args.image_path)
        report["crop_comparison"] = crop_report

    if args.json:
        print(json.dumps(report, indent=2))
        return

    print("=" * 80)
    print("MINERAL SPECIMEN INFERENCE AUDIT & DIAGNOSTIC REPORT")
    print("=" * 80)
    meta = report["file_metadata"]
    print(f"File Path:         {meta['path']}")
    print(f"SHA-256 Hash:      {meta['sha256']}")
    print(f"Dimensions / Mode: {meta['original_dimensions'][0]}x{meta['original_dimensions'][1]} | Mode: {meta['original_mode']} | Size: {meta['size_bytes']} bytes")
    print(f"Model Checkpoint:  {report['model_metadata']['checkpoint_path']}")
    print(f"Embedding Norm:    {report['intermediate_embedding_128D']['norm_l2']} (L2)")
    print("-" * 80)
    print(f"{'Class':12s} | {'Logit':8s} | {'Softmax':9s} | {'Alpha':8s} | {'d_perp':8s} | {'Penalty':8s} | {'Total Dist':10s}")
    print("-" * 80)
    for cls, data in report["class_evaluations"].items():
        print(
            f"{data['display_name']:12s} | "
            f"{data['raw_logit']:8.4f} | "
            f"{data['raw_softmax_prob_pct']:7.2f}% | "
            f"{data['projection_scale_alpha']:8.4f} | "
            f"{data['orthogonal_divergence_d_perp']:8.4f} | "
            f"{data['scale_penalty']:8.4f} | "
            f"{data['total_distance']:10.4f}"
        )
    print("-" * 80)
    closest = report["closest_candidate"]
    dec = report["final_decision"]
    conf_str = "Withheld" if dec["confidence_withheld"] else f"{dec['accepted_confidence_pct']}%"
    candidate_label = f"{closest['mineral']} — unconfirmed candidate" if not dec["accepted"] else closest['mineral']
    print(f"Closest Candidate:     {candidate_label} (Feature Distance: {round(closest['feature_distance'], 2)} [exact: {closest['feature_distance']}] vs Threshold: {closest['threshold']})")
    print(f"Identification Status: {dec['identification_status']}")
    print(f"Main Identification:   {dec['display_label']}")
    print(f"Identification Result: {dec['decision']}")
    print(f"Accepted Confidence:   {conf_str}")
    print("=" * 80)

    if crop_report and crop_report.get("status") == "SUCCESS":
        c_seg = crop_report["segmentation"]
        c_orig = crop_report["original"]
        c_crop = crop_report["candidate_crop"]
        print("\n" + "=" * 80)
        print("SPECIMEN SEGMENTATION & CROP COMPARISON")
        print("=" * 80)
        print(f"Crop Status / Quality: {'SUCCESS' if c_seg['is_segmented'] else 'UNCERTAIN'} | Grade: {c_seg['quality']} | Method: {c_seg['method_used']}")
        print(f"Bounding Box:          {c_seg['crop_box']} (Area Ratio: {c_seg['foreground_area_ratio']:.1%})")
        print("-" * 80)
        print(f"{'METRIC':<30} | {'ORIGINAL BASELINE':<22} | {'CANDIDATE CROP':<22}")
        print("-" * 80)
        print(f"{'Closest Manifold Class':<30} | {c_orig['closest_candidate']:<22} | {c_crop['closest_candidate']:<22}")
        print(f"{'Manifold Distance (tau=5.0)':<30} | {c_orig['manifold_distance']:<22} | {c_crop['manifold_distance']:<22}")
        print(f"{'Identification Status':<30} | {c_orig['ood_status']:<22} | {c_crop['ood_status']:<22}")
        print(f"{'Accepted Confidence':<30} | {c_orig['accepted_confidence']:<22} | {c_crop['accepted_confidence']:<22}")
        print("-" * 80)
        for c in ["Coal", "Manganese", "Iron Ore", "Bauxite"]:
            print(f"  {c:<28} | {c_orig['probabilities'][c]:>6.2f}%               | {c_crop['probabilities'][c]:>6.2f}%")
        print("=" * 80)


if __name__ == "__main__":
    main()
