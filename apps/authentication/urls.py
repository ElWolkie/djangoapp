# apps/authentication/urls.py
from django.urls import path
from .views import login_view, logout_view, register_view, CustomTokenObtainPairView

urlpatterns = [
    # API JWT
    path('api/login/', CustomTokenObtainPairView.as_view(), name='api_login'),  
    
    # Vistas tradicionales (HTML)
    path('web/login/', login_view, name='login'),
    path('web/register/', register_view, name='register'),
    path('logout/', logout_view, name='logout'),
]