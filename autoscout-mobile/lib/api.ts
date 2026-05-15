import axios from 'axios';
import * as SecureStore from 'expo-secure-store';

export const apiClient = axios.create({
  baseURL: process.env.EXPO_PUBLIC_API_URL || 'http://localhost:8000',
});

// Inject Firebase token from SecureStore on each request
apiClient.interceptors.request.use(async (config) => {
  try {
    const token = await SecureStore.getItemAsync('firebase_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
  } catch (error) {
    console.error('Error retrieving token from SecureStore:', error);
  }
  return config;
});

export async function syncUser(firebaseToken: string) {
  const response = await apiClient.post('/auth/sync', {
    firebase_token: firebaseToken,
  });
  return response.data;
}

// ── Profile types ────────────────────────────────────────────────────────────

export interface SearchProfile {
  id: string;
  user_id: string;
  name: string;
  make?: string;
  model?: string;
  year_min?: number;
  year_max?: number;
  price_min?: number;
  price_max?: number;
  currency: string;
  mileage_max?: number;
  location_lat?: number;
  location_lng?: number;
  radius_km?: number;
  body_type?: string;
  transmission?: string;
  fuel_type?: string;
  free_text_criteria?: string;
  delivery_time_local: number;
  timezone: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export type SearchProfileCreate = Omit<SearchProfile, 'id' | 'user_id' | 'created_at' | 'updated_at'>;

export interface ParseResponse {
  profile: SearchProfileCreate;
  needs_review: boolean;
  low_confidence_fields: string[];
}

// ── Profile API ──────────────────────────────────────────────────────────────

export const profilesApi = {
  list: (): Promise<SearchProfile[]> =>
    apiClient.get<SearchProfile[]>('/profiles').then((r) => r.data),

  create: (data: Partial<SearchProfileCreate>): Promise<SearchProfile> =>
    apiClient.post<SearchProfile>('/profiles', data).then((r) => r.data),

  update: (id: string, data: Partial<SearchProfileCreate>): Promise<SearchProfile> =>
    apiClient.patch<SearchProfile>(`/profiles/${id}`, data).then((r) => r.data),

  remove: (id: string): Promise<void> =>
    apiClient.delete(`/profiles/${id}`).then(() => undefined),

  toggle: (id: string): Promise<SearchProfile> =>
    apiClient.post<SearchProfile>(`/profiles/${id}/toggle`).then((r) => r.data),

  parse: (text: string): Promise<ParseResponse> =>
    apiClient.post<ParseResponse>('/profiles/parse', { text }).then((r) => r.data),
};
