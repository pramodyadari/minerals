# INDEPENDENT VALIDATION DATA CONTRACT (PHASE 8)

## 1. Scientific Objective
The primary scientific objective of this contract is **Independent Deposit Validation**.
Independent validation measures the model's true external generalization capability on documented mineral deposits that were **completely excluded** from training, validation, spatial blocking, feature selection, threshold tuning, and probability calibration.

---

## 2. Hard Requirements for Ingestion

Every independent validation record must satisfy the following strict requirements:

| Field | Type | Validation Constraint | Description |
| :--- | :--- | :--- | :--- |
| `mineral` | String | Must equal `"manganese"` (case-insensitive) | Strict commodity identity enforcement |
| `latitude` | Float | `21.3667 <= lat <= 22.4333` (within T44QMK) | WGS84 decimal latitude |
| `longitude` | Float | `79.9333 <= lon <= 80.6515` (within T44QMK) | WGS84 decimal longitude |
| `deposit_id` | String | Unique, non-empty identifier | Official lease or occurrence code |
| `deposit_name` | String | Must NOT contain `"Ghondi"` | Distinct mine or occurrence name |
| `source` | String | Official scientific/government agency | e.g. GSI, IBM, USGS, or certified drilling assay |
| `source_url` | String | URL or bibliographic reference | Traceable authoritative origin |
| `geographic_separation_m` | Float | Minimum **500 meters** from Ghondi training boundary | Prevents spatial autocorrelation leakage |
| `independent_status` | String | Must be `"VERIFIED_INDEPENDENT"` | Contract compliance flag |

---

## 3. Strict Rejection & Leakage Rules

Any record or dataset violating ANY of the following rules **MUST BE IMMEDIATELY REJECTED** and raise `IndependentValidationLeakageError`:

1. **No Overlap with Training Data**:
   Any coordinate within 500 meters of any training sample (1,681 positive pixels from Ghondi Mine or 1,681 pseudo-absence points) will cause immediate dataset rejection.
2. **No Model-Derived Candidates**:
   Occurrences derived from the model's own prospectivity surface (`outputs/manganese_prospectivity.tif`), connected components (`high_prospectivity_zones.csv`), or XAI leaf nodes are strictly forbidden as ground truth.
3. **No Synthetic Barren Pseudo-Absences**:
   If the independent dataset consists only of positive deposit points, **no synthetic negative points may be manufactured**. Classification metrics requiring negative controls (specificity, precision, ROC-AUC) must be disabled, and only the **Independent Positive Occurrence Test** (distribution, median prospectivity, threshold recall) reported.
4. **Model Immutability**:
   The Random Forest model (`models/manganese_random_forest.pkl`) must NOT be retrained, fine-tuned, or calibrated against the independent dataset. Its SHA-256 hash must be verified before and after evaluation.

---

## 4. Handling Single-Class Independent Ground Truth

In real mineral exploration, published deposit databases contain documented positive occurrences (mines, prospects, outcrops) but rarely contain verified barren non-deposits.
* **Standard practice**: Ingest verified positive deposits only.
* **Prohibited action**: Fabricating synthetic negative points to calculate a false ROC-AUC.
* **Reporting format**:
  * Total independent deposits tested ($N$)
  * Predicted Spatial Prospectivity Index (Minimum, Median, Mean, Maximum)
  * Proportion of independent deposits with score $\ge 50\%$ (Moderate) and $\ge 75\%$ (High)
  * Mandatory disclaimer: *"Independent positive occurrence data does not contain verified barren controls; classification metrics requiring both classes are not available."*
