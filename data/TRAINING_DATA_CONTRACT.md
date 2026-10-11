# Standard Mineral Training Data Contract

**Specification Version**: 1.0  
**Scope**: Machine learning training data ingestion for the AI Mineral Intelligence Platform  
**Target Architecture**: Random Forest Spatial Prospectivity Classifier

---

## 1. Overview

To maintain scientific integrity and prevent cross-mineral contamination, every mineral commodity trained in this system must adhere strictly to this contract. Datasets that fail any requirement are rejected, and the mineral remains in `AWAITING REAL TRAINING DATA` status.

---

## 2. Dataset Schema Requirements

A valid mineral training dataset must be provided as a structured CSV or GeoPackage containing the following columns:

| Column Name | Data Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `latitude` | Float64 | `-90.0` to `90.0` | WGS84 geographic latitude coordinate |
| `longitude` | Float64 | `-180.0` to `180.0` | WGS84 geographic longitude coordinate |
| `mineral` | String | Must match registered commodity ID | Exact mineral identifier (e.g. `manganese`, `iron_ore`) |
| `label` | Int32 | `0` or `1` only | `1` = Ground-truth occurrence/deposit, `0` = Verified background/non-deposit |
| `B02` | Float64 | `0.0` to `1.0` (Surface Reflectance) | Sentinel-2 Blue band (490 nm) |
| `B03` | Float64 | `0.0` to `1.0` (Surface Reflectance) | Sentinel-2 Green band (560 nm) |
| `B04` | Float64 | `0.0` to `1.0` (Surface Reflectance) | Sentinel-2 Red band (665 nm) |
| `B08` | Float64 | `0.0` to `1.0` (Surface Reflectance) | Sentinel-2 NIR band (842 nm) |
| `B11` | Float64 | `0.0` to `1.0` (Surface Reflectance) | Sentinel-2 SWIR-1 band (1610 nm) |
| `B12` | Float64 | `0.0` to `1.0` (Surface Reflectance) | Sentinel-2 SWIR-2 band (2190 nm) |
| `NDVI` | Float64 | `-1.0` to `1.0` | Normalized Difference Vegetation Index: `(B08 - B04)/(B08 + B04)` |
| `NDWI` | Float64 | `-1.0` to `1.0` | Normalized Difference Water Index: `(B03 - B08)/(B03 + B08)` |
| `clay_ratio` | Float64 | `> 0.0` (finite) | Hydrothermal clay alteration ratio: `B11 / B12` |
| `iron_oxide_ratio`| Float64 | `> 0.0` (finite) | Gossan / iron oxide alteration ratio: `B04 / B02` |

Optional provenance metadata columns:
- `sample_id`: Unique record identifier
- `deposit_name`: Name of known deposit or quarry
- `source_citation`: Published survey citation, GSI report, or mine registry ID
- `observation_date`: ISO 8601 date of field observation or imagery acquisition

---

## 3. Data Integrity & Validation Rules

1. **No Missing Values**: No nulls, `NaN`, or infinite values permitted across coordinates, labels, or features.
2. **Binary Balance & Minimum Sample Count**:
   - Minimum positive observations: 20 independent ground-truth locations.
   - Minimum negative observations: 20 independent non-occurrence locations.
3. **Spatial Deduplication**:
   - Observations located within 20 meters of each other (1 Sentinel-2 pixel) must be deduplicated to avoid over-sampling identical ground cells.
4. **Spatial Leakage Prevention**:
   - Training pipeline must employ spatially blocked validation (e.g. 5 km spatial grid blocks or spatial cluster holdout) to prevent spatial autocorrelation leakage between train and test splits.
5. **Tile Bounds Verification**:
   - All coordinates must fall within the bounding footprint of the designated satellite exploration tile.
6. **Zero Cross-Mineral Contamination**:
   - Samples labeled for mineral $A$ can never be relabeled or reused for mineral $B$.
