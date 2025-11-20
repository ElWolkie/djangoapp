// src/api/api.ts (corregido)
import axios, { AxiosError, AxiosRequestConfig, AxiosResponse } from 'axios';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { Platform, Alert } from 'react-native';
import Constants from 'expo-constants';

// Si no instalas @types/node, esto evita error TS sobre "process"
declare const process: any;

const STORAGE_KEY = 'myapp-tokens';
const REFRESH_ENDPOINT = '/api/token/refresh/';

// Determinar base URL: priorizar expoConfig.extra (definido en app.config.ts), luego env, luego fallback
const expoExtra = (Constants.expoConfig && (Constants.expoConfig as any).extra) || {};
const PRODUCTION_URL = expoExtra.apiBaseUrl || process?.env?.EXPO_PUBLIC_API_BASE_URL || 'https://djangoapp-6wxv.onrender.com';
const EMULATOR_ANDROID = 'http://10.0.2.2:8000';
const LOCALHOST = 'http://127.0.0.1:8000';

function detectBaseUrl(): string {
  // Si en algún momento quieres detectar emuladores:
  // if (__DEV__ && Platform.OS === 'android') return EMULATOR_ANDROID;
  // Pero para producción, forzamos la URL pública (Render).
  return PRODUCTION_URL;
}

const BASE_URL = detectBaseUrl();
console.log('[api] URL final ->', BASE_URL);

const api = axios.create({
  baseURL: BASE_URL,
  timeout: 20000,
  headers: {
    'Content-Type': 'application/json',
    Accept: 'application/json',
  },
});

// ---- helpers de tokens ----
export type StoredTokens = { access?: string | null; refresh?: string | null } | null;

export const getStoredTokens = async (): Promise<StoredTokens> => {
  try {
    const raw = await AsyncStorage.getItem(STORAGE_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch (e) {
    console.warn('[api] Error leyendo tokens de AsyncStorage', e);
    return null;
  }
};

export const setStoredTokens = async (tokens: { access?: string | null; refresh?: string | null }) => {
  try {
    await AsyncStorage.setItem(STORAGE_KEY, JSON.stringify(tokens));
  } catch (e) {
    console.warn('[api] Error guardando tokens', e);
    throw e;
  }
};

export const clearTokens = async (): Promise<void> => {
  try {
    await AsyncStorage.removeItem(STORAGE_KEY);
    // eliminar header Authorization de axios por defecto
    delete (api.defaults.headers as any).common?.['Authorization'];
    console.log('[api] Tokens limpiados.');
  } catch (e) {
    console.error('[api] Error limpiando tokens', e);
    throw e;
  }
};

// Inicializar Authorization header al arrancar la app
export const initAuthHeader = async (): Promise<void> => {
  try {
    const tokens = await getStoredTokens();
    if (tokens?.access) {
      // setear en defaults (casteo para evitar error de tipos)
      (api.defaults.headers as any).common = {
        ...(api.defaults.headers as any).common,
        Authorization: `Bearer ${tokens.access}`,
      };
    }
  } catch (e) {
    console.warn('[api] initAuthHeader fallo', e);
  }
};

// ---- Gestión de refresh con cola (evita refreshes simultáneos) ----
let isRefreshing = false;
let failedQueue: Array<{
  resolve: (value?: AxiosResponse | PromiseLike<AxiosResponse> | undefined) => void;
  reject: (err: any) => void;
  config: AxiosRequestConfig;
}> = [];

const processQueue = (error: any, token: string | null = null) => {
  failedQueue.forEach(({ resolve, reject, config }) => {
    if (error) {
      reject(error);
    } else {
      if (token) {
        if (!config.headers) config.headers = {} as any;
        (config.headers as any).Authorization = `Bearer ${token}`;
      }
      resolve(api(config));
    }
  });
  failedQueue = [];
};

// Interceptor request: agregar Authorization salvo endpoints públicos
api.interceptors.request.use(
  async (config) => {
    const publicEndpoints = ['/api/token/', '/api/token/refresh/', '/api/verificar-cedula/', '/api/obtener-persona-login/'];
    const url = config.url ?? '';
    const isPublic = publicEndpoints.some(endpoint => url.includes(endpoint));
    if (!isPublic) {
      // Asegurar que headers exista y setear Authorization si es necesario
      if (!config.headers) config.headers = {} as any;
      if (!(config.headers as any).Authorization) {
        const tokens = await getStoredTokens();
        if (tokens?.access) {
          (config.headers as any).Authorization = `Bearer ${tokens.access}`;
        }
      }
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Interceptor response: refrescar token si 401
api.interceptors.response.use(
  (response) => response,
  async (err: AxiosError) => {
    const error = err;
    const originalRequest = (error.config ?? {}) as AxiosRequestConfig & { _retry?: boolean };

    const status = error.response?.status;

    // Si no hay status -> error de red (timeout, DNS, etc). Rechazar.
    if (!status) {
      console.error('[api] Network error o sin respuesta del servidor:', error.message);
      return Promise.reject(error);
    }

    // Manejo 401
    if (status === 401 && originalRequest && !originalRequest._retry && !(originalRequest.url ?? '').includes(REFRESH_ENDPOINT)) {
      // marcar reintento
      originalRequest._retry = true;

      if (isRefreshing) {
        // agregar a la cola y esperar
        return new Promise((resolve, reject) => {
          failedQueue.push({ resolve, reject, config: originalRequest });
        });
      }

      isRefreshing = true;
      console.log('[api] Token expirado. Intentando refrescar...');

      try {
        const tokens = await getStoredTokens();
        if (!tokens?.refresh) {
          console.log('[api] No hay refresh token disponible');
          await clearTokens();
          // podrías redirigir al login aquí si tu flujo lo necesita
          isRefreshing = false;
          processQueue(new Error('No refresh token'));
          return Promise.reject(error);
        }

        // Llamada de refresh con instancia axios (sin interceptors)
        const refreshResponse = await axios.post(
          `${BASE_URL}${REFRESH_ENDPOINT}`,
          { refresh: tokens.refresh },
          { headers: { 'Content-Type': 'application/json' }, timeout: 10000 }
        );

        const newAccess = refreshResponse.data.access;
        const newRefresh = refreshResponse.data.refresh || tokens.refresh;

        const newTokens = { ...tokens, access: newAccess, refresh: newRefresh };
        await setStoredTokens(newTokens);

        // actualizar header por defecto (casteo para evitar error de tipos)
        (api.defaults.headers as any).common = {
          ...(api.defaults.headers as any).common,
          Authorization: `Bearer ${newAccess}`,
        };

        isRefreshing = false;
        processQueue(null, newAccess);

        // actualizar headers en la petición original y reintentar
        if (!originalRequest.headers) originalRequest.headers = {} as any;
        (originalRequest.headers as any).Authorization = `Bearer ${newAccess}`;
        return api(originalRequest);
      } catch (refreshError: any) {
        console.error('[api] ❌ Error refrescando token:', refreshError?.response?.data ?? refreshError?.message ?? refreshError);
        isRefreshing = false;
        processQueue(refreshError, null);
        await clearTokens();

        // Notificar al usuario (mobile/web)
        if (Platform.OS === 'web') {
          alert('Tu sesión ha expirado. Por favor, inicia sesión nuevamente.');
        } else {
          Alert.alert('Sesión expirada', 'Tu sesión ha expirado. Por favor, inicia sesión nuevamente.');
        }

        return Promise.reject(refreshError);
      }
    }

    // Si llega aquí y es 401 (pero ya intentó refresh o es endpoint de refresh), limpiar tokens
    if (status === 401) {
      console.error('[api] 401 no manejado. Limpiando tokens.');
      await clearTokens();
    }

    console.error(`❌ ${status} en ${originalRequest?.url}:`, error.message);
    return Promise.reject(error);
  }
);

export default api;
export { STORAGE_KEY, REFRESH_ENDPOINT };
