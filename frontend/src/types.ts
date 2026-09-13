export interface Disaster {
  event_id: number;
  event_type: string;
  name: string;
  country: string;
  alert_level: 'Green' | 'Orange' | 'Red';
  severity: number;
  date: string;
}

export interface Node {
  lat: number;
  lon: number;
}

export interface Edge {
  u: string;
  v: string;
  risk_weight: number;
  normal_weight: number;
  blocked: boolean;
}

export interface Emergency {
  request_id: string;
  location_node: string;
  severity: number;
  medical_urgency: number;
  affected_people: number;
  waiting_minutes?: number;
  urgency_score: number;
}

export interface AppState {
  event: {
    event_id: number;
    event_type: string;
    alert_level: string;
    center: [number, number];
  } | null;
  rescue_base: string | null;
  nodes: Record<string, Node>;
  edges: Edge[];
  emergencies: Emergency[];
  dispatch_log: DispatchResult[];
}

export interface DispatchResult {
  status: string;
  request_id: string;
  target_node: string;
  urgency_score: number;
  risk_aware_route?: {
    path: string[];
    coordinates: number[][];
    total_cost: number;
  };
  normal_route?: {
    path: string[];
    coordinates: number[][];
    total_distance_km: number;
  };
  routes_differ: boolean;
  message?: string;
}

export interface ModelInfo {
  selected_model: string;
  primary_metric: string;
  metrics: Record<string, { mean_rmse: number; std_rmse: number; fold_rmse: number[] }>;
  training_metadata: {
    dataset_statistics: {
      row_count: number;
    };
    trained_at_utc: string;
  };
}
