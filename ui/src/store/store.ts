import { configureStore } from '@reduxjs/toolkit';
import extractionsReducer from './extractionsSlice';
import uploadQueueReducer from './uploadQueueSlice';

export const store = configureStore({
  reducer: {
    uploadQueue: uploadQueueReducer,
    extractions: extractionsReducer,
  },
});

export type RootState = ReturnType<typeof store.getState>;
export type AppDispatch = typeof store.dispatch;
