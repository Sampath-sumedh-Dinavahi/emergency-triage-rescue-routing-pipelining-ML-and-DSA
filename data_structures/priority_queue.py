import heapq
import time
from typing import Optional, Any
from models.request import EmergencyRequest

class EmergencyPriorityQueue:
    """
    Max-priority queue for emergency requests using heapq.
    Urgency scores are negated to simulate a max-heap.
    """
    def __init__(self):
        self._heap = []
        self._counter = 0 # Deterministic tie-breaker
        
    def push(self, request: EmergencyRequest, current_time: float = None):
        """
        Pushes a request into the priority queue based on its calculated urgency score.
        """
        if current_time is None:
            current_time = time.time()
            
        score = request.calculate_urgency(current_time)
        # Push (-score, counter, request)
        # -score ensures highest score is popped first
        # counter ensures FIFO for requests with the exact same score
        heapq.heappush(self._heap, (-score, self._counter, request))
        self._counter += 1
        
    def extract_max(self) -> Optional[EmergencyRequest]:
        """
        Pops and returns the EmergencyRequest with the highest urgency score.
        Returns None if the queue is empty.
        """
        if not self._heap:
            return None
        _, _, request = heapq.heappop(self._heap)
        return request
        
    def peek_max(self) -> Optional[EmergencyRequest]:
        """
        Returns the highest-priority request without removing it.
        """
        if not self._heap:
            return None
        return self._heap[0][2]
        
    def is_empty(self) -> bool:
        """Returns True if the queue is empty."""
        return len(self._heap) == 0
        
    def __len__(self):
        return len(self._heap)
