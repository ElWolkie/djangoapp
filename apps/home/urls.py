from django.urls import path, re_path
from . import views

urlpatterns = [
    path('', views.index, name='home'),  # Ruta para la página principal
    re_path(r'^.*\.*', views.pages, name='pages'),  # Ruta para manejar páginas estáticas (como about.html, contact.html, etc.)
]