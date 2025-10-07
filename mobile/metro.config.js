// metro.config.js - VERSIÓN SIMPLIFICADA Y FUNCIONAL
const {getDefaultConfig, mergeConfig} = require('@react-native/metro-config');

/**
 * Metro configuration for React Native
 * https://facebook.github.io/metro/docs/configuration
 *
 * @type {import('metro-config').MetroConfig}
 */
const config = {
  transformer: {
    getTransformOptions: async () => ({
      transform: {
        experimentalImportSupport: false,
        inlineRequires: true,
      },
    }),
    // ELIMINAMOS esta línea: babelTransformerPath: require.resolve('react-native-svg-transformer'),
  },
  resolver: {
    assetExts: [
      'bmp', 'gif', 'jpg', 'jpeg', 'png', 'psd', 'svg', 'webp',
      'm4v', 'mov', 'mp4', 'mpeg', 'mpg', 'webm',
      'aac', 'aiff', 'caf', 'm4a', 'mp3', 'wav',
      'html', 'pdf', 'yaml', 'yml', 'json',
      'otf', 'ttf',
    ],
    sourceExts: ['js', 'jsx', 'ts', 'tsx', 'json'],
  },
};

module.exports = mergeConfig(getDefaultConfig(__dirname), config);