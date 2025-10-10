// app.config.ts
import 'dotenv/config';

export default ({ config }: { config: any }) => {
  const APP_NAME = process.env.EXPO_APP_NAME ?? 'Mini SACFU';
  const SLUG = process.env.EXPO_SLUG ?? 'minisacfu';
  const SDK_VERSION = process.env.EXPO_SDK_VERSION ?? '54.0.0';
  const API_BASE = process.env.EXPO_PUBLIC_API_BASE_URL ?? 'https://djangoapp-6wxv.onrender.com';
  const EAS_PROJECT_ID = process.env.EAS_PROJECT_ID ?? 'a0212456-d171-49be-97a5-e6400ce43427';

  return {
    expo: {
      name: APP_NAME,
      slug: SLUG,
      version: '1.0.0',
      sdkVersion: SDK_VERSION,
      // Runtime version: debe ser un string fijo cuando usas workflow "bare" / prebuild.
      runtimeVersion: '1.0.0',

      // Control de actualizaciones OTA (opcional, lo dejaste)
      updates: {
        fallbackToCacheTimeout: 0
      },

      // Mantén solo lo que no es configuración nativa
      web: {
        favicon: './assets/favicon.png'
      },

      // Extras (API base + eas project id)
      extra: {
        API_BASE_URL: API_BASE,
        eas: {
          projectId: EAS_PROJECT_ID
        }
      }

      // NOTA: no incluimos `icon`, `splash`, `ios`, `android`, `plugins`, `orientation`
      // porque tu proyecto ya contiene carpetas nativas (android/ ios/) y EAS no sincroniza
      // esas propiedades con archivos nativos cuando existen.
    }
  };
};
