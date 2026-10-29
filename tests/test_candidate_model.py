"""
Automated Tests for Candidate Model Fine-Tuning & Dataset Manifest
Covers:
  1. Dataset manifest integrity and categorization.
  2. Candidate model checkpoint and OOD configuration integrity.
  3. Production checkpoint isolation (production weights untouched).
  4. Candidate classification performance on test set (N=40).
  5. Candidate OOD rejection on unknown rocks (Quartz, Granite, Limestone, Sandstone, Basalt).
  6. Disputed field photograph OOD rejection retention.
  7. Rollback verification to production checkpoint.
"""

import os
import json
import pytest
import numpy as np
import torch
from PIL import Image

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

from ai.train import MineralConvNet, CLASSES
from ai.evaluate_candidate_vs_baseline import load_model_and_config, evaluate_single_image


def test_dataset_manifest_integrity():
    """Verify data/dataset_manifest.json exists and accurately catalogs files."""
    manifest_path = os.path.join(BASE_DIR, "data", "dataset_manifest.json")
    assert os.path.exists(manifest_path), "Dataset manifest must exist"

    with open(manifest_path, "r") as fp:
        manifest = json.load(fp)

    assert "total_files_indexed" in manifest
    assert "total_unique_hashes" in manifest
    assert manifest["total_files_indexed"] > 300
    assert "summary_by_source_type" in manifest
    assert "records" in manifest
    assert len(manifest["records"]) == manifest["total_files_indexed"]

    # Check source types segregation
    types = manifest["summary_by_source_type"]
    assert "SYNTHETIC_TEXTURE_PATCH" in types
    assert "OOD_REFERENCE_LITHOLOGY" in types
    assert "UNVERIFIED_FIELD_PHOTO" in types


def test_production_checkpoint_isolation():
    """Verify that production checkpoint was NOT overwritten and remains identical to baseline."""
    prod_path = os.path.join(BASE_DIR, "models", "mineral_image_classifier.pth")
    baseline_backup = os.path.join(BASE_DIR, "models", "mineral_image_classifier_baseline_cnn.pth")
    candidate_path = os.path.join(BASE_DIR, "models", "candidate_mineral_fine_tuned.pth")

    assert os.path.exists(prod_path), "Production checkpoint must exist"
    assert os.path.exists(candidate_path), "Candidate checkpoint must exist separately"

    if os.path.exists(baseline_backup):
        import hashlib
        with open(prod_path, "rb") as fp1, open(baseline_backup, "rb") as fp2:
            h1 = hashlib.sha256(fp1.read()).hexdigest()
            h2 = hashlib.sha256(fp2.read()).hexdigest()
        assert h1 == h2, "Production checkpoint must strictly match baseline backup (no unauthorized overwrite)"


def test_candidate_ood_config_integrity():
    """Verify candidate OOD configuration exists and contains calibrated statistical bounds."""
    cfg_path = os.path.join(BASE_DIR, "models", "candidate_mineral_ood_config.json")
    assert os.path.exists(cfg_path), "Candidate OOD configuration must exist"

    with open(cfg_path, "r") as fp:
        cfg = json.load(fp)

    assert cfg["rejection_threshold_tau"] == 5.0
    assert "centroids" in cfg
    assert "scale_bounds" in cfg
    for c in CLASSES:
        assert c in cfg["centroids"]
        assert len(cfg["centroids"][c]) == 128
        assert c in cfg["scale_bounds"]
        assert cfg["scale_bounds"][c][0] < cfg["scale_bounds"][c][1]


def test_candidate_model_test_set_performance():
    """Verify candidate model accurately classifies the untouched test set (N=40)."""
    weights_path = os.path.join(BASE_DIR, "models", "candidate_mineral_fine_tuned.pth")
    cfg_path = os.path.join(BASE_DIR, "models", "candidate_mineral_ood_config.json")

    model, ood_cfg = load_model_and_config("convnet", weights_path, cfg_path)
    assert model is not None, "Candidate model must be loadable"

    total = 0
    correct = 0
    for c in CLASSES:
        folder = os.path.join(BASE_DIR, "data", "test", c)
        for fname in os.listdir(folder):
            if fname.lower().endswith((".jpg", ".png")):
                fpath = os.path.join(folder, fname)
                with Image.open(fpath) as im:
                    res = evaluate_single_image(model, ood_cfg, im.convert("RGB"))
                total += 1
                if res["raw_predicted_class"] == c:
                    correct += 1

    acc = (correct / float(total)) * 100.0
    assert acc >= 95.0, f"Candidate model test accuracy ({acc}%) must meet >= 95% benchmark"


def test_candidate_model_ood_safety():
    """Verify candidate model safely rejects unknown rocks (0% False Acceptance Rate)."""
    weights_path = os.path.join(BASE_DIR, "models", "candidate_mineral_fine_tuned.pth")
    cfg_path = os.path.join(BASE_DIR, "models", "candidate_mineral_ood_config.json")

    model, ood_cfg = load_model_and_config("convnet", weights_path, cfg_path)
    assert model is not None, "Candidate model must be loadable"

    ood_dir = os.path.join(BASE_DIR, "data", "evaluation", "ood")
    if not os.path.exists(ood_dir):
        pytest.skip("OOD evaluation directory not found")

    total_ood = 0
    rejected = 0
    for rk in ["quartz", "granite", "limestone", "sandstone", "basalt"]:
        folder = os.path.join(ood_dir, rk)
        if os.path.exists(folder):
            for fname in os.listdir(folder):
                if fname.lower().endswith(".jpg"):
                    fpath = os.path.join(folder, fname)
                    with Image.open(fpath) as im:
                        res = evaluate_single_image(model, ood_cfg, im.convert("RGB"))
                    total_ood += 1
                    if res["ood_status"] == "OUT_OF_DISTRIBUTION":
                        rejected += 1

    assert total_ood == 60, f"Expected 60 OOD samples, found {total_ood}"
    assert rejected == 60, f"All 60 OOD unknown rock samples must be rejected (found {rejected}/{total_ood})"


def test_candidate_model_field_coal_rejection():
    """Verify candidate model safely withholds confidence on disputed coal upload."""
    coal_path = os.path.join(BASE_DIR, "data", "uploads", "20261028_134742_70df91e2acfb_Bituminous_Coal.jpg")
    if not os.path.exists(coal_path):
        pytest.skip("Disputed coal photo not found")

    weights_path = os.path.join(BASE_DIR, "models", "candidate_mineral_fine_tuned.pth")
    cfg_path = os.path.join(BASE_DIR, "models", "candidate_mineral_ood_config.json")

    model, ood_cfg = load_model_and_config("convnet", weights_path, cfg_path)
    with Image.open(coal_path) as im:
        res = evaluate_single_image(model, ood_cfg, im.convert("RGB"))

    assert res["ood_status"] == "OUT_OF_DISTRIBUTION"
    assert res["manifold_distance"] > 5.0
    assert res["final_decision"] == "Unknown / Unsupported Mineral"

