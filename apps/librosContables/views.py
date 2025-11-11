import decimal
import json
from django.shortcuts import get_object_or_404, render
from django.db.models import Sum
from apps.asientoContable.models import AsientoContable, DetalleAsiento
from apps.planCuenta.models import PlanCuenta
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.db.models import Q
from apps.periodoContable.models import periodoContable
from apps.saldoContable.models import SaldoContable  # Importar modelo SaldoContable
from apps.home.models import Configuracion, Moneda, Tasa
from apps.factura.models import Pago

import os
import io
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter, landscape
from reportlab.platypus import Table, TableStyle, SimpleDocTemplate
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import Paragraph, Spacer
from reportlab.lib.units import inch
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from django.http import HttpResponse
from datetime import datetime




def libro_diario(request):
    """
    Vista para generar el Libro Diario.
    Muestra los asientos contables y sus detalles en orden cronológico.
    """
    search_query = request.GET.get('search', '').strip()  # Obtener el término de búsqueda
    start_date = request.GET.get('start_date')  # Obtener la fecha de inicio
    end_date = request.GET.get('end_date')  # Obtener la fecha de fin
    periodo_id = request.GET.get('periodo')  # Obtener el ID del período contable
     # Usar la moneda con idMoneda = 1 en lugar de la configuracion
    moneda_nacional = Moneda.objects.filter(idMoneda=1).first()
    simbolo = moneda_nacional.simboloMoneda if moneda_nacional and getattr(moneda_nacional, 'simboloMoneda', None) else 'Bs'
    print(f"[libro_mayor] Moneda nacional seleccionada: id=1 simbolo={simbolo}")

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

    def convertir_a_moneda_nacional(detalle_asiento):
        """
        Convierte los montos de un detalle asiento a la moneda nacional.
        Si el detalle tiene idMoneda=1, no necesita conversión.
        Si tiene otro idMoneda, busca la tasa de cambio a través del pago relacionado.
        """
        # Si la moneda es la nacional (idMoneda=1), no hay conversión necesaria
        if detalle_asiento.idMoneda_id == 1:
            return {
                'debe': detalle_asiento.debe,
                'haber': detalle_asiento.haber,
                'tasa_aplicada': decimal.Decimal('1.00')
            }
        
        # Si tiene moneda diferente a 1, buscar el pago relacionado
        pago = Pago.objects.filter(idAsiento=detalle_asiento.idAsiento).first()
        
        if pago and pago.idTasa:
            # Obtener la tasa de cambio del pago
            tasa_cambio = Tasa.objects.filter(idTasa=pago.idTasa_id).first()
            if tasa_cambio and hasattr(tasa_cambio, 'montoTasa'):
                # Convertir la tasa del formato español
                try:
                    # Manejar formato español: "10.800,23" -> 10800.23
                    tasa_str = str(tasa_cambio.montoTasa).replace('.', '').replace(',', '.')
                    tasa_valor = decimal.Decimal(tasa_str)
                except (decimal.InvalidOperation, ValueError):
                    tasa_valor = decimal.Decimal('1.00')
                
                # Convertir los montos usando la tasa de cambio
                return {
                    'debe': detalle_asiento.debe * tasa_valor,
                    'haber': detalle_asiento.haber * tasa_valor,
                    'tasa_aplicada': tasa_valor
                }
        
        # Si no se encuentra tasa de cambio, usar los valores originales
        return {
            'debe': detalle_asiento.debe,
            'haber': detalle_asiento.haber,
            'tasa_aplicada': decimal.Decimal('1.00')
        }

    def formatear_a_dos_decimales(valor):
        """
        Formatea un valor Decimal a 2 decimales para mostrar en el frontend.
        Los cálculos internos mantienen máxima precisión.
        """
        if isinstance(valor, decimal.Decimal):
            return valor.quantize(decimal.Decimal('0.01'), rounding=decimal.ROUND_HALF_UP)
        return decimal.Decimal(str(valor)).quantize(decimal.Decimal('0.01'), rounding=decimal.ROUND_HALF_UP)

    # Procesar asientos para convertir a moneda nacional
    asientos_procesados = []
    total_debe_global = decimal.Decimal('0.00')
    total_haber_global = decimal.Decimal('0.00')

    for asiento in asientos:
        detalles_procesados = []
        total_debe_asiento = decimal.Decimal('0.00')
        total_haber_asiento = decimal.Decimal('0.00')
        
        for detalle in asiento.detalles.all():
            # Convertir montos a moneda nacional
            montos_convertidos = convertir_a_moneda_nacional(detalle)
            debe_convertido = montos_convertidos['debe']
            haber_convertido = montos_convertidos['haber']
            
            # Acumular totales con máxima precisión
            total_debe_asiento += debe_convertido
            total_haber_asiento += haber_convertido
            total_debe_global += debe_convertido
            total_haber_global += haber_convertido
            
            # Formatear a 2 decimales solo para display
            detalles_procesados.append({
                'id': detalle.idDetalle,
                'cuenta': detalle.idPlanCuenta,
                'debe': formatear_a_dos_decimales(debe_convertido),
                'haber': formatear_a_dos_decimales(haber_convertido),
                'moneda_original': detalle.idMoneda_id,
                'tasa_aplicada': formatear_a_dos_decimales(montos_convertidos['tasa_aplicada'])
            })
        
        asientos_procesados.append({
            'id': asiento.idAsiento,
            'numeroAsiento': asiento.numeroAsiento,
            'fechaAsiento': asiento.fechaAsiento,
            'conceptoAsiento': asiento.conceptoAsiento,
            'periodo': asiento.idPeriodo,
            'detalles': detalles_procesados,
            'total_debe': formatear_a_dos_decimales(total_debe_asiento),
            'total_haber': formatear_a_dos_decimales(total_haber_asiento)
        })

    # Paginación con asientos procesados
    paginator = Paginator(asientos_procesados, 10)  # 10 asientos por página
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    print("=== Libro Diario: Datos de Asientos (Moneda Nacional) ===")
    for asiento in asientos_procesados:
        print(f"Asiento #{asiento['numeroAsiento']} | Fecha: {asiento['fechaAsiento']} | Concepto: {asiento['conceptoAsiento']}")
        for detalle in asiento['detalles']:
            print(f"  Cuenta: {detalle['cuenta'].codigoPlanCuenta} - {detalle['cuenta'].nombrePlanCuenta} | Debe: {detalle['debe']} | Haber: {detalle['haber']} | Moneda Original: {detalle['moneda_original']} | Tasa: {detalle['tasa_aplicada']}")
        print(f"  Total Asiento - Debe: {asiento['total_debe']} | Haber: {asiento['total_haber']}")
    print(f"Total Global - Debe: {formatear_a_dos_decimales(total_debe_global)} | Haber: {formatear_a_dos_decimales(total_haber_global)}")
    print("=======================================")

    # Obtener el objeto del período contable seleccionado
    periodo_seleccionado = None
    if periodo_id:
        periodo_seleccionado = periodoContable.objects.filter(idPeriodo=periodo_id).first()

    return render(request, 'librosContables/libroDiario.html', {
        'asientos': page_obj,
        'total_debe': formatear_a_dos_decimales(total_debe_global),
        'total_haber': formatear_a_dos_decimales(total_haber_global),
        'periodos': periodoContable.objects.all(),  # Lista de períodos contables
        'periodo_seleccionado': periodo_seleccionado,  # Objeto del período seleccionado
        'search_query': search_query,
        'simbolo': simbolo,
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
        # Obtener símbolo de la moneda desde la configuración
        # Usar la moneda con idMoneda = 1 en lugar de la configuracion
        moneda_nacional = Moneda.objects.filter(idMoneda=1).first()
        simbolo = moneda_nacional.simboloMoneda if moneda_nacional and getattr(moneda_nacional, 'simboloMoneda', None) else 'Bs'
        print(f"[libro_mayor] Moneda nacional seleccionada: id=1 simbolo={simbolo}")

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
        global_total_debe = decimal.Decimal('0.00')
        global_total_haber = decimal.Decimal('0.00')

        def convertir_formato_numero(valor):
            """
            Convierte un string en formato español (1.234,56) a Decimal para máxima precisión.
            Maneja diferentes tipos de entrada.
            """
            if valor is None:
                return decimal.Decimal('0.00')
            
            # Si ya es numérico, retornar como Decimal
            if isinstance(valor, (int, float, decimal.Decimal)):
                return decimal.Decimal(str(valor)).quantize(decimal.Decimal('0.0000000001'))
            
            # Si es string, convertir del formato español
            if isinstance(valor, str):
                # Remover puntos de separación de miles y reemplazar coma decimal por punto
                valor_limpio = valor.strip().replace('.', '').replace(',', '.')
                try:
                    return decimal.Decimal(valor_limpio).quantize(decimal.Decimal('0.0000000001'))
                except (decimal.InvalidOperation, ValueError):
                    # Si falla la conversión, intentar directamente
                    try:
                        return decimal.Decimal(valor).quantize(decimal.Decimal('0.0000000001'))
                    except (decimal.InvalidOperation, ValueError):
                        return decimal.Decimal('0.00')
            
            # Para cualquier otro tipo, intentar conversión directa
            try:
                return decimal.Decimal(str(valor)).quantize(decimal.Decimal('0.0000000001'))
            except (decimal.InvalidOperation, ValueError, TypeError):
                return decimal.Decimal('0.00')

        def formatear_a_dos_decimales(valor):
            """
            Formatea un valor Decimal a 2 decimales para mostrar en el frontend.
            Los cálculos internos mantienen máxima precisión.
            """
            if isinstance(valor, decimal.Decimal):
                return float(valor.quantize(decimal.Decimal('0.01'), rounding=decimal.ROUND_HALF_UP))
            return float(decimal.Decimal(str(valor)).quantize(decimal.Decimal('0.01'), rounding=decimal.ROUND_HALF_UP))

        def convertir_a_moneda_nacional(detalle_asiento):
            """
            Convierte los montos de un detalle asiento a la moneda nacional.
            Si el detalle tiene idMoneda=1, no necesita conversión.
            Si tiene otro idMoneda, busca la tasa de cambio a través del pago relacionado.
            """
            # Convertir valores a Decimal usando el formato correcto (máxima precisión)
            debe_original = convertir_formato_numero(detalle_asiento.debe)
            haber_original = convertir_formato_numero(detalle_asiento.haber)
            moneda_origen = getattr(detalle_asiento, 'idMoneda_id', None)
            print(f"[convertir_a_moneda_nacional] DetalleAsiento idAsiento={detalle_asiento.idAsiento.idAsiento if detalle_asiento.idAsiento else 'N/A'} "
                  f"moneda_origen={moneda_origen} debe_original={debe_original} haber_original={haber_original}")

            # Si la moneda es la nacional (idMoneda=1), no hay conversión necesaria
            if moneda_origen == 1:
                print("[convertir_a_moneda_nacional] Moneda origen es nacional (1). No se aplica tasa. Resultado = original")
                return {
                    'debe': debe_original,
                    'haber': haber_original,
                    'tasa_aplicada': decimal.Decimal('1.00'),
                    'operacion': 'none'
                }
            
            # Si tiene moneda diferente a 1, buscar el pago relacionado
            pago = Pago.objects.filter(idAsiento=detalle_asiento.idAsiento).first()
            if pago:
                print(f"[convertir_a_moneda_nacional] Pago encontrado para asiento id={detalle_asiento.idAsiento.idAsiento} pago.idTasa={getattr(pago, 'idTasa_id', None)}")
            else:
                print(f"[convertir_a_moneda_nacional] No se encontró Pago para asiento id={detalle_asiento.idAsiento.idAsiento if detalle_asiento.idAsiento else 'N/A'}")

            if pago and pago.idTasa:
                # Obtener la tasa de cambio del pago
                tasa_cambio = Tasa.objects.filter(idTasa=pago.idTasa_id).first()
                if tasa_cambio and hasattr(tasa_cambio, 'montoTasa'):
                    # Convertir la tasa del formato español con máxima precisión
                    tasa_valor = convertir_formato_numero(tasa_cambio.montoTasa)
                    print(f"[convertir_a_moneda_nacional] Tasa encontrada id={tasa_cambio.idTasa} montoTasa={tasa_cambio.montoTasa} -> tasa_valor={tasa_valor}")

                    # Convertir los montos usando la tasa de cambio (máxima precisión)
                    debe_conv = debe_original * tasa_valor
                    haber_conv = haber_original * tasa_valor
                    print(f"[convertir_a_moneda_nacional] Operacion: multiplicacion. debe: {debe_original} * {tasa_valor} = {debe_conv}; "
                          f"haber: {haber_original} * {tasa_valor} = {haber_conv}")
                    return {
                        'debe': debe_conv,
                        'haber': haber_conv,
                        'tasa_aplicada': tasa_valor,
                        'operacion': 'multiply'
                    }
                else:
                    print("[convertir_a_moneda_nacional] Pago asociado pero no se encontró tasa válida. Se usan valores originales.")
            
            # Si no se encuentra tasa de cambio, usar los valores originales
            print("[convertir_a_moneda_nacional] No se aplicó tasa. Resultado = original")
            return {
                'debe': debe_original,
                'haber': haber_original,
                'tasa_aplicada': decimal.Decimal('1.00'),
                'operacion': 'none'
            }

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

            saldo_inicial = decimal.Decimal('0.00')
            saldo_final = saldo_inicial
            total_debe = decimal.Decimal('0.00')
            total_haber = decimal.Decimal('0.00')
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
                # Convertir montos a moneda nacional (máxima precisión)
                montos_convertidos = convertir_a_moneda_nacional(movimiento)
                debe_convertido = montos_convertidos['debe']  # Decimal con máxima precisión
                haber_convertido = montos_convertidos['haber']  # Decimal con máxima precisión
                tasa_aplicada = montos_convertidos['tasa_aplicada']  # Decimal con máxima precisión
                operacion = montos_convertidos.get('operacion', 'unknown')

                saldo_anterior = saldo_final
                saldo_final += debe_convertido - haber_convertido
                total_debe += debe_convertido
                total_haber += haber_convertido

                print(f"[calcular_saldos] Cuenta {cuenta.codigoPlanCuenta} movimiento asiento_id={movimiento.idAsiento.idAsiento} "
                      f"moneda_original={movimiento.idMoneda_id} operacion={operacion} tasa={tasa_aplicada} "
                      f"debe_conv={debe_convertido} haber_conv={haber_convertido} saldo_anterior={saldo_anterior} saldo_final={saldo_final}")

                # Obtener movimientos relacionados para este asiento específico
                movimientos_asiento_completo = movimientos_relacionados.get(movimiento.idAsiento.idAsiento, [])

                # Preparar movimientos completos para JSON (convertidos a 2 decimales para frontend)
                movimientos_completos_json = []
                for mov_rel in movimientos_asiento_completo:
                    if mov_rel.idPlanCuenta.codigoPlanCuenta != cuenta.codigoPlanCuenta:  # Excluir el movimiento actual
                        # Convertir también los movimientos relacionados
                        montos_rel_convertidos = convertir_a_moneda_nacional(mov_rel)
                        movimientos_completos_json.append({
                            'cuenta': mov_rel.idPlanCuenta.codigoPlanCuenta + ' - ' + mov_rel.idPlanCuenta.nombrePlanCuenta,
                            'debe': formatear_a_dos_decimales(montos_rel_convertidos['debe']),
                            'haber': formatear_a_dos_decimales(montos_rel_convertidos['haber'])
                        })
                        print(f"[calcular_saldos]   Movimiento relacionado asiento={mov_rel.idAsiento.idAsiento} cuenta={mov_rel.idPlanCuenta.codigoPlanCuenta} "
                              f"moneda={mov_rel.idMoneda_id} debe_rel={montos_rel_convertidos['debe']} haber_rel={montos_rel_convertidos['haber']} tasa_rel={montos_rel_convertidos['tasa_aplicada']}")

                # Obtener beneficiario desde el pago relacionado
                beneficiario = None
                pago = Pago.objects.filter(idAsiento=movimiento.idAsiento).first()
                if pago and pago.idNota:
                    nota = pago.idNota
                    if nota.idPersona:
                        beneficiario = f"{nota.idPersona.cedula} - {nota.idPersona.nombres} {nota.idPersona.apellidos}"
                    elif nota.idEmpresa:
                        beneficiario = f"{nota.idEmpresa.rifEmpresa} - {nota.idEmpresa.nombreEmpresa}"

                # Formatear a 2 decimales solo para el frontend
                detalles.append({
                    'fecha': movimiento.idAsiento.fechaAsiento,
                    'concepto': movimiento.idAsiento.conceptoAsiento,
                    'beneficiario': beneficiario,
                    'debe': formatear_a_dos_decimales(debe_convertido),
                    'haber': formatear_a_dos_decimales(haber_convertido),
                    'saldo': formatear_a_dos_decimales(saldo_final),
                    'id_asiento': movimiento.idAsiento.idAsiento,
                    'movimientos_completos': movimientos_completos_json,
                    'moneda_original': movimiento.idMoneda_id,  # Para debugging
                    'tasa_aplicada': formatear_a_dos_decimales(tasa_aplicada)  # Para ver qué tasa se usó
                })

            # Sumar al total global (manteniendo máxima precisión)
            global_total_debe += total_debe
            global_total_haber += total_haber
            print(f"[calcular_saldos] Totales cuenta {cuenta.codigoPlanCuenta}: total_debe={total_debe}, total_haber={total_haber}. "
                  f"Acumulado global_debe={global_total_debe}, global_haber={global_total_haber}")

            subcuentas = []
            for subcuenta in cuenta.subcuentas.all():
                subcuenta_data = calcular_saldos(subcuenta, nivel + 1)
                subcuentas.append(subcuenta_data)

            return {
                'cuenta': cuenta,
                'saldo_inicial': formatear_a_dos_decimales(saldo_inicial),
                'saldo_final': formatear_a_dos_decimales(saldo_final),
                'total_debe': formatear_a_dos_decimales(total_debe),
                'total_haber': formatear_a_dos_decimales(total_haber),
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
                print(f"  Detalle: Fecha: {detalle['fecha']}, Concepto: {detalle['concepto']}, Beneficiario: {detalle['beneficiario']}, "
                      f"Debe: {detalle['debe']}, Haber: {detalle['haber']}, Saldo: {detalle['saldo']}, "
                      f"Moneda Original: {detalle['moneda_original']}, Tasa aplicada: {detalle['tasa_aplicada']}")

        if search_query:
            print(f"=== Búsqueda: {search_query} ===")
            cuentas_data = buscar_en_cuentas(cuentas_data, search_query)
            print(f"=== Resultados encontrados: {len(cuentas_data)} ===")
            for cuenta in cuentas_data:
                print(f"Cuenta: {cuenta['cuenta'].codigoPlanCuenta} - {cuenta['cuenta'].nombrePlanCuenta}")
                for detalle in cuenta['detalles']:
                    print(f"  Detalle: Fecha: {detalle['fecha']}, Concepto: {detalle['concepto']}, Beneficiario: {detalle['beneficiario']}, "
                          f"Debe: {detalle['debe']}, Haber: {detalle['haber']}, Saldo: {detalle['saldo']}")

        # Imprimir totales globales finales y en qué moneda están (moneda nacional id=1)
        print(f"[libro_mayor] Totales globales finales (en moneda nacional id=1 '{simbolo}'): total_debe={global_total_debe}, total_haber={global_total_haber}")

        page_number = request.GET.get('page', 1)
        items_per_page = 10

        cuentas_data_paginadas = paginate_cuentas_data(cuentas_data, page_number, items_per_page)

        # Formatear los totales globales a 2 decimales para el frontend
        context = {
            'cuentas_data': cuentas_data_paginadas['page_data'],
            'search_query': search_query,
            'periodos': periodoContable.objects.all(),
            'periodo_seleccionado': periodo,
            'total_debe': formatear_a_dos_decimales(global_total_debe),
            'total_haber': formatear_a_dos_decimales(global_total_haber),
            'simbolo': simbolo,
        }

        return render(request, 'librosContables/libroMayor.html', context)

def balance_cuentas(request):
    """
    Vista optimizada para generar el Balance de Cuentas con saldo anterior.
    """
    periodo_id = request.GET.get('periodo')
    page_number = request.GET.get('page', 1)
    items_per_page = 20
    # Usar la moneda con idMoneda = 1 en lugar de la configuracion
    moneda_nacional = Moneda.objects.filter(idMoneda=1).first()
    simbolo = moneda_nacional.simboloMoneda if moneda_nacional and getattr(moneda_nacional, 'simboloMoneda', None) else 'Bs'
    print(f"[libro_mayor] Moneda nacional seleccionada: id=1 simbolo={simbolo}")

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

    # Función para convertir formato de números
    def convertir_formato_numero(valor):
        """
        Convierte un string en formato español (1.234,56) a Decimal para máxima precisión.
        """
        if valor is None:
            return decimal.Decimal('0.00')
        
        if isinstance(valor, (int, float, decimal.Decimal)):
            return decimal.Decimal(str(valor)).quantize(decimal.Decimal('0.0000000001'))
        
        if isinstance(valor, str):
            valor_limpio = valor.strip().replace('.', '').replace(',', '.')
            try:
                return decimal.Decimal(valor_limpio).quantize(decimal.Decimal('0.0000000001'))
            except (decimal.InvalidOperation, ValueError):
                try:
                    return decimal.Decimal(valor).quantize(decimal.Decimal('0.0000000001'))
                except (decimal.InvalidOperation, ValueError):
                    return decimal.Decimal('0.00')
        
        try:
            return decimal.Decimal(str(valor)).quantize(decimal.Decimal('0.0000000001'))
        except (decimal.InvalidOperation, ValueError, TypeError):
            return decimal.Decimal('0.00')

    def formatear_a_dos_decimales(valor):
        """
        Formatea un valor Decimal a 2 decimales para mostrar en el frontend.
        """
        if isinstance(valor, decimal.Decimal):
            return float(valor.quantize(decimal.Decimal('0.01'), rounding=decimal.ROUND_HALF_UP))
        return float(decimal.Decimal(str(valor)).quantize(decimal.Decimal('0.01'), rounding=decimal.ROUND_HALF_UP))

    def convertir_a_moneda_nacional(detalle_asiento):
        """
        Convierte los montos de un detalle asiento a la moneda nacional.
        """
        # Convertir valores a Decimal usando el formato correcto
        debe_original = convertir_formato_numero(detalle_asiento.debe)
        haber_original = convertir_formato_numero(detalle_asiento.haber)
        
        # Si la moneda es la nacional (idMoneda=1), no hay conversión necesaria
        if detalle_asiento.idMoneda_id == 1:
            return {
                'debe': debe_original,
                'haber': haber_original
            }
        
        # Si tiene moneda diferente a 1, buscar el pago relacionado
        pago = Pago.objects.filter(idAsiento=detalle_asiento.idAsiento).first()
        
        if pago and pago.idTasa:
            # Obtener la tasa de cambio del pago
            tasa_cambio = Tasa.objects.filter(idTasa=pago.idTasa_id).first()
            if tasa_cambio and hasattr(tasa_cambio, 'montoTasa'):
                # Convertir la tasa del formato español
                tasa_valor = convertir_formato_numero(tasa_cambio.montoTasa)
                
                # Convertir los montos usando la tasa de cambio
                return {
                    'debe': debe_original * tasa_valor,
                    'haber': haber_original * tasa_valor
                }
        
        # Si no se encuentra tasa de cambio, usar los valores originales
        return {
            'debe': debe_original,
            'haber': haber_original
        }

    # OBTENER TODOS LOS MOVIMIENTOS DEL PERÍODO ACTUAL Y CONVERTIRLOS
    movimientos_actual_raw = DetalleAsiento.objects.filter(
        idAsiento__idPeriodo=periodo
    ).select_related('idPlanCuenta', 'idMoneda')

    # Procesar movimientos y convertir a moneda nacional
    movimientos_actual_convertidos = {}
    for detalle in movimientos_actual_raw:
        montos_convertidos = convertir_a_moneda_nacional(detalle)
        cuenta_id = detalle.idPlanCuenta_id
        
        if cuenta_id not in movimientos_actual_convertidos:
            movimientos_actual_convertidos[cuenta_id] = {
                'total_debe': decimal.Decimal('0.00'),
                'total_haber': decimal.Decimal('0.00'),
                'codigo': detalle.idPlanCuenta.codigoPlanCuenta,
                'nombre': detalle.idPlanCuenta.nombrePlanCuenta,
                'cuentaPadre_id': detalle.idPlanCuenta.cuentaPadre_id
            }
        
        movimientos_actual_convertidos[cuenta_id]['total_debe'] += montos_convertidos['debe']
        movimientos_actual_convertidos[cuenta_id]['total_haber'] += montos_convertidos['haber']

    print("=== Movimientos del periodo actual (Moneda Nacional) ===")
    for cuenta_id, mov in movimientos_actual_convertidos.items():
        print(f"Cuenta: {mov['codigo']} - {mov['nombre']}, Debe: {mov['total_debe']}, Haber: {mov['total_haber']}")

    # OBTENER MOVIMIENTOS DEL PERÍODO ANTERIOR Y CONVERTIRLOS
    movimientos_anterior = {}
    if periodo_anterior:
        movimientos_anterior_raw = DetalleAsiento.objects.filter(
            idAsiento__idPeriodo=periodo_anterior
        ).select_related('idPlanCuenta', 'idMoneda')

        for detalle in movimientos_anterior_raw:
            montos_convertidos = convertir_a_moneda_nacional(detalle)
            cuenta_id = detalle.idPlanCuenta_id
            saldo_anterior = montos_convertidos['debe'] - montos_convertidos['haber']
            
            if cuenta_id not in movimientos_anterior:
                movimientos_anterior[cuenta_id] = decimal.Decimal('0.00')
            
            movimientos_anterior[cuenta_id] += saldo_anterior

        print("=== Movimientos del periodo anterior (Moneda Nacional) ===")
        for cuenta_id, saldo in movimientos_anterior.items():
            print(f"Cuenta ID: {cuenta_id}, Saldo anterior: {saldo}")

    # Crear diccionario de saldos por cuenta ID
    saldos_por_cuenta = {}
    for cuenta_id, mov in movimientos_actual_convertidos.items():
        saldo_anterior = movimientos_anterior.get(cuenta_id, decimal.Decimal('0.00'))
        total_debe = mov['total_debe']
        total_haber = mov['total_haber']
        saldo_actual = total_debe - total_haber
        saldo_acumulado = saldo_anterior + saldo_actual

        print(f"Cuenta: {mov['codigo']} - {mov['nombre']}, "
              f"Debe: {total_debe}, Haber: {total_haber}, Saldo anterior: {saldo_anterior}, "
              f"Saldo actual: {saldo_actual}, Saldo acumulado: {saldo_acumulado}")

        saldos_por_cuenta[cuenta_id] = {
            'total_debe': total_debe,
            'total_haber': total_haber,
            'saldo_actual': saldo_actual,
            'saldo_anterior': saldo_anterior,
            'saldo_acumulado': saldo_acumulado,
            'codigo': mov['codigo'],
            'nombre': mov['nombre'],
            'cuentaPadre_id': mov['cuentaPadre_id']
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
                'total_debe': decimal.Decimal('0.00'),
                'total_haber': decimal.Decimal('0.00'),
                'saldo_actual': decimal.Decimal('0.00'),
                'saldo_anterior': decimal.Decimal('0.00'),
                'saldo_acumulado': decimal.Decimal('0.00')
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

    print("=== Totales generales del balance (Moneda Nacional) ===")
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
        'total_general_debe': formatear_a_dos_decimales(total_general_debe),
        'total_general_haber': formatear_a_dos_decimales(total_general_haber),
        'total_general_saldo_anterior': formatear_a_dos_decimales(total_general_saldo_anterior),
        'total_general_saldo_actual': formatear_a_dos_decimales(total_general_saldo_actual),
        'total_general_saldo_acumulado': formatear_a_dos_decimales(total_general_saldo_acumulado),
        'paginator': paginator,
        'mostrando_total': f"Mostrando {len(cuentas_aplanadas)} cuentas",
        'search_query': search_query,
        'simbolo': simbolo
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



##Vistas para generar PDF y Excel
def balance_cuentas_pdf(request):
    """
    Vista para generar PDF del Balance de Cuentas con estilos mejorados
    """
    # Obtener parámetros de filtro
    periodo_id = request.GET.get('periodo')
    search_query = request.GET.get('search', '').strip()

    # Obtener período contable
    if periodo_id:
        periodo = get_object_or_404(periodoContable, idPeriodo=periodo_id)
    else:
        periodo = periodoContable.objects.filter(estadoPeriodo=True).first()
        if not periodo:
            return HttpResponse("No hay períodos contables disponibles.")

    # Obtener el período anterior
    periodo_anterior = periodoContable.objects.filter(
        fechaFinPeriodo__lt=periodo.fechaInicioPeriodo
    ).order_by('-fechaFinPeriodo').first()

    # Obtener símbolo de moneda nacional
    moneda_nacional = Moneda.objects.filter(idMoneda=1).first()
    simbolo = moneda_nacional.simboloMoneda if moneda_nacional and getattr(moneda_nacional, 'simboloMoneda', None) else 'Bs'

    # FUNCIONES DE CONVERSIÓN (copiadas de balance_cuentas)
    def convertir_formato_numero(valor):
        if valor is None:
            return decimal.Decimal('0.00')
        
        if isinstance(valor, (int, float, decimal.Decimal)):
            return decimal.Decimal(str(valor)).quantize(decimal.Decimal('0.0000000001'))
        
        if isinstance(valor, str):
            valor_limpio = valor.strip().replace('.', '').replace(',', '.')
            try:
                return decimal.Decimal(valor_limpio).quantize(decimal.Decimal('0.0000000001'))
            except (decimal.InvalidOperation, ValueError):
                try:
                    return decimal.Decimal(valor).quantize(decimal.Decimal('0.0000000001'))
                except (decimal.InvalidOperation, ValueError):
                    return decimal.Decimal('0.00')
        
        try:
            return decimal.Decimal(str(valor)).quantize(decimal.Decimal('0.0000000001'))
        except (decimal.InvalidOperation, ValueError, TypeError):
            return decimal.Decimal('0.00')

    def convertir_a_moneda_nacional(detalle_asiento):
        debe_original = convertir_formato_numero(detalle_asiento.debe)
        haber_original = convertir_formato_numero(detalle_asiento.haber)
        
        # Si la moneda es la nacional (idMoneda=1), no hay conversión necesaria
        if detalle_asiento.idMoneda_id == 1:
            return {
                'debe': debe_original,
                'haber': haber_original
            }
        
        # Si tiene moneda diferente a 1, buscar el pago relacionado
        pago = Pago.objects.filter(idAsiento=detalle_asiento.idAsiento).first()
        
        if pago and pago.idTasa:
            # Obtener la tasa de cambio del pago
            tasa_cambio = Tasa.objects.filter(idTasa=pago.idTasa_id).first()
            if tasa_cambio and hasattr(tasa_cambio, 'montoTasa'):
                # Convertir la tasa del formato español
                tasa_valor = convertir_formato_numero(tasa_cambio.montoTasa)
                
                # Convertir los montos usando la tasa de cambio
                return {
                    'debe': debe_original * tasa_valor,
                    'haber': haber_original * tasa_valor
                }
        
        # Si no se encuentra tasa de cambio, usar los valores originales
        return {
            'debe': debe_original,
            'haber': haber_original
        }

    # OBTENER TODOS LOS MOVIMIENTOS DEL PERÍODO ACTUAL Y CONVERTIRLOS
    movimientos_actual_raw = DetalleAsiento.objects.filter(
        idAsiento__idPeriodo=periodo
    ).select_related('idPlanCuenta', 'idMoneda')

    # Procesar movimientos y convertir a moneda nacional
    movimientos_actual_convertidos = {}
    for detalle in movimientos_actual_raw:
        montos_convertidos = convertir_a_moneda_nacional(detalle)
        cuenta_id = detalle.idPlanCuenta_id
        
        if cuenta_id not in movimientos_actual_convertidos:
            movimientos_actual_convertidos[cuenta_id] = {
                'total_debe': decimal.Decimal('0.00'),
                'total_haber': decimal.Decimal('0.00'),
                'codigo': detalle.idPlanCuenta.codigoPlanCuenta,
                'nombre': detalle.idPlanCuenta.nombrePlanCuenta,
                'cuentaPadre_id': detalle.idPlanCuenta.cuentaPadre_id
            }
        
        movimientos_actual_convertidos[cuenta_id]['total_debe'] += montos_convertidos['debe']
        movimientos_actual_convertidos[cuenta_id]['total_haber'] += montos_convertidos['haber']

    # OBTENER MOVIMIENTOS DEL PERÍODO ANTERIOR Y CONVERTIRLOS
    movimientos_anterior = {}
    if periodo_anterior:
        movimientos_anterior_raw = DetalleAsiento.objects.filter(
            idAsiento__idPeriodo=periodo_anterior
        ).select_related('idPlanCuenta', 'idMoneda')

        for detalle in movimientos_anterior_raw:
            montos_convertidos = convertir_a_moneda_nacional(detalle)
            cuenta_id = detalle.idPlanCuenta_id
            saldo_anterior = montos_convertidos['debe'] - montos_convertidos['haber']
            
            if cuenta_id not in movimientos_anterior:
                movimientos_anterior[cuenta_id] = decimal.Decimal('0.00')
            
            movimientos_anterior[cuenta_id] += saldo_anterior

    # Crear diccionario de saldos por cuenta ID
    saldos_por_cuenta = {}
    for cuenta_id, mov in movimientos_actual_convertidos.items():
        saldo_anterior = movimientos_anterior.get(cuenta_id, decimal.Decimal('0.00'))
        total_debe = mov['total_debe']
        total_haber = mov['total_haber']
        saldo_actual = total_debe - total_haber
        saldo_acumulado = saldo_anterior + saldo_actual

        saldos_por_cuenta[cuenta_id] = {
            'total_debe': total_debe,
            'total_haber': total_haber,
            'saldo_actual': saldo_actual,
            'saldo_anterior': saldo_anterior,
            'saldo_acumulado': saldo_acumulado,
            'codigo': mov['codigo'],
            'nombre': mov['nombre'],
            'cuentaPadre_id': mov['cuentaPadre_id']
        }

    # OBTENER TODAS LAS CUENTAS EN ORDEN JERÁRQUICO
    todas_las_cuentas = PlanCuenta.objects.all().select_related('cuentaPadre').order_by('codigoPlanCuenta')

    if search_query:
        todas_las_cuentas = todas_las_cuentas.filter(
            Q(codigoPlanCuenta__icontains=search_query) |
            Q(nombrePlanCuenta__icontains=search_query)
        )

    # Crear estructuras para el árbol
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
            saldo_data = saldos_por_cuenta.get(cuenta.idPlanCuenta, {
                'total_debe': decimal.Decimal('0.00'),
                'total_haber': decimal.Decimal('0.00'),
                'saldo_actual': decimal.Decimal('0.00'),
                'saldo_anterior': decimal.Decimal('0.00'),
                'saldo_acumulado': decimal.Decimal('0.00')
            })

            subcuentas = construir_arbol_cuentas(cuenta.idPlanCuenta, nivel + 1)

            # Calcular totales acumulados (incluyendo subcuentas)
            total_debe_acumulado = saldo_data['total_debe']
            total_haber_acumulado = saldo_data['total_haber']
            saldo_anterior_acumulado = saldo_data['saldo_anterior']
            saldo_actual_acumulado = saldo_data['saldo_actual']
            saldo_acumulado_total = saldo_data['saldo_acumulado']

            for subcuenta in subcuentas:
                total_debe_acumulado += subcuenta['total_debe_acumulado']
                total_haber_acumulado += subcuenta['total_haber_acumulado']
                saldo_anterior_acumulado += subcuenta['saldo_anterior_acumulado']
                saldo_actual_acumulado += subcuenta['saldo_actual_acumulado']
                saldo_acumulado_total += subcuenta['saldo_acumulado_total']

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

    # Construir el árbol completo
    arbol_cuentas = construir_arbol_cuentas(None, 0)

    # Aplanar el árbol para el reporte
    cuentas_aplanadas = []
    def aplanar_arbol(arbol, lista_plana):
        for item in arbol:
            lista_plana.append(item)
            aplanar_arbol(item['subcuentas'], lista_plana)

    aplanar_arbol(arbol_cuentas, cuentas_aplanadas)

    # Calcular totales generales
    total_general_debe = sum(item['total_debe_acumulado'] for item in arbol_cuentas)
    total_general_haber = sum(item['total_haber_acumulado'] for item in arbol_cuentas)
    total_general_saldo_anterior = sum(item['saldo_anterior_acumulado'] for item in arbol_cuentas)
    total_general_saldo_actual = sum(item['saldo_actual_acumulado'] for item in arbol_cuentas)
    total_general_saldo_acumulado = sum(item['saldo_acumulado_total'] for item in arbol_cuentas)

    # Configuración inicial del PDF
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="balance_cuentas_{periodo.nombrePeriodo}.pdf"'
    
    # Usar landscape para mejor visualización de tablas anchas
    from reportlab.lib.pagesizes import landscape, letter
    p = canvas.Canvas(response, pagesize=landscape(letter))
    p.setTitle("Reporte de balance de cuentas.")
    width, height = landscape(letter)
    
    # Configuración de márgenes y estilos
    logo_width, logo_height, logo_margin = 80, 80, 15
    min_margin = 30
    safe_left = min_margin
    safe_right = width - min_margin
    safe_width = safe_right - safe_left
    safe_center = width / 2

    # Obtener configuración institucional
    config = Configuracion.objects.order_by('-fechaConfiguracion').first()
    logo_path = config.logo.path if config and config.logo else None
    firma_path = config.firma.path if config and config.firma else None
    nombre_institucion = config.nombreInstitucion if config else "Institución"
    rif_institucion = config.rif if config else ""
    direccion1 = "AV. ALBERTO RAVELL CON AV. INTERCOMUNAL JOSE ANTONIO PAEZ"
    direccion2 = "LOCAL UPTYAB, INDEPENDENCIA – EDO YARACUY"

    def draw_header():
        # Logo a la derecha
        if logo_path and os.path.exists(logo_path):
            p.drawImage(
                logo_path,
                width - logo_width - logo_margin,
                height - logo_height - logo_margin,
                width=logo_width,
                height=logo_height,
                preserveAspectRatio=True,
                mask='auto'
            )
        
        # Texto institucional a la izquierda
        text_top = height - logo_margin - 15
        p.setFont("Helvetica-Bold", 10)
        p.drawString(min_margin, text_top, nombre_institucion)
        p.drawString(min_margin, text_top - 15, f"RIF: {rif_institucion}")
        p.drawString(min_margin, text_top - 30, direccion1)
        p.drawString(min_margin, text_top - 45, direccion2)
        
        # Título centrado
        p.setFont("Helvetica-Bold", 14)
        p.drawCentredString(safe_center, text_top - 85, "BALANCE DE CUENTAS")
        
        # Información del período
        p.setFont("Helvetica", 10)
        periodo_info = f"Período: {periodo.nombrePeriodo} - Del {periodo.fechaInicioPeriodo.strftime('%d/%m/%Y')} al {periodo.fechaFinPeriodo.strftime('%d/%m/%Y')}"
        p.drawCentredString(safe_center, text_top - 105, periodo_info)
        
        # Información de moneda
        p.setFont("Helvetica", 9)
        p.drawCentredString(safe_center, text_top - 120, f"Todos los montos en {simbolo} (Moneda Nacional)")

    def draw_footer():
        # Firma centrada en el pie de página
        if firma_path and os.path.exists(firma_path):
            p.setFont("Helvetica-Oblique", 9)
            p.drawCentredString(width/2, 35, "Firma autorizada")
        
        # Fecha de generación
        p.setFont("Helvetica", 8)
        fecha_generacion = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        p.drawString(min_margin, 20, f"Generado el: {fecha_generacion}")

    # Preparar datos de la tabla
    headers = ["Código", "Nombre de Cuenta", "Saldo Anterior", "Total Débe", "Total Haber", "Saldo Actual", "Saldo Acumulado"]
    data = [headers]
    
    for cuenta_data in cuentas_aplanadas:
        nivel = cuenta_data['nivel']
        indent = "  " * nivel
        codigo = f"{indent}{cuenta_data['cuenta'].codigoPlanCuenta}"
        nombre = f"{indent}{cuenta_data['cuenta'].nombrePlanCuenta}"

        data.append([
            codigo,
            nombre,
            f"{simbolo} {cuenta_data['saldo_anterior_acumulado']:,.2f}",
            f"{simbolo} {cuenta_data['total_debe_acumulado']:,.2f}",
            f"{simbolo} {cuenta_data['total_haber_acumulado']:,.2f}",
            f"{simbolo} {cuenta_data['saldo_actual_acumulado']:,.2f}",
            f"{simbolo} {cuenta_data['saldo_acumulado_total']:,.2f}"
        ])

    # Totales generales
    data.append([
        'TOTALES GENERALES:',
        '',
        f"{simbolo} {total_general_saldo_anterior:,.2f}",
        f"{simbolo} {total_general_debe:,.2f}",
        f"{simbolo} {total_general_haber:,.2f}",
        f"{simbolo} {total_general_saldo_actual:,.2f}",
        f"{simbolo} {total_general_saldo_acumulado:,.2f}"
    ])

    # Resto del código de configuración de la tabla y generación del PDF permanece igual...
    # ... (mantener el mismo código de configuración de tabla, estilos, paginación, etc.)

    # Configuración de la tabla
    col_widths = [120, 200, 80, 80, 80, 80, 80]
    table_width = sum(col_widths)
    
    # Espaciado vertical
    header_height = 150
    footer_height = 100
    row_height = 22
    cell_padding = 4
    
    # Calcular espacio disponible
    available_height = height - header_height - footer_height
    max_rows_per_page = max(1, int(available_height // row_height))
    total_rows = len(data) - 1
    page = 0

    # Generar páginas
    for start_row in range(0, total_rows, max_rows_per_page):
        end_row = min(start_row + max_rows_per_page, total_rows)
        page_data = [data[0]] + data[start_row + 1:end_row + 1]
        
        if page > 0:
            p.showPage()
        
        draw_header()
        y_position = height - header_height
        
        # Centrar tabla horizontalmente
        table_x = safe_left + (safe_width - table_width) / 2
        table = Table(page_data, colWidths=col_widths, rowHeights=[row_height]*len(page_data))
        
        # Estilo de la tabla
        table_style = TableStyle([
            # Encabezado
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#fe8330")),
            ('TEXTCOLOR', (0,0), (-1,0), colors.white),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('FONTSIZE', (0,0), (-1,0), 8),
            ('ALIGN', (0,0), (-1,0), 'CENTER'),
            ('VALIGN', (0,0), (-1,0), 'MIDDLE'),
            ('BOTTOMPADDING', (0,0), (-1,0), cell_padding),
            
            # Cuerpo de la tabla
            ('FONTSIZE', (0,1), (-1,-2), 7),
            ('ALIGN', (0,1), (-1,-2), 'RIGHT'),
            ('ALIGN', (0,1), (1,-2), 'LEFT'),
            ('VALIGN', (0,1), (-1,-2), 'MIDDLE'),
            ('BACKGROUND', (0,1), (-1,-2), colors.whitesmoke),
            
            # Totales
            ('BACKGROUND', (0,-1), (-1,-1), colors.HexColor("#366092")),
            ('TEXTCOLOR', (0,-1), (-1,-1), colors.white),
            ('FONTNAME', (0,-1), (-1,-1), 'Helvetica-Bold'),
            ('FONTSIZE', (0,-1), (-1,-1), 8),
            ('ALIGN', (0,-1), (-1,-1), 'RIGHT'),
            ('ALIGN', (0,-1), (1,-1), 'LEFT'),
            
            # Bordes
            ('GRID', (0,0), (-1,-1), 0.5, colors.lightgrey),
            ('BOX', (0,0), (-1,-1), 0.5, colors.black),
            ('TOPPADDING', (0,1), (-1,-1), cell_padding),
            ('BOTTOMPADDING', (0,1), (-1,-1), cell_padding),
        ])
        
        table.setStyle(table_style)
        table.wrapOn(p, width, height)
        table.drawOn(p, table_x, y_position - row_height * len(page_data) - 10)
        
        # Información de paginación
        p.setFont("Helvetica", 8)
        pagination_text = f"Página {page + 1} - Registros {start_row + 1} a {end_row} de {total_rows}"
        p.drawCentredString(
            safe_center, 
            y_position - row_height * len(page_data) - 25,
            pagination_text
        )
        
        draw_footer()
        page += 1

    p.save()
    return response

def balance_cuentas_excel(request):
    """
    Vista para generar Excel del Balance de Cuentas con estilos mejorados
    """
    # Obtener parámetros de filtrado
    periodo_id = request.GET.get('periodo')
    search_query = request.GET.get('search', '').strip()

    if periodo_id:
        periodo = get_object_or_404(periodoContable, idPeriodo=periodo_id)
    else:
        periodo = periodoContable.objects.filter(estadoPeriodo=True).first()
        if not periodo:
            return HttpResponse("No hay períodos contables disponibles.")

    # Obtener el período anterior
    periodo_anterior = periodoContable.objects.filter(
        fechaFinPeriodo__lt=periodo.fechaInicioPeriodo
    ).order_by('-fechaFinPeriodo').first()

    # Obtener símbolo de moneda nacional
    moneda_nacional = Moneda.objects.filter(idMoneda=1).first()
    simbolo = moneda_nacional.simboloMoneda if moneda_nacional and getattr(moneda_nacional, 'simboloMoneda', None) else 'Bs'

    # FUNCIONES DE CONVERSIÓN (igual que en balance_cuentas_pdf)
    def convertir_formato_numero(valor):
        if valor is None:
            return decimal.Decimal('0.00')
        
        if isinstance(valor, (int, float, decimal.Decimal)):
            return decimal.Decimal(str(valor)).quantize(decimal.Decimal('0.0000000001'))
        
        if isinstance(valor, str):
            valor_limpio = valor.strip().replace('.', '').replace(',', '.')
            try:
                return decimal.Decimal(valor_limpio).quantize(decimal.Decimal('0.0000000001'))
            except (decimal.InvalidOperation, ValueError):
                try:
                    return decimal.Decimal(valor).quantize(decimal.Decimal('0.0000000001'))
                except (decimal.InvalidOperation, ValueError):
                    return decimal.Decimal('0.00')
        
        try:
            return decimal.Decimal(str(valor)).quantize(decimal.Decimal('0.0000000001'))
        except (decimal.InvalidOperation, ValueError, TypeError):
            return decimal.Decimal('0.00')

    def convertir_a_moneda_nacional(detalle_asiento):
        debe_original = convertir_formato_numero(detalle_asiento.debe)
        haber_original = convertir_formato_numero(detalle_asiento.haber)
        
        # Si la moneda es la nacional (idMoneda=1), no hay conversión necesaria
        if detalle_asiento.idMoneda_id == 1:
            return {
                'debe': debe_original,
                'haber': haber_original
            }
        
        # Si tiene moneda diferente a 1, buscar el pago relacionado
        pago = Pago.objects.filter(idAsiento=detalle_asiento.idAsiento).first()
        
        if pago and pago.idTasa:
            # Obtener la tasa de cambio del pago
            tasa_cambio = Tasa.objects.filter(idTasa=pago.idTasa_id).first()
            if tasa_cambio and hasattr(tasa_cambio, 'montoTasa'):
                # Convertir la tasa del formato español
                tasa_valor = convertir_formato_numero(tasa_cambio.montoTasa)
                
                # Convertir los montos usando la tasa de cambio
                return {
                    'debe': debe_original * tasa_valor,
                    'haber': haber_original * tasa_valor
                }
        
        # Si no se encuentra tasa de cambio, usar los valores originales
        return {
            'debe': debe_original,
            'haber': haber_original
        }

    # OBTENER TODOS LOS MOVIMIENTOS DEL PERÍODO ACTUAL Y CONVERTIRLOS
    movimientos_actual_raw = DetalleAsiento.objects.filter(
        idAsiento__idPeriodo=periodo
    ).select_related('idPlanCuenta', 'idMoneda')

    # Procesar movimientos y convertir a moneda nacional
    movimientos_actual_convertidos = {}
    for detalle in movimientos_actual_raw:
        montos_convertidos = convertir_a_moneda_nacional(detalle)
        cuenta_id = detalle.idPlanCuenta_id
        
        if cuenta_id not in movimientos_actual_convertidos:
            movimientos_actual_convertidos[cuenta_id] = {
                'total_debe': decimal.Decimal('0.00'),
                'total_haber': decimal.Decimal('0.00'),
                'codigo': detalle.idPlanCuenta.codigoPlanCuenta,
                'nombre': detalle.idPlanCuenta.nombrePlanCuenta,
                'cuentaPadre_id': detalle.idPlanCuenta.cuentaPadre_id
            }
        
        movimientos_actual_convertidos[cuenta_id]['total_debe'] += montos_convertidos['debe']
        movimientos_actual_convertidos[cuenta_id]['total_haber'] += montos_convertidos['haber']

    # OBTENER MOVIMIENTOS DEL PERÍODO ANTERIOR Y CONVERTIRLOS
    movimientos_anterior = {}
    if periodo_anterior:
        movimientos_anterior_raw = DetalleAsiento.objects.filter(
            idAsiento__idPeriodo=periodo_anterior
        ).select_related('idPlanCuenta', 'idMoneda')

        for detalle in movimientos_anterior_raw:
            montos_convertidos = convertir_a_moneda_nacional(detalle)
            cuenta_id = detalle.idPlanCuenta_id
            saldo_anterior = montos_convertidos['debe'] - montos_convertidos['haber']
            
            if cuenta_id not in movimientos_anterior:
                movimientos_anterior[cuenta_id] = decimal.Decimal('0.00')
            
            movimientos_anterior[cuenta_id] += saldo_anterior

    # Crear diccionario de saldos por cuenta ID
    saldos_por_cuenta = {}
    for cuenta_id, mov in movimientos_actual_convertidos.items():
        saldo_anterior = movimientos_anterior.get(cuenta_id, decimal.Decimal('0.00'))
        total_debe = mov['total_debe']
        total_haber = mov['total_haber']
        saldo_actual = total_debe - total_haber
        saldo_acumulado = saldo_anterior + saldo_actual

        saldos_por_cuenta[cuenta_id] = {
            'total_debe': total_debe,
            'total_haber': total_haber,
            'saldo_actual': saldo_actual,
            'saldo_anterior': saldo_anterior,
            'saldo_acumulado': saldo_acumulado,
            'codigo': mov['codigo'],
            'nombre': mov['nombre'],
            'cuentaPadre_id': mov['cuentaPadre_id']
        }

    # OBTENER TODAS LAS CUENTAS EN ORDEN JERÁRQUICO
    todas_las_cuentas = PlanCuenta.objects.all().select_related('cuentaPadre').order_by('codigoPlanCuenta')

    if search_query:
        todas_las_cuentas = todas_las_cuentas.filter(
            Q(codigoPlanCuenta__icontains=search_query) |
            Q(nombrePlanCuenta__icontains=search_query)
        )

    # Crear estructuras para el árbol
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
                'total_debe': decimal.Decimal('0.00'),
                'total_haber': decimal.Decimal('0.00'),
                'saldo_actual': decimal.Decimal('0.00'),
                'saldo_anterior': decimal.Decimal('0.00'),
                'saldo_acumulado': decimal.Decimal('0.00')
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

    # Aplanar el árbol para la exportación
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

    # Crear libro de Excel
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = f"Balance Cuentas {periodo.nombrePeriodo}"[:31]  # Máximo 31 caracteres

    # Estilos mejorados
    header_font = Font(bold=True, color="FFFFFF", size=12)
    header_fill = PatternFill(start_color="fe8330", end_color="fe8330", fill_type="solid")
    total_fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
    total_font = Font(bold=True, color="FFFFFF")
    border = Border(left=Side(style='thin'), right=Side(style='thin'), 
                   top=Side(style='thin'), bottom=Side(style='thin'))
    
    # Estilo para cuentas principales
    cuenta_principal_fill = PatternFill(start_color="FFE699", end_color="FFE699", fill_type="solid")
    # Estilo para subcuentas según nivel
    subcuenta_fills = [
        PatternFill(start_color="E2EFDA", end_color="E2EFDA", fill_type="solid"),
        PatternFill(start_color="DDEBF7", end_color="DDEBF7", fill_type="solid"),
        PatternFill(start_color="FCE4D6", end_color="FCE4D6", fill_type="solid"),
        PatternFill(start_color="EDEDED", end_color="EDEDED", fill_type="solid"),
    ]

    # Obtener configuración institucional
    config = Configuracion.objects.order_by('-fechaConfiguracion').first()
    nombre_institucion = config.nombreInstitucion if config else "Institución"
    rif_institucion = config.rif if config else ""

    # Título e información del período
    worksheet.cell(row=1, column=1, value=nombre_institucion).font = Font(bold=True, size=14)
    worksheet.merge_cells('A1:G1')
    
    worksheet.cell(row=2, column=1, value=f"RIF: {rif_institucion}").font = Font(bold=True)
    worksheet.merge_cells('A2:G2')
    
    worksheet.cell(row=3, column=1, value="BALANCE DE CUENTAS").font = Font(bold=True, size=16)
    worksheet.merge_cells('A3:G3')
    
    worksheet.cell(row=4, column=1, value=f"Período: {periodo.nombrePeriodo}").font = Font(bold=True)
    worksheet.merge_cells('A4:G4')
    
    worksheet.cell(row=5, column=1, value=f"Del {periodo.fechaInicioPeriodo.strftime('%d/%m/%Y')} al {periodo.fechaFinPeriodo.strftime('%d/%m/%Y')}")
    worksheet.merge_cells('A5:G5')
    
    worksheet.cell(row=6, column=1, value=f"Moneda: {simbolo} (Moneda Nacional)").font = Font(bold=True)
    worksheet.merge_cells('A6:G6')
    
    if periodo_anterior:
        worksheet.cell(row=7, column=1, value=f"Período Anterior: {periodo_anterior.nombrePeriodo}")
        worksheet.merge_cells('A7:G7')
        row_num = 9
    else:
        row_num = 8

    # Encabezados
    headers = ['Código', 'Nombre de Cuenta', 'Saldo Anterior', 'Total Débe', 'Total Haber', 'Saldo Actual', 'Saldo Acumulado']
    for col_num, header in enumerate(headers, 1):
        cell = worksheet.cell(row=row_num, column=col_num, value=header)
        cell.font = header_font
        cell.fill = header_fill
        cell.border = border
        cell.alignment = Alignment(horizontal='center', vertical='center')
    
    row_num += 1

    # Datos
    for cuenta_data in cuentas_aplanadas:
        nivel = cuenta_data['nivel']
        indent = "  " * nivel
        
        # Determinar el estilo de relleno según el nivel
        if nivel == 0:
            fill_style = cuenta_principal_fill
        else:
            fill_index = min(nivel - 1, len(subcuenta_fills) - 1)
            fill_style = subcuenta_fills[fill_index]
        
        # Escribir datos de la cuenta
        worksheet.cell(row=row_num, column=1, value=f"{indent}{cuenta_data['cuenta'].codigoPlanCuenta}").border = border
        worksheet.cell(row=row_num, column=2, value=f"{indent}{cuenta_data['cuenta'].nombrePlanCuenta}").border = border
        worksheet.cell(row=row_num, column=3, value=float(cuenta_data['saldo_anterior_acumulado'])).border = border
        worksheet.cell(row=row_num, column=4, value=float(cuenta_data['total_debe_acumulado'])).border = border
        worksheet.cell(row=row_num, column=5, value=float(cuenta_data['total_haber_acumulado'])).border = border
        worksheet.cell(row=row_num, column=6, value=float(cuenta_data['saldo_actual_acumulado'])).border = border
        worksheet.cell(row=row_num, column=7, value=float(cuenta_data['saldo_acumulado_total'])).border = border
        
        # Aplicar estilo de relleno
        for col in range(1, 8):
            worksheet.cell(row=row_num, column=col).fill = fill_style
        
        row_num += 1

    # Totales
    total_row = row_num
    worksheet.cell(row=total_row, column=1, value="TOTALES GENERALES:").font = total_font
    worksheet.cell(row=total_row, column=2, value="").font = total_font
    worksheet.cell(row=total_row, column=3, value=float(total_general_saldo_anterior)).fill = total_fill
    worksheet.cell(row=total_row, column=4, value=float(total_general_debe)).fill = total_fill
    worksheet.cell(row=total_row, column=5, value=float(total_general_haber)).fill = total_fill
    worksheet.cell(row=total_row, column=6, value=float(total_general_saldo_actual)).fill = total_fill
    worksheet.cell(row=total_row, column=7, value=float(total_general_saldo_acumulado)).fill = total_fill
    
    # Aplicar bordes y estilos a las celdas de totales
    for col in range(1, 8):
        cell = worksheet.cell(row=total_row, column=col)
        cell.border = border
        cell.font = total_font
        if col >= 3:
            cell.fill = total_fill

    # Ajustar anchos de columna
    column_widths = {
        'A': 15,
        'B': 50,
        'C': 15,
        'D': 15,
        'E': 15,
        'F': 15,
        'G': 15
    }
    
    for col_letter, width in column_widths.items():
        worksheet.column_dimensions[col_letter].width = width

    # Formato de números para columnas monetarias
    for row in worksheet.iter_rows(min_row=row_num - len(cuentas_aplanadas), max_row=worksheet.max_row, min_col=3, max_col=7):
        for cell in row:
            if isinstance(cell.value, (int, float)):
                cell.number_format = f'#,##0.00"{simbolo}"'

    # Información adicional al final
    info_row = total_row + 2
    worksheet.cell(row=info_row, column=1, value="Notas:").font = Font(bold=True)
    worksheet.cell(row=info_row + 1, column=1, value="- Saldo Deudor: Positivo")
    worksheet.cell(row=info_row + 2, column=1, value="- Saldo Acreedor: Negativo")
    worksheet.cell(row=info_row + 3, column=1, value=f"- Generado el: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    worksheet.cell(row=info_row + 4, column=1, value=f"- Todos los montos en {simbolo} (Moneda Nacional)")

    # Preparar respuesta
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = f'attachment; filename="balance_cuentas_{periodo.nombrePeriodo}.xlsx"'
    workbook.save(response)

    return response

def libro_diario_pdf(request):
    """
    Vista para generar PDF del Libro Diario con estilos mejorados
    """
    search_query = request.GET.get('search', '').strip()
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    periodo_id = request.GET.get('periodo')

    # Obtener símbolo de moneda nacional
    moneda_nacional = Moneda.objects.filter(idMoneda=1).first()
    simbolo = moneda_nacional.simboloMoneda if moneda_nacional and getattr(moneda_nacional, 'simboloMoneda', None) else 'Bs'

    asientos = AsientoContable.objects.prefetch_related('detalles').order_by('fechaAsiento', 'numeroAsiento')

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

    if start_date:
        asientos = asientos.filter(fechaAsiento__gte=start_date)
    if end_date:
        asientos = asientos.filter(fechaAsiento__lte=end_date)
    if periodo_id:
        asientos = asientos.filter(idPeriodo__idPeriodo=periodo_id)

    # Funciones de conversión (copiadas de libro_diario)
    def convertir_formato_numero(valor):
        if valor is None:
            return decimal.Decimal('0.00')
        
        if isinstance(valor, (int, float, decimal.Decimal)):
            return decimal.Decimal(str(valor)).quantize(decimal.Decimal('0.0000000001'))
        
        if isinstance(valor, str):
            valor_limpio = valor.strip().replace('.', '').replace(',', '.')
            try:
                return decimal.Decimal(valor_limpio).quantize(decimal.Decimal('0.0000000001'))
            except (decimal.InvalidOperation, ValueError):
                try:
                    return decimal.Decimal(valor).quantize(decimal.Decimal('0.0000000001'))
                except (decimal.InvalidOperation, ValueError):
                    return decimal.Decimal('0.00')
        
        try:
            return decimal.Decimal(str(valor)).quantize(decimal.Decimal('0.0000000001'))
        except (decimal.InvalidOperation, ValueError, TypeError):
            return decimal.Decimal('0.00')

    def convertir_a_moneda_nacional(detalle_asiento):
        debe_original = convertir_formato_numero(detalle_asiento.debe)
        haber_original = convertir_formato_numero(detalle_asiento.haber)
        
        # Si la moneda es la nacional (idMoneda=1), no hay conversión necesaria
        if detalle_asiento.idMoneda_id == 1:
            return {
                'debe': debe_original,
                'haber': haber_original
            }
        
        # Si tiene moneda diferente a 1, buscar el pago relacionado
        pago = Pago.objects.filter(idAsiento=detalle_asiento.idAsiento).first()
        
        if pago and pago.idTasa:
            # Obtener la tasa de cambio del pago
            tasa_cambio = Tasa.objects.filter(idTasa=pago.idTasa_id).first()
            if tasa_cambio and hasattr(tasa_cambio, 'montoTasa'):
                # Convertir la tasa del formato español
                tasa_valor = convertir_formato_numero(tasa_cambio.montoTasa)
                
                # Convertir los montos usando la tasa de cambio
                return {
                    'debe': debe_original * tasa_valor,
                    'haber': haber_original * tasa_valor
                }
        
        # Si no se encuentra tasa de cambio, usar los valores originales
        return {
            'debe': debe_original,
            'haber': haber_original
        }

    # Procesar asientos para convertir a moneda nacional
    asientos_procesados = []
    total_debe_global = decimal.Decimal('0.00')
    total_haber_global = decimal.Decimal('0.00')

    for asiento in asientos:
        for detalle in asiento.detalles.all():
            montos_convertidos = convertir_a_moneda_nacional(detalle)
            debe_convertido = montos_convertidos['debe']
            haber_convertido = montos_convertidos['haber']
            
            total_debe_global += debe_convertido
            total_haber_global += haber_convertido

    # Reconstruir la lista de asientos con los montos convertidos para el PDF
    # Nota: En el PDF, vamos a mostrar los detalles convertidos, pero no tenemos una estructura de asientos_procesados como en la vista HTML.
    # Para no complicar, vamos a generar el PDF con los datos originales pero convertidos. Sin embargo, el código anterior ya calcula los totales convertidos.

    # Pero para mostrar cada detalle convertido, necesitamos procesar cada asiento y detalle again. Para evitar duplicación, podemos crear una estructura similar a la vista HTML.

    # Vamos a crear una lista de datos para el PDF que incluya los detalles convertidos.
    data_detalles = []
    for asiento in asientos:
        for detalle in asiento.detalles.all():
            montos_convertidos = convertir_a_moneda_nacional(detalle)
            data_detalles.append({
                'numeroAsiento': asiento.numeroAsiento,
                'fechaAsiento': asiento.fechaAsiento,
                'conceptoAsiento': asiento.conceptoAsiento,
                'cuenta': detalle.idPlanCuenta,
                'debe': montos_convertidos['debe'],
                'haber': montos_convertidos['haber']
            })

    # Ahora, usamos data_detalles para construir el PDF.

    periodo_seleccionado = None
    if periodo_id:
        periodo_seleccionado = periodoContable.objects.filter(idPeriodo=periodo_id).first()

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'inline; filename="libro_diario.pdf"'
    
    from reportlab.lib.pagesizes import landscape, letter
    p = canvas.Canvas(response, pagesize=landscape(letter))
    p.setTitle("Reporte de libro diario.")
    width, height = landscape(letter)
    
    logo_width, logo_height, logo_margin = 80, 80, 15
    min_margin = 30
    safe_left = min_margin
    safe_right = width - min_margin
    safe_width = safe_right - safe_left
    safe_center = width / 2

    config = Configuracion.objects.order_by('-fechaConfiguracion').first()
    logo_path = config.logo.path if config and config.logo else None
    firma_path = config.firma.path if config and config.firma else None
    nombre_institucion = config.nombreInstitucion if config else "Institución"
    rif_institucion = config.rif if config else ""
    direccion1 = "AV. ALBERTO RAVELL CON AV. INTERCOMUNAL JOSE ANTONIO PAEZ"
    direccion2 = "LOCAL UPTYAB, INDEPENDENCIA – EDO YARACUY"

    def draw_header():
        if logo_path and os.path.exists(logo_path):
            p.drawImage(
                logo_path,
                width - logo_width - logo_margin,
                height - logo_height - logo_margin,
                width=logo_width,
                height=logo_height,
                preserveAspectRatio=True,
                mask='auto'
            )
        
        text_top = height - logo_margin - 15
        p.setFont("Helvetica-Bold", 10)
        p.drawString(min_margin, text_top, nombre_institucion)
        p.drawString(min_margin, text_top - 15, f"RIF: {rif_institucion}")
        p.drawString(min_margin, text_top - 30, direccion1)
        p.drawString(min_margin, text_top - 45, direccion2)
        
        p.setFont("Helvetica-Bold", 14)
        p.drawCentredString(safe_center, text_top - 85, "LIBRO DIARIO")
        
        p.setFont("Helvetica", 10)
        if periodo_seleccionado:
            periodo_info = f"Período: {periodo_seleccionado.nombrePeriodo} - Del {periodo_seleccionado.fechaInicioPeriodo.strftime('%d/%m/%Y')} al {periodo_seleccionado.fechaFinPeriodo.strftime('%d/%m/%Y')}"
        else:
            periodo_info = "Período: Todos los movimientos"
        p.drawCentredString(safe_center, text_top - 105, periodo_info)

        # Agregar información de moneda
        p.setFont("Helvetica", 9)
        p.drawCentredString(safe_center, text_top - 120, f"Todos los montos en {simbolo} (Moneda Nacional)")

    def draw_footer():
        if firma_path and os.path.exists(firma_path):
            p.setFont("Helvetica-Oblique", 9)
            p.drawCentredString(width/2, 35, "Firma autorizada")
        
        p.setFont("Helvetica", 8)
        fecha_generacion = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        p.drawString(min_margin, 20, f"Generado el: {fecha_generacion}")

    headers = ["N° Asiento", "Fecha", "Concepto", "Cuenta", "Debe", "Haber"]
    data = [headers]

    # Llenar la tabla con los detalles convertidos
    for detalle_data in data_detalles:
        data.append([
            detalle_data['numeroAsiento'],
            detalle_data['fechaAsiento'].strftime("%d/%m/%Y"),
            detalle_data['conceptoAsiento'][:50] + "..." if len(detalle_data['conceptoAsiento']) > 50 else detalle_data['conceptoAsiento'],
            f"{detalle_data['cuenta'].codigoPlanCuenta} - {detalle_data['cuenta'].nombrePlanCuenta}",
            f"{simbolo} {detalle_data['debe']:,.2f}" if detalle_data['debe'] else "",
            f"{simbolo} {detalle_data['haber']:,.2f}" if detalle_data['haber'] else ""
        ])

    data.append([
        'TOTALES:',
        '',
        '',
        '',
        f"{simbolo} {total_debe_global:,.2f}",
        f"{simbolo} {total_haber_global:,.2f}"
    ])

    col_widths = [120, 80, 200, 120, 80, 80]
    table_width = sum(col_widths)
    
    header_height = 150
    footer_height = 100
    row_height = 22
    cell_padding = 4
    
    available_height = height - header_height - footer_height
    max_rows_per_page = max(1, int(available_height // row_height))
    total_rows = len(data) - 1
    page = 0

    for start_row in range(0, total_rows, max_rows_per_page):
        end_row = min(start_row + max_rows_per_page, total_rows)
        page_data = [data[0]] + data[start_row + 1:end_row + 1]
        
        if page > 0:
            p.showPage()
        
        draw_header()
        y_position = height - header_height
        
        table_x = safe_left + (safe_width - table_width) / 2
        table = Table(page_data, colWidths=col_widths, rowHeights=[row_height]*len(page_data))
        
        table_style = TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#fe8330")),
            ('TEXTCOLOR', (0,0), (-1,0), colors.white),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('FONTSIZE', (0,0), (-1,0), 8),
            ('ALIGN', (0,0), (-1,0), 'CENTER'),
            ('VALIGN', (0,0), (-1,0), 'MIDDLE'),
            ('BOTTOMPADDING', (0,0), (-1,0), cell_padding),
            
            ('FONTSIZE', (0,1), (-1,-2), 7),
            ('ALIGN', (0,1), (-1,-2), 'CENTER'),
            ('ALIGN', (3,1), (3,-2), 'LEFT'),
            ('VALIGN', (0,1), (-1,-2), 'MIDDLE'),
            ('BACKGROUND', (0,1), (-1,-2), colors.whitesmoke),
            
            ('BACKGROUND', (0,-1), (-1,-1), colors.HexColor("#366092")),
            ('TEXTCOLOR', (0,-1), (-1,-1), colors.white),
            ('FONTNAME', (0,-1), (-1,-1), 'Helvetica-Bold'),
            ('FONTSIZE', (0,-1), (-1,-1), 8),
            ('ALIGN', (0,-1), (-1,-1), 'RIGHT'),
            ('ALIGN', (0,-1), (3,-1), 'LEFT'),
            
            ('GRID', (0,0), (-1,-1), 0.5, colors.lightgrey),
            ('BOX', (0,0), (-1,-1), 0.5, colors.black),
            ('TOPPADDING', (0,1), (-1,-1), cell_padding),
            ('BOTTOMPADDING', (0,1), (-1,-1), cell_padding),
        ])
        
        table.setStyle(table_style)
        table.wrapOn(p, width, height)
        table.drawOn(p, table_x, y_position - row_height * len(page_data) - 10)
        
        p.setFont("Helvetica", 8)
        pagination_text = f"Página {page + 1} - Registros {start_row + 1} a {end_row} de {total_rows}"
        p.drawCentredString(
            safe_center, 
            y_position - row_height * len(page_data) - 25,
            pagination_text
        )
        
        draw_footer()
        page += 1

    p.save()
    return response

def libro_diario_excel(request):
    """
    Vista para generar Excel del Libro Diario
    """
    # Obtener parámetros de filtrado
    search_query = request.GET.get('search', '').strip()
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    periodo_id = request.GET.get('periodo')

    # Obtener símbolo de moneda nacional
    moneda_nacional = Moneda.objects.filter(idMoneda=1).first()
    simbolo = moneda_nacional.simboloMoneda if moneda_nacional and getattr(moneda_nacional, 'simboloMoneda', None) else 'Bs'

    asientos = AsientoContable.objects.prefetch_related('detalles').order_by('fechaAsiento', 'numeroAsiento')

    # Aplicar filtros
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

    if start_date:
        asientos = asientos.filter(fechaAsiento__gte=start_date)
    if end_date:
        asientos = asientos.filter(fechaAsiento__lte=end_date)
    if periodo_id:
        asientos = asientos.filter(idPeriodo__idPeriodo=periodo_id)

    # FUNCIONES DE CONVERSIÓN
    def convertir_formato_numero(valor):
        if valor is None:
            return decimal.Decimal('0.00')
        
        if isinstance(valor, (int, float, decimal.Decimal)):
            return decimal.Decimal(str(valor)).quantize(decimal.Decimal('0.0000000001'))
        
        if isinstance(valor, str):
            valor_limpio = valor.strip().replace('.', '').replace(',', '.')
            try:
                return decimal.Decimal(valor_limpio).quantize(decimal.Decimal('0.0000000001'))
            except (decimal.InvalidOperation, ValueError):
                try:
                    return decimal.Decimal(valor).quantize(decimal.Decimal('0.0000000001'))
                except (decimal.InvalidOperation, ValueError):
                    return decimal.Decimal('0.00')
        
        try:
            return decimal.Decimal(str(valor)).quantize(decimal.Decimal('0.0000000001'))
        except (decimal.InvalidOperation, ValueError, TypeError):
            return decimal.Decimal('0.00')

    def convertir_a_moneda_nacional(detalle_asiento):
        debe_original = convertir_formato_numero(detalle_asiento.debe)
        haber_original = convertir_formato_numero(detalle_asiento.haber)
        
        # Si la moneda es la nacional (idMoneda=1), no hay conversión necesaria
        if detalle_asiento.idMoneda_id == 1:
            return {
                'debe': debe_original,
                'haber': haber_original
            }
        
        # Si tiene moneda diferente a 1, buscar el pago relacionado
        pago = Pago.objects.filter(idAsiento=detalle_asiento.idAsiento).first()
        
        if pago and pago.idTasa:
            # Obtener la tasa de cambio del pago
            tasa_cambio = Tasa.objects.filter(idTasa=pago.idTasa_id).first()
            if tasa_cambio and hasattr(tasa_cambio, 'montoTasa'):
                # Convertir la tasa del formato español
                tasa_valor = convertir_formato_numero(tasa_cambio.montoTasa)
                
                # Convertir los montos usando la tasa de cambio
                return {
                    'debe': debe_original * tasa_valor,
                    'haber': haber_original * tasa_valor
                }
        
        # Si no se encuentra tasa de cambio, usar los valores originales
        return {
            'debe': debe_original,
            'haber': haber_original
        }

    # Procesar asientos para convertir a moneda nacional
    asientos_procesados = []
    total_debe_global = decimal.Decimal('0.00')
    total_haber_global = decimal.Decimal('0.00')

    for asiento in asientos:
        detalles_procesados = []
        total_debe_asiento = decimal.Decimal('0.00')
        total_haber_asiento = decimal.Decimal('0.00')
        
        for detalle in asiento.detalles.all():
            # Convertir montos a moneda nacional
            montos_convertidos = convertir_a_moneda_nacional(detalle)
            debe_convertido = montos_convertidos['debe']
            haber_convertido = montos_convertidos['haber']
            
            # Acumular totales
            total_debe_asiento += debe_convertido
            total_haber_asiento += haber_convertido
            total_debe_global += debe_convertido
            total_haber_global += haber_convertido
            
            detalles_procesados.append({
                'detalle': detalle,
                'debe_convertido': debe_convertido,
                'haber_convertido': haber_convertido
            })
        
        asientos_procesados.append({
            'asiento': asiento,
            'detalles': detalles_procesados,
            'total_debe': total_debe_asiento,
            'total_haber': total_haber_asiento
        })

    # Obtener período seleccionado para el nombre del archivo
    periodo_seleccionado = None
    if periodo_id:
        periodo_seleccionado = periodoContable.objects.filter(idPeriodo=periodo_id).first()

    # Crear libro de Excel
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = "Libro Diario"

    # Estilos
    header_font = Font(bold=True, color="FFFFFF")
    header_fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
    total_fill = PatternFill(start_color="D9E1F2", end_color="D9E1F2", fill_type="solid")
    border = Border(left=Side(style='thin'), right=Side(style='thin'), 
                   top=Side(style='thin'), bottom=Side(style='thin'))

    # CORRECCIÓN: Calcular row_num correctamente sin conflictos con celdas combinadas
    current_row = 1

    # Título e información - SIN COMBINAR CELDAS
    title_cell = worksheet.cell(row=current_row, column=1, value="LIBRO DIARIO")
    title_cell.font = Font(bold=True, size=16)
    title_cell.alignment = Alignment(horizontal='center')
    # Aplicar el estilo a todas las celdas del título manualmente
    for col in range(1, 7):  # Columnas A-F
        cell = worksheet.cell(row=current_row, column=col)
        cell.fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
        cell.font = Font(bold=True, color="FFFFFF", size=16)
        cell.alignment = Alignment(horizontal='center')
    current_row += 1

    if periodo_seleccionado:
        periodo_cell = worksheet.cell(row=current_row, column=1, value=f"Período: {periodo_seleccionado.nombrePeriodo}")
        periodo_cell.font = Font(bold=True)
        periodo_cell.alignment = Alignment(horizontal='center')
        # Aplicar a todas las celdas de la fila
        for col in range(1, 7):
            cell = worksheet.cell(row=current_row, column=col)
            cell.font = Font(bold=True)
            cell.alignment = Alignment(horizontal='center')
        current_row += 1
        
        fecha_cell = worksheet.cell(row=current_row, column=1, value=f"Fecha: {periodo_seleccionado.fechaInicioPeriodo} - {periodo_seleccionado.fechaFinPeriodo}")
        fecha_cell.alignment = Alignment(horizontal='center')
        # Aplicar a todas las celdas de la fila
        for col in range(1, 7):
            cell = worksheet.cell(row=current_row, column=col)
            cell.alignment = Alignment(horizontal='center')
        current_row += 1

    moneda_cell = worksheet.cell(row=current_row, column=1, value=f"Moneda: {simbolo} (Moneda Nacional)")
    moneda_cell.font = Font(bold=True)
    moneda_cell.alignment = Alignment(horizontal='center')
    # Aplicar a todas las celdas de la fila
    for col in range(1, 7):
        cell = worksheet.cell(row=current_row, column=col)
        cell.font = Font(bold=True)
        cell.alignment = Alignment(horizontal='center')
    current_row += 1

    current_row += 1  # Espacio

    # Encabezados de la tabla - ESTA ES LA LÍNEA QUE CAUSABA EL ERROR
    headers = ['N° Asiento', 'Fecha', 'Concepto', 'Cuenta', 'Debe', 'Haber']
    for col_num, header in enumerate(headers, 1):
        # CORRECCIÓN: Usar current_row que sabemos que no está en un rango combinado
        cell = worksheet.cell(row=current_row, column=col_num, value=header)
        cell.font = header_font
        cell.fill = header_fill
        cell.border = border
        cell.alignment = Alignment(horizontal='center')
    
    current_row += 1

    # Datos
    for asiento_data in asientos_procesados:
        asiento = asiento_data['asiento']
        for detalle_data in asiento_data['detalles']:
            detalle = detalle_data['detalle']
            worksheet.cell(row=current_row, column=1, value=asiento.numeroAsiento).border = border
            worksheet.cell(row=current_row, column=2, value=asiento.fechaAsiento.strftime("%d/%m/%Y")).border = border
            worksheet.cell(row=current_row, column=3, value=asiento.conceptoAsiento).border = border
            worksheet.cell(row=current_row, column=4, value=f"{detalle.idPlanCuenta.codigoPlanCuenta} - {detalle.idPlanCuenta.nombrePlanCuenta}").border = border
            worksheet.cell(row=current_row, column=5, value=float(detalle_data['debe_convertido']) if detalle_data['debe_convertido'] else 0).border = border
            worksheet.cell(row=current_row, column=6, value=float(detalle_data['haber_convertido']) if detalle_data['haber_convertido'] else 0).border = border
            current_row += 1

    # Totales
    total_row = current_row
    worksheet.cell(row=total_row, column=3, value="TOTALES:").font = Font(bold=True)
    worksheet.cell(row=total_row, column=5, value=float(total_debe_global)).fill = total_fill
    worksheet.cell(row=total_row, column=6, value=float(total_haber_global)).fill = total_fill
    
    # Aplicar bordes a las celdas de totales
    for col in range(1, 7):
        cell = worksheet.cell(row=total_row, column=col)
        cell.border = border
        if col >= 5:
            cell.fill = total_fill

    # Ajustar anchos de columna
    column_widths = {
        'A': 15,  # N° Asiento
        'B': 12,  # Fecha
        'C': 50,  # Concepto
        'D': 40,  # Cuenta
        'E': 15,  # Debe
        'F': 15   # Haber
    }
    
    for col_letter, width in column_widths.items():
        worksheet.column_dimensions[col_letter].width = width

    # Formato de números para columnas monetarias
    for row in worksheet.iter_rows(min_row=current_row - len(list(asientos)) + 1, max_row=worksheet.max_row, min_col=5, max_col=6):
        for cell in row:
            if isinstance(cell.value, (int, float)):
                cell.number_format = f'#,##0.00"{simbolo}"'

    # Información adicional
    info_row = total_row + 2
    worksheet.cell(row=info_row, column=1, value=f"Generado el: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    worksheet.cell(row=info_row + 1, column=1, value=f"Todos los montos en {simbolo} (Moneda Nacional)")

    # Preparar respuesta
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    
    # Nombre del archivo con período si está disponible
    if periodo_seleccionado:
        filename = f"libro_diario_{periodo_seleccionado.nombrePeriodo}.xlsx"
    else:
        filename = "libro_diario.xlsx"
        
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    workbook.save(response)

    return response

def libro_mayor_pdf(request):
    """
    Vista para generar PDF del Libro Mayor con texto responsive
    """
    search_query = request.GET.get('search', '').strip()
    periodo_id = request.GET.get('periodo')
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')

    # Obtener símbolo de moneda nacional
    moneda_nacional = Moneda.objects.filter(idMoneda=1).first()
    simbolo = moneda_nacional.simboloMoneda if moneda_nacional and getattr(moneda_nacional, 'simboloMoneda', None) else 'Bs'

    if start_date or end_date:
        periodo = None
    else:
        if not periodo_id:
            periodo = periodoContable.objects.filter(estadoPeriodo=True).first()
        else:
            periodo = periodoContable.objects.filter(idPeriodo=periodo_id).first()

    if not periodo and not (start_date or end_date):
        return HttpResponse("No hay períodos contables disponibles.")

    cuentas = PlanCuenta.objects.prefetch_related('subcuentas').filter(cuentaPadre__isnull=True).order_by('codigoPlanCuenta')

    global_total_debe = decimal.Decimal('0.00')
    global_total_haber = decimal.Decimal('0.00')

    # FUNCIONES DE CONVERSIÓN (copiadas de libro_mayor)
    def convertir_formato_numero(valor):
        if valor is None:
            return decimal.Decimal('0.00')
        
        if isinstance(valor, (int, float, decimal.Decimal)):
            return decimal.Decimal(str(valor)).quantize(decimal.Decimal('0.0000000001'))
        
        if isinstance(valor, str):
            valor_limpio = valor.strip().replace('.', '').replace(',', '.')
            try:
                return decimal.Decimal(valor_limpio).quantize(decimal.Decimal('0.0000000001'))
            except (decimal.InvalidOperation, ValueError):
                try:
                    return decimal.Decimal(valor).quantize(decimal.Decimal('0.0000000001'))
                except (decimal.InvalidOperation, ValueError):
                    return decimal.Decimal('0.00')
        
        try:
            return decimal.Decimal(str(valor)).quantize(decimal.Decimal('0.0000000001'))
        except (decimal.InvalidOperation, ValueError, TypeError):
            return decimal.Decimal('0.00')

    def convertir_a_moneda_nacional(detalle_asiento):
        debe_original = convertir_formato_numero(detalle_asiento.debe)
        haber_original = convertir_formato_numero(detalle_asiento.haber)
        
        # Si la moneda es la nacional (idMoneda=1), no hay conversión necesaria
        if detalle_asiento.idMoneda_id == 1:
            return {
                'debe': debe_original,
                'haber': haber_original
            }
        
        # Si tiene moneda diferente a 1, buscar el pago relacionado
        pago = Pago.objects.filter(idAsiento=detalle_asiento.idAsiento).first()
        
        if pago and pago.idTasa:
            # Obtener la tasa de cambio del pago
            tasa_cambio = Tasa.objects.filter(idTasa=pago.idTasa_id).first()
            if tasa_cambio and hasattr(tasa_cambio, 'montoTasa'):
                # Convertir la tasa del formato español
                tasa_valor = convertir_formato_numero(tasa_cambio.montoTasa)
                
                # Convertir los montos usando la tasa de cambio
                return {
                    'debe': debe_original * tasa_valor,
                    'haber': haber_original * tasa_valor
                }
        
        # Si no se encuentra tasa de cambio, usar los valores originales
        return {
            'debe': debe_original,
            'haber': haber_original
        }

    def calcular_saldos(cuenta, nivel=0):
        nonlocal global_total_debe, global_total_haber

        movimientos = DetalleAsiento.objects.filter(idPlanCuenta=cuenta)

        if periodo:
            movimientos = movimientos.filter(idAsiento__idPeriodo=periodo)
        if start_date:
            movimientos = movimientos.filter(idAsiento__fechaAsiento__gte=start_date)
        if end_date:
            movimientos = movimientos.filter(idAsiento__fechaAsiento__lte=end_date)

        movimientos = movimientos.order_by('idAsiento__fechaAsiento', 'idAsiento__numeroAsiento')

        saldo_inicial = decimal.Decimal('0.00')
        saldo_final = saldo_inicial
        total_debe = decimal.Decimal('0.00')
        total_haber = decimal.Decimal('0.00')
        detalles = []

        asientos_ids = movimientos.values_list('idAsiento__idAsiento', flat=True)
        movimientos_relacionados = {}

        if asientos_ids:
            todos_movimientos_asiento = DetalleAsiento.objects.filter(
                idAsiento__idAsiento__in=asientos_ids
            ).select_related('idPlanCuenta', 'idAsiento')

            for mov in todos_movimientos_asiento:
                if mov.idAsiento.idAsiento not in movimientos_relacionados:
                    movimientos_relacionados[mov.idAsiento.idAsiento] = []
                movimientos_relacionados[mov.idAsiento.idAsiento].append(mov)

        for movimiento in movimientos:
            # Convertir montos a moneda nacional
            montos_convertidos = convertir_a_moneda_nacional(movimiento)
            debe_convertido = montos_convertidos['debe']
            haber_convertido = montos_convertidos['haber']
            
            saldo_anterior = saldo_final
            saldo_final += debe_convertido - haber_convertido
            total_debe += debe_convertido
            total_haber += haber_convertido

            movimientos_asiento_completo = movimientos_relacionados.get(movimiento.idAsiento.idAsiento, [])
            
            movimientos_completos_json = [
                {
                    'cuenta': mov_rel.idPlanCuenta.codigoPlanCuenta + ' - ' + mov_rel.idPlanCuenta.nombrePlanCuenta,
                    'debe': float(mov_rel.debe),
                    'haber': float(mov_rel.haber)
                }
                for mov_rel in movimientos_asiento_completo
                if mov_rel.idPlanCuenta.codigoPlanCuenta != cuenta.codigoPlanCuenta
            ]

            beneficiario = None
            try:
                pago = Pago.objects.filter(idAsiento=movimiento.idAsiento).first()
                if pago and pago.idNota:
                    nota = pago.idNota
                    if nota.idPersona:
                        beneficiario = f"{nota.idPersona.cedula} - {nota.idPersona.nombres} {nota.idPersona.apellidos}"
                    elif nota.idEmpresa:
                        beneficiario = f"{nota.idEmpresa.rifEmpresa} - {nota.idEmpresa.nombreEmpresa}"
            except:
                pass

            detalles.append({
                'fecha': movimiento.idAsiento.fechaAsiento,
                'concepto': movimiento.idAsiento.conceptoAsiento,
                'beneficiario': beneficiario,
                'debe': debe_convertido,
                'haber': haber_convertido,
                'saldo': saldo_final,
                'id_asiento': movimiento.idAsiento.idAsiento,
                'movimientos_completos': movimientos_completos_json
            })

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
            'subcuentas': subcuentas,
            'nivel': nivel
        }

    def buscar_en_cuentas(cuentas_data, search_query):
        resultados = []
        for cuenta in cuentas_data:
            if (search_query.lower() in cuenta['cuenta'].nombrePlanCuenta.lower() or 
                search_query.lower() in cuenta['cuenta'].codigoPlanCuenta.lower() or
                any(search_query.lower() in str(detalle.get('debe', '')).lower() or
                    search_query.lower() in str(detalle.get('haber', '')).lower() or
                    search_query.lower() in str(detalle.get('saldo', '')).lower() or
                    search_query.lower() in detalle.get('concepto', '').lower()
                    for detalle in cuenta['detalles'])):
                resultados.append(cuenta)

            subcuentas_resultados = buscar_en_cuentas(cuenta.get('subcuentas', []), search_query)
            resultados.extend(subcuentas_resultados)

        return resultados

    cuentas_data = [calcular_saldos(cuenta) for cuenta in cuentas]

    if search_query:
        cuentas_data = buscar_en_cuentas(cuentas_data, search_query)

    response = HttpResponse(content_type='application/pdf')
    
    if periodo:
        filename = f"libro_mayor_{periodo.nombrePeriodo}.pdf"
    else:
        filename = "libro_mayor.pdf"
        
    response['Content-Disposition'] = f'inline; filename="{filename}"'

    from reportlab.lib.pagesizes import landscape, letter
    p = canvas.Canvas(response, pagesize=landscape(letter))
    p.setTitle("Reporte de libro mayor.")
    width, height = landscape(letter)
    
    logo_width, logo_height, logo_margin = 80, 80, 15
    min_margin = 30
    safe_left = min_margin
    safe_right = width - min_margin
    safe_width = safe_right - safe_left
    safe_center = width / 2

    config = Configuracion.objects.order_by('-fechaConfiguracion').first()
    logo_path = config.logo.path if config and config.logo else None
    firma_path = config.firma.path if config and config.firma else None
    nombre_institucion = config.nombreInstitucion if config else "Institución"
    rif_institucion = config.rif if config else ""
    direccion1 = "AV. ALBERTO RAVELL CON AV. INTERCOMUNAL JOSE ANTONIO PAEZ"
    direccion2 = "LOCAL UPTYAB, INDEPENDENCIA – EDO YARACUY"

    def draw_header():
        if logo_path and os.path.exists(logo_path):
            p.drawImage(
                logo_path,
                width - logo_width - logo_margin,
                height - logo_height - logo_margin,
                width=logo_width,
                height=logo_height,
                preserveAspectRatio=True,
                mask='auto'
            )
        
        text_top = height - logo_margin - 15
        p.setFont("Helvetica-Bold", 10)
        p.drawString(min_margin, text_top, nombre_institucion)
        p.drawString(min_margin, text_top - 15, f"RIF: {rif_institucion}")
        p.drawString(min_margin, text_top - 30, direccion1)
        p.drawString(min_margin, text_top - 45, direccion2)
        
        p.setFont("Helvetica-Bold", 14)
        p.drawCentredString(safe_center, text_top - 85, "LIBRO MAYOR")
        
        p.setFont("Helvetica", 10)
        periodo_info = ""
        if periodo:
            periodo_info = f"Período: {periodo.nombrePeriodo} - Del {periodo.fechaInicioPeriodo.strftime('%d/%m/%Y')} al {periodo.fechaFinPeriodo.strftime('%d/%m/%Y')}"
        else:
            if start_date and end_date:
                periodo_info = f"Período: Del {start_date} al {end_date}"
            else:
                periodo_info = "Período: Todos los movimientos"
        p.drawCentredString(safe_center, text_top - 105, periodo_info)
        
        # Información de moneda
        p.setFont("Helvetica", 9)
        p.drawCentredString(safe_center, text_top - 120, f"Todos los montos en {simbolo} (Moneda Nacional)")

    def draw_footer():
        if firma_path and os.path.exists(firma_path):
            p.setFont("Helvetica-Oblique", 9)
            p.drawCentredString(width/2, 35, "Firma autorizada")
        
        p.setFont("Helvetica", 8)
        fecha_generacion = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        p.drawString(min_margin, 20, f"Generado el: {fecha_generacion}")

    # Preparar datos de la tabla con Paragraph para texto responsive
    from reportlab.platypus import Paragraph
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

    styles = getSampleStyleSheet()
    normal_style = ParagraphStyle(
        'Normal',
        parent=styles['Normal'],
        fontSize=7,
        leading=8,
        wordWrap='LTR',
        alignment=0,
    )
    
    header_style = ParagraphStyle(
        'Header',
        parent=styles['Normal'],
        fontSize=8,
        leading=9,
        wordWrap='LTR',
        textColor=colors.white,
        alignment=1,
        fontName='Helvetica-Bold'
    )
    
    center_style = ParagraphStyle(
        'Center',
        parent=normal_style,
        alignment=1,
    )

    def agregar_datos_cuenta(cuenta_data, data, nivel=0):
        cuenta = cuenta_data['cuenta']
        indent = "&nbsp;" * nivel * 2
        
        # Fila de la cuenta principal
        data.append([
            Paragraph(f"{indent}{cuenta.codigoPlanCuenta}", normal_style),
            Paragraph(f"{indent}{cuenta.nombrePlanCuenta}", normal_style),
            Paragraph("", normal_style),
            Paragraph("", normal_style),
            Paragraph("", normal_style),
            Paragraph("", normal_style),
            Paragraph("", normal_style)
        ])
        
        # Saldo inicial
        data.append([
            Paragraph("", normal_style),
            Paragraph(f"{indent}&nbsp;&nbsp;Saldo Inicial", normal_style),
            Paragraph("", normal_style),
            Paragraph("", normal_style),
            Paragraph("", normal_style),
            Paragraph("", normal_style),
            Paragraph(f"{simbolo} {cuenta_data['saldo_inicial']:,.2f}", normal_style)
        ])
        
        # Movimientos/detalles
        for detalle in cuenta_data['detalles']:
            concepto = detalle['concepto']
            beneficiario = detalle['beneficiario'] or ""
            
            data.append([
                Paragraph("", normal_style),
                Paragraph(f"{indent}&nbsp;&nbsp;{cuenta.nombrePlanCuenta}", normal_style),
                Paragraph(detalle['fecha'].strftime("%d/%m/%Y"), center_style),
                Paragraph(concepto, normal_style),
                Paragraph(f"{simbolo} {detalle['debe']:,.2f}" if detalle['debe'] else "", center_style),
                Paragraph(f"{simbolo} {detalle['haber']:,.2f}" if detalle['haber'] else "", center_style),
                Paragraph(f"{simbolo} {detalle['saldo']:,.2f}", normal_style)
            ])
        
        # Saldo final
        naturaleza = "Deudor" if cuenta_data['saldo_final'] > 0 else "Acreedor" if cuenta_data['saldo_final'] < 0 else "Saldado"
        data.append([
            Paragraph("", normal_style),
            Paragraph(f"{indent}&nbsp;&nbsp;Saldo Final", normal_style),
            Paragraph("", normal_style),
            Paragraph("", normal_style),
            Paragraph("", normal_style),
            Paragraph("", normal_style),
            Paragraph(f"{simbolo} {cuenta_data['saldo_final']:,.2f} ({naturaleza})", normal_style)
        ])
        
        # Espacio entre cuentas
        data.append([
            Paragraph("", normal_style),
            Paragraph("", normal_style),
            Paragraph("", normal_style),
            Paragraph("", normal_style),
            Paragraph("", normal_style),
            Paragraph("", normal_style),
            Paragraph("", normal_style)
        ])
        
        # Subcuentas
        for subcuenta in cuenta_data['subcuentas']:
            agregar_datos_cuenta(subcuenta, data, nivel + 1)

    # Construir datos de la tabla
    headers = [
        Paragraph("Código", header_style),
        Paragraph("Nombre", header_style),
        Paragraph("Fecha", header_style),
        Paragraph("Concepto", header_style),
        Paragraph("Debe", header_style),
        Paragraph("Haber", header_style),
        Paragraph("Saldo", header_style)
    ]
    data = [headers]

    for cuenta_data in cuentas_data:
        agregar_datos_cuenta(cuenta_data, data)

    # Totales generales
    data.append([
        Paragraph('TOTALES GENERALES:', normal_style),
        Paragraph('', normal_style),
        Paragraph('', normal_style),
        Paragraph('', normal_style),
        Paragraph(f"{simbolo} {global_total_debe:,.2f}", center_style),
        Paragraph(f"{simbolo} {global_total_haber:,.2f}", center_style),
        Paragraph('', normal_style)
    ])

    # Configuración de la tabla responsive
    col_widths = [80, 150, 60, 120, 60, 60, 80]
    table_width = sum(col_widths)
    
    if table_width > safe_width:
        scale_factor = safe_width / table_width
        col_widths = [int(width * scale_factor) for width in col_widths]
        table_width = sum(col_widths)

    header_height = 150
    footer_height = 100
    cell_padding = 4
    
    available_height = height - header_height - footer_height
    total_rows = len(data) - 1
    page = 0

    for start_row in range(0, total_rows, 15):  # 15 filas por página
        end_row = min(start_row + 15, total_rows)
        page_data = [data[0]] + data[start_row + 1:end_row + 1]
        
        if page > 0:
            p.showPage()
        
        draw_header()
        y_position = height - header_height
        
        table_x = safe_left + (safe_width - table_width) / 2
        table = Table(page_data, colWidths=col_widths)
        
        table_style = TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#fe8330")),
            ('VALIGN', (0,0), (-1,0), 'MIDDLE'),
            ('BOTTOMPADDING', (0,0), (-1,0), cell_padding),
            
            ('BACKGROUND', (0,1), (-1,-2), colors.whitesmoke),
            ('VALIGN', (0,1), (-1,-1), 'TOP'),
            
            ('BACKGROUND', (0,-1), (-1,-1), colors.HexColor("#366092")),
            ('TEXTCOLOR', (0,-1), (-1,-1), colors.white),
            
            ('GRID', (0,0), (-1,-1), 0.5, colors.lightgrey),
            ('BOX', (0,0), (-1,-1), 0.5, colors.black),
            ('TOPPADDING', (0,0), (-1,-1), cell_padding),
            ('BOTTOMPADDING', (0,0), (-1,-1), cell_padding),
            ('LEFTPADDING', (0,0), (-1,-1), 3),
            ('RIGHTPADDING', (0,0), (-1,-1), 3),
        ])
        
        table.setStyle(table_style)
        table.wrapOn(p, width, height)
        table_height = table._height
        
        # Verificar que la tabla no se salga de la página
        if y_position - table_height - 10 < footer_height:
            p.showPage()
            draw_header()
            y_position = height - header_height
        
        table.drawOn(p, table_x, y_position - table_height - 10)
        
        p.setFont("Helvetica", 8)
        pagination_text = f"Página {page + 1} - Registros {start_row + 1} a {end_row} de {total_rows}"
        p.drawCentredString(
            safe_center, 
            y_position - table_height - 25,
            pagination_text
        )
        
        draw_footer()
        page += 1

    p.save()
    return response

def libro_mayor_excel(request):
    """
    Vista para generar Excel del Libro Mayor
    """
    # Obtener parámetros de filtrado
    search_query = request.GET.get('search', '').strip()
    periodo_id = request.GET.get('periodo')
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')

    # Obtener símbolo de moneda nacional
    moneda_nacional = Moneda.objects.filter(idMoneda=1).first()
    simbolo = moneda_nacional.simboloMoneda if moneda_nacional and getattr(moneda_nacional, 'simboloMoneda', None) else 'Bs'

    # Lógica para obtener el período
    if start_date or end_date:
        periodo = None
    else:
        if not periodo_id:
            periodo = periodoContable.objects.filter(estadoPeriodo=True).first()
        else:
            periodo = periodoContable.objects.filter(idPeriodo=periodo_id).first()

    if not periodo and not (start_date or end_date):
        return HttpResponse("No hay períodos contables disponibles.")

    # Obtener cuentas principales
    cuentas = PlanCuenta.objects.prefetch_related('subcuentas').filter(cuentaPadre__isnull=True).order_by('codigoPlanCuenta')

    # Variables globales para acumular totales
    global_total_debe = decimal.Decimal('0.00')
    global_total_haber = decimal.Decimal('0.00')

    # FUNCIONES DE CONVERSIÓN
    def convertir_formato_numero(valor):
        if valor is None:
            return decimal.Decimal('0.00')
        
        if isinstance(valor, (int, float, decimal.Decimal)):
            return decimal.Decimal(str(valor)).quantize(decimal.Decimal('0.0000000001'))
        
        if isinstance(valor, str):
            valor_limpio = valor.strip().replace('.', '').replace(',', '.')
            try:
                return decimal.Decimal(valor_limpio).quantize(decimal.Decimal('0.0000000001'))
            except (decimal.InvalidOperation, ValueError):
                try:
                    return decimal.Decimal(valor).quantize(decimal.Decimal('0.0000000001'))
                except (decimal.InvalidOperation, ValueError):
                    return decimal.Decimal('0.00')
        
        try:
            return decimal.Decimal(str(valor)).quantize(decimal.Decimal('0.0000000001'))
        except (decimal.InvalidOperation, ValueError, TypeError):
            return decimal.Decimal('0.00')

    def convertir_a_moneda_nacional(detalle_asiento):
        debe_original = convertir_formato_numero(detalle_asiento.debe)
        haber_original = convertir_formato_numero(detalle_asiento.haber)
        
        # Si la moneda es la nacional (idMoneda=1), no hay conversión necesaria
        if detalle_asiento.idMoneda_id == 1:
            return {
                'debe': debe_original,
                'haber': haber_original
            }
        
        # Si tiene moneda diferente a 1, buscar el pago relacionado
        pago = Pago.objects.filter(idAsiento=detalle_asiento.idAsiento).first()
        
        if pago and pago.idTasa:
            # Obtener la tasa de cambio del pago
            tasa_cambio = Tasa.objects.filter(idTasa=pago.idTasa_id).first()
            if tasa_cambio and hasattr(tasa_cambio, 'montoTasa'):
                # Convertir la tasa del formato español
                tasa_valor = convertir_formato_numero(tasa_cambio.montoTasa)
                
                # Convertir los montos usando la tasa de cambio
                return {
                    'debe': debe_original * tasa_valor,
                    'haber': haber_original * tasa_valor
                }
        
        # Si no se encuentra tasa de cambio, usar los valores originales
        return {
            'debe': debe_original,
            'haber': haber_original
        }

    def calcular_saldos(cuenta, nivel=0):
        nonlocal global_total_debe, global_total_haber

        movimientos = DetalleAsiento.objects.filter(idPlanCuenta=cuenta)

        # Aplicar filtros
        if periodo:
            movimientos = movimientos.filter(idAsiento__idPeriodo=periodo)
        if start_date:
            movimientos = movimientos.filter(idAsiento__fechaAsiento__gte=start_date)
        if end_date:
            movimientos = movimientos.filter(idAsiento__fechaAsiento__lte=end_date)

        movimientos = movimientos.order_by('idAsiento__fechaAsiento', 'idAsiento__numeroAsiento')

        saldo_inicial = decimal.Decimal('0.00')
        saldo_final = saldo_inicial
        total_debe = decimal.Decimal('0.00')
        total_haber = decimal.Decimal('0.00')
        detalles = []

        # Obtener movimientos relacionados para contrapartidas
        asientos_ids = movimientos.values_list('idAsiento__idAsiento', flat=True)
        movimientos_relacionados = {}

        if asientos_ids:
            todos_movimientos_asiento = DetalleAsiento.objects.filter(
                idAsiento__idAsiento__in=asientos_ids
            ).select_related('idPlanCuenta', 'idAsiento')

            for mov in todos_movimientos_asiento:
                if mov.idAsiento.idAsiento not in movimientos_relacionados:
                    movimientos_relacionados[mov.idAsiento.idAsiento] = []
                movimientos_relacionados[mov.idAsiento.idAsiento].append(mov)

        # Procesar cada movimiento
        for movimiento in movimientos:
            # Convertir montos a moneda nacional
            montos_convertidos = convertir_a_moneda_nacional(movimiento)
            debe_convertido = montos_convertidos['debe']
            haber_convertido = montos_convertidos['haber']
            
            saldo_anterior = saldo_final
            saldo_final += debe_convertido - haber_convertido
            total_debe += debe_convertido
            total_haber += haber_convertido

            # Obtener movimientos completos del asiento para contrapartidas
            movimientos_asiento_completo = movimientos_relacionados.get(movimiento.idAsiento.idAsiento, [])
            
            movimientos_completos_json = [
                {
                    'cuenta': mov_rel.idPlanCuenta.codigoPlanCuenta + ' - ' + mov_rel.idPlanCuenta.nombrePlanCuenta,
                    'debe': float(mov_rel.debe),
                    'haber': float(mov_rel.haber)
                }
                for mov_rel in movimientos_asiento_completo
                if mov_rel.idPlanCuenta.codigoPlanCuenta != cuenta.codigoPlanCuenta
            ]

            # Obtener beneficiario
            beneficiario = None
            try:
                from apps.factura.models import Pago
                pago = Pago.objects.filter(idAsiento=movimiento.idAsiento).first()
                if pago and pago.idNota:
                    nota = pago.idNota
                    if nota.idPersona:
                        beneficiario = f"{nota.idPersona.cedula} - {nota.idPersona.nombres} {nota.idPersona.apellidos}"
                    elif nota.idEmpresa:
                        beneficiario = f"{nota.idEmpresa.rifEmpresa} - {nota.idEmpresa.nombreEmpresa}"
            except:
                pass

            detalles.append({
                'fecha': movimiento.idAsiento.fechaAsiento,
                'concepto': movimiento.idAsiento.conceptoAsiento,
                'beneficiario': beneficiario,
                'debe': debe_convertido,
                'haber': haber_convertido,
                'saldo': saldo_final,
                'id_asiento': movimiento.idAsiento.idAsiento,
                'movimientos_completos': movimientos_completos_json
            })

        # Sumar al total global
        global_total_debe += total_debe
        global_total_haber += total_haber

        # Procesar subcuentas recursivamente
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
            'subcuentas': subcuentas,
            'nivel': nivel
        }

    def buscar_en_cuentas(cuentas_data, search_query):
        """Función recursiva para buscar en cuentas y subcuentas"""
        resultados = []
        for cuenta in cuentas_data:
            if (search_query.lower() in cuenta['cuenta'].nombrePlanCuenta.lower() or 
                search_query.lower() in cuenta['cuenta'].codigoPlanCuenta.lower() or
                any(search_query.lower() in str(detalle.get('debe', '')).lower() or
                    search_query.lower() in str(detalle.get('haber', '')).lower() or
                    search_query.lower() in str(detalle.get('saldo', '')).lower() or
                    search_query.lower() in detalle.get('concepto', '').lower()
                    for detalle in cuenta['detalles'])):
                resultados.append(cuenta)

            # Buscar en subcuentas
            subcuentas_resultados = buscar_en_cuentas(cuenta.get('subcuentas', []), search_query)
            resultados.extend(subcuentas_resultados)

        return resultados

    # Calcular saldos para todas las cuentas principales
    cuentas_data = [calcular_saldos(cuenta) for cuenta in cuentas]

    # Aplicar búsqueda si existe
    if search_query:
        cuentas_data = buscar_en_cuentas(cuentas_data, search_query)

    # Crear libro de Excel
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = "Libro Mayor"

    # Estilos
    header_font = Font(bold=True, color="FFFFFF")
    header_fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
    total_fill = PatternFill(start_color="D9E1F2", end_color="D9E1F2", fill_type="solid")
    border = Border(left=Side(style='thin'), right=Side(style='thin'), 
                   top=Side(style='thin'), bottom=Side(style='thin'))
    
    # Estilo para cuentas principales
    cuenta_principal_fill = PatternFill(start_color="FFE699", end_color="FFE699", fill_type="solid")
    # Estilo para subcuentas
    subcuenta_fill = PatternFill(start_color="E2EFDA", end_color="E2EFDA", fill_type="solid")

    # Título e información
    worksheet.cell(row=1, column=1, value="LIBRO MAYOR").font = Font(bold=True, size=16)
    worksheet.merge_cells('A1:I1')
    
    row_num = 2
    if periodo:
        worksheet.cell(row=row_num, column=1, value=f"Período: {periodo.nombrePeriodo}")
        worksheet.merge_cells('A2:I2')
        row_num += 1
    else:
        if start_date and end_date:
            worksheet.cell(row=row_num, column=1, value=f"Período: Del {start_date} al {end_date}")
            worksheet.merge_cells('A2:I2')
            row_num += 1
        else:
            worksheet.cell(row=row_num, column=1, value="Período: Todos los movimientos")
            worksheet.merge_cells('A2:I2')
            row_num += 1

    worksheet.cell(row=row_num, column=1, value=f"Moneda: {simbolo} (Moneda Nacional)")
    worksheet.merge_cells('A3:I3')
    row_num += 1
    
    row_num += 1  # Espacio

    # Encabezados
    headers = ['Código', 'Nombre', 'Fecha', 'Concepto', 'Beneficiario', 'Debe', 'Haber', 'Saldo', 'Naturaleza']
    for col_num, header in enumerate(headers, 1):
        cell = worksheet.cell(row=row_num, column=col_num, value=header)
        cell.font = header_font
        cell.fill = header_fill
        cell.border = border
        cell.alignment = Alignment(horizontal='center')

    row_num += 1

    # Función recursiva para escribir datos en Excel
    def escribir_cuenta_excel(worksheet, cuenta_data, row_num):
        nivel = cuenta_data['nivel']
        cuenta = cuenta_data['cuenta']
        
        # Escribir información de la cuenta
        indent = "  " * nivel
        worksheet.cell(row=row_num, column=1, value=cuenta.codigoPlanCuenta)
        worksheet.cell(row=row_num, column=2, value=f"{indent}{cuenta.nombrePlanCuenta}")
        
        # Aplicar estilo según el nivel
        if nivel == 0:
            fill_style = cuenta_principal_fill
        else:
            fill_style = subcuenta_fill
            
        for col in range(1, 10):
            worksheet.cell(row=row_num, column=col).fill = fill_style
            worksheet.cell(row=row_num, column=col).border = border
        
        row_num += 1

        # Escribir saldos inicial y final como filas especiales
        # Saldo inicial
        worksheet.cell(row=row_num, column=2, value=f"{indent}  Saldo Inicial")
        worksheet.cell(row=row_num, column=8, value=float(cuenta_data['saldo_inicial']))
        naturaleza_inicial = "Deudor" if cuenta_data['saldo_inicial'] > 0 else "Acreedor" if cuenta_data['saldo_inicial'] < 0 else "Saldado"
        worksheet.cell(row=row_num, column=9, value=naturaleza_inicial)
        
        for col in range(1, 10):
            worksheet.cell(row=row_num, column=col).border = border
            worksheet.cell(row=row_num, column=col).fill = subcuenta_fill
            
        row_num += 1

        # Escribir movimientos/detalles
        for detalle in cuenta_data['detalles']:
            worksheet.cell(row=row_num, column=1, value=cuenta.codigoPlanCuenta)
            worksheet.cell(row=row_num, column=2, value=f"{indent}  {cuenta.nombrePlanCuenta}")
            worksheet.cell(row=row_num, column=3, value=detalle['fecha'].strftime("%d/%m/%Y"))
            worksheet.cell(row=row_num, column=4, value=detalle['concepto'])
            worksheet.cell(row=row_num, column=5, value=detalle['beneficiario'] or '')
            worksheet.cell(row=row_num, column=6, value=float(detalle['debe']) if detalle['debe'] else 0)
            worksheet.cell(row=row_num, column=7, value=float(detalle['haber']) if detalle['haber'] else 0)
            worksheet.cell(row=row_num, column=8, value=float(detalle['saldo']))
            naturaleza = "Deudor" if detalle['saldo'] > 0 else "Acreedor" if detalle['saldo'] < 0 else "Saldado"
            worksheet.cell(row=row_num, column=9, value=naturaleza)
            
            for col in range(1, 10):
                worksheet.cell(row=row_num, column=col).border = border
                
            row_num += 1

        # Escribir saldo final
        worksheet.cell(row=row_num, column=2, value=f"{indent}  Saldo Final")
        worksheet.cell(row=row_num, column=8, value=float(cuenta_data['saldo_final']))
        naturaleza_final = "Deudor" if cuenta_data['saldo_final'] > 0 else "Acreedor" if cuenta_data['saldo_final'] < 0 else "Saldado"
        worksheet.cell(row=row_num, column=9, value=naturaleza_final)
        
        for col in range(1, 10):
            worksheet.cell(row=row_num, column=col).border = border
            worksheet.cell(row=row_num, column=col).fill = subcuenta_fill
            
        row_num += 1

        # Espacio entre cuentas
        row_num += 1

        # Procesar subcuentas recursivamente
        for subcuenta in cuenta_data['subcuentas']:
            row_num = escribir_cuenta_excel(worksheet, subcuenta, row_num)

        return row_num

    # Escribir datos en Excel
    row_num = 6  # Después de encabezados y espacio
    for cuenta_data in cuentas_data:
        row_num = escribir_cuenta_excel(worksheet, cuenta_data, row_num)

    # Escribir totales generales
    worksheet.cell(row=row_num, column=2, value="TOTALES GENERALES:").font = Font(bold=True)
    worksheet.cell(row=row_num, column=6, value=float(global_total_debe)).fill = total_fill
    worksheet.cell(row=row_num, column=7, value=float(global_total_haber)).fill = total_fill
    
    for col in range(1, 10):
        worksheet.cell(row=row_num, column=col).border = border

    # Ajustar anchos de columna
    column_widths = {
        'A': 15,  # Código
        'B': 40,  # Nombre
        'C': 12,  # Fecha
        'D': 30,  # Concepto
        'E': 25,  # Beneficiario
        'F': 15,  # Debe
        'G': 15,  # Haber
        'H': 15,  # Saldo
        'I': 12   # Naturaleza
    }
    
    for col_letter, width in column_widths.items():
        worksheet.column_dimensions[col_letter].width = width

    # Formato de números para columnas monetarias
    for row in worksheet.iter_rows(min_row=6, max_row=worksheet.max_row, min_col=6, max_col=8):
        for cell in row:
            if isinstance(cell.value, (int, float)):
                cell.number_format = f'#,##0.00"{simbolo}"'

    # Información adicional
    info_row = row_num + 2
    worksheet.cell(row=info_row, column=1, value=f"Generado el: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    worksheet.cell(row=info_row + 1, column=1, value=f"Todos los montos en {simbolo} (Moneda Nacional)")

    # Preparar respuesta
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    
    # Nombre del archivo con período si está disponible
    if periodo:
        filename = f"libro_mayor_{periodo.nombrePeriodo}.xlsx"
    else:
        filename = "libro_mayor.xlsx"
        
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    workbook.save(response)

    return response

def get_filtros_periodo(request):
    """Obtiene y valida los parámetros de filtro de período"""
    periodo_id = request.GET.get('periodo')
    search_query = request.GET.get('search', '').strip()
    
    # Obtener período
    if periodo_id:
        periodo = get_object_or_404(periodoContable, idPeriodo=periodo_id)
    else:
        periodo = periodoContable.objects.filter(estadoPeriodo=True).first()
    
    return {
        'periodo': periodo,
        'search_query': search_query,
        'periodo_id': periodo_id
    }

def aplicar_filtros_asientos(asientos, request):
    """Aplica filtros comunes a los asientos contables"""
    search_query = request.GET.get('search', '').strip()
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    periodo_id = request.GET.get('periodo')

    # Aplicar filtros
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

    if start_date:
        asientos = asientos.filter(fechaAsiento__gte=start_date)
    if end_date:
        asientos = asientos.filter(fechaAsiento__lte=end_date)
    if periodo_id:
        asientos = asientos.filter(idPeriodo__idPeriodo=periodo_id)

    return asientos