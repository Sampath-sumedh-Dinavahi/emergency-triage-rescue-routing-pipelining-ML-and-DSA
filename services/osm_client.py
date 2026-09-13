import requests
import logging

logger = logging.getLogger(__name__)

class OSMClient:
    OVERPASS_URL = "https://overpass-api.de/api/interpreter"

    def fetch_roads_in_bbox(self, min_lon, min_lat, max_lon, max_lat):
        query = f"""
        [out:json][timeout:25];
        (
          way["highway"]({min_lat},{min_lon},{max_lat},{max_lon});
        );
        out geom;
        """
        headers = {
            'User-Agent': 'DisasterResponseRouting/1.0 (StudentProject)'
        }
        try:
            response = requests.post(self.OVERPASS_URL, data={'data': query}, headers=headers, timeout=30)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error fetching OSM roads: {e}")
            return None
