from django.urls import path
from . import views

urlpatterns = [
    path("home/", views.home_view, name="home"),  # Página de inicio
    path("login/", views.login_view, name="login"),  # Página de login
    path("logout/", views.logout_view, name="logout"),  # Cierre de sesión
]