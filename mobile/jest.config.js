module.exports = {
  preset: 'jest-expo',
  moduleNameMapper: {
    'react-native-reanimated': '<rootDir>/node_modules/react-native-reanimated/mock',
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
};
