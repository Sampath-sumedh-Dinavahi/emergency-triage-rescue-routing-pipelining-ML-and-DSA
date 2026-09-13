"""Build the Phase 1 training dataset from historical GDACS events + OSM roads.

Phase 2.1 revision: samples roads from TWO spatial zones per event to produce
meaningful target variation:
  - Inner zone: roads inside/near the GDACS affected polygon → target ≈ 1
  - Outer zone: roads outside the affected polygon → target ≈ 0
This prevents the dataset from being overwhelmed with 1.0 labels.

exposed_population has been removed because it was random noise, not real data.
"""

import os
import csv
import math
import random
import time
import sys

# Add parent directory to path so we can import services
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shapely.geometry import shape, LineString, Point
from services.gdacs_client import GDACSClient
from services.osm_client import OSMClient

# GDACS alert level ordinal mapping
ALERT_LEVEL_MAP = {"Green": 1, "Orange": 2, "Red": 3}

CSV_COLUMNS = [
    'event_id', 'disaster_type', 'alert_level_ordinal', 'severity',
    'distance_to_center_km', 'distance_to_boundary_km',
    'road_length_m', 'road_type', 'road_impact_score'
]


def get_derived_radius_km(event_type, severity_level):
    """Dynamically derived median radius proxy from historical data."""
    medians = {
        'EQ': {1: 10.0, 2: 30.0, 3: 100.0},
        'FL': {1: 5.0, 2: 15.0, 3: 50.0},
        'TC': {1: 20.0, 2: 50.0, 3: 150.0},
        'WF': {1: 2.0, 2: 10.0, 3: 30.0},
    }
    return medians.get(event_type, {}).get(severity_level, 10.0)


def compute_distance_km(lon1, lat1, lon2, lat2):
    """Haversine distance in km."""
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
         math.sin(dlon / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


def cap_bbox(min_lon, min_lat, max_lon, max_lat, max_span=0.1):
    """Cap bbox to max_span degrees to avoid Overpass 504 timeouts."""
    if max_lon - min_lon > max_span:
        mid = (min_lon + max_lon) / 2
        min_lon, max_lon = mid - max_span / 2, mid + max_span / 2
    if max_lat - min_lat > max_span:
        mid = (min_lat + max_lat) / 2
        min_lat, max_lat = mid - max_span / 2, mid + max_span / 2
    return (min_lon, min_lat, max_lon, max_lat)


def get_outer_bbox(center_lon, center_lat, polygon_extent_deg, direction_idx):
    """Generate a 0.1° × 0.1° bbox placed OUTSIDE the affected area.

    The offset is set so the outer bbox does not overlap the polygon:
      offset = max(polygon_half_extent, 0.05) + 0.1
    This places the outer bbox center at least 0.1° beyond the polygon edge.
    A rotating cardinal direction (E/W/N/S) is used per event for diversity.
    """
    offset = max(polygon_extent_deg / 2, 0.05) + 0.1
    half = 0.05  # outer bbox is 0.1° × 0.1°

    directions = [(1, 0), (-1, 0), (0, 1), (0, -1)]
    dx, dy = directions[direction_idx % len(directions)]

    cx = center_lon + dx * offset
    cy = center_lat + dy * offset
    return (cx - half, cy - half, cx + half, cy + half)


def fetch_roads(osm, bbox):
    """Fetch road ways from Overpass for the given bbox. Returns list of ways."""
    data = osm.fetch_roads_in_bbox(*bbox)
    if not data or 'elements' not in data:
        return []
    return [e for e in data['elements'] if e['type'] == 'way' and 'geometry' in e]


def compute_road_row(way, event_id, event_type, alert_level_ordinal, severity,
                     center_lon, center_lat, affected_polygon, has_polygon, radius_km):
    """Compute one CSV row for a road segment. Returns list or None."""
    coords = [(pt['lon'], pt['lat']) for pt in way['geometry']]
    if len(coords) < 2:
        return None

    line = LineString(coords)
    road_length_m = sum(
        compute_distance_km(coords[i][0], coords[i][1],
                            coords[i + 1][0], coords[i + 1][1]) * 1000
        for i in range(len(coords) - 1)
    )
    if road_length_m == 0:
        return None

    road_type = way.get('tags', {}).get('highway', 'unknown')
    road_center = line.centroid
    dist_to_center_km = compute_distance_km(
        road_center.x, road_center.y, center_lon, center_lat
    )

    if has_polygon:
        try:
            dist_to_boundary_km = affected_polygon.boundary.distance(road_center) * 111.0

            intersection = line.intersection(affected_polygon)
            frac = intersection.length / line.length if line.length > 0 else 0
            target = min(max(frac, 0.0), 1.0)
        except Exception:
            return None
    else:
        dist_to_boundary_km = -1.0
        s = (alert_level_ordinal - 1) / 2.0
        d = math.exp(-dist_to_center_km / radius_km)
        target = min(max(s * d, 0.0), 1.0)

    return [
        event_id, event_type, alert_level_ordinal, severity,
        dist_to_center_km, dist_to_boundary_km,
        road_length_m, road_type, target
    ]


def process_event(event, gdacs, osm, writer, event_index):
    """Process one GDACS event: fetch inner + outer zone roads, write CSV rows.

    Returns the number of valid road samples written.
    """
    props = event.get('properties', {})
    geom = event.get('geometry', {})
    if not props or not geom or geom.get('type') != 'Point':
        print("  Skipping: missing point geometry")
        return 0

    event_type = props.get('eventtype')
    event_id = props.get('eventid')
    episode_id = props.get('episodeid')
    alert_level = props.get('alertlevel', 'Green')
    severity = props.get('severitydata', {}).get('severity', 0.0)
    center_lon, center_lat = geom['coordinates']
    alert_level_ordinal = ALERT_LEVEL_MAP.get(alert_level, 1)

    # Fetch GDACS geometry
    poly_data = gdacs.get_event_geometry(event_type, event_id, episode_id)
    affected_polygon = None
    has_polygon = False
    polygon_extent_deg = 0.1  # default for point-only events

    if poly_data and 'features' in poly_data:
        for feat in poly_data.get('features', []):
            gtype = feat.get('geometry', {}).get('type', '')
            if gtype in ('Polygon', 'MultiPolygon'):
                try:
                    affected_polygon = shape(feat['geometry'])
                    has_polygon = True
                    bounds = affected_polygon.bounds
                    polygon_extent_deg = max(bounds[2] - bounds[0],
                                             bounds[3] - bounds[1])
                    print(f"  Found polygon (extent ~{polygon_extent_deg:.3f} deg)")
                except Exception as e:
                    print(f"  Polygon parse error: {e}")
                break

    radius_km = get_derived_radius_km(event_type, alert_level_ordinal)

    # === INNER ZONE: roads inside / near the affected area ===
    if has_polygon:
        inner_bbox_raw = affected_polygon.bounds
    else:
        lat_off = radius_km / 111.0
        lon_off = radius_km / (111.0 * math.cos(math.radians(center_lat)) + 1e-9)
        inner_bbox_raw = (center_lon - lon_off, center_lat - lat_off,
                          center_lon + lon_off, center_lat + lat_off)

    inner_bbox = cap_bbox(*inner_bbox_raw, max_span=0.1)
    print("  Fetching inner zone...")
    inner_ways = fetch_roads(osm, inner_bbox)
    print(f"  Inner: {len(inner_ways)} roads")

    # === OUTER ZONE: roads outside the affected area ===
    time.sleep(1.5)  # respect Overpass rate limits between queries
    outer_bbox = get_outer_bbox(center_lon, center_lat,
                                polygon_extent_deg, event_index)
    print("  Fetching outer zone...")
    outer_ways = fetch_roads(osm, outer_bbox)
    print(f"  Outer: {len(outer_ways)} roads")

    # Balanced sampling: up to 50 from each zone
    max_per_zone = 50
    if len(inner_ways) > max_per_zone:
        inner_ways = random.sample(inner_ways, max_per_zone)
    if len(outer_ways) > max_per_zone:
        outer_ways = random.sample(outer_ways, max_per_zone)

    all_ways = inner_ways + outer_ways
    if not all_ways:
        print("  No roads found in either zone")
        return 0

    valid = 0
    for way in all_ways:
        row = compute_road_row(
            way, event_id, event_type, alert_level_ordinal, severity,
            center_lon, center_lat, affected_polygon, has_polygon, radius_km
        )
        if row is not None:
            writer.writerow(row)
            valid += 1

    print(f"  Added {valid} samples ({len(inner_ways)} inner + {len(outer_ways)} outer)")
    return valid


def main():
    random.seed(42)
    gdacs = GDACSClient()
    osm = OSMClient()

    events = gdacs.get_recent_events(limit=15)
    print(f"Fetched {len(events)} events from GDACS.\n")

    csv_path = os.path.join(os.path.dirname(__file__), 'training_data.csv')
    total = 0

    with open(csv_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(CSV_COLUMNS)

        for i, event in enumerate(events):
            p = event.get('properties', {})
            eid = p.get('eventid')
            etype = p.get('eventtype')
            print(f"Event {i + 1}/{len(events)}: {etype}-{eid}")
            rows = process_event(event, gdacs, osm, writer, event_index=i)
            total += rows
            f.flush()  # flush after each event so partial results are saved
            time.sleep(2)  # inter-event delay for Overpass

    print(f"\nDataset building complete. Total rows: {total}")


if __name__ == '__main__':
    main()
