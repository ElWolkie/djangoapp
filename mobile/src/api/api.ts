import axios, { AxiosError, AxiosRequestConfig } from 'axios';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { Platform } from 'react-native';

const PRODUCTION_URL = 'https://djangoapp-6wxv.onrender.com';
const EMULATOR_ANDROID = 'http://10.0.2.2:8000';
const LOCALHOST = 'http://127.0.0.1:8000';

function detectBaseUrl(): string {
  if (!__DEV__) {
    console.log('[api] Entorno de Producción ->', PRODUCTION_URL);
    return PRODUCTION_URL;
  }
  if (Platform.OS === 'web') {
    console.log('[api] Web (Dev) -> Usando URL de producción para pruebas ->', PRODUCTION_URL);
    return PRODUCTION_URL;
  }
  if (Platform.OS === 'android') {
    console.log('[api] Android (Dev) -> Usando IP de emulador ->', EMULATOR_ANDROID);
    return EMULATOR_ANDROID;
  }
  console.log('[api] Dev -> Fallback a localhost ->', LOCALHOST);
  return LOCALHOST;
}

const BASE_URL = detectBaseUrl();
console.log('[api] BASE_URL final ->', BASE_URL);

const api = axios.create({
  baseURL: BASE_URL,
  timeout: 15000,
  headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' },
});

export const STORAGE_KEY = 'myapp-tokens';
const REFRESH_ENDPOINT = '/api/token/refresh/';

// Esta función ahora es INTERNA a este archivo.
async function getStoredTokens(): Promise<{ access?: string | null; refresh?: string | null } | null> {
  try {
    const raw = await AsyncStorage.getItem(STORAGE_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch (e) {
    console.warn('[api] Error leyendo tokens de AsyncStorage', e);
    return null;
  }
}

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

api.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const originalRequest = error.config as AxiosRequestConfig & { _retry?: boolean };

    if (error.response?.status !== 401 || !originalRequest || originalRequest._retry) {
      console.error(`❌ ${error.response?.status || 'Network Error'} en ${originalRequest?.url}:`, error.message);
      return Promise.reject(error);
    }

    originalRequest._retry = true;
    console.log('[api] Token expirado. Intentando refrescar...');

    try {
      const tokens = await getStoredTokens();
      if (!tokens?.refresh) {
        console.log('[api] No hay refresh token. Deslogueando.');
        return Promise.reject(error);
      }
      
      const { data } = await axios.post(`${BASE_URL}${REFRESH_ENDPOINT}`, { refresh: tokens.refresh });
      const newAccess = data.access;
      const newRefresh = data.refresh || tokens.refresh;
      
      const stored = await getStoredTokens();
      await AsyncStorage.setItem(STORAGE_KEY, JSON.stringify({ ...stored, access: newAccess, refresh: newRefresh }));
      
      api.defaults.headers.common['Authorization'] = `Bearer ${newAccess}`;
      if (originalRequest.headers) {
        originalRequest.headers.Authorization = `Bearer ${newAccess}`;
      }
      
      console.log('[api] Token refrescado. Reintentando petición original.');
      return api(originalRequest);

    } catch (refreshError) {
      console.error('[api] Falló el refresco de token.', refreshError);
      await AsyncStorage.removeItem(STORAGE_KEY);
      return Promise.reject(error);
    }
  }
);

export default api;

