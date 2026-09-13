# Phase 5 Completion Report

## 1. Goal
The goal of Phase 5 was to expose the existing working Phase 4 backend (which integrated the DSA components, ML model predictions, GDACS live data, and OSM infrastructure) through a thin Flask REST API layer. The API's responsibility is solely to bridge the backend with the future frontend.

## 2. Endpoints Implemented

| Method | Endpoint | Action |
|---|---|---|
| GET | `/api/disasters` | Returns a concise list of recent GDACS events suitable for selection, stripping heavy geographic data. |
| POST | `/api/load-disaster` | Orchestrates the `Dispatcher` to load an event, build the road graph, apply ML risk weights, and generate emergencies. |
| GET | `/api/state` | Returns the serializable current map state, including nodes, risk and normal edges, the emergency queue, the rescue base, and the dispatch log. |
| POST | `/api/dispatch` | Dispatches the highest-priority emergency using `dispatcher.dispatch_next()`. |
| POST | `/api/road/block` | Manually blocks a specific road segment on the map. |
| POST | `/api/road/unblock` | Unblocks a previously blocked road segment. |
| POST | `/api/reset` | Purges all current state by re-instantiating the global Dispatcher. |
| GET | `/api/model-info` | Reads and returns the `ml/model_info.json` file. |

## 3. Request/Response Structure
- All POST requests expect `application/json` bodies.
- All responses return strictly formatted `application/json`.
- The graph edges have been serialized into a frontend-friendly deduplicated list of objects (`u`, `v`, `risk_weight`, `normal_weight`, `blocked`).
- `emergencies` handles the structural complexity of extracting `EmergencyRequest` objects safely from the `heapq` tuple structure (`(-score, count, request)`).

## 4. Validation and Security Decisions
- **Validation**: Enforced presence checks for critical fields (e.g., `event_id`, `event_type` for loading, `u`, `v` for blocking).
- **CORS**: Implemented globally on the `/api/*` blueprint namespace using `flask-cors`.
- **Security**: Caught all exceptions at the handler level to prevent Flask from sending HTML stack traces to the frontend.
- **Secrets**: No secrets, API keys, or databases were introduced.

## 5. External-Service Error Handling
If `GDACS` or `OSM Overpass` encounters issues, the backend throws specific errors (`RuntimeError`, `ValueError`). The REST endpoints capture these standard exceptions and re-emit them as clean 4xx or 5xx JSON responses with explicit error messages (e.g., `"Failed to fetch disasters from GDACS"`).

## 6. Tests and Results
- Created `tests/test_phase5_api.py`.
- Mocked all external network dependencies (`GDACSClient`, `OSMClient`) using `unittest.mock`.
- Addressed an initial serialization bug where `blocked_edges` was queried instead of `blocked` within the node attribute dictionary.
- Addressed an initial heapq unpack bug.
- **Result:** The `TestPhase5API` suite passes perfectly. Furthermore, the global test command `python -m pytest tests/` confirms **all 21 tests across Phases 2, 3, 4, and 5 pass completely.**

## 7. Files Changed
- `api/routes.py` (NEW)
- `tests/test_phase5_api.py` (NEW)
- `app.py` (MODIFIED to register blueprint and handlers)
- `requirements.txt` (MODIFIED to add `flask-cors`)

## 8. Limitations
- Single global session: The API holds exactly one `Dispatcher` state. It is not currently designed for concurrent users.
- In-Memory Only: A server restart wipes the disaster layout state, as per architecture requirements.

## 9. Confirmation
**Phase 6 (Frontend) has NOT been implemented.** No HTML, Leaflet.js, CSS, UI buttons, or map renderings were written. The boundary strictly terminates at the JSON API boundary.
