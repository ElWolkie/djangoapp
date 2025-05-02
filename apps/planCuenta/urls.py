from django.urls import path
from . import views

urlpatterns = [
    path('', views.plan_cuenta_list, name='plan_cuenta_list'),
    path('nuevo/', views.plan_cuenta_create, name='plan_cuenta_create'),
]