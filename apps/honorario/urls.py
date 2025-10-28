from django.urls import path, re_path
from . import views

urlpatterns = [

    path('tablaHonorarios/', views.tabla_honorarios, name='tabla_honorarios'),

    # Specific route for honorario modal
    path('honorarioModal/', views.honorario_modal, name='honorario_modal'),
    path('editHonorario/<int:pk>/', views.edit_honorario, name='edit_honorario'),
    path('deleteHonorario/<int:pk>/', views.delete_honorario, name='delete_honorario'),
    path('desactivar_honorario/<int:pk>/', views.desactivar_honorario, name='desactivar_honorario'),
    path('reactivateHonorario/<int:pk>/', views.reactivate_honorario, name='reactivate_honorario'),
    path('reporteHonorarios/', views.reporte_honorarios_pdf, name='reporte_honorarios_pdf'),
    # Nueva URL para redirigir a factura de honorario
    path('honorario/factura/<int:pk>/', views.redirigir_a_factura_honorario, name='redirigir_factura_honorario'),
    path('honorario/nota/<int:pk>/', views.redirigir_a_nota_honorario, name='redirigir_nota_honorario'),
    # Coincide con cualquier archivo HTML (no mover de lugar)
    re_path(r'^.*\.*', views.pages, name='pages'),

]