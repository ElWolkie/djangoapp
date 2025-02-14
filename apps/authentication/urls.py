from django.urls import path
from .views import login_view, register_user, home_view

urlpatterns = [
    path("login/", login_view, name="login"),  # URL para el inicio de sesión
    path("register/", register_user, name="register"),  # URL para el registro
    path("home/", home_view, name="index"),  # URL para la página de inicio
]
