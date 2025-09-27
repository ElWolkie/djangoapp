from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from . import views
from .endpoints import verificar_cedula  # Nueva función

urlpatterns = [
    path('personas/', views.PersonaListCreate.as_view(), name='persona-list'),
    path('personas/<int:pk>/', views.PersonaRetrieveUpdateDestroy.as_view(), name='persona-detail'),
    path('tipo-personas/', views.TipoPersonaListCreate.as_view(), name='tipo-persona-list'),
    path('personastp/', views.PersonaTPListCreate.as_view(), name='personatp-list'),
    path('formaciones/', views.FormacionListCreate.as_view(), name='formaciones-list'),
    path('tipo-formaciones/', views.TPFormacionListCreate.as_view(), name='tipo-formaciones-list'),
    path('materias/', views.MateriaListCreate.as_view(), name='materia-list'),

    path('verificar-cedula/', verificar_cedula, name='verificar-cedula'),

    path('cohorte/', views.CohorteListCreate.as_view(), name='cohorte-list'),
    path('cargo/', views.CargoListCreate.as_view(), name='cargo-list'),
    path('honorario/', views.HonorarioListCreate.as_view(), name='honorario-list'),
    path('inscripcion/', views.InscripcionListCreate.as_view(), name='inscripcion-list'),
    path('requisito/', views.RequisitoListCreate.as_view(), name='requisito-list'),
    path('servicio/', views.ServicioListCreate.as_view(), name='servicio-list'),
    path('tramite/', views.TramiteListCreate.as_view(), name='tramite-list'),
    path('solicitud/', views.SolicitudListCreate.as_view(), name='solicitud-list'),
    path('moneda/', views.MonedaListCreate.as_view(), name='moneda-list'),
    path('tasa/', views.TasaListCreate.as_view(), name='tasa-list'),

    path('token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),  # Solo permite POST
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),  # Solo permite POST

    # URLs para contabilidad
    path('libro-diario/', views.LibroDiarioAPIView.as_view(), name='libro-diario'),
    path('libro-mayor/', views.LibroMayorAPIView.as_view(), name='libro-mayor'),
    path('balance-cuentas/', views.BalanceCuentasAPIView.as_view(), name='balance-cuentas'),
]
