// src/contexts/AuthContext.tsx
import React, { createContext, useState, useEffect, useCallback } from 'react';
import { useNavigation } from '@react-navigation/native';
import { storeTokens, getTokens, clearTokens } from '../api/auth';
import api from '../api'; // por si necesitas llamar algo al montar
import { Alert } from 'react-native';

type AuthContextType = {
  token: string | null;
  user: any | null;
  loading: boolean;
  signIn: (tokens: { access: string; refresh?: string }, user?: any) => Promise<void>;
  signOut: () => Promise<void>;
};

export const AuthContext = createContext<AuthContextType>({
  token: null, user: null, loading: true,
  signIn: async () => {}, signOut: async () => {}
});

export const AuthProvider: React.FC<{children: React.ReactNode}> = ({ children }) => {
  const [token, setToken] = useState<string | null>(null);
  const [user, setUser] = useState<any | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    (async () => {
      try {
        const stored = await getTokens();
        if (stored?.access) setToken(stored.access);
        if (stored?.user) setUser(stored.user);
      } catch (e) {
        // console.warn(e);
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  const signIn = useCallback(async (tokens: { access: string; refresh?: string }, usr?: any) => {
    try {
      await storeTokens(tokens.access, tokens.refresh ?? null, usr ?? null);
      setToken(tokens.access);
      if (usr) setUser(usr);
    } catch (e) {
      console.error('signIn storeTokens error', e);
      throw e;
    }
  }, []);

  const signOut = useCallback(async () => {
    try {
      await clearTokens();
      setToken(null);
      setUser(null);
    } catch (e) {
      console.error('signOut clearTokens error', e);
    }
  }, []);

  return (
    <AuthContext.Provider value={{ token, user, loading, signIn, signOut }}>
      {loading ? null : children}
    </AuthContext.Provider>
  );
};
