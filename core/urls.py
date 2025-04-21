# core/urls.py
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('auth/', include('apps.authentication.urls')),
    path('api/', include('apps.api.urls')),
    path('persona/', include('apps.persona.urls')),      # UI Kits Html files persona
    path('honorario/', include('apps.honorario.urls')),      # UI Kits Html files honorario
    path('inscripcion/', include('apps.inscripcion.urls')),      # UI Kits Html files honorario
    path('solicitud/', include('apps.solicitud.urls')),      # UI Kits Html files solicitud
    path('home/', include("apps.home.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

urlpatterns += [
    path("", include("apps.home.urls")),
]
