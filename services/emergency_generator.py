import random
from typing import List
from models.request import EmergencyRequest
from data_structures.graph import Graph

def generate_emergencies(graph: Graph, num_requests: int = 5) -> List[EmergencyRequest]:
    """
    Generates a small set of plausible simulated emergency requests 
    at random active nodes within the current road graph.
    
    Args:
        graph: The active road network graph.
        num_requests: Number of simulated emergencies to generate.
        
    Returns:
        A list of EmergencyRequest objects.
    """
    nodes = graph.get_nodes()
    if not nodes:
        return []
        
    # Use a fixed seed for reproducibility during simulation/testing
    random.seed(42)
    
    selected_nodes = random.sample(nodes, min(num_requests, len(nodes)))
    requests = []
    
    for i, node in enumerate(selected_nodes):
        # Generate varied but plausible severity and urgency scores
        severity = round(random.uniform(2.0, 10.0), 1)
        medical_urgency = round(random.uniform(1.0, 10.0), 1)
        
        # Exponential-like distribution for affected people (few large, many small)
        affected_people = int(random.expovariate(1.0 / 20.0))
        
        req = EmergencyRequest(
            location_node=node,
            severity=severity,
            medical_urgency=medical_urgency,
            affected_people=affected_people
        )
        
        # Stagger the creation times to simulate requests coming in over time
        # This gives a waiting bonus to earlier requests
        req.created_at -= random.uniform(0, 3600) # up to 1 hour ago
        
        requests.append(req)
        
    return requests
