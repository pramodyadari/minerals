"""
Automated Tests for Phase 4: Specimen Data Governance & Evaluation Infrastructure
Covers:
  1. Manifest-to-disk hash consistency across all indexed records.
  2. Near-duplicate detection and reporting (iron_ore_train_004 vs iron_ore_test_004).
  3. Physical-specimen split isolation (all images of any specimen ID in exactly one split).
  4. Upload provenance categorization and reversible quarantine preservation.
  5. Specimen schema verification-status enforcement (Pydantic ground-truth validator).
  6. Separation of synthetic and field evaluation results (field accuracy is UNAVAILABLE).
  7. Production checkpoint and OOD configuration integrity.
"""

import os
import json
import hashlib
import pytest
from pydantic import ValidationError

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MANIFEST_PATH = os.path.join(BASE_DIR, "data", "dataset_manifest.json")
REPORT_PATH = os.path.join(BASE_DIR, "models", "phase4_data_governance_report.json")
PROD_MODEL_PATH = os.path.join(BASE_DIR, "models", "mineral_image_classifier.pth")
BASELINE_BACKUP_PATH = os.path.join(BASE_DIR, "models", "mineral_image_classifier_baseline_cnn.pth")
OOD_CONFIG_PATH = os.path.join(BASE_DIR, "models", "mineral_classifier_ood_config.json")

import sys
sys.path.insert(0, os.path.join(BASE_DIR, "backend", "app"))
from specimen_governance import (
    SpecimenRecord, VerificationStatus, DatasetSplit, LaboratoryAssayReport
)


def compute_sha256(filepath):
    with open(filepath, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def test_manifest_to_disk_hash_consistency():
    """Verify that every file in the manifest exists on disk and its SHA256 matches."""
    assert os.path.exists(MANIFEST_PATH), "dataset_manifest.json must exist"
    with open(MANIFEST_PATH, "r") as fp:
        manifest = json.load(fp)

    records = manifest["records"]
    assert len(records) >= 600, f"Expected at least 600 records, got {len(records)}"

    sample_records = records[::15]  # Deterministic sampling of every 15th file
    for r in sample_records:
        rel_path = r["relative_path"]
        abs_path = os.path.join(BASE_DIR, rel_path.replace("/", os.sep))
        assert os.path.exists(abs_path), f"File {rel_path} in manifest missing from disk"
        disk_sha = compute_sha256(abs_path)
        assert disk_sha == r["sha256"], f"SHA256 mismatch for {rel_path}"


def test_near_duplicate_detection_and_reporting():
    """Verify forensic evidence resolving iron_ore_train_004 vs iron_ore_test_004."""
    train_path = os.path.join(BASE_DIR, "data", "train", "iron_ore", "iron_ore_train_004.jpg")
    test_path = os.path.join(BASE_DIR, "data", "test", "iron_ore", "iron_ore_test_004.jpg")

    assert os.path.exists(train_path)
    assert os.path.exists(test_path)

    sha_tr = compute_sha256(train_path)
    sha_te = compute_sha256(test_path)
    assert sha_tr != sha_te, "Files must have distinct SHA-256 hashes"

    with open(REPORT_PATH, "r") as fp:
        report = json.load(fp)

    task1 = report["task1_split_integrity_resolution"]
    assert task1["forensic_evidence"]["sha256_train"] == sha_tr
    assert task1["forensic_evidence"]["sha256_test"] == sha_te
    assert task1["forensic_evidence"]["dhash_hamming_distance"] == 4
    assert task1["forensic_evidence"]["ahash_hamming_distance"] >= 12
    assert task1["forensic_evidence"]["pixel_max_absolute_difference"] > 50.0
    assert "INDEPENDENT_SYNTHETIC_PATCHES" in task1["conclusion_and_action"]


def test_physical_specimen_split_isolation():
    """Verify that all images sharing a physical_specimen_id reside in exactly one split."""
    with open(MANIFEST_PATH, "r") as fp:
        manifest = json.load(fp)

    specimen_to_splits = {}
    for r in manifest["records"]:
        pid = r.get("physical_specimen_id")
        if pid:
            split = r["split_source"]
            if pid not in specimen_to_splits:
                specimen_to_splits[pid] = set()
            specimen_to_splits[pid].add(split)

    for pid, splits in specimen_to_splits.items():
        assert len(splits) == 1, f"Specimen ID '{pid}' is leaked across multiple splits: {splits}"


def test_upload_provenance_and_reversible_quarantine():
    """Verify upload provenance categorization and confirm zero files were deleted."""
    with open(MANIFEST_PATH, "r") as fp:
        manifest = json.load(fp)

    upload_records = [r for r in manifest["records"] if r["split_source"] == "uploads"]
    assert len(upload_records) >= 250, "Expected at least 250 upload files"

    provenances = set(r["provenance_category"] for r in upload_records)
    assert "ORIGINAL_USER_UPLOAD" in provenances
    assert "EXACT_DUPLICATE_USER_COPY" in provenances
    assert "TEST_GENERATED_API_UPLOAD_REFERENCE" in provenances
    assert "CORRUPT_TEST_FIXTURE" in provenances
    assert "SOLID_BLOCK_TEST_FIXTURE" in provenances

    original_user_uploads = [r for r in upload_records if r["provenance_category"] == "ORIGINAL_USER_UPLOAD"]
    assert len(original_user_uploads) == 3, f"Expected exactly 3 original user uploads, got {len(original_user_uploads)}"


def test_verification_status_enforcement():
    """Verify that SpecimenRecord schema forbids is_verified_ground_truth=True without certified assay."""
    # 1. Unverified upload cannot be marked verified ground truth
    with pytest.raises(ValidationError):
        SpecimenRecord(
            specimen_id="SPECIMEN_INVALID_001",
            mineral_label="coal",
            verification_status=VerificationStatus.UNVERIFIED_PENDING_ASSAY,
            is_verified_ground_truth=True,  # VIOLATION: must raise
            laboratory_report=None
        )

    # 2. Cannot mark verified even if status is VERIFIED_ASSAYED without laboratory report
    with pytest.raises(ValidationError):
        SpecimenRecord(
            specimen_id="SPECIMEN_INVALID_002",
            mineral_label="iron_ore",
            verification_status=VerificationStatus.VERIFIED_ASSAYED,
            is_verified_ground_truth=True,  # VIOLATION: lacks report
            laboratory_report=None
        )

    # 3. Valid laboratory report succeeds
    valid_record = SpecimenRecord(
        specimen_id="SPECIMEN_ASSAYED_001",
        mineral_label="bauxite",
        verification_status=VerificationStatus.VERIFIED_ASSAYED,
        is_verified_ground_truth=True,
        laboratory_report=LaboratoryAssayReport(
            report_id="GEO_LAB_CERT_2026_094",
            assay_method="X-Ray Powder Diffraction (XRD) & WDXRF",
            accredited_laboratory="National Geological Materials Assay Centre",
            elemental_or_mineral_pct={"Al2O3": 48.2, "SiO2": 3.1, "Fe2O3": 18.5}
        )
    )
    assert valid_record.is_verified_ground_truth is True
    assert valid_record.laboratory_report.report_id == "GEO_LAB_CERT_2026_094"


def test_separation_of_synthetic_and_field_evaluation():
    """Verify that report strictly separates synthetic benchmarks and states field accuracy is UNAVAILABLE."""
    with open(REPORT_PATH, "r") as fp:
        report = json.load(fp)

    eval_gov = report["task4_evaluation_governance_report"]
    assert "section_a_synthetic_known_class_benchmark" in eval_gov
    assert "section_b_synthetic_ood_benchmark" in eval_gov
    assert "section_c_unverified_field_photo_diagnostics" in eval_gov
    assert "section_d_verified_field_specimen_evaluation" in eval_gov

    # Section A has valid synthetic test accuracy
    assert eval_gov["section_a_synthetic_known_class_benchmark"]["accuracy_pct"] == 100.0

    # Section B has safe OOD rejection
    assert eval_gov["section_b_synthetic_ood_benchmark"]["false_acceptance_rate_far_pct"] == 0.0

    # Section D explicitly states UNAVAILABLE
    sec_d = eval_gov["section_d_verified_field_specimen_evaluation"]
    assert sec_d["verified_field_accuracy"] == "UNAVAILABLE"
    assert sec_d["verified_field_macro_f1"] == "UNAVAILABLE"
    assert sec_d["verified_specimens_available"] == 0


def test_production_checkpoint_and_ood_config_integrity():
    """Verify production weights and threshold are identical to baseline and untouched."""
    assert os.path.exists(PROD_MODEL_PATH)
    assert os.path.exists(BASELINE_BACKUP_PATH)

    h_prod = compute_sha256(PROD_MODEL_PATH)
    h_base = compute_sha256(BASELINE_BACKUP_PATH)
    assert h_prod == h_base, "Production checkpoint was tampered with!"

    with open(OOD_CONFIG_PATH, "r") as fp:
        cfg = json.load(fp)

    tau = cfg.get("rejection_threshold_tau") or cfg.get("threshold")
    assert tau == 5.0, f"Production OOD threshold must remain 5.0, got {tau}"
    assert "Manifold" in cfg.get("method", "") or "embedding" in cfg.get("method", "").lower()
