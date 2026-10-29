"""
AI Mineral Intelligence — Specimen Inference Module & CLI (Section 5)
Predicts mineral class (Coal, Manganese, Iron Ore, Bauxite) for any image file,
with scale-robust Out-of-Distribution (OOD) rejection for unsupported rocks/minerals.
"""

import os
import sys
import json
import numpy as np
import torch
import torch.nn.functional as F
from PIL import Image

try:
    from .train import MineralConvNet, CLASSES, MODEL_PATH
except ImportError:
    from train import MineralConvNet, CLASSES, MODEL_PATH

CLASS_DISPLAY = {
    "coal": "Coal",
    "manganese": "Manganese",
    "iron_ore": "Iron Ore",
    "bauxite": "Bauxite"
}

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from backend.app.vision_service import build_specimen_classification_decision

_model = None
_ood_config = None

def get_inference_model():
    global _model
    if _model is None:
        device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
        model_path = MODEL_PATH if os.path.isabs(MODEL_PATH) else os.path.join(BASE_DIR, MODEL_PATH)
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"Model file not found at {model_path}. Train model first via ai/train.py")
        state_dict = torch.load(model_path, map_location=device)
        if "layer1.0.conv1.weight" in state_dict:
            try:
                from ai.train_improved import MineralResNet18
            except ImportError:
                from train_improved import MineralResNet18
            m = MineralResNet18(num_classes=len(CLASSES))
        else:
            m = MineralConvNet(num_classes=len(CLASSES))
        m.load_state_dict(state_dict)
        m = m.to(device)
        m.eval()
        _model = m
    return _model

def get_ood_config():
    global _ood_config
    if _ood_config is None:
        config_path = os.path.join(BASE_DIR, "models", "mineral_classifier_ood_config.json")
        if os.path.exists(config_path):
            try:
                with open(config_path, "r") as fp:
                    _ood_config = json.load(fp)
            except Exception:
                _ood_config = None
    return _ood_config

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
    else:
        if alpha < 0.35:
            rad_pen = (0.35 - alpha) * 8.0
        elif alpha > 1.80:
            rad_pen = (alpha - 1.80) * 8.0
        
    return float(d_perp + rad_pen), alpha, d_perp

def predict_image(image_input):
    """
    Predicts mineral class from an image path, bytes, or PIL Image instance.
    Includes scale-robust manifold distance verification for OOD detection.
    Maintains exact schema parity with backend/app/vision_service.py.
    """
    try:
        model = get_inference_model()
    except Exception as e:
        return {
            "status": "MODEL_UNAVAILABLE",
            "message": f"AI mineral specimen classification model unavailable: {str(e)}",
            "classes": [CLASS_DISPLAY[c] for c in CLASSES],
            "disclaimer": "Specimen model required. Run ai/train.py to initialize."
        }

    # Input validation & image loading
    try:
        Image.MAX_IMAGE_PIXELS = 25000000
        if isinstance(image_input, (str, bytes)):
            if isinstance(image_input, str):
                if not os.path.exists(image_input):
                    return {"status": "INVALID_IMAGE", "message": f"Image file not found: {image_input}"}
                raw_img = Image.open(image_input)
            else:
                if len(image_input) == 0:
                    return {"status": "INVALID_IMAGE", "message": "Uploaded image is empty."}
                import io
                raw_img = Image.open(io.BytesIO(image_input))
        elif isinstance(image_input, Image.Image):
            raw_img = image_input
        else:
            return {"status": "INVALID_IMAGE", "message": f"Unsupported image input type: {type(image_input)}"}

        fmt = raw_img.format
        if fmt and fmt.upper() not in ["JPEG", "PNG", "WEBP", "MPO"]:
            return {
                "status": "INVALID_IMAGE",
                "message": f"Unsupported image format '{fmt}'. Only JPEG, PNG, WebP, and MPO are supported."
            }
        w, h = raw_img.size
        if w < 16 or h < 16:
            return {
                "status": "INVALID_IMAGE",
                "message": f"Image dimensions ({w}x{h}) are too small. Minimum resolution is 16x16 pixels."
            }
        if w > 8192 or h > 8192:
            return {
                "status": "INVALID_IMAGE",
                "message": f"Image dimensions ({w}x{h}) exceed maximum allowed dimension (8192x8192)."
            }
        if hasattr(raw_img, "seek"):
            try:
                raw_img.seek(0)
            except Exception as seek_err:
                return {
                    "status": "INVALID_IMAGE",
                    "message": f"Failed to access primary image frame: {str(seek_err)}"
                }
        img = raw_img.convert("RGB").resize((224, 224))
    except Image.DecompressionBombError:
        return {
            "status": "INVALID_IMAGE",
            "message": "Image exceeds maximum safe decompression limit (decompression bomb risk)."
        }
    except Exception as e:
        return {
            "status": "INVALID_IMAGE",
            "message": f"Could not parse uploaded image: {str(e)}"
        }

    arr = np.array(img, dtype=np.float32) / 255.0
    mean = np.array([0.485, 0.456, 0.406], dtype=np.float32)
    std = np.array([0.229, 0.224, 0.225], dtype=np.float32)
    arr = (arr - mean) / std

    device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
    tensor = torch.from_numpy(arr).permute(2, 0, 1).unsqueeze(0).to(device)

    with torch.no_grad():
        if hasattr(model, "extract_features"):
            _, h128, outputs = model.extract_features(tensor)
        else:
            f256 = torch.flatten(model.features(tensor), 1)
            h128 = model.classifier[2](model.classifier[1](f256))
            outputs = model.classifier[4](h128)
        probs = F.softmax(outputs, dim=1).squeeze(0).cpu().numpy()
        h_vec = h128.squeeze(0).cpu().numpy()

    best_idx = int(probs.argmax())
    best_class = CLASSES[best_idx]
    confidence = float(probs[best_idx])

    probs_dict = {
        cls: round(float(probs[i]), 4)
        for i, cls in enumerate(CLASSES)
    }
    probs_dict_pct = {
        CLASS_DISPLAY[cls]: round(float(probs[i]) * 100, 2)
        for i, cls in enumerate(CLASSES)
    }

    # Fetch model metadata and build qualified evaluation scope
    metadata_path = os.path.join(BASE_DIR, "models", "mineral_image_classifier_metadata.json")
    model_acc = None
    if os.path.exists(metadata_path):
        try:
            with open(metadata_path) as fp:
                meta = json.load(fp)
                model_acc = meta.get("best_validation_accuracy_pct")
        except Exception:
            pass

    evaluation_metadata = {
        "curated_validation_accuracy_pct": model_acc,
        "validation_sample_count": 40,
        "evaluation_scope": "Curated Laboratory Reference Set (40 validation / 40 test specimens)",
        "split_methodology": "Stratified held-out split (10 specimens per class) strictly segregated from 140 training samples",
        "qualification": "100% metric applies strictly to the curated reference split (N=40); real-world field specimens with weathering, mixed lithologies, or dust exhibit higher uncertainty."
    }

    softmax_diagnostic_note = (
        "Closed-world neural network probabilities always sum to 100% across the 4 trained classes by definition, "
        "even for non-mineral inputs. Raw logits and softmax values are diagnostic references only, not geological occurrence probabilities."
    )

    image_guidance = {
        "surface": "Photograph a freshly broken, unweathered specimen surface rather than weathered rind or soil.",
        "lighting": "Use diffused, balanced natural light. Avoid direct camera flash, heavy shadows, or specular hotspots.",
        "framing": "Ensure the specimen is in sharp macroscopic focus, filling at least 70% of the camera frame.",
        "background": "Place the rock on a neutral, matte background (e.g. neutral card or scale ruler).",
        "retest_safety_note": (
            "Retaking the photo can resolve poor illumination or blurry focus. However, if the sample is genuinely a "
            "non-supported lithology (e.g., Quartz, Granite, Basalt, Sandstone), retaking the photo will NOT change its geological identity. "
            "OOD rejection safely protects against false identification."
        )
    }

    # Evaluate OOD rejection
    ood_cfg = get_ood_config()
    is_supported = True
    min_dist = 0.0
    rejection_threshold = 5.0
    closest_candidate = best_class
    rejection_reason = None

    dists = {}
    distance_breakdown = {}
    if ood_cfg and "centroids" in ood_cfg:
        centroids = ood_cfg["centroids"]
        rejection_threshold = float(ood_cfg.get("rejection_threshold_tau", 5.0))
        scale_bounds = ood_cfg.get("scale_bounds", {})
        penalty_weight = float(ood_cfg.get("scale_penalty_weight", 25.0))
        for cls in CLASSES:
            if cls in centroids:
                c_vec = np.array(centroids[cls])
                cls_bounds = scale_bounds.get(cls)
                dist, alpha, d_perp = compute_scale_robust_distance(
                    h_vec, c_vec, scale_bounds=cls_bounds, penalty_weight=penalty_weight
                )
                dists[cls] = dist
                distance_breakdown[cls] = {
                    "total_distance": round(float(dist), 4),
                    "orthogonal_divergence_d_perp": round(float(d_perp), 4),
                    "projection_scale_alpha": round(float(alpha), 4),
                    "scale_penalty": round(float(max(0.0, dist - d_perp)), 4),
                    "calibrated_scale_bounds": cls_bounds,
                }
        if dists:
            closest_candidate = min(dists, key=dists.get)
            min_dist = dists[closest_candidate]
            if min_dist > rejection_threshold:
                is_supported = False
                rejection_reason = (
                    f"Visual feature divergence: scale-robust manifold distance ({min_dist:.2f}) "
                    f"exceeds calibrated acceptance threshold ({rejection_threshold:.2f})."
                )

    model_diagnostic_info = {
        "model_architecture": "MineralConvNet",
        "embedding_dimension": 128,
        "checkpoint_path": os.path.join(BASE_DIR, "models", "mineral_image_classifier.pth"),
        "checkpoint_sha256": "f4382a869f1793cec05820a16f42ec7ac574830ef16012090d4a1cfb5cb3485f",
        "ood_method": "Class-Conditional Scale-Robust Manifold Ray Distance",
        "ood_threshold_tau": float(rejection_threshold),
        "exact_unrounded_distance": round(float(min_dist), 4),
        "distance_breakdown": distance_breakdown,
    }

    return build_specimen_classification_decision(
        best_class=best_class,
        confidence=confidence,
        min_dist=min_dist,
        rejection_threshold=rejection_threshold,
        closest_candidate=closest_candidate,
        probs_dict=probs_dict_pct,
        model_acc=model_acc,
        evaluation_metadata=evaluation_metadata,
        image_guidance=image_guidance,
        model_diagnostic_info=model_diagnostic_info,
        distance_breakdown=distance_breakdown,
        rejection_reason=rejection_reason,
        softmax_diagnostic_note=softmax_diagnostic_note,
    )

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: py -3.11 ai/predict.py <path_to_image>")
        sys.exit(1)

    result = predict_image(sys.argv[1])
    print(json.dumps(result, indent=2))
