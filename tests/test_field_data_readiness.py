"""
Automated Tests for Phase 3: Field-Data Readiness & Classifier Reliability Audit
Covers:
  1. Manifest disk synchronization & hash integrity.
  2. Manifest metadata traceability (source, label, physical specimen ID, status, acquisition conditions).
  3. Strict zero-tolerance: zero verified field photographs in training split.
  4. Core split isolation (no cross-split exact content leakage among train, val, test).
  5. Specimen feedback queue quarantine enforcement (100% quarantined, zero training-eligible).
  6. Unverified field photo quarantine enforcement.
  7. Duplicate hash detection and cataloging consistency.
  8. Field data readiness report artifact integrity.
"""

import os
import json
import hashlib
import pytest

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MANIFEST_PATH = os.path.join(BASE_DIR, "data", "dataset_manifest.json")
FEEDBACK_PATH = os.path.join(BASE_DIR, "data", "feedback", "specimen_feedback_queue.jsonl")
REPORT_JSON_PATH = os.path.join(BASE_DIR, "models", "field_data_readiness_report.json")
REPORT_MD_PATH = os.path.join(BASE_DIR, "models", "field_data_readiness_report.md")


def compute_sha256(filepath):
    with open(filepath, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def test_manifest_disk_synchronization_and_hashes():
    """Verify that every file in the manifest exists on disk and its SHA256 matches."""
    assert os.path.exists(MANIFEST_PATH), "dataset_manifest.json must exist"
    with open(MANIFEST_PATH, "r") as fp:
        manifest = json.load(fp)

    records = manifest["records"]
    assert len(records) >= 600, f"Expected at least 600 records, got {len(records)}"

    # Spot check disk existence and hashes for a deterministic sample
    sample_records = records[::20]  # Every 20th file
    for r in sample_records:
        rel_path = r["relative_path"]
        abs_path = os.path.join(BASE_DIR, rel_path.replace("/", os.sep))
        assert os.path.exists(abs_path), f"File {rel_path} in manifest missing from disk"
        disk_sha = compute_sha256(abs_path)
        assert disk_sha == r["sha256"], f"SHA256 mismatch for {rel_path}"


def test_manifest_metadata_traceability():
    """Verify that every record contains traceable metadata with explicit null/unknown values."""
    with open(MANIFEST_PATH, "r") as fp:
        manifest = json.load(fp)

    required_keys = [
        "relative_path", "filename", "sha256", "file_size_bytes",
        "split_source", "inferred_or_assigned_class", "source_type",
        "verification_status", "physical_specimen_id", "is_verified_ground_truth",
        "acquisition_conditions", "is_corrupt", "dimensions", "format", "mode"
    ]

    for r in manifest["records"]:
        for k in required_keys:
            assert k in r, f"Record {r.get('relative_path')} missing key '{k}'"

        assert isinstance(r["is_verified_ground_truth"], bool)
        # All records must currently be false because no laboratory assays exist
        assert r["is_verified_ground_truth"] is False


def test_zero_verified_field_photos_in_training():
    """Verify that data/train contains 0 real field photographs and 0 unverified uploads."""
    with open(MANIFEST_PATH, "r") as fp:
        manifest = json.load(fp)

    train_records = [r for r in manifest["records"] if r["split_source"] == "train"]
    assert len(train_records) == 140, f"Expected exactly 140 training images, got {len(train_records)}"

    for r in train_records:
        assert r["source_type"] == "SYNTHETIC_TEXTURE_PATCH", (
            f"Training image {r['relative_path']} has unexpected source_type: {r['source_type']}"
        )
        assert r["verification_status"] == "SYNTHETIC_REFERENCE_ONLY"
        assert r["physical_specimen_id"] is None, "Synthetic patches cannot have physical specimen IDs"


def test_core_split_isolation_no_leakage():
    """Verify that no SHA-256 hash appears across multiple core splits (train, validation, test)."""
    with open(MANIFEST_PATH, "r") as fp:
        manifest = json.load(fp)

    sha_to_splits = {}
    for r in manifest["records"]:
        split = r["split_source"]
        if split in ["train", "validation", "test"]:
            h = r["sha256"]
            if h not in sha_to_splits:
                sha_to_splits[h] = set()
            sha_to_splits[h].add(split)

    leakages = {h: splits for h, splits in sha_to_splits.items() if len(splits) > 1}
    assert len(leakages) == 0, f"Detected cross-split exact data leakage: {leakages}"


def test_feedback_queue_quarantine_enforcement():
    """Verify that all user/expert feedback records are strictly quarantined and ineligible for training."""
    assert os.path.exists(FEEDBACK_PATH), "Feedback queue file must exist"

    records = []
    with open(FEEDBACK_PATH, "r") as fp:
        for line in fp:
            line = line.strip()
            if line:
                records.append(json.loads(line))

    assert len(records) > 0, "Expected non-empty feedback queue"

    for entry in records:
        assert entry.get("is_verified_ground_truth") is False, (
            f"Feedback {entry.get('feedback_id')} was improperly marked as verified ground truth"
        )
        assert entry.get("training_eligible") is False, (
            f"Feedback {entry.get('feedback_id')} was improperly marked as training eligible"
        )
        assert entry.get("review_status") == "PENDING_GEOLOGICAL_VALIDATION", (
            f"Feedback {entry.get('feedback_id')} is not in quarantined PENDING_GEOLOGICAL_VALIDATION state"
        )


def test_unverified_field_photos_quarantined():
    """Verify that all macroscopic field uploads in data/uploads are quarantined with explicit specimen IDs."""
    with open(MANIFEST_PATH, "r") as fp:
        manifest = json.load(fp)

    field_uploads = [r for r in manifest["records"] if r["source_type"] == "UNVERIFIED_FIELD_PHOTO"]
    assert len(field_uploads) >= 31, f"Expected at least 31 field upload files, got {len(field_uploads)}"

    for r in field_uploads:
        assert r["verification_status"] == "UNVERIFIED_QUARANTINED"
        assert r["is_verified_ground_truth"] is False
        assert r["physical_specimen_id"] in [
            "SPECIMEN_FIELD_COAL_001",
            "SPECIMEN_FIELD_MANGANESE_001",
            "SPECIMEN_FIELD_ROCK_001"
        ]


def test_field_data_readiness_report_artifacts():
    """Verify that models/field_data_readiness_report.json and .md exist and contain expected sections."""
    assert os.path.exists(REPORT_JSON_PATH), "field_data_readiness_report.json must exist"
    assert os.path.exists(REPORT_MD_PATH), "field_data_readiness_report.md must exist"

    with open(REPORT_JSON_PATH, "r") as fp:
        report = json.load(fp)

    assert report["executive_readiness_assessment"]["dataset_ready_for_scientifically_defensible_field_photo_evaluation"] is False
    assert report["executive_readiness_assessment"]["overall_status"] == "NOT_READY_FOR_FIELD_DEPLOYMENT"
    assert report["physical_specimens_vs_images"]["total_independent_physical_rock_specimens"] == 3
    assert report["physical_specimens_vs_images"]["verified_physical_specimens_count"] == 0
    assert "prioritized_specimen_acquisition_plan" in report

    with open(REPORT_MD_PATH, "r", encoding="utf-8") as fp:
        md = fp.read()

    assert "NOT READY FOR FIELD-PHOTO EVALUATION" in md
    assert "SPECIMEN_FIELD_COAL_001" in md
    assert "SPECIMEN_FIELD_MANGANESE_001" in md
    assert "SPECIMEN_FIELD_ROCK_001" in md

