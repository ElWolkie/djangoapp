// src/api.ts
import axios from 'axios';
import AsyncStorage from '@react-native-async-storage/async-storage';
import Config from 'react-native-config';
import Constants from 'expo-constants';
import { NativeModules, Platform } from 'react-native';

const EMULATOR_ANDROID = 'http://10.0.2.2:8000';
const LOCALHOST = 'http://127.0.0.1:8000';
const DEFAULT_PORT = 8000;

function fromExpoExtra(): string | null {
  try {
    const extra = (Constants as any)?.manifest?.extra;
    if (extra && extra.API_BASE_URL) return String(extra.API_BASE_URL);
  } catch (e) {}
  return null;
}

function fromReactNativeConfig(): string | null {
  try {
    if (Config && typeof (Config as any).API_BASE_URL === 'string' && (Config as any).API_BASE_URL.length > 0) {
      return (Config as any).API_BASE_URL;
    }
  } catch (e) {}
  return null;
}

function fromDebuggerHost(): string | null {
  try {
    const dbg = (Constants as any)?.manifest?.debuggerHost;
    if (dbg) {
      const host = String(dbg).split(':')[0];
      return `http://${host}:${DEFAULT_PORT}`;
    }
  } catch (e) {}
  return null;
}

function fromSourceCodeScriptURL(): string | null {
  try {
    const scriptURL = (NativeModules as any)?.SourceCode?.scriptURL;
    if (scriptURL && typeof scriptURL === 'string') {
      // scriptURL ejemplo: "http://192.168.1.5:19000/index.bundle?platform=android&..."
      const m = scriptURL.match(/^https?:\/\/([^/:]+)(?::(\d+))?/);
      if (m) {
        const host = m[1];
        const port = m[2] || DEFAULT_PORT;
        return `http://${host}:${port}`;
      }
    }
  } catch (e) {}
  return null;
}

function detectBaseUrl(): string {
  // 1) Expo app.config.js extra (recomendado para Expo-managed)
  const expo = fromExpoExtra();
  if (expo) {
    console.log('[api] usando API_BASE_URL desde Constants.manifest.extra ->', expo);
    return expo;
  }

  // 2) react-native-config (si estás en bare RN y has hecho rebuild)
  const rnc = fromReactNativeConfig();
  if (rnc) {
    console.log('[api] usando API_BASE_URL desde react-native-config ->', rnc);
    return rnc;
  }

  // 3) debuggerHost (Expo dev / Metro) -> 192.168.x.x:port
  const dbg = fromDebuggerHost();
  if (dbg) {
    console.log('[api] detectado via debuggerHost ->', dbg);
    return dbg;
  }

  // 4) NativeModules.SourceCode.scriptURL (RN packager)
  const src = fromSourceCodeScriptURL();
  if (src) {
    console.log('[api] detectado via SourceCode.scriptURL ->', src);
    return src;
  }

  // 5) Si Android dispositivo físico, 10.0.2.2 solo para emulador Android
  if (Platform.OS === 'android') {
    console.log('[api] fallback emulador android ->', EMULATOR_ANDROID);
    return EMULATOR_ANDROID;
  }

  // 6) fallback a localhost
  console.log('[api] fallback localhost ->', LOCALHOST);
  return LOCALHOST;
}

const BASE_URL = detectBaseUrl();

console.log('[api] BASE_URL final ->', BASE_URL);

const api = axios.create({
  baseURL: BASE_URL,
  timeout: 15000,
});

api.interceptors.request.use(async (config) => {
  try {
    const creds = await AsyncStorage.getItem('myapp-tokens');
    if (creds) {
      const parsed = JSON.parse(creds);
      const access = parsed?.access;
      if (access) {
        config.headers = config.headers || {};
        config.headers.Authorization = `Bearer ${access}`;
      }
    }
  } catch (e) {
    console.warn('[api] error leyendo myapp-tokens', e);
  }
  return config;
}, (err) => Promise.reject(err));

export default api;
