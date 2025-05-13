from django.urls import path
from . import views

urlpatterns = [
    path('', views.cuentaBanco_list, name='cuentaBanco_list'),
    path('nuevo/', views.cuentaBanco_create, name='cuentaBanco_create'),
    path('editar/<int:id>/', views.cuentaBanco_edit, name='cuentaBanco_edit'),
]