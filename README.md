# Priority-Based Emergency Triage & Disaster Rescue Routing System

This project is a high-performance Emergency Disaster Intelligence & Rescue Routing Command Center designed for operational contexts. It dynamically triages incoming emergencies based on severity and routes rescue teams through real-world road networks affected by simulated disasters.

## What It Does
1. **Disaster Data Intake**: Fetches live disaster events (floods, earthquakes, etc.) from the Global Disaster Alert and Coordination System (GDACS).
2. **Road Network Extraction**: Queries the OpenStreetMap (Overpass) API for the precise road network geometry within the disaster's bounding box.
3. **ML Risk Prediction**: Applies a trained Gradient Boosting Regression model to predict the functional exposure/impact (proxy for road damage) on every road segment based on its proximity to the disaster epicenter.
4. **Emergency Triage**: Maintains a priority queue (Binary Heap) of incoming emergency requests, triaged by severity, medical needs, and affected personnel.
5. **Risk-Aware Routing**: Uses a modified Dijkstra's algorithm to calculate the optimal rescue route that balances distance and predicted road risk.

## Architecture & Technologies

### Backend (Python/Flask)
- **DSA**: Custom implementations of a Binary Heap (for the priority queue) and Graph Adjacency Lists (for the road network). Dijkstra's algorithm is used for pathfinding.
- **Machine Learning**: `scikit-learn` Gradient Boosting model trained on spatial data to predict road exposure.
- **External APIs**: GDACS (RSS/JSON) and OpenStreetMap (Overpass API).

### Frontend (React/Vite)
- **Map Rendering**: `maplibre-gl` and `react-map-gl` for high-performance WebGL mapping. Uses OpenStreetMap raster tiles for offline/firewall-friendly basemaps.
- **Styling**: TailwindCSS (v4) with a custom CSS variable design system (`index.css`) for a premium, dark-mode operational aesthetic.
- **Build**: Vite with TypeScript.

## Setup & Installation

### Prerequisites
- Python 3.10+
- Node.js 18+

### 1. Backend Setup
Clone the repository and set up a virtual environment:

```bash
python -m venv venv
# Windows:
venv\Scripts\activate
# Mac/Linux:
source venv/bin/activate

pip install -r requirements.txt
```

### 2. Frontend Setup
Navigate to the frontend directory and install dependencies:

```bash
cd frontend
npm install
npm run build
cd ..
```
*Note: The frontend is built into `static/dist` and served directly by Flask. You do not need to run a separate Node server in production.*

### 3. Running the Application
Start the Flask server from the project root:

```bash
python -m flask run
```
Open `http://localhost:5000` in your browser.

## API Endpoints

- `GET /api/disasters`: Fetch recent GDACS events.
- `POST /api/load-disaster`: Initiates the uplink (fetches OSM roads, runs ML model, spawns emergencies).
- `GET /api/state`: Returns the current graph, emergencies, and rescue base.
- `POST /api/dispatch`: Dispatches the highest-priority emergency and returns the risk-aware and normal routes.
- `POST /api/road/block`: Manually block a road segment.
- `POST /api/road/unblock`: Unblock a road segment.
- `POST /api/reset`: Reset the application state.
- `GET /api/model-info`: Returns ML model metrics and training metadata.

## Limitations
- **Weakly Supervised Spatial Target**: The ML model predicts "exposure" based on spatial proximity to the epicenter, which is a proxy for risk, not confirmed physical road damage.
- **Simulated Emergencies**: The emergency queue is populated with simulated events for demonstration purposes.
- **OSM/Overpass Availability**: The application relies on the public Overpass API for road data. Large bounding boxes or high API load may result in rate limiting or timeouts.
- **Prototype Nature**: This is a prototype system intended for demonstration of the DSA/ML pipeline and UI/UX concepts. It is not currently integrated with live dispatch hardware.
