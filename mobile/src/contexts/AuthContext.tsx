// src/contexts/AuthContext.tsx
import React, { createContext, useCallback, useEffect, useState } from 'react';
import AsyncStorage from '@react-native-async-storage/async-storage';
import api from '../api/api';
import { storeTokens, getTokens, clearTokens } from '../api/auth';

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
  // Agregar función para obtener datos completos del usuario
  fetchUserProfile: () => Promise<void>;
};

export const AuthContext = createContext<AuthContextType>({
  isLoading: true,
  isAuthenticated: false,
  user: null,
  accessToken: null,
  loginWithTokens: async () => {},
  logout: async () => {},
  fetchUserProfile: async () => {},
});

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [isLoading, setIsLoading] = useState(true);
  const [accessToken, setAccessToken] = useState<string | null>(null);
  const [user, setUser] = useState<UserPayload | null>(null);

  // Función para obtener el perfil completo del usuario
  const fetchUserProfile = useCallback(async () => {
    if (!accessToken) return;
    
    try {
      console.log('🔍 Obteniendo perfil completo del usuario...');
      const response = await api.get('/api/user/profile/'); // Ajusta este endpoint según tu API
      const userData = response.data;
      
      console.log('📋 Perfil completo recibido:', userData);
      
      // Mapear los campos según lo que devuelve tu API
      const completeUser: UserPayload = {
        idPersona: userData.idPersona || userData.id,
        id: userData.id,
        cedula: userData.cedula,
        nombres: userData.nombres,
        apellidos: userData.apellidos,
        email: userData.email,
        displayName: userData.displayName || `${userData.nombres} ${userData.apellidos}`,
      };
      
      setUser(completeUser);
      
      // Guardar en AsyncStorage
      const tokens = await getTokens();
      const toSave = { 
        access: tokens?.access ?? accessToken, 
        refresh: tokens?.refresh ?? null, 
        user: completeUser 
      };
      await AsyncStorage.setItem('myapp-tokens', JSON.stringify(toSave));
      
    } catch (error) {
      console.error('❌ Error obteniendo perfil del usuario:', error);
      // Si falla, intentar obtener de manera alternativa
      await tryAlternativeUserData();
    }
  }, [accessToken]);

  // Función alternativa para obtener datos del usuario
  const tryAlternativeUserData = useCallback(async () => {
    try {
      // Intentar obtener datos de diferentes endpoints
      const endpoints = ['/api/me/', '/api/user/', '/api/auth/user/'];
      
      for (const endpoint of endpoints) {
        try {
          const response = await api.get(endpoint);
          if (response.data) {
            const userData = response.data;
            const completeUser: UserPayload = {
              idPersona: userData.idPersona || userData.id,
              id: userData.id,
              cedula: userData.cedula,
              nombres: userData.nombres,
              apellidos: userData.apellidos,
              email: userData.email,
              displayName: userData.displayName || `${userData.nombres} ${userData.apellidos}`,
            };
            
            setUser(completeUser);
            const tokens = await getTokens();
            const toSave = { 
              access: tokens?.access ?? accessToken, 
              refresh: tokens?.refresh ?? null, 
              user: completeUser 
            };
            await AsyncStorage.setItem('myapp-tokens', JSON.stringify(toSave));
            break;
          }
        } catch (e) {
          continue; // Intentar con el siguiente endpoint
        }
      }
    } catch (error) {
      console.error('❌ Error en método alternativo:', error);
    }
  }, [accessToken]);

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
          
          if (u) {
            setUser(u);
            console.log('👤 Usuario cargado desde storage:', u);
            
            // Si no tenemos idPersona, intentar obtener el perfil completo
            if (!u.idPersona && at) {
              console.log('🔄 No hay idPersona, obteniendo perfil completo...');
              await fetchUserProfile();
            }
          }
        }
      } catch (e) {
        console.warn('AuthProvider load error', e);
      } finally {
        setIsLoading(false);
      }
    })();
  }, [fetchUserProfile]);

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
        
        // Si el usuario no tiene idPersona, obtener perfil completo
        if (!userObj.idPersona) {
          console.log('🔄 Usuario sin idPersona, obteniendo perfil completo...');
          setTimeout(() => fetchUserProfile(), 1000); // Pequeño delay para asegurar el token
        }
      } else {
        // Si no viene userObj, obtener el perfil completo
        console.log('🔄 Obteniendo perfil completo después del login...');
        setTimeout(() => fetchUserProfile(), 1000);
      }
    } catch (e) {
      console.warn('loginWithTokens error', e);
      throw e;
    }
  }, [fetchUserProfile]);

  const logout = useCallback(async () => {
    try {
      await clearTokens();
      await AsyncStorage.removeItem('myapp-tokens');
      await AsyncStorage.removeItem('myapp-user');
      setAccessToken(null);
      setUser(null);
      delete api.defaults.headers.common['Authorization'];
      console.log('👋 Logout completado');
    } catch (e) {
      console.warn('logout error', e);
    }
  }, []);

  const setUserFromApi = useCallback((u: UserPayload) => {
    console.log('👤 Actualizando usuario desde API:', u);
    setUser(u);
    (async () => {
      try {
        const tk = await getTokens();
        const toSave = { 
          access: tk?.access ?? accessToken, 
          refresh: tk?.refresh ?? null, 
          user: u ?? null 
        };
        await AsyncStorage.setItem('myapp-tokens', JSON.stringify(toSave));
      } catch (e) { 
        console.warn('Error guardando usuario actualizado', e);
      }
    })();
  }, [accessToken]);

  return (
    <AuthContext.Provider value={{
      isLoading,
      isAuthenticated: !!accessToken,
      user,
      accessToken,
      loginWithTokens,
      logout,
      setUserFromApi,
      fetchUserProfile,
    }}>
      {children}
    </AuthContext.Provider>
  );
};