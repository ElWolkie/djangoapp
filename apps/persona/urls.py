from django.urls import path, re_path
from . import views

urlpatterns = [
    #Ruta especifica para Persona
    path('persona.html', views.pages, name='persona_page'),
    path('persona_modal/', views.persona_modal, name='persona_modal'), # URL para el POST del formulario principal
    path('seleccionar-tipo-consulta/', views.seleccionar_tipo_consulta, name='seleccionar_tipo_consulta'), # URL para el POST de la tabla principal
    path('editPersona/<int:pk>/', views.edit_persona, name='edit_persona'),
    path('deletePersona/<int:pk>/', views.delete_persona, name='delete_persona'),
    path('desactivar_persona/<int:pk>/', views.desactivar_persona, name='desactivar_persona'),
    path('reactivatePersona/<int:pk>/', views.reactivate_persona, name='reactivate_persona'),
    path('reporte_personas_pdf/', views.reporte_personas_pdf, name='reporte_personas_pdf'),
    path('tabla_persona/', views.tabla_persona, name='tabla_persona'),

    #Ruta especifica para TipoPersona
    path('tipoPersonaModal/', views.tipo_persona_modal, name='tipo_persona_modal'),
    path('registroTipoPersona/', views.registro_tipo_persona, name='registro_tipo_persona'),
    path('tipopersona/', views.listado_tipos_persona, name='listado_tipos_persona'),
    path('editTipoPersona/<int:pk>/', views.edit_tipo_persona, name='edit_tipo_persona'),
    path('deleteTipoPersona/<int:pk>/', views.delete_tipo_persona, name='delete_tipo_persona'),
    path('reactivateTipoPersona/<int:pk>/', views.reactivate_tipo_persona, name='reactivate_tipo_persona'),

    path('solicitud.html', views.solicitud_view, name='solicitud_page'),


    # Coincide con cualquier archivo HTML (no mover de lugar)
    re_path(r'^.*\.*', views.pages, name='pages'),

]