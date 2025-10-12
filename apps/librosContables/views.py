import json
from django.shortcuts import get_object_or_404, render
from django.db.models import Sum
from apps.asientoContable.models import AsientoContable, DetalleAsiento
from apps.planCuenta.models import PlanCuenta
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
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

    # Obtener el objeto del período contable seleccionado
    periodo_seleccionado = None
    if periodo_id:
        periodo_seleccionado = periodoContable.objects.filter(idPeriodo=periodo_id).first()

    return render(request, 'librosContables/libroDiario.html', {
        'asientos': page_obj,
        'total_debe': totales['total_debe'] or 0,
        'total_haber': totales['total_haber'] or 0,
        'periodos': periodoContable.objects.all(),  # Lista de períodos contables
        'periodo_seleccionado': periodo_seleccionado  # Objeto del período seleccionado
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
    Vista optimizada para generar el Balance de Cuentas con saldo anterior.
    """
    periodo_id = request.GET.get('periodo')
    page_number = request.GET.get('page', 1)
    items_per_page = 20

    search_query = request.GET.get('search', '').strip()

    # Obtener período contable
    if periodo_id:
        periodo = get_object_or_404(periodoContable, idPeriodo=periodo_id)
    else:
        periodo = periodoContable.objects.filter(estadoPeriodo=True).first()
        if not periodo:
            return render(request, 'librosContables/balanceCuentas.html', {
                'error': 'No hay períodos contables disponibles.',
                'periodos': periodoContable.objects.all().order_by('-fechaInicioPeriodo'),
                'cuentas_data': [],
                'periodo_seleccionado': None
            })

    # Obtener el período anterior
    periodo_anterior = periodoContable.objects.filter(
        fechaFinPeriodo__lt=periodo.fechaInicioPeriodo
    ).order_by('-fechaFinPeriodo').first()

    # OBTENER TODOS LOS MOVIMIENTOS DEL PERÍODO ACTUAL EN UNA SOLA CONSULTA
    movimientos_actual = DetalleAsiento.objects.filter(
        idAsiento__idPeriodo=periodo
    ).select_related('idPlanCuenta').values(
        'idPlanCuenta',
        'idPlanCuenta__codigoPlanCuenta',
        'idPlanCuenta__nombrePlanCuenta',
        'idPlanCuenta__cuentaPadre_id'
    ).annotate(
        total_debe=Sum('debe'),
        total_haber=Sum('haber')
    )

    print("=== Movimientos del periodo actual ===")
    for mov in movimientos_actual:
        print(f"Cuenta: {mov['idPlanCuenta__codigoPlanCuenta']} - {mov['idPlanCuenta__nombrePlanCuenta']}, Debe: {mov['total_debe']}, Haber: {mov['total_haber']}")

    # OBTENER MOVIMIENTOS DEL PERÍODO ANTERIOR (SALDO ANTERIOR)
    movimientos_anterior = {}
    if periodo_anterior:
        movimientos_anterior_query = DetalleAsiento.objects.filter(
            idAsiento__idPeriodo=periodo_anterior
        ).select_related('idPlanCuenta').values(
            'idPlanCuenta'
        ).annotate(
            total_debe=Sum('debe'),
            total_haber=Sum('haber')
        )

        print("=== Movimientos del periodo anterior ===")
        for mov in movimientos_anterior_query:
            cuenta_id = mov['idPlanCuenta']
            saldo_anterior = (mov['total_debe'] or 0) - (mov['total_haber'] or 0)
            movimientos_anterior[cuenta_id] = saldo_anterior
            print(f"Cuenta ID: {cuenta_id}, Saldo anterior: {saldo_anterior}")

    # Crear diccionario de saldos por cuenta ID
    saldos_por_cuenta = {}
    for mov in movimientos_actual:
        cuenta_id = mov['idPlanCuenta']
        saldo_anterior = movimientos_anterior.get(cuenta_id, 0)
        total_debe = mov['total_debe'] or 0
        total_haber = mov['total_haber'] or 0
        saldo_actual = total_debe - total_haber
        saldo_acumulado = saldo_anterior + saldo_actual

        print(f"Cuenta: {mov['idPlanCuenta__codigoPlanCuenta']} - {mov['idPlanCuenta__nombrePlanCuenta']}, "
              f"Debe: {total_debe}, Haber: {total_haber}, Saldo anterior: {saldo_anterior}, "
              f"Saldo actual: {saldo_actual}, Saldo acumulado: {saldo_acumulado}")

        saldos_por_cuenta[cuenta_id] = {
            'total_debe': total_debe,
            'total_haber': total_haber,
            'saldo_actual': saldo_actual,
            'saldo_anterior': saldo_anterior,
            'saldo_acumulado': saldo_acumulado,
            'codigo': mov['idPlanCuenta__codigoPlanCuenta'],
            'nombre': mov['idPlanCuenta__nombrePlanCuenta'],
            'cuentaPadre_id': mov['idPlanCuenta__cuentaPadre_id']
        }

    # OBTENER TODAS LAS CUENTAS EN ORDEN JERÁRQUICO
    todas_las_cuentas = PlanCuenta.objects.all().select_related('cuentaPadre').order_by('codigoPlanCuenta')

    # Filtrar cuentas por el término de búsqueda
    if search_query:
        todas_las_cuentas = todas_las_cuentas.filter(
            Q(codigoPlanCuenta__icontains=search_query) |
            Q(nombrePlanCuenta__icontains=search_query)
        )

    # Crear estructuras para el árbol
    cuentas_por_id = {cuenta.idPlanCuenta: cuenta for cuenta in todas_las_cuentas}
    hijos_por_padre = {}

    for cuenta in todas_las_cuentas:
        padre_id = cuenta.cuentaPadre_id if cuenta.cuentaPadre else None
        if padre_id not in hijos_por_padre:
            hijos_por_padre[padre_id] = []
        hijos_por_padre[padre_id].append(cuenta)

    # FUNCIÓN RECURSIVA OPTIMIZADA CON SALDO ANTERIOR
    def construir_arbol_cuentas(cuenta_padre_id=None, nivel=0):
        if cuenta_padre_id not in hijos_por_padre:
            return []

        resultado = []
        for cuenta in hijos_por_padre[cuenta_padre_id]:
            # Obtener saldos de esta cuenta
            saldo_data = saldos_por_cuenta.get(cuenta.idPlanCuenta, {
                'total_debe': 0,
                'total_haber': 0,
                'saldo_actual': 0,
                'saldo_anterior': 0,
                'saldo_acumulado': 0
            })

            # Obtener subcuentas recursivamente
            subcuentas = construir_arbol_cuentas(cuenta.idPlanCuenta, nivel + 1)

            # Calcular totales acumulados (incluyendo subcuentas)
            total_debe_acumulado = saldo_data['total_debe']
            total_haber_acumulado = saldo_data['total_haber']
            saldo_anterior_acumulado = saldo_data['saldo_anterior']
            saldo_actual_acumulado = saldo_data['saldo_actual']
            saldo_acumulado_total = saldo_data['saldo_acumulado']

            # Acumular de las subcuentas
            for subcuenta in subcuentas:
                total_debe_acumulado += subcuenta['total_debe_acumulado']
                total_haber_acumulado += subcuenta['total_haber_acumulado']
                saldo_anterior_acumulado += subcuenta['saldo_anterior_acumulado']
                saldo_actual_acumulado += subcuenta['saldo_actual_acumulado']
                saldo_acumulado_total += subcuenta['saldo_acumulado_total']

            print(f"[Nivel {nivel}] Cuenta: {cuenta.codigoPlanCuenta} - {cuenta.nombrePlanCuenta}, "
                  f"Debe acumulado: {total_debe_acumulado}, Haber acumulado: {total_haber_acumulado}, "
                  f"Saldo anterior acumulado: {saldo_anterior_acumulado}, "
                  f"Saldo actual acumulado: {saldo_actual_acumulado}, "
                  f"Saldo acumulado total: {saldo_acumulado_total}")

            cuenta_info = {
                'cuenta': cuenta,
                'nivel': nivel,
                'total_debe': saldo_data['total_debe'],
                'total_haber': saldo_data['total_haber'],
                'saldo_anterior': saldo_data['saldo_anterior'],
                'saldo_actual': saldo_data['saldo_actual'],
                'saldo_acumulado': saldo_data['saldo_acumulado'],
                'total_debe_acumulado': total_debe_acumulado,
                'total_haber_acumulado': total_haber_acumulado,
                'saldo_anterior_acumulado': saldo_anterior_acumulado,
                'saldo_actual_acumulado': saldo_actual_acumulado,
                'saldo_acumulado_total': saldo_acumulado_total,
                'subcuentas': subcuentas,
                'tiene_subcuentas': len(subcuentas) > 0,
                'es_cuenta_principal': nivel == 0
            }
            resultado.append(cuenta_info)

        return resultado

    # Construir el árbol completo empezando por las cuentas principales (nivel 0)
    arbol_cuentas = construir_arbol_cuentas(None, 0)

    # Aplanar el árbol para paginación manteniendo la jerarquía visual
    cuentas_aplanadas = []
    def aplanar_arbol(arbol, lista_plana):
        for item in arbol:
            lista_plana.append(item)
            aplanar_arbol(item['subcuentas'], lista_plana)

    aplanar_arbol(arbol_cuentas, cuentas_aplanadas)

    # Calcular totales generales del balance
    total_general_debe = sum(item['total_debe_acumulado'] for item in arbol_cuentas)
    total_general_haber = sum(item['total_haber_acumulado'] for item in arbol_cuentas)
    total_general_saldo_anterior = sum(item['saldo_anterior_acumulado'] for item in arbol_cuentas)
    total_general_saldo_actual = sum(item['saldo_actual_acumulado'] for item in arbol_cuentas)
    total_general_saldo_acumulado = sum(item['saldo_acumulado_total'] for item in arbol_cuentas)

    print("=== Totales generales del balance ===")
    print(f"Total Debe: {total_general_debe}")
    print(f"Total Haber: {total_general_haber}")
    print(f"Total Saldo Anterior: {total_general_saldo_anterior}")
    print(f"Total Saldo Actual: {total_general_saldo_actual}")
    print(f"Total Saldo Acumulado: {total_general_saldo_acumulado}")

    # PAGINACIÓN
    paginator = Paginator(cuentas_aplanadas, items_per_page)

    try:
        cuentas_paginadas = paginator.get_page(page_number)
    except PageNotAnInteger:
        cuentas_paginadas = paginator.get_page(1)
    except EmptyPage:
        cuentas_paginadas = paginator.get_page(paginator.num_pages)

    context = {
        'cuentas_data': cuentas_paginadas,
        'periodos': periodoContable.objects.all().order_by('-fechaInicioPeriodo'),
        'periodo_seleccionado': periodo,
        'periodo_anterior': periodo_anterior,
        'total_general_debe': total_general_debe,
        'total_general_haber': total_general_haber,
        'total_general_saldo_anterior': total_general_saldo_anterior,
        'total_general_saldo_actual': total_general_saldo_actual,
        'total_general_saldo_acumulado': total_general_saldo_acumulado,
        'paginator': paginator,
        'mostrando_total': f"Mostrando {len(cuentas_aplanadas)} cuentas"
    }

    return render(request, 'librosContables/balanceCuentas.html', context)
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