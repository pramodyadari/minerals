# Official Geological, Remote Sensing & Terrain Data Audit
**Project:** AI Mineral Exploration System (India)  
**Date of Audit:** October 16, 2026  
**Auditor:** Senior AI/ML Engineer & Geospatial Data Specialist  
**Standard Jurisdiction:** Sovereign Territory of India (SOI / GSI / IBM Baseline)

---

## 1. Executive Summary

This audit assesses the authenticity, legal access status, coordinate reference systems, resolution, and scientific defensibility of all geospatial and geological data sources integrated into the AI Mineral Exploration Platform. 

The primary guiding principle is **scientific and legal defensibility**:
- A dataset discovered in a portal catalogue is **not** recorded as downloaded or processed until physical raster bands or vector geometries exist and are cryptographically verified locally.
- Models are trained **strictly** when verified ground-truth labels and relevant physical measurements exist.
- Where data gaps exist (e.g., restricted aeromagnetic grids, subsurface borehole core logs, laboratory XRF assays), predictions remain **strictly withheld** (`MODEL_UNAVAILABLE` / `EVIDENCE_ONLY`) rather than generated using synthetic numbers or cross-mineral model substitution.

---

## 2. Source-by-Source Data Audit

### A. Geological Survey of India (GSI) & Bhukosh Gateway
- **Official Portals:** [https://www.gsi.gov.in/](https://www.gsi.gov.in/) | [https://bhukosh.gsi.gov.in/](https://bhukosh.gsi.gov.in/)
- **Datasets Audited:**
  1. *National Mineral Inventory (1:2,000,000)*: Publicly accessible geological metallogenic framework. Integrated for all 4 commodities (Sausar Group, Singhbhum Iron Ore Group, Gondwana Supergroup, Eastern Ghats Granulites).
  2. *Detailed 1:50,000 Lithological Vectors & Structural Faults*: Public web viewing available on Bhukosh Map Viewer; bulk programmatic vector download requires institutional credentials and clearance.
  3. *High-Resolution Aeromagnetic Grids (NAGMP)*: Classified under Ministry of Mines Remote Sensing Data Guidelines. Direct public download is restricted.
- **Licensing & Terms:** Free viewing for educational and research exploration; distribution of classified aeromagnetic tensor grids is legally restricted.
- **System Handling:** The platform maintains verified curated JSON registries ([coal_occurrences.json](file:///C:/Users/yadar/Downloads/ai_mineral_explo/data/curated/coal_occurrences.json), [iron_ore_occurrences.json](file:///C:/Users/yadar/Downloads/ai_mineral_explo/data/curated/iron_ore_occurrences.json), [bauxite_occurrences.json](file:///C:/Users/yadar/Downloads/ai_mineral_explo/data/curated/bauxite_occurrences.json)) citing official GSI publications and maintains an explicit data contract stub ([gsi_aeromag_geology_contract.json](file:///C:/Users/yadar/Downloads/ai_mineral_explo/data/curated/gsi_aeromag_geology_contract.json)).

### B. Indian Bureau of Mines (IBM)
- **Official Portal:** [https://ibm.gov.in/](https://ibm.gov.in/)
- **Datasets Audited:**
  1. *Directory of Mining Leases in India (2022–2024)*: Verified coordinates, leaseholder names, and operational status for producing mines across Madhya Pradesh, Jharkhand, Odisha, and Maharashtra.
  2. *Indian Minerals Yearbook*: Commodity overview, national reserve estimates, and metallogenic host descriptions.
- **Licensing:** Public domain government statistical publication.
- **System Handling:** Mining lease centroids are integrated as verified reference markers in the 2D map and evidence dossiers, distinguishing active mining leases from greenfield prospects.

### C. Copernicus Data Space Ecosystem (CDSE)
- **Official Portal:** [https://dataspace.copernicus.eu/](https://dataspace.copernicus.eu/)
- **Datasets Audited:**
  1. *Sentinel-2 MSI Level-2A BOA Surface Reflectance*:
     - Tile `T44QMK` (Balaghat corridor): Multi-spectral bands B02, B03, B04, B08, B11, B12 processed at 10m/20m. Cloud cover < 0.5%.
     - Tile `T45QUE` (Noamundi iron ore corridor): Sensing date 2026-10-10. Cloud cover 1.15%.
     - Scene classification layers (SCL) applied to mask clouds, cloud shadows, and water bodies.
- **Licensing:** Open access under the European Union Copernicus Data Policy.
- **System Handling:** Seamless fallback between live CDSE OData API queries and cached offline multi-band rasters, computing authentic spectral indices (ferric iron B04/B02, ferrous iron B12/B11, Al-OH clay B11/B12).

### D. Copernicus Digital Elevation Model (GLO-30 Public)
- **Official Registry:** [https://registry.opendata.aws/copernicus-dem/](https://registry.opendata.aws/copernicus-dem/)
- **Datasets Audited:**
  - Tile `Copernicus_DSM_COG_10_N22_00_E085_00_DEM.tif` (44.88 MB, SHA256: `147ec7153ac712cb8d171210fa84fce2ea161efe501ca93b08e27ee3dfed4b08`)
  - Tile `Copernicus_DSM_COG_10_N21_00_E085_00_DEM.tif` (44.39 MB)
  - Aligned UTM Zone 45N raster: `noamundi_10km_copernicus_dem_utm45n.tif` (10.83 MB, SHA256: `b2db7085cf03e04ac872ad044cc77f196aa6c0c525694b693ff45d55b33b302f`)
- **Properties:**
  - Vertical datum: EGM2008 geoid height in meters.
  - Native spatial resolution: 1 arc-second (~30m).
  - Derived bands: Band 1 (Elevation m ASL), Band 2 (Slope in degrees via Horn's method), Band 3 (Topographic Position Index with 500m moving window).
- **Licensing:** Free, full, and open Copernicus DEM Policy.
- **System Handling:** Geomorphic evidence engine extracts real elevations (Noamundi open pit centroid: 532.9m ASL; regional range 364.9m – 907.3m).

### E. Subsurface Coal & Bauxite Assay Data (CMPDI, SCCL, NALCO)
- **CMPDI / SCCL Core Drill Logs:** Proprietary exploration data owned by Coal India Limited / SCCL. Optical sensors see only surface spoil and bench cuts; underground coal seams cannot be sensed through overburden.
- **NALCO Bauxite Drill Core Assays:** Laboratory XRF geochemical assays ($>45\%\ \text{Al}_2\text{O}_3$, $<3\%\ \text{reactive}\ \text{SiO}_2$). Optical SWIR Al-OH absorption cannot quantify chemical grade.
- **System Handling:** Status maintained as `ACCESS_RESTRICTED` / `UNAVAILABLE_NO_MODEL`. No synthetic assays or fabricated labels are permitted.

---

## 3. Data Integrity & Verification Summary

| Dataset ID | Source | Mineral | Local File Status | Verified Checksum | Suitability |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `COP_DEM_GLO30_NOAMUNDI` | ESA / Copernicus | All | Downloaded (3 files, 100 MB) | `b2db7085cf...` | Evidence Only |
| `CDSE_SENTINEL2_L2A_T44QMK` | ESA / CDSE | Manganese | Downloaded (Local Archive) | Verified | Training & Validation |
| `CDSE_SENTINEL2_L2A_T45QUE` | ESA / CDSE | Iron Ore | Downloaded (Local Cache) | `c86f9e59d2...` | Evidence Only |
| `GSI_NMI_CURATED_OCCURRENCES` | GSI / IBM | All 4 | Downloaded (Curated JSON) | Verified | Evidence & Validation |
| `GSI_AEROMAG_LINEAMENT_GRID` | GSI Geodata | Iron Ore | Access Restricted | Contract Stub | Pending Clearance |
| `CMPDI_SCCL_BOREHOLE_LOGS` | CMPDI / CIL | Coal | Access Restricted | None | Pending Permit |
| `NALCO_GSI_BAUXITE_XRF_ASSAYS` | NALCO / DGM | Bauxite | Access Restricted | None | Pending Permit |
