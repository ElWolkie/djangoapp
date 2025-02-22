from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('apps.api.urls')),  # Incluye las rutas de la API
    path("", include("apps.authentication.urls")),  # Rutas de autenticación
    path("", include("apps.home.urls")),  # Rutas de la interfaz de usuario
]