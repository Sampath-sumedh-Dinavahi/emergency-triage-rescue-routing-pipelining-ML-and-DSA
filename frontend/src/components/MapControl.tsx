import { useRef, useEffect, useMemo, useState, useCallback } from 'react';
import Map, { Popup, Marker, NavigationControl } from 'react-map-gl/maplibre';
import type { MapRef } from 'react-map-gl/maplibre';
import type { Map as MaplibreMap } from 'maplibre-gl';
import 'maplibre-gl/dist/maplibre-gl.css';
import type { AppState, DispatchResult } from '../types';
import { api } from '../api';

interface MapControlProps {
  appState: AppState | null;
  latestDispatch: DispatchResult | null;
  onStateChange: () => void;
}

const EMPTY_LINE = {
  type: 'Feature' as const,
  properties: {},
  geometry: { type: 'LineString' as const, coordinates: [] as number[][] }
};

// Inline style — no external style.json fetch, onLoad fires reliably
const MAP_STYLE = {
  version: 8 as const,
  sources: {
    'osm-tiles': {
      type: 'raster' as const,
      tiles: ['https://tile.openstreetmap.org/{z}/{x}/{y}.png'],
      tileSize: 256,
      attribution: '&copy; OpenStreetMap contributors',
      maxzoom: 19,
    },
  },
  layers: [
    {
      id: 'osm-background',
      type: 'raster' as const,
      source: 'osm-tiles',
      minzoom: 0,
      maxzoom: 19,
    },
  ],
  glyphs: 'https://demotiles.maplibre.org/font/{fontstack}/{range}.pbf',
  sprite: '',
};

// ─── Fully imperative map management ─────────────────────────────────────────
// We do NOT use react-map-gl <Source>/<Layer> for dynamic data.
// Instead we manage all data sources & layers directly on the MapLibre GL map instance.
// This avoids the react-map-gl Source timing and lifecycle issues.

function addRouteSources(map: MaplibreMap) {
  if (!map.getSource('route-risk')) {
    map.addSource('route-risk', { type: 'geojson', data: EMPTY_LINE as any });
  }
  if (!map.getSource('route-normal')) {
    map.addSource('route-normal', { type: 'geojson', data: EMPTY_LINE as any });
  }
}

function addRouteLayers(map: MaplibreMap) {
  if (!map.getLayer('layer-route-normal')) {
    map.addLayer({
      id: 'layer-route-normal',
      type: 'line',
      source: 'route-normal',
      layout: { 'line-join': 'round', 'line-cap': 'round' },
      paint: {
        'line-color': '#64748b',
        'line-width': 3,
        'line-opacity': 0.75,
        'line-dasharray': [3, 3],
      },
    });
  }
  if (!map.getLayer('layer-route-risk')) {
    map.addLayer({
      id: 'layer-route-risk',
      type: 'line',
      source: 'route-risk',
      layout: { 'line-join': 'round', 'line-cap': 'round' },
      paint: {
        'line-color': '#10b981',
        'line-width': 6,
        'line-opacity': 0.95,
      },
    });
  }
  if (!map.getLayer('layer-route-risk-glow')) {
    map.addLayer({
      id: 'layer-route-risk-glow',
      type: 'line',
      source: 'route-risk',
      layout: { 'line-join': 'round', 'line-cap': 'round' },
      paint: {
        'line-color': '#10b981',
        'line-width': 14,
        'line-opacity': 0.12,
        'line-blur': 6,
      },
    });
  }
}

function addRoadSources(map: MaplibreMap) {
  if (!map.getSource('roads')) {
    map.addSource('roads', { type: 'geojson', data: { type: 'FeatureCollection', features: [] } });
  }
}

function addRoadLayers(map: MaplibreMap) {
  if (!map.getLayer('road-visible')) {
    map.addLayer({
      id: 'road-visible',
      type: 'line',
      source: 'roads',
      layout: { 'line-cap': 'round', 'line-join': 'round' },
      paint: {
        'line-color': ['get', 'color'],
        'line-width': ['case', ['get', 'blocked'], 1.5, 4],
        'line-opacity': ['case', ['get', 'blocked'], 0.3, 0.9],
      },
    });
  }
  if (!map.getLayer('road-hitbox')) {
    map.addLayer({
      id: 'road-hitbox',
      type: 'line',
      source: 'roads',
      paint: { 'line-width': 18, 'line-opacity': 0 },
    });
  }
}

export default function MapControl({ appState, latestDispatch, onStateChange }: MapControlProps) {
  const mapRef = useRef<MapRef>(null);
  const mapReadyRef = useRef(false);
  const [hoverInfo, setHoverInfo] = useState<{ lngLat: { lng: number; lat: number }; props: any } | null>(null);

  // ─── Road network GeoJSON ──────────────────────────────────────────────────
  const roadData = useMemo(() => {
    if (!appState?.edges) return null;
    const features: any[] = [];
    for (const edge of appState.edges) {
      const u = appState.nodes[edge.u];
      const v = appState.nodes[edge.v];
      if (!u || !v) continue;
      const ratio = edge.normal_weight > 0 ? edge.risk_weight / edge.normal_weight : 1;
      const impact = Math.max(0, Math.min(1, (ratio - 1) / 9.0));
      const color = edge.blocked ? '#334155'
        : impact < 0.3 ? '#22c55e'
        : impact < 0.65 ? '#f59e0b'
        : '#ef4444';
      features.push({
        type: 'Feature',
        properties: { u: edge.u, v: edge.v, color, blocked: edge.blocked,
          risk: edge.risk_weight, normal: edge.normal_weight, impactScore: impact },
        geometry: { type: 'LineString', coordinates: [[u.lon, u.lat], [v.lon, v.lat]] },
      });
    }
    return { type: 'FeatureCollection', features } as any;
  }, [appState]);

  // ─── Update road network imperatively ─────────────────────────────────────
  useEffect(() => {
    const map = mapRef.current?.getMap();
    if (!map || !mapReadyRef.current || !roadData) return;
    (map.getSource('roads') as any)?.setData(roadData);
  }, [roadData]);

  // ─── Update routes imperatively ───────────────────────────────────────────
  const applyRoutes = useCallback((map: MaplibreMap, dispatch: DispatchResult | null) => {
    const riskSrc = map.getSource('route-risk') as any;
    const normalSrc = map.getSource('route-normal') as any;
    if (!riskSrc || !normalSrc) return;

    if (dispatch?.status === 'dispatched') {
      const riskCoords = dispatch.risk_aware_route?.coordinates ?? [];
      const normalCoords = dispatch.normal_route?.coordinates ?? [];

      riskSrc.setData(riskCoords.length >= 2
        ? { type: 'Feature', properties: {}, geometry: { type: 'LineString', coordinates: riskCoords } }
        : EMPTY_LINE);

      normalSrc.setData(normalCoords.length >= 2
        ? { type: 'Feature', properties: {}, geometry: { type: 'LineString', coordinates: normalCoords } }
        : EMPTY_LINE);

      // Frame the route
      const allCoords = [...riskCoords, ...normalCoords];
      if (allCoords.length >= 2) {
        const lngs = allCoords.map(c => c[0]);
        const lats = allCoords.map(c => c[1]);
        const minLng = Math.min(...lngs), maxLng = Math.max(...lngs);
        const minLat = Math.min(...lats), maxLat = Math.max(...lats);
        const lngBuf = Math.max((maxLng - minLng) * 0.25, 0.005);
        const latBuf = Math.max((maxLat - minLat) * 0.25, 0.005);
        mapRef.current?.fitBounds(
          [[minLng - lngBuf, minLat - latBuf], [maxLng + lngBuf, maxLat + latBuf]],
          { padding: 100, duration: 1200, pitch: 25 }
        );
      }
    } else {
      riskSrc.setData(EMPTY_LINE);
      normalSrc.setData(EMPTY_LINE);
    }
  }, []);

  useEffect(() => {
    const map = mapRef.current?.getMap();
    if (!map || !mapReadyRef.current) return;
    applyRoutes(map, latestDispatch);
  }, [latestDispatch, applyRoutes]);

  // ─── Camera: frame disaster area ──────────────────────────────────────────
  useEffect(() => {
    if (!appState?.event || !appState.edges.length || !mapRef.current || !mapReadyRef.current) return;
    let minLng = 180, maxLng = -180, minLat = 90, maxLat = -90, hasPoints = false;
    for (const edge of appState.edges) {
      const u = appState.nodes[edge.u];
      if (!u) continue;
      hasPoints = true;
      minLng = Math.min(minLng, u.lon); maxLng = Math.max(maxLng, u.lon);
      minLat = Math.min(minLat, u.lat); maxLat = Math.max(maxLat, u.lat);
    }
    if (hasPoints) {
      const lngBuf = (maxLng - minLng) * 0.15;
      const latBuf = (maxLat - minLat) * 0.15;
      mapRef.current.fitBounds(
        [[minLng - lngBuf, minLat - latBuf], [maxLng + lngBuf, maxLat + latBuf]],
        { padding: 80, duration: 2000, pitch: 30, bearing: 0 }
      );
    }
  }, [appState?.event]); // eslint-disable-line react-hooks/exhaustive-deps

  const handleBlockToggle = useCallback(async (u: string, v: string, blocked: boolean) => {
    setHoverInfo(null);
    try {
      if (blocked) await api.unblockRoad(u, v);
      else await api.blockRoad(u, v);
      onStateChange();
    } catch (e: any) {
      console.error('Road toggle failed:', e.message);
    }
  }, [onStateChange]);

  const handleMapLoad = useCallback(() => {
    const map = mapRef.current?.getMap();
    if (!map) return;
    mapReadyRef.current = true;

    addRouteSources(map);
    addRoadSources(map);
    addRoadLayers(map);
    addRouteLayers(map);

    if (roadData) (map.getSource('roads') as any)?.setData(roadData);
    applyRoutes(map, latestDispatch);
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <Map
      ref={mapRef}
      initialViewState={{ longitude: 20, latitude: 15, zoom: 2 }}
      minZoom={1.5}
      maxZoom={19}
      renderWorldCopies={false}
      mapStyle={MAP_STYLE}
      interactiveLayerIds={['road-hitbox']}
      onLoad={handleMapLoad}
      onClick={(e) => {
        if (e.features && e.features.length > 0) {
          setHoverInfo({ lngLat: e.lngLat, props: e.features[0].properties });
        } else {
          setHoverInfo(null);
        }
      }}
      cursor={hoverInfo ? 'pointer' : 'grab'}
      style={{ position: 'absolute', inset: 0 }}
    >
      <NavigationControl position="top-right" />

      {/* Road click popup */}
      {hoverInfo && (
        <Popup
          longitude={hoverInfo.lngLat.lng}
          latitude={hoverInfo.lngLat.lat}
          closeButton={false}
          anchor="bottom"
          offset={12}
        >
          <div
            className="rounded-lg overflow-hidden shadow-2xl min-w-[200px]"
            style={{ background: 'var(--bg-elevated)', border: '1px solid var(--border-default)' }}
          >
            <div className="px-3 py-2" style={{ borderBottom: '1px solid var(--border-subtle)', background: 'var(--bg-surface)' }}>
              <div className="text-[9px] font-black tracking-widest uppercase" style={{ color: 'var(--text-muted)' }}>Road Segment</div>
              <div className="font-mono text-[9px] mt-0.5 truncate" style={{ color: 'var(--text-secondary)' }}>
                {hoverInfo.props.u} ↔ {hoverInfo.props.v}
              </div>
            </div>
            <div className="px-3 py-2 grid grid-cols-2 gap-y-2 gap-x-4 text-xs">
              <div style={{ color: 'var(--text-muted)' }} className="text-[10px]">Status</div>
              <div className="text-right font-bold text-[10px]" style={{ color: hoverInfo.props.blocked ? '#64748b' : '#10b981' }}>
                {hoverInfo.props.blocked ? 'BLOCKED' : 'ACTIVE'}
              </div>
              <div style={{ color: 'var(--text-muted)' }} className="text-[10px]">Exposure</div>
              <div className="text-right font-mono text-[10px]" style={{ color: 'var(--text-primary)' }}>
                {(hoverInfo.props.impactScore * 100).toFixed(1)}%
              </div>
              <div style={{ color: 'var(--text-muted)' }} className="text-[10px]">Cost</div>
              <div className="text-right font-mono text-[10px]" style={{ color: 'var(--text-secondary)' }}>
                {Number(hoverInfo.props.risk).toFixed(3)}
              </div>
            </div>
            <div className="px-3 pb-3">
              <button
                onClick={() => handleBlockToggle(hoverInfo.props.u, hoverInfo.props.v, hoverInfo.props.blocked)}
                className="w-full py-1.5 rounded text-[10px] font-bold tracking-wider transition-all"
                style={{
                  background: hoverInfo.props.blocked ? 'rgba(16,185,129,0.12)' : 'rgba(239,68,68,0.12)',
                  border: hoverInfo.props.blocked ? '1px solid rgba(16,185,129,0.4)' : '1px solid rgba(239,68,68,0.4)',
                  color: hoverInfo.props.blocked ? '#10b981' : '#ef4444',
                }}
              >
                {hoverInfo.props.blocked ? 'UNBLOCK SEGMENT' : 'BLOCK SEGMENT'}
              </button>
            </div>
          </div>
        </Popup>
      )}

      {/* Emergency markers */}
      {appState?.emergencies.map((em, idx) => {
        const node = appState.nodes[em.location_node];
        if (!node) return null;
        const isTop = idx === 0;
        return (
          <Marker key={em.request_id} longitude={node.lon} latitude={node.lat} anchor="center">
            <div
              className="relative flex items-center justify-center rounded-full font-black text-white shadow-lg"
              style={{
                width: isTop ? 22 : 14,
                height: isTop ? 22 : 14,
                fontSize: isTop ? 9 : 7,
                background: isTop ? '#ef4444' : '#f59e0b',
                border: isTop ? '2px solid rgba(255,255,255,0.5)' : '1.5px solid rgba(255,255,255,0.3)',
                zIndex: isTop ? 20 : 10,
                boxShadow: isTop ? '0 0 0 4px rgba(239,68,68,0.25)' : undefined,
              }}
            >
              {idx + 1}
              {isTop && (
                <span className="absolute inset-0 rounded-full op-ping" style={{ background: 'rgba(239,68,68,0.35)' }} />
              )}
            </div>
          </Marker>
        );
      })}

      {/* Rescue base marker */}
      {appState?.rescue_base && appState.nodes[appState.rescue_base] && (() => {
        const node = appState.nodes[appState.rescue_base!];
        return (
          <Marker longitude={node.lon} latitude={node.lat} anchor="center">
            <div
              className="flex items-center justify-center rounded-full shadow-xl"
              style={{ width: 22, height: 22, background: '#1d4ed8', border: '2px solid rgba(147,197,253,0.6)', zIndex: 30, boxShadow: '0 0 0 4px rgba(59,130,246,0.25)' }}
            >
              <svg width="10" height="10" viewBox="0 0 10 10" fill="none">
                <rect x="4" y="1" width="2" height="8" rx="1" fill="white" />
                <rect x="1" y="4" width="8" height="2" rx="1" fill="white" />
              </svg>
            </div>
          </Marker>
        );
      })()}
    </Map>
  );
}
