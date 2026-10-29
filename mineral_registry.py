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


class ValidatedProspectivityModel:
    """
    Data and model interface for validated mineral prospectivity models.
    Supports genuine future expansion across additional commodities and geographic regions.
    Each model declares its mineral, training footprint, input features, data provenance,
    validation results, and score interpretation.
    """
    def __init__(
        self,
        mineral: str,
        commodity_id: str,
        model_name: str,
        training_footprint: Dict[str, Any],
        input_features: List[str],
        data_provenance: Dict[str, Any],
        validation_results: Dict[str, Any],
        score_interpretation: Dict[str, Any],
        model_path: Optional[str] = None,
        has_validated_model: bool = False,
    ):
        self.mineral = mineral
        self.commodity_id = commodity_id
        self.model_name = model_name
        self.training_footprint = training_footprint
        self.input_features = input_features
        self.data_provenance = data_provenance
        self.validation_results = validation_results
        self.score_interpretation = score_interpretation
        self.model_path = model_path
        self.has_validated_model = has_validated_model

    def is_coordinate_covered(self, lat: float, lon: float) -> bool:
        """Evaluates whether given WGS84 coordinate falls within validated training footprint."""
        if not self.has_validated_model:
            return False
        bounds = self.training_footprint.get("bounds")
        if bounds:
            return (
                bounds.get("min_lat", -90.0) <= lat <= bounds.get("max_lat", 90.0) and
                bounds.get("min_lon", -180.0) <= lon <= bounds.get("max_lon", 180.0)
            )
        validator = self.training_footprint.get("validator")
        if callable(validator):
            return validator(lat, lon)
        return False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "mineral": self.mineral,
            "commodity_id": self.commodity_id,
            "model_name": self.model_name,
            "has_validated_model": self.has_validated_model,
            "model_path": self.model_path,
            "training_footprint": {
                k: v for k, v in self.training_footprint.items() if k != "validator"
            },
            "input_features": self.input_features,
            "data_provenance": self.data_provenance,
            "validation_results": self.validation_results,
            "score_interpretation": self.score_interpretation,
        }


class ProspectivityModelRegistry:
    """
    Authoritative registry of machine-learning prospectivity models for mineral exploration.
    Enforces scientific integrity:
    - Never claims Coal, Iron Ore, or Bauxite geographical prediction is available without a validated model.
    - Manganese Random Forest model is strictly scoped to Sentinel-2 Tile T44QMK.
    - Distinguishes PROSPECTIVITY_AVAILABLE, OUTSIDE_TRAINING_FOOTPRINT, and DATA_NOT_AVAILABLE.
    """
    _MODELS: Dict[str, ValidatedProspectivityModel] = {}

    @classmethod
    def register_model(cls, model: ValidatedProspectivityModel) -> None:
        cls._MODELS[model.commodity_id.lower()] = model

    @classmethod
    def get_model(cls, commodity: str) -> Optional[ValidatedProspectivityModel]:
        clean = commodity.strip().lower().replace(" ", "_").replace("-", "_")
        return cls._MODELS.get(clean)

    @classmethod
    def list_registered_models(cls) -> List[Dict[str, Any]]:
        return [m.to_dict() for m in cls._MODELS.values()]

    @classmethod
    def evaluate_coverage(cls, mineral: str, lat: float, lon: float) -> Dict[str, Any]:
        """
        Evaluates model coverage for specified commodity and coordinates.
        Returns standardized status:
        - PROSPECTIVITY_AVAILABLE
        - OUTSIDE_TRAINING_FOOTPRINT
        - DATA_NOT_AVAILABLE
        """
        clean_min = mineral.strip().title() if mineral else "Unknown"
        model = cls.get_model(clean_min)

        if not model or not model.has_validated_model:
            return {
                "prospectivity_status": "DATA_NOT_AVAILABLE",
                "model_coverage": "NO_MODEL_FOR_COMMODITY",
                "prediction_availability": "UNAVAILABLE_NO_MODEL",
                "is_covered": False,
                "mineral": clean_min,
                "model_metadata": model.to_dict() if model else None,
                "reason": f"No validated spatial machine-learning model exists for {clean_min}. 3D prospectivity meshes and predictive scores are withheld to preserve scientific integrity."
            }

        # Model exists: check spatial footprint
        if model.is_coordinate_covered(lat, lon):
            return {
                "prospectivity_status": "PROSPECTIVITY_AVAILABLE",
                "model_coverage": "VALIDATED_ACTIVE",
                "prediction_availability": "AVAILABLE",
                "is_covered": True,
                "mineral": clean_min,
                "model_metadata": model.to_dict(),
                "reason": f"Target coordinates ({lat:.4f}°N, {lon:.4f}°E) fall within validated {model.training_footprint.get('region_name', 'training footprint')} ({model.training_footprint.get('tile_id', 'T44QMK')})."
            }
        else:
            return {
                "prospectivity_status": "OUTSIDE_TRAINING_FOOTPRINT",
                "model_coverage": "OUTSIDE_TRAINING_FOOTPRINT",
                "prediction_availability": "UNAVAILABLE_UNVALIDATED_REGION",
                "is_covered": False,
                "mineral": clean_min,
                "model_metadata": model.to_dict(),
                "reason": f"Target coordinates ({lat:.4f}°N, {lon:.4f}°E) lie outside the validated {model.training_footprint.get('region_name', 'training footprint')} ({model.training_footprint.get('tile_id', 'T44QMK')}). Regional extrapolation prohibited."
            }


# -----------------------------------------------------------------------------
# Default Registrations: Manganese (Tile T44QMK) + Explicit Non-Claims
# -----------------------------------------------------------------------------
_MANGANESE_MODEL = ValidatedProspectivityModel(
    mineral="Manganese",
    commodity_id="manganese",
    model_name="Sentinel-2 MSI Random Forest Manganese Classifier",
    training_footprint={
        "tile_id": "T44QMK",
        "region_name": "Balaghat-Nagpur-Bhandara Manganese Belt",
        "crs": "EPSG:32644 (UTM Zone 44N)",
        "bounds": {
            "min_lat": 21.4880,
            "max_lat": 22.4220,
            "min_lon": 79.7900,
            "max_lon": 80.7600
        },
        "center_coordinates": {"lat": 21.9455, "lon": 80.4295}
    },
    input_features=[
        "B02", "B03", "B04", "B08", "B11", "B12",
        "NDVI", "NDWI", "clay_ratio", "iron_oxide_ratio"
    ],
    data_provenance={
        "satellite_platform": "Copernicus Sentinel-2A MSI Level-2A BOA Surface Reflectance",
        "training_tile": "T44QMK",
        "scene_id": "S2A_MSIL2A_20260315_T44QMK",
        "ground_truth_source": "MOIL verified lease logs & GSI Sausar Group gondite publications",
        "known_deposits": ["Ghondi Manganese Mine", "Bharweli Deep Shaft", "Ukwa Stratiform Gondite"]
    },
    validation_results={
        "validation_methodology": "Spatial sector holdout cross-validation across mine corridor",
        "cross_validation_accuracy_pct": 89.2,
        "auc_roc": 0.912,
        "f1_score": 0.884,
        "validation_report_ref": "models/manganese_validation_report.json"
    },
    score_interpretation={
        "metric_name": "Relative Spatial Prospectivity Index",
        "scale": "0 to 100",
        "unit": "percent",
        "priority_tiers": {
            "High Priority": ">= 75.0%",
            "Moderate Priority": "50.0% - 74.9%",
            "Low Priority": "< 50.0%"
        },
        "scientific_caveats": (
            "Surface screening index derived from optical BOA reflectance and band ratios. "
            "Does not represent subsurface ore grade (% Mn), deposit thickness, or economic reserve feasibility."
        )
    },
    model_path="models/manganese_random_forest.pkl",
    has_validated_model=os.path.exists(os.path.join(os.path.dirname(os.path.abspath(__file__)), "models", "manganese_random_forest.pkl"))
)
ProspectivityModelRegistry.register_model(_MANGANESE_MODEL)

_COAL_FRAMEWORK = ValidatedProspectivityModel(
    mineral="Coal",
    commodity_id="coal",
    model_name="Gondwana Basin Coal Evidence Framework (Awaiting Subsurface Model)",
    training_footprint={
        "status": "UNVALIDATED_FOR_GEOGRAPHICAL_ML",
        "target_basins": "Gondwana Basins (Pranhita-Godavari, Damodar Valley, Son-Mahanadi)",
        "bounds": None
    },
    input_features=["SWIR1", "SWIR2", "Carbonaceous Shale Index", "DEM Subsidence Grabens"],
    data_provenance={
        "geological_records": "GSI / CMPDI / SCCL published colliery inventories",
        "subsurface_data_requirement": "Borehole core lithologs and seismic seam profiles required"
    },
    validation_results={
        "status": "AWAITING_GROUND_TRUTH_TRAINING",
        "spatial_validation": "NONE",
        "explanation": "Optical satellite reflectance cannot penetrate overburden to sense coal seams."
    },
    score_interpretation={
        "status": "PREDICTION_WITHHELD",
        "explanation": "Numerical AI prospectivity predictions are withheld until borehole logs are ingested."
    },
    model_path=None,
    has_validated_model=False
)
ProspectivityModelRegistry.register_model(_COAL_FRAMEWORK)

_IRON_ORE_FRAMEWORK = ValidatedProspectivityModel(
    mineral="Iron Ore",
    commodity_id="iron_ore",
    model_name="Singhbhum BIF Iron Ore Framework (Model Withheld Under Spatial Validation Deficit)",
    training_footprint={
        "status": "SPATIAL_VALIDATION_FAILED",
        "target_cratons": "Singhbhum-North Odisha Craton (Noamundi, Joda East, Kiriburu, Gua, Bolani)",
        "bounds": None
    },
    input_features=["B04/B02 Ferric Iron", "B11/B08 Ferrous Silicate", "B11/B12 Clay Halos", "Copernicus DEM 30m"],
    data_provenance={
        "geological_records": "GSI / IBM Singhbhum BIF occurrences & Tata Steel / SAIL mine locations",
        "geophysical_requirement": "GSI aeromagnetic tensor grids and chemical drill assays (% Fe > 62%) required"
    },
    validation_results={
        "status": "SPATIAL_VALIDATION_FAILED",
        "random_cv_accuracy_pct": 83.5,
        "spatially_blocked_cv_accuracy_pct": 47.7,
        "spatially_blocked_f1": 0.313,
        "diagnostic": "GENUINE_SPATIAL_GENERALIZATION_DEFICIT"
    },
    score_interpretation={
        "status": "PREDICTION_WITHHELD",
        "explanation": "Scores withheld due to tropical laterite confounding without subsurface assays or aeromagnetics."
    },
    model_path=None,
    has_validated_model=False
)
ProspectivityModelRegistry.register_model(_IRON_ORE_FRAMEWORK)

_BAUXITE_FRAMEWORK = ValidatedProspectivityModel(
    mineral="Bauxite",
    commodity_id="bauxite",
    model_name="East Coast & Central India Bauxite Plateau Framework (Awaiting Assays)",
    training_footprint={
        "status": "UNVALIDATED_FOR_GEOGRAPHICAL_ML",
        "target_provinces": "East Coast Bauxite & Central Indian Plateaus (Panchpatmali, Baphlimali, Amarkantak)",
        "bounds": None
    },
    input_features=["B11/B12 Al-OH Absorption", "Copernicus DEM Mesa Morphology (>900m ASL)"],
    data_provenance={
        "geological_records": "GSI / IBM / NALCO bauxite inventory",
        "geochemical_requirement": "XRF geochemical drill assays (Al2O3 >= 40%, SiO2 < 4%) required"
    },
    validation_results={
        "status": "AWAITING_GROUND_TRUTH_TRAINING",
        "spatial_validation": "NONE",
        "explanation": "Optical SWIR sensors detect Al-OH absorption, but cannot distinguish bauxite ore from barren laterite."
    },
    score_interpretation={
        "status": "PREDICTION_WITHHELD",
        "explanation": "Numerical AI prospectivity predictions are withheld until chemical assays are ingested."
    },
    model_path=None,
    has_validated_model=False
)
ProspectivityModelRegistry.register_model(_BAUXITE_FRAMEWORK)

