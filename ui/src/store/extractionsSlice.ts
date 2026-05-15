/**
 * Redux slice for caching ExtractionResponse objects.
 *
 * Stores a map of extraction_id → ExtractionResponse so screens can read
 * previously seen results without waiting for a poll, and so the detail
 * screen can skip polling entirely when a terminal result is already cached.
 *
 * Persistence: every upsert writes the full map to platform storage under
 * 'extractions_cache'. Hydration happens at app startup alongside the upload
 * queue hydration in _layout.tsx.
 */

import { createAsyncThunk, createSlice, PayloadAction } from '@reduxjs/toolkit';
import { ExtractionResponse } from '../api/client';
import { storage } from '../storage/platform';
import { RootState } from './store';

const PERSIST_KEY = 'extractions_cache';

// ---------------------------------------------------------------------------
// State
// ---------------------------------------------------------------------------

interface ExtractionsState {
  /** Map of extraction_id → ExtractionResponse */
  extractions: Record<string, ExtractionResponse>;
  hydrated: boolean;
}

const initialState: ExtractionsState = {
  extractions: {},
  hydrated: false,
};

// ---------------------------------------------------------------------------
// Persistence helpers
// ---------------------------------------------------------------------------

async function persist(extractions: Record<string, ExtractionResponse>): Promise<void> {
  await storage.setItem(PERSIST_KEY, JSON.stringify(extractions));
}

// ---------------------------------------------------------------------------
// Thunks
// ---------------------------------------------------------------------------

/** Load persisted extractions cache on app start. */
export const hydrateExtractions = createAsyncThunk(
  'extractions/hydrate',
  async (): Promise<Record<string, ExtractionResponse>> => {
    const raw = await storage.getItem(PERSIST_KEY);
    if (!raw) return {};
    try {
      return JSON.parse(raw) as Record<string, ExtractionResponse>;
    } catch {
      return {};
    }
  },
);

// ---------------------------------------------------------------------------
// Slice
// ---------------------------------------------------------------------------

export const extractionsSlice = createSlice({
  name: 'extractions',
  initialState,
  reducers: {
    upsertExtraction(state, action: PayloadAction<ExtractionResponse>) {
      state.extractions[action.payload.extraction_id] = action.payload;
      // Fire-and-forget persistence — slice reducers must be synchronous;
      // the async write is intentionally not awaited here.
      persist(state.extractions);
    },
    clearExtractions(state) {
      state.extractions = {};
      persist(state.extractions);
    },
  },
  extraReducers: (builder) => {
    builder.addCase(hydrateExtractions.fulfilled, (state, action) => {
      state.extractions = action.payload;
      state.hydrated = true;
    });
  },
});

export const { upsertExtraction, clearExtractions } = extractionsSlice.actions;
export default extractionsSlice.reducer;

// ---------------------------------------------------------------------------
// Selectors
// ---------------------------------------------------------------------------

export function selectExtraction(id: string) {
  return (state: RootState): ExtractionResponse | undefined =>
    state.extractions.extractions[id];
}
