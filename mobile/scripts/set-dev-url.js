// scripts/set-dev-url.js
const os = require('os');
const fs = require('fs');
const path = require('path');

function getLocalIPv4() {
  const ifaces = os.networkInterfaces();
  for (const name of Object.keys(ifaces)) {
    for (const iface of ifaces[name]) {
      if (iface.family === 'IPv4' && !iface.internal) {
        // ignora adaptadores virtuales si quieres (opcional)
        if (!iface.address.startsWith('169.254')) return iface.address;
      }
    }
  }
  return null;
}

const ip = getLocalIPv4();
if (!ip) {
  console.error('No se encontró IP local. Conéctate a la red y reintenta.');
  process.exit(1);
}

const port = process.env.BACKEND_PORT || '8000';
const envPath = path.resolve(process.cwd(), '.env.development'); // o .env
const content = `API_BASE_URL=http://${ip}:${port}\n`;

fs.writeFileSync(envPath, content);
console.log(`Wrote ${envPath}: ${content}`);
