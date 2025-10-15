// app.config.ts
import 'dotenv/config';

export default ({ config }: { config: any }) => {
  const APP_NAME = process.env.EXPO_APP_NAME ?? 'Mini SACFU';
  const SLUG = process.env.EXPO_SLUG ?? 'minisacfu';
  const SDK_VERSION = process.env.EXPO_SDK_VERSION ?? '54.0.0';
  const API_BASE = process.env.EXPO_PUBLIC_API_BASE_URL ?? 'https://djangoapp-6wxv.onrender.com';
  const EAS_PROJECT_ID = process.env.EAS_PROJECT_ID ?? 'a0212456-d171-49be-97a5-e6400ce43427';
  const ANDROID_PACKAGE = process.env.EXPO_ANDROID_PACKAGE ?? 'com.shootspire2.minisacfu'; // <-- cambia esto si quieres
  const IOS_BUNDLE_ID = process.env.EXPO_IOS_BUNDLE_IDENTIFIER ?? 'com.shootspire2.minisacfu'; // <-- cambia esto si quieres

  return {
    expo: {
      name: APP_NAME,
      slug: SLUG,
      version: '1.0.0',
      sdkVersion: SDK_VERSION,
      // Runtime version: debe ser un string fijo cuando usas workflow "bare" / prebuild.
      runtimeVersion: '1.0.0',
      scheme: "minisacfu", // Agrega esto

      // Control de actualizaciones OTA (opcional)
      updates: {
        enabled: false // ← Agrega esta línea
      },

      // Web config (mantener)
      web: {
        favicon: './assets/appfu.png'
      },

      // Identificadores nativos IMPORTANTES — necesarios para prebuild / EAS
      android: {
        package: ANDROID_PACKAGE
      },
      ios: {
        bundleIdentifier: IOS_BUNDLE_ID
      },

      // Extras (API base + eas project id)
      extra: {
        API_BASE_URL: API_BASE,
        eas: {
          projectId: EAS_PROJECT_ID
        }
      }

      // NOTA: no incluimos icon/splash/otras propiedades nativas porque tienes carpetas android/ios presentes.
    }
  };
};
