from django.shortcuts import render
from django.db.models import Sum
from apps.asientoContable.models import AsientoContable, DetalleAsiento
from apps.planCuenta.models import PlanCuenta
from django.core.paginator import Paginator
from django.db.models import Q
def libro_diario(request):
    """
    Vista para generar el Libro Diario.
    Muestra los asientos contables y sus detalles en orden cronológico.
    """
    search_query = request.GET.get('search', '').strip()  # Obtener el término de búsqueda
    start_date = request.GET.get('start_date')  # Obtener la fecha de inicio
    end_date = request.GET.get('end_date')  # Obtener la fecha de fin

    asientos = AsientoContable.objects.prefetch_related('detalles').order_by('fechaAsiento', 'numeroAsiento')

    # Filtrar por el término de búsqueda si existe
    if search_query:
        asientos = asientos.filter(
            Q(numeroAsiento__icontains=search_query) |
            Q(fechaAsiento__icontains=search_query) |
            Q(conceptoAsiento__icontains=search_query) |
            Q(detalles__idPlanCuenta__nombrePlanCuenta__icontains=search_query) |
            Q(detalles__idPlanCuenta__codigoPlanCuenta__icontains=search_query) |
            Q(detalles__debe__icontains=search_query) |
            Q(detalles__haber__icontains=search_query)
        ).distinct()

    # Filtrar por rango de fechas si existen
    if start_date:
        asientos = asientos.filter(fechaAsiento__gte=start_date)
    if end_date:
        asientos = asientos.filter(fechaAsiento__lte=end_date)

    # Calcular los totales de debe y haber
    totales = asientos.aggregate(
        total_debe=Sum('detalles__debe'),
        total_haber=Sum('detalles__haber')
    )

    paginator = Paginator(asientos, 10)  # 10 asientos por página
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'librosContables/libroDiario.html', {
        'asientos': page_obj,
        'total_debe': totales['total_debe'] or 0,
        'total_haber': totales['total_haber'] or 0
    })


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