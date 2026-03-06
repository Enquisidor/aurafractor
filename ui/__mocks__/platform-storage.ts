/** In-memory platform storage mock for Jest */
const store = new Map<string, string>();

export const storage = {
  getItem: (key: string) => Promise.resolve(store.get(key) ?? null),
  setItem: (key: string, value: string) => { store.set(key, value); return Promise.resolve(); },
  removeItem: (key: string) => { store.delete(key); return Promise.resolve(); },
  __clear: () => store.clear(),
};
