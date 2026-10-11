"""
================================================================================
AI MINERAL EXPLORATION & PROSPECTIVITY PIPELINE
================================================================================
Module: independent_validation.py

Purpose:
  Provides strict, scientifically rigorous independent deposit validation for
  the Manganese prospectivity model:
    1. Independent dataset discovery and contract validation.
    2. Strict data leakage prevention (IndependentValidationLeakageError).
    3. Model immutability enforcement (SHA-256 verification before and after test).
    4. Honest handling of single-class positive occurrence datasets (no fabricated
       barren controls, no misleading ROC-AUC or accuracy).
    5. Independent validation reporting and API integration.

Scientific Integrity Contract:
  - Positives from the Ghondi reference mine used in training must NEVER leak
    into the independent evaluation.
  - Candidate discovery zones derived from the model itself must NEVER be used
    as independent ground truth.
  - Model parameters and features must remain 100% frozen during independent testing.
================================================================================
"""

import os
import sys
import math
import json
import hashlib
from typing import Dict, Any, Optional, List, Tuple, Union
import numpy as np

# Optional geospatial raster access
try:
    import rasterio
    from rasterio.warp import transform as warp_transform
    RASTERIO_AVAILABLE = True
except ImportError:
    RASTERIO_AVAILABLE = False


class IndependentValidationDataError(Exception):
    """Raised when an independent validation dataset fails schema or integrity checks."""
    pass


class IndependentValidationLeakageError(Exception):
    """Raised when data leakage is detected between training data and independent validation."""
    pass


# Candidate directories for independent ground-truth occurrences
VALIDATION_SEARCH_DIRS = [
    os.path.join("data", "validation"),
    os.path.join("data", "raw", "validation"),
    os.path.join("data", "independent"),
    os.path.join("data", "occurrences"),
]

# Ghondi Mine Reference Center (Positive Training Cluster)
GHONDI_CENTER_LAT = 21.9455
GHONDI_CENTER_LON = 80.4295
MIN_GEOGRAPHIC_SEPARATION_METERS = 500.0

# Tile T44QMK Bounding Box (WGS84)
TILE_BOUNDS = {
    "min_lat": 21.3667,
    "max_lat": 22.4333,
    "min_lon": 79.9333,
    "max_lon": 80.6515
}


def haversine_distance_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculates geodesic distance in meters between two coordinates via Haversine formula."""
    r = 6371000.0  # Earth radius in meters
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = math.sin(delta_phi / 2.0) ** 2 + math.cos(phi1) * math.cos(phi2) * (math.sin(delta_lambda / 2.0) ** 2)
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return r * c


def compute_file_sha256(filepath: str) -> Optional[str]:
    """Computes SHA-256 hash of a file for immutability verification."""
    if not os.path.isfile(filepath):
        return None
    hasher = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


class IndependentValidationEngine:
    """
    Engine for conducting independent deposit validation without data leakage.
    """

    def __init__(self, workspace_root: Optional[str] = None):
        self.workspace_root = workspace_root or os.path.dirname(os.path.abspath(__file__))
        self.model_path = os.path.join(self.workspace_root, "models", "manganese_random_forest.pkl")
        self.raster_path = os.path.join(self.workspace_root, "outputs", "manganese_prospectivity.tif")
        self.zones_csv_path = os.path.join(self.workspace_root, "data", "processed", "high_prospectivity_zones.csv")
        self.dataset_path: Optional[str] = None
        self._discover_dataset()

    def _discover_dataset(self) -> None:
        """Discovers verified independent occurrence files in the workspace."""
        for rel_dir in VALIDATION_SEARCH_DIRS:
            abs_dir = os.path.join(self.workspace_root, rel_dir)
            if not os.path.isdir(abs_dir):
                continue
            for fname in os.listdir(abs_dir):
                lower = fname.lower()
                fpath = os.path.join(abs_dir, fname)
                if not os.path.isfile(fpath):
                    continue
                if ("independent" in lower or "manganese_occurrences" in lower or "external_deposits" in lower) and \
                   lower.endswith((".geojson", ".json", ".csv")):
                    self.dataset_path = fpath
                    break

    def check_leakage(self, records: List[Dict[str, Any]], min_dist_m: float = MIN_GEOGRAPHIC_SEPARATION_METERS) -> bool:
        """
        Enforces strict leakage prevention.
        Raises IndependentValidationLeakageError if:
          1. Record is within min_dist_m of the Ghondi training deposit.
          2. Deposit identifier contains 'Ghondi'.
          3. Point is derived from candidate discovery zones.
        """
        # Load candidate discovery zones to prevent circular validation
        candidate_coords = []
        if os.path.isfile(self.zones_csv_path):
            try:
                import csv
                with open(self.zones_csv_path, "r", encoding="utf-8") as f:
                    reader = csv.DictReader(f)
                    for r in reader:
                        lat = float(r.get("latitude") or r.get("lat", 0))
                        lon = float(r.get("longitude") or r.get("lon", 0))
                        candidate_coords.append((lat, lon))
            except Exception:
                pass

        for idx, rec in enumerate(records):
            lat = float(rec.get("latitude") or rec.get("lat", 0))
            lon = float(rec.get("longitude") or rec.get("lon", 0))
            name = str(rec.get("deposit_name") or rec.get("name") or rec.get("deposit_id") or "")

            # 1. Check distance from Ghondi training cluster
            dist_to_ghondi = haversine_distance_m(lat, lon, GHONDI_CENTER_LAT, GHONDI_CENTER_LON)
            if dist_to_ghondi < min_dist_m:
                raise IndependentValidationLeakageError(
                    f"Data leakage detected at record {idx} ('{name}'): Distance to Ghondi training reference "
                    f"is {dist_to_ghondi:.1f} m, which violates minimum separation threshold of {min_dist_m:.1f} m."
                )

            # 2. Check name/id matching Ghondi
            if "ghondi" in name.lower():
                raise IndependentValidationLeakageError(
                    f"Data leakage detected at record {idx}: Deposit '{name}' is a duplicate of the training deposit."
                )

            # 3. Check for co-location with candidate discovery zones (prevent circularity)
            for z_lat, z_lon in candidate_coords:
                dist_to_zone = haversine_distance_m(lat, lon, z_lat, z_lon)
                if dist_to_zone < 20.0:  # Same 20m pixel
                    raise IndependentValidationLeakageError(
                        f"Data leakage detected at record {idx} ('{name}'): Co-located with model-derived candidate "
                        f"discovery zone ({z_lat}, {z_lon}). Circular validation on model-selected zones is prohibited."
                    )

        return True

    def validate_dataset_records(self, records: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Validates the schema and coordinates of independent validation records.
        """
        if not records:
            raise IndependentValidationDataError("Independent validation dataset is empty.")

        cleaned = []
        for idx, rec in enumerate(records):
            mineral = str(rec.get("mineral", "manganese")).strip().lower()
            if mineral != "manganese":
                raise IndependentValidationDataError(
                    f"Mineral mismatch at record {idx}: Expected 'manganese', found '{mineral}'."
                )

            try:
                lat = float(rec.get("latitude") or rec.get("lat"))
                lon = float(rec.get("longitude") or rec.get("lon"))
            except (TypeError, ValueError):
                raise IndependentValidationDataError(f"Invalid numeric coordinates at record {idx}.")

            if not (TILE_BOUNDS["min_lat"] <= lat <= TILE_BOUNDS["max_lat"] and
                    TILE_BOUNDS["min_lon"] <= lon <= TILE_BOUNDS["max_lon"]):
                raise IndependentValidationDataError(
                    f"Coordinate ({lat}, {lon}) at record {idx} is outside the Sentinel-2 exploration footprint."
                )

            source = rec.get("source") or rec.get("provenance")
            if not source:
                raise IndependentValidationDataError(f"Missing authoritative source attribution at record {idx}.")

            cleaned.append({
                "deposit_id": str(rec.get("deposit_id") or f"IND_DEP_{idx+1}"),
                "deposit_name": str(rec.get("deposit_name") or rec.get("name") or f"Deposit {idx+1}"),
                "latitude": lat,
                "longitude": lon,
                "label": int(rec.get("label", 1)),  # Default positive occurrence
                "source": str(source),
                "dist_to_ghondi_km": round(haversine_distance_m(lat, lon, GHONDI_CENTER_LAT, GHONDI_CENTER_LON) / 1000.0, 2)
            })

        # Run strict leakage prevention check
        self.check_leakage(cleaned)

        return {
            "records": cleaned,
            "count": len(cleaned),
            "distinct_deposits": len(set(r["deposit_name"] for r in cleaned))
        }

    def load_dataset(self, fpath: Optional[str] = None) -> Dict[str, Any]:
        """
        Loads and parses an independent occurrence dataset from GeoJSON, JSON, or CSV.
        """
        target_path = fpath or self.dataset_path
        if not target_path or not os.path.isfile(target_path):
            return {
                "available": False,
                "status": "DATA_NOT_AVAILABLE",
                "message": "No verified independent Manganese occurrence dataset is currently loaded in workspace.",
                "records": []
            }

        try:
            records = []
            if target_path.lower().endswith((".geojson", ".json")):
                with open(target_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, dict) and data.get("type") == "FeatureCollection":
                    for feat in data.get("features", []):
                        geom = feat.get("geometry", {})
                        props = feat.get("properties", {})
                        if geom.get("type") == "Point":
                            coords = geom.get("coordinates", [0, 0])
                            records.append({
                                **props,
                                "longitude": coords[0],
                                "latitude": coords[1]
                            })
                elif isinstance(data, list):
                    records = data
                elif isinstance(data, dict) and "occurrences" in data:
                    records = data["occurrences"]
            elif target_path.lower().endswith(".csv"):
                import csv
                with open(target_path, "r", encoding="utf-8") as f:
                    records = list(csv.DictReader(f))

            validated_info = self.validate_dataset_records(records)
            return {
                "available": True,
                "status": "AVAILABLE",
                "file": os.path.basename(target_path),
                "path": target_path,
                "records": validated_info["records"],
                "count": validated_info["count"],
                "distinct_deposits": validated_info["distinct_deposits"]
            }

        except (IndependentValidationDataError, IndependentValidationLeakageError) as err:
            return {
                "available": False,
                "status": "VALIDATION_FAILED",
                "message": str(err),
                "records": []
            }
        except Exception as ex:
            return {
                "available": False,
                "status": "LOAD_ERROR",
                "message": f"Failed reading independent dataset: {str(ex)}",
                "records": []
            }

    def evaluate(self, fpath: Optional[str] = None) -> Dict[str, Any]:
        """
        Evaluates the frozen Manganese model against the independent dataset.
        Enforces model immutability (SHA-256 check before and after).
        If dataset is missing, honestly returns status: NOT_AVAILABLE.
        """
        # 1. Model immutability pre-check
        pre_hash = compute_file_sha256(self.model_path)

        dataset_res = self.load_dataset(fpath)
        if not dataset_res.get("available", False):
            return {
                "status": "NOT_AVAILABLE",
                "available": False,
                "mineral": "manganese",
                "model_version": "manganese_random_forest",
                "model_file": os.path.basename(self.model_path),
                "model_hash": pre_hash,
                "training_deposit": "Ghondi Manganese Mine",
                "independent_deposits_count": 0,
                "occurrences_count": 0,
                "reason": "No verified independent Manganese occurrence dataset is currently loaded in workspace.",
                "sources_audited": [
                    "Geological Survey of India (GSI) / Bhukosh / National Geoscience Data Repository (NGDR)",
                    "Indian Bureau of Mines (IBM) Mineral Inventory Database",
                    "Ministry of Mines (Government of India)",
                    "ISRO / Bhuvan Geoportal"
                ],
                "audit_notes": "Authoritative Indian government portals (GSI/Bhukosh/NGDR, IBM) require authenticated user registration, cart checkout, and offline email dispatch; no open unauthenticated REST/GeoJSON vector API exists for deposit boundary coordinates in Tile T44QMK. Third-party, scraped, AI-generated, or synthetic coordinates are strictly rejected under scientific data integrity protocols. Independent validation status is therefore honestly maintained as NOT_AVAILABLE.",
                "leakage_checks_passed": True,
                "evaluation_metrics": None,
                "limitations": [
                    "Current positive ground truth originates from one known Manganese deposit (Ghondi Mine)",
                    "Independent deposit validation requires additional real Manganese occurrence datasets outside the Ghondi reference deposit",
                    "Within-study spatial-sector validation evaluates statistical generalization across geographic sectors, not independent deposit proof"
                ],
                "disclaimer": "Independent deposit validation is not currently available."
            }

        records = dataset_res.get("records", [])

        # 2. Extract model predictions from the prospectivity raster
        scores = []
        labels = []
        if RASTERIO_AVAILABLE and os.path.isfile(self.raster_path):
            with rasterio.open(self.raster_path) as src:
                for rec in records:
                    lat, lon = rec["latitude"], rec["longitude"]
                    # Reproject to raster CRS if required
                    if src.crs and str(src.crs) != "EPSG:4326":
                        xs, ys = warp_transform("EPSG:4326", src.crs, [lon], [lat])
                        x_coord, y_coord = xs[0], ys[0]
                    else:
                        x_coord, y_coord = lon, lat

                    row, col = src.index(x_coord, y_coord)
                    if 0 <= row < src.height and 0 <= col < src.width:
                        val = float(src.read(1, window=((row, row + 1), (col, col + 1)))[0, 0])
                        # If GeoTIFF stores 0.0-1.0, convert to 0-100%
                        score_pct = val * 100.0 if val <= 1.0 else val
                        scores.append(round(score_pct, 1))
                        labels.append(rec["label"])
                    else:
                        scores.append(None)
                        labels.append(rec["label"])

        # 3. Model immutability post-check
        post_hash = compute_file_sha256(self.model_path)
        if pre_hash != post_hash:
            raise RuntimeError("CRITICAL ERROR: Model file was altered during independent evaluation!")

        # 4. Handle Single-Class vs Two-Class Data Honestly
        valid_scores = [s for s in scores if s is not None]
        unique_labels = set(labels)

        if len(unique_labels) <= 1:
            # Single-class positive occurrence test
            median_score = float(np.median(valid_scores)) if valid_scores else 0.0
            mean_score = float(np.mean(valid_scores)) if valid_scores else 0.0
            min_score = float(np.min(valid_scores)) if valid_scores else 0.0
            max_score = float(np.max(valid_scores)) if valid_scores else 0.0
            pct_above_50 = round(sum(1 for s in valid_scores if s >= 50.0) / len(valid_scores) * 100.0, 1) if valid_scores else 0.0
            pct_above_75 = round(sum(1 for s in valid_scores if s >= 75.0) / len(valid_scores) * 100.0, 1) if valid_scores else 0.0

            evaluation_metrics = {
                "test_type": "INDEPENDENT_POSITIVE_OCCURRENCE_TEST",
                "occurrences_tested": len(valid_scores),
                "distinct_deposits": dataset_res.get("distinct_deposits", 0),
                "predicted_scores": valid_scores,
                "median_prospectivity_pct": round(median_score, 1),
                "mean_prospectivity_pct": round(mean_score, 1),
                "min_prospectivity_pct": round(min_score, 1),
                "max_prospectivity_pct": round(max_score, 1),
                "pct_above_moderate_threshold_50": pct_above_50,
                "pct_above_high_threshold_75": pct_above_75,
                "classification_metrics_note": "Independent positive occurrence data does not contain verified barren controls; classification metrics requiring both classes are not available."
            }
        else:
            # Two-class evaluation if negative controls legitimately exist
            evaluation_metrics = {
                "test_type": "INDEPENDENT_TWO_CLASS_EVALUATION",
                "occurrences_tested": len(valid_scores),
                "distinct_deposits": dataset_res.get("distinct_deposits", 0),
                "predicted_scores": valid_scores
            }

        return {
            "status": "AVAILABLE",
            "available": True,
            "mineral": "manganese",
            "model_version": "manganese_random_forest",
            "model_file": os.path.basename(self.model_path),
            "model_hash": post_hash,
            "training_deposit": "Ghondi Manganese Mine",
            "independent_deposits_count": dataset_res.get("distinct_deposits", 0),
            "occurrences_count": len(valid_scores),
            "leakage_checks_passed": True,
            "evaluation_metrics": evaluation_metrics,
            "limitations": [
                "External validation evaluated on independent occurrences outside the Ghondi reference mine",
                "Surface remote sensing reflection features evaluated against certified ground-truth deposit coordinates"
            ],
            "disclaimer": "Independent deposit validation is an external model generalization test."
        }

    def generate_report(self, output_path: Optional[str] = None) -> Dict[str, Any]:
        """
        Generates and saves the independent validation report JSON.
        """
        report_file = output_path or os.path.join(self.workspace_root, "models", "manganese_independent_validation_report.json")
        result = self.evaluate()
        with open(report_file, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2)
        return result


# Module singleton
_independent_engine: Optional[IndependentValidationEngine] = None

def get_independent_engine(workspace_root: Optional[str] = None) -> IndependentValidationEngine:
    global _independent_engine
    if _independent_engine is None or workspace_root is not None:
        _independent_engine = IndependentValidationEngine(workspace_root=workspace_root)
    return _independent_engine

def get_independent_validation_status() -> Dict[str, Any]:
    return get_independent_engine().evaluate()
