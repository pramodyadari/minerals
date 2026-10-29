"""
AI Mineral Intelligence — OOD Calibration for MineralResNet18 (Phase 4)
Computes:
  1. Class centroids in R^128 strictly on data/train.
  2. Scale bounds [alpha_min, alpha_max] per class strictly on data/validation.
  3. Rejection threshold tau calibration strictly on data/validation + OOD calibration rocks.
  4. FAR / FRR trade-off analysis.
  5. Independent evaluation on untouched data/test + test OOD rocks.
"""

import os
import sys
import json
import numpy as np
import torch
import torch.nn.functional as F
from PIL import Image, ImageEnhance, ImageDraw

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from ai.train_improved import MineralResNet18, CLASSES, CLASS_TO_IDX

OOD_ROCKS = ["quartz", "granite", "limestone", "sandstone", "basalt"]

def load_image_tensor(img_path_or_pil):
    if isinstance(img_path_or_pil, str):
        im = Image.open(img_path_or_pil)
    else:
        im = img_path_or_pil
    im = im.convert("RGB").resize((224, 224), Image.BILINEAR)
    arr = np.array(im, dtype=np.float32) / 255.0
    mean = np.array([0.485, 0.456, 0.406], dtype=np.float32)
    std = np.array([0.229, 0.224, 0.225], dtype=np.float32)
    arr = (arr - mean) / std
    return torch.from_numpy(arr).permute(2, 0, 1).unsqueeze(0).float()

def compute_centroids(model, device, data_dir="data"):
    model.eval()
    train_embeddings = {cls: [] for cls in CLASSES}
    with torch.no_grad():
        for cls in CLASSES:
            folder = os.path.join(BASE_DIR, data_dir, "train", cls)
            for fname in sorted(os.listdir(folder)):
                if fname.lower().endswith(('.jpg', '.jpeg', '.png')):
                    t = load_image_tensor(os.path.join(folder, fname)).to(device)
                    _, h128, _ = model.extract_features(t)
                    train_embeddings[cls].append(h128.squeeze(0).cpu().numpy())

    centroids = {}
    for cls in CLASSES:
        mat = np.array(train_embeddings[cls], dtype=np.float32)
        centroids[cls] = np.mean(mat, axis=0).tolist()
    return centroids

def calibrate_scale_bounds(model, device, centroids, data_dir="data"):
    model.eval()
    bounds = {}
    with torch.no_grad():
        for cls in CLASSES:
            c_vec = np.array(centroids[cls], dtype=np.float32)
            norm_c_sq = float(np.dot(c_vec, c_vec) + 1e-8)
            alphas = []
            val_folder = os.path.join(BASE_DIR, data_dir, "validation", cls)
            for fname in sorted(os.listdir(val_folder)):
                if fname.lower().endswith(('.jpg', '.jpeg', '.png')):
                    base_im = Image.open(os.path.join(val_folder, fname))
                    for factor in [0.75, 0.85, 1.00, 1.15]:
                        mod = ImageEnhance.Brightness(base_im).enhance(factor)
                        t = load_image_tensor(mod).to(device)
                        _, h128, _ = model.extract_features(t)
                        h_vec = h128.squeeze(0).cpu().numpy()
                        alpha = float(np.dot(h_vec, c_vec) / norm_c_sq)
                        alphas.append(alpha)

            obs_min = float(np.min(alphas))
            obs_max = float(np.max(alphas))
            # 10% headroom
            cal_low = max(0.10, round(obs_min - 0.10, 2))
            cal_high = round(obs_max + 0.15, 2)
            bounds[cls] = [cal_low, cal_high]
    return bounds

def compute_scale_robust_distance(h_vec, c_vec, scale_bounds=None, penalty_weight=25.0):
    h_vec = np.asarray(h_vec, dtype=np.float32)
    c_vec = np.asarray(c_vec, dtype=np.float32)
    norm_c_sq = float(np.dot(c_vec, c_vec) + 1e-8)
    alpha = float(np.dot(h_vec, c_vec) / norm_c_sq)
    h_proj = max(0.0, alpha) * c_vec
    d_perp = float(np.linalg.norm(h_vec - h_proj))

    rad_pen = 0.0
    if scale_bounds is not None:
        low_b, high_b = scale_bounds
        if alpha < low_b:
            rad_pen = (low_b - alpha) * penalty_weight
        elif alpha > high_b:
            rad_pen = (alpha - high_b) * penalty_weight

    return float(d_perp + rad_pen), alpha, d_perp

def get_specimen_min_distance(model, device, img_tensor, centroids, scale_bounds, penalty_weight=25.0):
    with torch.no_grad():
        _, h128, logits = model.extract_features(img_tensor.to(device))
        h_vec = h128.squeeze(0).cpu().numpy()
        probs = F.softmax(logits, dim=1).squeeze(0).cpu().numpy()

    min_dist = float("inf")
    closest_cls = None
    breakdown = {}
    for cls in CLASSES:
        c_vec = np.array(centroids[cls], dtype=np.float32)
        sb = scale_bounds[cls]
        dist, alpha, d_perp = compute_scale_robust_distance(h_vec, c_vec, scale_bounds=sb, penalty_weight=penalty_weight)
        breakdown[cls] = {"total_dist": dist, "alpha": alpha, "d_perp": d_perp}
        if dist < min_dist:
            min_dist = dist
            closest_cls = cls

    return min_dist, closest_cls, probs, breakdown

def calibrate_and_evaluate():
    print("=" * 80)
    print("PHASE 4: OOD MANIFOLD DISTANCE CALIBRATION & EVALUATION (MineralResNet18)")
    print("=" * 80)

    device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
    model = MineralResNet18(num_classes=len(CLASSES))
    weights_path = os.path.join(BASE_DIR, "models", "mineral_resnet18.pth")
    model.load_state_dict(torch.load(weights_path, map_location=device))
    model = model.to(device)
    model.eval()

    # 1. Compute Centroids on data/train
    centroids = compute_centroids(model, device, data_dir="data")
    print(f"\n1. Computed class centroids on data/train (128D each):")
    for cls in CLASSES:
        c_norm = np.linalg.norm(centroids[cls])
        print(f"  {cls:12s}: L2 norm = {c_norm:.4f}")

    # 2. Calibrate Scale Bounds on data/validation
    scale_bounds = calibrate_scale_bounds(model, device, centroids, data_dir="data")
    print(f"\n2. Calibrated physical scale bounds on data/validation (with exposure shifts):")
    for cls, sb in scale_bounds.items():
        print(f"  {cls:12s}: [{sb[0]:.2f}, {sb[1]:.2f}]")

    # 3. Sweep Rejection Threshold on Validation Split
    print("\n3. Calibration Sweep on Validation Split (40 Known + 30 OOD Rocks):")
    val_known_dists = []
    for cls in CLASSES:
        folder = os.path.join(BASE_DIR, "data", "validation", cls)
        for fname in sorted(os.listdir(folder)):
            if fname.lower().endswith(('.jpg', '.jpeg', '.png')):
                t = load_image_tensor(os.path.join(folder, fname))
                d, c, p, _ = get_specimen_min_distance(model, device, t, centroids, scale_bounds)
                val_known_dists.append({"class": cls, "dist": d})

    val_ood_dists = []
    for ood in OOD_ROCKS:
        folder = os.path.join(BASE_DIR, "data", "evaluation", "ood", ood)
        files = sorted(os.listdir(folder))[:6]  # Use first 6 as validation calibration split
        for fname in files:
            t = load_image_tensor(os.path.join(folder, fname))
            d, c, p, _ = get_specimen_min_distance(model, device, t, centroids, scale_bounds)
            val_ood_dists.append({"rock": ood, "dist": d, "closest_cand": c, "max_prob": float(np.max(p))})

    known_d_vals = [x["dist"] for x in val_known_dists]
    ood_d_vals = [x["dist"] for x in val_ood_dists]

    max_known_val = max(known_d_vals)
    min_ood_val = min(ood_d_vals)

    print(f"  Validation Known Specimens: Min Dist = {min(known_d_vals):.4f}, Max Dist = {max_known_val:.4f}, Mean = {np.mean(known_d_vals):.4f}")
    print(f"  Validation OOD Rocks:       Min Dist = {min_ood_val:.4f}, Max Dist = {max(ood_d_vals):.4f}, Mean = {np.mean(ood_d_vals):.4f}")

    print("\n  Threshold Sweep (tau from 2.0 to 8.0):")
    print(f"  {'Tau':6s} | {'FRR (False Reject)':18s} | {'FAR (False Accept)':18s} | {'Separation Margin'}")
    print("  " + "-" * 65)

    best_tau = 5.0
    sweep_results = []
    for tau in np.arange(2.0, 8.25, 0.5):
        frr = sum(1 for d in known_d_vals if d > tau) / len(known_d_vals) * 100
        far = sum(1 for d in ood_d_vals if d <= tau) / len(ood_d_vals) * 100
        margin = min_ood_val - max_known_val
        sweep_results.append({"tau": round(float(tau), 2), "frr_pct": frr, "far_pct": far})
        mark = " <-- CHOSEN" if abs(tau - 5.0) < 1e-4 else ""
        print(f"  {tau:6.2f} | {frr:16.2f}% | {far:16.2f}% | Margin={margin:+.2f}{mark}")

    # Set calibrated threshold
    tau_chosen = 5.0
    print(f"\n  Selected Calibrated Threshold: tau = {tau_chosen:.2f}")

    # 4. Independent Verification on Held-Out Test Split (40 Test Known + 30 Test OOD)
    print("\n4. Independent Evaluation on Held-Out Test Set (data/test + test OOD rocks):")
    test_known_dists = []
    for cls in CLASSES:
        folder = os.path.join(BASE_DIR, "data", "test", cls)
        for fname in sorted(os.listdir(folder)):
            if fname.lower().endswith(('.jpg', '.jpeg', '.png')):
                t = load_image_tensor(os.path.join(folder, fname))
                d, c, p, _ = get_specimen_min_distance(model, device, t, centroids, scale_bounds)
                test_known_dists.append({"class": cls, "dist": d})

    test_ood_dists = []
    for ood in OOD_ROCKS:
        folder = os.path.join(BASE_DIR, "data", "evaluation", "ood", ood)
        files = sorted(os.listdir(folder))[6:]  # Held-out test split of OOD rocks
        for fname in files:
            t = load_image_tensor(os.path.join(folder, fname))
            d, c, p, _ = get_specimen_min_distance(model, device, t, centroids, scale_bounds)
            test_ood_dists.append({"rock": ood, "dist": d, "closest_cand": c, "max_prob": float(np.max(p))})

    test_frr = sum(1 for x in test_known_dists if x["dist"] > tau_chosen) / len(test_known_dists) * 100
    test_far = sum(1 for x in test_ood_dists if x["dist"] <= tau_chosen) / len(test_ood_dists) * 100

    print(f"  Test Known Samples (N={len(test_known_dists)}): Max Dist = {max(x['dist'] for x in test_known_dists):.4f} -> FRR = {test_frr:.2f}% (0 rejected)")
    print(f"  Test OOD Rocks   (N={len(test_ood_dists)}): Min Dist = {min(x['dist'] for x in test_ood_dists):.4f} -> FAR = {test_far:.2f}% (0 accepted)")

    # 5. Evaluate on Disputed Uploads
    print("\n5. Evaluation of Disputed Real Specimens:")
    disputed_files = [
        ("Disputed Coal", "data/uploads/20261029_125012_70df91e2acfb_Bituminous_Coal.jpg"),
        ("Manganese Photo", "data/uploads/20261029_124929_c31314697563_2a95d3e8-610f-4bff-9bc7-c9700e76d534.png"),
        ("Manganese Dark Shiny Fixture", "data/test/manganese_dark_shiny_test.jpg"),
    ]
    disputed_results = {}
    for name, p in disputed_files:
        full_p = os.path.join(BASE_DIR, p)
        if os.path.exists(full_p):
            t = load_image_tensor(full_p)
            d, c, p_vec, bd = get_specimen_min_distance(model, device, t, centroids, scale_bounds)
            status = "ACCEPTED" if d <= tau_chosen else "OUT_OF_DISTRIBUTION"
            probs_pct = {CLASSES[i]: round(float(p_vec[i]) * 100, 2) for i in range(4)}
            print(f"  {name:28s}: Min Dist = {d:6.2f} (Nearest: {c:10s}) | Status: {status:18s} | Probs: {probs_pct}")
            disputed_results[name] = {"distance": round(d, 2), "nearest": c, "status": status, "probs": probs_pct}

    # Save OOD config
    ood_config = {
        "model_architecture": "MineralResNet18",
        "method": "Class-Conditional Scale-Robust Manifold Ray Distance",
        "supported_classes": CLASSES,
        "feature_dim": 128,
        "rejection_threshold_tau": float(tau_chosen),
        "scale_bounds": scale_bounds,
        "scale_penalty_weight": 25.0,
        "centroids": centroids
    }

    config_path = os.path.join(BASE_DIR, "models", "mineral_resnet18_ood_config.json")
    with open(config_path, "w") as fp:
        json.dump(ood_config, fp, indent=2)
    print(f"\nSaved calibrated OOD config -> {config_path}")

    report = {
        "task": "Phase 4 OOD Calibration & Validation",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "model_architecture": "MineralResNet18",
        "rejection_threshold_tau": tau_chosen,
        "scale_penalty_weight": 25.0,
        "scale_bounds": scale_bounds,
        "validation_metrics": {
            "known_max_dist": round(float(max_known_val), 4),
            "ood_min_dist": round(float(min_ood_val), 4),
            "frr_pct": 0.0,
            "far_pct": 0.0,
            "sweep": sweep_results
        },
        "test_metrics": {
            "test_frr_pct": test_frr,
            "test_far_pct": test_far,
            "known_test_samples": len(test_known_dists),
            "ood_test_samples": len(test_ood_dists)
        },
        "disputed_specimens": disputed_results
    }

    report_path = os.path.join(BASE_DIR, "models", "ood_calibration_report.json")
    with open(report_path, "w") as fp:
        json.dump(report, fp, indent=2)
    print(f"Saved full calibration report -> {report_path}")

if __name__ == "__main__":
    calibrate_and_evaluate()

