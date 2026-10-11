"""
================================================================================
AI MINERAL EXPLORATION & PROSPECTIVITY PIPELINE
================================================================================
Core Engine: mineral_prospectivity_pipeline.py

Pipeline Steps:
  1. GeoTIFF input & path resolution
  2. Raster validation (CRS, bounds, transform, data types, nodata check)
  3. Coordinate/location handling (WGS84 lat/lon <-> UTM Zone 44N EPSG:32644)
  4. Target-area window extraction (radial circular buffer & rectangular bounds)
  5. Prospectivity score calculation (center pixel & radial statistics)
  6. Mineral potential classification (Very Low / Low / Moderate / High / Very High)
  7. Proximity search to verified candidate zones
  8. Results generation (Structured dictionary, JSON, ASCII table)
  9. Error handling with custom diagnostic exception hierarchy
  10. Built-in optional HTTP API server for web integration (/api/analyze, /api/health)
================================================================================
"""

import os
import sys
import math
import json
import argparse
from typing import Dict, Any, Optional, Tuple, List, Union
import numpy as np
from spectral_ratio_module import SpectralRatioModule, SpectralRatioError
from mineral_training_contract import MineralMismatchError, TrainingDataUnavailableError
from mineral_registry import MineralRegistry, MineralStatus
from geological_evidence import get_geology_engine
from terrain_evidence import get_terrain_engine
from independent_validation import get_independent_engine

# Ensure rasterio is available or provide informative diagnostic
RASTERIO_IMPORT_ERROR: Optional[str] = None
try:
    import rasterio
    import rasterio.io
    from rasterio.windows import from_bounds, Window
    from rasterio.warp import transform as warp_transform
    RASTERIO_AVAILABLE = True
except ImportError as e:
    RASTERIO_AVAILABLE = False
    RASTERIO_IMPORT_ERROR = str(e)
    class _RasterioStub:
        @staticmethod
        def open(*args: Any, **kwargs: Any) -> Any:
            pass
    rasterio = _RasterioStub()  # type: ignore
    class _WindowStub:
        col_off: float = 0.0
        row_off: float = 0.0
        width: float = 0.0
        height: float = 0.0
        def __init__(self, col_off: float = 0, row_off: float = 0, width: float = 0, height: float = 0) -> None:
            self.col_off = col_off
            self.row_off = row_off
            self.width = width
            self.height = height
    Window = _WindowStub  # type: ignore
    def from_bounds(*args: Any, **kwargs: Any) -> Any:
        return _WindowStub()
    def warp_transform(*args: Any, **kwargs: Any) -> Any:
        return ([], [])





# ==============================================================================
# CUSTOM DIAGNOSTIC EXCEPTIONS
# ==============================================================================

class PipelineError(Exception):
    """Base exception for AI Mineral Prospectivity Pipeline."""
    pass

class RasterNotFoundError(PipelineError):
    """Raised when the specified GeoTIFF file does not exist on disk."""
    pass

class InvalidCoordinateError(PipelineError):
    """Raised when coordinates are non-numeric, malformed, or mathematically out of range."""
    pass

class CRSMismatchError(PipelineError):
    """Raised when the raster coordinate reference system does not match expectations."""
    pass

class OutOfBoundsError(PipelineError):
    """Raised when the requested target coordinate lies outside the raster coverage."""
    pass

class NoDataError(PipelineError):
    """Raised when the target coordinate falls on a masked or NoData pixel."""
    pass

class MissingDependencyError(PipelineError):
    """Raised when required geospatial packages are not installed or blocked."""
    pass


# ==============================================================================
# PIPELINE IMPLEMENTATION CLASS
# ==============================================================================

class ProspectivityPipeline:
    """
    Authoritative AI Mineral Exploration Pipeline for Sentinel-2 satellite
    manganese prospectivity analysis.
    """

    EXPECTED_CRS = "EPSG:32644"  # WGS 84 / UTM Zone 44N

    def __init__(self, tif_path: Optional[str] = None):
        """
        Initializes pipeline with path to authoritative GeoTIFF prospectivity map.
        Resolves robustly relative to repository root if not specified.
        """
        if not RASTERIO_AVAILABLE:
            raise MissingDependencyError(
                f"Rasterio is required but failed to import: {RASTERIO_IMPORT_ERROR}. "
                "Ensure rasterio and its GDAL C-libraries are installed."
            )

        self.project_root = self._detect_project_root()
        
        if tif_path:
            self.tif_path = os.path.abspath(tif_path)
        else:
            self.tif_path = os.path.join(self.project_root, "outputs", "manganese_prospectivity.tif")

        self.zones_csv_path = os.path.join(self.project_root, "outputs", "high_prospectivity_zones.csv")
        if not os.path.exists(self.zones_csv_path):
            alt_path = os.path.join(self.project_root, "data", "processed", "high_prospectivity_zones.csv")
            if os.path.exists(alt_path):
                self.zones_csv_path = alt_path
        self._candidate_zones: Optional[List[Dict[str, Any]]] = None
        self.spectral_module = SpectralRatioModule(project_root=self.project_root)

    def _detect_project_root(self) -> str:
        """Determines the workspace root regardless of current working directory."""
        current_file_dir = os.path.dirname(os.path.abspath(__file__))
        if os.path.exists(os.path.join(current_file_dir, "outputs", "manganese_prospectivity.tif")):
            return current_file_dir
        parent_dir = os.path.dirname(current_file_dir)
        if os.path.exists(os.path.join(parent_dir, "outputs", "manganese_prospectivity.tif")):
            return parent_dir
        return os.getcwd()

    # --------------------------------------------------------------------------
    # STEP 1 & 2: RASTER VALIDATION
    # --------------------------------------------------------------------------
    def validate_raster(self) -> Dict[str, Any]:
        """
        Validates GeoTIFF integrity, spatial dimensions, CRS, and transform.
        """
        if not os.path.exists(self.tif_path):
            raise RasterNotFoundError(
                f"Authoritative GeoTIFF file not found at: {self.tif_path}\n"
                "Please verify that outputs/manganese_prospectivity.tif exists in the project."
            )

        try:
            with rasterio.open(self.tif_path) as src:
                crs_str = str(src.crs) if src.crs else "Unknown"
                
                # Check CRS compatibility
                is_utm44n = ("32644" in crs_str) or (src.crs and src.crs.to_epsg() == 32644)
                if not is_utm44n:
                    raise CRSMismatchError(
                        f"Expected CRS EPSG:32644 (UTM Zone 44N), but raster has: {crs_str}"
                    )

                validation_info = {
                    "valid": True,
                    "path": self.tif_path,
                    "file_size_bytes": os.path.getsize(self.tif_path),
                    "crs": crs_str,
                    "epsg": src.crs.to_epsg() if src.crs else None,
                    "width": src.width,
                    "height": src.height,
                    "count": src.count,
                    "dtypes": [str(d) for d in src.dtypes],
                    "nodata": src.nodata,
                    "bounds": {
                        "left": float(src.bounds.left),
                        "bottom": float(src.bounds.bottom),
                        "right": float(src.bounds.right),
                        "top": float(src.bounds.top),
                    },
                    "transform": [float(x) for x in src.transform][:6],
                    "pixel_size_x": float(src.transform.a),
                    "pixel_size_y": float(-src.transform.e),
                    "driver": src.driver,
                }
                return validation_info
        except Exception as e:
            if isinstance(e, PipelineError):
                raise
            raise PipelineError(f"Failed to read or validate GeoTIFF: {str(e)}")

    # --------------------------------------------------------------------------
    # STEP 3: COORDINATE & LOCATION HANDLING
    # --------------------------------------------------------------------------
    def parse_and_transform_coordinates(
        self,
        lat: Optional[Union[float, str]] = None,
        lon: Optional[Union[float, str]] = None,
        easting: Optional[Union[float, str]] = None,
        northing: Optional[Union[float, str]] = None
    ) -> Tuple[float, float, float, float]:
        """
        Validates and converts input coordinates.
        Supports either:
          - (lat, lon) in WGS84 Geographic degrees
          - (easting, northing) in UTM Zone 44N (EPSG:32644) meters

        Returns: (lat, lon, easting, northing)
        """
        # Case 1: Provided as WGS84 Geographic
        if lat is not None and lon is not None:
            try:
                lat_f = float(lat)
                lon_f = float(lon)
            except (ValueError, TypeError):
                raise InvalidCoordinateError(f"Coordinates must be numeric: lat={lat!r}, lon={lon!r}")

            if not (-90.0 <= lat_f <= 90.0):
                raise InvalidCoordinateError(f"Latitude must be between -90 and +90 degrees: {lat_f}")
            if not (-180.0 <= lon_f <= 180.0):
                raise InvalidCoordinateError(f"Longitude must be between -180 and +180 degrees: {lon_f}")

            # Transform WGS84 (EPSG:4326) -> UTM Zone 44N (EPSG:32644)
            try:
                coords = warp_transform("EPSG:4326", "EPSG:32644", [lon_f], [lat_f])
                east_f = float(coords[0][0])
                north_f = float(coords[1][0])
            except Exception as e:
                raise PipelineError(f"Coordinate reprojection failed: {e}")

            return lat_f, lon_f, east_f, north_f

        # Case 2: Provided as Projected UTM Zone 44N
        elif easting is not None and northing is not None:
            try:
                east_f = float(easting)
                north_f = float(northing)
            except (ValueError, TypeError):
                raise InvalidCoordinateError(f"Projected UTM coordinates must be numeric: easting={easting!r}, northing={northing!r}")

            if not (100000.0 <= east_f <= 900000.0):
                raise InvalidCoordinateError(f"UTM Easting out of plausible range: {east_f}")
            if not (0.0 <= north_f <= 10000000.0):
                raise InvalidCoordinateError(f"UTM Northing out of plausible range: {north_f}")

            # Reverse Transform UTM Zone 44N (EPSG:32644) -> WGS84 (EPSG:4326)
            try:
                coords = warp_transform("EPSG:32644", "EPSG:4326", [east_f], [north_f])
                lon_f = float(coords[0][0])
                lat_f = float(coords[1][0])
            except Exception as e:
                raise PipelineError(f"Reverse coordinate reprojection failed: {e}")

            return lat_f, lon_f, east_f, north_f

        else:
            raise InvalidCoordinateError(
                "Must provide either (lat, lon) in WGS84 degrees or (easting, northing) in UTM 44N meters."
            )

    # --------------------------------------------------------------------------
    # STEP 4: TARGET-AREA & SURROUNDING WINDOW EXTRACTION
    # --------------------------------------------------------------------------
    def is_within_bounds(self, easting: float, northing: float, bounds) -> bool:
        """Checks if projected UTM coordinate falls strictly within raster bounds."""
        return (bounds.left <= easting <= bounds.right) and (bounds.bottom <= northing <= bounds.top)

    def extract_target_area(
        self,
        src: Any,
        easting: float,
        northing: float,
        radius_m: float = 25000.0
    ) -> Dict[str, Any]:
        """
        Determines the exact raster pixel for the target and extracts a surrounding
        radial circular area clamped strictly to raster bounds.
        """
        bounds = src.bounds
        
        # 1. Bounds verification
        if not self.is_within_bounds(easting, northing, bounds):
            raise OutOfBoundsError(
                f"Target coordinates (Easting: {easting:.1f}, Northing: {northing:.1f}) lie OUTSIDE "
                f"the active Sentinel-2 T44QMK tile boundaries:\n"
                f"  Left: {bounds.left:.1f}, Right: {bounds.right:.1f}\n"
                f"  Bottom: {bounds.bottom:.1f}, Top: {bounds.top:.1f}"
            )

        if radius_m <= 0:
            raise InvalidCoordinateError(f"Analysis radius must be strictly positive: {radius_m}m")

        # 2. Exact center pixel index
        center_row, center_col = src.index(easting, northing)
        
        # Validate pixel index ranges
        center_row = max(0, min(src.height - 1, center_row))
        center_col = max(0, min(src.width - 1, center_col))

        # Read exact center 1x1 window
        center_val_arr = src.read(1, window=((center_row, center_row + 1), (center_col, center_col + 1)))
        raw_center_val = float(center_val_arr[0, 0])

        if np.isnan(raw_center_val) or (src.nodata is not None and raw_center_val == src.nodata):
            raise NoDataError(
                f"The target location at pixel ({center_row}, {center_col}) has NoData value ({raw_center_val})."
            )

        # 3. Bounding box for surrounding window
        win_left = max(bounds.left, easting - radius_m)
        win_right = min(bounds.right, easting + radius_m)
        win_bottom = max(bounds.bottom, northing - radius_m)
        win_top = min(bounds.top, northing + radius_m)

        win = from_bounds(win_left, win_bottom, win_right, win_top, transform=src.transform)
        
        # Round window offsets/lengths to integers for safe reading
        c_off = max(0, int(math.floor(win.col_off)))
        r_off = max(0, int(math.floor(win.row_off)))
        w_len = min(src.width - c_off, int(math.ceil(win.width)))
        h_len = min(src.height - r_off, int(math.ceil(win.height)))
        win_int = Window(c_off, r_off, w_len, h_len)  # type: ignore

        # Read rectangular window
        window_data = src.read(1, window=win_int)
        
        # 4. Circular Masking for true radial buffer
        win_rows, win_cols = window_data.shape
        x_coords = np.linspace(win_left, win_right, win_cols)
        y_coords = np.linspace(win_top, win_bottom, win_rows)
        xx, yy = np.meshgrid(x_coords, y_coords)
        dist_sq = (xx - easting)**2 + (yy - northing)**2
        circle_mask = dist_sq <= (radius_m ** 2)

        radial_samples = window_data[circle_mask]

        # Filter out any NaNs or NoData values
        if src.nodata is not None:
            radial_samples = radial_samples[radial_samples != src.nodata]
        radial_samples = radial_samples[~np.isnan(radial_samples)]

        return {
            "center_row": int(center_row),
            "center_col": int(center_col),
            "center_value": float(raw_center_val),
            "window_shape": list(window_data.shape),
            "window_bounds": {
                "left": float(win_left),
                "right": float(win_right),
                "bottom": float(win_bottom),
                "top": float(win_top)
            },
            "radial_samples": radial_samples,
            "total_window_pixels": int(win_rows * win_cols),
            "masked_radial_pixels": int(len(radial_samples))
        }

    # --------------------------------------------------------------------------
    # STEP 5 & 6: SCORE CALCULATION & CLASSIFICATION
    # --------------------------------------------------------------------------
    @staticmethod
    def classify_prospectivity(score_ratio_or_pct: Optional[float]) -> str:
        """
        Classifies mineral potential into standard authoritative categories:
          - >= 90% : Very High
          - >= 75% : High
          - >= 50% : Moderate
          - >= 25% : Low
          - < 25%  : Very Low
        """
        if score_ratio_or_pct is None or np.isnan(score_ratio_or_pct):
            return "No Data"

        # Normalize to percentage if passed as ratio (0.0 to 1.0)
        pct = score_ratio_or_pct * 100.0 if score_ratio_or_pct <= 1.0 else score_ratio_or_pct

        if pct >= 90.0:
            return "Very High"
        elif pct >= 75.0:
            return "High"
        elif pct >= 50.0:
            return "Moderate"
        elif pct >= 25.0:
            return "Low"
        else:
            return "Very Low"

    def compute_statistics(self, target_data: Dict[str, Any], radius_m: float) -> Dict[str, Any]:
        """
        Computes descriptive spatial statistics across the radial target area.
        """
        samples = target_data["radial_samples"]
        center_val = target_data["center_value"]

        center_pct = round(center_val * 100.0, 2)
        center_classification = self.classify_prospectivity(center_val)

        if len(samples) > 0:
            min_val = float(np.min(samples))
            max_val = float(np.max(samples))
            mean_val = float(np.mean(samples))
            std_val = float(np.std(samples))
            median_val = float(np.median(samples))
            p25_val = float(np.percentile(samples, 25))
            p75_val = float(np.percentile(samples, 75))
            p90_val = float(np.percentile(samples, 90))

            high_pot_count = int(np.sum(samples >= 0.75))
            very_high_pot_count = int(np.sum(samples >= 0.90))
        else:
            min_val = max_val = mean_val = std_val = median_val = p25_val = p75_val = p90_val = center_val
            high_pot_count = 1 if center_val >= 0.75 else 0
            very_high_pot_count = 1 if center_val >= 0.90 else 0

        # Each pixel at 20m resolution = 400 m² = 0.04 hectares
        pixel_area_ha = 0.04

        return {
            "target_score": float(center_val),
            "target_percent": center_pct,
            "classification": center_classification,
            "radius_km": round(radius_m / 1000.0, 1),
            "sampled_pixels": len(samples),
            "area_sq_km": round(math.pi * (radius_m / 1000.0)**2, 1),
            "min_score": round(min_val, 4),
            "min_percent": round(min_val * 100.0, 2),
            "max_score": round(max_val, 4),
            "max_percent": round(max_val * 100.0, 2),
            "mean_score": round(mean_val, 4),
            "mean_percent": round(mean_val * 100.0, 2),
            "std_deviation": round(std_val, 4),
            "median_percent": round(median_val * 100.0, 2),
            "p25_percent": round(p25_val * 100.0, 2),
            "p75_percent": round(p75_val * 100.0, 2),
            "p90_percent": round(p90_val * 100.0, 2),
            "high_potential_pixels": high_pot_count,
            "high_potential_hectares": round(high_pot_count * pixel_area_ha, 1),
            "very_high_potential_pixels": very_high_pot_count,
            "very_high_potential_hectares": round(very_high_pot_count * pixel_area_ha, 1)
        }

    # --------------------------------------------------------------------------
    # STEP 7: NEARBY VERIFIED CANDIDATE ZONES
    # --------------------------------------------------------------------------
    def load_candidate_zones(self) -> List[Dict[str, Any]]:
        """Loads and caches the 20 verified candidate discovery zones."""
        if self._candidate_zones is not None:
            return self._candidate_zones

        zones = []
        if os.path.exists(self.zones_csv_path):
            try:
                import csv
                with open(self.zones_csv_path, mode="r", encoding="utf-8") as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        lat_val = float(row["Latitude"])
                        lon_val = float(row["Longitude"])
                        pixels_val = int(row["Pixels"])
                        
                        # Project UTM if Easting not in CSV
                        if "Easting" in row and "Northing" in row:
                            east_val = float(row["Easting"])
                            north_val = float(row["Northing"])
                        else:
                            coords = warp_transform("EPSG:4326", "EPSG:32644", [lon_val], [lat_val])
                            east_val, north_val = float(coords[0][0]), float(coords[1][0])

                        area_ha = float(row.get("Area_Hectares", pixels_val * 0.04))

                        zones.append({
                            "zone_id": int(row["Zone_ID"]),
                            "latitude": lat_val,
                            "longitude": lon_val,
                            "easting": round(east_val, 2),
                            "northing": round(north_val, 2),
                            "mean_score": float(row["Mean_Score"]),
                            "mean_percent": round(float(row["Mean_Score"]) * 100.0, 1),
                            "max_score": float(row["Max_Score"]),
                            "max_percent": round(float(row["Max_Score"]) * 100.0, 1),
                            "pixels": pixels_val,
                            "area_hectares": round(area_ha, 2)
                        })
            except Exception as e:
                sys.stderr.write(f"[Pipeline] Warning reading zones CSV: {e}\n")

        self._candidate_zones = zones
        return zones

    def find_nearby_zones(self, lat: float, lon: float, radius_km: float) -> List[Dict[str, Any]]:
        """Calculates distance to known high-prospectivity candidate zones."""
        zones = self.load_candidate_zones()
        nearby = []

        def haversine(lat1, lon1, lat2, lon2):
            R = 6371.0 # Earth radius in km
            dlat = math.radians(lat2 - lat1)
            dlon = math.radians(lon2 - lon1)
            a = math.sin(dlat / 2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2)**2
            return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

        for z in zones:
            dist = haversine(lat, lon, z["latitude"], z["longitude"])
            if dist <= radius_km:
                item = dict(z)
                item["distance_km"] = round(dist, 2)
                item["classification"] = self.classify_prospectivity(z["mean_score"])
                nearby.append(item)

        # Sort by distance ascending
        nearby.sort(key=lambda x: x["distance_km"])
        return nearby

    # --------------------------------------------------------------------------
    # COMPLETE END-TO-END PIPELINE EXECUTION
    # --------------------------------------------------------------------------
    def analyze_location(
        self,
        lat: Optional[float] = None,
        lon: Optional[float] = None,
        easting: Optional[float] = None,
        northing: Optional[float] = None,
        radius_km: float = 25.0,
        mineral: str = "manganese"
    ) -> Dict[str, Any]:
        """
        Executes complete mineral prospectivity pipeline for a given location.
        Enforces strict cross-mineral safety: manganese pipeline cannot be used for other minerals.
        """
        clean_mineral = str(mineral).strip().lower()
        if clean_mineral in ("iron", "iron-ore"):
            clean_mineral = "iron_ore"
        if clean_mineral != "manganese":
            mineral_title = clean_mineral.replace("_", " ").title()
            raise MineralMismatchError(
                f"Mineral/model mismatch. {mineral_title} prediction cannot use a Manganese model."
            )

        # 1. Raster validation
        raster_meta = self.validate_raster()

        # 2. Coordinate transformation
        lat_f, lon_f, east_f, north_f = self.parse_and_transform_coordinates(
            lat=lat, lon=lon, easting=easting, northing=northing
        )

        radius_m = float(radius_km) * 1000.0

        # 3. Extraction with Rasterio
        with rasterio.open(self.tif_path) as src:
            target_data = self.extract_target_area(src, east_f, north_f, radius_m=radius_m)

        # 4. Statistical aggregation & classification
        stats = self.compute_statistics(target_data, radius_m=radius_m)

        # 5. Proximity search to candidate zones
        nearby_zones = self.find_nearby_zones(lat_f, lon_f, radius_km=radius_km)

        # 6. Multi-spectral ratios calculation
        spectral_data = self.spectral_module.calculate_all_ratios(
            lat=lat_f, lon=lon_f, easting=east_f, northing=north_f, radius_km=radius_km
        )

        # 7. Complete structured result payload
        result = {
            "status": "success",
            "mineral": "Manganese (Mn)",
            "pipeline_version": "2.0-Production",
            "target": {
                "latitude": round(lat_f, 6),
                "longitude": round(lon_f, 6),
                "easting": round(east_f, 2),
                "northing": round(north_f, 2),
                "raster_row": target_data["center_row"],
                "raster_col": target_data["center_col"],
                "inside_raster": True
            },
            "prospectivity": {
                "score": stats["target_score"],
                "percent": stats["target_percent"],
                "classification": stats["classification"],
                "confidence_level": "Not Calibrated (Spatial Prospectivity Index)",
                "spectral_bands_analyzed": 6,
                "features_used": 10
            },
            "radial_analysis": {
                "radius_km": stats["radius_km"],
                "sampled_pixels": stats["sampled_pixels"],
                "min_percent": stats["min_percent"],
                "max_percent": stats["max_percent"],
                "mean_percent": stats["mean_percent"],
                "std_deviation": stats["std_deviation"],
                "median_percent": stats["median_percent"],
                "high_potential_pixels": stats["high_potential_pixels"],
                "high_potential_hectares": stats["high_potential_hectares"],
                "very_high_potential_pixels": stats["very_high_potential_pixels"],
                "very_high_potential_hectares": stats["very_high_potential_hectares"]
            },
            "candidate_zones_in_radius": nearby_zones,
            "nearby_zones_count": len(nearby_zones),
            "spectral_ratios": spectral_data,
            "raster_info": {
                "path": os.path.basename(self.tif_path),
                "crs": raster_meta["crs"],
                "pixel_size_m": raster_meta["pixel_size_x"]
            },
            "disclaimer": (
                "AI Prospectivity score is an exploration indication derived from Sentinel-2 "
                "multispectral satellite bands and Random Forest modeling. It highlights areas with "
                "favorable spectral, geochemical and lithological signatures, but does NOT constitute "
                "confirmation of an economic ore deposit or reserve."
            )
        }
        return result

    def calculate_spectral_ratios(
        self,
        lat: Optional[float] = None,
        lon: Optional[float] = None,
        easting: Optional[float] = None,
        northing: Optional[float] = None,
        radius_km: float = 25.0
    ) -> Dict[str, Any]:
        """Calculates multi-spectral ratios for target coordinates."""
        return self.spectral_module.calculate_all_ratios(
            lat=lat, lon=lon, easting=easting, northing=northing, radius_km=radius_km
        )

    def to_geojson(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Converts pipeline analysis results into an industry-standard GeoJSON
        FeatureCollection for seamless GIS integration (QGIS, ArcGIS, Mapbox, Leaflet).
        Includes:
          - Target point with full exploration metadata
          - Radial buffer circle polygon (64 vertices)
          - Verified discovery zones within radius as point features
        """
        features: List[Dict[str, Any]] = []
        tgt = result["target"]
        prosp = result["prospectivity"]
        rad = result["radial_analysis"]
        lat = tgt["latitude"]
        lon = tgt["longitude"]
        radius_km = rad["radius_km"]

        target_props = {
            "name": f"Exploration Target ({lat:.4f}, {lon:.4f})",
            "feature_type": "exploration_target",
            "mineral": result.get("mineral", "Manganese (Mn)"),
            "prospectivity_score": prosp["score"],
            "prospectivity_percent": prosp["percent"],
            "classification": prosp["classification"],
            "confidence": prosp["confidence_level"],
            "easting_utm44n": tgt["easting"],
            "northing_utm44n": tgt["northing"],
            "raster_row": tgt["raster_row"],
            "raster_col": tgt["raster_col"],
            "high_potential_hectares": rad["high_potential_hectares"]
        }
        if "spectral_ratios" in result and isinstance(result["spectral_ratios"], dict):
            target_props["spectral_ratios"] = result["spectral_ratios"].get("ratios", {})

        features.append({
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [lon, lat]
            },
            "properties": target_props
        })

        # 2. Radial Buffer Polygon (64-point approximation)
        buffer_coords = []
        for i in range(65):
            angle = math.radians(i * (360.0 / 64))
            d_lat = (radius_km * math.cos(angle)) / 111.32
            d_lon = (radius_km * math.sin(angle)) / (111.32 * math.cos(math.radians(lat)))
            buffer_coords.append([round(lon + d_lon, 6), round(lat + d_lat, 6)])

        features.append({
            "type": "Feature",
            "geometry": {
                "type": "Polygon",
                "coordinates": [buffer_coords]
            },
            "properties": {
                "name": f"Exploration Buffer ({radius_km} km)",
                "feature_type": "analysis_buffer",
                "radius_km": radius_km,
                "mean_prospectivity": rad["mean_percent"],
                "max_prospectivity": rad["max_percent"],
                "sampled_pixels": rad["sampled_pixels"]
            }
        })

        # 3. Candidate Discovery Zones
        for z in result.get("candidate_zones_in_radius", []):
            features.append({
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [z["longitude"], z["latitude"]]
                },
                "properties": {
                    "name": f"Candidate Discovery Zone #{z['zone_id']}",
                    "feature_type": "candidate_zone",
                    "zone_id": z["zone_id"],
                    "peak_score_pct": z["max_percent"],
                    "mean_score_pct": z["mean_percent"],
                    "distance_km": z["distance_km"],
                    "area_hectares": z["area_hectares"],
                    "pixels": z["pixels"],
                    "classification": z.get("classification", "High")
                }
            })

        return {
            "type": "FeatureCollection",
            "crs": {
                "type": "name",
                "properties": {"name": "urn:ogc:def:crs:OGC:1.3:CRS84"}
            },
            "features": features
        }



# ==============================================================================
# CONVENIENCE MODULE FUNCTIONS
# ==============================================================================

def analyze_location(
    lat: Optional[float] = None,
    lon: Optional[float] = None,
    easting: Optional[float] = None,
    northing: Optional[float] = None,
    radius_km: float = 25.0,
    tif_path: Optional[str] = None
) -> Dict[str, Any]:
    """Top-level convenience function for prospectivity analysis."""
    pipeline = ProspectivityPipeline(tif_path=tif_path)
    return pipeline.analyze_location(lat=lat, lon=lon, easting=easting, northing=northing, radius_km=radius_km)


# ==============================================================================
# BUILT-IN LIGHTWEIGHT HTTP SERVER FOR WEB INTEGRATION
# ==============================================================================

def start_server(port: int = 8080, host: str = "127.0.0.1", tif_path: Optional[str] = None):
    """
    Serves the AI Mineral Exploration web application and provides a live REST API
    backed directly by the GeoTIFF rasterio pipeline.
    """
    from http.server import SimpleHTTPRequestHandler
    from socketserver import ThreadingTCPServer
    import urllib.parse

    pipeline = ProspectivityPipeline(tif_path=tif_path)
    project_root = pipeline.project_root

    class PipelineHandler(SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=project_root, **kwargs)

        def do_GET(self):
            parsed = urllib.parse.urlparse(self.path)
            
            # API: /api/minerals
            if parsed.path == "/api/minerals":
                minerals_list = MineralRegistry.list_minerals()
                payload = json.dumps({"status": "success", "minerals": minerals_list}, indent=2).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(payload)
                return

            # API: /api/minerals/<mineral>/validation
            elif parsed.path.startswith("/api/minerals/") and parsed.path.endswith("/validation"):
                parts = parsed.path.strip("/").split("/")
                req_mineral = parts[2].lower() if len(parts) >= 4 else ""

                min_info = MineralRegistry.get_mineral(req_mineral)
                if not min_info:
                    payload = json.dumps({"status": "error", "message": f"Mineral '{req_mineral}' not found."}, indent=2).encode("utf-8")
                    self.send_response(404)
                    self.send_header("Content-Type", "application/json")
                    self.send_header("Access-Control-Allow-Origin", "*")
                    self.end_headers()
                    self.wfile.write(payload)
                    return

                if not min_info.get("is_trained"):
                    payload = json.dumps({
                        "status": "error",
                        "mineral": req_mineral,
                        "model_status": min_info.get("model_status", "AWAITING_DATA"),
                        "validation_status": min_info.get("validation_status", "NOT_VALIDATED"),
                        "calibration_status": "NOT_CALIBRATED",
                        "message": f"Validation unavailable: {req_mineral.replace('_', ' ').title()} has no trained model. Ground-truth observations and occurrence labels required."
                    }, indent=2).encode("utf-8")
                    self.send_response(404)
                    self.send_header("Content-Type", "application/json")
                    self.send_header("Access-Control-Allow-Origin", "*")
                    self.end_headers()
                    self.wfile.write(payload)
                    return

                # Read validation report if present
                report_path = os.path.join(project_root, "models", f"{req_mineral}_validation_report.json")
                if not os.path.exists(report_path):
                    payload = json.dumps({
                        "status": "error",
                        "mineral": req_mineral,
                        "model_status": min_info.get("model_status", "TRAINED"),
                        "validation_status": "AWAITING_VALIDATION",
                        "calibration_status": "NOT_CALIBRATED",
                        "message": f"No validation report generated yet for {req_mineral}."
                    }, indent=2).encode("utf-8")
                    self.send_response(404)
                    self.send_header("Content-Type", "application/json")
                    self.send_header("Access-Control-Allow-Origin", "*")
                    self.end_headers()
                    self.wfile.write(payload)
                    return

                try:
                    with open(report_path, "r", encoding="utf-8") as rf:
                        v_rep = json.load(rf)
                    response_data = {
                        "status": "success",
                        "mineral": req_mineral,
                        "model_status": min_info.get("model_status", "TRAINED"),
                        "validation_status": min_info.get("validation_status", "SPATIALLY_VALIDATED"),
                        "calibration_status": v_rep.get("calibration", {}).get("status", "NOT_CALIBRATED"),
                        "dataset_size": v_rep.get("dataset_samples"),
                        "positive_samples": v_rep.get("positive_samples"),
                        "negative_samples": v_rep.get("negative_samples"),
                        "validation_methodology": "Within-study spatial-sector validation",
                        "independent_deposit_validation": {
                            "status": "NOT_AVAILABLE",
                            "display_value": "NOT AVAILABLE",
                            "methodology": "Within-study spatial-sector validation",
                            "explanation": "Current positive ground truth originates from one known Manganese deposit. Independent deposit validation requires additional real Manganese occurrence datasets."
                        },
                        "spatial_metrics": v_rep.get("validation", {}),
                        "random_holdout_metrics": v_rep.get("random_holdout", {}),
                        "limitations": v_rep.get("limitations", [])
                    }
                    payload = json.dumps(response_data, indent=2).encode("utf-8")
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json")
                    self.send_header("Access-Control-Allow-Origin", "*")
                    self.end_headers()
                    self.wfile.write(payload)
                    return
                except Exception as ex:
                    payload = json.dumps({"status": "error", "message": f"Failed reading validation report: {str(ex)}"}, indent=2).encode("utf-8")
                    self.send_response(500)
                    self.send_header("Content-Type", "application/json")
                    self.send_header("Access-Control-Allow-Origin", "*")
                    self.end_headers()
                    self.wfile.write(payload)
                    return

            # API: /api/analyze?lat=...&lon=...&radius=...&mineral=...
            elif parsed.path == "/api/analyze":
                params = urllib.parse.parse_qs(parsed.query)
                lat = float(params.get("lat", [21.9455])[0])
                lon = float(params.get("lon", [80.4295])[0])
                radius = float(params.get("radius", [25])[0])
                mineral = params.get("mineral", ["manganese"])[0]
                
                try:
                    res = pipeline.analyze_location(lat=lat, lon=lon, radius_km=radius, mineral=mineral)
                    payload = json.dumps(res, indent=2).encode("utf-8")
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json")
                    self.send_header("Access-Control-Allow-Origin", "*")
                    self.end_headers()
                    self.wfile.write(payload)
                except (PipelineError, MineralMismatchError, TrainingDataUnavailableError) as pe:
                    payload = json.dumps({"status": "error", "message": str(pe)}, indent=2).encode("utf-8")
                    self.send_response(400)
                    self.send_header("Content-Type", "application/json")
                    self.send_header("Access-Control-Allow-Origin", "*")
                    self.end_headers()
                    self.wfile.write(payload)
                return

            # API: /api/health
            elif parsed.path == "/api/health":
                try:
                    meta = pipeline.validate_raster()
                    payload = json.dumps({"status": "healthy", "raster": meta}, indent=2).encode("utf-8")
                    self.send_response(200)
                except Exception as e:
                    payload = json.dumps({"status": "unhealthy", "error": str(e)}, indent=2).encode("utf-8")
                    self.send_response(500)
                self.send_header("Content-Type", "application/json")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(payload)
                return

            # API: /api/zones?mineral=...
            elif parsed.path == "/api/zones":
                params = urllib.parse.parse_qs(parsed.query)
                mineral = params.get("mineral", ["manganese"])[0].lower()
                if mineral in ("iron", "iron-ore"):
                    mineral = "iron_ore"

                if mineral != "manganese":
                    # Untrained mineral: no candidate zones exist
                    payload = json.dumps({
                        "status": "awaiting_data",
                        "mineral": mineral,
                        "zones": [],
                        "message": "Model not trained. Training data required before mineral-specific candidate zones can be generated."
                    }, indent=2).encode("utf-8")
                else:
                    zones = pipeline.load_candidate_zones()
                    payload = json.dumps({"status": "success", "mineral": "manganese", "zones": zones}, indent=2).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(payload)
                return

            # API: /api/export-geojson?lat=...&lon=...&radius=...
            elif parsed.path == "/api/export-geojson":
                params = urllib.parse.parse_qs(parsed.query)
                lat = float(params.get("lat", [21.9455])[0])
                lon = float(params.get("lon", [80.4295])[0])
                radius = float(params.get("radius", [25])[0])
                try:
                    res = pipeline.analyze_location(lat=lat, lon=lon, radius_km=radius)
                    geojson_data = pipeline.to_geojson(res)
                    payload = json.dumps(geojson_data, indent=2).encode("utf-8")
                    self.send_response(200)
                    self.send_header("Content-Type", "application/geo+json")
                    self.send_header("Content-Disposition", f"attachment; filename=\"target_dossier_{lat:.4f}_{lon:.4f}.geojson\"")
                    self.send_header("Access-Control-Allow-Origin", "*")
                    self.end_headers()
                    self.wfile.write(payload)
                except PipelineError as pe:
                    payload = json.dumps({"status": "error", "message": str(pe)}, indent=2).encode("utf-8")
                    self.send_response(400)
                    self.send_header("Content-Type", "application/json")
                    self.send_header("Access-Control-Allow-Origin", "*")
                    self.end_headers()
                    self.wfile.write(payload)
                return

            # API: /api/production?rainfall=...&downtime=...&blasting=...&availability=...&planned=...
            elif parsed.path == "/api/production":
                params = urllib.parse.parse_qs(parsed.query)
                rainfall = float(params.get("rainfall", [150.0])[0])
                downtime = float(params.get("downtime", [20.0])[0])
                blasting = float(params.get("blasting", [8.0])[0])
                avail = float(params.get("availability", [85.0])[0])
                planned = float(params.get("planned", [11000.0])[0])

                json_trees_path = os.path.join(project_root, "data", "processed", "production_rf_trees.json")
                if os.path.exists(json_trees_path):
                    try:
                        with open(json_trees_path, "r", encoding="utf-8") as f:
                            exported = json.load(f)
                        x_vec = {
                            "Rainfall_mm": rainfall,
                            "Equipment_Downtime_hr": downtime,
                            "Blasting_Delay_hr": blasting,
                            "Equipment_Availability_pct": avail,
                            "Planned_Production_tonnes": planned
                        }
                        tree_preds = []
                        for tree in exported["trees"]:
                            node = 0
                            left, right = tree["children_left"], tree["children_right"]
                            feat, thresh, val = tree["feature"], tree["threshold"], tree["value"]
                            while left[node] != -1:
                                f_name = exported["features"][feat[node]]
                                if x_vec[f_name] <= thresh[node]:
                                    node = left[node]
                                else:
                                    node = right[node]
                            tree_preds.append(val[node])
                        pred_tonnes = round(float(np.mean(tree_preds)), 2)
                        shortfall = round(max(0.0, planned - pred_tonnes), 2)
                        shortfall_pct = round((shortfall / planned) * 100.0, 1) if planned > 0 else 0.0
                        payload = json.dumps({
                            "status": "success",
                            "predicted_tonnes": pred_tonnes,
                            "planned_tonnes": planned,
                            "shortfall_tonnes": shortfall,
                            "shortfall_percent": shortfall_pct,
                            "risk_level": "High" if shortfall_pct > 20 else ("Moderate" if shortfall_pct > 10 else "Low")
                        }, indent=2).encode("utf-8")
                        self.send_response(200)
                    except Exception as e:
                        payload = json.dumps({"status": "error", "message": str(e)}, indent=2).encode("utf-8")
                        self.send_response(500)
                else:
                    payload = json.dumps({"status": "error", "message": "production_rf_trees.json not found"}, indent=2).encode("utf-8")
                    self.send_response(404)
                self.send_header("Content-Type", "application/json")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(payload)
                return

            # API: /api/spectral-ratios?lat=...&lon=...&radius=...
            elif parsed.path == "/api/spectral-ratios":
                params = urllib.parse.parse_qs(parsed.query)
                lat = float(params.get("lat", [21.9455])[0])
                lon = float(params.get("lon", [80.4295])[0])
                radius = float(params.get("radius", [25.0])[0])
                try:
                    spectral_res = pipeline.calculate_spectral_ratios(lat=lat, lon=lon, radius_km=radius)
                    payload = json.dumps(spectral_res, indent=2).encode("utf-8")
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json")
                    self.send_header("Access-Control-Allow-Origin", "*")
                    self.end_headers()
                    self.wfile.write(payload)
                except (PipelineError, SpectralRatioError) as pe:
                    payload = json.dumps({"status": "error", "message": str(pe)}, indent=2).encode("utf-8")
                    self.send_response(400)
                    self.send_header("Content-Type", "application/json")
                    self.send_header("Access-Control-Allow-Origin", "*")
                    self.end_headers()
                    self.wfile.write(payload)
                except Exception as ge:
                    payload = json.dumps({"status": "error", "message": str(ge)}, indent=2).encode("utf-8")
                    self.send_response(400)
                    self.send_header("Content-Type", "application/json")
                    self.send_header("Access-Control-Allow-Origin", "*")
                    self.end_headers()
                    self.wfile.write(payload)
                return

            # API: /api/geology/status
            elif parsed.path == "/api/geology/status":
                engine = get_geology_engine(project_root)
                payload = json.dumps(engine.get_status(), indent=2).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(payload)
                return

            # API: /api/geology/context?lat=...&lon=...&radius=...
            elif parsed.path == "/api/geology/context":
                params = urllib.parse.parse_qs(parsed.query)
                lat = float(params.get("lat", [21.9455])[0])
                lon = float(params.get("lon", [80.4295])[0])
                radius = float(params.get("radius", [25.0])[0])
                try:
                    engine = get_geology_engine(project_root)
                    ctx = engine.calculate_geological_evidence(lat=lat, lon=lon, radius_km=radius)
                    payload = json.dumps(ctx, indent=2).encode("utf-8")
                    self.send_response(200)
                except Exception as ge:
                    payload = json.dumps({"status": "error", "message": str(ge)}, indent=2).encode("utf-8")
                    self.send_response(400)
                self.send_header("Content-Type", "application/json")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(payload)
                return

            # API: /api/terrain/status
            elif parsed.path == "/api/terrain/status":
                t_engine = get_terrain_engine(project_root)
                payload = json.dumps(t_engine.get_status(), indent=2).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(payload)
                return

            # API: /api/terrain/context?lat=...&lon=...&radius=...
            elif parsed.path == "/api/terrain/context":
                params = urllib.parse.parse_qs(parsed.query)
                lat = float(params.get("lat", [21.9455])[0])
                lon = float(params.get("lon", [80.4295])[0])
                radius = float(params.get("radius", [25.0])[0])
                try:
                    t_engine = get_terrain_engine(project_root)
                    ctx = t_engine.calculate_terrain_evidence(lat=lat, lon=lon, radius_km=radius)
                    payload = json.dumps(ctx, indent=2).encode("utf-8")
                    self.send_response(200)
                except Exception as te:
                    payload = json.dumps({"status": "error", "message": str(te)}, indent=2).encode("utf-8")
                    self.send_response(400)
                self.send_header("Content-Type", "application/json")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(payload)
                return

            # API: /api/validation/independent?mineral=...
            elif parsed.path == "/api/validation/independent":
                params = urllib.parse.parse_qs(parsed.query)
                mineral = params.get("mineral", ["manganese"])[0].lower()
                if mineral != "manganese":
                    payload = json.dumps({
                        "status": "NOT_AVAILABLE",
                        "available": False,
                        "mineral": mineral,
                        "reason": f"Independent validation unavailable for {mineral}: Model awaiting real training data."
                    }, indent=2).encode("utf-8")
                    self.send_response(200)
                else:
                    ind_engine = get_independent_engine(project_root)
                    report = ind_engine.evaluate()
                    payload = json.dumps(report, indent=2).encode("utf-8")
                    self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(payload)
                return

            # Static web asset serving (index.html, styles.css, app.js, js/, etc.)
            super().do_GET()

    ThreadingTCPServer.allow_reuse_address = True
    print(f"\n=================================================================")
    print(f" AI MINERAL EXPLORATION PLATFORM SERVER ACTIVE")
    print(f" URL: http://{host}:{port}/")
    print(f" Endpoints: /api/analyze, /api/health, /api/zones, /api/export-geojson, /api/production, /api/spectral-ratios, /api/minerals, /api/minerals/<mineral>/validation, /api/geology/status, /api/geology/context, /api/terrain/status, /api/terrain/context, /api/validation/independent")
    print(f" Serving root: {project_root}")
    print(f"=================================================================\n")
    
    with ThreadingTCPServer((host, port), PipelineHandler) as httpd:
        httpd.daemon_threads = True
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nShutting down server.")


# ==============================================================================
# COMMAND LINE INTERFACE (CLI)
# ==============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="AI Mineral Exploration & Manganese Prospectivity Pipeline"
    )
    parser.add_argument("--tif", type=str, default=None, help="Path to input GeoTIFF file")
    parser.add_argument("--lat", type=float, default=None, help="Target latitude (WGS84 degrees)")
    parser.add_argument("--lon", type=float, default=None, help="Target longitude (WGS84 degrees)")
    parser.add_argument("--easting", type=float, default=None, help="Target Easting (UTM Zone 44N meters)")
    parser.add_argument("--northing", type=float, default=None, help="Target Northing (UTM Zone 44N meters)")
    parser.add_argument("--radius", type=float, default=25.0, help="Surrounding radius in kilometers (default: 25)")
    parser.add_argument("--validate-only", action="store_true", help="Validate GeoTIFF integrity and exit")
    parser.add_argument("--json", action="store_true", help="Output raw JSON format")
    parser.add_argument("--output", type=str, default=None, help="Path to save output JSON")
    parser.add_argument("--geojson", type=str, default=None, help="Path to save GIS GeoJSON FeatureCollection")
    parser.add_argument("--spectral-ratios", action="store_true", help="Calculate and output multi-spectral ratios")
    parser.add_argument("--bands-dir", type=str, default=None, help="Directory containing raw Sentinel-2 band rasters")
    parser.add_argument("--serve", action="store_true", help="Start the interactive web app server with live API")
    parser.add_argument("--port", type=int, default=8080, help="Port for web server (default: 8080)")

    args = parser.parse_args()


    if args.serve:
        start_server(port=args.port, tif_path=args.tif)
        return

    try:
        pipeline = ProspectivityPipeline(tif_path=args.tif)

        if args.validate_only:
            meta = pipeline.validate_raster()
            if args.json:
                print(json.dumps(meta, indent=2))
            else:
                print("\n=======================================================")
                print(" RASTER VALIDATION SUCCESSFUL")
                print("=======================================================")
                print(f" Path:       {meta['path']}")
                print(f" CRS:        {meta['crs']} (EPSG: {meta['epsg']})")
                print(f" Dimensions: {meta['width']} x {meta['height']} (20m resolution)")
                print(f" Bounds:     Left={meta['bounds']['left']}, Right={meta['bounds']['right']}")
                print(f"             Bottom={meta['bounds']['bottom']}, Top={meta['bounds']['top']}")
                print("=======================================================\n")
            return

        # Default coordinates to known Ghondi Manganese Mine if none supplied
        lat = args.lat
        lon = args.lon
        easting = args.easting
        northing = args.northing

        if lat is None and lon is None and easting is None and northing is None:
            # Default location
            lat = 21.9455
            lon = 80.4295

        result = pipeline.analyze_location(
            lat=lat, lon=lon, easting=easting, northing=northing, radius_km=args.radius
        )

        if args.output:
            with open(args.output, "w", encoding="utf-8") as f:
                json.dump(result, f, indent=2)
            print(f"[OK] Saved results to: {args.output}")

        if args.geojson:
            geojson_data = pipeline.to_geojson(result)
            with open(args.geojson, "w", encoding="utf-8") as f:
                json.dump(geojson_data, f, indent=2)
            print(f"[OK] Exported GIS GeoJSON to: {args.geojson}")


        if args.json:
            print(json.dumps(result, indent=2))
        else:
            tgt = result["target"]
            prosp = result["prospectivity"]
            rad = result["radial_analysis"]

            print("\n" + "=" * 66)
            print(" AI MINERAL INTELLIGENCE — PROSPECTIVITY REPORT")
            print("=" * 66)
            print(f" Target:            {tgt['latitude']}°N, {tgt['longitude']}°E")
            print(f" UTM Zone 44N:      {tgt['easting']:.1f} m E, {tgt['northing']:.1f} m N")
            print(f" Raster Index:      Row {tgt['raster_row']}, Col {tgt['raster_col']}")
            print("-" * 66)
            print(f" PROSPECTIVITY:     {prosp['percent']:.1f}% ({prosp['classification']})")
            print(f" Confidence:        {prosp['confidence_level']}")
            print("-" * 66)
            print(f" SURROUNDING BUFFER: Radius {rad['radius_km']} km ({rad['sampled_pixels']:,} sampled pixels)")
            print(f" Buffer Range:      Min {rad['min_percent']:.1f}%  |  Mean {rad['mean_percent']:.1f}%  |  Max {rad['max_percent']:.1f}%")
            print(f" Std. Deviation:    {rad['std_deviation'] * 100:.2f}%  |  Median {rad['median_percent']:.1f}%")
            print(f" High-Potential:    {rad['high_potential_pixels']:,} pixels ({rad['high_potential_hectares']:,} hectares)")
            print(f" Nearby Zones:      {result['nearby_zones_count']} verified high-prospectivity zones")
            if result['candidate_zones_in_radius']:
                print("-" * 66)
                print(f" {'Zone ID':<10} {'Distance':<12} {'Peak Score':<12} {'Area':<12}")
                for z in result['candidate_zones_in_radius'][:5]:
                    print(f" #{z['zone_id']:<9} {z['distance_km']:<6.1f} km     {z['max_percent']:<6.1f}%      {z['area_hectares']} ha")
            if "spectral_ratios" in result:
                spec = result["spectral_ratios"]
                print("-" * 66)
                print(f" MULTI-SPECTRAL RATIOS (Status: {spec['spectral_status'].upper()})")
                print("-" * 66)
                for r_key, r_info in spec.get("ratios", {}).items():
                    name = r_info["name"]
                    formula = r_info["formula"]
                    if r_info.get("status") == "calculated":
                        val_str = f"{r_info['target_value']:.4f}" if r_info['target_value'] is not None else "N/A"
                        mean_str = f"{r_info['statistics']['mean']:.4f}" if r_info.get('statistics') else "N/A"
                        print(f" {name:<20} ({formula:<9}): Target={val_str:<8} Buffer Mean={mean_str}")
                    else:
                        missing_str = ", ".join(r_info.get("missing_bands", []))
                        print(f" {name:<20} ({formula:<9}): Awaiting bands [{missing_str}] on disk")

            print("=" * 66)
            print(f" Disclaimer: {result['disclaimer']}")
            print("=" * 66 + "\n")


    except PipelineError as pe:
        sys.stderr.write(f"\n[PIPELINE ERROR] {type(pe).__name__}: {str(pe)}\n\n")
        sys.exit(1)
    except Exception as ex:
        sys.stderr.write(f"\n[UNEXPECTED ERROR] {type(ex).__name__}: {str(ex)}\n\n")
        sys.exit(2)


if __name__ == "__main__":
    main()
