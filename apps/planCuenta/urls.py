from django.urls import path
from . import views


urlpatterns = [
    # Planes de Cuenta
    path('planes/', views.plan_cuenta_list, name='plan_cuenta_list'),
    path('planes/<int:pk>/', views.plan_cuenta_detail, name='plan_cuenta_detail'),
    path('planes/nuevo/', views.plan_cuenta_create, name='plan_cuenta_create'),
    path('planes/editar/<int:pk>/', views.plan_cuenta_update, name='plan_cuenta_update'),
    path('planes/eliminar/<int:pk>/', views.plan_cuenta_delete, name='plan_cuenta_delete'),
    
]