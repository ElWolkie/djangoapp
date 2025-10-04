import axios, { AxiosError, AxiosRequestConfig } from 'axios';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { Platform } from 'react-native';

const PRODUCTION_URL = 'https://djangoapp-6wxv.onrender.com';
const EMULATOR_ANDROID = 'http://10.0.2.2:8000';
const LOCALHOST = 'http://127.0.0.1:8000';

function detectBaseUrl(): string {
  // Siempre usar producción para evitar problemas de CORS
  return PRODUCTION_URL;
}

const BASE_URL = detectBaseUrl();
console.log('[api] URL final ->', BASE_URL);

const api = axios.create({
  baseURL: BASE_URL,
  timeout: 20000,
  headers: { 
    'Content-Type': 'application/json', 
    'Accept': 'application/json',
  },
});

export const STORAGE_KEY = 'myapp-tokens';

async function getStoredTokens() {
  try {
    const raw = await AsyncStorage.getItem(STORAGE_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch (e) {
    console.warn('[api] Error leyendo tokens', e);
    return null;
  }
}

// Interceptor MUY SIMPLE sin headers personalizados
api.interceptors.request.use(
  async (config) => {
    const tokens = await getStoredTokens();
    if (tokens?.access) {
      config.headers.Authorization = `Bearer ${tokens.access}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

export default api;