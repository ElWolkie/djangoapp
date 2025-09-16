from django.urls import path
from .views import libro_diario, libro_mayor, balance_cuentas
from apps.asientoContable.urls import urlpatterns as asiento_contable_urls

urlpatterns = [
    path('libroDiario/', libro_diario, name='libro_diario'),
    path('libroMayor/', libro_mayor, name='libro_mayor'),
    path('balanceCuentas/', balance_cuentas, name='balance_cuentas'),
]