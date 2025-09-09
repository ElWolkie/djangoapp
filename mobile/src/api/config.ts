import Config from 'react-native-config';
import Constants from 'expo-constants';

const envUrl = Config.API_BASE_URL; // set via .env.development / .env
const prodEnvUrl = Config.API_BASE_URL_PROD; // optional, set via .env.production

const emulatorFallback = 'http://10.0.2.2:8000'; // Android emulator
const defaultLocal = 'http://127.0.0.1:8000';

export const API_BASE_URL = (() => {
  // 1) Prioriza la variable del .env (dev)
  if (envUrl) return envUrl;

  // 2) En modo produccion, toma la variable de prod si existe; si no, log y evita usar un enlace roto
  if (!__DEV__) {
    if (prodEnvUrl) return prodEnvUrl;
    // Si ya estás construyendo release sin backend, mejor fallar explícitamente:
    console.error('API_BASE_URL no está configurada para producción. Define API_BASE_URL_PROD en .env.production');
    // Opciones: lanzar excepción o devolver una URL segura (vacía) para que las llamadas fallen controladamente
    return ''; // o: throw new Error('No production API URL configured');
  }

  // 3) En desarrollo (dev) intenta deducir la IP desde Expo debuggerHost si corresponde
  try {
    const dbg = (Constants as any).manifest?.debuggerHost;
    if (dbg) {
      const host = dbg.split(':')[0];
      return `http://${host}:8000`;
    }
  } catch (e) {}

  // 4) Fallback para emuladores
  return emulatorFallback;
})();
