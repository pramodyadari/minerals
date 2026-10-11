# Geological & Terrain Data Provenance Contract

**Specification Version**: 1.0  
**Project**: AI Mineral Intelligence Platform  
**Scope**: Ingestion, Validation, and Provenance Contract for Geological and Terrain Evidence Layers  
**Audit Date**: October 2026  

---

## 1. Executive Summary & Audit Declaration

In accordance with strict scientific integrity principles:
- **No fabricated, estimated, or synthetic geological, structural, or terrain layers are introduced.**
- When verified real datasets are absent from the repository footprint, the platform must report **`DATA NOT AVAILABLE`**.
- All layers must declare verified provenance (Source, Dataset, CRS, Spatial Extent, Resolution, and Availability).

---

## 2. In-Depth Layer Audit Status

| Evidence Layer | Category | Status | File / Source Path | CRS | Resolution | Provenance & Scientific Basis |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Sentinel-2 Prospectivity** | Multispectral ML | **AVAILABLE** | `outputs/manganese_prospectivity.tif` | `EPSG:32644` | 20 m | Copernicus Sentinel-2 L2A Tile T44QMK evaluated with 100-tree Random Forest |
| **Candidate Discovery Zones** | Spatial Clustering | **AVAILABLE** | `data/processed/high_prospectivity_zones.csv` | `EPSG:4326` / `EPSG:32644` | Vector Centroids | 20 high-prospectivity anomaly clusters extracted from authoritative prospectivity raster |
| **Regional Lithology** | Geology | **DATA NOT AVAILABLE** | None found on disk | N/A | N/A | No digitized regional lithological formation vector map or raster loaded in repository |
| **Structural Geology (Faults/Shears)** | Geology | **DATA NOT AVAILABLE** | None found on disk | N/A | N/A | No digitized fault, fracture, lineament, or shear zone vector shapefile loaded in repository |
| **Digital Elevation Model (DEM)** | Terrain | **DATA NOT AVAILABLE** | None found on disk | N/A | N/A | No digital elevation raster (SRTM, ASTER DEM, or Copernicus DEM) loaded in repository |
| **Terrain Derivatives (Slope/Aspect)** | Terrain | **DATA NOT AVAILABLE** | None found on disk | N/A | N/A | Requires genuine DEM raster before derivative slope and aspect grids can be computed |
| **Subsurface Drilling & Assays** | Geochemistry | **DATA NOT AVAILABLE** | None found on disk | N/A | N/A | No diamond drill logs, borehole assays, or core geochemistry loaded in repository |

---

## 3. Provenance Schema Requirements for Future Ingestion

When genuine geological or terrain datasets become available for ingestion, they must strictly satisfy the following schema contracts:

### 3.1 Geological Layer Contract (`geology`)
A valid geological dataset must provide:
- **Format**: GeoJSON, Shapefile (`.shp`), GeoPackage (`.gpkg`), or GeoTIFF (`.tif`).
- **CRS**: Verified coordinate reference system (must be reprojectable to `EPSG:4326` and `EPSG:32644`).
- **Footprint**: Must intersect Sentinel-2 Tile T44QMK (`21.3667°N` to `22.4333°N`, `79.9333°E` to `80.6515°E`).
- **Attributes**:
  - `unit_name` (String): Recognized lithological or formation name (e.g. "Mansar Formation, Sausar Group").
  - `rock_type` (String): Primary rock classification (e.g. "Mica schist, quartzite, gondite").
  - `source_agency` (String): Authoritative surveying authority (e.g. "Geological Survey of India").
  - `citation` (String): Published map/quadrangle citation or report identifier.

### 3.2 Structural Geology Contract (`structures`)
A valid structural lineament dataset must provide:
- **Format**: GeoJSON, Shapefile, or GeoPackage containing `LineString` or `MultiLineString` features.
- **Attributes**:
  - `structure_type` (String): Categorized structure (e.g. "Normal Fault", "Thrust Fault", "Shear Zone", "Photolineament").
  - `strike_dip` (Optional String): Dip angle and direction if field-measured.
  - `source_agency` (String): Authoritative surveying authority.

### 3.3 Terrain / DEM Contract (`terrain`)
A valid Digital Elevation Model must provide:
- **Format**: Single-band GeoTIFF (`.tif`).
- **Data Type**: Float32 or Int16 elevation values in meters above mean sea level.
- **CRS**: Projected or geographic CRS matching regional bounds.
- **Resolution**: $\le 30\text{ m}$ (e.g. SRTM 1 Arc-Second 30m or Copernicus DEM GLO-30).
- **Derivatives Calculation**: Slope in degrees ($0^\circ - 90^\circ$) and Aspect ($0^\circ - 360^\circ$) calculated via Horn's formula or standard finite differences only from verified elevation pixels.

---

## 4. Scientific Honesty & Interpretation Invariants

1. **Absence Handling**: When datasets are missing, engines must return `available: false` and `status: "DATA_NOT_AVAILABLE"`. Engines must NEVER synthesize random coordinates, heights, or rock types.
2. **Contextual Distinction**: Geological and terrain layers provide **contextual exploration screening evidence**, NOT standalone proof of mineralization.
3. **No Fake Occurrence Rules**: Proximity to faults or presence of specific rock types must be reported as objective spatial measurements (e.g. "Distance to nearest fault: 340 m"), never as artificial probability multipliers.
4. **Independent Deposit Validation**: Validation of the Manganese model remains **Within-study spatial-sector validation (96.76%)**. Independent deposit validation across distinct mining districts remains **`NOT AVAILABLE`** until multi-deposit ground-truth datasets are ingested.
