from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from . import views

urlpatterns = [
    path('personas/', views.PersonaListCreate.as_view(), name='persona-list'),
    path('personas/<int:pk>/', views.PersonaRetrieveUpdateDestroy.as_view(), name='persona-detail'),
    path('tipo-personas/', views.TipoPersonaListCreate.as_view(), name='tipo-persona-list'),  # Nueva ruta
    path('cuota/', views.CuotaListCreate.as_view(), name='cuota-list'),
    path('ofertas/', views.OfertasListCreate.as_view(), name='oferta-list'),
    path('tipo-oferta/', views.TipoOfertaListCreate.as_view(), name='tipo-oferta-list'),
    path('token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),  # Solo permite POST
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),  # Solo permite POST
]