# apps/saldoContable/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('create/', views.saldo_contable_create, name='saldo_contable_create'),
    path('list/', views.saldo_contable_list, name='saldo_contable_list'),
    path('api/saldos-existente/', views.saldos_existentes_api, name='saldos_existentes_api'),
]