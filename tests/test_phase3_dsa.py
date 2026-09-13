import unittest
import time
from unittest.mock import patch

from models.request import EmergencyRequest
from data_structures.priority_queue import EmergencyPriorityQueue
from data_structures.graph import Graph
from algorithms.dijkstra import find_shortest_path

class TestPriorityQueue(unittest.TestCase):
    
    @patch('time.time', return_value=1000.0)
    def test_priority_queue_ordering(self, mock_time):
        """Test that the priority queue returns requests in correct urgency order."""
        pq = EmergencyPriorityQueue()
        
        # We will create 7 requests with explicit features to calculate known scores
        # Score formula: 5*severity + 4*medical_urgency + 2*log(affected_people + 1) + min(wait*0.5, 10.0)
        
        # Req 1: Low urgency
        req1 = EmergencyRequest("node_A", severity=2.0, medical_urgency=2.0, affected_people=0)
        req1.created_at = 1000.0 # wait = 0
        
        # Req 2: High severity
        req2 = EmergencyRequest("node_B", severity=8.0, medical_urgency=2.0, affected_people=0)
        req2.created_at = 1000.0 # wait = 0
        
        # Req 3: High medical urgency
        req3 = EmergencyRequest("node_C", severity=2.0, medical_urgency=8.0, affected_people=0)
        req3.created_at = 1000.0 # wait = 0
        
        # Req 4: Exact same score as Req 1 but earlier creation (wait bonus)
        req4 = EmergencyRequest("node_D", severity=2.0, medical_urgency=2.0, affected_people=0)
        req4.created_at = 980.0 # 20 mins wait -> +10 bonus
        
        # Req 5: Moderate all
        req5 = EmergencyRequest("node_E", severity=5.0, medical_urgency=5.0, affected_people=100)
        req5.created_at = 1000.0 # wait = 0
        
        # Req 6: Tie breaker 1 (same absolute score and wait as Req 7)
        req6 = EmergencyRequest("node_F", severity=10.0, medical_urgency=10.0, affected_people=1000)
        req6.created_at = 1000.0
        
        # Req 7: Tie breaker 2
        req7 = EmergencyRequest("node_G", severity=10.0, medical_urgency=10.0, affected_people=1000)
        req7.created_at = 1000.0
        
        # Calculate expected scores for verification (independent of PQ behavior)
        scores = {
            req1: req1.calculate_urgency(1000.0),
            req2: req2.calculate_urgency(1000.0),
            req3: req3.calculate_urgency(1000.0),
            req4: req4.calculate_urgency(1000.0),
            req5: req5.calculate_urgency(1000.0),
            req6: req6.calculate_urgency(1000.0),
            req7: req7.calculate_urgency(1000.0),
        }
        
        # Push in random order
        pq.push(req3, 1000.0)
        pq.push(req1, 1000.0)
        pq.push(req6, 1000.0)
        pq.push(req5, 1000.0)
        pq.push(req2, 1000.0)
        pq.push(req7, 1000.0) # Pushed after req6
        pq.push(req4, 1000.0)
        
        # Extract all and check ordering
        extracted = []
        while not pq.is_empty():
            extracted.append(pq.extract_max())
            
        # Verify scores are strictly descending
        for i in range(len(extracted) - 1):
            self.assertTrue(
                scores[extracted[i]] >= scores[extracted[i+1]], 
                "Priority queue failed to order by urgency score descending"
            )
            
        # Verify deterministic tie-breaking (FIFO for same score)
        # req6 and req7 have same score. req6 was pushed first, so it should be extracted first.
        idx6 = extracted.index(req6)
        idx7 = extracted.index(req7)
        self.assertTrue(idx6 < idx7, "Deterministic tie-breaking failed")

class TestGraph(unittest.TestCase):
    
    def setUp(self):
        self.graph = Graph()
        self.graph.add_edge("A", "B", 5.0)
        self.graph.add_edge("A", "C", 10.0)
        self.graph.add_edge("B", "C", 2.0)
        
    def test_add_edge(self):
        """Test Graph adds edges correctly."""
        neighbors_A = self.graph.get_neighbors("A")
        # Should contain ('B', 5.0) and ('C', 10.0)
        self.assertEqual(len(neighbors_A), 2)
        self.assertIn(("B", 5.0), neighbors_A)
        self.assertIn(("C", 10.0), neighbors_A)
        
    def test_block_road(self):
        """Test blocking removes an edge from active neighbors."""
        self.graph.block_road("A", "B")
        neighbors_A = self.graph.get_neighbors("A")
        self.assertEqual(len(neighbors_A), 1)
        self.assertIn(("C", 10.0), neighbors_A)
        
        # B's neighbors should no longer include A (since it's bidirectional)
        neighbors_B = self.graph.get_neighbors("B")
        self.assertEqual(len(neighbors_B), 1)
        self.assertIn(("C", 2.0), neighbors_B)
        
    def test_unblock_road(self):
        """Test unblocking restores original weight."""
        self.graph.block_road("A", "B")
        self.graph.unblock_road("A", "B")
        
        neighbors_A = self.graph.get_neighbors("A")
        self.assertEqual(len(neighbors_A), 2)
        self.assertIn(("B", 5.0), neighbors_A)

class TestDijkstra(unittest.TestCase):
    
    def setUp(self):
        self.graph = Graph()
        self.graph.add_edge("A", "B", 2.0)
        self.graph.add_edge("A", "C", 5.0)
        self.graph.add_edge("B", "C", 1.0)
        self.graph.add_edge("B", "D", 6.0)
        self.graph.add_edge("C", "D", 2.0)
        
    def test_shortest_path(self):
        """Test Dijkstra finds the expected shortest path."""
        # A -> B -> C -> D = 2 + 1 + 2 = 5
        distance, path = find_shortest_path(self.graph, "A", "D")
        self.assertEqual(distance, 5.0)
        self.assertEqual(path, ["A", "B", "C", "D"])
        
    def test_blocked_road_forces_alternate_route(self):
        """Test blocking the original shortest route causes an alternate route to be selected."""
        # Block B-C edge
        self.graph.block_road("B", "C")
        
        # New shortest path: A -> C -> D = 5 + 2 = 7
        distance, path = find_shortest_path(self.graph, "A", "D")
        self.assertEqual(distance, 7.0)
        self.assertEqual(path, ["A", "C", "D"])
        
    def test_unreachable_destination(self):
        """Test if all routes are blocked, destination is reported unreachable."""
        self.graph.block_road("C", "D")
        self.graph.block_road("B", "D")
        
        distance, path = find_shortest_path(self.graph, "A", "D")
        self.assertIsNone(distance)
        self.assertIsNone(path)

if __name__ == '__main__':
    unittest.main()
