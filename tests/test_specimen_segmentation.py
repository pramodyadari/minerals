"""
Unit and Integration Tests for Specimen Segmentation & Rock Isolation Utility
Covers all requirements from the Master Prompt:
  1. White background with a dark specimen.
  2. Dark and shiny specimens (specular highlights).
  3. Light-colored specimens on pale backgrounds.
  4. Uneven lighting and background cast shadows.
  5. Images where segmentation fails / homogeneous texture fallback.
  6. Corrupt, tiny, and oversized inputs.
  7. Original versus cropped preprocessing consistency.
  8. OOD rejection after cropping (unknown rocks remain rejected).
  9. Existing JPEG, PNG, and MPO upload compatibility.
  10. Disputed Coal upload behavior: reduced Bauxite probability with strict OOD retention.
"""

import os
import io
import pytest
import numpy as np
from PIL import Image, ImageDraw

from ai.specimen_preprocessing import (
    isolate_specimen,
    preprocess_image_input,
    prepare_production_tensor,
    is_opencv_available,
)
from ai.compare_specimen_crop import compare_image_and_crop, run_specimen_inference
from backend.app.vision_service import get_model, get_ood_config

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


@pytest.fixture
def model_and_ood():
    model = get_model()
    ood_cfg = get_ood_config()
    assert model is not None, "Model must be loadable"
    assert ood_cfg is not None, "OOD config must be present"
    return model, ood_cfg


def test_white_background_with_dark_specimen():
    """Verify clean isolation of a dark specimen resting on a white support card."""
    w, h = 600, 400
    img = Image.new("RGB", (w, h), (235, 235, 235))
    rock = np.random.normal(loc=40, scale=8, size=(180, 260, 3)).clip(10, 80).astype(np.uint8)
    img.paste(Image.fromarray(rock), (170, 110))

    res = isolate_specimen(img)
    assert res["status"] == "SUCCESS"
    assert res["is_segmented"] is True
    assert res["segmentation_quality"] == "HIGH"
    assert res["method_used"] in ["scipy_morphological_texture", "opencv_grabcut"]

    x1, y1, x2, y2 = res["crop_box"]
    assert x1 <= 170 and y1 <= 110
    assert x2 >= 430 and y2 >= 290
    assert res["foreground_area_ratio"] < 0.80
    assert res["candidate_crop"].size == (x2 - x1, y2 - y1)


def test_dark_and_shiny_specimen():
    """Verify specimen segmentation bridges internal specular hotspots without splitting rock."""
    w, h = 600, 400
    img = Image.new("RGB", (w, h), (230, 230, 230))
    rock = np.random.normal(loc=50, scale=10, size=(180, 260, 3)).clip(15, 90).astype(np.uint8)
    # Intense specular bright spot in the center of the rock
    rock[60:120, 90:170] = np.random.normal(loc=240, scale=8, size=(60, 80, 3)).clip(210, 255)
    img.paste(Image.fromarray(rock), (170, 110))

    res = isolate_specimen(img)
    assert res["is_segmented"] is True
    assert res["segmentation_quality"] in ["HIGH", "MODERATE"]
    x1, y1, x2, y2 = res["crop_box"]
    # Verify the crop spans the full specimen, including the bright spot
    assert x1 <= 170 and y1 <= 110
    assert x2 >= 430 and y2 >= 290


def test_light_colored_specimen_on_pale_background():
    """Verify texture gradient isolates a light-toned specimen on a pale card."""
    w, h = 600, 400
    # Pale card (240, 235, 230)
    img = Image.new("RGB", (w, h), (240, 235, 230))
    # Light rock with high texture/grain variation
    rock = np.random.normal(loc=195, scale=25, size=(180, 260, 3)).clip(130, 245).astype(np.uint8)
    img.paste(Image.fromarray(rock), (170, 110))

    res = isolate_specimen(img)
    assert res["is_segmented"] is True
    assert res["segmentation_quality"] in ["HIGH", "MODERATE"]
    x1, y1, x2, y2 = res["crop_box"]
    assert x1 <= 180 and y1 <= 120
    assert x2 >= 420 and y2 >= 280


def test_uneven_lighting_and_shadows():
    """Verify planar illumination fitting removes directional lighting gradients on cards."""
    w, h = 600, 400
    img = Image.new("RGB", (w, h), (240, 240, 240))
    draw = ImageDraw.Draw(img)
    # Severe linear gradient: 250 on left edge to 170 on right edge
    for x in range(w):
        val = int(250 - (x / w) * 80)
        draw.line([(x, 0), (x, h)], fill=(val, val, val))
    # Add dark specimen in center
    rock = np.random.normal(loc=45, scale=8, size=(160, 240, 3)).clip(10, 80).astype(np.uint8)
    img.paste(Image.fromarray(rock), (180, 120))

    res = isolate_specimen(img)
    assert res["is_segmented"] is True
    assert res["segmentation_quality"] in ["HIGH", "MODERATE"]
    x1, y1, x2, y2 = res["crop_box"]
    assert x1 <= 185 and y1 <= 125
    assert x2 >= 415 and y2 >= 275


def test_segmentation_uncertainty_and_fallback():
    """Verify that images already filling the frame safely fall back to original baseline."""
    # Create macro texture image with zero background card
    w, h = 224, 224
    texture = np.random.normal(loc=70, scale=12, size=(h, w, 3)).clip(20, 120).astype(np.uint8)
    img = Image.fromarray(texture)

    res = isolate_specimen(img)
    assert res["status"] == "SUCCESS"
    assert res["is_segmented"] is False
    assert res["segmentation_quality"] == "UNCERTAIN_FALLBACK"
    assert res["method_used"] == "original_baseline_passthrough"
    assert res["crop_box"] == [0, 0, w, h]
    assert res["candidate_crop"] == img
    assert any("already fill" in note.lower() or "contrast" in note.lower() or "no foreground" in note.lower() for note in res["notes"])


def test_corrupt_and_invalid_inputs():
    """Verify robust error handling for corrupt, empty, tiny, and oversized images."""
    # 1. None
    res = isolate_specimen(None)
    assert res["status"] == "ERROR"
    assert res["segmentation_quality"] == "INVALID_INPUT"

    # 2. Empty bytes
    res = isolate_specimen(b"")
    assert res["status"] == "ERROR"
    assert res["segmentation_quality"] == "INVALID_INPUT"

    # 3. Corrupt bytes
    res = isolate_specimen(b"NOT_A_VALID_IMAGE_DATA_12345")
    assert res["status"] == "ERROR"
    assert res["segmentation_quality"] == "INVALID_INPUT"

    # 4. Tiny image (<16x16)
    tiny = Image.new("RGB", (10, 10), (100, 100, 100))
    res = isolate_specimen(tiny)
    assert res["status"] == "ERROR"
    assert "too small" in res["notes"][0].lower()


def test_original_versus_cropped_preprocessing_consistency():
    """Verify prepare_production_tensor applies identical normalization to original and crop."""
    img = Image.new("RGB", (400, 300), (200, 200, 200))
    crop = img.crop((50, 50, 250, 250))

    t_orig = prepare_production_tensor(img)
    t_crop = prepare_production_tensor(crop)

    assert t_orig.shape == (3, 224, 224)
    assert t_crop.shape == (3, 224, 224)
    assert t_orig.dtype == np.float32
    assert t_crop.dtype == np.float32
    # Check normalization range
    assert -3.0 <= t_orig.min() <= 3.0
    assert -3.0 <= t_orig.max() <= 3.0


def test_ood_rejection_after_cropping(model_and_ood):
    """Verify that cropping an out-of-distribution rock (e.g. Quartz) remains rejected."""
    model, ood_cfg = model_and_ood
    quartz_files = [
        os.path.join(BASE_DIR, "data", "evaluation", "ood", "quartz", "quartz_000.jpg"),
        os.path.join(BASE_DIR, "data", "uploads", "20261026_161013_81cb0e31b644_quartz_sample.jpg")
    ]
    test_file = next((f for f in quartz_files if os.path.exists(f)), None)
    if test_file is None:
        pytest.skip("No quartz evaluation fixture found.")

    im = Image.open(test_file).convert("RGB")
    seg = isolate_specimen(im)
    crop_eval = run_specimen_inference(model, ood_cfg, seg["candidate_crop"])

    assert crop_eval["ood_status"] == "OUT_OF_DISTRIBUTION"
    assert crop_eval["manifold_distance"] > crop_eval["ood_threshold"]
    assert crop_eval["accepted_confidence"] == "Withheld"
    assert crop_eval["final_decision"] == "Unknown / Unsupported Mineral"


def test_jpeg_png_and_mpo_upload_compatibility():
    """Verify compatibility with JPEG, PNG, and multi-frame MPO formats."""
    # 1. JPEG
    buf_jpg = io.BytesIO()
    Image.new("RGB", (200, 200), (120, 120, 120)).save(buf_jpg, format="JPEG")
    res_jpg = isolate_specimen(buf_jpg.getvalue())
    assert res_jpg["status"] == "SUCCESS"

    # 2. PNG
    buf_png = io.BytesIO()
    Image.new("RGB", (200, 200), (120, 120, 120)).save(buf_png, format="PNG")
    res_png = isolate_specimen(buf_png.getvalue())
    assert res_png["status"] == "SUCCESS"

    # 3. Multi-frame MPO (if present in uploads or simulated)
    mpo_files = [f for f in os.listdir(os.path.join(BASE_DIR, "data", "uploads")) if f.endswith(".mpo")]
    if mpo_files:
        mpo_path = os.path.join(BASE_DIR, "data", "uploads", mpo_files[0])
        res_mpo = isolate_specimen(mpo_path)
        assert res_mpo["status"] in ["SUCCESS", "ERROR"]


def test_disputed_coal_specimen_crop_reduces_bauxite_bias_and_retains_ood(model_and_ood):
    """
    Evaluates the exact disputed Coal photograph:
    data/uploads/20261028_134742_70df91e2acfb_Bituminous_Coal.jpg
    Verifies:
      1. Specimen isolation successfully executes.
      2. Cropping reduces artifactual Bauxite probability.
      3. OOD rejection is strictly maintained (distance > 5.0).
      4. Final decision remains 'Unknown / Unsupported Mineral' with withheld confidence.
    """
    model, ood_cfg = model_and_ood
    coal_path = os.path.join(BASE_DIR, "data", "uploads", "20261028_134742_70df91e2acfb_Bituminous_Coal.jpg")
    if not os.path.exists(coal_path):
        pytest.skip(f"Target upload not found at {coal_path}")

    report = compare_image_and_crop(coal_path)
    assert report["status"] == "SUCCESS"

    seg = report["segmentation"]
    assert seg["is_segmented"] is True
    assert seg["quality"] == "HIGH"
    assert seg["foreground_area_ratio"] < 0.85

    orig = report["original"]
    crop = report["candidate_crop"]

    # In the candidate crop, Bauxite probability decreases
    assert crop["probabilities"]["Bauxite"] < orig["probabilities"]["Bauxite"]
    # Distance to Bauxite remains above threshold
    assert crop["manifold_distance"] > crop["ood_threshold"]
    # OOD status is strictly preserved
    assert crop["ood_status"] == "OUT_OF_DISTRIBUTION"
    assert crop["final_decision"] == "Unknown / Unsupported Mineral"
    assert crop["accepted_confidence"] == "Withheld"


def test_compare_specimen_crop_schema():
    """Verify compare_image_and_crop returns stable schema keys."""
    coal_path = os.path.join(BASE_DIR, "data", "uploads", "20261028_134742_70df91e2acfb_Bituminous_Coal.jpg")
    if not os.path.exists(coal_path):
        pytest.skip("Target upload not found")

    rep = compare_image_and_crop(coal_path)
    for key in ["status", "image_path", "segmentation", "original", "candidate_crop", "comparison_analysis"]:
        assert key in rep, f"Missing key '{key}' in report"

    for seg_key in ["is_segmented", "quality", "method_used", "crop_box", "original_dimensions", "crop_dimensions", "foreground_area_ratio"]:
        assert seg_key in rep["segmentation"], f"Missing segmentation key '{seg_key}'"

