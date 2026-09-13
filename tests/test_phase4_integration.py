import unittest
from unittest.mock import patch, MagicMock
import pandas as pd

from services.dispatcher import Dispatcher
from models.request import EmergencyRequest

class TestPhase4Integration(unittest.TestCase):
    
    @patch('services.gdacs_client.GDACSClient.get_recent_events')
    @patch('services.gdacs_client.GDACSClient.get_event_geometry')
    @patch('services.osm_client.OSMClient.fetch_roads_in_bbox')
    def test_pipeline_load_and_dispatch(self, mock_fetch_roads, mock_get_geometry, mock_get_events):
        """
        Test that a mock GDACS event can be loaded into the pipeline,
        graph is built, ML predictions attached, emergencies queued,
        and dispatch returns a risk-aware route.
        """
        # 1. Mock GDACS response
        mock_get_events.return_value = [{
            'properties': {
                'eventid': '12345',
                'eventtype': 'FL',
                'severitydata': {'severity': 2.0},
                'alertlevel': 'Orange'
            },
            'geometry': {
                'type': 'Point',
                'coordinates': [0.5, 0.5]
            }
        }]
        
        mock_get_geometry.return_value = {
            'type': 'Polygon', 
            'coordinates': [[[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]]
        }
        
        # 2. Mock OSM roads
        # We create a simple graph: A-B (safe), B-C (safe), A-C (dangerous)
        mock_fetch_roads.return_value = {
            'elements': [
                {
                    'type': 'way',
                    'id': 1,
                    'nodes': ['A', 'B'],
                    'geometry': [{'lat': 0.5, 'lon': 0.5}, {'lat': 0.51, 'lon': 0.5}],
                    'tags': {'highway': 'primary'}
                },
                {
                    'type': 'way',
                    'id': 2,
                    'nodes': ['B', 'C'],
                    'geometry': [{'lat': 0.51, 'lon': 0.5}, {'lat': 0.51, 'lon': 0.51}],
                    'tags': {'highway': 'primary'}
                },
                {
                    'type': 'way',
                    'id': 3,
                    'nodes': ['A', 'C'],
                    'geometry': [{'lat': 0.5, 'lon': 0.5}, {'lat': 0.51, 'lon': 0.51}],
                    'tags': {'highway': 'primary'}
                }
            ]
        }
        
        # Initialize Dispatcher
        dispatcher = Dispatcher()
        
        # We need to mock the predictor to avoid dependency on the saved model during this specific unit test, 
        # but we also want to test that edge weights differ. 
        # Actually, let's mock predictor.predict to return fixed values to guarantee the test logic.
        with patch('ml.predictor.RoadImpactPredictor.predict') as mock_predict:
            # Predict low risk for A-B and B-C, high risk for A-C
            mock_predict.return_value = [0.0, 0.0, 1.0]
            
            result = dispatcher.load_disaster('FL', '12345')
            
            # Assert loading success
            self.assertEqual(result['status'], 'success')
            self.assertEqual(result['road_count'], 3)
            self.assertEqual(result['node_count'], 3) # A, B, C
            self.assertEqual(result['emergency_count'], 3)
            
            # Set rescue base manually for deterministic testing
            dispatcher.rescue_base_node = 'A'
            
            # Clear priority queue and add a specific request at 'C'
            dispatcher.priority_queue._heap = []
            req = EmergencyRequest("C", severity=10.0, medical_urgency=10.0, affected_people=10)
            dispatcher.priority_queue.push(req)
            
            # Dispatch
            dispatch_result = dispatcher.dispatch_next()
            
            self.assertEqual(dispatch_result['status'], 'dispatched')
            self.assertEqual(dispatch_result['target_node'], 'C')
            
            # Normal route should be A -> C
            self.assertEqual(dispatch_result['normal_route']['path'], ['A', 'C'])
            
            # Risk-aware route should avoid A-C because it has risk=1.0 and beta=9.0
            # So risk-aware should be A -> B -> C
            self.assertEqual(dispatch_result['risk_aware_route']['path'], ['A', 'B', 'C'])
            
            self.assertTrue(dispatch_result['routes_differ'])
            
            # Test road blocking
            dispatcher.block_road('B', 'C')
            
            # Add request at C again
            req2 = EmergencyRequest("C", severity=5.0, medical_urgency=5.0, affected_people=1)
            dispatcher.priority_queue.push(req2)
            
            # Dispatch again
            dispatch_result_2 = dispatcher.dispatch_next()
            
            # Now B-C is blocked. The only way is A-C
            self.assertEqual(dispatch_result_2['status'], 'dispatched')
            self.assertEqual(dispatch_result_2['risk_aware_route']['path'], ['A', 'C'])
            
            # Test unreachable
            dispatcher.block_road('A', 'C')
            
            req3 = EmergencyRequest("C", severity=5.0, medical_urgency=5.0, affected_people=1)
            dispatcher.priority_queue.push(req3)
            
            dispatch_result_3 = dispatcher.dispatch_next()
            self.assertEqual(dispatch_result_3['status'], 'unreachable')

    @patch('services.gdacs_client.GDACSClient.get_recent_events')
    @patch('services.gdacs_client.GDACSClient.get_event_geometry')
    @patch('services.osm_client.OSMClient.fetch_roads_in_bbox')
    def test_rescue_base_selection(self, mock_fetch_roads, mock_get_geometry, mock_get_events):
        """
        Test explicit rescue base selection, validation, and deterministic default.
        """
        mock_get_events.return_value = [{'properties': {'eventid': '123'}, 'geometry': {'type': 'Point', 'coordinates': [0, 0]}}]
        mock_get_geometry.return_value = None
        mock_fetch_roads.return_value = {
            'elements': [
                {'type': 'way', 'nodes': ['B', 'C'], 'geometry': [{'lat': 0, 'lon': 0}, {'lat': 1, 'lon': 1}], 'tags': {}},
                {'type': 'way', 'nodes': ['A', 'B'], 'geometry': [{'lat': 0, 'lon': 0}, {'lat': 1, 'lon': 1}], 'tags': {}}
            ]
        }
        
        dispatcher = Dispatcher()
        with patch('ml.predictor.RoadImpactPredictor.predict', return_value=[0.0, 0.0]):
            dispatcher.load_disaster('FL', '123')
            
        # Deterministic default should be the minimum string ID: 'A'
        self.assertEqual(dispatcher.rescue_base_node, 'A')
        
        # Test valid explicit set
        dispatcher.set_rescue_base('C')
        self.assertEqual(dispatcher.rescue_base_node, 'C')
        
        # Test invalid set
        with self.assertRaises(ValueError):
            dispatcher.set_rescue_base('Z')

if __name__ == '__main__':
    unittest.main()
