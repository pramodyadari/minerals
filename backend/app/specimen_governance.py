"""
Specimen Data Governance & Provenance Schema (Phase 4)
Defines strict Pydantic models and validation rules for geological mineral specimens.

Rules enforced:
1. is_verified_ground_truth CANNOT be True unless accompanied by a certified laboratory assay report.
2. Unverified user uploads, synthetic patches, and test fixtures are strictly non-ground-truth.
3. Every specimen record maintains traceable image hashes, acquisition conditions, and split isolation.
"""

from enum import Enum
from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, field_validator, model_validator


class VerificationStatus(str, Enum):
    VERIFIED_ASSAYED = "VERIFIED_ASSAYED"
    UNVERIFIED_PENDING_ASSAY = "UNVERIFIED_PENDING_ASSAY"
    SYNTHETIC_REFERENCE = "SYNTHETIC_REFERENCE"
    SYNTHETIC_OOD_BENCHMARK = "SYNTHETIC_OOD_BENCHMARK"
    TEST_FIXTURE = "TEST_FIXTURE"
    CORRUPT_FIXTURE = "CORRUPT_FIXTURE"


class DatasetSplit(str, Enum):
    TRAIN = "train"
    VALIDATION = "validation"
    TEST = "test"
    EVALUATION_KNOWN = "evaluation_known"
    EVALUATION_OOD = "evaluation_ood"
    QUARANTINED_UPLOAD = "quarantined_upload"
    UNASSIGNED = "unassigned"


class LaboratoryAssayReport(BaseModel):
    report_id: str = Field(..., description="Unique laboratory assay report or certificate identifier")
    assay_method: str = Field(..., description="Analytical method: XRF, XRD, ICP-MS, proximate analysis, etc.")
    accredited_laboratory: str = Field(..., description="Name of certifying laboratory or analytical facility")
    elemental_or_mineral_pct: Dict[str, float] = Field(default_factory=dict, description="Certified mineral/element weight percentages")
    report_date: Optional[str] = Field(None, description="ISO-8601 date of laboratory certificate")
    notes: Optional[str] = None


class SamplingProvenance(BaseModel):
    geological_formation: Optional[str] = None
    mining_district: Optional[str] = None
    state_province: Optional[str] = None
    country: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    collector_or_operator: Optional[str] = None
    collection_date: Optional[str] = None


class AcquisitionConditions(BaseModel):
    lighting_regime: Optional[str] = None
    background: Optional[str] = None
    scale_bar_present: bool = False
    color_calibration_target: Optional[str] = None
    camera_make_model: Optional[str] = None
    original_dimensions: List[int] = Field(default_factory=lambda: [0, 0])
    raw_exif_preserved: bool = False


class DerivedImageRelationship(BaseModel):
    derived_path: str
    derivation_type: str  # e.g., "crop", "specimen_isolation", "synthetic_patch"
    sha256: str
    dimensions: List[int]


class SpecimenRecord(BaseModel):
    specimen_id: str = Field(..., description="Unique specimen identifier (e.g. SPECIMEN_FIELD_COAL_001)")
    mineral_label: str = Field(..., description="Target mineral or lithology name")
    verification_status: VerificationStatus = Field(..., description="Formal verification status")
    is_verified_ground_truth: bool = Field(False, description="Strict boolean ground truth flag")
    laboratory_report: Optional[LaboratoryAssayReport] = Field(None, description="Certified laboratory assay report")
    sampling_provenance: Optional[SamplingProvenance] = None
    acquisition_conditions: Optional[AcquisitionConditions] = None
    original_image_hashes: List[str] = Field(default_factory=list, description="List of primary capture SHA-256 hashes")
    derived_images: List[DerivedImageRelationship] = Field(default_factory=list)
    dataset_split: DatasetSplit = Field(DatasetSplit.UNASSIGNED)
    reviewer_role: Optional[str] = None
    verification_timestamp: Optional[str] = None
    quarantine_notes: Optional[str] = None

    @model_validator(mode="after")
    def validate_ground_truth_integrity(self):
        """Enforces that is_verified_ground_truth can only be True if a laboratory report is attached."""
        if self.is_verified_ground_truth:
            if self.verification_status != VerificationStatus.VERIFIED_ASSAYED:
                raise ValueError(
                    f"Ground truth violation: Specimen '{self.specimen_id}' has is_verified_ground_truth=True "
                    f"but verification_status is '{self.verification_status.value}' (must be VERIFIED_ASSAYED)."
                )
            if self.laboratory_report is None:
                raise ValueError(
                    f"Ground truth violation: Specimen '{self.specimen_id}' has is_verified_ground_truth=True "
                    f"but lacks a certified laboratory assay report."
                )
            if not self.laboratory_report.report_id or not self.laboratory_report.assay_method:
                raise ValueError(
                    f"Ground truth violation: Specimen '{self.specimen_id}' laboratory report must include "
                    f"both 'report_id' and 'assay_method'."
                )
        return self


def create_quarantined_field_specimen(
    specimen_id: str,
    mineral_label: str,
    original_sha256: str,
    dimensions: List[int],
    acquisition_summary: str,
    notes: str
) -> SpecimenRecord:
    """Helper to instantiate a properly quarantined, unverified field specimen record."""
    return SpecimenRecord(
        specimen_id=specimen_id,
        mineral_label=mineral_label,
        verification_status=VerificationStatus.UNVERIFIED_PENDING_ASSAY,
        is_verified_ground_truth=False,
        laboratory_report=None,
        sampling_provenance=SamplingProvenance(),
        acquisition_conditions=AcquisitionConditions(
            lighting_regime=acquisition_summary,
            original_dimensions=dimensions
        ),
        original_image_hashes=[original_sha256],
        dataset_split=DatasetSplit.QUARANTINED_UPLOAD,
        reviewer_role="Senior Computer-Vision Engineer & Mineral-Data Quality Auditor",
        quarantine_notes=notes
    )

