// src/utils/tokenManager.ts
import AsyncStorage from '@react-native-async-storage/async-storage';
import api, { getStoredTokens, clearTokens } from '../api/api';
import axios from 'axios';

const BASE_URL = 'https://djangoapp-6wxv.onrender.com';
const REFRESH_ENDPOINT = '/api/token/refresh/';
const STORAGE_KEY = 'myapp-tokens';

export const verifyAndRefreshToken = async (): Promise<boolean> => {
  try {
    const tokens = await getStoredTokens();
    
    if (!tokens?.access) {
      console.log('[tokenManager] No hay token de acceso');
      return false;
    }

    console.log('[tokenManager] Verificando token...');

    // Verificar si el token es válido haciendo una petición simple
    try {
      // Usar un endpoint que requiera autenticación pero sea liviano
      const response = await api.get('/api/inscripcion/', { 
        timeout: 10000,
        validateStatus: (status) => status < 500 // No considerar errores 5xx como token inválido
      });
      
      // Si llegamos aquí, el token es válido
      console.log('[tokenManager] ✅ Token válido - Status:', response.status);
      return true;

    } catch (error: any) {
      console.log('[tokenManager] Error en verificación:', error.response?.status || error.message);
      
      if (error.response?.status === 401) {
        console.log('[tokenManager] Token inválido (401), intentando refrescar...');
        
        if (!tokens.refresh) {
          console.log('[tokenManager] ❌ No hay refresh token disponible');
          await clearTokens();
          return false;
        }

        try {
          // Intentar refrescar el token
          console.log('[tokenManager] Refrescando token...');
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
          const newRefresh = refreshResponse.data.refresh || tokens.refresh;

          console.log('[tokenManager] ✅ Token refrescado exitosamente');

          // Guardar los nuevos tokens
          await AsyncStorage.setItem(STORAGE_KEY, JSON.stringify({
            ...tokens,
            access: newAccess,
            refresh: newRefresh
          }));

          // Actualizar el header de autorización
          api.defaults.headers.common['Authorization'] = `Bearer ${newAccess}`;
          
          console.log('[tokenManager] ✅ Tokens actualizados en API');
          return true;

        } catch (refreshError: any) {
          console.error('[tokenManager] ❌ Error refrescando token:', refreshError.response?.data || refreshError.message);
          
          // Si falla el refresh, limpiar tokens
          await clearTokens();
          return false;
        }
      }
      
      // Si no es error 401, podría ser otro problema de red, etc.
      console.error('[tokenManager] Error no manejado:', error);
      return false;
    }
  } catch (error) {
    console.error('[tokenManager] Error general verificando token:', error);
    await clearTokens();
    return false;
  }
};

// Función para verificar tokens al inicio de la app
export const initializeTokenSystem = async (): Promise<boolean> => {
  console.log('[tokenManager] 🔄 Inicializando sistema de tokens...');
  
  const tokens = await getStoredTokens();
  if (!tokens) {
    console.log('[tokenManager] No hay tokens guardados');
    return false;
  }

  console.log('[tokenManager] Tokens encontrados, verificando...');
  return await verifyAndRefreshToken();
};