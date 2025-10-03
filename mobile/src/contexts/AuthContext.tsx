// src/contexts/AuthContext.tsx
import React, { createContext, useCallback, useEffect, useState } from 'react';
import AsyncStorage from '@react-native-async-storage/async-storage';
import api from '../api/api';
import { storeTokens, getTokens, clearTokens } from '../api/auth';

type UserPayload = {
  displayName?: string | null;
  cedula?: string | null;
  [k: string]: any;
};

type AuthContextType = {
  isLoading: boolean;
  isAuthenticated: boolean;
  user: UserPayload | null;
  accessToken: string | null;
  loginWithTokens: (access: string, refresh?: string | null, user?: any | null) => Promise<void>;
  logout: () => Promise<void>;
  setUserFromApi?: (userObj: any) => void;
};

export const AuthContext = createContext<AuthContextType>({
  isLoading: true,
  isAuthenticated: false,
  user: null,
  accessToken: null,
  loginWithTokens: async () => {},
  logout: async () => {},
});

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [isLoading, setIsLoading] = useState(true);
  const [accessToken, setAccessToken] = useState<string | null>(null);
  const [user, setUser] = useState<UserPayload | null>(null);

  useEffect(() => {
    (async () => {
      try {
        const stored = await AsyncStorage.getItem('myapp-tokens');
        if (stored) {
          const parsed = JSON.parse(stored);
          const at = parsed?.access ?? null;
          const u = parsed?.user ?? null;
          if (at) {
            setAccessToken(at);
            api.defaults.headers.common['Authorization'] = `Bearer ${at}`;
          }
          if (u) setUser(u);
        }
      } catch (e) {
        console.warn('AuthProvider load error', e);
      } finally {
        setIsLoading(false);
      }
    })();
  }, []);

  const loginWithTokens = useCallback(async (access: string, refresh?: string | null, userObj?: any | null) => {
    try {
      // guarda usando tu helper
      await storeTokens(access, refresh ?? null, userObj ?? null);
      setAccessToken(access);
      api.defaults.headers.common['Authorization'] = `Bearer ${access}`;
      if (userObj) setUser(userObj);
    } catch (e) {
      console.warn('loginWithTokens error', e);
      throw e;
    }
  }, []);

  const logout = useCallback(async () => {
    try {
      await clearTokens();
      await AsyncStorage.removeItem('myapp-user'); // por si lo usabas
      setAccessToken(null);
      setUser(null);
      delete api.defaults.headers.common['Authorization'];
    } catch (e) {
      console.warn('logout error', e);
    }
  }, []);

  const setUserFromApi = useCallback((u: any) => {
    setUser(u);
    (async () => {
      try {
        const tk = await getTokens();
        const toSave = { access: tk?.access ?? null, refresh: tk?.refresh ?? null, user: u ?? null };
        await AsyncStorage.setItem('myapp-tokens', JSON.stringify(toSave));
      } catch (e) { /* noop */ }
    })();
  }, []);

  return (
    <AuthContext.Provider value={{
      isLoading,
      isAuthenticated: !!accessToken,
      user,
      accessToken,
      loginWithTokens,
      logout,
      setUserFromApi,
    }}>
      {children}
    </AuthContext.Provider>
  );
};
