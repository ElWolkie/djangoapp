from django.urls import path, re_path
from . import views

urlpatterns = [
    #Ruta especifica para Persona
    path('persona.html', views.pages, name='persona_page'),
    path('editPersona/<int:pk>/', views.edit_persona, name='edit_persona'),
    path('deletePersona/<int:pk>/', views.delete_persona, name='delete_persona'),
    path('reactivatePersona/<int:pk>/', views.reactivate_persona, name='reactivate_persona'),

    #Ruta especifica para TipoPersona
    path('tipoPersonaModal/', views.tipo_persona_modal, name='tipo_persona_modal'),
    path('editTipoPersona/<int:pk>/', views.edit_tipo_persona, name='edit_tipo_persona'),
    path('deleteTipoPersona/<int:pk>/', views.delete_tipo_persona, name='delete_tipo_persona'),
    path('reactivateTipoPersona/<int:pk>/', views.reactivate_tipo_persona, name='reactivate_tipo_persona'),

    path('solicitud.html', views.solicitud_view, name='solicitud_page'),


    # Coincide con cualquier archivo HTML (no mover de lugar)
    re_path(r'^.*\.*', views.pages, name='pages'),

]