// src/api/auth.ts
import AsyncStorage from '@react-native-async-storage/async-storage';

export interface Tokens {
  access: string;
  refresh: string;
}

const SERVICE_NAME = 'myapp-tokens';

/**
 * Guarda los tokens de acceso y refresh en AsyncStorage.
 */
export const storeTokens = async (access: string, refresh: string | null = null, user: any | null = null): Promise<void> => {
  try {
    const credentials: string = JSON.stringify({ access, refresh, user });
    await AsyncStorage.setItem(SERVICE_NAME, credentials);
  } catch (e) {
    console.error('Error guardando tokens en AsyncStorage', e);
    throw e;
  }
};

/**
 * Obtiene los tokens almacenados.
 * Devuelve null si no hay tokens.
 */
export const getTokens = async (): Promise<{ access: string | null; refresh: string | null; user?: any } | null> => {
  try {
    const creds = await AsyncStorage.getItem(SERVICE_NAME);
    if (!creds) return null;
    return JSON.parse(creds) as { access: string | null; refresh: string | null; user?: any };
  } catch (e) {
    console.error('Error leyendo tokens desde AsyncStorage', e);
    return null;
  }
};

/**
 * Elimina los tokens almacenados.
 */
export const clearTokens = async (): Promise<void> => {
  try {
    await AsyncStorage.removeItem(SERVICE_NAME);
  } catch (e) {
    console.error('Error limpiando tokens en AsyncStorage', e);
    throw e;
  }
};
