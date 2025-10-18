// src/contexts/AuthContext.tsx
import React, { createContext, useCallback, useContext, useEffect, useState } from 'react';
import AsyncStorage from '@react-native-async-storage/async-storage';
import api from '../api/api';

// Definir un tipo más completo para el usuario
type UserPayload = {
  idPersona?: number;
  id?: number;
  cedula?: string;
  nombres?: string;
  apellidos?: string;
  correo?: string;
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

// Hook personalizado para usar el contexto
export const useAuth = () => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth debe ser usado dentro de un AuthProvider');
  }
  return context;
};

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [isLoading, setIsLoading] = useState(true);
  const [accessToken, setAccessToken] = useState<string | null>(null);
  const [user, setUser] = useState<UserPayload | null>(null);

  // Función para guardar tokens
  const storeTokens = useCallback(async (access: string, refresh: string | null, userData: UserPayload | null) => {
    try {
      const tokens = {
        access,
        refresh,
        user: userData
      };
      await AsyncStorage.setItem('myapp-tokens', JSON.stringify(tokens));
      console.log('✅ Tokens guardados en AsyncStorage');
    } catch (error) {
      console.error('❌ Error guardando tokens:', error);
    }
  }, []);

  // Función para limpiar tokens
  const clearTokens = useCallback(async () => {
    try {
      await AsyncStorage.removeItem('myapp-tokens');
      console.log('✅ Tokens eliminados de AsyncStorage');
    } catch (error) {
      console.error('❌ Error limpiando tokens:', error);
    }
  }, []);

  // Función para obtener tokens del almacenamiento
  const getTokens = useCallback(async () => {
    try {
      const stored = await AsyncStorage.getItem('myapp-tokens');
      return stored ? JSON.parse(stored) : null;
    } catch (error) {
      console.error('❌ Error obteniendo tokens:', error);
      return null;
    }
  }, []);

  const loginWithTokens = useCallback(async (
    access: string, 
    refresh?: string | null, 
    userObj?: UserPayload | null
  ) => {
    try {
      console.log('🔐 Iniciando loginWithTokens...');
      
      // Guardar tokens
      await storeTokens(access, refresh ?? null, userObj ?? null);
      setAccessToken(access);
      api.defaults.headers.common['Authorization'] = `Bearer ${access}`;
      
      if (userObj) {
        setUser(userObj);
        console.log('👤 Usuario establecido en login:', userObj);
      } else {
        console.log('⚠️ Login exitoso pero sin información de usuario');
      }
    } catch (e) {
      console.warn('❌ Error en loginWithTokens:', e);
      throw e;
    }
  }, [storeTokens]);

  const logout = useCallback(async () => {
    try {
      await clearTokens();
      setAccessToken(null);
      setUser(null);
      delete api.defaults.headers.common['Authorization'];
      console.log('👋 Logout completado');
    } catch (e) {
      console.warn('❌ Error en logout:', e);
    }
  }, [clearTokens]);

  const fetchUserFromCedula = useCallback(async (cedula: string) => {
    if (!accessToken) {
      console.warn('⚠️ No hay accessToken para obtener información del usuario');
      return;
    }
    
    try {
      console.log('🔍 Obteniendo información del usuario por cédula:', cedula);
      const response = await api.get(`/obtener-persona-login/`);
      const userData = response.data;
      
      console.log('📋 Información de usuario recibida:', userData);
      
      if (userData && userData.idPersona) {
        const completeUser: UserPayload = {
          idPersona: userData.idPersona,
          cedula: userData.cedula || cedula,
          nombres: userData.nombres,
          apellidos: userData.apellidos,
          correo: userData.correo,
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

  const setUserFromApi = useCallback((userObj: UserPayload) => {
    console.log('👤 Actualizando usuario desde API:', userObj);
    setUser(userObj);
    (async () => {
      try {
        const tokens = await getTokens();
        if (tokens) {
          await storeTokens(tokens.access, tokens.refresh, userObj);
        }
      } catch (e) { 
        console.warn('❌ Error guardando usuario actualizado', e);
      }
    })();
  }, [getTokens, storeTokens]);

  useEffect(() => {
    const initializeAuth = async () => {
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
            console.log('✅ Token establecido en headers de API');
          }
          
          if (u) {
            setUser(u);
            console.log('👤 Usuario cargado desde storage:', u);
          }
        }
      } catch (e) {
        console.warn('❌ Error inicializando auth:', e);
      } finally {
        setIsLoading(false);
        console.log('🏁 Inicialización de auth completada');
      }
    };

    initializeAuth();
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
      fetchUserFromCedula,
    }}>
      {children}
    </AuthContext.Provider>
  );
};