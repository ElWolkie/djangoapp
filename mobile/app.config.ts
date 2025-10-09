// app.config.ts
import 'dotenv/config';
export default ({ config }: { config: any }) => {
  const APP_NAME = process.env.EXPO_APP_NAME ?? 'Mini SACFU';
  const SLUG = process.env.EXPO_SLUG ?? 'minisacfu';
  const SDK_VERSION = process.env.EXPO_SDK_VERSION ?? '54.0.0';
  const BUNDLE_ID = process.env.EXPO_IOS_BUNDLE_IDENTIFIER ?? 'com.edgar.minisacfu';
  const PACKAGE = process.env.EXPO_ANDROID_PACKAGE ?? 'com.edgar.minisacfu';
  const API_BASE = process.env.EXPO_PUBLIC_API_BASE_URL ?? 'https://djangoapp-6wxv.onrender.com';

  return {
    expo: {
      name: APP_NAME,
      slug: SLUG,
      version: '1.0.0',
      sdkVersion: SDK_VERSION,
      runtimeVersion: "1.0",
        updates: {
          fallbackToCacheTimeout: 0
        },
      orientation: 'portrait',
      icon: './assets/icon.png',
      userInterfaceStyle: 'light',
      // newArchEnabled: true, // DESCOMENTA solo si sabes que tus libs y RN lo soportan
      splash: {
        image: './assets/splash-icon.png',
        resizeMode: 'contain',
        backgroundColor: '#ffffff'
      },
      ios: {
        supportsTablet: true,
        bundleIdentifier: BUNDLE_ID,
        buildNumber: process.env.IOS_BUILD_NUMBER ?? '1'
      },
      android: {
        adaptiveIcon: { foregroundImage: './assets/adaptive-icon.png', backgroundColor: '#ffffff' },
        edgeToEdgeEnabled: true,
        package: PACKAGE,
        permissions: ['INTERNET','ACCESS_NETWORK_STATE'],
        versionCode: Number(process.env.ANDROID_VERSION_CODE ?? 1)
      },
      web: { favicon: './assets/favicon.png' },

      extra: {
        API_BASE_URL: API_BASE,
        eas: { projectId: 'a0212456-d171-49be-97a5-e6400ce43427' }
      },

      plugins: [
        [ 'expo-build-properties', { android: { usesCleartextTraffic: true, compileSdkVersion: 34, targetSdkVersion: 34, buildToolsVersion: '34.0.0' } } ]
      ]
    }

      };
};
