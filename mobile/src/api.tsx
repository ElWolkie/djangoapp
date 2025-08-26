// src/api/api.ts
import axios, { AxiosInstance, AxiosRequestConfig, AxiosResponse } from 'axios';
import { API_BASE_URL } from './config';
import { getTokens, storeTokens } from './auth';

interface RefreshResponse {
  access: string;
  refresh: string;
}

const api: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  timeout: 10_000,
});

api.interceptors.request.use(
  async (config) => {
    const tokens = await getTokens();
    if (tokens?.access && config.headers) {
      config.headers.Authorization = `Bearer ${tokens.access}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

api.interceptors.response.use(
  (response: AxiosResponse) => response,
  async (error) => {
    const originalRequest = error.config;
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;
      const tokens = await getTokens();
      if (tokens?.refresh) {
        try {
          const { data } = await axios.post<RefreshResponse>(
            `${API_BASE_URL}/api/token/refresh/`,
            { refresh: tokens.refresh }
          );
          // Guarda los nuevos tokens
          await storeTokens(data.access, data.refresh);
          // Reintenta la petición original con el nuevo access token
          if (originalRequest.headers) {
            originalRequest.headers.Authorization = `Bearer ${data.access}`;
          }
          return api(originalRequest);
        } catch (refreshError) {
          console.error('Error refreshing token:', refreshError);
        }
      }
    }
    return Promise.reject(error);
  }
);

export default api;
