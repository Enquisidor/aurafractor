/**
 * Typed API client for the Aurafractor backend.
 * All requests include the Bearer session token from secure storage.
 */

import { Platform } from 'react-native';
import { storage } from '../storage/platform';

// Android emulator routes 10.0.2.2 → host machine; iOS simulator uses localhost
const DEV_HOST = Platform.OS === 'android' ? '10.0.2.2' : 'localhost';

export const BASE_URL = __DEV__
  ? `http://${DEV_HOST}:5001`
  : 'https://api.aurafractor.com';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface AuthResponse {
  user_id: string;
  session_token: string;
  refresh_token: string;
  expires_in: number;
  subscription_tier: 'free' | 'pro' | 'studio';
  credits_remaining: number;
  is_new_user: boolean;
  timestamp: string;
}

export interface UploadResponse {
  track_id: string;
  uploaded_at: string;
  duration_seconds: number;
  file_size_mb: number;
  audio_url: string;
  genre_detected: string;
  tempo_detected: number;
  status: string;
}

export interface LabelSuggestion {
  label: string;
  confidence: number;
  frequency_range: [number, number];
  recommended: boolean;
}

export interface SuggestLabelsResponse {
  track_id: string;
  suggested_labels: LabelSuggestion[];
  genre: string;
  tempo: number;
  user_history_suggestions: string[];
}

export interface ExtractionSource {
  label: string;
  model?: 'demucs' | 'spleeter';
}

export interface ExtractionResult {
  label: string;
  model_used: string;
  audio_url: string;
  waveform_url: string;
  duration_seconds: number;
  sample_rate: number;
}

export interface ExtractionResponse {
  extraction_id: string;
  track_id: string;
  status: 'queued' | 'processing' | 'completed' | 'failed' | 'awaiting_confirmation';
  job_id?: string;
  cost_credits?: number;
  cost_breakdown?: {
    total_cost: number;
    base_cost: number;
    ambiguity_cost: number;
    ambiguous_labels: number;
  };
  ambiguous_labels?: Array<{ label: string; ambiguity_score: number; suggestion: string }>;
  estimated_time_seconds?: number;
  queue_position?: number;
  created_at?: string;
  started_at?: string | null;
  completed_at?: string | null;
  processing_time_seconds?: number;
  results?: { sources: ExtractionResult[] };
  message?: string;
}

export interface FeedbackResponse {
  feedback_id: string;
  extraction_id: string;
  status: 'recorded' | 'queued_for_reextraction';
  reextraction_queued: boolean;
  new_extraction_id: string | null;
  cost_credits: number;
  created_at: string;
}

export interface TrackSummary {
  track_id: string;
  filename: string;
  uploaded_at: string;
  extractions_count: number;
  latest_extraction: { extraction_id: string; status: string } | null;
}

export interface HistoryResponse {
  total_tracks: number;
  tracks: TrackSummary[];
  pagination: { limit: number; offset: number; has_more: boolean };
}

export interface CreditsResponse {
  current_balance: number;
  monthly_allowance: number;
  subscription_tier: 'free' | 'pro' | 'studio';
  reset_date: string;
  usage_this_month: { extractions: number; credits_spent: number };
  recent_transactions: Array<{
    amount: number;
    reason: string;
    balance_after: number;
    created_at: string;
  }>;
}

// ---------------------------------------------------------------------------
// HTTP helpers
// ---------------------------------------------------------------------------

async function getToken(): Promise<string | null> {
  return storage.getItem('session_token');
}

const REQUEST_TIMEOUT_MS = 10_000;

async function request<T>(
  path: string,
  options: RequestInit = {},
  isFormData = false,
): Promise<T> {
  const token = await getToken();
  const headers: Record<string, string> = {
    ...(options.headers as Record<string, string>),
  };
  if (!isFormData) {
    headers['Content-Type'] = 'application/json';
  }
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);

  let res: Response;
  try {
    res = await fetch(`${BASE_URL}${path}`, { ...options, headers, signal: controller.signal });
  } catch (e: unknown) {
    if (e instanceof Error && e.name === 'AbortError') {
      throw new Error('Request timed out — backend unreachable');
    }
    throw e;
  } finally {
    clearTimeout(timer);
  }

  const json = await res.json();

  if (!res.ok) {
    throw new ApiError(json.error ?? 'Unknown error', res.status);
  }
  return json as T;
}

export class ApiError extends Error {
  constructor(
    message: string,
    public readonly status: number,
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

// ---------------------------------------------------------------------------
// Auth
// ---------------------------------------------------------------------------

export const auth = {
  register: (deviceId: string, appVersion?: string) =>
    request<AuthResponse>('/auth/register', {
      method: 'POST',
      body: JSON.stringify({ device_id: deviceId, app_version: appVersion }),
    }),

  refresh: (refreshToken: string) =>
    request<{ session_token: string; expires_in: number }>('/auth/refresh', {
      method: 'POST',
      body: JSON.stringify({ refresh_token: refreshToken }),
    }),
};

// ---------------------------------------------------------------------------
// Upload
// ---------------------------------------------------------------------------

export const upload = {
  audio: async (fileUri: string, filename: string, mimeType: string, clientId?: string): Promise<UploadResponse> => {
    const formData = new FormData();
    formData.append('file', { uri: fileUri, name: filename, type: mimeType } as unknown as Blob);
    if (clientId) formData.append('client_id', clientId);
    return request<UploadResponse>('/upload', { method: 'POST', body: formData }, true);
  },
};

// ---------------------------------------------------------------------------
// Extraction
// ---------------------------------------------------------------------------

export const extraction = {
  suggestLabels: (trackId: string) =>
    request<SuggestLabelsResponse>('/extraction/suggest-labels', {
      method: 'POST',
      body: JSON.stringify({ track_id: trackId }),
    }),

  extract: (trackId: string, sources: ExtractionSource[], forceAmbiguous = false) =>
    request<ExtractionResponse>('/extraction/extract', {
      method: 'POST',
      body: JSON.stringify({ track_id: trackId, sources, force_ambiguous: forceAmbiguous }),
    }),

  poll: (extractionId: string) =>
    request<ExtractionResponse>(`/extraction/${extractionId}`),

  feedback: (
    extractionId: string,
    body: {
      feedback_type: 'too_much' | 'too_little' | 'artifacts' | 'good';
      segment_label: string;
      segment_start_seconds?: number;
      segment_end_seconds?: number;
      feedback_detail?: string;
      refined_label?: string;
      comment?: string;
    },
  ) =>
    request<FeedbackResponse>(`/extraction/${extractionId}/feedback`, {
      method: 'POST',
      body: JSON.stringify(body),
    }),
};

// ---------------------------------------------------------------------------
// User
// ---------------------------------------------------------------------------

export const user = {
  history: (limit = 20, offset = 0) =>
    request<HistoryResponse>(`/user/history?limit=${limit}&offset=${offset}`),

  credits: () => request<CreditsResponse>('/user/credits'),

  deleteTrack: (trackId: string) =>
    request<{ track_id: string; deleted_at: string }>(`/track/${trackId}`, { method: 'DELETE' }),
};
