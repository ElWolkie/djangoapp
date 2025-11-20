// app.config.ts
import 'dotenv/config';

export default ({ config }: { config: any }) => {
  const APP_NAME = process.env.EXPO_APP_NAME ?? 'Mini SACFU';
  const SLUG = process.env.EXPO_SLUG ?? 'minisacfu';
  const SDK_VERSION = process.env.EXPO_SDK_VERSION ?? '54.0.0';
  const API_BASE = process.env.EXPO_PUBLIC_API_BASE_URL ?? process.env.API_BASE_URL_PROD ?? 'https://djangoapp-6wxv.onrender.com';
  const EAS_PROJECT_ID = process.env.EAS_PROJECT_ID ?? 'a0212456-d171-49be-97a5-e6400ce43427';
  const ANDROID_PACKAGE = process.env.EXPO_ANDROID_PACKAGE ?? 'com.shootspire2.minisacfu';
  const IOS_BUNDLE_ID = process.env.EXPO_IOS_BUNDLE_IDENTIFIER ?? 'com.shootspire2.minisacfu';

  return {
    expo: {
      owner: 'shootspire-2',

      name: APP_NAME,
      slug: SLUG,
      version: '1.0.0',
      sdkVersion: SDK_VERSION,
      runtimeVersion: '1.0.0',
      scheme: 'minisacfu',
      updates: {
        enabled: false
      },
      web: {
        favicon: './assets/appfu.png'
      },
      android: {
        package: ANDROID_PACKAGE
      },
      ios: {
        bundleIdentifier: IOS_BUNDLE_ID
      },
      extra: {
        // clave "apiBaseUrl" en camelCase para un acceso JS más natural
        apiBaseUrl: API_BASE,
        eas: {
          projectId: EAS_PROJECT_ID
        }
      }
    }
  };
};
