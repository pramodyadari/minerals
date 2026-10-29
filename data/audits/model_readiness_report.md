# Mineral Model Readiness & Scientific Validation Report
**Project:** AI Mineral Exploration System (India)  
**Evaluation Standard:** Independent Spatial & Stratigraphic Validation  
**Date:** October 16, 2026  

---

## 1. Overview of Mineral Model Status

The platform maintains four distinct mineral workflows. Each workflow is governed by strict scientific guardrails that separate **evidence availability** from **model prediction availability**.

```
                +-------------------------------------------------------------+
                |              MINERAL MODEL READINESS MATRIX                 |
+---------------+---------------------+-------------------+-------------------+-------------------+
| Commodity     | Evidence Pipeline   | Spatial CV Metric | Model Status      | Prediction Output |
+---------------+---------------------+-------------------+-------------------+-------------------+
| Manganese     | OPERATIONAL         | Validated T44QMK  | VALIDATED_ACTIVE  | RELATIVE INDEX %  |
| Iron Ore      | OPERATIONAL (DEM)   | Failed (47.7% Acc)| NOT_VALIDATED     | STRICTLY NULL     |
| Coal          | OPERATIONAL         | Insufficient Logs | UNAVAILABLE       | STRICTLY NULL     |
| Bauxite       | OPERATIONAL         | Insufficient XRF  | UNAVAILABLE       | STRICTLY NULL     |
+---------------+---------------------+-------------------+-------------------+-------------------+
```

---

## 2. Mineral-Specific Validation Audits

### A. Manganese (Strategic Ferroalloy)
- **Model Architecture:** Random Forest Classifier (100 estimators, max depth 12).
- **Spatial Domain:** Sentinel-2 Tile `T44QMK` (Balaghat–Nagpur Manganese Belt).
- **Input Features:** 6 surface reflectance bands (B02, B03, B04, B08, B11, B12) + Derived Ratios (VNIR alteration, manganese gossan index).
- **Validation Results:**
  - Validated against 20 certified GSI/IBM open-pit and underground mines (Bharweli, Balaghat, Ukwa, Tirodi, Dongri Buzurg, Chikla).
  - Spatial cross-validation within the Balaghat corridor confirms strong rank-order correlation with known mineralized trends.
- **Scientific Guardrail:** 
  - Output is documented as an **uncalibrated relative prospectivity index (0–100%)**, **not** a calibrated deposit probability.
  - Predictions are strictly gated to Tile `T44QMK`. Queries outside `T44QMK` return `OUTSIDE_TRAINING_FOOTPRINT` / `MODEL_UNAVAILABLE` to prevent invalid geographical extrapolation.

### B. Iron Ore (Ferrous Metal Ore — Noamundi & Singhbhum Craton)
- **Investigative Dataset:** 16,033 pixels curated across 5 verified mine leases (Noamundi, Joda East, Kiriburu, Gua, Bolani) and unmineralized background sectors ([iron_ore_training_curated.csv](file:///C:/Users/yadar/Downloads/ai_mineral_explo/data/curated/iron_ore_training_curated.csv)).
- **Audit of Random Holdout vs. Spatial Leave-Deposit-Out Validation:**
  - *Random Train/Test Split (80/20)*: 83.5% apparent accuracy, Macro F1: 0.82.
  - *Leave-Deposit-Out Spatial Cross-Validation (Grouping by Deposit)*:
    - **Spatially Blocked Accuracy:** **47.66%** (worse than random coin toss)
    - **Macro F1 Score:** **0.31**
    - **ROC-AUC:** **0.504**
- **Root-Cause Scientific Analysis:**
  1. *Spatial Autocorrelation Leakage*: Random train/test splitting samples pixels from the exact same open-pit mine bench into both train and test sets, artificially inflating metrics.
  2. *Regolith & Laterite Confounding*: Band 4 / Band 2 (ferric iron oxide) and Band 12 / Band 11 (ferrous iron) ratios detect surface iron-stained lateritic crusts, ferruginous sandstones, and hematitic float indiscriminately. They cannot penetrate beneath the weathered duricrust to detect commercial high-grade hematite ($>62\%\ \text{Fe}$).
  3. *Missing Subsurface Geophysics*: Commercial hematite ore bodies in the Singhbhum Iron Ore Group (IOG) are concentrated along synclinal keel structures and fault splays. Without GSI aeromagnetic tensor grids (Total Magnetic Intensity and Analytical Signal) and 1:50,000 structural vectors, optical ML models cannot generalize across deposits.
- **Readiness Decision:** `UNAVAILABLE_INSUFFICIENT_SPATIAL_VALIDATION`. Numerical AI prospectivity scores remain **strictly withheld (`null`)**. The platform exposes authentic Copernicus GLO-30 DEM elevation (532.9m ASL at Noamundi pit centroid), slope (6.5°), and TPI ridge crest metrics as evidence without fabricated predictions.

### C. Coal (Energy Commodity — Gondwana Basins)
- **Geological Setting:** Permian Gondwana grabens (Damodar, Godavari, Mahanadi, Son, Wardha valleys) with Barakar and Raniganj coal-bearing cyclothems.
- **Remote Sensing Limitations:**
  - Optical Sentinel-2 imagery detects carbonaceous shales and coal spoil in active opencast pits (e.g., Manuguru, Jharia).
  - However, **optical sensors cannot detect unmined subsurface coal seams** situated beneath 20m to 500m of barren sandstone and shale overburden.
- **Data Gap:** Defensible coal prospectivity modeling requires CMPDI / SCCL borehole core lithologs (seam depth, thickness, ash percentage, gross calorific value).
- **Readiness Decision:** `UNAVAILABLE_NO_MODEL`. No synthetic machine-learning scores are produced. The evidence pipeline provides verified colliery occurrence registries, Gondwana graben boundary audits, and surface reflectance indicators with clear disclaimers that subsurface drilling is mandatory.

### D. Bauxite (Aluminum Lateritic Ore — High-Elevation Plateaus)
- **Geological Setting:** Tertiary lateritic bauxite capping high-elevation granulite/khondalite plateaus and Deccan basalt patlands (>900m ASL in Eastern Ghats and Maikala Range).
- **Remote Sensing Limitations:**
  - Sentinel-2 SWIR bands (B11/B12) detect molecular Al-OH vibrational absorption typical of gibbsite and kaolinite.
  - However, **multispectral satellite sensors cannot quantify the chemical ratio of $\text{Al}_2\text{O}_3$ to reactive $\text{SiO}_2$ and $\text{Fe}_2\text{O}_3$**, which defines economic bauxite ore ($>40\%\ \text{Al}_2\text{O}_3, <4\%\ \text{reactive}\ \text{SiO}_2$) versus barren ferruginous laterite.
- **Data Gap:** Downhole laboratory XRF geochemical assays are required to distinguish commercial ore from sub-economic laterite caps.
- **Readiness Decision:** `UNAVAILABLE_NO_MODEL`. Numerical prospectivity scores remain **strictly withheld (`null`)**. The evidence pipeline evaluates high-elevation geomorphology, verified deposit provenance (NALCO Panchpatmali, Baphlimali), and SWIR absorption with explicit scientific caveats.

---

## 3. Summary of Operational Guardrails

1. **Zero Cross-Mineral Model Substitution**: The Manganese model is never queried or reused to predict Iron Ore, Coal, or Bauxite.
2. **Explicit Null Predictions**: Unmodeled commodities return `prediction: null` and `confidence_score: null`. Fallback defaults (e.g. hardcoded 40%) are strictly prohibited.
3. **Calibrated 3D Visualization Guard**: The Three.js 3D prospectivity mesh is rendered **strictly** when a validated, calibrated prediction grid exists (`is_calibrated: true`). For all other commodities and unvalidated regions, a fallback notice is rendered with a 1-click option to switch to 3D Terrain View.
