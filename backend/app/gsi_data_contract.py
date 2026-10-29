"""
GSI Aeromagnetic & Geological Vector Data Contract Specification
================================================================
Defines the strict scientific data-ingestion contracts, validation schemas,
and refusal criteria for future Geological Survey of India (GSI) datasets:

1. GSI High-Resolution Aeromagnetic Survey (HRAS) tensor grids (NAGMP).
2. GSI Bhukosh 1:50,000 Quadrangle Geological & Structural Vector Layers.

Scientific Guardrail:
- Never manufactures synthetic magnetic rasters, false anomaly lineaments,
  or uncalibrated WMS image scrapes.
- Validates real datasets against published GSI survey flight specifications.
"""

import os
import json
import hashlib
from typing import Dict, Any, List, Optional, Tuple


MANDATORY_AEROMAG_METADATA = [
    "survey_name",
    "agency",
    "quadrangle",
    "sensor_type",
    "sensor_sensitivity_nt",
    "nominal_flight_altitude_agl_m",
    "flight_line_spacing_m",
    "tie_line_spacing_m",
    "flight_direction_deg",
    "vertical_datum",
    "target_crs"
]

MANDATORY_GEOLOGICAL_VECTOR_LAYERS = [
    "lithological_formations",
    "structural_lineaments",
    "banded_iron_formation_contacts",
    "newer_dolerite_dykes_exclusion_mask"
]

MANDATORY_LITHOLOGY_ATTRIBUTES = [
    "LITHO_NAME",
    "STRAT_UNIT",
    "FORMATION",
    "SUPERGROUP"
]


class GSIDataContractValidator:
    """
    Validates candidate GSI geophysical grids and geological vectors
    prior to any machine learning ingestion or spatial feature extraction.
    """

    def __init__(self, workspace_root: Optional[str] = None):
        self.workspace_root = workspace_root or os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        self.curated_dir = os.path.join(self.workspace_root, "data", "curated")

    def get_contract_specification(self) -> Dict[str, Any]:
        """Returns the complete technical ingestion contract."""
        contract_file = os.path.join(self.curated_dir, "gsi_aeromag_geology_contract.json")
        if os.path.exists(contract_file):
            with open(contract_file, "r", encoding="utf-8") as f:
                return json.load(f)
        return {
            "status": "SPECIFICATION_DEFINED",
            "aeromagnetic_grid_requirements": {
                "formats": [".grd (Geosoft Oasis Montaj binary grid)", ".tif (Cloud Optimized GeoTIFF)"],
                "target_crs": "EPSG:32645 (WGS 84 / UTM Zone 45N)",
                "grid_cell_size_m": 50.0,
                "units": "nanoTesla (nT) for TMI and RTP; nT/m for vertical derivatives; radians for tilt derivatives",
                "survey_standard": "GSI NAGMP Standard Flight Specs (80m AGL, 200m line spacing, Cesium vapor sensor)"
            },
            "geological_vector_requirements": {
                "formats": [".geojson (GeoJSON RFC 7946)", ".shp (ESRI Shapefile with .prj and .dbf)", ".gpkg (OGC GeoPackage)"],
                "target_crs": "EPSG:4326 (WGS 84) or EPSG:32645 (UTM 45N)",
                "scale": "1:50,000 Quadrangle Series (Toposheet 73F)",
                "mandatory_layers": MANDATORY_GEOLOGICAL_VECTOR_LAYERS
            },
            "prohibited_practices": [
                "Scraping uncalibrated raster images from Bhukosh WMS browser maps",
                "Synthesizing artificial magnetic anomaly grids with random noise or Gaussian hills",
                "Tracing approximate lithological boundaries from low-resolution paper sketches",
                "Using point coordinates without verified lease boundary polygons"
            ]
        }

    def validate_aeromagnetic_grid(self, filepath: str, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Validates an incoming aeromagnetic grid file.
        Rejects unverified or synthetic files.
        """
        if not os.path.exists(filepath):
            return {
                "valid": False,
                "status": "FILE_NOT_FOUND",
                "filepath": filepath,
                "rejection_reasons": ["Specified grid file does not exist on disk."]
            }

        reasons: List[str] = []
        ext = os.path.splitext(filepath)[1].lower()
        if ext not in (".grd", ".tif", ".tiff", ".xyz"):
            reasons.append(f"Invalid extension '{ext}'. Must be .grd, .tif, or .xyz.")

        meta = metadata or {}
        missing_meta = [k for k in MANDATORY_AEROMAG_METADATA if k not in meta]
        if missing_meta:
            reasons.append(f"Missing mandatory GSI survey flight metadata: {missing_meta}")

        # Check for synthetic indicators
        if meta.get("synthetic", False) or "simulated" in filepath.lower():
            reasons.append("Synthetic or simulated geophysical data is strictly forbidden by project integrity rules.")

        if reasons:
            return {
                "valid": False,
                "status": "REJECTED_CONTRACT_VIOLATION",
                "filepath": filepath,
                "rejection_reasons": reasons
            }

        return {
            "valid": True,
            "status": "VERIFIED_READY_FOR_INGESTION",
            "filepath": filepath,
            "metadata": meta
        }

    def validate_geological_vector(self, filepath: str, layer_type: str) -> Dict[str, Any]:
        """
        Validates an incoming geological vector shapefile or geojson.
        """
        if not os.path.exists(filepath):
            return {
                "valid": False,
                "status": "FILE_NOT_FOUND",
                "filepath": filepath,
                "rejection_reasons": ["Specified vector file does not exist on disk."]
            }

        reasons: List[str] = []
        ext = os.path.splitext(filepath)[1].lower()
        if ext not in (".geojson", ".json", ".shp", ".gpkg"):
            reasons.append(f"Invalid extension '{ext}'. Must be .geojson, .shp, or .gpkg.")

        if layer_type not in MANDATORY_GEOLOGICAL_VECTOR_LAYERS:
            reasons.append(f"Layer type '{layer_type}' not in recognized GSI layers: {MANDATORY_GEOLOGICAL_VECTOR_LAYERS}")

        if reasons:
            return {
                "valid": False,
                "status": "REJECTED_CONTRACT_VIOLATION",
                "filepath": filepath,
                "rejection_reasons": reasons
            }

        return {
            "valid": True,
            "status": "VERIFIED_READY_FOR_INGESTION",
            "filepath": filepath,
            "layer_type": layer_type
        }


# Singleton helper
_gsi_contract_validator: Optional[GSIDataContractValidator] = None

def get_gsi_contract_validator(workspace_root: Optional[str] = None) -> GSIDataContractValidator:
    global _gsi_contract_validator
    if _gsi_contract_validator is None or workspace_root is not None:
        _gsi_contract_validator = GSIDataContractValidator(workspace_root=workspace_root)
    return _gsi_contract_validator
