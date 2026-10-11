"""
AI Mineral Intelligence — Specimen Vision Service (Section 6)
Loads the 4-class PyTorch MineralConvNet model and classifies uploaded mineral specimens.
Classes: Coal, Manganese, Iron Ore, Bauxite.
"""

import os
import io
import json
from PIL import Image
import numpy as np
import torch
import torch.nn.functional as F

# Import MineralConvNet from ai.train
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

def get_model():
    global _model
    if _model is None:
        full_path = os.path.join(BASE_DIR, MODEL_PATH)
        if not os.path.exists(full_path):
            return None
        device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
        m = MineralConvNet(num_classes=len(CLASSES))
        m.load_state_dict(torch.load(full_path, map_location=device))
        m = m.to(device)
        m.eval()
        _model = m
    return _model

def classify_specimen_image(image_bytes: bytes) -> dict:
    model = get_model()
    if model is None:
        return {
            "status": "MODEL_UNAVAILABLE",
            "message": "AI mineral specimen classification model not yet trained.",
            "classes": [CLASS_DISPLAY[c] for c in CLASSES],
            "disclaimer": "Specimen model required. Run ai/train.py to initialize."
        }

    try:
        img = Image.open(io.BytesIO(image_bytes)).convert("RGB").resize((224, 224))
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
        outputs = model(tensor)
        probs = F.softmax(outputs, dim=1).squeeze(0).cpu().numpy()

    best_idx = int(probs.argmax())
    best_class = CLASSES[best_idx]
    confidence = float(probs[best_idx])

    probs_dict = {
        CLASS_DISPLAY[cls]: round(float(probs[i]) * 100, 2)
        for i, cls in enumerate(CLASSES)
    }

    # Fetch model metadata if available
    metadata_path = os.path.join(BASE_DIR, "models", "mineral_image_classifier_metadata.json")
    model_acc = None
    if os.path.exists(metadata_path):
        try:
            with open(metadata_path) as fp:
                meta = json.load(fp)
                model_acc = meta.get("best_validation_accuracy_pct")
        except Exception:
            pass

    return {
        "status": "SUCCESS",
        "predicted_class": best_class,
        "predicted_mineral": CLASS_DISPLAY.get(best_class, best_class.title()),
        "confidence_percentage": round(confidence * 100, 2),
        "confidence_score": round(confidence, 4),
        "class_probabilities_pct": probs_dict,
        "model_validation_accuracy_pct": model_acc,
        "supported_minerals": [CLASS_DISPLAY[c] for c in CLASSES],
        "notice": "Visual classification of rock/ore sample specimen. Does NOT prove underground mineral occurrence."
    }
