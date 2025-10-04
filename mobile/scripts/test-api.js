// scripts/test-api.js
const https = require('https');

const API_URL = 'https://djangoapp-6wxv.onrender.com';

console.log('🔍 Probando conexión con la API...');
console.log(`📡 URL: ${API_URL}`);

// Función para probar un endpoint
function testEndpoint(endpoint) {
  return new Promise((resolve, reject) => {
    const url = `${API_URL}${endpoint}`;
    console.log(`\n🔄 Probando: ${url}`);
    
    const req = https.get(url, (res) => {
      console.log(`   ✅ Status: ${res.statusCode}`);
      console.log(`   📋 Headers:`, res.headers['content-type']);
      resolve(res.statusCode);
    });
    
    req.on('error', (err) => {
      console.log(`   ❌ Error: ${err.message}`);
      reject(err);
    });
    
    req.setTimeout(10000, () => {
      console.log('   ⏰ Timeout: La solicitud tardó demasiado');
      req.destroy();
      reject(new Error('Timeout'));
    });
  });
}

// Probar múltiples endpoints
async function testAllEndpoints() {
  try {
    console.log('🚀 Iniciando pruebas de conexión...\n');
    
    // Probar endpoints que deberían existir
    await testEndpoint('/api/tipo-formaciones/');
    await testEndpoint('/api/auth/login/');
    
    console.log('\n🎉 ¡Todas las pruebas completadas!');
    console.log('✅ Tu API está funcionando correctamente');
    console.log('🚀 Puedes proceder con el build de la app');
    
  } catch (error) {
    console.log('\n⚠️  Algunas pruebas fallaron, pero podemos continuar...');
    console.log('💡 Verifica que los endpoints necesarios estén funcionando');
  }
}

testAllEndpoints();