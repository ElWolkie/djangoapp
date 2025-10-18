from django.urls import path
from .views import libro_diario, libro_mayor, balance_cuentas, balance_cuentas_pdf, balance_cuentas_excel, libro_diario_pdf, libro_diario_excel, libro_mayor_pdf, libro_mayor_excel
from apps.asientoContable.urls import urlpatterns as asiento_contable_urls

urlpatterns = [
    path('libroDiario/', libro_diario, name='libro_diario'),
    path('libroMayor/', libro_mayor, name='libro_mayor'),
    path('balanceCuentas/', balance_cuentas, name='balance_cuentas'),

    # URLs para PDF
    path('balanceCuentas/pdf/', balance_cuentas_pdf, name='balance_cuentas_pdf'),
    path('libroDiario/pdf/', libro_diario_pdf, name='libro_diario_pdf'),
    path('libroMayor/pdf/', libro_mayor_pdf, name='libro_mayor_pdf'),
    
    # URLs para Excel
    path('balanceCuentas/excel/', balance_cuentas_excel, name='balance_cuentas_excel'),
    path('libroDiario/excel/', libro_diario_excel, name='libro_diario_excel'),
    path('libroMayor/excel/', libro_mayor_excel, name='libro_mayor_excel'),
]