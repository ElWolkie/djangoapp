import { Platform } from 'react-native';
import Config from 'react-native-config';

const DEV_URL = 'http://192.168.250.5:8000';
const PROD_URL = 'https://djangoapp-6wxv.onrender.com';

export const API_BASE_URL = Config.API_BASE_URL
  ? Config.API_BASE_URL
  : __DEV__
    ? DEV_URL
    : PROD_URL;