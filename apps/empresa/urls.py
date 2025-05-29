from django.urls import path
from . import views

urlpatterns = [
    path('', views.empresa_list, name='empresa_list'),
    path('nuevo/', views.empresa_create, name='empresa_create'),
    path('editar/<int:id>/', views.editar_empresa, name='editar_empresa'),
    path('desactivar/<int:id>/', views.desactivar_empresa, name='desactivar_empresa'),
    path('reactivar/<int:id>/', views.reactivar_empresa, name='reactivar_empresa'),
    path('reporteEmpresa/', views.reporte_empresas_pdf, name='reporte_empresas_pdf'),
]