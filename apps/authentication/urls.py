from django.urls import path
from .views import login_view, logout_view, home_view

urlpatterns = [
    path('login/', login_view, name='login'),  # Ruta para el inicio de sesión
    path('logout/', logout_view, name='logout'),  # Ruta para el cierre de sesión
    path('home/', home_view, name='home'),  # Ruta para la página de inicio (home)
]