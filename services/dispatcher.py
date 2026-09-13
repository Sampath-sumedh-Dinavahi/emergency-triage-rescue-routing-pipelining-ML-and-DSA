import logging
import math
from typing import Optional, Dict, Any, List
import pandas as pd
from shapely.geometry import LineString, shape

from services.gdacs_client import GDACSClient
from services.osm_client import OSMClient
from services.emergency_generator import generate_emergencies
from data_structures.graph import Graph
from data_structures.priority_queue import EmergencyPriorityQueue
from models.request import EmergencyRequest
from ml.predictor import RoadImpactPredictor
from algorithms.dijkstra import find_shortest_path

logger = logging.getLogger(__name__)

class Dispatcher:
    """
    Central orchestrator for Phase 4.
    Integrates GDACS, OSM, ML predictions, Graph, PQ, and Dijkstra.
    """
    def __init__(self, rescue_base_node: Optional[str] = None):
        self.gdacs_client = GDACSClient()
        self.osm_client = OSMClient()
        self.predictor = RoadImpactPredictor()
        
        self.risk_graph = Graph()
        self.normal_graph = Graph()
        self.priority_queue = EmergencyPriorityQueue()
        self.node_coords: Dict[str, dict] = {}
        
        self.current_event = None
        self.rescue_base_node = rescue_base_node
        self.dispatch_log: List[dict] = []
        
        self.beta = 9.0  # Risk multiplier from architecture spec
        
    def load_disaster(self, event_type: str, event_id: str, episode_id: Optional[str] = None) -> dict:
        """
        Loads a live GDACS event, fetches OSM roads, applies ML risk predictions,
        and generates simulated emergencies.
        """
        # 1. Fetch GDACS event
        try:
            recent_events = self.gdacs_client.get_recent_events(limit=500)
            event_detail = next((e for e in recent_events if str(e.get('properties', {}).get('eventid')) == str(event_id)), None)
            if not event_detail:
                raise ValueError(f"Event {event_id} not found or unavailable in GDACS.")
        except Exception as e:
            logger.error(f"Failed to fetch GDACS event: {e}")
            raise RuntimeError(f"GDACS integration failed: {e}")
            
        self.current_event = event_detail
        
        # Determine affected polygon and center
        try:
            polygon = self.gdacs_client.get_event_geometry(event_type, event_id, episode_id)
        except Exception:
            polygon = None
            
        props = event_detail.get('properties', {})
        geom = event_detail.get('geometry', {})
        
        if geom and geom.get('type') == 'Point':
            center = geom.get('coordinates', [0, 0])
        else:
            center = [0, 0]
        
        # Extract features for ML (from GDACS metadata)
        severity = props.get('severitydata', {}).get('severity', 1.0)
        if isinstance(severity, dict):
            severity = 1.0 # fallback if structure is nested weirdly
            
        alert_level = props.get('alertlevel', 'Green')
        alert_mapping = {'Green': 1, 'Orange': 2, 'Red': 3}
        alert_level_ordinal = alert_mapping.get(alert_level, 1)

        polygon_shape = None
        has_polygon = False
        if polygon and polygon.get('type') in ('Polygon', 'MultiPolygon'):
            try:
                polygon_shape = shape(polygon)
                has_polygon = True
            except Exception:
                pass
                
        # 2. Fetch OSM road network
        try:
            def get_derived_radius_km(ev_type, sev_level):
                medians = {
                    'EQ': {1: 10.0, 2: 30.0, 3: 100.0},
                    'FL': {1: 5.0, 2: 15.0, 3: 50.0},
                    'TC': {1: 20.0, 2: 50.0, 3: 150.0},
                    'WF': {1: 2.0, 2: 10.0, 3: 30.0},
                }
                return medians.get(ev_type, {}).get(sev_level, 10.0)

            # Create a bbox around the center
            radius_km = get_derived_radius_km(event_type, alert_level_ordinal) if not has_polygon else 10.0
            # Rough conversion: 1 deg ~ 111km
            deg_offset = (radius_km / 111.0)
            
            min_lon = center[0] - deg_offset
            min_lat = center[1] - deg_offset
            max_lon = center[0] + deg_offset
            max_lat = center[1] + deg_offset
            
            # Cap bbox span to max 0.1 to avoid timeouts
            max_span = 0.1
            if max_lon - min_lon > max_span:
                mid = (min_lon + max_lon) / 2
                min_lon, max_lon = mid - max_span / 2, mid + max_span / 2
            if max_lat - min_lat > max_span:
                mid = (min_lat + max_lat) / 2
                min_lat, max_lat = mid - max_span / 2, mid + max_span / 2
                
            osm_data = self.osm_client.fetch_roads_in_bbox(min_lon, min_lat, max_lon, max_lat)
            if osm_data and 'elements' in osm_data:
                osm_roads = [e for e in osm_data['elements'] if e['type'] == 'way' and 'geometry' in e]
            else:
                osm_roads = []
                
        except Exception as e:
            logger.error(f"Failed to fetch OSM roads: {e}")
            raise RuntimeError(f"OSM integration failed: {e}")
            
        if not osm_roads:
            raise ValueError("No roads found near the disaster area.")

        # Re-initialize graphs
        self.risk_graph = Graph()
        self.normal_graph = Graph()
        self.node_coords = {}
        
        # 3. Apply ML predictions and build graphs
        ml_features = []
        road_data_list = []
        
        def compute_distance_km(lon1, lat1, lon2, lat2):
            R = 6371
            dlat = math.radians(lat2 - lat1)
            dlon = math.radians(lon2 - lon1)
            a = (math.sin(dlat / 2) ** 2 +
                 math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
                 math.sin(dlon / 2) ** 2)
            c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
            return R * c
        
        for way in osm_roads:
            coords = [(pt['lon'], pt['lat']) for pt in way['geometry']]
            nodes = way['nodes']
            for i in range(len(nodes)):
                self.node_coords[str(nodes[i])] = {'lat': coords[i][1], 'lon': coords[i][0]}
                
            if len(coords) < 2:
                continue
                
            line = LineString(coords)
            road_length_m = sum(
                compute_distance_km(coords[i][0], coords[i][1],
                                    coords[i + 1][0], coords[i + 1][1]) * 1000
                for i in range(len(coords) - 1)
            )
            
            if road_length_m == 0:
                continue
                
            road_center = line.centroid
            dist_to_center_km = compute_distance_km(
                road_center.x, road_center.y, center[0], center[1]
            )
            
            dist_to_boundary_km = -1.0
            if has_polygon:
                try:
                    dist_to_boundary_km = polygon_shape.boundary.distance(road_center) * 111.0
                except Exception:
                    pass
            
            ml_feature = {
                "disaster_type": event_type,
                "alert_level_ordinal": alert_level_ordinal,
                "severity": severity,
                "distance_to_center_km": dist_to_center_km,
                "distance_to_boundary_km": dist_to_boundary_km,
                "road_length_m": road_length_m,
                "road_type": way.get('tags', {}).get('highway', 'unknown')
            }
            ml_features.append(ml_feature)
            
            road_info = {
                'nodes': way['nodes'],
                'length_m': road_length_m,
                'oneway': way.get('tags', {}).get('oneway', 'no')
            }
            road_data_list.append(road_info)

        features_df = pd.DataFrame(ml_features)
        
        try:
            predicted_road_impacts = self.predictor.predict(features_df)
        except Exception as e:
            logger.error(f"ML Prediction failed: {e}")
            raise RuntimeError(f"ML integration failed: {e}")
            
        # Build the graphs
        for road, predicted_impact in zip(road_data_list, predicted_road_impacts):
            nodes = road['nodes']
            length_km = road['length_m'] / 1000.0
            
            # Risk-aware weight: weight = length_km * (1 + beta * predicted_impact)
            risk_weight = length_km * (1.0 + self.beta * predicted_impact)
            normal_weight = length_km
            
            for i in range(len(nodes) - 1):
                u = str(nodes[i])
                v = str(nodes[i+1])
                
                # Assume bidirectional for simplicity unless explicitly one-way
                is_oneway = road.get('oneway', 'no') == 'yes'
                bidirectional = not is_oneway
                
                self.risk_graph.add_edge(u, v, risk_weight, bidirectional)
                self.normal_graph.add_edge(u, v, normal_weight, bidirectional)
                
        # 4. Generate simulated emergencies
        self.priority_queue = EmergencyPriorityQueue()
        emergencies = generate_emergencies(self.risk_graph, num_requests=10)
        
        for req in emergencies:
            self.priority_queue.push(req)
            
        # 5. Set default rescue base if not provided
        if not self.rescue_base_node and self.risk_graph.get_nodes():
            # For determinism, pick the node with the minimum string ID
            self.rescue_base_node = min(self.risk_graph.get_nodes())
            
        return {
            "status": "success",
            "message": "Disaster loaded, graph built, and emergencies generated.",
            "road_count": len(osm_roads),
            "node_count": len(self.risk_graph.get_nodes()),
            "emergency_count": len(emergencies),
            "rescue_base": self.rescue_base_node
        }

    def set_rescue_base(self, node_id: str):
        """
        Explicitly sets the rescue base node.
        Validates that the node exists in the current graph.
        """
        if node_id not in self.risk_graph.get_nodes():
            raise ValueError(f"Node {node_id} does not exist in the current road network.")
        self.rescue_base_node = node_id

    def dispatch_next(self) -> dict:
        """
        Dispatches the highest priority emergency and calculates paths.
        """
        if self.priority_queue.is_empty():
            return {"status": "empty", "message": "No pending emergencies."}
            
        if not self.rescue_base_node:
            return {"status": "error", "message": "Rescue base not set."}
            
        request = self.priority_queue.extract_max()
        urgency = request.calculate_urgency()
        target_node = request.location_node
        
        # Calculate Risk-Aware Route
        risk_dist, risk_path = find_shortest_path(self.risk_graph, self.rescue_base_node, target_node)
        
        if risk_path is None:
            # Unreachable
            result = {
                "status": "unreachable",
                "request_id": request.request_id,
                "target_node": target_node,
                "urgency_score": urgency,
                "message": "Target is unreachable from rescue base."
            }
            self.dispatch_log.append(result)
            return result
            
        # Calculate Normal Route for comparison
        normal_dist, normal_path = find_shortest_path(self.normal_graph, self.rescue_base_node, target_node)
        
        risk_coords = [[self.node_coords[n]['lon'], self.node_coords[n]['lat']] for n in risk_path if n in self.node_coords] if risk_path else []
        normal_coords = [[self.node_coords[n]['lon'], self.node_coords[n]['lat']] for n in normal_path if n in self.node_coords] if normal_path else []

        result = {
            "status": "dispatched",
            "request_id": request.request_id,
            "target_node": target_node,
            "urgency_score": urgency,
            "risk_aware_route": {
                "path": risk_path,
                "coordinates": risk_coords,
                "total_cost": risk_dist
            },
            "normal_route": {
                "path": normal_path,
                "coordinates": normal_coords,
                "total_distance_km": normal_dist
            },
            "routes_differ": risk_path != normal_path
        }
        
        self.dispatch_log.append(result)
        return result
        
    def block_road(self, u: str, v: str, bidirectional: bool = True):
        """Manually block a road in both graphs."""
        self.risk_graph.block_road(u, v, bidirectional)
        self.normal_graph.block_road(u, v, bidirectional)
        
    def unblock_road(self, u: str, v: str, bidirectional: bool = True):
        """Manually unblock a road in both graphs."""
        self.risk_graph.unblock_road(u, v, bidirectional)
        self.normal_graph.unblock_road(u, v, bidirectional)
