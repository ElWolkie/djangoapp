from django.urls import path
from . import views


urlpatterns = [
    # Planes de Cuenta
    path('planes/', views.plan_cuenta_list, name='plan_cuenta_list'),
    path('planes/<int:pk>/', views.plan_cuenta_detail, name='plan_cuenta_detail'),
    path('planes/nuevo/', views.plan_cuenta_create, name='plan_cuenta_create'),
    path('planes/editar/<int:pk>/', views.editar_plan, name='editar_plan'),
    path('planes/eliminar/<int:id>/', views.desactivar_plan, name='desactivar_plan'),
    path('reactivar/<int:id>/', views.reactivar_plan, name='reactivar_plan'),
    path('reportePlanes/',views.reporte_planes_pdf, name='reporte_planes_pdf' )
    
]