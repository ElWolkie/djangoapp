from django.urls import path, re_path
from . import views

urlpatterns = [

    path('tablaSolicitud/', views.tabla_solicitud, name='tabla_solicitud'),


    # Ruta para el modal de solicitud
    path('registrarSolicitud/', views.solicitud_modal, name='solicitud_modal'),
    path('editSolicitud/<int:pk>/', views.edit_solicitud, name='edit_solicitud'),
    path('deleteSolicitud/<int:pk>/', views.delete_solicitud, name='delete_solicitud'),
    path('desactivar_solicitud/<int:pk>/', views.desactivar_solicitud, name='desactivar_solicitud'),
    path('reactivateSolicitud/<int:pk>/', views.reactivate_solicitud, name='reactivate_solicitud'),
    path('reporteSolicitudes/', views.reporte_solicitudes_pdf, name='reporte_solicitudes_pdf'),
    path('solicitudes/', views.pages, {'load_template': 'tablaSolicitud.html'}, name='lista_solicitudes'),

    # Ruta para los requisitos de la solicitud
    path('requisitosSolicitud/<int:pk>/form/', views.requisitos_solicitud_modal, name='requisitos_solicitud_modal'),
    path('requisitosSolicitud/<int:pk>/', views.guardar_requisitos_solicitud, name='guardar_requisitos_solicitud'),

    # Nueva URL para redirigir a factura de solicitud
    path('solicitud/factura/<int:pk>/', views.redirigir_a_factura_solicitud, name='redirigir_factura_solicitud'),
    path('solicitud/nota/<int:pk>/', views.redirigir_a_nota_solicitud, name='redirigir_nota_solicitud'),
   
    # Coincide con cualquier archivo HTML (no mover de lugar)
    re_path(r'^.*\.*', views.pages, name='pages'),

]