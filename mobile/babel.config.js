module.exports = function (api) {
  api.cache(false);
  const isTest = process.env.NODE_ENV === 'test';
  return {
    presets: ['babel-preset-expo'],
    plugins: isTest ? [] : ['react-native-reanimated/plugin'],
  };
};
