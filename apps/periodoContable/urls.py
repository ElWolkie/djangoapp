from django.urls import path
from . import views

urlpatterns = [
    path('', views.periodo_contable_list, name='periodo_contable_list'),
    path('nuevo/', views.periodo_contable_create, name='periodo_contable_create'),
    path('editar/<int:id>/', views.periodo_contable_edit, name='periodo_contable_edit'),
]