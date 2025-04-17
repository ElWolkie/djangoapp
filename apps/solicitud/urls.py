from django.urls import path, re_path
from . import views

urlpatterns = [

    path('tablaSolicitud/', views.tabla_solicitud, name='tabla_solicitud'),


    # Coincide con cualquier archivo HTML (no mover de lugar)
    re_path(r'^.*\.*', views.pages, name='pages'),

]