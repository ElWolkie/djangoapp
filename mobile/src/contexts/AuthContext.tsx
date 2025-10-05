// src/contexts/AuthContext.tsx
import React, { createContext, useCallback, useEffect, useState } from 'react';
import AsyncStorage from '@react-native-async-storage/async-storage';
import api from '../api/api';

// Definir un tipo más completo para el usuario
type UserPayload = {
  idPersona?: number;
  id?: number;
  cedula?: string;
  nombres?: string;
  apellidos?: string;
  email?: string;
  displayName?: string;
  [k: string]: any;
};

type AuthContextType = {
  isLoading: boolean;
  isAuthenticated: boolean;
  user: UserPayload | null;
  accessToken: string | null;
  loginWithTokens: (access: string, refresh?: string | null, user?: UserPayload | null) => Promise<void>;
  logout: () => Promise<void>;
  setUserFromApi?: (userObj: UserPayload) => void;
  // Agregar función para obtener datos del usuario basado en cédula
  fetchUserFromCedula: (cedula: string) => Promise<void>;
};

export const AuthContext = createContext<AuthContextType>({
  isLoading: true,
  isAuthenticated: false,
  user: null,
  accessToken: null,
  loginWithTokens: async () => {},
  logout: async () => {},
  fetchUserFromCedula: async () => {},
});

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [isLoading, setIsLoading] = useState(true);
  const [accessToken, setAccessToken] = useState<string | null>(null);
  const [user, setUser] = useState<UserPayload | null>(null);

  // Función para obtener tokens del almacenamiento
  const getTokens = useCallback(async () => {
    try {
      const stored = await AsyncStorage.getItem('myapp-tokens');
      return stored ? JSON.parse(stored) : null;
    } catch (error) {
      console.error('Error obteniendo tokens:', error);
      return null;
    }
  }, []);

  // Función para guardar tokens
  const storeTokens = useCallback(async (access: string, refresh: string | null, userData: UserPayload | null) => {
    try {
      const tokens = {
        access,
        refresh,
        user: userData
      };
      await AsyncStorage.setItem('myapp-tokens', JSON.stringify(tokens));
    } catch (error) {
      console.error('Error guardando tokens:', error);
    }
  }, []);

  // Función para limpiar tokens
  const clearTokens = useCallback(async () => {
    try {
      await AsyncStorage.removeItem('myapp-tokens');
    } catch (error) {
      console.error('Error limpiando tokens:', error);
    }
  }, []);

  // Función para obtener información del usuario basado en cédula (usando el endpoint que SÍ existe)
  const fetchUserFromCedula = useCallback(async (cedula: string) => {
    if (!accessToken) return;
    
    try {
      console.log('🔍 Obteniendo información del usuario por cédula:', cedula);
      const response = await api.get(`/api/obtener-persona-login/?cedula=${encodeURIComponent(cedula)}`);
      const userData = response.data;
      
      console.log('📋 Información de usuario recibida:', userData);
      
      if (userData && userData.idPersona) {
        const completeUser: UserPayload = {
          idPersona: userData.idPersona,
          cedula: userData.cedula || cedula,
          nombres: userData.nombres,
          apellidos: userData.apellidos,
          email: userData.email,
          displayName: userData.displayName || `${userData.nombres} ${userData.apellidos}`,
        };
        
        setUser(completeUser);
        
        // Actualizar en AsyncStorage
        const tokens = await getTokens();
        if (tokens) {
          await storeTokens(tokens.access, tokens.refresh, completeUser);
        }
      }
    } catch (error) {
      console.error('❌ Error obteniendo información del usuario por cédula:', error);
    }
  }, [accessToken, getTokens, storeTokens]);

  useEffect(() => {
    (async () => {
      try {
        const stored = await AsyncStorage.getItem('myapp-tokens');
        console.log('🔐 Tokens almacenados:', stored);
        
        if (stored) {
          const parsed = JSON.parse(stored);
          const at = parsed?.access ?? null;
          const u = parsed?.user ?? null;
          
          if (at) {
            setAccessToken(at);
            api.defaults.headers.common['Authorization'] = `Bearer ${at}`;
          }
          
          if (u) {
            setUser(u);
            console.log('👤 Usuario cargado desde storage:', u);
            
            // Si tenemos cédula pero no idPersona, intentar obtener información completa
            if (u.cedula && !u.idPersona && at) {
              console.log('🔄 Tenemos cédula pero no idPersona, obteniendo información completa...');
              await fetchUserFromCedula(u.cedula);
            }
          }
        }
      } catch (e) {
        console.warn('AuthProvider load error', e);
      } finally {
        setIsLoading(false);
      }
    })();
  }, [fetchUserFromCedula]);

  const loginWithTokens = useCallback(async (
    access: string, 
    refresh?: string | null, 
    userObj?: UserPayload | null
  ) => {
    try {
      // Guardar tokens iniciales
      await storeTokens(access, refresh ?? null, userObj ?? null);
      setAccessToken(access);
      api.defaults.headers.common['Authorization'] = `Bearer ${access}`;
      
      if (userObj) {
        setUser(userObj);
        console.log('👤 Usuario establecido en login:', userObj);
        
        // Si el usuario tiene cédula pero no idPersona, obtener información completa
        if (userObj.cedula && !userObj.idPersona) {
          console.log('🔄 Usuario con cédula pero sin idPersona, obteniendo información completa...');
          setTimeout(() => fetchUserFromCedula(userObj.cedula!), 1000);
        }
      } else {
        // Si no viene userObj, intentar obtenerlo del token o de otra manera
        console.log('⚠️ No se recibió userObj en el login');
      }
    } catch (e) {
      console.warn('loginWithTokens error', e);
      throw e;
    }
  }, [storeTokens, fetchUserFromCedula]);

  const logout = useCallback(async () => {
    try {
      await clearTokens();
      setAccessToken(null);
      setUser(null);
      delete api.defaults.headers.common['Authorization'];
      console.log('👋 Logout completado');
    } catch (e) {
      console.warn('logout error', e);
    }
  }, [clearTokens]);

  const setUserFromApi = useCallback((u: UserPayload) => {
    console.log('👤 Actualizando usuario desde API:', u);
    setUser(u);
    (async () => {
      try {
        const tokens = await getTokens();
        if (tokens) {
          await storeTokens(tokens.access, tokens.refresh, u);
        }
      } catch (e) { 
        console.warn('Error guardando usuario actualizado', e);
      }
    })();
  }, [getTokens, storeTokens]);

  return (
    <AuthContext.Provider value={{
      isLoading,
      isAuthenticated: !!accessToken,
      user,
      accessToken,
      loginWithTokens,
      logout,
      setUserFromApi,
      fetchUserFromCedula,
    }}>
      {children}
    </AuthContext.Provider>
  );
};