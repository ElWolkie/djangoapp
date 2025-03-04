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
       # Specific route for materia modal
    path('materiaModal/', views.materia_modal, name='materia_modal'),
    # Specific route for cohorte modal
    path('cohorteModal/', views.cohorte_modal, name='cohorte_modal'),
    # Specific route for cohorte modal
    path('cargoModal/', views.cargo_modal, name='cargo_modal'),
    # Specific route for cohorte modal
    path('contratoModal/', views.contrato_modal, name='contrato_modal'),
   
   
    # Matches any html file no mover de lugar 
    re_path(r'^.*\.*', views.pages, name='pages'),
]