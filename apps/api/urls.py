from django.urls import include, path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from . import views
from .endpoints import *
from .views import CedulaTokenObtainView

urlpatterns = [
    path('personas/', views.PersonaListCreate.as_view(), name='persona-list'),
    path('personas/<int:pk>/', views.PersonaRetrieveUpdateDestroy.as_view(), name='persona-detail'),
    path('tipo-personas/', views.TipoPersonaListCreate.as_view(), name='tipo-persona-list'),
    path('personastp/', views.PersonaTPListCreate.as_view(), name='personatp-list'),
    path('tipo-formaciones/', views.TPFormacionListCreate.as_view(), name='tipo-formaciones-list'),
    path('materias/', views.MateriaListCreate.as_view(), name='materia-list'),

    path('verificar-cedula/', verificar_cedula, name='verificar-cedula'),
    path('registrar_persona/', PersonaPublicRegisterView.as_view(), name='registrar_persona_public'),
    path('registrar_usuario/', UsuarioPublicRegisterView.as_view(), name='registrar_usuario_public'),
    path('obtener-persona-login/', obtener_persona_login, name='obtener-persona-login'),
    path('api/formaciones/<int:formacion_id>/cuotas/', CuotasFormacionAPIView.as_view(), name='formacion-cuotas'),
    path('nota-cobro/create/', NotaCobroCreateAPIView.as_view(), name='nota_cobro_create'),
    path('api/pagos/create/', views.PagoCreateAPIView.as_view(), name='pago_create'),
    path('notas/usuario/autenticado/', notas_por_usuario_autenticado, name='notas_autenticado'),
    path('corregir-relaciones/', corregir_relaciones_notas, name='corregir_relaciones'),
    path('notas/por-cedula/', notas_por_cedula, name='notas_por_cedula'),
    path('diagnosticar-notas/', diagnosticar_notas, name='diagnosticar_notas'),
    
    path('cohorte/', views.CohorteListCreate.as_view(), name='cohorte-list'),
    path('cargo/', views.CargoListCreate.as_view(), name='cargo-list'),
    path('honorario/', views.HonorarioListCreate.as_view(), name='honorario-list'),
    path('inscripcion/', views.InscripcionListCreate.as_view(), name='inscripcion-list'),
    path('formaciones/<int:pk>/cuotas/', views.CuotasPorFormacionList.as_view(), name='formacion-cuotas'),
    path('formaciones/<int:pk>/', views.FormacionRetrieve.as_view(), name='formacion-detail'),  # opcional si no existe
    path('formaciones/', views.FormacionListCreate.as_view(), name='formaciones-list'),
    path('requisito/', views.RequisitoListCreate.as_view(), name='requisito-list'),
    path('servicio/', views.ServicioListCreate.as_view(), name='servicio-list'),
    path('tramite/', views.TramiteListCreate.as_view(), name='tramite-list'),
    path('solicitud/', views.SolicitudListCreate.as_view(), name='solicitud-list'),
    path('moneda/', views.MonedaListCreate.as_view(), name='moneda-list'),
    path('tasa/', views.TasaListCreate.as_view(), name='tasa-list'),
    path('usuario/', views.UsuarioListCreate.as_view(), name='usuario-list'),

    path('token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),  # Solo permite POST
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),  # Solo permite POST
    path('token_cedula/', CedulaTokenObtainView.as_view(), name='token_obtain_pair'),

    # URLs para contabilidad
    path('libro-diario/', views.LibroDiarioAPIView.as_view(), name='libro-diario'),
    path('libro-mayor/', views.LibroMayorAPIView.as_view(), name='libro-mayor'),
    path('balance-cuentas/', views.BalanceCuentasAPIView.as_view(), name='balance-cuentas'),
]
