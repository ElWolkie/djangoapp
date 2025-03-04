from django.urls import path, re_path
from . import views

urlpatterns = [
    # Ruta principal (Home)
    path('', views.index, name='home'),
    
    # Ruta para el index (sin duplicados)
    path('index/', views.index_view, name='index'),
    
    # Rutas específicas para modales
    path('tipoPersonaModal/', views.tipo_persona_modal, name='tipo_persona_modal'),
    path('tipoOfertaModal/', views.tipo_oferta_modal, name='tipo_oferta_modal'),
    path('ofertaModal/', views.oferta_modal, name='oferta_modal'),
    path('cuotaModal/', views.cuota_modal, name='cuota_modal'),
    
    # Catch-all para páginas estáticas (DEBE IR AL FINAL) El orden de las URLs en Django es crítico. debe ir SIEMPRE AL FINAL.
    re_path(r'^.*\.*', views.pages, name='pages'),
]