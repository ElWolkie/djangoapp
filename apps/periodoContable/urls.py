from django.urls import path
from . import views

urlpatterns = [
    path('', views.periodo_contable_list, name='periodo_contable_list'),
    path('nuevo/', views.periodo_contable_create, name='periodo_contable_create'),
    path('editar/<int:id>/', views.periodo_contable_edit, name='periodo_contable_edit'),
    path('eliminar/<int:id>/', views.desactivar_periodo_contable, name='periodo_contable_delete'),
    path('reactivar/<int:id>/', views.reactivar_periodo_contable, name='periodo_contable_reactivate'),
    path('reporte_periodos_pdf/', views.reporte_periodos_pdf, name='reporte_periodos_pdf'),
]