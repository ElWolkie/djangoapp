// src/hooks/useAuth.ts
import { useState, useCallback } from 'react';
// Update the import path below if your api file is located elsewhere
import api from '../api/api';
import { storeTokens, clearTokens } from '../api/auth';

export const useAuth = () => {
  const [token, setToken] = useState<string | null>(null);

  const login = useCallback(async (idPersona: number, password: string) => {
    const { data } = await api.post('/api/token/', { idPersona, password });
    await storeTokens(data.access, data.refresh);
    setToken(data.access);
  }, []);

  const logout = useCallback(async () => {
    await clearTokens();
    setToken(null);
  }, []);

  return { token, login, logout };
};
