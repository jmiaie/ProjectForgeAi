'use client';

import { useEffect, useState } from 'react';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { apiGet, apiPost } from '@/lib/api';

type MapMarker = {
  asset_id: string;
  name: string;
  latitude: number;
  longitude: number;
  asset_type: string;
  graph_node_id?: string | null;
};

type MapView = {
  marker_count: number;
  bounds: {
    min_lat: number;
    max_lat: number;
    min_lon: number;
    max_lon: number;
  } | null;
  markers: MapMarker[];
};

type SpatialStatus = {
  asset_count: number;
  rtk_cli_available: boolean;
};

type MapPanelProps = {
  projectId: string;
};

export function MapPanel({ projectId }: MapPanelProps) {
  const [mapView, setMapView] = useState<MapView | undefined>();
  const [status, setStatus] = useState<SpatialStatus | undefined>();
  const [name, setName] = useState('Site anchor');
  const [latitude, setLatitude] = useState('37.7749');
  const [longitude, setLongitude] = useState('-122.4194');
  const [message, setMessage] = useState('');

  const refresh = async () => {
    const [mapResult, statusResult] = await Promise.all([
      apiGet<MapView>(`/api/v1/projects/${projectId}/spatial/map`),
      apiGet<SpatialStatus>(`/api/v1/projects/${projectId}/spatial/status`),
    ]);
    setMapView(mapResult);
    setStatus(statusResult);
  };

  useEffect(() => {
    refresh().catch(() => undefined);
  }, [projectId]);

  const addAsset = async () => {
    await apiPost(`/api/v1/projects/${projectId}/spatial/assets`, {
      name,
      latitude: Number(latitude),
      longitude: Number(longitude),
      asset_type: 'site',
    });
    setMessage(`Registered spatial asset ${name}.`);
    await refresh();
  };

  const syncGraph = async () => {
    const result = await apiPost<{ synced: number; total_assets: number }>(
      `/api/v1/projects/${projectId}/spatial/sync-graph`,
      {},
    );
    setMessage(`Synced ${result.synced} graph node(s); ${result.total_assets} total assets.`);
    await refresh();
  };

  return (
    <Card className="panel">
      <div className="panel-header">
        <div>
          <div className="eyebrow">Spatial</div>
          <h2>Project map</h2>
          <p className="muted">Geo-tagged assets from RTK layer and graph node coordinates.</p>
        </div>
        <div className="row">
          <Button variant="outline" onClick={syncGraph}>Sync graph</Button>
          <Button variant="outline" onClick={refresh}>Refresh</Button>
        </div>
      </div>
      <div className="stack">
        {status ? (
          <p className="muted">
            {status.asset_count} asset(s) · RTK CLI {status.rtk_cli_available ? 'available' : 'not detected'}
          </p>
        ) : null}
        <div className="button-row">
          <input className="input" value={name} onChange={(event) => setName(event.target.value)} />
          <input className="input" value={latitude} onChange={(event) => setLatitude(event.target.value)} />
          <input className="input" value={longitude} onChange={(event) => setLongitude(event.target.value)} />
          <Button onClick={addAsset}>Add site</Button>
        </div>
        <SpatialMap mapView={mapView} />
        {message ? <p className="muted">{message}</p> : null}
      </div>
    </Card>
  );
}

function SpatialMap({ mapView }: { mapView: MapView | undefined }) {
  if (!mapView?.bounds || !mapView.markers.length) {
    return <p className="muted">Add spatial assets or sync graph nodes with latitude/longitude properties.</p>;
  }

  const { bounds, markers } = mapView;
  const latSpan = Math.max(bounds.max_lat - bounds.min_lat, 0.0001);
  const lonSpan = Math.max(bounds.max_lon - bounds.min_lon, 0.0001);

  return (
    <div className="spatial-map">
      {markers.map((marker) => {
        const left = ((marker.longitude - bounds.min_lon) / lonSpan) * 100;
        const top = (1 - (marker.latitude - bounds.min_lat) / latSpan) * 100;
        return (
          <div
            key={marker.asset_id}
            className="spatial-marker"
            style={{ left: `${left}%`, top: `${top}%` }}
            title={`${marker.name} (${marker.latitude}, ${marker.longitude})`}
          >
            <span>{marker.name}</span>
          </div>
        );
      })}
    </div>
  );
}
