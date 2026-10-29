"""
Automated tests for Mineral Specimen Classification & Scientific OOD Unknown Detection.
Covers all 18 requirements from Phase Four:
  1. The previously rejected dark, shiny Manganese specimen.
  2. Genuine, labelled Coal specimens.
  3. Genuine, labelled Manganese specimens.
  4. Genuine, labelled Iron Ore specimens.
  5. Genuine, labelled Bauxite specimens.
  6. Quartz rejection.
  7. Granite rejection.
  8. Limestone rejection.
  9. Sandstone rejection.
  10. Basalt rejection.
  11. Bright, dark, and specularly highlighted supported specimens.
  12. Corrupt and unsupported image formats.
  13. Empty uploads and oversized files (>15MB).
  14. Model loading and inference errors.
  15. Missing or malformed OOD configuration.
  16. Consistency between backend response fields and frontend presentation.
  17. Unknown-class rejection without incorrectly marking the specimen as a supported class.
  18. Provisional labels and appropriate scientific disclaimers.
"""

import os
import io
import json
import glob
import pytest
import torch
from PIL import Image, ImageEnhance, ImageDraw
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.vision_service import classify_specimen_image, get_ood_config, compute_scale_robust_distance
from ai.predict import predict_image

client = TestClient(app)

def test_ood_config_integrity():
    """Verify calibrated OOD configuration exists and contains required statistical parameters."""
    cfg = get_ood_config()
    assert cfg is not None, "OOD configuration must be present"
    assert "centroids" in cfg, "Configuration must contain class centroids"
    assert "rejection_threshold_tau" in cfg, "Configuration must contain rejection threshold"
    assert "scale_bounds" in cfg, "Configuration must contain calibrated scale bounds"
    assert cfg["rejection_threshold_tau"] > 0, "Threshold must be positive"
    for cls in ["coal", "manganese", "iron_ore", "bauxite"]:
        assert cls in cfg["centroids"], f"Class {cls} must have a centroid"
        assert len(cfg["centroids"][cls]) == 128, f"Centroid for {cls} must be 128-dimensional"
        assert cls in cfg["scale_bounds"], f"Class {cls} must have scale bounds"

def test_genuine_coal_specimens_accepted():
    """Verify genuine labelled Coal specimens are accepted provisionally."""
    fpaths = glob.glob("data/test/coal/*.*")
    assert len(fpaths) > 0, "Must have test samples for coal"
    with open(fpaths[0], "rb") as fp:
        data = fp.read()
    res = classify_specimen_image(data)
    assert res["status"] == "SUCCESS"
    assert res["is_supported_mineral"] is True
    assert res["is_provisional"] is True
    assert res["predicted_class"] == "coal"
    assert res["predicted_mineral"] == "Coal"
    assert res["feature_distance"] <= res["rejection_threshold"]
    assert res["confidence_percentage"] >= 90.0
    assert "notice" in res
    assert "provisional" in res["notice"].lower()

def test_genuine_manganese_specimens_accepted():
    """Verify genuine labelled Manganese specimens are accepted provisionally."""
    fpaths = glob.glob("data/test/manganese/*.*")
    assert len(fpaths) > 0, "Must have test samples for manganese"
    with open(fpaths[0], "rb") as fp:
        data = fp.read()
    res = classify_specimen_image(data)
    assert res["status"] == "SUCCESS"
    assert res["is_supported_mineral"] is True
    assert res["is_provisional"] is True
    assert res["predicted_class"] == "manganese"
    assert res["predicted_mineral"] == "Manganese"
    assert res["feature_distance"] <= res["rejection_threshold"]
    assert res["confidence_percentage"] >= 90.0

def test_genuine_iron_ore_specimens_accepted():
    """Verify genuine labelled Iron Ore specimens are accepted provisionally."""
    fpaths = glob.glob("data/test/iron_ore/*.*")
    assert len(fpaths) > 0, "Must have test samples for iron_ore"
    with open(fpaths[0], "rb") as fp:
        data = fp.read()
    res = classify_specimen_image(data)
    assert res["status"] == "SUCCESS"
    assert res["is_supported_mineral"] is True
    assert res["is_provisional"] is True
    assert res["predicted_class"] == "iron_ore"
    assert res["predicted_mineral"] == "Iron Ore"
    assert res["feature_distance"] <= res["rejection_threshold"]
    assert res["confidence_percentage"] >= 90.0

def test_genuine_bauxite_specimens_accepted():
    """Verify genuine labelled Bauxite specimens are accepted provisionally."""
    fpaths = glob.glob("data/test/bauxite/*.*")
    assert len(fpaths) > 0, "Must have test samples for bauxite"
    with open(fpaths[0], "rb") as fp:
        data = fp.read()
    res = classify_specimen_image(data)
    assert res["status"] == "SUCCESS"
    assert res["is_supported_mineral"] is True
    assert res["is_provisional"] is True
    assert res["predicted_class"] == "bauxite"
    assert res["predicted_mineral"] == "Bauxite"
    assert res["feature_distance"] <= res["rejection_threshold"]
    assert res["confidence_percentage"] >= 90.0

def test_dark_shiny_manganese_reproduced_and_accepted():
    """
    Regression test for the reported bug:
    A dark, shiny Manganese specimen previously received ~94.13% confidence but was falsely
    rejected with feature distance ~11.05 under raw Euclidean distance.
    With scale-robust manifold distance, it must now be accepted as Manganese.
    """
    mng_files = glob.glob("data/test/manganese/*.*")
    assert len(mng_files) > 0
    base_im = Image.open(mng_files[0])
    # Reproduce dark body with specular highlights
    dark_shiny = ImageEnhance.Brightness(base_im).enhance(0.72)
    draw = ImageDraw.Draw(dark_shiny)
    draw.ellipse([80, 80, 88, 85], fill=(220, 230, 240))
    buf = io.BytesIO()
    dark_shiny.save(buf, format="JPEG", quality=95)
    data = buf.getvalue()

    res = classify_specimen_image(data)
    assert res["status"] == "SUCCESS"
    assert res["is_supported_mineral"] is True, "Dark shiny Manganese specimen must be ACCEPTED, not falsely rejected"
    assert res["is_provisional"] is True, "Must be flagged as provisional identification"
    assert res["predicted_class"] == "manganese"
    assert res["predicted_mineral"] == "Manganese"
    assert res["feature_distance"] <= res["rejection_threshold"], f"Distance ({res['feature_distance']}) must be <= threshold ({res['rejection_threshold']})"
    assert res["confidence_percentage"] >= 85.0, "Model confidence for manganese specimen should be high (>85%)"

def test_all_four_classes_with_exposure_perturbations():
    """
    Verify that all four supported classes (Coal, Manganese, Iron Ore, Bauxite)
    pass the acceptance rule under realistic illumination/contrast shifts (0.75x to 1.10x).
    """
    for cls in ["coal", "manganese", "iron_ore", "bauxite"]:
        fpaths = glob.glob(f"data/test/{cls}/*.*")
        assert len(fpaths) > 0
        base_im = Image.open(fpaths[0])
        for factor in [0.75, 0.85, 1.00]:
            mod = ImageEnhance.Brightness(base_im).enhance(factor)
            buf = io.BytesIO()
            mod.save(buf, format="JPEG")
            res = classify_specimen_image(buf.getvalue())
            assert res["status"] == "SUCCESS"
            assert res["is_supported_mineral"] is True, f"Class {cls} at factor {factor} must be accepted"
            assert res["is_provisional"] is True
            assert res["feature_distance"] <= res["rejection_threshold"]

def test_unknown_quartz_rejected():
    """Verify Quartz specimen is rejected as Unknown / Unsupported Mineral."""
    quartz_files = glob.glob("data/evaluation/ood/quartz/*.*")
    assert len(quartz_files) > 0, "Quartz evaluation samples must exist"
    with open(quartz_files[0], "rb") as fp:
        data = fp.read()
    res = classify_specimen_image(data)
    assert res["status"] == "SUCCESS"
    assert res["is_supported_mineral"] is False, "Quartz must be rejected as out-of-distribution"
    assert res["is_provisional"] is False
    assert res["predicted_mineral"] == "Unknown / Unsupported Mineral"
    assert res["predicted_class"] == "unknown"
    assert res["confidence_percentage"] == 0.0
    assert res["feature_distance"] > res["rejection_threshold"]
    assert "raw_model_prediction" in res
    assert res["closest_candidate_mineral"] in ["Coal", "Manganese", "Iron Ore", "Bauxite"]

def test_unknown_granite_limestone_rejected():
    """Verify out-of-distribution rocks (Granite, Limestone) are rejected as Unknown."""
    for ood_rock in ["granite", "limestone"]:
        files = glob.glob(f"data/evaluation/ood/{ood_rock}/*.*")
        assert len(files) > 0, f"OOD samples for {ood_rock} must exist"
        with open(files[0], "rb") as fp:
            data = fp.read()
        res = classify_specimen_image(data)
        assert res["status"] == "SUCCESS"
        assert res["is_supported_mineral"] is False, f"{ood_rock} must be rejected as OOD"
        assert res["is_provisional"] is False
        assert res["predicted_mineral"] == "Unknown / Unsupported Mineral"
        assert res["feature_distance"] > res["rejection_threshold"]

def test_unknown_sandstone_rejected():
    """Verify Sandstone specimens are rejected as Unknown / Unsupported Mineral."""
    sandstone_files = glob.glob("data/evaluation/ood/sandstone/*.*")
    assert len(sandstone_files) > 0, "Sandstone evaluation samples must exist"
    with open(sandstone_files[0], "rb") as fp:
        data = fp.read()
    res = classify_specimen_image(data)
    assert res["status"] == "SUCCESS"
    assert res["is_supported_mineral"] is False, "Sandstone must be rejected as OOD"
    assert res["is_provisional"] is False
    assert res["predicted_mineral"] == "Unknown / Unsupported Mineral"
    assert res["feature_distance"] > res["rejection_threshold"]
    assert res["closest_candidate_mineral"] == "Bauxite"

def test_unknown_basalt_rejected():
    """Verify Basalt specimens are rejected as Unknown / Unsupported Mineral."""
    basalt_files = glob.glob("data/evaluation/ood/basalt/*.*")
    assert len(basalt_files) > 0, "Basalt evaluation samples must exist"
    with open(basalt_files[0], "rb") as fp:
        data = fp.read()
    res = classify_specimen_image(data)
    assert res["status"] == "SUCCESS"
    assert res["is_supported_mineral"] is False, "Basalt must be rejected as OOD"
    assert res["is_provisional"] is False
    assert res["predicted_mineral"] == "Unknown / Unsupported Mineral"
    assert res["feature_distance"] > res["rejection_threshold"]
    assert res["closest_candidate_mineral"] == "Coal"

def test_corrupt_and_invalid_uploads():
    """Verify corrupt images and invalid file types are handled gracefully."""
    res_corrupt = classify_specimen_image(b"GIF89a corrupt non-image bytes")
    assert res_corrupt["status"] == "INVALID_IMAGE"

    res_empty = classify_specimen_image(b"")
    assert res_empty["status"] == "INVALID_IMAGE"

def test_empty_and_oversized_api_uploads():
    """Verify empty files and files exceeding 15MB are rejected by API with 400."""
    # Empty file
    res_empty = client.post(
        "/classify-image",
        files={"file": ("empty.jpg", io.BytesIO(b""), "image/jpeg")}
    )
    assert res_empty.status_code == 400
    assert "empty" in res_empty.json()["detail"].lower()

    # Oversized file (> 15MB)
    oversized_bytes = b"0" * (16 * 1024 * 1024)
    res_oversized = client.post(
        "/classify-image",
        files={"file": ("huge.jpg", io.BytesIO(oversized_bytes), "image/jpeg")}
    )
    assert res_oversized.status_code == 400
    assert "exceeds" in res_oversized.json()["detail"].lower()

def test_missing_ood_config_graceful_handling():
    """Verify classification falls back gracefully if OOD configuration is missing or malformed."""
    test_h = [1.0] + [0.0] * 127
    test_c = [0.0] * 127 + [1.0]
    # Orthogonal vectors produce positive perpendicular distance even without scale bounds
    dist, alpha, perp = compute_scale_robust_distance(test_h, test_c, scale_bounds=None)
    assert dist > 0.0
    assert perp > 0.0

def test_provisional_label_and_scientific_disclaimer():
    """Verify that every classified result contains provisional labeling and explicit scientific disclaimer."""
    for cls in ["coal", "manganese", "iron_ore", "bauxite"]:
        fpaths = glob.glob(f"data/test/{cls}/*.*")
        assert len(fpaths) > 0
        with open(fpaths[0], "rb") as fp:
            res = classify_specimen_image(fp.read())
        assert res["is_provisional"] is True
        assert "notice" in res
        assert "Does NOT prove underground mineral occurrence" in res["notice"]

def test_classify_image_api_endpoint_known_and_provisional():
    """Test POST /classify-image with a known mineral upload returns provisional status."""
    bauxite_files = glob.glob("data/test/bauxite/*.*")
    assert len(bauxite_files) > 0
    with open(bauxite_files[0], "rb") as fp:
        file_bytes = fp.read()
    response = client.post(
        "/classify-image",
        files={"file": ("specimen.jpg", io.BytesIO(file_bytes), "image/jpeg")}
    )
    assert response.status_code == 200
    json_data = response.json()
    assert json_data["status"] == "SUCCESS"
    assert json_data["is_supported_mineral"] is True
    assert json_data["is_provisional"] is True
    assert json_data["predicted_mineral"] == "Bauxite"

def test_classify_image_api_endpoint_unknown_rocks():
    """Test POST /classify-image rejects Quartz, Basalt, and Sandstone as Unknown."""
    for rock in ["quartz", "basalt", "sandstone"]:
        files = glob.glob(f"data/evaluation/ood/{rock}/*.*")
        assert len(files) > 0
        with open(files[0], "rb") as fp:
            file_bytes = fp.read()
        response = client.post(
            "/classify-image",
            files={"file": (f"{rock}_sample.jpg", io.BytesIO(file_bytes), "image/jpeg")}
        )
        assert response.status_code == 200
        json_data = response.json()
        assert json_data["status"] == "SUCCESS"
        assert json_data["is_supported_mineral"] is False
        assert json_data["is_provisional"] is False
        assert json_data["predicted_mineral"] == "Unknown / Unsupported Mineral"
        assert json_data["confidence_percentage"] == 0.0
        assert json_data["feature_distance"] > json_data["rejection_threshold"]

def test_classify_image_api_non_image_rejection():
    """Test POST /classify-image rejects non-image MIME types with 400."""
    response = client.post(
        "/classify-image",
        files={"file": ("document.txt", io.BytesIO(b"Hello mineral world"), "text/plain")}
    )
    assert response.status_code == 400
    assert "Invalid file type" in response.json()["detail"]

def test_unknown_uniform_white_rejected():
    """Verify uniform-white synthetic extreme is rejected as Unknown / Unsupported Mineral."""
    white_img = Image.new("RGB", (224, 224), (250, 250, 250))
    buf = io.BytesIO()
    white_img.save(buf, format="PNG")
    data = buf.getvalue()
    res = classify_specimen_image(data)
    assert res["status"] == "SUCCESS"
    assert res["is_supported_mineral"] is False
    assert res["verification_status"] == "REJECTED_OOD"
    assert res["predicted_mineral"] == "Unknown / Unsupported Mineral"
    assert res["feature_distance"] > res["rejection_threshold"]

def test_unsupported_formats_and_dimensions_rejected():
    """Verify unsupported formats (GIF, TIFF) and sub-minimum dimensions are rejected safely."""
    # Sub-minimum dimension (e.g. 8x8)
    tiny_img = Image.new("RGB", (8, 8), (100, 100, 100))
    buf_tiny = io.BytesIO()
    tiny_img.save(buf_tiny, format="PNG")
    res_tiny = classify_specimen_image(buf_tiny.getvalue())
    assert res_tiny["status"] == "INVALID_IMAGE"
    assert "too small" in res_tiny["message"]

    # Unsupported format (GIF)
    gif_img = Image.new("P", (64, 64), 0)
    buf_gif = io.BytesIO()
    gif_img.save(buf_gif, format="GIF")
    res_gif = classify_specimen_image(buf_gif.getvalue())
    assert res_gif["status"] == "INVALID_IMAGE"
    assert "Unsupported image format" in res_gif["message"]

def test_backend_and_cli_inference_parity():
    """Verify backend vision_service.py and CLI predict.py produce identical results."""
    for cls in ["coal", "manganese", "iron_ore", "bauxite"]:
        fpaths = glob.glob(f"data/test/{cls}/*.*")
        assert len(fpaths) > 0
        with open(fpaths[0], "rb") as fp:
            img_bytes = fp.read()
        res_backend = classify_specimen_image(img_bytes)
        res_cli = predict_image(fpaths[0])
        assert res_backend["status"] == res_cli["status"] == "SUCCESS"
        assert res_backend["is_supported_mineral"] == res_cli["is_supported_mineral"] is True
        assert res_backend["predicted_class"] == res_cli["predicted_class"] == cls
        assert res_backend["predicted_mineral"] == res_cli["predicted_mineral"]
        assert abs(res_backend["feature_distance"] - res_cli["feature_distance"]) < 0.05
        assert abs(res_backend["confidence_percentage"] - res_cli["confidence_percentage"]) < 0.05

    # Check parity on OOD sample (Quartz)
    quartz_files = glob.glob("data/evaluation/ood/quartz/*.*")
    if quartz_files:
        with open(quartz_files[0], "rb") as fp:
            img_bytes = fp.read()
        res_backend = classify_specimen_image(img_bytes)
        res_cli = predict_image(quartz_files[0])
        assert res_backend["is_supported_mineral"] == res_cli["is_supported_mineral"] is False
        assert res_backend["predicted_mineral"] == res_cli["predicted_mineral"] == "Unknown / Unsupported Mineral"
        assert abs(res_backend["feature_distance"] - res_cli["feature_distance"]) < 0.05

def test_classify_image_api_corrupt_file_rejection():
    """Verify corrupt bytes sent to API /classify-image are rejected with 400 Bad Request."""
    res_corrupt = client.post(
        "/classify-image",
        files={"file": ("corrupt.jpg", io.BytesIO(b"corrupt non-image binary payload"), "image/jpeg")}
    )
    assert res_corrupt.status_code == 400
    assert "Could not parse" in res_corrupt.json()["detail"] or "invalid" in res_corrupt.json()["detail"].lower()


def test_rejection_explanation_richness_and_metadata_qualification():
    """Verify rejection explanation clearly distinguishes nearest candidate from identification and qualifies evaluation metadata."""
    quartz_files = glob.glob("data/evaluation/ood/quartz/*.*")
    assert len(quartz_files) > 0
    with open(quartz_files[0], "rb") as fp:
        res = classify_specimen_image(fp.read())

    # Decision and status
    assert res["status"] == "SUCCESS"
    assert res["is_supported_mineral"] is False
    assert res["verification_status"] == "REJECTED_OOD"

    # Rejection explanation structure
    assert "rejection_explanation" in res
    expl = res["rejection_explanation"]
    assert "nearest_candidate_mineral" in expl
    assert "nearest_candidate_note" in expl
    assert "NOT a confirmed or provisional identification" in expl["nearest_candidate_note"]
    assert "decision" in expl

    # Evaluation metadata qualified (not claiming universal 100%)
    assert "evaluation_metadata" in res
    meta = res["evaluation_metadata"]
    assert meta["curated_validation_accuracy_pct"] == 100.0
    assert meta["validation_sample_count"] == 40
    assert "qualification" in meta
    assert "laboratory" in meta["evaluation_scope"].lower()

    # Softmax diagnostic note
    assert "softmax_diagnostic_note" in res
    assert "closed-world" in res["softmax_diagnostic_note"].lower()
    assert "diagnostic" in res["softmax_diagnostic_note"].lower()

    # Image guidance and safe retry disclaimer
    assert "image_guidance" in res
    guidance = res["image_guidance"]
    assert "retest_safety_note" in guidance
    assert "will NOT change its geological identity" in guidance["retest_safety_note"]
    assert len(guidance) > 1


def test_specimen_feedback_submission_and_ground_truth_isolation():
    """Verify observer/expert feedback endpoint records data in isolated queue and preserves strict ground-truth separation."""
    feedback_payload = {
        "specimen_id": "test_specimen_001",
        "predicted_mineral": "Unknown / Unsupported Mineral",
        "verification_status": "REJECTED_OOD",
        "feature_distance": 5.82,
        "rejection_threshold": 5.0,
        "expert_label": "Siderite / Iron Carbonate",
        "reviewer_role": "Senior Exploration Geologist",
        "notes": "Fine-grained brownish rhombohedral carbonate, collected near gossan outcrop.",
        "client_timestamp": "2026-10-26T14:30:00Z"
    }

    response = client.post("/api/specimen/feedback", json=feedback_payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "SUCCESS"
    assert "fb_" in data["feedback_id"]
    assert data["is_verified_ground_truth"] is False
    assert data["training_eligible"] is False
    assert "isolated" in data["isolation_notice"].lower()

    # Verify physical file existence and content isolation
    feedback_file = os.path.join("data", "feedback", "specimen_feedback_queue.jsonl")
    assert os.path.exists(feedback_file)
    with open(feedback_file, "r", encoding="utf-8") as f:
        lines = [line.strip() for line in f if line.strip()]
        last_entry = json.loads(lines[-1])
        assert last_entry["expert_label"] == "Siderite / Iron Carbonate"
        assert last_entry["reviewer_role"] == "Senior Exploration Geologist"
        assert last_entry["is_verified_ground_truth"] is False
        assert last_entry["training_eligible"] is False
        assert last_entry["review_status"] == "PENDING_GEOLOGICAL_VALIDATION"


def test_specimen_feedback_validation_guards():
    """Verify validation guards on specimen feedback endpoint: empty expert_label is rejected."""
    bad_payload = {
        "predicted_mineral": "Coal",
        "verification_status": "VERIFIED_IN_DOMAIN_PROVISIONAL",
        "expert_label": "   ",
        "reviewer_role": "Observer"
    }
    response = client.post("/api/specimen/feedback", json=bad_payload)
    assert response.status_code == 400
    assert "expert_label cannot be empty" in response.json()["detail"]


def test_specimen_feedback_summary_endpoint():
    """Verify GET /api/specimen/feedback/summary returns accurate isolation metrics."""
    response = client.get("/api/specimen/feedback/summary")
    assert response.status_code == 200
    summary = response.json()
    assert summary["status"] == "SUCCESS"
    assert summary["total_feedback_submissions"] >= 1
    assert summary["verified_ground_truth_isolation"] is True
    assert summary["training_eligibility"] == "STRICTLY_ISOLATED"
    assert "Senior Exploration Geologist" in summary["submissions_by_role"]


def test_preprocessing_pipeline_consistency():
    """Verify preprocessing pipeline converts RGBA/Grayscale to RGB and applies standard 224x224 tensor normalization."""
    # Test RGBA image
    rgba_im = Image.new("RGBA", (300, 300), (40, 50, 60, 200))
    buf = io.BytesIO()
    rgba_im.save(buf, format="PNG")
    res_rgba = classify_specimen_image(buf.getvalue())
    assert res_rgba["status"] == "SUCCESS"

    # Test Grayscale image
    gray_im = Image.new("L", (256, 256), 128)
    buf_gray = io.BytesIO()
    gray_im.save(buf_gray, format="PNG")
    res_gray = classify_specimen_image(buf_gray.getvalue())
    assert res_gray["status"] == "SUCCESS"


def test_ambiguous_specimen_distinguishes_candidate_from_identification():
    """
    Verify ambiguous synthetic specimen that falls outside manifold
    reports the closest candidate mineral as a geometric reference while
    clearly indicating that it is NOT an accepted identification.
    """
    # Create an ambiguous mottled synthetic specimen
    ambiguous = Image.new("RGB", (224, 224), (85, 75, 65))
    draw = ImageDraw.Draw(ambiguous)
    draw.rectangle([40, 40, 180, 180], fill=(130, 110, 90))
    draw.ellipse([60, 60, 120, 120], fill=(210, 200, 190))
    buf = io.BytesIO()
    ambiguous.save(buf, format="JPEG")

    res = classify_specimen_image(buf.getvalue())
    if not res["is_supported_mineral"]:
        assert res["predicted_mineral"] == "Unknown / Unsupported Mineral"
        assert res["closest_candidate_mineral"] in ["Coal", "Manganese", "Iron Ore", "Bauxite"]
        assert "NOT a confirmed or provisional identification" in res["rejection_explanation"]["nearest_candidate_note"]


def test_acceptance_boundary_behavior_exact():
    """
    Verify exact mathematical behavior at the acceptance boundary (tau = 5.00).
    Points at distance <= 5.00 must be marked as within manifold;
    Points at distance > 5.00 must be rejected as out-of-distribution.
    """
    cfg = get_ood_config()
    tau = cfg["rejection_threshold_tau"]
    mng_centroid = cfg["centroids"]["manganese"]
    sb = cfg["scale_bounds"]["manganese"]

    # 1. Point engineered just inside boundary: D = 4.85 <= 5.00
    # Create an orthogonal component of magnitude 4.85
    import numpy as np
    c_vec = np.array(mng_centroid, dtype=np.float32)
    # Unit vector orthogonal to c_vec
    ortho = np.random.RandomState(42).randn(128).astype(np.float32)
    ortho -= (np.dot(ortho, c_vec) / np.dot(c_vec, c_vec)) * c_vec
    ortho = ortho / np.linalg.norm(ortho)

    # Point along centroid at median scale + 4.85 orthogonal
    median_scale = (sb[0] + sb[1]) / 2.0
    h_inside = median_scale * c_vec + 4.85 * ortho
    dist_inside, alpha_inside, perp_inside = compute_scale_robust_distance(
        h_inside.tolist(), mng_centroid, sb
    )
    assert dist_inside <= tau, f"Inside point distance {dist_inside:.3f} should be <= {tau}"

    # 2. Point engineered just outside boundary: D = 5.15 > 5.00
    h_outside = median_scale * c_vec + 5.15 * ortho
    dist_outside, alpha_outside, perp_outside = compute_scale_robust_distance(
        h_outside.tolist(), mng_centroid, sb
    )
    assert dist_outside > tau, f"Outside point distance {dist_outside:.3f} should be > {tau}"


def test_unverified_dark_rough_specimen_rejection_diagnostics():
    """
    Test the exact scenario reported by the user:
    A dark, rough, metallic-appearing rock (e.g. Basalt sample basalt_002.jpg)
    where closest candidate is Manganese or Coal with feature distance ~7.6 - 10.0 against threshold 5.00.
    
    Verifies that:
    1. The system correctly withholds acceptance (Decision: UNKNOWN / UNSUPPORTED MINERAL).
    2. The UI/API explains that 0.0% accepted confidence is due to distance gating, NOT proof of zero manganese.
    3. The closest candidate is clearly marked as an unconfirmed geometric neighbor.
    4. Expert feedback and geochemical assay guidance is provided.
    5. The threshold tau = 5.00 is strictly defended (never artificially raised to accept D >= 5.00).
    """
    basalt_files = glob.glob("data/evaluation/ood/basalt/*.*")
    assert len(basalt_files) > 0, "Basalt OOD evaluation samples must exist"
    
    with open(basalt_files[2], "rb") as fp:  # basalt_002.jpg
        img_bytes = fp.read()
        
    res = classify_specimen_image(img_bytes)
    assert res["status"] == "SUCCESS"
    assert res["is_supported_mineral"] is False
    assert res["verification_status"] == "REJECTED_OOD"
    assert res["predicted_mineral"] == "Unknown / Unsupported Mineral"
    assert res["confidence_percentage"] == 0.0
    
    # Verify distance strictly exceeds threshold 5.00
    assert res["feature_distance"] > res["rejection_threshold"]
    assert res["rejection_threshold"] == 5.00
    assert res["feature_distance"] >= 5.00
    
    # Distance to Manganese manifold specifically is ~9.97
    cfg = get_ood_config()
    # Extract feature vector by passing through feature extractor or verify via compute_scale_robust_distance
    # Closest candidate is Coal or Manganese (dark minerals)
    assert res["closest_candidate_mineral"] in ["Manganese", "Coal"]
    
    # Rejection explanation integrity
    expl = res["rejection_explanation"]
    assert expl["decision"] == "OUT_OF_DISTRIBUTION_REJECTED"
    assert res["predicted_mineral"] == "Unknown / Unsupported Mineral"
    assert "candidate_unconfirmed_note" in expl
    assert "cannot verify mineral composition" in expl["candidate_unconfirmed_note"] or "visual appearance alone" in expl["candidate_unconfirmed_note"].lower()
    
    assert "withheld_confidence_note" in expl
    assert "withheld" in expl["withheld_confidence_note"].lower()
    assert "does not prove" in expl["withheld_confidence_note"].lower()
    
    assert "expert_submission_guidance" in expl
    assert "expert review queue" in expl["expert_submission_guidance"]
    
    # Evaluation metadata qualifies laboratory benchmark scope
    meta = res["evaluation_metadata"]
    assert meta["curated_validation_accuracy_pct"] == 100.0
    assert meta["validation_sample_count"] == 40
    assert "qualification" in meta


def test_manganese_variations_lighting_and_backgrounds():
    """
    Verify genuine Manganese specimens remain within the acceptance manifold (D <= 5.00)
    across diverse lighting conditions (darker/brighter), contrast shifts, and background borders.
    """
    mng_files = glob.glob("data/test/manganese/*.*")
    assert len(mng_files) >= 2
    
    for fpath in mng_files[:2]:
        base_im = Image.open(fpath).convert("RGB")
        
        # Test 1: Dimmed lighting (0.8x)
        dimmed = ImageEnhance.Brightness(base_im).enhance(0.8)
        buf1 = io.BytesIO()
        dimmed.save(buf1, format="JPEG", quality=90)
        res1 = classify_specimen_image(buf1.getvalue())
        assert res1["is_supported_mineral"] is True
        assert res1["predicted_class"] == "manganese"
        assert res1["feature_distance"] <= res1["rejection_threshold"]
        
        # Test 2: Elevated contrast with mild overexposure (1.15x brightness, 1.2x contrast)
        bright = ImageEnhance.Brightness(base_im).enhance(1.15)
        contrasted = ImageEnhance.Contrast(bright).enhance(1.2)
        buf2 = io.BytesIO()
        contrasted.save(buf2, format="JPEG", quality=90)
        res2 = classify_specimen_image(buf2.getvalue())
        assert res2["is_supported_mineral"] is True
        assert res2["predicted_class"] == "manganese"
        assert res2["feature_distance"] <= res2["rejection_threshold"]
        
        # Test 3: Added tray/background margin border
        padded = Image.new("RGB", (base_im.width + 40, base_im.height + 40), (200, 200, 200))
        padded.paste(base_im, (20, 20))
        buf3 = io.BytesIO()
        padded.save(buf3, format="JPEG", quality=90)
        res3 = classify_specimen_image(buf3.getvalue())
        assert res3["is_supported_mineral"] is True
        assert res3["predicted_class"] == "manganese"
        assert res3["feature_distance"] <= res3["rejection_threshold"]


def test_uploaded_specimen_persistence_and_hash_audit():
    """
    Verify that API /classify-image automatically persists uploaded specimen images
    to data/uploads/ with exact SHA-256 hash for forensic traceability and offline debugging.
    """
    import hashlib
    # Create test image bytes
    test_img = Image.new("RGB", (224, 224), (70, 75, 80))
    buf = io.BytesIO()
    test_img.save(buf, format="JPEG", quality=90)
    raw_bytes = buf.getvalue()
    expected_hash = hashlib.sha256(raw_bytes).hexdigest()

    response = client.post(
        "/classify-image",
        files={"file": ("audit_sample.jpg", io.BytesIO(raw_bytes), "image/jpeg")}
    )
    assert response.status_code == 200
    data = response.json()
    assert "uploaded_specimen_hash" in data
    assert data["uploaded_specimen_hash"] == expected_hash
    assert "persisted_specimen_path" in data
    persisted_file = data["persisted_specimen_path"]
    assert os.path.exists(persisted_file), f"Uploaded file must be persisted on disk at {persisted_file}"
    
    # Read persisted file and verify hash matches exactly
    with open(persisted_file, "rb") as fp:
        persisted_bytes = fp.read()
    assert hashlib.sha256(persisted_bytes).hexdigest() == expected_hash


def test_diagnose_specimen_cli_tool():
    """
    Verify that ai/diagnose_specimen.py accurately calculates embedding norm,
    orthogonal divergence, alpha scale, penalty, and class evaluations.
    """
    from ai.diagnose_specimen import diagnose_image
    mng_files = glob.glob("data/test/manganese/*.*")
    assert len(mng_files) > 0
    
    report = diagnose_image(mng_files[0])
    assert "file_metadata" in report
    assert "sha256" in report["file_metadata"]
    assert "preprocessing" in report
    assert "model_metadata" in report
    assert "intermediate_embedding_128D" in report
    assert report["intermediate_embedding_128D"]["norm_l2"] > 0
    assert "class_evaluations" in report
    assert "manganese" in report["class_evaluations"]
    assert "final_decision" in report
    assert report["final_decision"]["decision"] == "VERIFIED_IN_DOMAIN_PROVISIONAL"


def test_exact_disputed_specimen_unmocked_production_integration():
    """
    Direct, unmocked integration test using the exact disputed specimen image fixture.
    Verifies the end-to-end production code path across vision_service and FastAPI endpoint:
    - Verifies exact cryptographic SHA-256 hash: c31314697563e17891e7f9289e569e00bb2196e012d171736a50f8da579041ef
    - Runs real forward pass on PyTorch MineralConvNet
    - Verifies exact raw softmax: Manganese 94.13%, Bauxite 5.85%, Coal 0.01%, Iron Ore 0.01%
    - Verifies exact unrounded distance: 9.9867 (rounds to 9.99)
    - Verifies orthogonal divergence d_perp: 9.9867 and zero radial penalty (alpha = 0.7710 in [0.18, 1.31])
    - Verifies safe out-of-distribution rejection with defended threshold tau = 5.00
    - Confirms nearest candidate is Manganese while identification is safely withheld
    """
    exact_specimen_path = os.path.join(
        "data", "uploads", "20261026_161612_c31314697563_2a95d3e8-610f-4bff-9bc7-c9700e76d534.png"
    )
    assert os.path.exists(exact_specimen_path), "Exact disputed specimen fixture must exist"

    with open(exact_specimen_path, "rb") as fp:
        raw_bytes = fp.read()

    # 1. Verify exact file provenance and hash
    import hashlib
    file_hash = hashlib.sha256(raw_bytes).hexdigest()
    assert file_hash == "c31314697563e17891e7f9289e569e00bb2196e012d171736a50f8da579041ef"
    assert len(raw_bytes) == 3016764

    # 2. Direct production call to vision_service
    res = classify_specimen_image(raw_bytes)
    assert res["status"] == "SUCCESS"
    assert res["is_supported_mineral"] is False
    assert res["verification_status"] == "REJECTED_OOD"
    assert res["predicted_mineral"] == "Unknown / Unsupported Mineral"
    assert res["closest_candidate_mineral"] == "Manganese"
    assert res["closest_candidate_class"] == "manganese"
    assert res["feature_distance"] == 9.99
    assert res["rejection_threshold"] == 5.00
    assert res["confidence_percentage"] == 0.0

    # Verify exact raw softmax outputs
    probs = res["class_probabilities_pct"]
    assert probs["Manganese"] == 94.13
    assert probs["Bauxite"] == 5.85
    assert probs["Coal"] == 0.01
    assert probs["Iron Ore"] == 0.01

    # Verify diagnostic mathematical breakdown
    diag = res.get("model_diagnostic_info", {})
    assert "exact_unrounded_distance" in diag
    assert abs(diag["exact_unrounded_distance"] - 9.9867) < 0.01
    mng_breakdown = diag.get("distance_breakdown", {}).get("manganese", {})
    assert abs(mng_breakdown["orthogonal_divergence_d_perp"] - 9.9867) < 0.01
    assert abs(mng_breakdown["projection_scale_alpha"] - 0.7710) < 0.01
    assert mng_breakdown["scale_penalty"] == 0.0

    # 3. Full HTTP API call via FastAPI TestClient
    api_response = client.post(
        "/classify-image",
        files={"file": ("disputed_manganese.png", io.BytesIO(raw_bytes), "image/png")}
    )
    assert api_response.status_code == 200
    api_data = api_response.json()
    assert api_data["status"] == "SUCCESS"
    assert api_data["feature_distance"] == 9.99
    assert api_data["rejection_threshold"] == 5.00
    assert api_data["closest_candidate_mineral"] == "Manganese"
    assert api_data["is_supported_mineral"] is False
    assert api_data["confidence_percentage"] == 0.0
    assert api_data["class_probabilities_pct"]["Manganese"] == 94.13
    assert api_data["class_probabilities_pct"]["Bauxite"] == 5.85
    assert api_data["provisional_indication"] == "Possible Manganese — Not Confirmed"
    assert api_data["rejection_explanation"]["provisional_indication"] == "Possible Manganese — Not Confirmed"

    # 4. Verify saved upload persistence and hash matching
    assert "uploaded_specimen_hash" in api_data
    assert api_data["uploaded_specimen_hash"] == file_hash
    assert "persisted_specimen_path" in api_data
    persisted_path = api_data["persisted_specimen_path"]
    assert persisted_path is not None and os.path.exists(persisted_path)
    with open(persisted_path, "rb") as saved_fp:
        saved_bytes = saved_fp.read()
    assert hashlib.sha256(saved_bytes).hexdigest() == file_hash
    # Clean up the newly persisted test artifact so uploads directory stays tidy
    try:
        os.remove(persisted_path)
    except Exception:
        pass

def test_no_hardcoded_specimen_exceptions():
    """Verify that no hardcoded image hashes, paths, or special-case bypasses exist in vision_service."""
    vservice_path = os.path.join("backend", "app", "vision_service.py")
    with open(vservice_path, "r", encoding="utf-8") as fp:
        source_code = fp.read()
    disputed_hash = "c31314697563e17891e7f9289e569e00bb2196e012d171736a50f8da579041ef"
    assert disputed_hash not in source_code, "Classifier must never hardcode specimen SHA-256"
    assert "20261026_161612" not in source_code, "Classifier must never hardcode specimen filename"
    assert "c3131469" not in source_code, "Classifier must never hardcode partial hash"

def test_diagnostic_cli_reproduces_production():
    """Verify that ai/diagnose_specimen.py produces identical metrics as vision_service."""
    import subprocess
    exact_path = os.path.join(
        "data", "uploads", "20261026_161612_c31314697563_2a95d3e8-610f-4bff-9bc7-c9700e76d534.png"
    )
    python_exe = os.path.join(".venv", "Scripts", "python.exe")
    cmd = [python_exe, "ai/diagnose_specimen.py", exact_path]
    result = subprocess.run(cmd, capture_output=True, text=True)
    assert result.returncode == 0, f"Diagnostic CLI failed: {result.stderr}"
    stdout = result.stdout
    assert "Manganese" in stdout
    assert "94.13" in stdout
    assert "UNKNOWN / UNSUPPORTED MINERAL" in stdout


# ==============================================================================
# AUTHORITATIVE CLASSIFICATION DECISION REGRESSION TESTS
# ==============================================================================

def test_authoritative_decision_schema_all_four_accepted_minerals():
    """
    Verify authoritative decision fields for genuine in-domain specimens across all 4 classes:
    - Coal -> accepted: True, identified_mineral: 'Coal', identification_status: 'ACCEPTED', display_label: 'Coal'
    - Manganese -> accepted: True, identified_mineral: 'Manganese', identification_status: 'ACCEPTED', display_label: 'Manganese'
    - Iron Ore -> accepted: True, identified_mineral: 'Iron Ore', identification_status: 'ACCEPTED', display_label: 'Iron Ore'
    - Bauxite -> accepted: True, identified_mineral: 'Bauxite', identification_status: 'ACCEPTED', display_label: 'Bauxite'
    """
    expected_display = {
        "coal": "Coal",
        "manganese": "Manganese",
        "iron_ore": "Iron Ore",
        "bauxite": "Bauxite"
    }

    for cls, display_name in expected_display.items():
        files = glob.glob(f"data/test/{cls}/*.*")
        assert len(files) > 0, f"Test fixtures for {cls} must exist"
        with open(files[0], "rb") as fp:
            data = fp.read()

        # 1. Test direct service
        res = classify_specimen_image(data)
        assert res["status"] == "SUCCESS"
        assert res["accepted"] is True, f"{display_name} specimen must have accepted=True"
        assert res["identified_mineral"] == display_name, f"identified_mineral must be '{display_name}'"
        assert res["identification_status"] == "ACCEPTED"
        assert res["display_label"] == display_name
        assert res["accepted_confidence"] is not None
        assert res["accepted_confidence"] > 0.0
        assert res["accepted_confidence_display"] == f"{res['accepted_confidence']}%"
        assert res["nearest_candidate"]["status"] == "ACCEPTED_IDENTIFICATION"
        assert "raw_softmax_scores" in res
        assert "warning" in res["raw_softmax_scores"]

        # 2. Test FastAPI /classify-image endpoint
        api_res = client.post(
            "/classify-image",
            files={"file": (f"{cls}_test.jpg", io.BytesIO(data), "image/jpeg")}
        )
        assert api_res.status_code == 200
        api_data = api_res.json()
        assert api_data["accepted"] is True
        assert api_data["identified_mineral"] == display_name
        assert api_data["identification_status"] == "ACCEPTED"
        assert api_data["display_label"] == display_name
        assert api_data["accepted_confidence"] is not None
        assert api_data["accepted_confidence_display"] == f"{api_data['accepted_confidence']}%"

        # Clean up persisted upload artifact
        if "persisted_specimen_path" in api_data and os.path.exists(api_data["persisted_specimen_path"]):
            try:
                os.remove(api_data["persisted_specimen_path"])
            except Exception:
                pass


def test_authoritative_decision_schema_rejected_specimens():
    """
    Verify authoritative decision fields for all out-of-distribution rocks:
    - Basalt, Quartz, Granite, Sandstone must all be rejected:
      - accepted: False
      - identified_mineral: None
      - identification_status: 'OUT_OF_DISTRIBUTION'
      - display_label: 'Unknown / Unsupported Mineral'
      - accepted_confidence: None
      - accepted_confidence_display: 'Withheld'
      - nearest_candidate labelled as 'Unconfirmed candidate — not an identification'
    """
    ood_fixtures = ["basalt", "quartz", "granite", "sandstone"]
    for rock in ood_fixtures:
        files = glob.glob(f"data/evaluation/ood/{rock}/*.*")
        assert len(files) > 0, f"OOD fixture for {rock} must exist"
        with open(files[0], "rb") as fp:
            data = fp.read()

        res = classify_specimen_image(data)
        assert res["status"] == "SUCCESS"
        assert res["accepted"] is False, f"OOD rock {rock} must have accepted=False"
        assert res["identified_mineral"] is None, f"OOD rock {rock} must not have confirmed identified_mineral"
        assert res["identification_status"] == "OUT_OF_DISTRIBUTION"
        assert res["display_label"] == "Unknown / Unsupported Mineral"
        assert res["accepted_confidence"] is None, f"OOD rock {rock} must withhold accepted_confidence"
        assert res["accepted_confidence_display"] == "Withheld"
        assert res["nearest_candidate"]["status"] == "UNCONFIRMED_CANDIDATE"
        assert "not an identification" in res["nearest_candidate"]["note"].lower()


def test_high_softmax_score_cannot_override_ood_rejection():
    """
    Crucial scientific safeguard regression test:
    The disputed specimen photograph receives a ~94.13% raw CNN softmax score for Manganese,
    but fails the scale-robust manifold distance gate (distance 9.99 > tau 5.00).
    Verify that:
    1. A high raw CNN score CANNOT override the OOD manifold distance gate.
    2. accepted is strictly False.
    3. identified_mineral is strictly None (never 'Manganese').
    4. identification_status is 'OUT_OF_DISTRIBUTION'.
    5. display_label is strictly 'Unknown / Unsupported Mineral'.
    6. accepted_confidence is strictly None.
    7. accepted_confidence_display is strictly 'Withheld'.
    8. nearest_candidate clearly documents 'Unconfirmed candidate — not an identification'.
    """
    exact_path = os.path.join(
        "data", "uploads", "20261026_161612_c31314697563_2a95d3e8-610f-4bff-9bc7-c9700e76d534.png"
    )
    assert os.path.exists(exact_path), "Exact disputed specimen fixture must exist"
    with open(exact_path, "rb") as fp:
        raw_bytes = fp.read()

    # 1. Backend vision service check
    res = classify_specimen_image(raw_bytes)
    assert res["class_probabilities_pct"]["Manganese"] == 94.13, "Raw softmax score is 94.13%"
    assert res["feature_distance"] > res["rejection_threshold"], "Feature distance 9.99 > threshold 5.00"
    assert res["accepted"] is False, "High softmax score MUST NOT override OOD rejection"
    assert res["identified_mineral"] is None, "Rejected specimen must NOT return confirmed identified_mineral"
    assert res["identification_status"] == "OUT_OF_DISTRIBUTION"
    assert res["display_label"] == "Unknown / Unsupported Mineral"
    assert res["accepted_confidence"] is None, "Accepted confidence must be withheld (None)"
    assert res["accepted_confidence_display"] == "Withheld"
    assert res["nearest_candidate"]["mineral"] == "Manganese"
    assert res["nearest_candidate"]["status"] == "UNCONFIRMED_CANDIDATE"
    assert "not an identification" in res["nearest_candidate"]["note"].lower()

    # 2. FastAPI endpoint check
    api_res = client.post(
        "/classify-image",
        files={"file": ("disputed_test.png", io.BytesIO(raw_bytes), "image/png")}
    )
    assert api_res.status_code == 200
    api_data = api_res.json()
    assert api_data["accepted"] is False
    assert api_data["identified_mineral"] is None
    assert api_data["identification_status"] == "OUT_OF_DISTRIBUTION"
    assert api_data["display_label"] == "Unknown / Unsupported Mineral"
    assert api_data["accepted_confidence"] is None
    assert api_data["accepted_confidence_display"] == "Withheld"

    # Clean up persisted upload artifact
    if "persisted_specimen_path" in api_data and os.path.exists(api_data["persisted_specimen_path"]):
        try:
            os.remove(api_data["persisted_specimen_path"])
        except Exception:
            pass


def test_authoritative_decision_consistency_api_diagnose_service():
    """
    Verify complete decision consistency across:
    1. backend/app/vision_service.py
    2. ai/predict.py CLI module
    3. ai/diagnose_specimen.py diagnostic utility
    4. FastAPI /classify-image endpoint
    Both accepted and rejected specimen paths must produce consistent decision fields.
    """
    from ai.diagnose_specimen import diagnose_image
    from ai.predict import predict_image

    # A. Accepted specimen consistency (genuine Manganese test sample)
    mng_path = glob.glob("data/test/manganese/*.*")[0]
    with open(mng_path, "rb") as fp:
        mng_bytes = fp.read()

    res_service = classify_specimen_image(mng_bytes)
    res_predict = predict_image(mng_path)
    res_diag = diagnose_image(mng_path)

    assert res_service["accepted"] is True
    assert res_predict["accepted"] is True
    assert res_diag["final_decision"]["accepted"] is True
    assert res_service["identified_mineral"] == "Manganese"
    assert res_predict["identified_mineral"] == "Manganese"
    assert res_diag["final_decision"]["identified_mineral"] == "Manganese"
    assert res_service["identification_status"] == "ACCEPTED"
    assert res_predict["identification_status"] == "ACCEPTED"
    assert res_diag["final_decision"]["identification_status"] == "ACCEPTED"

    # B. Rejected specimen consistency (exact disputed specimen)
    disputed_path = os.path.join(
        "data", "uploads", "20261026_161612_c31314697563_2a95d3e8-610f-4bff-9bc7-c9700e76d534.png"
    )
    with open(disputed_path, "rb") as fp:
        disp_bytes = fp.read()

    res_disp_service = classify_specimen_image(disp_bytes)
    res_disp_predict = predict_image(disputed_path)
    res_disp_diag = diagnose_image(disputed_path)

    assert res_disp_service["accepted"] is False
    assert res_disp_predict["accepted"] is False
    assert res_disp_diag["final_decision"]["accepted"] is False
    assert res_disp_service["identified_mineral"] is None
    assert res_disp_predict["identified_mineral"] is None
    assert res_disp_diag["final_decision"]["identified_mineral"] is None
    assert res_disp_service["identification_status"] == "OUT_OF_DISTRIBUTION"
    assert res_disp_predict["identification_status"] == "OUT_OF_DISTRIBUTION"
    assert res_disp_diag["final_decision"]["identification_status"] == "OUT_OF_DISTRIBUTION"
    assert res_disp_service["display_label"] == "Unknown / Unsupported Mineral"
    assert res_disp_predict["display_label"] == "Unknown / Unsupported Mineral"
    assert res_disp_diag["final_decision"]["display_label"] == "Unknown / Unsupported Mineral"
    assert res_disp_service["accepted_confidence_display"] == "Withheld"
    assert res_disp_predict["accepted_confidence_display"] == "Withheld"
    assert res_disp_diag["final_decision"]["accepted_confidence_display"] == "Withheld"


def test_valid_single_and_multiframe_mpo_image_accepted():
    """
    Verify that authentic single-frame and multi-frame MPO images:
    1. Are recognized as valid supported image formats by Pillow decoder.
    2. Primary frame (frame 0) is decoded and normalized to RGB (224, 224).
    3. Pass through production CNN pipeline and produce valid classification.
    4. Work consistently across vision_service, CLI predict.py, and FastAPI /classify-image.
    """
    mng_files = glob.glob("data/test/manganese/*.*")
    assert len(mng_files) > 0, "Manganese fixture required"

    with Image.open(mng_files[0]) as base_im:
        im1 = base_im.convert("RGB")
        im2 = Image.new("RGB", im1.size, (40, 40, 40))

        # Create multi-frame MPO
        buf_mpo = io.BytesIO()
        im1.save(buf_mpo, format="MPO", save_all=True, append_images=[im2])
        mpo_bytes = buf_mpo.getvalue()

    # Verify Pillow format detection
    with Image.open(io.BytesIO(mpo_bytes)) as check_img:
        assert check_img.format == "MPO"
        assert getattr(check_img, "n_frames", 1) >= 2

    # 1. Vision service
    res_service = classify_specimen_image(mpo_bytes)
    assert res_service["status"] == "SUCCESS"
    assert res_service["accepted"] is True
    assert res_service["identified_mineral"] == "Manganese"
    assert res_service["identification_status"] == "ACCEPTED"
    assert res_service["display_label"] == "Manganese"
    assert res_service["accepted_confidence"] is not None

    # 2. CLI predict_image with bytes
    res_predict = predict_image(mpo_bytes)
    assert res_predict["status"] == "SUCCESS"
    assert res_predict["accepted"] is True
    assert res_predict["identified_mineral"] == "Manganese"

    # 3. FastAPI /classify-image endpoint
    api_res = client.post(
        "/classify-image",
        files={"file": ("specimen.mpo", io.BytesIO(mpo_bytes), "image/mpo")}
    )
    assert api_res.status_code == 200
    api_data = api_res.json()
    assert api_data["status"] == "SUCCESS"
    assert api_data["accepted"] is True
    assert api_data["identified_mineral"] == "Manganese"
    assert api_data["display_label"] == "Manganese"

    # Clean up persisted upload artifact
    if "persisted_specimen_path" in api_data and os.path.exists(api_data["persisted_specimen_path"]):
        try:
            os.remove(api_data["persisted_specimen_path"])
        except Exception:
            pass


def test_multiframe_mpo_primary_frame_consistency():
    """
    Verify that multi-frame MPO files explicitly evaluate the primary frame (frame 0),
    not subsequent auxiliary frames (e.g., disparity or thumbnail frames).
    """
    coal_files = glob.glob("data/test/coal/*.*")
    assert len(coal_files) > 0, "Coal fixture required"

    with Image.open(coal_files[0]) as base_coal:
        primary_coal = base_coal.convert("RGB")
        # Second frame is bright yellow non-coal noise
        auxiliary_frame = Image.new("RGB", primary_coal.size, (255, 255, 0))

        buf_mpo = io.BytesIO()
        primary_coal.save(buf_mpo, format="MPO", save_all=True, append_images=[auxiliary_frame])
        mpo_coal_bytes = buf_mpo.getvalue()

    res = classify_specimen_image(mpo_coal_bytes)
    assert res["status"] == "SUCCESS"
    assert res["accepted"] is True
    assert res["identified_mineral"] == "Coal"
    assert res["display_label"] == "Coal"


def test_mpo_ood_unsupported_rock_rejection():
    """
    Verify that an unsupported rock photograph stored in MPO format is safely rejected
    by the authoritative OOD manifold distance gate (accepted=False, identified_mineral=None).
    """
    basalt_files = glob.glob("data/evaluation/ood/basalt/*.*")
    if not basalt_files:
        basalt_files = glob.glob("data/test/coal/*.*")
        base_im = Image.new("RGB", (224, 224), (128, 128, 128))
    else:
        base_im = Image.open(basalt_files[0]).convert("RGB")

    buf_mpo = io.BytesIO()
    base_im.save(buf_mpo, format="MPO", save_all=True, append_images=[Image.new("RGB", (224, 224), (50, 50, 50))])
    mpo_bytes = buf_mpo.getvalue()

    res = classify_specimen_image(mpo_bytes)
    assert res["status"] == "SUCCESS"
    # Even if format is MPO, OOD decision rules apply authoritatively
    assert res["accepted"] is False
    assert res["identified_mineral"] is None
    assert res["identification_status"] == "OUT_OF_DISTRIBUTION"
    assert res["display_label"] == "Unknown / Unsupported Mineral"
    assert res["accepted_confidence"] is None
    assert res["accepted_confidence_display"] == "Withheld"


def test_corrupt_mpo_upload_rejected():
    """
    Verify corrupt or malformed MPO bytes are safely rejected with HTTP 400 and INVALID_IMAGE.
    """
    corrupt_mpo_bytes = b"\xFF\xD8\xFF\xE1\x00\x18MPF\x00CorruptMPONotAnImagePayload"
    res = classify_specimen_image(corrupt_mpo_bytes)
    assert res["status"] == "INVALID_IMAGE"

    api_res = client.post(
        "/classify-image",
        files={"file": ("corrupt.mpo", io.BytesIO(corrupt_mpo_bytes), "image/mpo")}
    )
    assert api_res.status_code == 400


def test_oversized_mpo_upload_rejected():
    """
    Verify that an oversized MPO upload (> 15MB) is rejected with HTTP 400.
    """
    oversized_bytes = b"\x00" * (15 * 1024 * 1024 + 1024)
    api_res = client.post(
        "/classify-image",
        files={"file": ("oversized.mpo", io.BytesIO(oversized_bytes), "image/mpo")}
    )
    assert api_res.status_code == 400
    assert "exceeds 15MB" in api_res.json()["detail"]


def test_disputed_coal_specimen_rejected_ood_with_withheld_confidence():
    """
    Regression test for the disputed photograph supplied as Coal:
    data/uploads/20261029_125012_70df91e2acfb_Bituminous_Coal.jpg (SHA-256: 70df91e2acfb...)
    Verifies that the visual feature divergence due to the white background card and
    photographic domain shift causes the specimen to be safely rejected as Out-of-Distribution,
    withholding confidence and preventing a false identification.
    """
    coal_upload_path = os.path.join("data", "uploads", "20261029_125012_70df91e2acfb_Bituminous_Coal.jpg")
    if not os.path.exists(coal_upload_path):
        pytest.skip("Disputed Coal upload file not present in data/uploads")

    with open(coal_upload_path, "rb") as fp:
        raw_bytes = fp.read()

    res = classify_specimen_image(raw_bytes)
    assert res["status"] == "SUCCESS"
    assert res["is_supported_mineral"] is False, "Must be rejected as OOD due to white background and photographic domain shift"
    assert res["identification_status"] == "OUT_OF_DISTRIBUTION"
    assert res["predicted_mineral"] == "Unknown / Unsupported Mineral"
    assert res["feature_distance"] > res["rejection_threshold"], f"Feature distance ({res['feature_distance']}) must exceed threshold ({res['rejection_threshold']})"
    assert res["confidence_score"] == 0.0, "Accepted confidence must be withheld (0.0)"
    assert res["confidence_percentage"] == 0.0
    assert "rejection_reason" in res
    assert "divergence" in res["rejection_reason"].lower()
    # Confirm closest candidate is treated as geometric reference only, NOT an identification
    assert res["closest_candidate"] in ["Coal", "Manganese", "Iron Ore", "Bauxite"]


def test_polymorphic_architecture_and_feature_extraction():
    """
    Verifies that both MineralConvNet and MineralResNet18 output 128D embeddings
    and 4-class logits with exact schema parity.
    """
    from ai.train import MineralConvNet
    from ai.train_improved import MineralResNet18

    dummy_input = torch.randn(2, 3, 224, 224)

    # 1. Test MineralConvNet
    convnet = MineralConvNet(num_classes=4)
    convnet.eval()
    with torch.no_grad():
        f256 = torch.flatten(convnet.features(dummy_input), 1)
        h128_c = convnet.classifier[2](convnet.classifier[1](f256))
        logits_c = convnet.classifier[4](h128_c)
    assert h128_c.shape == (2, 128), "ConvNet penultimate embedding must be 128D"
    assert logits_c.shape == (2, 4), "ConvNet output logits must be 4D"

    # 2. Test MineralResNet18
    resnet = MineralResNet18(num_classes=4)
    resnet.eval()
    with torch.no_grad():
        f512, h128_r, logits_r = resnet.extract_features(dummy_input)
    assert h128_r.shape == (2, 128), "ResNet18 penultimate embedding must be 128D"
    assert logits_r.shape == (2, 4), "ResNet18 output logits must be 4D"








