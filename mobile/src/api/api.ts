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
const REFRESH_ENDPOINT = '/api/token/refresh/';

export const getStoredTokens = async (): Promise<{ access?: string | null; refresh?: string | null } | null> => {
  try {
    const raw = await AsyncStorage.getItem(STORAGE_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch (e) {
    console.warn('[api] Error leyendo tokens de AsyncStorage', e);
    return null;
  }
};

export const clearTokens = async (): Promise<void> => {
  try {
    await AsyncStorage.removeItem(STORAGE_KEY);
    delete api.defaults.headers.common['Authorization'];
    console.log('[api] Tokens limpiados.');
  } catch (e) {
    console.error('[api] Error limpiando tokens', e);
    throw e;
  }
};

// Interceptor de request - SIMPLE
api.interceptors.request.use(
  async (config) => {
    // Evitar agregar Authorization a endpoints públicos
    const publicEndpoints = ['/api/token/', '/api/token/refresh/', '/api/verificar-cedula/', '/api/obtener-persona-login/'];
    const isPublic = publicEndpoints.some(endpoint => config.url?.includes(endpoint));
    
    if (!isPublic) {
      const tokens = await getStoredTokens();
      if (tokens?.access) {
        config.headers.Authorization = `Bearer ${tokens.access}`;
      }
    }
    
    return config;
  },
  (error) => Promise.reject(error)
);

// Interceptor de response - MEJORADO
api.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const originalRequest = error.config as AxiosRequestConfig & { _retry?: boolean };

    // Si es error 401 y no es una petición de refresh ni ya se reintentó
    if (error.response?.status === 401 && 
        !originalRequest.url?.includes(REFRESH_ENDPOINT) && 
        originalRequest && 
        !originalRequest._retry) {
      
      originalRequest._retry = true;
      console.log('[api] Token expirado. Intentando refrescar...');

      try {
        const tokens = await getStoredTokens();
        
        if (!tokens?.refresh) {
          console.log('[api] No hay refresh token disponible');
          await clearTokens();
          // Podrías redirigir al login aquí si es necesario
          return Promise.reject(error);
        }

        console.log('[api] Refrescando token con:', tokens.refresh.substring(0, 20) + '...');
        
        // Hacer refresh del token
        const refreshResponse = await axios.post(
          `${BASE_URL}${REFRESH_ENDPOINT}`, 
          { refresh: tokens.refresh },
          {
            headers: {
              'Content-Type': 'application/json',
            },
            timeout: 10000,
          }
        );

        const newAccess = refreshResponse.data.access;
        const newRefresh = refreshResponse.data.refresh || tokens.refresh; // Usar el nuevo refresh si viene, sino mantener el anterior

        console.log('[api] Token refrescado exitosamente');

        // Guardar los nuevos tokens
        const newTokens = {
          ...tokens,
          access: newAccess,
          refresh: newRefresh
        };
        
        await AsyncStorage.setItem(STORAGE_KEY, JSON.stringify(newTokens));

        // Actualizar el header de autorización
        api.defaults.headers.common['Authorization'] = `Bearer ${newAccess}`;
        if (originalRequest.headers) {
          originalRequest.headers.Authorization = `Bearer ${newAccess}`;
        }

        console.log('[api] Reintentando petición original...');
        return api(originalRequest);

      } catch (refreshError: any) {
        console.error('[api] ❌ Error refrescando token:', refreshError.response?.data || refreshError.message);
        
        // Si falla el refresh, limpiar tokens y forzar logout
        await clearTokens();
        
        // Mostrar alerta al usuario
        if (Platform.OS === 'web') {
          alert('Tu sesión ha expirado. Por favor, inicia sesión nuevamente.');
        }
        
        return Promise.reject(refreshError);
      }
    }

    // Para otros errores, simplemente rechazar
    if (error.response?.status === 401) {
      console.error('[api] ❌ Error 401 - No autorizado');
      await clearTokens();
    }

    console.error(`❌ ${error.response?.status || 'Network Error'} en ${originalRequest?.url}:`, error.message);
    return Promise.reject(error);
  }
);

export default api;