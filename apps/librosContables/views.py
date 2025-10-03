import json
from django.shortcuts import render
from django.db.models import Sum
from apps.asientoContable.models import AsientoContable, DetalleAsiento
from apps.planCuenta.models import PlanCuenta
from django.core.paginator import Paginator
from django.db.models import Q
from apps.periodoContable.models import periodoContable

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
    Vista para generar el Libro Mayor con estructura jerárquica.
    Incluye buscador, filtro por período contable y paginación.
    """
    search_query = request.GET.get('search', '').strip()
    periodo_id = request.GET.get('periodo')

    if not periodo_id:
        periodo = periodoContable.objects.filter(estadoPeriodo=True).first()
    else:
        periodo = periodoContable.objects.filter(idPeriodo=periodo_id).first()

    if not periodo:
        return render(request, 'librosContables/libroMayor.html', {
            'error': 'No hay períodos contables disponibles.'
        })

    cuentas = PlanCuenta.objects.prefetch_related('subcuentas').filter(cuentaPadre__isnull=True).order_by('codigoPlanCuenta')
    print("Cuentas principales:", cuentas)

    # Variables globales para acumular totales
    global_total_debe = 0
    global_total_haber = 0

    def calcular_saldos(cuenta, saldo_inicial=0, nivel=0):
        """
        Función recursiva para calcular los saldos iniciales y finales de una cuenta y sus subcuentas.
        """
        nonlocal global_total_debe, global_total_haber
        
        indent = "  " * nivel
        print(f"{indent}Procesando cuenta: {cuenta.codigoPlanCuenta} - {cuenta.nombrePlanCuenta}")
        print(f"{indent}Saldo inicial recibido: {saldo_inicial}")

        movimientos = DetalleAsiento.objects.filter(
            idPlanCuenta=cuenta,
            idAsiento__idPeriodo=periodo
        ).order_by('idAsiento__fechaAsiento', 'idAsiento__numeroAsiento')

        print(f"{indent}Movimientos encontrados para la cuenta {cuenta.codigoPlanCuenta}: {len(movimientos)}")

        saldo = saldo_inicial
        detalles = []
        total_debe = 0
        total_haber = 0

        # VALIDACIÓN: Cuentas de grupo no deben tener movimientos directos
        if movimientos and cuenta.subcuentas.exists():
            print(f"⚠️  ADVERTENCIA: La cuenta {cuenta.codigoPlanCuenta} es un grupo pero tiene movimientos directos")
            print(f"⚠️  Esto viola la estructura contable venezolana")

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
            print(f"{indent}Procesando movimiento: Fecha={movimiento.idAsiento.fechaAsiento}, Concepto={movimiento.idAsiento.conceptoAsiento}, Debe={movimiento.debe}, Haber={movimiento.haber}")
            
            saldo_anterior = saldo
            saldo += movimiento.debe - movimiento.haber
            total_debe += movimiento.debe
            total_haber += movimiento.haber
            
            # Determinar naturaleza del saldo después de cada movimiento
            if saldo > 0:
                naturaleza = "Deudor"
            elif saldo < 0:
                naturaleza = "Acreedor"
            else:
                naturaleza = "Saldado"
                
            print(f"{indent}Saldo actualizado después del movimiento: {saldo} ({naturaleza})")
            
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
            
            detalles.append({
                'fecha': movimiento.idAsiento.fechaAsiento,
                'concepto': movimiento.idAsiento.conceptoAsiento,
                'debe': movimiento.debe,
                'haber': movimiento.haber,
                'saldo': saldo,
                'naturaleza': naturaleza,
                'id_asiento': movimiento.idAsiento.idAsiento,
                'movimientos_completos': movimientos_completos_json,
                'movimientos_completos_json': json.dumps(movimientos_completos_json)  # Añadido para el template
            })
        
        # Determinar naturaleza del saldo final después de todos los movimientos
        if saldo > 0:
            naturaleza_final = "Deudor"
        elif saldo < 0:
            naturaleza_final = "Acreedor"
        else:
            naturaleza_final = "Saldado"
            
        print(f"{indent}Saldo después de procesar movimientos: {saldo} ({naturaleza_final})")
        print(f"{indent}Total Débitos: {total_debe}, Total Créditos: {total_haber}")

        # SUMAR AL TOTAL GLOBAL (solo para cuentas de movimiento, no grupos)
        if not cuenta.subcuentas.exists():
            global_total_debe += total_debe
            global_total_haber += total_haber
            print(f"{indent}Sumando a total global: Débito={total_debe}, Crédito={total_haber}")
            print(f"{indent}Total global acumulado: Débito={global_total_debe}, Crédito={global_total_haber}")

        subcuentas = []
        saldo_final_subcuentas = 0
        for subcuenta in cuenta.subcuentas.all():
            print(f"{indent}Procesando subcuenta: {subcuenta.codigoPlanCuenta} - {subcuenta.nombrePlanCuenta}")
            subcuenta_data = calcular_saldos(subcuenta, 0, nivel + 1)
            saldo_final_subcuentas += subcuenta_data['saldo_final']
            subcuentas.append(subcuenta_data)

        # LÓGICA VENEZOLANA: Las cuentas de grupo suman sus subcuentas
        if subcuentas:
            saldo_final = saldo_final_subcuentas
            
            # Determinar naturaleza para cuenta grupo
            if saldo_final > 0:
                naturaleza_final = "Deudor"
            elif saldo_final < 0:
                naturaleza_final = "Acreedor"
            else:
                naturaleza_final = "Saldado"
                
            print(f"{indent}✓ Cuenta grupo - Saldo final: {saldo_final} ({naturaleza_final}) - Suma de {len(subcuentas)} subcuentas")
        else:
            saldo_final = saldo
            # naturaleza_final ya está calculada arriba
            
            # Validar consistencia según naturaleza de la cuenta
            codigo = cuenta.codigoPlanCuenta
            if codigo.startswith('1'):  # Activo
                if naturaleza_final == "Acreedor":
                    print(f"⚠️  ALERTA: Cuenta de activo {codigo} con saldo acreedor (anormal)")
            elif codigo.startswith(('2', '3')):  # Pasivo/Patrimonio
                if naturaleza_final == "Deudor":
                    print(f"⚠️  ALERTA: Cuenta de pasivo/patrimonio {codigo} con saldo deudor (anormal)")
            elif codigo.startswith('4'):  # Ingresos
                if naturaleza_final == "Deudor":
                    print(f"⚠️  ALERTA: Cuenta de ingreso {codigo} con saldo deudor (anormal)")
            elif codigo.startswith('5'):  # Gastos
                if naturaleza_final == "Acreedor":
                    print(f"⚠️  ALERTA: Cuenta de gasto {codigo} con saldo acreedor (anormal)")
            
            print(f"{indent}✓ Cuenta de movimiento - Saldo final: {saldo_final} ({naturaleza_final})")

        # Preparar datos JSON para la cuenta completa
        movimientos_json = []
        for detalle in detalles:
            movimientos_json.append({
                'id_asiento': detalle['id_asiento'],
                'movimientos_completos': detalle['movimientos_completos']
            })

        return {
            'cuenta': cuenta,
            'saldo_inicial': saldo_inicial,
            'saldo_final': saldo_final,
            'naturaleza_final': naturaleza_final,
            'total_debe': total_debe,
            'total_haber': total_haber,
            'detalles': detalles,
            'movimientos_json': json.dumps(movimientos_json),  # Añadido para el template
            'subcuentas': subcuentas,
            'tiene_movimientos_invalidos': bool(movimientos and subcuentas)
        }

    # Calcular saldos para todas las cuentas principales
    cuentas_data = [calcular_saldos(cuenta) for cuenta in cuentas]
    
    # Ya no necesitamos este bucle porque los totales se acumularon durante la recursión
    # total_general_debe = 0
    # total_general_haber = 0
    # for cuenta_data in cuentas_data:
    #     total_general_debe += cuenta_data['total_debe']
    #     total_general_haber += cuenta_data['total_haber']
    #     print(f"Totales generales - Débito: {total_general_debe}, Crédito: {total_general_haber}")

    # Verificar inconsistencias estructurales
    cuentas_con_problemas = [c for c in cuentas_data if c['tiene_movimientos_invalidos']]
    if cuentas_con_problemas:
        print("🚨 CUENTAS CON ESTRUCTURA INCONSISTENTE:")
        for cuenta in cuentas_con_problemas:
            print(f"   - {cuenta['cuenta'].codigoPlanCuenta} - {cuenta['cuenta'].nombrePlanCuenta}")

    if search_query:
        cuentas_data = [
            cuenta for cuenta in cuentas_data
            if search_query.lower() in cuenta['cuenta'].nombrePlanCuenta.lower() or
               search_query.lower() in cuenta['cuenta'].codigoPlanCuenta.lower() or
               any(search_query.lower() in detalle['concepto'].lower() for detalle in cuenta['detalles'])
        ]

    page_number = request.GET.get('page', 1)
    items_per_page = 10

    cuentas_data_paginadas = paginate_cuentas_data(cuentas_data, page_number, items_per_page)

    # Debugging: Print the paginated data and related records
    print("=== Debugging Information ===")
    print("Cuentas Data Paginadas (Page Data):")
    for page in cuentas_data_paginadas['page_data']:
        for item in page:
            print(item)

    print("Related Records:")
    for record in cuentas_data_paginadas['related_records']:
        print(record)
    print("=============================")

    # Filtrar registros relacionados para evitar duplicados
    unique_related_records = []
    seen_ids = set()
    for record in cuentas_data_paginadas['related_records']:
        if record['data']['id_asiento'] not in seen_ids:
            unique_related_records.append(record)
            seen_ids.add(record['data']['id_asiento'])

    context = {
        'cuentas_data': cuentas_data_paginadas['page_data'],
        'related_records': unique_related_records,  # Usar registros únicos
        'search_query': search_query,
        'periodos': periodoContable.objects.all(),
        'periodo_seleccionado': periodo,
        'inconsistencias': len(cuentas_con_problemas) > 0,
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