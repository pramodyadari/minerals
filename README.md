# AI Mineral Exploration and Terrain Intelligence System

An integrated, evidence-based geospatial mineral prospectivity dashboard, 3D terrain intelligence engine, and 4-class rock specimen classification system built with **React 18**, **Vite**, **Leaflet**, **MapLibre GL JS**, **FastAPI**, **Rasterio**, and **PyTorch**.

---

## 1. System Overview & Core Philosophy

The system provides dual capabilities with rigorous scientific integrity:
1. **Geographical Mineral Prospectivity & Terrain Analysis**: Geospatial exploration mapping across authentic Copernicus Sentinel-2 Level-2A multi-spectral rasters, official Copernicus GLO-30 Digital Elevation Models, and Geological Survey of India (GSI) / Indian Bureau of Mines (IBM) occurrence inventories.
2. **AI Specimen Image Classification**: A PyTorch 4-class Convolutional Neural Network (`MineralConvNet`) trained on verified rock and ore hand samples. The application explicitly distinguishes photographed surface hand-specimens from subsurface geological occurrence modeling.
3. **Interactive 2D / 3D Visualizations**:
   - **2D Cartographic Map**: Dynamic Leaflet map with OpenStreetMap basemap, accurate metric radius buffer circles, and 20 verified high-prospectivity anomaly zones.
   - **3D Terrain Model**: Real-time terrain elevation viewer powered by MapLibre GL JS with customizable pitch, bearing, and terrain vertical exaggeration.
   - **3D Mineral Prospectivity Surface**: High-resolution Three.js prospectivity surface rendered **strictly** when a validated, calibrated prediction grid exists. When a model or grid is unavailable, an honest unavailable notice is displayed with an option to switch to 3D Terrain View. Never generates synthetic or fabricated prospectivity grids.

---

## 2. Four Selectable Minerals & Model Status

The platform supports **strictly four selectable mineral commodities**, each with its own verified data sources, evidence logic, model status, validation metadata, and response behavior:

| Mineral | Category | Model Status | AI Prospectivity Score | Genuine Data Sources |
| :--- | :--- | :--- | :--- | :--- |
| **Manganese (`Mn`)** | Strategic Ferroalloy | `VALIDATED_ACTIVE` (Tile `T44QMK`) | Active (Uncalibrated Spatial Index %) | Sentinel-2 L2A (B02, B03, B04, B08, B11, B12), GSI Sausar Group lithology, Balaghat-Nagpur mining belt |
| **Iron Ore (`Fe`)** | Ferrous Metal Ore | `UNAVAILABLE_INSUFFICIENT_SPATIAL_VALIDATION` | **Strictly Null** (`None`) | Copernicus DEM GLO-30 (30m), Sentinel-2 L2A (Noamundi), GSI Singhbhum Craton Iron Ore Group (BIF/BHQ) |
| **Coal (`C`)** | Energy Commodity | `UNAVAILABLE_NO_MODEL` | **Strictly Null** (`None`) | Gondwana Basin stratigraphy, colliery occurrences, VNIR surface albedo (subsurface seams require core logs) |
| **Bauxite (`Al`)** | Aluminum Lateritic Ore | `UNAVAILABLE_NO_MODEL` | **Strictly Null** (`None`) | Tertiary lateritic plateau/pat geomorphology, SWIR Al-OH clay absorption (chemical assay required for ore grade) |

### Scientific Guardrails
- **Manganese**: The Random Forest model is validated strictly within Sentinel-2 tile `T44QMK` (Balaghat corridor). Outside `T44QMK`, the system reports `OUTSIDE_TRAINING_FOOTPRINT`, withholding predictions to prevent invalid regional transfer without retraining.
- **Iron Ore**: Spatial cross-validation across 16,033 pixels from 5 confirmed deposits (Noamundi, Joda East, Kiriburu, Gua, Bolani) demonstrates that optical features achieve 83.5% random holdout accuracy due to spatial autocorrelation, but drop to 47.7% accuracy under true spatially blocked validation due to regolith/laterite confounding. Numerical AI scores remain strictly withheld pending authorized GSI aeromagnetic tensor grids and 1:50,000 lithological vectors.
- **Coal & Bauxite**: Honest evidence-only workflows. No synthetic scores, fabricated probabilities, or placeholder defaults.

---

## 3. Copernicus GLO-30 Terrain Integration

Authentic Copernicus Digital Elevation Model (GLO-30 Public) data has been downloaded and integrated for the Noamundi iron ore corridor:

- **Source DEM Tiles**:
  - `data/dem/Copernicus_DSM_COG_10_N22_00_E085_00_DEM.tif` (44.88 MB, SHA256: `147ec7153ac712cb8d171210fa84fce2ea161efe501ca93b08e27ee3dfed4b08`)
  - `data/dem/Copernicus_DSM_COG_10_N21_00_E085_00_DEM.tif` (44.39 MB)
- **Aligned 3-Band GeoTIFF**:
  - `data/dem/noamundi_10km_copernicus_dem_utm45n.tif` (10.83 MB, SHA256: `b2db7085cf03e04ac872ad044cc77f196aa6c0c525694b693ff45d55b33b302f`)
  - Band 1: Elevation (m ASL, EGM2008 geoid)
  - Band 2: Slope (degrees, Horn finite differences on UTM metric grid)
  - Band 3: Topographic Position Index (TPI, 500m moving window filter)
- **Geomorphic Metrics**:
  - Elevation Range: 364.9 m – 907.3 m (Mean: 483.1 m, Noamundi open pit centroid: 532.9 m)
  - Slope: Mean 6.5°, Steep scarp slopes (> 15°): 8.32%
  - TPI (500m): Prominent ridge crests (> 12 m): 6.41%, Incised valleys (< -12 m): 4.09%
- **Spatial Resolution Notice**: Resampling the native 1 arc-second (~30.87 m) DEM to 20 m UTM grid aligns geometrically with Sentinel-2 L2A 20 m bands, but does **not** create new 20 m terrain information. Effective spatial resolving power remains ~30 m.

---

## 4. End-to-End User Workflow

1. **Location Search**: Search places across India via OpenStreetMap Nominatim geocoding or direct coordinate entry (e.g. `22.15, 85.50` or `21.90, 80.18`).
2. **Select Location**: Map smoothly pans and centers on the selected coordinates.
3. **Select Mineral**: Choose from Coal, Manganese, Iron Ore, or Bauxite.
4. **Choose Radius**: Select 1 km, 5 km, 10 km, 25 km, or 50 km exploration footprint (geometric survey area computed dynamically in $\text{km}^2$).
5. **Run Analysis**: Click **Analyze Selected Area** to trigger the geospatial and evidence pipeline.
6. **Results Dossier**:
   - **Verdict**: Overall status, spatial prospectivity index (when validated), or evidence-only notice.
   - **Geology**: Host stratigraphy, regional terranes, and certified GSI/IBM mine occurrences.
   - **Terrain**: Copernicus GLO-30 elevation, slope, TPI, geomorphic context, and resolution disclaimer.
   - **Evidence Matrix**: Breakdown of remote-sensing, geological, and topographic evidence items.
   - **Decisions**: Exploration readiness, target tier, and recommended field actions.
   - **Sources**: Traceable attributions for satellite, elevation, and geological datasets.
7. **2D & 3D Visualizations**: Toggle between 2D Map, 3D Terrain View, and 3D Prospectivity Mesh.

---

## 5. Local Setup & Startup Commands

### Prerequisites
- Python 3.11+
- Node.js 18+ and npm

### Backend Launch
```bash
# In workspace root (C:\Users\yadar\Downloads\ai_mineral_explo)
.venv\Scripts\python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```
Backend API will be accessible at `http://127.0.0.1:8000` (Interactive Swagger documentation at `/docs`).

### Frontend Launch
```bash
# In frontend directory
cd frontend
npm install
npm run dev
```
Frontend dashboard will be accessible at `http://127.0.0.1:5173`.

### Frontend Production Build
```bash
cd frontend
npm run build
```

---

## 6. Automated Testing & Verification Results

### Python Test Suite (`pytest`)
Execute all tests using the virtual environment:
```bash
# 1. 4-Mineral Activation & Isolation tests (11 tests)
.venv\Scripts\pytest tests/test_coal_iron_bauxite_activation.py

# 2. Copernicus DEM integration tests (12 tests)
.venv\Scripts\pytest tests/test_terrain_integration.py

# 3. Geology and terrain evidence tests (20 tests)
.venv\Scripts\pytest tests/test_geology_terrain.py

# 4. Iron ore pipeline and scientific guardrail tests (11 tests)
.venv\Scripts\pytest tests/test_iron_ore_pipeline.py

# 5. Processed satellite evidence tests (10 tests)
.venv\Scripts\pytest tests/test_evidence_processed.py

# 6. Core intelligence & 3D score integrity tests (17 tests)
.venv\Scripts\pytest tests/test_phase10_intelligence.py tests/test_mineral_eligibility_and_3d_scores.py

# 7. Backend API endpoint tests (16 tests)
.venv\Scripts\pytest tests/test_backend_api.py

# 8. Nationwide satellite raster ingestion tests (20 tests)
.venv\Scripts\pytest tests/test_raster_ingestion.py
```
**Python Test Summary**: **117 tests executed, 117 passed (100% pass rate)**.

### JavaScript Test Suite (`node`)
```bash
node tests/run_all_js_tests.js
```
**JavaScript Test Summary**: **219 tests executed across 19 test files, 219 passed (100% pass rate, 0 failures)**.

---

## 7. Submission Checklist & Security Safeguards

- [x] Zero credentials, passwords, or access tokens committed to the repository.
- [x] Machine-learning prospectivity scores strictly withheld when models are unvalidated.
- [x] Manganese Random Forest model preserved and restricted to its validated footprint (Tile `T44QMK`).
- [x] Iron Ore AI score and confidence remain strictly `null`.
- [x] Coal and Bauxite remain in graceful evidence-only states (`UNAVAILABLE_NO_MODEL`).
- [x] Authentic Copernicus GLO-30 DEM integrated with real SHA256 checksums.
- [x] 2D map, 3D terrain, and conditional 3D prospectivity visualization fully functional.
- [x] Frontend production bundle built successfully without compilation errors.
