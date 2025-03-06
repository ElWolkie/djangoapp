from django.urls import path, re_path
from apps.home import views

urlpatterns = [

    # The home page
    path('', views.index, name='home'),

    # Specific route for tipoPersona modal
    path('tipoPersonaModal/', views.tipo_persona_modal, name='tipo_persona_modal'),
    # Specific route for tipoCuota modal
    path('tipoOfertaModal/', views.tipo_oferta_modal, name='tipo_oferta_modal'),
    # Specific route for oferta modal
    path('ofertaModal/', views.oferta_modal, name='oferta_modal'),
    # Specific route for cuota modal
    path('cuotaModal/', views.cuota_modal, name='cuota_modal'),
       # Specific route for materia modal
    path('materiaModal/', views.materia_modal, name='materia_modal'),
    # Specific route for cohorte modal
    path('cohorteModal/', views.cohorte_modal, name='cohorte_modal'),
    # Specific route for cohorte modal
    path('cargoModal/', views.cargo_modal, name='cargo_modal'),
    # Specific route for cohorte modal
    path('contratoModal/', views.contrato_modal, name='contrato_modal'),    
    # Specific route for cohorte modal
    path('honorarioModal/', views.honorario_modal, name='honorario_modal'),
     # Specific route for cohorte modal
    path('requisitoModal/', views.requisito_modal, name='requisito_modal'),
    # Specific route for servicio modal
    path('servicioModal/', views.servicio_modal, name='servicio_modal'),

    # Matches any html file no mover de lugar 
    re_path(r'^.*\.*', views.pages, name='pages'),


]