#!/usr/bin/env python3
"""
Specimen Segmentation & Crop Comparison Utility
Compares CNN predictions and OOD manifold distances between the original uncropped
specimen image and the isolated/cropped specimen candidate.

Reports:
1. Image dimensions and crop coordinates.
2. CNN class probabilities (Coal, Manganese, Iron Ore, Bauxite).
3. Closest candidate class and feature distance.
4. OOD status (ACCEPTED vs OUT_OF_DISTRIBUTION, threshold tau=5.0).
5. Accepted confidence (withheld if rejected).
6. Segmentation quality and method utilized.
"""

import os
import sys
import json
import argparse
import numpy as np
import torch
import torch.nn.functional as F
from PIL import Image

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from backend.app.vision_service import (
    get_model,
    get_ood_config,
    compute_scale_robust_distance,
    CLASSES,
    CLASS_DISPLAY,
)
from ai.specimen_preprocessing import isolate_specimen, prepare_production_tensor


def run_specimen_inference(model, ood_cfg, pil_img: Image.Image) -> dict:
    """
    Runs forward inference and OOD distance evaluation using exact production pipeline.
    """
    tensor_np = prepare_production_tensor(pil_img)
    device = next(model.parameters()).device
    tensor = torch.from_numpy(tensor_np).unsqueeze(0).to(device)

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
    raw_class = CLASSES[best_idx]
    raw_confidence_pct = round(float(probs[best_idx]) * 100, 2)

    probs_dict = {
        CLASS_DISPLAY[c]: round(float(probs[i]) * 100, 2)
        for i, c in enumerate(CLASSES)
    }
    logits_dict = {
        CLASS_DISPLAY[c]: round(float(logits[i].item()), 4)
        for i, c in enumerate(CLASSES)
    }

    # Evaluate manifold distances
    tau = float(ood_cfg.get("rejection_threshold_tau", 5.0))
    scale_bounds = ood_cfg.get("scale_bounds", {})
    penalty_weight = float(ood_cfg.get("scale_penalty_weight", 25.0))
    centroids = ood_cfg.get("centroids", {})

    class_distances = {}
    class_breakdowns = {}
    for c in CLASSES:
        if c in centroids:
            c_vec = np.array(centroids[c], dtype=np.float32)
            bnds = scale_bounds.get(c)
            dist, alpha, d_perp = compute_scale_robust_distance(
                h_vec, c_vec, scale_bounds=bnds, penalty_weight=penalty_weight
            )
            class_distances[c] = dist
            class_breakdowns[CLASS_DISPLAY[c]] = {
                "distance": round(float(dist), 4),
                "alpha": round(float(alpha), 4),
                "d_perp": round(float(d_perp), 4),
                "penalty": round(float(max(0.0, dist - d_perp)), 4),
            }

    closest_cand = min(class_distances, key=class_distances.get) if class_distances else raw_class
    min_dist = class_distances.get(closest_cand, 999.0)
    is_supported = (min_dist <= tau)

    return {
        "raw_favored_class": CLASS_DISPLAY[raw_class],
        "raw_confidence_pct": raw_confidence_pct,
        "probabilities": probs_dict,
        "logits": logits_dict,
        "closest_candidate": CLASS_DISPLAY[closest_cand],
        "manifold_distance": round(float(min_dist), 4),
        "ood_threshold": tau,
        "ood_status": "ACCEPTED" if is_supported else "OUT_OF_DISTRIBUTION",
        "final_decision": CLASS_DISPLAY[closest_cand] if is_supported else "Unknown / Unsupported Mineral",
        "accepted_confidence": f"{raw_confidence_pct:.2f}%" if is_supported else "Withheld",
        "class_breakdowns": class_breakdowns,
        "embedding_norm": round(float(np.linalg.norm(h_vec)), 4)
    }


def compare_image_and_crop(image_path: str) -> dict:
    """
    Executes comparison between original image and segmented crop.
    """
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"Image not found at: {image_path}")

    model = get_model()
    if model is None:
        raise RuntimeError("Production specimen classifier checkpoint not found.")
    ood_cfg = get_ood_config()
    if ood_cfg is None:
        raise RuntimeError("OOD configuration not found.")

    # 1. Run segmentation
    seg_res = isolate_specimen(image_path)
    if seg_res["status"] != "SUCCESS" or seg_res["original_image"] is None:
        return {
            "status": "ERROR",
            "message": seg_res.get("message", "Segmentation failed"),
            "image_path": image_path
        }

    orig_img = seg_res["original_image"]
    crop_img = seg_res["candidate_crop"]

    # 2. Evaluate original image
    orig_eval = run_specimen_inference(model, ood_cfg, orig_img)

    # 3. Evaluate candidate crop
    crop_eval = run_specimen_inference(model, ood_cfg, crop_img)

    # 4. Formulate comparative report
    report = {
        "status": "SUCCESS",
        "image_path": image_path,
        "segmentation": {
            "is_segmented": seg_res["is_segmented"],
            "quality": seg_res["segmentation_quality"],
            "method_used": seg_res["method_used"],
            "crop_box": seg_res["crop_box"],
            "original_dimensions": seg_res["original_dimensions"],
            "crop_dimensions": seg_res["crop_dimensions"],
            "foreground_area_ratio": seg_res["foreground_area_ratio"],
            "notes": seg_res["notes"],
            "border_diagnostics": seg_res.get("border_diagnostics", {})
        },
        "original": orig_eval,
        "candidate_crop": crop_eval,
        "comparison_analysis": {
            "raw_favored_class_shift": f"{orig_eval['raw_favored_class']} -> {crop_eval['raw_favored_class']}",
            "bauxite_prob_change": f"{orig_eval['probabilities']['Bauxite']}% -> {crop_eval['probabilities']['Bauxite']}%",
            "coal_prob_change": f"{orig_eval['probabilities']['Coal']}% -> {crop_eval['probabilities']['Coal']}%",
            "manganese_prob_change": f"{orig_eval['probabilities']['Manganese']}% -> {crop_eval['probabilities']['Manganese']}%",
            "manifold_distance_change": f"{orig_eval['manifold_distance']} -> {crop_eval['manifold_distance']}",
            "ood_retained": (crop_eval["ood_status"] == "OUT_OF_DISTRIBUTION"),
            "summary": (
                f"Segmentation removed background card. "
                f"Manifold distance changed from {orig_eval['manifold_distance']} to {crop_eval['manifold_distance']} "
                f"(threshold {orig_eval['ood_threshold']}). "
                f"Status: {crop_eval['ood_status']}."
            )
        }
    }

    return report


def main():
    parser = argparse.ArgumentParser(description="Compare original vs segmented specimen image.")
    parser.add_argument("image_path", help="Path to specimen image file")
    parser.add_argument("--json", action="store_true", help="Output machine-readable JSON")
    args = parser.parse_args()

    try:
        report = compare_image_and_crop(args.image_path)
    except Exception as e:
        if args.json:
            print(json.dumps({"status": "ERROR", "message": str(e)}))
        else:
            print(f"Error: {e}")
        sys.exit(1)

    if args.json:
        print(json.dumps(report, indent=2))
        return

    # Formatted terminal display
    seg = report["segmentation"]
    orig = report["original"]
    crop = report["candidate_crop"]

    print("=" * 80)
    print("SPECIMEN SEGMENTATION & INFERENCE COMPARISON REPORT")
    print("=" * 80)
    print(f"Image File:          {report['image_path']}")
    print(f"Segmentation Status: {'SUCCESS' if seg['is_segmented'] else 'UNCERTAIN / UNSEGMENTED'}")
    print(f"Quality Grade:       {seg['quality']}")
    print(f"Method Used:         {seg['method_used']}")
    print(f"Original Dimensions: {seg['original_dimensions'][0]}x{seg['original_dimensions'][1]}")
    print(f"Crop Box:            {seg['crop_box']} (Area ratio: {seg['foreground_area_ratio']:.1%})")
    print(f"Crop Dimensions:     {seg['crop_dimensions'][0]}x{seg['crop_dimensions'][1]}")
    if seg["notes"]:
        print(f"Notes:               {'; '.join(seg['notes'])}")

    print("-" * 80)
    print(f"{'METRIC':<30} | {'ORIGINAL BASELINE':<22} | {'CANDIDATE CROP':<22}")
    print("-" * 80)
    print(f"{'Raw Favored Candidate':<30} | {orig['raw_favored_class']:<22} | {crop['raw_favored_class']:<22}")
    print(f"{'Raw Softmax Confidence':<30} | {orig['raw_confidence_pct']:<20}% | {crop['raw_confidence_pct']:<20}%")
    print(f"{'Closest Manifold Class':<30} | {orig['closest_candidate']:<22} | {crop['closest_candidate']:<22}")
    print(f"{'Manifold Distance (tau=5.0)':<30} | {orig['manifold_distance']:<22} | {crop['manifold_distance']:<22}")
    print(f"{'Identification Status':<30} | {orig['ood_status']:<22} | {crop['ood_status']:<22}")
    print(f"{'Final Authoritative Decision':<30} | {orig['final_decision']:<22} | {crop['final_decision']:<22}")
    print(f"{'Accepted Confidence':<30} | {orig['accepted_confidence']:<22} | {crop['accepted_confidence']:<22}")

    print("-" * 80)
    print("CLASS PROBABILITY DISTRIBUTION:")
    for c in ["Coal", "Manganese", "Iron Ore", "Bauxite"]:
        p_orig = orig['probabilities'][c]
        p_crop = crop['probabilities'][c]
        print(f"  {c:<28} | {p_orig:>6.2f}%               | {p_crop:>6.2f}%")

    print("-" * 80)
    print("EMBEDDING MANIFOLD DISTANCES:")
    for c in ["Coal", "Manganese", "Iron Ore", "Bauxite"]:
        d_orig = orig['class_breakdowns'][c]['distance']
        d_crop = crop['class_breakdowns'][c]['distance']
        print(f"  {c:<28} | {d_orig:>8.4f}               | {d_crop:>8.4f}")

    print("=" * 80)
    print(f"SUMMARY: {report['comparison_analysis']['summary']}")
    print("=" * 80)


if __name__ == "__main__":
    main()

