# TODO: Integrar Libros Contables en App Móvil

## Backend (Django)
- [x] Agregar serializadores para modelos contables en apps/api/serializers.py
- [x] Crear vistas API para libro diario, mayor, balance, ingresos, egresos en apps/api/views.py
- [x] Agregar URLs para endpoints contables en apps/api/urls.py

## Mobile (React Native)
- [x] Agregar funciones API en mobile/src/api/index.ts
- [x] Crear pantallas: LibroDiarioScreen, LibroMayorScreen, BalanceCuentasScreen, IngresosScreen, EgresosScreen
- [x] Actualizar navegación en AppNavigator.tsx para incluir nuevas pantallas

## Testing
- [x] Probar endpoints API con curl (servidor corriendo en localhost:8000)
- [ ] Verificar funcionamiento en app móvil (requiere datos en BD y app corriendo)

## Diseño
- [x] Actualizar diseño de LibroMayorScreen para coincidir con el sistema web
- [x] Actualizar diseño de LibroDiarioScreen para coincidir con el sistema web
