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
    # Matches any html file
    re_path(r'^.*\.*', views.pages, name='pages'),


]