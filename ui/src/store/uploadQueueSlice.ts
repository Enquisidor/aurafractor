/**
 * Redux slice for the client-side upload queue.
 *
 * Tracks upload attempts on-device so History shows entries even when the
 * backend is unreachable. Queued "failed" entries are retried automatically
 * when the backend comes back online via `syncUploadQueue`.
 */

import { createAsyncThunk, createSlice, PayloadAction } from '@reduxjs/toolkit';
import { extraction as extractionApi, upload as uploadApi } from '../api/client';
import { storage } from '../storage/platform';

const PERSIST_KEY = 'upload_queue';

export type UploadStatus = 'uploading' | 'uploaded' | 'failed' | 'queued';

export interface UploadEntry {
  localId: string;
  filename: string;
  fileUri: string;
  mimeType: string;
  attemptedAt: string;   // ISO
  status: UploadStatus;
  trackId?: string;
  errorMessage?: string;
}

interface UploadQueueState {
  entries: UploadEntry[];
  hydrated: boolean;
}

const initialState: UploadQueueState = {
  entries: [],
  hydrated: false,
};

// ---------------------------------------------------------------------------
// Persistence helpers
// ---------------------------------------------------------------------------

async function persist(entries: UploadEntry[]): Promise<void> {
  // Only persist non-uploading entries (uploading = in-flight, won't survive restart)
  const toSave = entries.filter((e) => e.status !== 'uploading');
  await storage.setItem(PERSIST_KEY, JSON.stringify(toSave));
}

// ---------------------------------------------------------------------------
// Thunks
// ---------------------------------------------------------------------------

/** Load persisted queue on app start. */
export const hydrateUploadQueue = createAsyncThunk(
  'uploadQueue/hydrate',
  async (): Promise<UploadEntry[]> => {
    const raw = await storage.getItem(PERSIST_KEY);
    if (!raw) return [];
    try { return JSON.parse(raw) as UploadEntry[]; } catch { return []; }
  },
);

/**
 * Retry all entries currently in `queued` status.
 * Called whenever the backend is confirmed reachable (e.g. successful auth).
 */
export const syncUploadQueue = createAsyncThunk(
  'uploadQueue/sync',
  async (_, { getState, dispatch }) => {
    const state = (getState() as { uploadQueue: UploadQueueState }).uploadQueue;
    const queued = state.entries.filter((e) => e.status === 'queued');
    for (const entry of queued) {
      dispatch(uploadQueueSlice.actions.setStatus({ localId: entry.localId, status: 'uploading' }));
      try {
        const uploadRes = await uploadApi.audio(entry.fileUri, entry.filename, entry.mimeType);
        await extractionApi.suggestLabels(uploadRes.track_id); // warm the track
        dispatch(uploadQueueSlice.actions.markUploaded({
          localId: entry.localId,
          trackId: uploadRes.track_id,
        }));
      } catch (e) {
        const msg = e instanceof Error ? e.message : 'Upload failed';
        dispatch(uploadQueueSlice.actions.markFailed({ localId: entry.localId, errorMessage: msg }));
      }
    }
  },
);

// ---------------------------------------------------------------------------
// Slice
// ---------------------------------------------------------------------------

export const uploadQueueSlice = createSlice({
  name: 'uploadQueue',
  initialState,
  reducers: {
    addEntry(state, action: PayloadAction<Omit<UploadEntry, 'attemptedAt' | 'status'>>) {
      const entry: UploadEntry = {
        ...action.payload,
        attemptedAt: new Date().toISOString(),
        status: 'uploading',
      };
      state.entries.unshift(entry);
      persist(state.entries);
    },
    setStatus(state, action: PayloadAction<{ localId: string; status: UploadStatus }>) {
      const entry = state.entries.find((e) => e.localId === action.payload.localId);
      if (entry) { entry.status = action.payload.status; persist(state.entries); }
    },
    markUploaded(state, action: PayloadAction<{ localId: string; trackId: string }>) {
      const entry = state.entries.find((e) => e.localId === action.payload.localId);
      if (entry) {
        entry.status = 'uploaded';
        entry.trackId = action.payload.trackId;
        entry.errorMessage = undefined;
        persist(state.entries);
      }
    },
    markFailed(state, action: PayloadAction<{ localId: string; errorMessage: string }>) {
      const entry = state.entries.find((e) => e.localId === action.payload.localId);
      if (entry) {
        // failed → queued so it will be retried on next sync
        entry.status = 'queued';
        entry.errorMessage = action.payload.errorMessage;
        persist(state.entries);
      }
    },
  },
  extraReducers: (builder) => {
    builder.addCase(hydrateUploadQueue.fulfilled, (state, action) => {
      state.entries = action.payload;
      state.hydrated = true;
    });
  },
});

export const { addEntry, markUploaded, markFailed } = uploadQueueSlice.actions;
export default uploadQueueSlice.reducer;
