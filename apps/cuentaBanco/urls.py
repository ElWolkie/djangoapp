from django.urls import path
from . import views

urlpatterns = [

    # Bancos
    path('', views.banco_list, name='banco_list'),
    path('<int:pk>/', views.banco_detail, name='banco_detail'),
    path('nuevo/', views.banco_create, name='banco_create'),
    path('editar/<int:pk>/', views.banco_update, name='banco_update'),
    path('eliminar/<int:pk>/', views.banco_delete, name='banco_delete'),
    path('reactivar/<int:pk>/', views.banco_reactivate, name='banco_reactivate'),
    
    # Cuentas Bancarias
    path('cuentas/', views.cuenta_banco_list, name='cuenta_banco_list'),
    path('cuentas/<int:pk>/', views.cuenta_banco_detail, name='cuenta_banco_detail'),
    path('cuentas/nuevo/', views.cuenta_banco_create, name='cuenta_banco_create'),
    path('cuentas/editar/<int:pk>/', views.cuenta_banco_update, name='cuenta_banco_update'),
    path('cuentas/eliminar/<int:pk>/', views.cuenta_banco_delete, name='cuenta_banco_delete'),
]