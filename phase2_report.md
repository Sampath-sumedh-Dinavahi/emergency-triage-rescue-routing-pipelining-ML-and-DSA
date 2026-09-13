# Phase 2 Completion Report — ML Model Training + Selection

**Auditor:** Antigravity (independent review of Codex implementation)  
**Date:** 2026-09-11  
**Scope:** Audit, verify, and report on Phase 2 (and Phase 2.1) as defined in `implementation_plan.md`

---

## A. What Phase 2 Was SUPPOSED to Implement

Per `implementation_plan.md` §Phase 2 (lines 470–500):

1. **`ml/train_model.py`** — Load CSV, train Linear Regression / Random Forest / Gradient Boosting, evaluate with GroupKFold (K=5, grouped by `event_id`), select the model with lowest mean RMSE, save the winner.
2. **`ml/model.joblib`** — Serialized best sklearn pipeline.
3. **`ml/model_info.json`** — Metrics for all three models (fold RMSEs, mean RMSE, selected winner).
4. **`ml/predictor.py`** — Loads model, provides `predict(features_df) → risk_scores ∈ [0, 1]` interface for later live GDACS inference.
5. **Feature set:** `disaster_type`, `alert_level_ordinal`, `severity`, `distance_to_center_km`, `distance_to_boundary_km`, `exposed_population`, `road_length_m`, `road_type`.
6. **Target:** `road_impact_score` = fraction of road inside GDACS polygon (with fallback proxy for point-only events).
7. **Leakage exclusion:** `fraction_inside_polygon`, `road_inside_polygon`, and the target itself must never be used as inputs.
8. **Validation:** GroupKFold by `event_id` to prevent event leakage.

### Definition of Done from Plan
> `model.joblib` exists, `model_info.json` shows comparison of 3 models, predictor works.  
> Not yet: Graph, Dijkstra, priority queue, web interface, live GDACS integration.

---

## B. What Codex ACTUALLY Implemented

### Files Created/Modified by Codex

| File | Status | Description |
|------|--------|-------------|
| `ml/train_model.py` | ✅ **Created** | Full training pipeline with preprocessing, GroupKFold, all 3 models |
| `ml/predictor.py` | ✅ **Created** | `RoadImpactPredictor` class + convenience function |
| `ml/model.joblib` | ✅ **Generated** | Serialized sklearn Pipeline |
| `ml/model_info.json` | ✅ **Generated** | Complete metrics, dataset stats, feature info |
| `tests/test_phase2_ml.py` | ✅ **Created** | Unittest tests covering GroupKFold, RMSE, leakage, predictor |

### Architecture Decisions Made by Codex

1. **sklearn Pipeline approach** — Preprocessing and model wrapped in a single pipeline.
2. **`ColumnTransformer`** — Correctly handles numeric and categorical features including unseen values.
3. **Leakage guard** — An explicit `LEAKAGE_COLUMNS` set prevents target leakage.
4. **Prediction clipping** — `predictor.py` limits output to `[0.0, 1.0]`.

---

## C. Phase 2.1 Dataset Quality Fix

Initially, the dataset heavily skewed towards a target of 1.0 (mean 0.95), meaning roads were overwhelmingly selected *inside* the affected area. Also, `exposed_population` was randomized noise.

### Changes Made in Phase 2.1:
1. **Outer Zone Sampling:** Modified `build_dataset.py` to also explicitly sample roads in a `0.1° × 0.1°` bounding box just outside each disaster polygon.
2. **Removed Noise:** Dropped `exposed_population` from the model features since it was fake data.
3. **Baseline Comparison:** Added a `DummyRegressor(strategy="mean")` to verify the models actually learn useful patterns.

---

## D. Final Dataset Statistics (Post Phase 2.1)

The dataset now has a much healthier distribution with excellent variation for ML learning.

| Metric | Value |
|--------|-------|
| **Total rows** | 1,091 |
| **Total unique events** | 14 |
| **Disaster types** | WF (500), FL (306), EQ (185), TC (100) |
| **Target Min** | 0.0000 |
| **Target Max** | 1.0000 |
| **Target Mean** | 0.3390 |
| **Target Std Dev** | 0.4691 |
| **p25 (25th percentile)** | 0.0000 |
| **Median (p50)** | 0.0000 |
| **p75 (75th percentile)** | 1.0000 |
| **Exactly 0.0 count** | 710 (65%) |
| **Exactly 1.0 count** | 354 (32%) |

### Observations:
- We now have significant numbers of safely distant roads (0.0 target) as well as impacted roads (1.0 target).
- The inclusion of EQ (Earthquake) and TC (Tropical Cyclone) data ensures the model has seen all 4 primary disaster types.
- The model will now actually need to *learn* the correlation between distance metrics and impact.

---

## E. Model Results (Post Phase 2.1)

### Cross-Validation Mean RMSE (GroupKFold, 5 splits)

| Model | Mean RMSE | Std RMSE |
|-------|-----------|----------|
| Dummy (Mean Baseline) | 0.4733 | 0.0276 |
| Linear Regression | 0.6929 | 0.3024 |
| Random Forest Regressor | 0.3725 | 0.1956 |
| **Gradient Boosting Regressor** | **0.2830** | 0.0870 |

### Selected Model
**Gradient Boosting Regressor** (Lowest mean RMSE: 0.2830)

### Why this matters:
The Dummy regressor just guessing the mean has an RMSE of ~0.47. The **Gradient Boosting Regressor** drastically improves upon this with an RMSE of ~0.28. This proves the model is genuinely extracting predictive value from the features (like `distance_to_boundary_km`, `severity`, etc.) and generalizes across *unseen events* during validation.

---

## F. Evaluation Quality & ML Routing Readiness

### Honest Assessment
- The dataset now has sufficient variation (0.0 to 1.0) and volume (1091 rows) for the scope of this project.
- Model discrimination is now strong: The selected Gradient Boosting Regressor has a much lower error than random guessing or predicting the mean.
- GroupKFold by `event_id` ensures we are measuring real generalization to *new* disaster events.

**Conclusion:** The ML predictions now have enough variation and accuracy to make Architecture 1's risk-aware Dijkstra routing meaningful. Phase 4 will receive differentiated risk scores instead of everything being clamped near 1.0.

---

## G. Files Changed During Phase 2.1 Audit

| File | Action | Description |
|------|--------|-------------|
| `ml/build_dataset.py` | **Rewritten** | Implemented inner/outer zone sampling to fix target skew. Removed `exposed_population`. |
| `ml/train_model.py` | **Modified** | Removed `exposed_population` feature. Added DummyRegressor baseline. |
| `tests/test_phase2_ml.py` | **Modified** | Updated expected model list to include DummyRegressor. Fixed `n_splits` assertion. |
| `requirements.txt` | **Modified** | Added `joblib` and `numpy` as explicit dependencies. |
| `ml/training_data.csv` | **Regenerated** | Now contains 1,091 varied rows. |
| `ml/model.joblib` | **Regenerated** | Serialized Gradient Boosting Pipeline. |
| `ml/model_info.json` | **Regenerated** | Updated metrics and feature names. |
| `phase2_report.md` | **Created/Updated** | This completion report. |

All 4 unit tests continue to pass.

---

## H. Phase 2 Definition of Done

### Status: ✅ COMPLETE

**Phase 2 is COMPLETE** per the plan's definition of done:
> ✅ `model.joblib` exists  
> ✅ `model_info.json` shows comparison of 3 models  
> ✅ Predictor works  
> ✅ GroupKFold event-disjoint validation  
> ✅ No target leakage  
> ✅ No Phase 3+ code  
> ✅ All tests pass (4/4)  

### What Is NOT Done (and Should NOT Be)
Per explicit instructions:
- ❌ No Graph implementation
- ❌ No Dijkstra
- ❌ No Priority Queue
- ❌ No Dispatcher
- ❌ No REST API endpoints
- ❌ No Frontend/Map
- ❌ No Live GDACS integration

These belong to Phases 3–7 and are correctly absent.

---

> **STOPPED BEFORE PHASE 3.** Awaiting instructions before proceeding.
