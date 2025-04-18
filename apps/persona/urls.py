from django.urls import path, re_path
from . import views

urlpatterns = [

    path('persona.html', views.pages, name='persona_page'),
   # Ruta específica para el modal tipoPersona
    path('tipoPersonaModal/', views.tipo_persona_modal, name='tipo_persona_modal'),
    

    path('solicitud.html', views.solicitud_view, name='solicitud_page'),


    # Coincide con cualquier archivo HTML (no mover de lugar)
    re_path(r'^.*\.*', views.pages, name='pages'),

]