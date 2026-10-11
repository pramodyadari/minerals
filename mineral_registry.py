"""
=============================================================================
AI MINERAL INTELLIGENCE — MULTI-MINERAL REGISTRY & STATUS AUDITOR
=============================================================================
Module: mineral_registry.py

Purpose:
  Provides the Python-side authoritative registry of supported minerals and
  their genuine training statuses:
    - TRAINED: Genuine model and verified prospectivity surface active on disk.
    - AWAITING_DATA / TRAINING_DATA_REQUIRED: No verified dataset found.
    - TRAINING_READY: Valid real dataset present, ready for training pipeline.
    - TRAINING_FAILED: Dataset was provided but failed validation.
    - NOT_TRAINED: Generic untrained state.

Scientific Integrity Rule:
  A commodity is marked TRAINED ONLY when an authentic model and data exist.
  Cross-mineral reuse is strictly prohibited.
=============================================================================
"""

import os
from enum import Enum
from typing import Dict, Any, List, Optional


class MineralStatus(str, Enum):
    TRAINED = "TRAINED"
    AWAITING_DATA = "AWAITING_DATA"
    TRAINING_DATA_REQUIRED = "TRAINING_DATA_REQUIRED"
    TRAINING_READY = "TRAINING_READY"
    TRAINING_FAILED = "TRAINING_FAILED"
    NOT_TRAINED = "NOT_TRAINED"


class ValidationStatus(str, Enum):
    SPATIALLY_VALIDATED = "SPATIALLY_VALIDATED"
    RANDOM_HOLDOUT_ONLY = "RANDOM_HOLDOUT_ONLY"
    NOT_VALIDATED = "NOT_VALIDATED"
    AWAITING_VALIDATION = "AWAITING_VALIDATION"


class CalibrationStatus(str, Enum):
    NOT_CALIBRATED = "NOT_CALIBRATED"
    CALIBRATED = "CALIBRATED"


class MineralRegistry:
    """
    Registry of all supported mineral commodities in the exploration platform.
    """

    _REGISTRY = {
        "manganese": {
            "id": "manganese",
            "display_name": "Manganese",
            "commodity_symbol": "Mn",
            "status": MineralStatus.TRAINED,
            "status_label": "TRAINED",
            "description": "Copernicus Sentinel-2 trained Random Forest model on Tile T44QMK (Balaghat belt, India).",
            "model_path": "models/manganese_random_forest.pkl",
            "metadata_path": "models/manganese_model_metadata.json",
            "prospectivity_raster": "outputs/manganese_prospectivity.tif",
            "zones_csv": "data/processed/high_prospectivity_zones.csv",
            "is_trained": True,
            "has_production_model": True
        },
        "iron_ore": {
            "id": "iron_ore",
            "display_name": "Iron Ore",
            "commodity_symbol": "Fe",
            "status": MineralStatus.AWAITING_DATA,
            "status_label": "AWAITING TRAINING DATA",
            "description": "Hematite/magnetite optical pipelines configured; awaiting ground-truth training data.",
            "model_path": "models/iron_ore_random_forest.pkl",
            "metadata_path": None,
            "prospectivity_raster": None,
            "zones_csv": None,
            "is_trained": False,
            "has_production_model": False
        },
        "bauxite": {
            "id": "bauxite",
            "display_name": "Bauxite",
            "commodity_symbol": "Al",
            "status": MineralStatus.AWAITING_DATA,
            "status_label": "AWAITING TRAINING DATA",
            "description": "Al-rich lateritic spectral pipelines configured; requires ground-truth deposit observations.",
            "model_path": "models/bauxite_random_forest.pkl",
            "metadata_path": None,
            "prospectivity_raster": None,
            "zones_csv": None,
            "is_trained": False,
            "has_production_model": False
        },
        "copper": {
            "id": "copper",
            "display_name": "Copper",
            "commodity_symbol": "Cu",
            "status": MineralStatus.AWAITING_DATA,
            "status_label": "AWAITING TRAINING DATA",
            "description": "Copper sulfide/oxide spectral pipelines configured; awaiting ground-truth training data.",
            "model_path": "models/copper_random_forest.pkl",
            "metadata_path": None,
            "prospectivity_raster": None,
            "zones_csv": None,
            "is_trained": False,
            "has_production_model": False
        },
        "lithium": {
            "id": "lithium",
            "display_name": "Lithium",
            "commodity_symbol": "Li",
            "status": MineralStatus.AWAITING_DATA,
            "status_label": "AWAITING TRAINING DATA",
            "description": "Lithium pegmatite/brine spectral pipelines configured; awaiting ground-truth training data.",
            "model_path": "models/lithium_random_forest.pkl",
            "metadata_path": None,
            "prospectivity_raster": None,
            "zones_csv": None,
            "is_trained": False,
            "has_production_model": False
        },
        "coal": {
            "id": "coal",
            "display_name": "Coal",
            "commodity_symbol": "C",
            "status": MineralStatus.AWAITING_DATA,
            "status_label": "AWAITING TRAINING DATA",
            "description": "Carbon absorption feature pipelines configured; awaiting ground-truth colliery data.",
            "model_path": "models/coal_random_forest.pkl",
            "metadata_path": None,
            "prospectivity_raster": None,
            "zones_csv": None,
            "is_trained": False,
            "has_production_model": False
        },
        "limestone": {
            "id": "limestone",
            "display_name": "Limestone",
            "commodity_symbol": "CaCO3",
            "status": MineralStatus.AWAITING_DATA,
            "status_label": "AWAITING TRAINING DATA",
            "description": "Carbonate absorption feature pipelines configured; awaiting ground-truth quarry data.",
            "model_path": "models/limestone_random_forest.pkl",
            "metadata_path": None,
            "prospectivity_raster": None,
            "zones_csv": None,
            "is_trained": False,
            "has_production_model": False
        }
    }

    @classmethod
    def get_mineral(cls, mineral_id: str) -> Optional[Dict[str, Any]]:
        clean_id = str(mineral_id).strip().lower()
        # Aliases
        if clean_id in ("iron", "iron-ore"):
            clean_id = "iron_ore"
        config = cls._REGISTRY.get(clean_id)
        if not config:
            return None

        # Dynamically verify if a model has been newly trained and placed on disk
        res = dict(config)
        model_p = res.get("model_path")
        if model_p and os.path.exists(model_p):
            res["is_trained"] = True
            res["status"] = MineralStatus.TRAINED
            res["status_label"] = "TRAINED"
        elif res["is_trained"] and not (model_p and os.path.exists(model_p)):
            res["is_trained"] = False
            res["status"] = MineralStatus.AWAITING_DATA
            res["status_label"] = "AWAITING TRAINING DATA"

        # Model and validation state isolation
        res["model_status"] = res["status"].value if isinstance(res["status"], MineralStatus) else str(res["status"])
        validation_report_p = os.path.join("models", f"{clean_id}_validation_report.json")
        if res["is_trained"] and os.path.exists(validation_report_p):
            res["validation_status"] = ValidationStatus.SPATIALLY_VALIDATED
        elif res["is_trained"]:
            res["validation_status"] = ValidationStatus.RANDOM_HOLDOUT_ONLY
        else:
            res["validation_status"] = ValidationStatus.NOT_VALIDATED

        res["calibration_status"] = CalibrationStatus.NOT_CALIBRATED
        res["independent_deposit_validation"] = {
            "status": "NOT_AVAILABLE",
            "display_value": "NOT AVAILABLE",
            "methodology": "Within-study spatial-sector validation",
            "training_deposit": "Ghondi Manganese Mine" if clean_id == "manganese" else "None",
            "independent_deposits_count": 0,
            "explanation": "Current positive ground truth originates from one known Manganese deposit (Ghondi Mine). Independent deposit validation requires additional real Manganese occurrence datasets."
        }
        return res

    @classmethod
    def list_minerals(cls) -> List[Dict[str, Any]]:
        return [cls.get_mineral(k) for k in cls._REGISTRY.keys()]

    @classmethod
    def is_trained(cls, mineral_id: str) -> bool:
        min_info = cls.get_mineral(mineral_id)
        return bool(min_info and min_info.get("is_trained"))
