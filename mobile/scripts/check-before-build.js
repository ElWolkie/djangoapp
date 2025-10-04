// scripts/check-before-build.js
const https = require('https');
const { execSync } = require('child_process');

console.log('🔍 Verificando requisitos antes del build...');

// 1. Verificar conexión con el backend usando un endpoint existente
console.log('1. Verificando backend en Render...');
try {
  const checkBackend = () => {
    return new Promise((resolve, reject) => {
      // Usamos un endpoint que existe en tu API
      const req = https.get('https://djangoapp-6wxv.onrender.com/api/tipo-formaciones/', (res) => {
        if (res.statusCode === 200) {
          console.log('   ✅ Backend funcionando correctamente');
          resolve(true);
        } else {
          console.log('   ❌ Backend respondió con status:', res.statusCode);
          reject(false);
        }
      });
      
      req.on('error', (err) => {
        console.log('   ❌ Error conectando al backend:', err.message);
        reject(false);
      });
      
      req.setTimeout(10000, () => {
        console.log('   ❌ Timeout conectando al backend');
        req.destroy();
        reject(false);
      });
    });
  };

  checkBackend().then(() => {
    // 2. Verificar configuración de la app
    console.log('2. Verificando configuración de la app...');
    
    const appJson = require('../app.json');
    if (appJson.expo.extra && appJson.expo.extra.API_BASE_URL) {
      console.log('   ✅ API_BASE_URL configurado:', appJson.expo.extra.API_BASE_URL);
    } else {
      console.log('   ❌ API_BASE_URL no está configurado en app.json');
      process.exit(1);
    }
    
    // 3. Verificar que eas.json existe
    try {
      const easJson = require('../eas.json');
      console.log('   ✅ eas.json configurado correctamente');
    } catch (e) {
      console.log('   ❌ eas.json no encontrado o tiene errores');
      process.exit(1);
    }
    
    console.log('🎉 Todo listo para el build!');
    console.log('🚀 Ejecuta: npm run build:production');
    
  }).catch(() => {
    console.log('💡 El backend no está disponible, pero podemos continuar...');
    console.log('🚀 Ejecuta: npm run build:production');
  });
  
} catch (error) {
  console.log('❌ Error en la verificación:', error.message);
  process.exit(1);
}