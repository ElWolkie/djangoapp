# core/urls.py
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('liuhjygtrfdewgvgthbyhujnkl/', admin.site.urls),
    path('auth/', include('apps.authentication.urls')),
    path('api/', include('apps.api.urls')),
    path('persona/', include('apps.persona.urls')),      # UI Kits Html files persona
    path('honorario/', include('apps.honorario.urls')),      # UI Kits Html files honorario
    path('inscripcion/', include('apps.inscripcion.urls')),      # UI Kits Html files honorario
    path('solicitud/', include('apps.solicitud.urls')),      # UI Kits Html files solicitud

    ################CONTABILIDAD######################
    path('planCuenta/', include('apps.planCuenta.urls')),      # UI Kits Html files solicitud
    path('periodoContable/', include('apps.periodoContable.urls')),      # UI Kits Html files solicitud
    path('empresa/', include('apps.empresa.urls')),      # UI Kits Html files empresa
    path('cuentaBanco/', include('apps.cuentaBanco.urls')),      # UI Kits Html files cuentaBanco
    path('asientoContable/', include('apps.asientoContable.urls')),      # UI Kits Html files empresa
    path('factura/', include('apps.factura.urls')),      # UI Kits Html files factura
    path('saldoContable/', include('apps.saldoContable.urls')),      # UI Kits Html files saldo contable
    path('librosContables/', include('apps.librosContables.urls')),      # UI Kits Html files factura


    path('home/', include("apps.home.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    # urlpatterns += [path('__debug__/', include('debug_toolbar.urls')),
    # ]    

urlpatterns += [
    path("", include("apps.home.urls")),
]
