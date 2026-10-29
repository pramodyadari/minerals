import os
import sys
import json
import hashlib
import pytest

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)


def compute_sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def test_production_checkpoint_integrity():
    prod_pth = os.path.join(BASE_DIR, "models", "mineral_image_classifier.pth")
    baseline_pth = os.path.join(BASE_DIR, "models", "mineral_image_classifier_baseline_cnn.pth")
    assert os.path.exists(prod_pth), "Production checkpoint must exist"
    assert os.path.exists(baseline_pth), "Baseline backup checkpoint must exist"
    assert compute_sha256(prod_pth) == compute_sha256(baseline_pth), "Production checkpoint must remain identical to baseline"


def test_ood_threshold_integrity():
    ood_cfg_path = os.path.join(BASE_DIR, "models", "mineral_classifier_ood_config.json")
    assert os.path.exists(ood_cfg_path), "OOD config must exist"
    with open(ood_cfg_path, "r") as f:
        cfg = json.load(f)
    assert cfg.get("rejection_threshold_tau") == 5.0, "OOD rejection threshold tau must remain exactly 5.0"


def test_experimental_models_isolation():
    reg_path = os.path.join(BASE_DIR, "models", "model_registry.json")
    if os.path.exists(reg_path):
        with open(reg_path, "r") as f:
            reg = json.load(f)
        for m in reg.get("registered_models", []):
            if m.get("model_id") in ["candidate_finetuned_cnn", "resnet18_transfer"]:
                assert m.get("deployment_status") != "ACTIVE_PRODUCTION", "Experimental models must not be active in production"


def test_data_governance_no_unverified_in_train():
    manifest_path = os.path.join(BASE_DIR, "data", "dataset_manifest.json")
    assert os.path.exists(manifest_path), "Dataset manifest must exist"
    with open(manifest_path, "r") as f:
        manifest = json.load(f)
    for record in manifest.get("records", []):
        if record.get("split_target") == "train" and record.get("source_category") == "FIELD_UPLOAD":
            assert record.get("verification_status") == "VERIFIED_GROUND_TRUTH", "No unverified field upload can be in train split"


def test_scientific_guardrails_contract():
    from backend.app.mineral_service import analyze_location_for_mineral
    res = analyze_location_for_mineral("Balaghat", 21.8000, 80.1800, "Manganese", 10.0, mock_satellite_error="MOCK_MODE")
    assert res.get("confidence_score") is None, "confidence_score must be None to prevent presenting relative scores as calibrated probabilities"
    assert "not been established" in res.get("confidence_note", "").lower()
    assert res.get("model_coverage") == "VALIDATED_ACTIVE"

    # Out of footprint
    res_out = analyze_location_for_mineral("Bangalore", 12.9716, 77.5946, "Manganese", 10.0, mock_satellite_error="MOCK_MODE")
    assert res_out.get("model_coverage") == "OUTSIDE_TRAINING_FOOTPRINT"
    assert res_out.get("prediction") is None


def test_phase5_reports_and_dual_verdict():
    json_path = os.path.join(BASE_DIR, "models", "phase5_end_to_end_validation_report.json")
    md_path = os.path.join(BASE_DIR, "models", "phase5_end_to_end_validation_report.md")
    assert os.path.exists(json_path), "Phase 5 JSON report must exist"
    assert os.path.exists(md_path), "Phase 5 Markdown report must exist"

    with open(json_path, "r") as f:
        data = json.load(f)

    verdicts = data.get("dual_verdict", {})
    assert verdicts.get("software_system_readiness", {}).get("status") == "PRODUCTION-READY"
    assert verdicts.get("scientific_field_readiness", {}).get("status") == "NOT READY FOR FIELD DEPLOYMENT"
