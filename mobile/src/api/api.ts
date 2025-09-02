// src/api.ts
import axios from 'axios';
import AsyncStorage from '@react-native-async-storage/async-storage';

const BASE_URL = 'http://192.168.250.5:8000'; // ajusta a tu backend

const api = axios.create({
  baseURL: BASE_URL,
  timeout: 15000,
});

api.interceptors.request.use(async (config) => {
  try {
    const creds = await AsyncStorage.getItem('myapp-tokens');
    if (creds) {
      const { access } = JSON.parse(creds);
      if (access) {
        config.headers = config.headers || {};
        config.headers.Authorization = `Bearer ${access}`;
      }
    }
  } catch (e) {
    // noop
  }
  return config;
}, (err) => Promise.reject(err));

export default api;
