// src/utils/productionCheck.ts
import api from '../api/api';

export const checkProductionSetup = async () => {
  console.log('🔍 Verificando configuración de producción...');
  
  // Verificar URL base
  console.log('🌐 URL Base:', api.defaults.baseURL);
  console.log('🔧 Modo desarrollo:', __DEV__);
  
  // Verificar conexión con el backend usando un endpoint que SÍ existe
  try {
    // Usamos un endpoint que sabemos que existe en tu API
    const response = await api.get('/api/tipo-formaciones/');
    console.log('✅ Backend conectado:', response.status);
    
    // Verificar endpoints críticos
    const endpoints = ['/api/tipo-formaciones/', '/api/formaciones/', '/api/cohorte/'];
    
    for (const endpoint of endpoints) {
      try {
        const testResponse = await api.get(endpoint);
        console.log(`✅ ${endpoint}: ${testResponse.status}`);
      } catch (error: any) {
        console.error(`❌ ${endpoint}:`, error.message);
      }
    }
  } catch (error: any) {
    console.error('❌ No se pudo conectar al backend:', error.message);
    console.log('💡 Asegúrate de que tu backend en Render esté funcionando');
  }
};

// Ejecutar en app principal
export const initializeApp = async () => {
  if (!__DEV__) {
    await checkProductionSetup();
  } else {
    console.log('🚀 Modo desarrollo activado');
    console.log('🌐 URL de desarrollo:', api.defaults.baseURL);
  }
};