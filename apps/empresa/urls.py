from django.urls import path
from . import views

urlpatterns = [
    path('', views.empresa_list, name='empresa_list'),
    path('nuevo/', views.empresa_create, name='empresa_create'),
    path('editar/<int:id>/', views.empresa_edit, name='empresa_edit'),
]