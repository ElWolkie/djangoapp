import json
from django.shortcuts import render
from django.db.models import Sum
from apps.asientoContable.models import AsientoContable, DetalleAsiento
from apps.planCuenta.models import PlanCuenta
from django.core.paginator import Paginator
from django.db.models import Q
from apps.periodoContable.models import periodoContable
from apps.saldoContable.models import SaldoContable  # Importar modelo SaldoContable

def libro_diario(request):
    """
    Vista para generar el Libro Diario.
    Muestra los asientos contables y sus detalles en orden cronológico.
    """
    search_query = request.GET.get('search', '').strip()  # Obtener el término de búsqueda
    start_date = request.GET.get('start_date')  # Obtener la fecha de inicio
    end_date = request.GET.get('end_date')  # Obtener la fecha de fin
    periodo_id = request.GET.get('periodo')  # Obtener el ID del período contable

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

    # Filtrar por período contable si existe
    if periodo_id:
        asientos = asientos.filter(idPeriodo__idPeriodo=periodo_id)

    # Calcular los totales de debe y haber
    totales = asientos.aggregate(
        total_debe=Sum('detalles__debe'),
        total_haber=Sum('detalles__haber')
    )

    paginator = Paginator(asientos, 10)  # 10 asientos por página
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    print("=== Libro Diario: Datos de Asientos ===")
    for asiento in asientos:
        print(f"Asiento #{asiento.numeroAsiento} | Fecha: {asiento.fechaAsiento} | Concepto: {asiento.conceptoAsiento}")
        for detalle in asiento.detalles.all():
            print(f"  Cuenta: {detalle.idPlanCuenta.codigoPlanCuenta} - {detalle.idPlanCuenta.nombrePlanCuenta} | Debe: {detalle.debe} | Haber: {detalle.haber}")
    print(f"Total Debe: {totales['total_debe'] or 0}")
    print(f"Total Haber: {totales['total_haber'] or 0}")
    print("=======================================")

    return render(request, 'librosContables/libroDiario.html', {
        'asientos': page_obj,
        'total_debe': totales['total_debe'] or 0,
        'total_haber': totales['total_haber'] or 0,
        'periodos': periodoContable.objects.all(),  # Lista de períodos contables
        'periodo_seleccionado': periodo_id  # Período seleccionado
    })

def libro_mayor(request):
    """
    Vista para generar el Libro Mayor con estructura jerárquica.
    Incluye buscador, filtro por período contable y paginación.
    """
    search_query = request.GET.get('search', '').strip()
    periodo_id = request.GET.get('periodo')
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')

    if start_date or end_date:
        # Si se está utilizando el filtro de rango de fechas, ignorar el filtro de período
        periodo = None
    else:
        if not periodo_id:
            periodo = periodoContable.objects.filter(estadoPeriodo=True).first()
        else:
            periodo = periodoContable.objects.filter(idPeriodo=periodo_id).first()

    if not periodo and not (start_date or end_date):
        return render(request, 'librosContables/libroMayor.html', {
            'error': 'No hay períodos contables disponibles.'
        })

    cuentas = PlanCuenta.objects.prefetch_related('subcuentas').filter(cuentaPadre__isnull=True).order_by('codigoPlanCuenta')

    # Variables globales para acumular totales
    global_total_debe = 0
    global_total_haber = 0

    def calcular_saldos(cuenta, nivel=0):
        """
        Función recursiva para calcular los totales de debe y haber de una cuenta y sus subcuentas.
        También incluye los detalles de los asientos relacionados.
        """
        nonlocal global_total_debe, global_total_haber

        movimientos = DetalleAsiento.objects.filter(idPlanCuenta=cuenta)

        if periodo:
            movimientos = movimientos.filter(idAsiento__idPeriodo=periodo)
        if start_date:
            movimientos = movimientos.filter(idAsiento__fechaAsiento__gte=start_date)
        if end_date:
            movimientos = movimientos.filter(idAsiento__fechaAsiento__lte=end_date)

        movimientos = movimientos.order_by('idAsiento__fechaAsiento', 'idAsiento__numeroAsiento')

        saldo_inicial = 0
        saldo_final = saldo_inicial
        total_debe = 0
        total_haber = 0
        detalles = []

        # Obtener todos los IDs de asientos para buscar movimientos relacionados
        asientos_ids = movimientos.values_list('idAsiento__idAsiento', flat=True)
        movimientos_relacionados = {}

        if asientos_ids:
            # Buscar TODOS los movimientos de estos asientos (aunque sean de otras cuentas)
            todos_movimientos_asiento = DetalleAsiento.objects.filter(
                idAsiento__idAsiento__in=asientos_ids
            ).select_related('idPlanCuenta', 'idAsiento')

            # Organizar por ID de asiento para fácil acceso
            for mov in todos_movimientos_asiento:
                if mov.idAsiento.idAsiento not in movimientos_relacionados:
                    movimientos_relacionados[mov.idAsiento.idAsiento] = []
                movimientos_relacionados[mov.idAsiento.idAsiento].append(mov)

        for movimiento in movimientos:
            saldo_anterior = saldo_final
            saldo_final += movimiento.debe - movimiento.haber
            total_debe += movimiento.debe
            total_haber += movimiento.haber

            # Obtener movimientos relacionados para este asiento específico
            movimientos_asiento_completo = movimientos_relacionados.get(movimiento.idAsiento.idAsiento, [])

            # Preparar movimientos completos para JSON
            movimientos_completos_json = [
                {
                    'cuenta': mov_rel.idPlanCuenta.codigoPlanCuenta + ' - ' + mov_rel.idPlanCuenta.nombrePlanCuenta,
                    'debe': float(mov_rel.debe),
                    'haber': float(mov_rel.haber)
                }
                for mov_rel in movimientos_asiento_completo
                if mov_rel.idPlanCuenta.codigoPlanCuenta != cuenta.codigoPlanCuenta  # Excluir el movimiento actual
            ]

            # Obtener beneficiario desde el pago relacionado
            beneficiario = None
            from apps.factura.models import Pago  # Importar el modelo Pago si no está importado arriba
            pago = Pago.objects.filter(idAsiento=movimiento.idAsiento).first()  # Obtener el primer pago relacionado al asiento
            if pago and pago.idNota:
                nota = pago.idNota
                if nota.idPersona:
                    beneficiario = f"{nota.idPersona.cedula} - {nota.idPersona.nombres} {nota.idPersona.apellidos}"
                elif nota.idEmpresa:
                    beneficiario = f"{nota.idEmpresa.rifEmpresa} - {nota.idEmpresa.nombreEmpresa}"

            detalles.append({
                'fecha': movimiento.idAsiento.fechaAsiento,
                'concepto': movimiento.idAsiento.conceptoAsiento,
                'beneficiario': beneficiario,
                'debe': movimiento.debe,
                'haber': movimiento.haber,
                'saldo': saldo_final,
                'id_asiento': movimiento.idAsiento.idAsiento,
                'movimientos_completos': movimientos_completos_json
            })

        # Sumar al total global
        global_total_debe += total_debe
        global_total_haber += total_haber

        subcuentas = []
        for subcuenta in cuenta.subcuentas.all():
            subcuenta_data = calcular_saldos(subcuenta, nivel + 1)
            subcuentas.append(subcuenta_data)

        return {
            'cuenta': cuenta,
            'saldo_inicial': saldo_inicial,
            'saldo_final': saldo_final,
            'total_debe': total_debe,
            'total_haber': total_haber,
            'detalles': detalles,
            'subcuentas': subcuentas
        }

    def buscar_en_cuentas(cuentas_data, search_query):
        """
        Función recursiva para buscar en cuentas y subcuentas.
        """
        resultados = []
        for cuenta in cuentas_data:
            if search_query.lower() in cuenta['cuenta'].nombrePlanCuenta.lower() or \
               search_query.lower() in cuenta['cuenta'].codigoPlanCuenta.lower() or \
               any(
                   search_query.lower() in str(detalle.get('debe', '')).lower() or
                   search_query.lower() in str(detalle.get('haber', '')).lower() or
                   search_query.lower() in str(detalle.get('saldo', '')).lower() or
                   search_query.lower() in detalle.get('concepto', '').lower()
                   for detalle in cuenta['detalles']
               ):
                resultados.append(cuenta)

            # Buscar en subcuentas
            subcuentas_resultados = buscar_en_cuentas(cuenta.get('subcuentas', []), search_query)
            resultados.extend(subcuentas_resultados)

        return resultados

    # Calcular saldos para todas las cuentas principales
    cuentas_data = [calcular_saldos(cuenta) for cuenta in cuentas]

    print("=== Datos de cuentas antes del filtro ===")
    for cuenta in cuentas_data:
        print(f"Cuenta: {cuenta['cuenta'].codigoPlanCuenta} - {cuenta['cuenta'].nombrePlanCuenta}")
        for detalle in cuenta['detalles']:
            print(f"  Detalle: Fecha: {detalle['fecha']}, Concepto: {detalle['concepto']}, Beneficiario: {detalle['beneficiario']}, Debe: {detalle['debe']}, Haber: {detalle['haber']}, Saldo: {detalle['saldo']}")

    if search_query:
        print(f"=== Búsqueda: {search_query} ===")
        cuentas_data = buscar_en_cuentas(cuentas_data, search_query)
        print(f"=== Resultados encontrados: {len(cuentas_data)} ===")
        for cuenta in cuentas_data:
            print(f"Cuenta: {cuenta['cuenta'].codigoPlanCuenta} - {cuenta['cuenta'].nombrePlanCuenta}")
            for detalle in cuenta['detalles']:
                print(f"  Detalle: Fecha: {detalle['fecha']}, Concepto: {detalle['concepto']}, Beneficiario: {detalle['beneficiario']}, Debe: {detalle['debe']}, Haber: {detalle['haber']}, Saldo: {detalle['saldo']}")

    page_number = request.GET.get('page', 1)
    items_per_page = 10

    cuentas_data_paginadas = paginate_cuentas_data(cuentas_data, page_number, items_per_page)

    context = {
        'cuentas_data': cuentas_data_paginadas['page_data'],
        'search_query': search_query,
        'periodos': periodoContable.objects.all(),
        'periodo_seleccionado': periodo,
        'total_debe': global_total_debe,
        'total_haber': global_total_haber
    }

    return render(request, 'librosContables/libroMayor.html', context)

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


def paginate_cuentas_data(cuentas_data, page_number, items_per_page):
    """
    Función para paginar los datos de cuentas tratándolos como una lista plana.
    Asegura que cada página comience con el encabezado del plan de cuenta correspondiente.
    También incluye registros relacionados de otras páginas para mostrarlos en un modal.
    """
    def flatten_cuenta(cuenta_data):
        flat_list = [{'tipo': 'cuenta', 'data': cuenta_data}]
        for subcuenta in cuenta_data.get('subcuentas', []):
            flat_list.extend(flatten_cuenta(subcuenta))  # Recursivamente agregar subcuentas
        for detalle in cuenta_data.get('detalles', []):
            flat_list.append({'tipo': 'detalle', 'data': detalle})  # Agregar detalles
        return flat_list

    flat_list = []
    for cuenta_data in cuentas_data:
        flat_list.extend(flatten_cuenta(cuenta_data))

    paginated_data = []
    current_page = []
    current_count = 0
    last_cuenta = None
    related_records = []  # Para almacenar registros relacionados de otras páginas

    for item in flat_list:
        if current_count == items_per_page:
            paginated_data.append(current_page)
            current_page = []
            current_count = 0

        if item['tipo'] == 'cuenta':
            last_cuenta = item['data']
            current_page.append(item)
            current_count += 1
        elif item['tipo'] == 'detalle':
            if current_count == 0 and last_cuenta:
                current_page.append({'tipo': 'cuenta', 'data': last_cuenta})
                current_count += 1

            # Verificar si el registro relacionado está en otra página
            if 'id_asiento' in item['data']:
                id_asiento = item['data']['id_asiento']
                for other_item in flat_list:
                    if (
                        other_item['tipo'] == 'detalle' and
                        other_item['data']['id_asiento'] == id_asiento and
                        other_item not in current_page
                    ):
                        related_records.append(other_item)

            current_page.append(item)
            current_count += 1

    if current_page:
        paginated_data.append(current_page)

    # Seleccionar la página solicitada
    paginator = Paginator(paginated_data, 1)  # Cada página contiene una lista de items
    current_page_data = paginator.get_page(page_number)

    # Incluir registros relacionados en el contexto
    return {
        'page_data': current_page_data,
        'related_records': related_records  # Registros relacionados para el modal
    }