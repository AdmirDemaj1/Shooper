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

// ── Match types ──────────────────────────────────────────────────────────────

export interface ListingSlim {
  id: string;
  source_id?: string;
  source_url?: string;
  title?: string;
  make?: string;
  model?: string;
  year?: number;
  price?: string;
  currency?: string;
  mileage?: number;
  location_text?: string;
  description?: string;
}

export interface Match {
  id: string;
  search_profile_id: string;
  listing_id: string;
  relevance_score?: number;
  score_source?: string;
  llm_reasoning?: string;
  summary?: string;
  selected_for_delivery: boolean;
  delivery_status: string;
  user_action?: string;
  delivered_at?: string;
  created_at: string;
  listing?: ListingSlim;
}

export interface MatchListResponse {
  matches: Match[];
  has_more: boolean;
  next_cursor?: string;
}

// ── Platform listings ─────────────────────────────────────────────────────────

export interface PlatformListing {
  id: string;
  seller_user_id?: string;
  source_id: string;
  source_url?: string;
  title?: string;
  make?: string;
  model?: string;
  year?: number;
  price?: string;
  currency: string;
  mileage?: number;
  location_text?: string;
  transmission?: string;
  fuel_type?: string;
  body_type?: string;
  description?: string;
  contact_phone?: string;
  photo_urls: string[];
  status: 'active' | 'sold' | 'expired' | 'removed';
  views_count: number;
  is_active: boolean;
  created_at: string;
}

export interface ListingCreateInput {
  title: string;
  make?: string;
  model?: string;
  year?: number;
  price?: string;
  currency?: string;
  mileage?: number;
  location_text?: string;
  transmission?: string;
  fuel_type?: string;
  body_type?: string;
  description?: string;
  contact_phone?: string;
}

export interface ListingBrowseResponse {
  listings: PlatformListing[];
  has_more: boolean;
  next_cursor?: string;
}

export const platformListingsApi = {
  browse: (params?: Record<string, any>): Promise<ListingBrowseResponse> =>
    apiClient.get<ListingBrowseResponse>('/listings', { params }).then((r) => r.data),

  get: (id: string): Promise<PlatformListing> =>
    apiClient.get<PlatformListing>(`/listings/${id}`).then((r) => r.data),

  create: (data: ListingCreateInput): Promise<PlatformListing> =>
    apiClient.post<PlatformListing>('/listings', data).then((r) => r.data),

  update: (id: string, data: Partial<ListingCreateInput & { status: string }>): Promise<PlatformListing> =>
    apiClient.patch<PlatformListing>(`/listings/${id}`, data).then((r) => r.data),

  remove: (id: string): Promise<void> =>
    apiClient.delete(`/listings/${id}`).then(() => undefined),

  myListings: (): Promise<PlatformListing[]> =>
    apiClient.get<PlatformListing[]>('/me/listings').then((r) => r.data),

  getPhotoUploadUrl: (id: string): Promise<{ upload_url: string; final_url: string }> =>
    apiClient.post<{ upload_url: string; final_url: string }>(`/listings/${id}/photos`).then((r) => r.data),

  confirmPhotoUpload: (id: string, url: string): Promise<PlatformListing> =>
    apiClient.post<PlatformListing>(`/listings/${id}/photos/confirm`, { url }).then((r) => r.data),

  uploadPhotoDirect: async (id: string, uri: string): Promise<PlatformListing> => {
    const form = new FormData();
    form.append('file', { uri, name: 'photo.jpg', type: 'image/jpeg' } as any);
    const response = await apiClient.post<PlatformListing>(`/listings/${id}/photos/upload`, form, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return response.data;
  },

  removePhoto: (id: string, url: string): Promise<void> =>
    apiClient.delete(`/listings/${id}/photos`, { data: { url } }).then(() => undefined),
};

// ── Matching API ─────────────────────────────────────────────────────────────

export interface RunMatchResult {
  status: string;
  candidates: number;
  inserted: number;
  skipped: number;
  top_n: number;
}

export const matchingApi = {
  runNow: (profileId: string): Promise<RunMatchResult> =>
    apiClient.post<RunMatchResult>(`/admin/profiles/${profileId}/run-match-now`).then((r) => r.data),
};

// ── Matches API ──────────────────────────────────────────────────────────────

export const matchesApi = {
  listForProfile: (profileId: string, cursor?: string): Promise<MatchListResponse> =>
    apiClient
      .get<MatchListResponse>(`/profiles/${profileId}/matches`, {
        params: cursor ? { cursor, limit: 20 } : { limit: 20 },
      })
      .then((r) => r.data),

  get: (matchId: string): Promise<Match> =>
    apiClient.get<Match>(`/matches/${matchId}`).then((r) => r.data),

  recordAction: (matchId: string, action: 'clicked' | 'dismissed' | 'saved'): Promise<void> =>
    apiClient.post(`/matches/${matchId}/action`, { action }).then(() => undefined),
};
