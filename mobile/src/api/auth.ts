import AsyncStorage from '@react-native-async-storage/async-storage';
// Importamos la instancia ya creada y configurada
import api, { STORAGE_KEY } from './api';

/**
 * Guarda tokens y datos de usuario, y actualiza la instancia de API.
 */
export const storeTokens = async (access: string, refresh: string | null = null, user: any | null = null): Promise<void> => {
  try {
    const payload = JSON.stringify({ access, refresh, user });
    await AsyncStorage.setItem(STORAGE_KEY, payload);
    // Actualiza el header por defecto para peticiones futuras en esta sesión
    api.defaults.headers.common['Authorization'] = `Bearer ${access}`;
    console.log('[auth] Tokens guardados y header de API actualizado.');
  } catch (e) {
    console.error('[auth] Error guardando tokens', e);
    throw e;
  }
};

/**
 * Limpia los tokens del almacenamiento y de la instancia de API.
 */
export const clearTokens = async (): Promise<void> => {
  try {
    await AsyncStorage.removeItem(STORAGE_KEY);
    // Elimina el header por defecto
    delete api.defaults.headers.common['Authorization'];
    console.log('[auth] Tokens limpiados.');
  } catch (e) {
    console.error('[auth] Error limpiando tokens', e);
    throw e;
  }
};

/**
 * Carga los tokens desde el almacenamiento a la instancia de API al iniciar la app.
 */
export const loadTokensToApi = async (): Promise<boolean> => {
  try {
    const raw = await AsyncStorage.getItem(STORAGE_KEY);
    if (raw) {
      const tokens = JSON.parse(raw);
      if (tokens.access) {
        api.defaults.headers.common['Authorization'] = `Bearer ${tokens.access}`;
        console.log('[auth] Tokens cargados en API al iniciar.');
        return true;
      }
    }
    return false;
  } catch (e) {
    console.warn('[auth] No se pudieron cargar tokens al iniciar.', e);
    return false;
  }
};
