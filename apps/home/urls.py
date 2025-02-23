from django.urls import path, re_path
from . import views

urlpatterns = [
    path('', views.index, name='home'),  # Ruta para la página principal
    re_path(r'^.*\.*', views.pages, name='pages'),  # Ruta para manejar páginas estáticas (como about.html, contact.html, etc.)

    # The home page
    path('', views.index, name='home'),
    # Matches any html file
    re_path(r'^.*\.*', views.pages, name='pages'),


    # Specific route for tipoPersona modal
    path('tipoPersonaModal/', views.tipo_persona_modal, name='tipo_persona_modal'),
    # Specific route for tipoPersona modal
    path('tipoOfertaModal/', views.tipo_oferta_modal, name='tipo_oferta_modal'),
    # Specific route for tipoPersona modal
    path('ofertaModal/', views.oferta_modal, name='oferta_modal'),


]