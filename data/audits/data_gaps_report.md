# Comprehensive Mineral Exploration Data Gaps & Technical Roadblocks Report
**Project:** AI Mineral Exploration System (India)  
**Date:** October 16, 2026  
**Focus:** Authoritative Data Deficits, Legal Access Barriers, and Remediation Pathways  

---

## 1. Executive Summary

This report documents the genuine physical and regulatory data gaps currently preventing operational machine-learning prospectivity modeling for **Iron Ore**, **Coal**, and **Bauxite**, as well as geographical extrapolation boundaries for **Manganese**.

Under strict scientific integrity standards:
> *"A withheld prediction is vastly preferable to an unreliable or fabricated score."*

Below is the definitive catalog of missing datasets, regulatory constraints, technical impacts, and actionable acquisition steps.

---

## 2. Granular Data Gaps by Commodity

### A. Iron Ore (Singhbhum–North Odisha Iron Ore Craton)

| Missing Dataset | Authoritative Source | Legal Access Status | Technical & Physical Impact | Actionable Remediation Step |
| :--- | :--- | :--- | :--- | :--- |
| **High-Resolution Aeromagnetic Grids** (Total Magnetic Intensity, Analytical Signal, RTP) | Geological Survey of India (NAGMP) | Restricted / Government Security Clearance required | Surface optical remote sensing cannot detect subsurface banded iron formation (BIF/BHQ) concealed beneath oxidized lateritic duricrust. Without magnetic susceptibility gradients, spatial models fail (47.7% CV accuracy). | Execute formal project MoU with GSI Geodata Division under the National Mineral Exploration Policy (NMEP). |
| **1:50,000 Structural Lineament Vectors** (Fault splays, fold hinges) | GSI Bhukosh / State DGMs | Viewable via WMS; bulk shapefile download restricted | High-grade hematite deposits in Singhbhum are structurally controlled by synclinal fold closures. Without vector structures, distance-to-structure feature cannot be computed continuously. | Request GIS shapefile extraction for Survey of India 1:50,000 toposheet quadrangles 73F/8 and 73F/12. |
| **Drill Core Assay Database** (% Fe, % SiO2, % Al2O3, % P) | IBM / State Mining Leases | Proprietary lessee data | Positive training labels are currently restricted to mine lease boundary centroids rather than genuine assay depth intervals. | Ingest public auction block geological reports (Form G2/G3) released on MSTC / state e-auction portals. |

---

### B. Coal (Gondwana Basin Cyclothems)

| Missing Dataset | Authoritative Source | Legal Access Status | Technical & Physical Impact | Actionable Remediation Step |
| :--- | :--- | :--- | :--- | :--- |
| **Subsurface Borehole Core Lithologs** | CMPDI / Coal India Limited (CIL) / SCCL | Confidential exploration data | Optical Sentinel-2 imagery has zero penetration depth. It detects surface opencast spoil, but **cannot detect unmined subsurface coal seams** beneath 20m–500m of barren sandstone/shale. Training on surface pixels alone produces pseudo-correlations with surface land-use changes. | Submit research data request to CMPDI Ranchi for open-file regional exploration blocks. |
| **Coal Seam Correlation & Floor Contours** | CMPDI Basin Reports | Proprietary | 3D prospectivity modeling requires seam floor elevation, roof elevation, and interburden thickness to construct a true volumetric block model. | Utilize open-file CMPDI Coal Inventory volumes for regional formation isopach maps. |
| **Coal Quality Parameters** (Ash %, Moisture %, Gross Calorific Value) | Coal Controller's Organisation (CCO) | Restricted annual returns | Necessary to separate high-grade metallurgical coking coal from non-coking thermal grade coal. | Aggregate published regional seam averages from CMPDI geological memoirs. |

---

### C. Bauxite (Lateritic Patlands & High-Elevation Plateaus)

| Missing Dataset | Authoritative Source | Legal Access Status | Technical & Physical Impact | Actionable Remediation Step |
| :--- | :--- | :--- | :--- | :--- |
| **Laboratory XRF Geochemical Assays** (% Al2O3, % reactive SiO2) | NALCO / Odisha DGM / GSI | Confidential lease reports | Sentinel-2 SWIR Al-OH index identifies aluminous phyllosilicates (gibbsite, kaolinite, halloysite), but **cannot determine whether the ore grade exceeds the economic threshold** ($\text{Al}_2\text{O}_3 \ge 40\%$, reactive $\text{SiO}_2 \le 4\%$). Bauxitic ore cannot be distinguished from sub-grade laterite. | Access public-domain geological reports from recent Odisha bauxite auction blocks (e.g., Kodingamali, Pottangi). |
| **Lateritic Profile Stratigraphic Thickness** (Duricrust, Bauxite zone, Lithomarge clay) | GSI Miscellaneous Publications | Published in print; non-digitized vector tables | Surface remote sensing only sees the topmost 1mm surface layer. The actual bauxite horizon lies beneath the hard ferruginous duricrust (1–3m) and above barren lithomarge clay (5–15m). | Digitize published GSI borehole cross-sections from Bulletin Series A (Economic Geology - Bauxite). |

---

### D. Manganese (Nationwide Transferability Gaps)

| Missing Dataset | Authoritative Source | Legal Access Status | Technical & Physical Impact | Actionable Remediation Step |
| :--- | :--- | :--- | :--- | :--- |
| **Sausar-Equivalent Multi-Tile Calibrated Rasters** | CDSE / Sentinel-2 Archive | Open Access | Current Random Forest model is trained and validated strictly within Sentinel-2 tile `T44QMK`. Transferring weights to other tiles without radiometric cross-calibration and regional ground-truth validation causes covariate shift. | Download and radiometrically normalize neighboring tiles `T44QNL`, `T44QNK`, and `T43QGF` across the full Nagpur-Bhandara belt. |
| **Independent Out-of-Belt Mine Occurrences** (e.g., Shimoga / Sandur belts, Karnataka) | GSI Southern Region | Publicly available in literature | Necessary to test whether the optical spectral model generalizes across different metamorphic facies (Dharwar Craton greenstone vs. Sausar Group granulite/amphibolite). | Curate verified occurrence records for Sandur and Shimoga manganese belts for cross-terrane validation. |

---

## 3. Immediate Technical Path Forward

1. **Maintain Honest Evidence-Only Pipelines**: Display verified occurrences, official lithology, and authentic Copernicus DEM geomorphology while keeping prospectivity scores strictly `null`.
2. **Preserve Nationwide Geographic Eligibility**: Continue executing the shared eligibility service to inform users of exact coverage, downloaded raster status, and model domain boundaries.
3. **Institutional Collaboration**: Use the machine-readable [official_data_inventory.json](file:///C:/Users/yadar/Downloads/ai_mineral_explo/data/audits/official_data_inventory.json) and data contracts to petition for authorized GSI and CMPDI exploration data access.
