// Mock Expo winter runtime globals to prevent ESM import errors in Jest
(globalThis as any).__ExpoImportMetaRegistry = {};

// structuredClone is native in Node 17+ but expo tries to polyfill it via ESM package
if (typeof globalThis.structuredClone === 'undefined') {
  (globalThis as any).structuredClone = (val: unknown) => JSON.parse(JSON.stringify(val));
}
