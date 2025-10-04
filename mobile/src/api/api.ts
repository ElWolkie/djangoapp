import axios, { AxiosError, AxiosRequestConfig } from 'axios';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { Platform } from 'react-native';

const PRODUCTION_URL = 'https://djangoapp-6wxv.onrender.com';
const EMULATOR_ANDROID = 'http://10.0.2.2:8000';
const LOCALHOST = 'http://127.0.0.1:8000';

function detectBaseUrl(): string {
  if (!__DEV__) {
    console.log('[api] Producción ->', PRODUCTION_URL);
    return PRODUCTION_URL;
  }
  
  // Para web development, usa producción también
  if (Platform.OS === 'web') {
    console.log('[api] Web ->', PRODUCTION_URL);
    return PRODUCTION_URL;
  }
  
  // Para Android
  if (Platform.OS === 'android') {
    // Si estamos en emulador
    if (__DEV__) {
      console.log('[api] Android Dev ->', EMULATOR_ANDROID);
      return EMULATOR_ANDROID;
    }
  }
  
  // Para iOS
  if (Platform.OS === 'ios' && __DEV__) {
    console.log('[api] iOS Dev ->', LOCALHOST);
    return LOCALHOST;
  }
  
  console.log('[api] Fallback ->', PRODUCTION_URL);
  return PRODUCTION_URL;
}

const BASE_URL = detectBaseUrl();
console.log('[api] URL final ->', BASE_URL);

const api = axios.create({
  baseURL: BASE_URL,
  timeout: 20000, // Aumentar timeout
  headers: { 
    'Content-Type': 'application/json', 
    'Accept': 'application/json',
  },
  withCredentials: false, // Importante para APIs
});

export const STORAGE_KEY = 'myapp-tokens';
const REFRESH_ENDPOINT = '/api/token/refresh/';

async function getStoredTokens() {
  try {
    const raw = await AsyncStorage.getItem(STORAGE_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch (e) {
    console.warn('[api] Error leyendo tokens', e);
    return null;
  }
}

// Interceptor de request
api.interceptors.request.use(
  async (config) => {
    const tokens = await getStoredTokens();
    if (tokens?.access) {
      config.headers.Authorization = `Bearer ${tokens.access}`;
    }
    
    // Agregar header para identificar mobile
    config.headers['X-Requested-With'] = 'XMLHttpRequest';
    config.headers['X-Client-Type'] = 'react-native';
    
    return config;
  },
  (error) => Promise.reject(error)
);

// Interceptor de response
api.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const originalRequest = error.config as AxiosRequestConfig & { _retry?: boolean };

    if (error.response?.status === 400) {
      console.error('❌ Error 400 - Revisar payload:', error.response.data);
    }

    if (error.response?.status !== 401 || !originalRequest || originalRequest._retry) {
      console.error(`❌ ${error.response?.status || 'Network Error'} en ${originalRequest?.url}:`, error.message);
      return Promise.reject(error);
    }

    originalRequest._retry = true;
    console.log('[api] Token expirado. Refrescando...');

    try {
      const tokens = await getStoredTokens();
      if (!tokens?.refresh) {
        console.log('[api] No hay refresh token');
        return Promise.reject(error);
      }
      
      const { data } = await axios.post(`${BASE_URL}${REFRESH_ENDPOINT}`, { 
        refresh: tokens.refresh 
      });
      
      const newAccess = data.access;
      const newRefresh = data.refresh || tokens.refresh;
      
      await AsyncStorage.setItem(STORAGE_KEY, JSON.stringify({ 
        ...tokens, 
        access: newAccess, 
        refresh: newRefresh 
      }));
      
      if (originalRequest.headers) {
        originalRequest.headers.Authorization = `Bearer ${newAccess}`;
      }
      
      console.log('[api] Token refrescado');
      return api(originalRequest);

    } catch (refreshError) {
      console.error('[api] Error refrescando token:', refreshError);
      await AsyncStorage.removeItem(STORAGE_KEY);
      return Promise.reject(error);
    }
  }
);

export default api;