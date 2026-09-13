import requests
import logging

logger = logging.getLogger(__name__)

class GDACSClient:
    BASE_URL = "https://www.gdacs.org/gdacsapi/api"

    def get_recent_events(self, limit=100):
        url = f"{self.BASE_URL}/events/geteventlist/SEARCH?eventlist=EQ,FL,TC,WF"
        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            data = response.json()
            features = data.get("features", [])
            return features[:limit]
        except Exception as e:
            logger.error(f"Error fetching GDACS events: {e}")
            return []

    def get_event_geometry(self, event_type, event_id, episode_id):
        if not episode_id:
            episode_id = "1"
        url = f"{self.BASE_URL}/polygons/getgeometry?eventtype={event_type}&eventid={event_id}&episodeid={episode_id}"
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error fetching GDACS geometry for {event_type}-{event_id}: {e}")
            return None

    def get_event_details(self, event_type, event_id):
        url = f"{self.BASE_URL}/events/geteventdata?eventtype={event_type}&eventid={event_id}"
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error fetching GDACS details for {event_type}-{event_id}: {e}")
            return None
