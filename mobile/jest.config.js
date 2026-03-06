module.exports = {
  preset: 'jest-expo',
  moduleNameMapper: {
    'react-native-reanimated': '<rootDir>/node_modules/react-native-reanimated/mock',
    '^expo-secure-store$': '<rootDir>/__mocks__/expo-secure-store.ts',
    '^expo-av$': '<rootDir>/__mocks__/expo-av.ts',
    '^@ungap/structured-clone$': '<rootDir>/__mocks__/structured-clone.ts',
  },
  transformIgnorePatterns: [
    'node_modules/(?!((jest-)?react-native|@react-native(-community)?)|expo(nent)?|@expo(nent)?/.*|@expo-google-fonts/.*|react-navigation|@react-navigation/.*|@unimodules/.*|unimodules|sentry-expo|native-base|react-native-svg)',
  ],
  collectCoverageFrom: [
    'src/**/*.{ts,tsx}',
    'app/**/*.{ts,tsx}',
    '!**/__tests__/**',
    '!**/node_modules/**',
  ],
  coverageReporters: ['text', 'lcov', 'html'],
  setupFiles: ['<rootDir>/jest.setup.ts'],
};
