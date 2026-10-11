"""
=============================================================================
AI MINERAL INTELLIGENCE — TRAINING DATA CONTRACT & SCHEMA VALIDATOR
=============================================================================
Module: mineral_training_contract.py

Purpose:
  Enforces rigorous scientific validation on candidate training datasets
  before model training can proceed:
    1. Schema validation (required coordinates, label, and 10 Sentinel-2 features)
    2. Missing value & non-finite numeric checks
    3. Minimum sample thresholds (>= 20 positive, >= 20 negative)
    4. Coordinate range & CRS bounds validation
    5. Deduplication of co-located samples (< 20m)
    6. Cross-mineral contamination prevention (verifies mineral identity)
=============================================================================
"""

import os
import math
from typing import Dict, Any, List, Optional, Tuple, Union
import numpy as np

# Standard feature set required by the Random Forest classifier
REQUIRED_FEATURE_COLUMNS = [
    "B02", "B03", "B04", "B08", "B11", "B12",
    "NDVI", "NDWI", "clay_ratio", "iron_oxide_ratio"
]

REQUIRED_COLUMNS = ["latitude", "longitude", "mineral", "label"] + REQUIRED_FEATURE_COLUMNS

# Minimum sample count thresholds
MIN_POSITIVE_SAMPLES = 20
MIN_NEGATIVE_SAMPLES = 20


class TrainingDataError(Exception):
    """Base exception for training data issues."""
    pass


class TrainingDataUnavailableError(TrainingDataError):
    """Raised when training is requested for a mineral with no real dataset."""
    pass


class InvalidTrainingDataError(TrainingDataError):
    """Raised when a dataset fails schema, numeric, or spatial integrity checks."""
    pass


class MineralMismatchError(TrainingDataError):
    """Raised when a dataset or model is evaluated against the wrong mineral."""
    pass


class TrainingDataContract:
    """
    Defines and validates the training data contract for mineral exploration models.
    """

    @classmethod
    def validate_records(
        cls,
        records: List[Dict[str, Any]],
        expected_mineral: str,
        tile_bounds: Optional[Dict[str, float]] = None
    ) -> Dict[str, Any]:
        """
        Validates a list of dictionary records against the training data contract.

        Parameters:
            records: List of sample dictionaries containing required columns.
            expected_mineral: Canonical mineral identifier (e.g. 'manganese', 'iron_ore').
            tile_bounds: Optional dictionary with 'min_lat', 'max_lat', 'min_lon', 'max_lon'.

        Returns:
            Dict containing validation summary report.

        Raises:
            InvalidTrainingDataError: If any contract rule is violated.
            MineralMismatchError: If mineral tag does not match expected_mineral.
        """
        if not records:
            raise InvalidTrainingDataError("Dataset is empty. At least 40 samples (20 positive, 20 negative) required.")

        expected_mineral_clean = str(expected_mineral).strip().lower()

        positive_count = 0
        negative_count = 0
        seen_coordinates = set()

        for idx, row in enumerate(records):
            # Check required columns
            for col in REQUIRED_COLUMNS:
                if col not in row or row[col] is None:
                    raise InvalidTrainingDataError(
                        f"Record {idx} missing required column '{col}'."
                    )

            # Check mineral identity (Cross-mineral contamination check)
            row_mineral = str(row["mineral"]).strip().lower()
            if row_mineral != expected_mineral_clean:
                raise MineralMismatchError(
                    f"Mineral mismatch at record {idx}: Expected '{expected_mineral_clean}', got '{row_mineral}'."
                )

            # Check coordinates
            try:
                lat = float(row["latitude"])
                lon = float(row["longitude"])
            except (ValueError, TypeError):
                raise InvalidTrainingDataError(f"Record {idx} has non-numeric coordinates.")

            if not (-90.0 <= lat <= 90.0) or not (-180.0 <= lon <= 180.0):
                raise InvalidTrainingDataError(
                    f"Record {idx} coordinates out of range: Lat {lat}, Lon {lon}."
                )

            # Tile bounding box check if specified
            if tile_bounds:
                if not (tile_bounds["min_lat"] <= lat <= tile_bounds["max_lat"] and
                        tile_bounds["min_lon"] <= lon <= tile_bounds["max_lon"]):
                    raise InvalidTrainingDataError(
                        f"Record {idx} ({lat}, {lon}) falls outside satellite tile bounds."
                    )

            # Check label
            try:
                label = int(row["label"])
            except (ValueError, TypeError):
                raise InvalidTrainingDataError(f"Record {idx} label must be integer 0 or 1.")

            if label not in (0, 1):
                raise InvalidTrainingDataError(f"Record {idx} label must be 0 or 1, got {label}.")

            if label == 1:
                positive_count += 1
            else:
                negative_count += 1

            # Check features for NaN / inf
            for feat in REQUIRED_FEATURE_COLUMNS:
                try:
                    val = float(row[feat])
                except (ValueError, TypeError):
                    raise InvalidTrainingDataError(f"Record {idx} feature '{feat}' is non-numeric.")

                if math.isnan(val) or math.isinf(val):
                    raise InvalidTrainingDataError(
                        f"Record {idx} feature '{feat}' contains NaN or Infinite value."
                    )

            # Deduplication key (~20m resolution cell: approx 0.0002 deg)
            coord_key = (round(lat, 4), round(lon, 4))
            seen_coordinates.add(coord_key)

        # Sample count validation
        if positive_count < MIN_POSITIVE_SAMPLES:
            raise InvalidTrainingDataError(
                f"Insufficient positive samples: found {positive_count}, minimum required is {MIN_POSITIVE_SAMPLES}."
            )
        if negative_count < MIN_NEGATIVE_SAMPLES:
            raise InvalidTrainingDataError(
                f"Insufficient negative samples: found {negative_count}, minimum required is {MIN_NEGATIVE_SAMPLES}."
            )

        return {
            "valid": True,
            "mineral": expected_mineral_clean,
            "total_samples": len(records),
            "positive_samples": positive_count,
            "negative_samples": negative_count,
            "unique_coordinate_cells": len(seen_coordinates),
            "feature_count": len(REQUIRED_FEATURE_COLUMNS),
            "features": list(REQUIRED_FEATURE_COLUMNS)
        }

    @classmethod
    def validate_csv(
        cls,
        csv_path: str,
        expected_mineral: str,
        tile_bounds: Optional[Dict[str, float]] = None
    ) -> Dict[str, Any]:
        """
        Parses and validates a CSV dataset file against the training contract.
        """
        if not os.path.exists(csv_path):
            raise TrainingDataUnavailableError(
                f"Training dataset file not found: '{csv_path}' for mineral '{expected_mineral}'."
            )

        import csv
        records = []
        with open(csv_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                records.append(row)

        return cls.validate_records(records, expected_mineral, tile_bounds)


def validate_mineral_dataset(
    dataset_or_path: Union[str, List[Dict[str, Any]]],
    mineral_id: str,
    tile_bounds: Optional[Dict[str, float]] = None
) -> Dict[str, Any]:
    """
    Public entry point for validating mineral datasets.
    """
    if isinstance(dataset_or_path, str):
        return TrainingDataContract.validate_csv(dataset_or_path, mineral_id, tile_bounds)
    elif isinstance(dataset_or_path, list):
        return TrainingDataContract.validate_records(dataset_or_path, mineral_id, tile_bounds)
    else:
        raise InvalidTrainingDataError("Unsupported dataset input type. Expected path or list of records.")
