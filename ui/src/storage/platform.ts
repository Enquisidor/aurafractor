/**
 * Platform-aware key-value storage.
 * Web: localStorage  |  Native: expo-secure-store
 */

import { Platform } from 'react-native';

interface Storage {
  getItem(key: string): Promise<string | null>;
  setItem(key: string, value: string): Promise<void>;
  removeItem(key: string): Promise<void>;
}

const webStorage: Storage = {
  getItem: (key) => Promise.resolve(localStorage.getItem(key)),
  setItem: (key, value) => Promise.resolve(localStorage.setItem(key, value)),
  removeItem: (key) => Promise.resolve(localStorage.removeItem(key)),
};

// Lazily resolved so expo-secure-store is never bundled for web
let _nativeStorage: Storage | null = null;
async function getNativeStorage(): Promise<Storage> {
  if (!_nativeStorage) {
    const SecureStore = await import('expo-secure-store');
    _nativeStorage = {
      getItem: (key) => SecureStore.getItemAsync(key),
      setItem: (key, value) => SecureStore.setItemAsync(key, value),
      removeItem: (key) => SecureStore.deleteItemAsync(key),
    };
  }
  return _nativeStorage;
}

export const storage: Storage = Platform.OS === 'web'
  ? webStorage
  : {
      getItem: async (key) => (await getNativeStorage()).getItem(key),
      setItem: async (key, value) => (await getNativeStorage()).setItem(key, value),
      removeItem: async (key) => (await getNativeStorage()).removeItem(key),
    };
