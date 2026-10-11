# AI Mineral Exploration and Analysis System

An integrated, evidence-based geographical mineral prospectivity dashboard and 4-class rock specimen classification system built with **React**, **Vite**, **Leaflet**, **FastAPI**, and **PyTorch**.

---

## 1. System Overview & Core Philosophy

The system provides dual capabilities with clear scientific demarcation:
1. **Geographical Mineral Prospectivity Analysis**: Geospatial exploration mapping across satellite/geological footprints, calculating prospectivity indices based on multi-spectral features without claiming certainty where data is absent.
2. **AI Specimen Image Classification**: A genuine PyTorch 4-class Convolutional Neural Network trained on rock and ore specimens. The application explicitly distinguishes visual rock identification from subsurface geological occurrences.
3. **Interactive 2D / 3D Terrain Exploration**: A dual-engine mapping interface providing both a lightweight 2D Leaflet cartographic map and an interactive 3D terrain elevation model powered by MapLibre GL JS and AWS Open Data (USGS 3DEP / SRTM Terrarium DEM).

### Strictly Fixed Mineral Classes (Exactly Four)
The system supports **strictly four mineral classes** across all frontend cards, API payloads, model weights, and pipelines:
1. **Coal** (`C`)
2. **Manganese** (`Mn`)
3. **Iron Ore** (`Fe`)
4. **Bauxite** (`Al`)

*No fifth mineral class exists or will ever be added.*

---

## 2. Architecture & Tech Stack

```
ai_mineral_explo/
├── frontend/                     # React + Vite + Leaflet + MapLibre GL 3D
│   ├── src/
│   │   ├── components/
│   │   │   ├── Header.jsx
│   │   │   ├── LocationSearch.jsx
│   │   │   ├── InteractiveMap.jsx       # Dual-engine 2D/3D container with switcher
│   │   │   ├── TerrainMap3D.jsx         # 3D Terrain elevation viewer (MapLibre GL)
│   │   │   ├── MineralSelector.jsx      # Exactly 4 mineral selection cards
│   │   │   ├── RadiusSelector.jsx       # 1, 5, 10, 25 km pills + area in km²
│   │   │   ├── ResultsPanel.jsx         # Explainable results dossier with tabs
│   │   │   └── SpecimenClassifierModal.jsx
│   │   ├── App.jsx
│   │   ├── index.css                    # Earthy ancient-map design system
│   │   └── main.jsx
│   ├── package.json
│   └── vite.config.js
│
├── backend/                      # Python + FastAPI REST API
│   ├── app/
│   │   ├── main.py               # REST endpoints (/health, /minerals, /analyze, /classify-image)
│   │   ├── mineral_service.py    # Explainable geographical prospectivity & evidence engine
│   │   └── vision_service.py     # Specimen PyTorch model loader & inference
│   └── requirements.txt
```
│
├── ai/                           # AI Model Pipeline
│   ├── dataset/                  # Structured dataset (train/, validation/, test/)
│   │   ├── train/{coal, manganese, iron_ore, bauxite}
│   │   ├── validation/{coal, manganese, iron_ore, bauxite}
│   │   └── test/{coal, manganese, iron_ore, bauxite}
│   ├── dataset_validator.py      # Dataset integrity, corruption & leakage checks
│   ├── train.py                  # PyTorch 4-class training script
│   ├── evaluate.py               # Test split evaluation (precision, recall, F1, confusion matrix)
│   └── predict.py                # Command-line specimen inference
│
├── models/                       # Model Weights & Reports
│   ├── mineral_image_classifier.pth             # PyTorch CNN weights
│   ├── mineral_image_classifier_metadata.json   # Training hyperparams & validation accuracy
│   ├── evaluation_report.json                   # Independent test metrics & confusion matrix
│   └── manganese_random_forest.pkl              # Sentinel-2 Tile T44QMK trained model
│
└── tests/
    └── test_backend_api.py       # Automated integration test suite
```

---

## 3. Dashboard Workflow

1. **Step 1: Search for a Location**:
   - Prominent search box at top of map.
   - Live OpenStreetMap Nominatim geocoding suggestions.
   - Coordinate search support (e.g. `21.85, 80.25`).
2. **Step 2: Interactive Map**:
   - Leaflet map with OpenStreetMap tiles.
   - Pan, zoom, click any random location to select coordinates.
3. **Step 3: Live GPS Location**:
   - "Use My Current Location" button requests browser GPS permission on click.
   - Graceful permission denial and timeout error handling.
4. **Step 4: Mineral Selection**:
   - Exactly 4 cards: **Coal**, **Manganese**, **Iron Ore**, **Bauxite**.
   - Clear icon, elemental symbol, status badge, and single-selection behavior.
5. **Step 5: Search Radius**:
   - 1 km ($3.14\text{ km}^2$), 5 km ($78.54\text{ km}^2$), 10 km ($314.16\text{ km}^2$), 25 km ($1963.50\text{ km}^2$).
   - Dynamic translucent circle centered on target location.
6. **Step 6: Analyze Button**:
   - Validates coordinates, mineral, and radius before sending request to `/analyze`.
   - Prevents duplicate requests with visual loading spinner.
7. **Step 7: Results Dashboard**:
   - Location name, Lat/Lon, Mineral, Radius, Status.
   - AI prediction / relative spatial prospectivity index.
   - Honest confidence notes: Manganese is explicitly marked `NOT CALIBRATED` with explanations.
   - For Coal, Iron Ore, and Bauxite: returns `"INSUFFICIENT_DATA"` with the honest notice `"Insufficient data for a reliable geographical assessment"`.
   - Authoritative data sources and limitations warnings.
8. **Rock Specimen Classifier Modal**:
   - Upload rock photo to classify between the 4 mineral classes via PyTorch CNN.
   - Displays probabilities and explicit disclaimer that rock classification does not prove underground deposit presence.

---

## 4. Running the Application

### Backend Setup & Launch
```bash
# In the project root directory
py -3.11 -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```
Backend runs at `http://127.0.0.1:8000` (Docs available at `/docs`).

### Frontend Setup & Launch
```bash
cd frontend
npm install
npm run dev -- --host 127.0.0.1 --port 5173
```
Frontend runs at `http://127.0.0.1:5173`.

---

## 5. Verification & Testing

Run the automated backend test suite:
```bash
py -3.11 -m pytest tests/test_backend_api.py -v
```
All 7 unit and integration tests pass:
- `test_health_endpoint` (PASS)
- `test_minerals_endpoint` (PASS)
- `test_analyze_manganese_inside_tile` (PASS)
- `test_analyze_manganese_outside_tile` (PASS)
- `test_analyze_coal_awaiting_data` (PASS)
- `test_analyze_invalid_mineral` (PASS)
- `test_classify_image_endpoint` (PASS)
