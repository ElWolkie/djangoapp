from django.urls import path, re_path
from . import views

urlpatterns = [

    path('tablaInscripciones/', views.tabla_inscripciones, name='tabla_inscripciones'),

    # Specific route for inscripcion modal
    path('inscripcionModal/', views.inscripcion_modal, name='inscripcion_modal'),
    path('editInscripcion/<int:pk>/', views.edit_inscripcion, name='edit_inscripcion'),
    path('deleteInscripcion/<int:pk>/', views.delete_inscripcion, name='delete_inscripcion'),
    path('desactivarInscripcion/<int:pk>/', views.desactivar_inscripcion, name='desactivar_inscripcion'),
    path('reactivateInscripcion/<int:pk>/', views.reactivate_inscripcion, name='reactivate_inscripcion'),
    path('reporteInscripcion/', views.reporte_inscripcion_pdf, name='reporte_inscripcion_pdf'),

    # Coincide con cualquier archivo HTML (no mover de lugar)
    re_path(r'^.*\.*', views.pages, name='pages'),

]