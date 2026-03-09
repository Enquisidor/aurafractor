import { configureStore } from '@reduxjs/toolkit';
import uploadQueueReducer from './uploadQueueSlice';

export const store = configureStore({
  reducer: {
    uploadQueue: uploadQueueReducer,
  },
});

export type RootState = ReturnType<typeof store.getState>;
export type AppDispatch = typeof store.dispatch;
