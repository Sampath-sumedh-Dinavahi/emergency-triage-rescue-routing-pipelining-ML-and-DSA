# Phase 4 Completion Report — Dispatcher + ML Integration + Live GDACS

**Author:** Antigravity  
**Date:** 2026-09-11  
**Scope:** Implement Phase 4 Pipeline Orchestration as defined in `implementation_plan.md`.

---

## 1. What Phase 4 Was SUPPOSED to Implement

Per `implementation_plan.md` Phase 4 §:
- `services/dispatcher.py` — central orchestrator that glues the pipeline together: loads a disaster, fetches the road network, predicts risk scores, manages the emergency queue, and handles dispatching.
- `services/emergency_generator.py` — generates plausible, simulated emergency requests near the loaded disaster to demonstrate priority queue functionality.
- Apply ML predictions to graph edge weights via the formula `weight = length_km × (1 + β × predicted_impact)` where β = 9.0.
- Compare normal (raw distance) routing against risk-aware routing during dispatch.
- Ensure gracefulness with live GDACS and OSM Overpass APIs.

---

## 2. What Was Implemented

All requested orchestration logic was implemented in Python.

- **`Dispatcher` Class**: 
  - Retrieves live event details and affected-area polygons directly from the GDACS API.
  - Dynamically estimates the appropriate OSM bounding box based on the GDACS polygon size or historical proxy distances.
  - Computes exact match ML features (`distance_to_center_km`, `distance_to_boundary_km`, etc.) on the fly using the haversine formula and Shapely geometries.
  - Passes these features to the pre-trained Gradient Boosting model (`model.joblib`) via `predictor.py` to get predicted road impact values between 0.0 and 1.0. The predictor is fully reusable and runs its prediction batch dynamically for whatever road features are loaded.
  - Maintains **two** separate instances of `Graph`: `risk_graph` and `normal_graph`.
  - Maintains explicit state for `rescue_base_node` via `set_rescue_base()` (defaulting to the deterministic minimum node ID if not explicitly set) to ensure paths anchor correctly.
- **Emergency Generator**: 
  - Uses the set of actual fetched nodes from OSM to seed simulated emergencies (`EmergencyRequest`).
  - Assigns severity, medical urgency, and randomly staggered creation times to trigger the waiting-time bonus in the priority queue.
- **Dispatch Logic**:
  - `dispatch_next()` pops from the priority queue.
  - Calls Dijkstra's algorithm twice (once for the risk-aware graph, once for the normal graph) to prove path diversion.
  - Explicitly handles unreachable nodes and integrates manual road blocking across both graphs simultaneously.

---

## 3. End-to-End Data Flow

1. **Input**: User calls `dispatcher.load_disaster(event_type='FL', event_id='12345')`.
2. **GDACS API**: Fetches event metadata (severity, alert level) and GeoJSON polygon.
3. **OSM Overpass**: Fetches road network (`way` elements) bounded around the disaster.
4. **Feature Extraction**: Shapely measures distances to the disaster center and boundary polygon.
5. **ML Prediction**: Scikit-Learn pipeline transforms features and predicts `predicted_impact` ∈ [0,1].
6. **Graph Creation**: Edges added to `normal_graph` and `risk_graph` with appropriate weights.
7. **Simulation**: Random valid nodes are assigned emergencies and pushed to the `EmergencyPriorityQueue`.
8. **Dispatch**: `dispatcher.dispatch_next()` routes the rescue base to the highest-urgency emergency via Dijkstra.

---

## 4. How ML Predictions Transform Graph Weights

The live GDACS data and the fetched OSM roads are merged into a Pandas DataFrame mirroring the training dataset.

The ML Predictor outputs a `predicted_impact` from `0.0` (low predicted exposure) to `1.0` (high predicted exposure/inside affected zone). Note that this score represents relative spatial exposure based on historical GDACS perimeters, not confirmed physical road damage or blockage.

We calculate edge weight using the specification-defined formula (β = 9.0):

```python
risk_weight = length_km * (1.0 + 9.0 * predicted_impact)
```

- If `predicted_impact` is 0.0, the weight equals the literal physical road length.
- If `predicted_impact` is 1.0, traversing this road costs **10x** its normal distance, heavily encouraging Dijkstra to route around the predicted danger zone.

---

## 5. Priority Queue and Dijkstra Integration

- Simulated requests are created via `EmergencyRequest`. The urgency score is calculated immediately based on severity, people affected, and wait time.
- Requests are pushed to `EmergencyPriorityQueue` (a max-heap built on `heapq`).
- `dispatch_next()` calls `extract_max()` to get the most urgent request.
- The `location_node` of the request is passed as the destination to `find_shortest_path` (Dijkstra) against the `rescue_base_node`.

---

## 6. Example Dispatch Result

```json
{
  "status": "dispatched",
  "request_id": "4b6b47c6-11f4-4e2b-b9d9-abc3d1",
  "target_node": "314159265",
  "urgency_score": 57.21,
  "risk_aware_route": {
    "path": ["123", "456", "789", "314159265"],
    "total_cost": 42.15
  },
  "normal_route": {
    "path": ["123", "999", "314159265"],
    "total_distance_km": 12.0
  },
  "routes_differ": true
}
```

---

## 7. Normal vs Risk-Aware Route Comparison

By running `find_shortest_path` simultaneously on both graphs, the Dispatcher guarantees comparison.
If the shortest physical route passes through the disaster center (where `risk_score` ~ 0.9), its `risk_aware_route.total_cost` skyrockets. 
Dijkstra on the `risk_graph` organically discovers a longer physical bypass that avoids the high-risk penalty multiplier, returning a different `path`. The frontend (Phase 5) will be able to render both simultaneously.

---

## 8. Tests and Results

A comprehensive integration test (`test_phase4_integration.py`) was created.
To avoid making the CI pipeline brittle to network conditions, `GDACSClient` and `OSMClient` were strictly mocked using `unittest.mock.patch`.

**Tested Scenarios**:
1. GDACS and OSM data are loaded and parsed successfully.
2. ML predictions influence edge weights.
3. Priority queue handles sorting and insertion correctly.
4. Dijkstra calculates a bypass route when the shortest physical route is highly dangerous.
5. Road blocking instantly severs paths in both graphs.
6. Unreachable detection triggers gracefully when surrounded by blocked edges.

**Results:** `python -m pytest tests/` completed with 12/12 passing tests across ML, DSA, and Orchestration.

---

## 9. External API / Fallback Behaviour

- **GDACS Missing Polygon**: If GDACS fails to return a polygon (e.g. for a point-source Earthquake), `has_polygon` gracefully defaults to False. Bounding boxes are determined via `get_derived_radius_km` proxy, and `distance_to_boundary_km` defaults to -1.0.
- **Overpass Limitations**: Bounding boxes are strictly capped at `max_span = 0.1` degrees (approx. 11x11 km) to avoid Overpass timeout errors (504s).

---

## 10. Files Changed

| File | Action | Description |
|------|--------|-------------|
| `services/emergency_generator.py` | **Created** | Deterministically spawns plausible emergencies on valid graph nodes. |
| `services/dispatcher.py` | **Created** | The central pipeline orchestrator. Merges APIs, ML, and algorithms. |
| `tests/test_phase4_integration.py` | **Created** | Mocked integration test of the full dispatch pipeline. |
| `phase4_report.md` | **Created** | This architecture and implementation summary. |

---

## 11. Known Behaviors

- **Rescue Base Selection**: The orchestrator allows explicit setting of the rescue base via `dispatcher.set_rescue_base(node_id)`, which validates against the current graph. By default, it falls back to a deterministically stable node (the one with the minimum string ID) to ensure repeatable backend-only tests. In Phase 5+, the frontend can let the user pick this base dynamically.

---

## 12. Confirmation of Scope Restrictions

**Confirmed:** Phase 5 (REST API, Flask endpoints) and Phase 6 (Frontend Map, UI) were explicitly **NOT** implemented. The orchestrator runs entirely in pure Python logic.
