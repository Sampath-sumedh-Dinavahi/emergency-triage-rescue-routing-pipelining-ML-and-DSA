import os
import json
import logging
from flask import Blueprint, jsonify, request

from services.dispatcher import Dispatcher

logger = logging.getLogger(__name__)
api_bp = Blueprint('api', __name__, url_prefix='/api')

# Global orchestrator instance
_dispatcher = Dispatcher()

def get_dispatcher():
    return _dispatcher

@api_bp.route('/disasters', methods=['GET'])
def get_disasters():
    """Returns a concise list of recent disasters suitable for UI selection."""
    try:
        dispatcher = get_dispatcher()
        # Fetch up to 100 recent events
        events = dispatcher.gdacs_client.get_recent_events(limit=100)
        
        # Strip heavy geometry for the list view
        summary = []
        for e in events:
            props = e.get('properties', {})
            summary.append({
                'event_id': props.get('eventid'),
                'event_type': props.get('eventtype'),
                'severity': props.get('severitydata', {}).get('severity', 1.0) if isinstance(props.get('severitydata'), dict) else 1.0,
                'alert_level': props.get('alertlevel', 'Green'),
                'name': props.get('eventname', 'Unknown Event'),
                'country': props.get('country', 'Unknown'),
                'date': props.get('fromdate')
            })
            
        return jsonify(summary), 200
    except Exception as e:
        logger.error(f"Error fetching disasters: {e}")
        return jsonify({"error": "Failed to fetch disasters from GDACS."}), 502

@api_bp.route('/load-disaster', methods=['POST'])
def load_disaster():
    """Loads a disaster, fetches roads, runs ML, generates emergencies."""
    data = request.get_json()
    if not data or 'event_type' not in data or 'event_id' not in data:
        return jsonify({"error": "Missing required fields: event_type, event_id"}), 400
        
    try:
        dispatcher = get_dispatcher()
        result = dispatcher.load_disaster(
            event_type=data['event_type'],
            event_id=data['event_id'],
            episode_id=data.get('episode_id')
        )
        return jsonify(result), 200
    except ValueError as ve:
        return jsonify({"error": str(ve)}), 404
    except RuntimeError as re:
        return jsonify({"error": str(re)}), 502
    except Exception as e:
        logger.exception("Unexpected error in load_disaster")
        return jsonify({"error": "An unexpected server error occurred."}), 500

@api_bp.route('/state', methods=['GET'])
def get_state():
    """Returns the full serializable system state for frontend rendering."""
    dispatcher = get_dispatcher()
    
    # 1. Base Event Info
    event_info = None
    if dispatcher.current_event:
        props = dispatcher.current_event.get('properties', {})
        event_info = {
            'event_id': props.get('eventid'),
            'event_type': props.get('eventtype'),
            'alert_level': props.get('alertlevel'),
            'center': dispatcher.current_event.get('geometry', {}).get('coordinates', [0, 0])
        }
        
    # 2. Extract graph edges for rendering
    # To keep response size reasonable and deduplicated, we serialize only risk_graph edges
    # (since normal_graph has the exact same edges, just different weights)
    # We will attach both weights so the frontend can visualize the difference.
    edges = []
    visited_edges = set()
    
    for u in dispatcher.risk_graph.get_nodes():
        for neighbor, data in dispatcher.risk_graph.adj[u].items():
            # Create a unique undirected key to prevent sending A->B and B->A if they share properties
            edge_key = tuple(sorted([u, neighbor]))
            if edge_key not in visited_edges:
                visited_edges.add(edge_key)
                
                normal_data = dispatcher.normal_graph.adj[u].get(neighbor, {})
                
                edges.append({
                    'u': u,
                    'v': neighbor,
                    'risk_weight': data.get('weight'),
                    'normal_weight': normal_data.get('weight'),
                    'blocked': data.get('blocked', False)
                })

    # 3. Emergency Queue
    emergencies = []
    # We shouldn't mutate the actual queue, so we iterate its underlying heap
    for item in dispatcher.priority_queue._heap:
        req = item[2]
        emergencies.append({
            'request_id': req.request_id,
            'location_node': req.location_node,
            'severity': req.severity,
            'medical_urgency': req.medical_urgency,
            'affected_people': req.affected_people,
            'urgency_score': req.calculate_urgency()
        })
    # Sort for UI convenience
    emergencies.sort(key=lambda x: x['urgency_score'], reverse=True)

    nodes_data = {
        node_id: dispatcher.node_coords.get(node_id)
        for node_id in dispatcher.risk_graph.get_nodes()
        if node_id in dispatcher.node_coords
    }

    state = {
        'event': event_info,
        'rescue_base': dispatcher.rescue_base_node,
        'nodes': nodes_data,
        'edges': edges,
        'emergencies': emergencies,
        'dispatch_log': dispatcher.dispatch_log
    }
    
    return jsonify(state), 200

@api_bp.route('/dispatch', methods=['POST'])
def dispatch_next():
    """Pops the highest priority emergency and routes it."""
    try:
        result = get_dispatcher().dispatch_next()
        if result.get('status') == 'empty':
            return jsonify(result), 404
        if result.get('status') == 'error':
            return jsonify(result), 400
        return jsonify(result), 200
    except Exception as e:
        logger.exception("Error during dispatch")
        return jsonify({"error": "Failed to calculate dispatch route."}), 500

@api_bp.route('/road/block', methods=['POST'])
def block_road():
    """Manually blocks a road."""
    data = request.get_json()
    if not data or 'u' not in data or 'v' not in data:
        return jsonify({"error": "Missing edge parameters: u, v"}), 400
        
    try:
        get_dispatcher().block_road(data['u'], data['v'], data.get('bidirectional', True))
        return jsonify({"status": "success", "message": f"Blocked road {data['u']}-{data['v']}"}), 200
    except KeyError:
        return jsonify({"error": "Invalid nodes provided."}), 400
    except Exception as e:
        return jsonify({"error": "Internal error blocking road."}), 500

@api_bp.route('/road/unblock', methods=['POST'])
def unblock_road():
    """Manually unblocks a road."""
    data = request.get_json()
    if not data or 'u' not in data or 'v' not in data:
        return jsonify({"error": "Missing edge parameters: u, v"}), 400
        
    try:
        get_dispatcher().unblock_road(data['u'], data['v'], data.get('bidirectional', True))
        return jsonify({"status": "success", "message": f"Unblocked road {data['u']}-{data['v']}"}), 200
    except Exception as e:
        return jsonify({"error": "Internal error unblocking road."}), 500

@api_bp.route('/reset', methods=['POST'])
def reset_state():
    """Resets the application state completely."""
    global _dispatcher
    _dispatcher = Dispatcher()
    return jsonify({"status": "success", "message": "State reset."}), 200

@api_bp.route('/model-info', methods=['GET'])
def get_model_info():
    """Returns the ML model comparison metrics."""
    # Attempt to load model_info.json from the ml/ directory
    info_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'ml', 'model_info.json')
    try:
        with open(info_path, 'r') as f:
            data = json.load(f)
        return jsonify(data), 200
    except FileNotFoundError:
        return jsonify({"error": "Model info not found. Has training been run?"}), 404
    except Exception as e:
        return jsonify({"error": "Failed to read model info."}), 500
