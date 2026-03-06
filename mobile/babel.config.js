module.exports = function (api) {
  api.cache.using(() => process.env.NODE_ENV);
  const isTest = process.env.NODE_ENV === 'test';
  return {
    presets: [['babel-preset-expo', { reanimated: false }]],
    plugins: isTest ? [] : ['react-native-reanimated/plugin'],
  };
};
