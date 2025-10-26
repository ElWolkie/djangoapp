from django.urls import path, re_path
from . import views

urlpatterns = [
    path('tablaInscripciones/', views.tabla_inscripciones, name='tabla_inscripciones'),

    # Rutas para inscripción
    path('inscripcionModal/', views.inscripcion_modal, name='inscripcion_modal'),
    path('editInscripcion/<int:pk>/', views.edit_inscripcion, name='edit_inscripcion'),
    path('deleteInscripcion/<int:pk>/', views.delete_inscripcion, name='delete_inscripcion'),
    path('desactivarInscripcion/<int:pk>/', views.desactivar_inscripcion, name='desactivar_inscripcion'),
    path('reactivateInscripcion/<int:pk>/', views.reactivate_inscripcion, name='reactivate_inscripcion'),
    path('reporteInscripcion/', views.reporte_inscripcion_pdf, name='reporte_inscripcion_pdf'),

    # # Rutas para pagos de cuotas
    # path('registrarPagoCuota/<int:pk>/', views.registrar_pago_cuota, name='registrar_pago_cuota'),

    # Rutas para requisitos de inscripción
    path('requisitosInscripcion/<int:pk>/form/', views.requisitos_inscripcion_modal, name='requisitos_inscripcion_modal'),
    path('requisitosInscripcion/<int:pk>/', views.guardar_requisitos_inscripcion, name='guardar_requisitos_inscripcion'),

    # Nueva ruta para ver cuotas de inscripción
    path('verCuotasInscripcion/<int:pk>/', views.ver_cuotas_inscripcion, name='ver_cuotas_inscripcion'),

    #Ruta para la redireccion a la factura de la inscripcion espeficifica
    path('inscripcion/factura/<int:pk>/', views.redirigir_a_factura_inscripcion, name='redirigir_factura_inscripcion'),

    # Coincide con cualquier archivo HTML (no mover de lugar)
    re_path(r'^.*\.*', views.pages, name='pages'),
]