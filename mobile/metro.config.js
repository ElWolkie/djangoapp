// metro.config.js — Configuración oficial compatible con Expo y EAS Build
const { getDefaultConfig } = require('expo/metro-config');

/**
 * Configuración Metro para Expo
 * https://docs.expo.dev/guides/customizing-metro/
 *
 * Esta versión garantiza compatibilidad con EAS Build
 * y evita errores como "Serializer did not return expected format".
 */
const projectRoot = __dirname;
const config = getDefaultConfig(projectRoot);

// ✅ Opciones de transformación recomendadas
config.transformer = {
  ...config.transformer,
  getTransformOptions: async () => ({
    transform: {
      experimentalImportSupport: false,
      inlineRequires: true,
    },
  }),
  // Si usas SVGs con react-native-svg-transformer, descomenta esta línea:
  // babelTransformerPath: require.resolve('react-native-svg-transformer'),
};

// ✅ Resolver configurado correctamente
config.resolver = {
  ...config.resolver,
  // Si no usas transformer SVG, puedes tratar los .svg como assets
  assetExts: config.resolver.assetExts.filter(ext => ext !== 'svg'),
  sourceExts: [...config.resolver.sourceExts, 'svg'],
};

// ✅ Exportar la configuración final
module.exports = config;
