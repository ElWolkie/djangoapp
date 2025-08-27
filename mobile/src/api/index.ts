// src/api/index.ts
import axios, { AxiosInstance, AxiosRequestConfig } from 'axios';
import { API_BASE_URL } from './config';
import { getTokens, storeTokens, clearTokens } from './auth';

interface RefreshResponse {
  access: string;
  refresh: string;
}

const api: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  timeout: 15_000,
});

// Interceptor request: añade Authorization si existe access token
api.interceptors.request.use(
  async (config: import('axios').InternalAxiosRequestConfig) => {
    try {
      const tokens = await getTokens();
      const access = tokens?.access;
      if (access) {
        if (!config.headers) {
          config.headers = new (require('axios').AxiosHeaders)();
        }
        (config.headers as any).Authorization = `Bearer ${access}`;
      }
    } catch (e) {
      // no impedimos la petición por un error de lectura
      // eslint-disable-next-line no-console
      console.error('request interceptor error', e);
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Interceptor response: refresca token si 401 y retry no hecho
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest: any = error.config;
    try {
      if (error.response?.status === 401 && !originalRequest?._retry) {
        originalRequest._retry = true;
        const tokens = await getTokens();
        const refresh = tokens?.refresh;
        if (refresh) {
          try {
            const resp = await axios.post<RefreshResponse>(`${API_BASE_URL}/api/token/refresh/`, {
              refresh,
            });
            const { access: newAccess, refresh: newRefresh } = resp.data;
            // guarda los nuevos tokens (mantén user si lo había)
            await storeTokens(newAccess, newRefresh, tokens?.user ?? null);
            // pone el header y reintenta
            if (originalRequest.headers) {
              originalRequest.headers.Authorization = `Bearer ${newAccess}`;
            } else {
              originalRequest.headers = { Authorization: `Bearer ${newAccess}` };
            }
            return api(originalRequest);
          } catch (refreshErr) {
            console.error('Refresh token failed', refreshErr);
            // limpiar tokens si refresh también falla
            try { await clearTokens(); } catch (e) { /* ignore */ }
            // opcional: redirigir al login desde aquí no es directo; maneja desde UI
          }
        }
      }
    } catch (e) {
      console.error('response interceptor error', e);
    }
    return Promise.reject(error);
  }
);

export default api;
