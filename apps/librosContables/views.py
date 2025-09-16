from django.shortcuts import render
from django.db.models import Sum
from apps.asientoContable.models import AsientoContable, DetalleAsiento
from apps.planCuenta.models import PlanCuenta

def libro_diario(request):
    """
    Vista para generar el Libro Diario.
    Muestra los asientos contables y sus detalles en orden cronológico.
    """
    asientos = AsientoContable.objects.prefetch_related('detalles').order_by('fechaAsiento', 'numeroAsiento')
    return render(request, 'librosContables/libroDiario.html', {'asientos': asientos})


def libro_mayor(request):
    """
    Vista para generar el Libro Mayor.
    Agrupa los movimientos por cuenta contable y calcula los saldos.
    """
    cuentas = PlanCuenta.objects.annotate(
        total_debe=Sum('detalleasiento__debe'),
        total_haber=Sum('detalleasiento__haber')
    ).order_by('codigoPlanCuenta')

    return render(request, 'librosContables/libroMayor.html', {'cuentas': cuentas})


def balance_cuentas(request):
    """
    Vista para generar el Balance de Cuentas.
    Agrupa las cuentas por tipo y calcula los totales y saldos.
    """
    tipos_cuentas = PlanCuenta.objects.values('tipoPlanCuenta').annotate(
        total_debe=Sum('detalleasiento__debe'),
        total_haber=Sum('detalleasiento__haber')
    ).order_by('tipoPlanCuenta')

    # Calcular el saldo para cada tipo de cuenta
    for tipo in tipos_cuentas:
        debe = tipo['total_debe'] or 0
        haber = tipo['total_haber'] or 0
        if debe > haber:
            tipo['saldo'] = f"Deudor: {debe - haber:.2f}"
        elif haber > debe:
            tipo['saldo'] = f"Acreedor: {haber - debe:.2f}"
        else:
            tipo['saldo'] = "Saldo Cero"

    return render(request, 'librosContables/balanceCuentas.html', {'tipos_cuentas': tipos_cuentas})