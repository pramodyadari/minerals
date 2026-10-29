"""
AI Mineral Intelligence — Specimen Vision Service (Section 6)
Loads the 4-class PyTorch MineralConvNet model and classifies uploaded mineral specimens.
Classes: Coal, Manganese, Iron Ore, Bauxite.
Includes a scale-robust, feature-space manifold distance verification mechanism to:
  1. Correctly accept supported mineral specimens (including dark/shiny exposure variations).
  2. Reject genuinely unfamiliar out-of-distribution rocks (e.g. Quartz, Granite, Limestone) as 'Unknown / Unsupported Mineral'.
"""

import os
import io
import json
import numpy as np
from PIL import Image
import torch
import torch.nn.functional as F

import sys
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)
AI_DIR = os.path.join(BASE_DIR, "ai")
if AI_DIR not in sys.path:
    sys.path.insert(0, AI_DIR)

from ai.train import MineralConvNet, CLASSES, MODEL_PATH

CLASS_DISPLAY = {
    "coal": "Coal",
    "manganese": "Manganese",
    "iron_ore": "Iron Ore",
    "bauxite": "Bauxite"
}

_model = None
_ood_config = None

def get_model():
    global _model
    if _model is None:
        full_path = os.path.join(BASE_DIR, MODEL_PATH)
        if not os.path.exists(full_path):
            return None
        device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
        state_dict = torch.load(full_path, map_location=device)
        # Polymorphic architecture support: ResNet18 vs MineralConvNet
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
    """
    Computes class-conditional scale-robust manifold distance:
    d = d_perp + radial_penalty
    Invariant to camera exposure / specular scaling within calibrated physical bounds.
    """
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

def classify_specimen_image(image_bytes: bytes) -> dict:
    model = get_model()
    if model is None:
        return {
            "status": "MODEL_UNAVAILABLE",
            "message": "AI mineral specimen classification model not yet trained.",
            "classes": [CLASS_DISPLAY[c] for c in CLASSES],
            "disclaimer": "Specimen model required. Run ai/train.py to initialize."
        }

    if not image_bytes or len(image_bytes) == 0:
        return {
            "status": "INVALID_IMAGE",
            "message": "Uploaded file is empty."
        }

    try:
        Image.MAX_IMAGE_PIXELS = 25000000
        raw_img = Image.open(io.BytesIO(image_bytes))
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
            # Pass through convolutional feature extractor
            f256 = torch.flatten(model.features(tensor), 1)
            # Penultimate layer (128-dimensional dense manifold embedding)
            h128 = model.classifier[2](model.classifier[1](f256))
            # Final linear classification layer
            outputs = model.classifier[4](h128)
        probs = F.softmax(outputs, dim=1).squeeze(0).cpu().numpy()
        h_vec = h128.squeeze(0).cpu().numpy()

    best_idx = int(probs.argmax())
    best_class = CLASSES[best_idx]
    confidence = float(probs[best_idx])

    probs_dict = {
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

    # Evaluate Out-of-Distribution (OOD) rejection via scale-robust manifold distance
    ood_cfg = get_ood_config()
    is_supported = True
    rejection_reason = None
    min_dist = 0.0
    rejection_threshold = 5.0
    closest_candidate = best_class

    if ood_cfg and "centroids" in ood_cfg:
        centroids = ood_cfg["centroids"]
        rejection_threshold = float(ood_cfg.get("rejection_threshold_tau", 5.0))
        scale_bounds = ood_cfg.get("scale_bounds", {})
        penalty_weight = float(ood_cfg.get("scale_penalty_weight", 25.0))
        dists = {}
        distance_breakdown = {}
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
                closest_display = CLASS_DISPLAY.get(closest_candidate, closest_candidate.title())
                rejection_reason = (
                    f"Visual feature divergence: scale-robust manifold distance ({min_dist:.2f}) "
                    f"exceeds calibrated acceptance threshold ({rejection_threshold:.2f})."
                )
    else:
        distance_breakdown = {}

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
        probs_dict=probs_dict,
        model_acc=model_acc,
        evaluation_metadata=evaluation_metadata,
        image_guidance=image_guidance,
        model_diagnostic_info=model_diagnostic_info,
        distance_breakdown=distance_breakdown,
        rejection_reason=rejection_reason,
        softmax_diagnostic_note=softmax_diagnostic_note,
    )


def build_specimen_classification_decision(
    best_class: str,
    confidence: float,
    min_dist: float,
    rejection_threshold: float,
    closest_candidate: str,
    probs_dict: dict,
    model_acc: float = None,
    evaluation_metadata: dict = None,
    image_guidance: dict = None,
    model_diagnostic_info: dict = None,
    distance_breakdown: dict = None,
    rejection_reason: str = None,
    provisional_indication: str = None,
    softmax_diagnostic_note: str = None,
) -> dict:
    """
    Authoritative classification decision rule for rock/mineral specimens.
    Shared across backend/app/vision_service.py, ai/predict.py, and diagnostics.
    """
    is_supported = (min_dist <= rejection_threshold)
    nearest_cand_display = CLASS_DISPLAY.get(closest_candidate, closest_candidate.title())
    raw_favored_display = CLASS_DISPLAY.get(best_class, best_class.title())

    if softmax_diagnostic_note is None:
        softmax_diagnostic_note = (
            "Closed-world neural network probabilities always sum to 100% across the 4 trained classes by definition, "
            "even for non-mineral inputs. Raw logits and softmax values are diagnostic references only, not geological occurrence probabilities."
        )

    if provisional_indication is None and not is_supported and (best_class == "manganese" or closest_candidate == "manganese"):
        provisional_indication = "Possible Manganese — Not Confirmed"

    if rejection_reason is None and not is_supported:
        rejection_reason = (
            f"Visual feature divergence: scale-robust manifold distance ({min_dist:.2f}) "
            f"exceeds calibrated acceptance threshold ({rejection_threshold:.2f})."
        )

    rejection_explanation = {
        "summary": f"Specimen feature distance ({min_dist:.2f}) exceeds acceptance threshold ({rejection_threshold:.2f}).",
        "provisional_indication": provisional_indication,
        "nearest_candidate_class": closest_candidate,
        "nearest_candidate_mineral": nearest_cand_display,
        "cnn_favored_class": best_class,
        "cnn_favored_mineral": raw_favored_display,
        "cnn_evaluation_summary": (
            f"The CNN favors {raw_favored_display} among the 4 supported classes (raw closed-world score {round(confidence * 100, 2)}%), "
            f"but the specimen failed the current acceptance criteria because its feature distance ({min_dist:.2f}) "
            f"exceeds the rejection threshold ({rejection_threshold:.2f}). Accepted confidence is withheld (0.0%)."
        ),
        "softmax_warning": (
            f"Never interpret a {round(confidence * 100, 2)}% closed-world softmax score as a {round(confidence * 100, 2)}% real-world probability. "
            f"The CNN normalizes scores to 100% across Coal, Manganese, Iron Ore, and Bauxite only. "
            f"An out-of-distribution sample can receive a high relative score despite not matching the reference mineralogy."
        ),
        "nearest_candidate_note": (
            f"'{nearest_cand_display}' is the nearest geometric neighbor in the 128-dimensional embedding space, "
            f"NOT a confirmed or provisional identification. The specimen visual texture and spectral properties "
            f"diverge significantly from all 4 supported classes."
        ),
        "candidate_unconfirmed_note": (
            f"Visual appearance alone (dark, rough, or metallic surface) cannot verify mineral composition. "
            f"'{nearest_cand_display}' is an unconfirmed candidate requiring laboratory geochemical assay."
        ),
        "withheld_confidence_note": (
            "Accepted confidence is withheld (0.0%) because the specimen failed the out-of-distribution distance criteria. "
            "This indicates visual divergence from the reference training manifold and does NOT prove the specimen contains no target mineral."
        ),
        "expert_submission_guidance": "Submit specimen field notes and assay verification via the expert review queue to support dataset expansion.",
        "decision": "OUT_OF_DISTRIBUTION_REJECTED",
        "feature_distance": round(min_dist, 2),
        "rejection_threshold": round(rejection_threshold, 2)
    }

    raw_prediction = {
        "raw_predicted_class": best_class,
        "raw_predicted_mineral": raw_favored_display,
        "raw_confidence_percentage": round(confidence * 100, 2),
        "raw_probabilities_pct": probs_dict,
        "diagnostic_note": softmax_diagnostic_note
    }

    raw_softmax_scores = {
        "scores": probs_dict,
        "warning": softmax_diagnostic_note,
        "normalized_classes": [CLASS_DISPLAY[c] for c in CLASSES]
    }

    if not is_supported:
        nearest_candidate_obj = {
            "class": closest_candidate,
            "mineral": nearest_cand_display,
            "label": f"{nearest_cand_display} — unconfirmed candidate",
            "feature_distance": round(min_dist, 2),
            "rejection_threshold": round(rejection_threshold, 2),
            "status": "UNCONFIRMED_CANDIDATE",
            "note": "Unconfirmed candidate — not an identification"
        }
        return {
            "status": "SUCCESS",
            "accepted": False,
            "identified_mineral": None,
            "identification_status": "OUT_OF_DISTRIBUTION",
            "display_label": "Unknown / Unsupported Mineral",
            "accepted_confidence": None,
            "accepted_confidence_display": "Withheld",
            "nearest_candidate": nearest_candidate_obj,
            "raw_softmax_scores": raw_softmax_scores,
            "is_supported_mineral": False,
            "is_provisional": False,
            "verification_status": "REJECTED_OOD",
            "predicted_mineral": "Unknown / Unsupported Mineral",
            "predicted_class": "unknown",
            "predicted_label": "Unknown / Unsupported Mineral",
            "provisional_indication": provisional_indication,
            "rejection_reason": rejection_reason,
            "rejection_explanation": rejection_explanation,
            "feature_distance": round(min_dist, 2),
            "rejection_threshold": round(rejection_threshold, 2),
            "closest_candidate": nearest_cand_display,
            "closest_candidate_mineral": nearest_cand_display,
            "closest_candidate_class": closest_candidate,
            "confidence_percentage": 0.0,
            "confidence_score": 0.0,
            "calibrated_confidence_pct": 0.0,
            "calibrated_confidence_score": 0.0,
            "class_probabilities_pct": probs_dict,
            "raw_model_prediction": raw_prediction,
            "softmax_diagnostic_note": softmax_diagnostic_note,
            "model_validation_accuracy_pct": model_acc,
            "evaluation_metadata": evaluation_metadata or {},
            "image_guidance": image_guidance or {},
            "model_diagnostic_info": model_diagnostic_info or {},
            "distance_breakdown": distance_breakdown or {},
            "supported_minerals": [CLASS_DISPLAY[c] for c in CLASSES],
            "notice": "Specimen rejected as Unknown / Unsupported Mineral. Visual features diverge from the supported 4-class mineralogical domain. Nearest candidate is a geometric reference only, NOT an identification.",
            "disclaimer": "Specimen visual features diverged from supported classes. Classified as Unknown / Unsupported Mineral."
        }

    # Calibrated confidence for accepted in-distribution samples
    distance_factor = max(0.0, 1.0 - (min_dist / (rejection_threshold + 1e-5)) ** 2)
    calibrated_conf = float(confidence * (0.6 + 0.4 * distance_factor))

    best_mineral_display = raw_favored_display
    nearest_candidate_obj = {
        "class": best_class,
        "mineral": best_mineral_display,
        "label": best_mineral_display,
        "feature_distance": round(min_dist, 2),
        "rejection_threshold": round(rejection_threshold, 2),
        "status": "ACCEPTED_IDENTIFICATION",
        "note": "Calibrated in-domain provisional identification"
    }

    return {
        "status": "SUCCESS",
        "accepted": True,
        "identified_mineral": best_mineral_display,
        "identification_status": "ACCEPTED",
        "display_label": best_mineral_display,
        "accepted_confidence": round(calibrated_conf * 100, 2),
        "accepted_confidence_display": f"{round(calibrated_conf * 100, 2)}%",
        "nearest_candidate": nearest_candidate_obj,
        "raw_softmax_scores": raw_softmax_scores,
        "is_supported_mineral": True,
        "is_provisional": True,
        "verification_status": "VERIFIED_IN_DOMAIN_PROVISIONAL",
        "predicted_class": best_class,
        "predicted_mineral": best_mineral_display,
        "predicted_label": best_mineral_display,
        "confidence_percentage": round(confidence * 100, 2),
        "confidence_score": round(confidence, 4),
        "calibrated_confidence_pct": round(calibrated_conf * 100, 2),
        "calibrated_confidence_score": round(calibrated_conf, 4),
        "calibrated_confidence_percentage": round(calibrated_conf * 100, 2),
        "feature_distance": round(min_dist, 2),
        "rejection_threshold": round(rejection_threshold, 2),
        "closest_candidate": best_mineral_display,
        "closest_candidate_mineral": best_mineral_display,
        "closest_candidate_class": best_class,
        "class_probabilities_pct": probs_dict,
        "raw_model_prediction": raw_prediction,
        "softmax_diagnostic_note": softmax_diagnostic_note,
        "model_validation_accuracy_pct": model_acc,
        "evaluation_metadata": evaluation_metadata or {},
        "image_guidance": image_guidance or {},
        "model_diagnostic_info": model_diagnostic_info or {},
        "distance_breakdown": distance_breakdown or {},
        "supported_minerals": [CLASS_DISPLAY[c] for c in CLASSES],
        "notice": "Provisional visual identification of rock/ore sample specimen. Does NOT prove underground mineral occurrence.",
        "disclaimer": "Provisional visual identification of rock/ore sample specimen. Does not prove underground mineral occurrence."
    }
