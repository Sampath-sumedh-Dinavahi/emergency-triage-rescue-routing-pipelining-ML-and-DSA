import math
import uuid
import time

class EmergencyRequest:
    """Represents an emergency incident requiring dispatch."""

    def __init__(self, location_node: str, severity: float, medical_urgency: float, affected_people: int):
        """
        Args:
            location_node: The target node ID in the graph.
            severity: 1.0 to 10.0 scale of disaster impact at location.
            medical_urgency: 1.0 to 10.0 scale of medical criticalness.
            affected_people: Number of people affected.
        """
        self.request_id = str(uuid.uuid4())
        self.location_node = location_node
        self.severity = severity
        self.medical_urgency = medical_urgency
        self.affected_people = affected_people
        self.created_at = time.time()
    
    def calculate_urgency(self, current_time: float = None) -> float:
        """
        Calculates the urgency score of the request.
        score = 5*severity + 4*medical_urgency + 2*log(affected_people + 1) + waiting_bonus
        waiting_bonus = min(waiting_minutes * 0.5, 10.0)
        """
        if current_time is None:
            current_time = time.time()
            
        waiting_minutes = (current_time - self.created_at) / 60.0
        waiting_bonus = min(waiting_minutes * 0.5, 10.0)
        
        score = (5.0 * self.severity) + \
                (4.0 * self.medical_urgency) + \
                (2.0 * math.log(max(self.affected_people, 0) + 1)) + \
                waiting_bonus
                
        return score
    
    def __repr__(self):
        return f"<EmergencyRequest {self.request_id[:8]} at {self.location_node}>"
