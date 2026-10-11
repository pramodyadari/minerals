"""
AI Mineral Intelligence — Specimen Inference Module & CLI (Section 5)
Predicts mineral class (Coal, Manganese, Iron Ore, Bauxite) for any image file.
"""

import os
import sys
import json
import numpy as np
import torch
import torch.nn.functional as F
from PIL import Image

# Support both package and script execution
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

_model = None

def get_inference_model():
    global _model
    if _model is None:
        device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
        m = MineralConvNet(num_classes=len(CLASSES))
        if not os.path.exists(MODEL_PATH):
            raise FileNotFoundError(f"Model file not found at {MODEL_PATH}. Train model first via ai/train.py")
        m.load_state_dict(torch.load(MODEL_PATH, map_location=device))
        m = m.to(device)
        m.eval()
        _model = m
    return _model

def predict_image(image_input):
    """
    Predicts mineral class from an image path or PIL Image instance.
    Returns:
        dict: {
            "predicted_class": "manganese",
            "predicted_label": "Manganese",
            "confidence_score": 0.9452,
            "confidence_percentage": 94.52,
            "all_probabilities": { "coal": 0.01, ... },
            "disclaimer": "Visual classification of rock/ore specimen sample. Does not prove underground mineral occurrence."
        }
    """
    if isinstance(image_input, str):
        img = Image.open(image_input)
    else:
        img = image_input

    img = img.convert("RGB").resize((224, 224))
    arr = np.array(img, dtype=np.float32) / 255.0
    mean = np.array([0.485, 0.456, 0.406], dtype=np.float32)
    std = np.array([0.229, 0.224, 0.225], dtype=np.float32)
    arr = (arr - mean) / std

    device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
    tensor = torch.from_numpy(arr).permute(2, 0, 1).unsqueeze(0).to(device)

    model = get_inference_model()
    with torch.no_grad():
        outputs = model(tensor)
        probs = F.softmax(outputs, dim=1).squeeze(0).cpu().numpy()

    best_idx = int(probs.argmax())
    best_class = CLASSES[best_idx]
    confidence = float(probs[best_idx])

    probs_dict = {
        cls: round(float(probs[i]), 4)
        for i, cls in enumerate(CLASSES)
    }

    return {
        "predicted_class": best_class,
        "predicted_label": CLASS_DISPLAY.get(best_class, best_class.title()),
        "confidence_score": round(confidence, 4),
        "confidence_percentage": round(confidence * 100, 2),
        "all_probabilities": probs_dict,
        "disclaimer": "Visual classification of rock/ore specimen sample. Does not prove underground mineral occurrence."
    }

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: py -3.11 ai/predict.py <path_to_image>")
        sys.exit(1)

    result = predict_image(sys.argv[1])
    print(json.dumps(result, indent=2))
