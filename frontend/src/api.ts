import type { AppState, Disaster, DispatchResult, ModelInfo } from './types';

const BASE_URL = '/api';

async function request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const response = await fetch(`${BASE_URL}${endpoint}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
    },
  });

  if (!response.ok) {
    let errorMsg = `HTTP ${response.status}`;
    try {
      const errorData = await response.json();
      if (errorData.error) errorMsg = errorData.error;
    } catch (e) {
      // Ignore parse error
    }
    throw new Error(errorMsg);
  }

  return response.json();
}

export const api = {
  getDisasters: () => request<Disaster[]>('/disasters'),
  
  loadDisaster: (event_type: string, event_id: number) => 
    request<any>('/load-disaster', {
      method: 'POST',
      body: JSON.stringify({ event_type, event_id })
    }),

  getState: () => request<AppState>('/state'),

  dispatchNext: () => request<DispatchResult>('/dispatch', { method: 'POST' }),

  blockRoad: (u: string, v: string) => 
    request<any>('/road/block', {
      method: 'POST',
      body: JSON.stringify({ u, v })
    }),

  unblockRoad: (u: string, v: string) => 
    request<any>('/road/unblock', {
      method: 'POST',
      body: JSON.stringify({ u, v })
    }),

  reset: () => request<any>('/reset', { method: 'POST' }),

  getModelInfo: () => request<ModelInfo>('/model-info'),
};
