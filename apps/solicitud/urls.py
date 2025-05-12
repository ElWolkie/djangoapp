from django.urls import path, re_path
from . import views

urlpatterns = [

    path('tablaSolicitud/', views.tabla_solicitud, name='tabla_solicitud'),


    # Specific route for solicitud modal
    path('registrarSolicitud/', views.solicitud_modal, name='solicitud_modal'),
    path('editSolicitud/<int:pk>/', views.edit_solicitud, name='edit_solicitud'),
    path('deleteSolicitud/<int:pk>/', views.delete_solicitud, name='delete_solicitud'),
    path('desactivar_solicitud/<int:pk>/', views.desactivar_solicitud, name='desactivar_solicitud'),
    path('reactivateSolicitud/<int:pk>/', views.reactivate_solicitud, name='reactivate_solicitud'),
    path('solicitudes/', views.pages, {'load_template': 'tablaSolicitud.html'}, name='lista_solicitudes'),

    # Coincide con cualquier archivo HTML (no mover de lugar)
    re_path(r'^.*\.*', views.pages, name='pages'),

]