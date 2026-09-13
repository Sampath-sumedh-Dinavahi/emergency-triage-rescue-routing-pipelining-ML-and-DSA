import unittest
from unittest.mock import patch, MagicMock
from app import app
from api.routes import get_dispatcher
from services.dispatcher import Dispatcher
import json

class TestPhase5API(unittest.TestCase):
    
    def setUp(self):
        self.client = app.test_client()
        self.client.testing = True
        
        # Reset the global dispatcher before each test
        # We can just hit the reset endpoint
        self.client.post('/api/reset')

    @patch('services.gdacs_client.GDACSClient.get_recent_events')
    def test_get_disasters(self, mock_get_events):
        mock_get_events.return_value = [
            {'properties': {'eventid': '101', 'eventtype': 'FL', 'eventname': 'Flood A', 'severitydata': {'severity': 2.0}, 'alertlevel': 'Orange'}}
        ]
        
        response = self.client.get('/api/disasters')
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]['event_id'], '101')
        self.assertEqual(data[0]['name'], 'Flood A')

    @patch('services.gdacs_client.GDACSClient.get_recent_events')
    @patch('services.gdacs_client.GDACSClient.get_event_geometry')
    @patch('services.osm_client.OSMClient.fetch_roads_in_bbox')
    def test_load_disaster(self, mock_fetch_roads, mock_get_geometry, mock_get_events):
        mock_get_events.return_value = [{'properties': {'eventid': '123', 'eventtype': 'FL'}, 'geometry': {'type': 'Point', 'coordinates': [0, 0]}}]
        mock_get_geometry.return_value = None
        mock_fetch_roads.return_value = {
            'elements': [
                {'type': 'way', 'nodes': ['A', 'B'], 'geometry': [{'lat': 0, 'lon': 0}, {'lat': 1, 'lon': 1}], 'tags': {}}
            ]
        }
        
        with patch('ml.predictor.RoadImpactPredictor.predict', return_value=[0.5]):
            response = self.client.post('/api/load-disaster', json={'event_type': 'FL', 'event_id': '123'})
            
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data['status'], 'success')
        self.assertIn('node_count', data)

    def test_load_disaster_missing_fields(self):
        response = self.client.post('/api/load-disaster', json={'event_id': '123'})
        self.assertEqual(response.status_code, 400)

    @patch('services.gdacs_client.GDACSClient.get_recent_events')
    @patch('services.gdacs_client.GDACSClient.get_event_geometry')
    @patch('services.osm_client.OSMClient.fetch_roads_in_bbox')
    def test_get_state(self, mock_fetch_roads, mock_get_geometry, mock_get_events):
        # Load a disaster first
        mock_get_events.return_value = [{'properties': {'eventid': '123', 'eventtype': 'FL'}, 'geometry': {'type': 'Point', 'coordinates': [0, 0]}}]
        mock_get_geometry.return_value = None
        mock_fetch_roads.return_value = {
            'elements': [
                {'type': 'way', 'nodes': ['A', 'B'], 'geometry': [{'lat': 0, 'lon': 0}, {'lat': 1, 'lon': 1}], 'tags': {}}
            ]
        }
        
        with patch('ml.predictor.RoadImpactPredictor.predict', return_value=[0.5]):
            self.client.post('/api/load-disaster', json={'event_type': 'FL', 'event_id': '123'})
            
        response = self.client.get('/api/state')
        self.assertEqual(response.status_code, 200)
        state = response.get_json()
        
        self.assertEqual(state['event']['event_id'], '123')
        self.assertIn('A', state['nodes'])
        self.assertTrue(len(state['edges']) > 0)
        self.assertIn('emergencies', state)
        
    @patch('services.gdacs_client.GDACSClient.get_recent_events')
    @patch('services.gdacs_client.GDACSClient.get_event_geometry')
    @patch('services.osm_client.OSMClient.fetch_roads_in_bbox')
    def test_dispatch(self, mock_fetch_roads, mock_get_geometry, mock_get_events):
        mock_get_events.return_value = [{'properties': {'eventid': '123', 'eventtype': 'FL'}, 'geometry': {'type': 'Point', 'coordinates': [0, 0]}}]
        mock_get_geometry.return_value = None
        mock_fetch_roads.return_value = {
            'elements': [
                {'type': 'way', 'nodes': ['A', 'B'], 'geometry': [{'lat': 0, 'lon': 0}, {'lat': 1, 'lon': 1}], 'tags': {}}
            ]
        }
        
        with patch('ml.predictor.RoadImpactPredictor.predict', return_value=[0.5]):
            self.client.post('/api/load-disaster', json={'event_type': 'FL', 'event_id': '123'})
            
        response = self.client.post('/api/dispatch')
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertIn(data['status'], ['dispatched', 'unreachable', 'empty'])

    def test_road_block(self):
        # Even without disaster loaded, we can hit the endpoint to see if it responds to missing keys
        response = self.client.post('/api/road/block', json={})
        self.assertEqual(response.status_code, 400)

    @patch('services.gdacs_client.GDACSClient.get_recent_events')
    @patch('services.gdacs_client.GDACSClient.get_event_geometry')
    @patch('services.osm_client.OSMClient.fetch_roads_in_bbox')
    def test_road_block_success(self, mock_fetch_roads, mock_get_geometry, mock_get_events):
        mock_get_events.return_value = [{'properties': {'eventid': '123', 'eventtype': 'FL'}, 'geometry': {'type': 'Point', 'coordinates': [0, 0]}}]
        mock_get_geometry.return_value = None
        mock_fetch_roads.return_value = {
            'elements': [
                {'type': 'way', 'nodes': ['A', 'B'], 'geometry': [{'lat': 0, 'lon': 0}, {'lat': 1, 'lon': 1}], 'tags': {}}
            ]
        }
        with patch('ml.predictor.RoadImpactPredictor.predict', return_value=[0.5]):
            self.client.post('/api/load-disaster', json={'event_type': 'FL', 'event_id': '123'})
            
        response = self.client.post('/api/road/block', json={'u': 'A', 'v': 'B'})
        self.assertEqual(response.status_code, 200)
        
        # Verify blocked in state
        state_resp = self.client.get('/api/state')
        edges = state_resp.get_json()['edges']
        edge = next(e for e in edges if (e['u'] == 'A' and e['v'] == 'B') or (e['u'] == 'B' and e['v'] == 'A'))
        self.assertTrue(edge['blocked'])
        
        # Unblock
        response2 = self.client.post('/api/road/unblock', json={'u': 'A', 'v': 'B'})
        self.assertEqual(response2.status_code, 200)
        
        state_resp2 = self.client.get('/api/state')
        edges2 = state_resp2.get_json()['edges']
        edge2 = next(e for e in edges2 if (e['u'] == 'A' and e['v'] == 'B') or (e['u'] == 'B' and e['v'] == 'A'))
        self.assertFalse(edge2['blocked'])

    def test_model_info(self):
        # Create a dummy model_info.json if it doesn't exist just to test the endpoint logic
        # Usually it exists from Phase 2
        response = self.client.get('/api/model-info')
        # Could be 200 or 404 depending on if ML training was run, 
        # but we just want to ensure it handles it cleanly without a 500
        self.assertIn(response.status_code, [200, 404])

if __name__ == '__main__':
    unittest.main()
