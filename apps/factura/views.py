from decimal import Decimal
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, HttpResponse
from django.db import transaction
from django.db.models import Max
import uuid
from django.urls import reverse
from django.utils.timezone import now
from django.core.exceptions import ValidationError
from django.views.decorators.http import require_POST

from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import landscape, letter
from reportlab.platypus import Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.units import inch
import os

from apps.cuentaBanco.models import CuentaBanco
from apps.periodoContable.models import periodoContable
from .models import Factura, FacturaDetalle, Pago, ParametroTributario, Nota
from .forms import FacturaForm, FacturaDetalleForm, PagoForm, ParametroTributarioForm, NotaForm
from apps.asientoContable.models import AsientoContable, DetalleAsiento
from apps.home.models import Configuracion, Moneda, Tasa
from apps.persona.models import Personas
from apps.empresa.models import empresa
from apps.planCuenta.models import PlanCuenta



def factura_cargando(request):
    """
    Vista para mostrar la ventana de carga mientras se genera la factura.
    """
    return render(request, 'factura/cargando.html')

def factura_list(request):
    """
    Vista para listar todas las facturas junto con sus detalles.
    """
    facturas = Factura.objects.prefetch_related('detalles').all()  # 'detalles' es el related_name definido en el modelo
    facturas_data = [
        {
            'pk': factura.pk,
            'numeroFactura': factura.numeroFactura,
            'fechaEmision': factura.fechaEmision.strftime('%d/%m/%Y'),
            'idPersonaCedula': factura.idPersona.cedula if factura.idPersona else "N/A",
            'idEmpresa': factura.idEmpresa.nombreEmpresa if factura.idEmpresa else "N/A",
            'totalVenta': float(factura.totalVenta),
            'estado': factura.estado,
            'detalles': [
                {
                    'descripcion': detalle.descripcion,
                    'cantidad': float(detalle.cantidad),
                    'precioUnitario': float(detalle.precioUnitario),
                    'subtotal': float(detalle.subtotal),
                }
                for detalle in factura.detalles.all()
            ],
        }
        for factura in facturas
    ]
    return render(request, 'factura/tablaFactura.html', {'facturas': facturas_data})
def nota_list(request):
    """
    Vista para listar todas las facturas junto con sus detalles.
    """
    facturas = Nota.objects.prefetch_related('detalles').all()  # 'detalles' es el related_name definido en el modelo
    facturas_data = [
        {
            'pk': factura.pk,
            'numeroFactura': factura.numeroFactura,
            'fechaEmision': factura.fechaEmision.strftime('%d/%m/%Y'),
            'idPersonaCedula': factura.idPersona.cedula if factura.idPersona else "N/A",
            'idEmpresa': factura.idEmpresa.nombreEmpresa if factura.idEmpresa else "N/A",
            'totalVenta': float(factura.totalVenta),
            'estado': factura.estado,
            'detalles': [
                {
                    'descripcion': detalle.descripcion,
                    'cantidad': float(detalle.cantidad),
                    'precioUnitario': float(detalle.precioUnitario),
                    'subtotal': float(detalle.subtotal),
                }
                for detalle in factura.detalles.all()
            ],
        }
        for factura in facturas
    ]
    return render(request, 'factura/tablaFactura.html', {'facturas': facturas_data})
def factura_detail(request, pk):
    """
    Vista para mostrar los detalles de una factura específica.
    """
    factura = get_object_or_404(Factura, pk=pk)
    detalles = FacturaDetalle.objects.filter(idFactura=factura)
    return render(request, 'factura/detalleFactura.html', {'factura': factura, 'detalles': detalles})

def generar_numero_factura():
    # Generar un número único basado en la fecha y un UUID
    fecha_actual = now().strftime('%Y%m%d')  # Formato: YYYYMMDD
    numero_unico = uuid.uuid4().hex[:6].upper()  # Tomar los primeros 6 caracteres del UUID
    return f"FAC-{fecha_actual}-{numero_unico}"
def generar_numero_nota():
    # Generar un número único basado en la fecha y un UUID
    fecha_actual = now().strftime('%Y%m%d')  # Formato: YYYYMMDD
    numero_unico = uuid.uuid4().hex[:6].upper()  # Tomar los primeros 6 caracteres del UUID
    return f"NOTA-{fecha_actual}-{numero_unico}"


@transaction.atomic
def notas_create(request):
    personas = Personas.objects.all()
    empresas = empresa.objects.all()
    tasas = Tasa.objects.select_related('idMoneda') \
        .values('idMoneda__idMoneda', 'idMoneda__nombreMoneda') \
        .annotate(ultima_idTasa=Max('idTasa'), ultima_tasa=Max('montoTasa'))
    cuentas_plan = PlanCuenta.objects.filter(estadoPlanCuenta=True).order_by('codigoPlanCuenta')
    numero_nota = generar_numero_nota()  # Generar el número de nota

    if request.method == 'POST':
        form = NotaForm(request.POST)
        if form.is_valid():
            try:
                nota = form.save(commit=False)

                # Verificar si hay un periodo contable activo
                periodo_activo = periodoContable.objects.filter(estadoPeriodo=True).first()
                if not periodo_activo:
                    periodo_activo = periodoContable.objects.order_by('-idPeriodo').first()
                if not periodo_activo:
                    return JsonResponse({
                        'success': False,
                        'message': 'No hay ningún periodo contable registrado o activo en el sistema. '
                                   'Por favor, registre o active un periodo contable antes de continuar.'
                    }, status=400)

                # Verificar que las cuentas contables estén presentes en la solicitud
                if 'idPlanCuentaDebe' not in request.POST or 'idPlanCuentaHaber' not in request.POST:
                    return JsonResponse({
                        'success': False,
                        'message': 'Debe seleccionar las cuentas contables para el debe y el haber. '
                                   'Asegúrese de que los campos "idPlanCuentaDebe" y "idPlanCuentaHaber" estén presentes.'
                    }, status=400)

                # Crear el asiento contable
                try:
                    asiento = AsientoContable.objects.create(
                        numeroAsiento=f"NOTA-{numero_nota}",
                        fechaAsiento=nota.fechaEmision,
                        conceptoAsiento=f"Asiento para la nota {numero_nota}",
                        idPeriodo=periodo_activo
                    )
                except Exception as e:
                    return JsonResponse({
                        'success': False,
                        'message': f'Error al crear el asiento contable: {str(e)}. '
                                   'Por favor, revise los datos ingresados e inténtelo nuevamente.'
                    }, status=500)

                # Crear los detalles del asiento contable
                try:
                    DetalleAsiento.objects.create(
                        idAsiento=asiento,
                        idPlanCuenta_id=request.POST['idPlanCuentaDebe'],
                        debe=nota.totalNota,
                        haber=0.00
                    )
                    DetalleAsiento.objects.create(
                        idAsiento=asiento,
                        idPlanCuenta_id=request.POST['idPlanCuentaHaber'],
                        debe=0.00,
                        haber=nota.totalNota
                    )
                except Exception as e:
                    return JsonResponse({
                        'success': False,
                        'message': f'Error al crear los detalles del asiento contable: {str(e)}. '
                                   'Por favor, revise las cuentas contables seleccionadas.'
                    }, status=500)

                # Asociar el asiento contable a la nota
                nota.idAsiento = asiento
                nota.numeroNota = numero_nota
                nota.save()

                return JsonResponse({
                    'success': True,
                    'message': 'Nota creada exitosamente.',
                    'redirect_url': reverse('nota_list'),
                    'nota': {
                        'idNota': nota.idNota,
                        'numeroNota': nota.numeroNota,
                        'tipoNota': nota.tipoNota,
                        'tipoFactura': nota.tipoFactura,
                        'totalNota': float(nota.totalNota),
                        'estado': nota.estado
                    }
                })
            except Exception as e:
                import traceback
                print(f"Error inesperado al crear la nota o el asiento contable: {e}")
                print(traceback.format_exc())
                return JsonResponse({
                    'success': False,
                    'message': f'Ocurrió un error inesperado: {str(e)}. '
                               'Por favor, contacte al administrador del sistema si el problema persiste.'
                }, status=500)
        else:
            return JsonResponse({
                'success': False,
                'message': 'El formulario contiene errores. Por favor, corríjalos e inténtelo nuevamente.',
                'errors': form.errors
            }, status=400)
    else:
        form = NotaForm()
    return render(request, 'factura/nota.html', {
        'form': form,
        'personas': personas,
        'empresas': empresas,
        'monedas': tasas,
        'cuentas_plan': cuentas_plan,
        'numero_nota': numero_nota
    })
@transaction.atomic
def factura_edit(request, pk):
    """
    Vista para editar una factura existente.
    """
    factura = get_object_or_404(Factura, pk=pk)
    personas = Personas.objects.all()
    empresas = empresa.objects.all()
    monedas = Moneda.objects.all()

    if request.method == 'POST':
        form = FacturaForm(request.POST, instance=factura)
        if form.is_valid():
            form.save()
            return redirect('factura_list')
    else:
        form = FacturaForm(instance=factura)
    return render(request, 'factura/factura.html', {
        'form': form,
        'personas': personas,
        'empresas': empresas,
        'monedas': monedas
    })

@transaction.atomic
def factura_delete(request, pk):
    """
    Vista para realizar una eliminación lógica de una factura.
    """
    factura = get_object_or_404(Factura, pk=pk)
    factura.estadoFactura = 'ELIMINADA'  # Cambia el estado a "ELIMINADA"
    factura.save()
    return JsonResponse({'success': True, 'message': 'Factura marcada como eliminada.'})
# Detalles de Factura
def factura_detalle_list(request, factura_id):
    """
    Vista para listar los detalles de una factura específica.
    """
    factura = get_object_or_404(Factura, pk=factura_id)
    detalles = FacturaDetalle.objects.filter(idFactura=factura)
    return render(request, 'factura/detalleFactura.html', {
        'factura': factura,
        'detalles': detalles
    })


@transaction.atomic
def factura_create_notas(request, nota_id):
    """
    Vista para crear una factura a partir de una o múltiples notas.
    """
    # Convertir nota_id en una lista si es un único ID
    if isinstance(nota_id, int):
        nota_ids = [nota_id]
    elif isinstance(nota_id, list):
        nota_ids = nota_id
    else:
        return JsonResponse({'success': False, 'message': 'El parámetro nota_id debe ser un entero o una lista.'}, status=400)

    # Filtrar las notas pagadas
    notas = Nota.objects.filter(idNota__in=nota_ids, estado='PAGADO')
    if not notas.exists():
        return JsonResponse({'success': False, 'message': 'No hay notas pagadas para generar la factura.'}, status=400)

    # Crear la factura
    factura = Factura.objects.create(
        numeroFactura=generar_numero_factura(),
        tipoFactura=notas.first().tipoFactura,  # Asume que todas las notas tienen el mismo tipo
        idPersona=notas.first().idPersona,
        idEmpresa=notas.first().idEmpresa,
        subtotalExento=sum(nota.subtotalExento for nota in notas),
        subtotalGravado=sum(nota.subtotalGravado for nota in notas),
        iva=sum(nota.iva for nota in notas),
        ivaRetenido=sum(nota.ivaRetenido for nota in notas),
        islrRetenido=sum(nota.islrRetenido for nota in notas),
        descuento=sum(nota.descuento for nota in notas),
        totalVenta=sum(nota.totalNota for nota in notas),
        observaciones="Factura generada a partir de notas pagadas."
    )

    # Asociar las notas a la factura
    factura.notas.set(notas)

    # Crear los detalles de la factura para cada nota
    for nota in notas:
        FacturaDetalle.objects.create(
            idFactura=factura,
            tipoItem=f"Nota de Cobro - {nota.get_tipoFactura_display()}" if nota.tipoNota == "COBRO" else f"Nota de Pago - {nota.get_tipoFactura_display()}",
            descripcion=f"Detalle generado a partir de la nota {nota.numeroNota}",
            cantidad=1,  # Cada nota cuenta como una unidad
            precioUnitario=nota.totalNota,
            exento=nota.subtotalExento > 0,
            descuentoItem=nota.descuento,
            subtotal=nota.totalNota,
            ivaItem=nota.iva,
            totalItem=nota.totalNota
        )

    return JsonResponse({
        'success': True,
        'message': 'Factura generada exitosamente.',
        'factura_id': factura.idFactura
    })
@transaction.atomic
def factura_detalle_create(request, factura_id):
    """
    Vista para crear un nuevo detalle para una factura específica.
    """
    factura = get_object_or_404(Factura, pk=factura_id)

    if request.method == 'POST':
        form = FacturaDetalleForm(request.POST)
        if form.is_valid():
            detalle = form.save(commit=False)
            detalle.idFactura = factura
            detalle.save()
            return redirect('factura_detalle_list', factura_id=factura_id)
    else:
        form = FacturaDetalleForm()
    return render(request, 'factura/detalleFactura.html', {
        'form': form,
        'factura': factura
    })

@transaction.atomic
def factura_detalle_edit(request, pk):
    """
    Vista para editar un detalle de factura existente.
    """
    detalle = get_object_or_404(FacturaDetalle, pk=pk)
    factura = detalle.idFactura

    if request.method == 'POST':
        form = FacturaDetalleForm(request.POST, instance=detalle)
        if form.is_valid():
            form.save()
            return redirect('factura_detalle_list', factura_id=factura.idFactura)
    else:
        form = FacturaDetalleForm(instance=detalle)
    return render(request, 'factura/detalleFactura.html', {
        'form': form,
        'factura': factura
    })

@transaction.atomic
def factura_detalle_delete(request, pk):
    """
    Vista para eliminar un detalle de factura existente.
    """
    detalle = get_object_or_404(FacturaDetalle, pk=pk)
    factura_id = detalle.idFactura_id
    detalle.delete()
    return redirect('factura_detalle_list', factura_id=factura_id)

# Pagos
def pago_list(request):
    """
    Vista para listar todos los pagos.
    """
    pagos = Pago.objects.all()
    return render(request, 'factura/tablaPago.html', {'pagos': pagos})

def pago_detail(request, pk):
    """
    Vista para mostrar los detalles de un pago específico.
    """
    pago = get_object_or_404(Pago, pk=pk)
    return render(request, 'factura/pago_detail.html', {'pago': pago})

@transaction.atomic
def pago_create(request):
    """
    Vista para crear un nuevo pago y generar un asiento contable asociado.
    """
    notas = Nota.objects.exclude(estado='PAGADO').order_by('numeroNota')  # Excluir Notas pagadas
    cuentas_banco = CuentaBanco.objects.filter(estado=True).order_by('idCuentaBanco')  # Filtrar cuentas bancarias activas
    tasas = Tasa.objects.select_related('idMoneda') \
            .values('idMoneda__idMoneda', 'idMoneda__nombreMoneda') \
            .annotate(ultima_idTasa=Max('idTasa'), ultima_tasa=Max('montoTasa'))
    cuentas_plan = PlanCuenta.objects.filter(estadoPlanCuenta=True).order_by('codigoPlanCuenta')

    # Obtener la moneda de configuración
    configuracion = Configuracion.objects.first()
    if not configuracion:
        return JsonResponse({
            'success': False,
            'message': 'No se encontró una configuración activa en el sistema.'
        }, status=400)
    moneda_configuracion = configuracion.moneda
    tasa_configuracion = Tasa.objects.filter(idMoneda=moneda_configuracion).order_by('-idTasa').first()

    if not tasa_configuracion:
        return JsonResponse({
            'success': False,
            'message': f'No se encontró una tasa registrada para la moneda de configuración ({moneda_configuracion.nombreMoneda}).'
        }, status=400)

    tasa_configuracion_valor = Decimal(tasa_configuracion.montoTasa)  # Convertir a Decimal
    print(f"Tasa de configuración ({moneda_configuracion.nombreMoneda}): {tasa_configuracion_valor}")

    # Calcular el saldo pendiente de cada nota
    notas_data = []
    for nota in notas:
        pagos_relacionados = Pago.objects.filter(idNota=nota)
        total_pagado = sum(
            Decimal(pago.monto) * Decimal(pago.idTasa.montoTasa) / tasa_configuracion_valor
            if pago.idTasa.idMoneda != moneda_configuracion else Decimal(pago.monto)
            for pago in pagos_relacionados
        )
        saldo_pendiente = Decimal(nota.totalNota) - total_pagado
        print(f"Nota {nota.numeroNota}: Total Nota: {nota.totalNota}, Total Pagado: {total_pagado}, Saldo Pendiente: {saldo_pendiente}")
        notas_data.append({
            'idNota': nota.idNota,
            'numeroNota': nota.numeroNota,
            'totalNota': nota.totalNota,
            'saldoPendiente': saldo_pendiente,  # Ya está en la moneda de configuración
            'idPersona': nota.idPersona.cedula if nota.idPersona else "N/A",  # Incluye la cédula del cliente
            'idEmpresa': nota.idEmpresa.nombreEmpresa if nota.idEmpresa else "N/A",  # Incluye la nombre de la empresa

            'estado': nota.estado
        })

    if request.method == 'POST':
        form = PagoForm(request.POST)
        if form.is_valid():
            try:
                # Iniciar una transacción atómica
                with transaction.atomic():
                    pago = form.save(commit=False)

                    # Verificar si hay un periodo contable activo
                    periodo_activo = periodoContable.objects.filter(estadoPeriodo=True).first()
                    if not periodo_activo:
                        periodo_activo = periodoContable.objects.order_by('-idPeriodo').first()
                    if not periodo_activo:
                        return JsonResponse({
                            'success': False,
                            'message': 'No hay ningún periodo contable registrado o activo en el sistema. '
                                       'Por favor, registre o active un periodo contable antes de continuar.'
                        }, status=400)

                    # Verificar los pagos relacionados a la nota
                    pagos_relacionados = Pago.objects.filter(idNota=pago.idNota)
                    total_pagado = sum(
                        Decimal(pago_relacionado.monto) * Decimal(pago_relacionado.idTasa.montoTasa) / tasa_configuracion_valor
                        if pago_relacionado.idTasa.idMoneda != moneda_configuracion else Decimal(pago_relacionado.monto)
                        for pago_relacionado in pagos_relacionados
                    )
                    saldo_nota= Decimal(pago.idNota.totalNota) - total_pagado
                    print(f"Saldo Nota {pago.idNota.numeroNota}: {saldo_nota}")

                    # Convertir el monto del pago a la moneda de configuración
                    tasa_pago = Tasa.objects.filter(idMoneda=pago.idTasa.idMoneda).order_by('-idTasa').first()
                    if not tasa_pago:
                        return JsonResponse({
                            'success': False,
                            'message': f'No se encontró una tasa registrada para la moneda del pago ({pago.idTasa.idMoneda.nombreMoneda}).'
                        }, status=400)

                    monto_pago_convertido = Decimal(pago.monto) * Decimal(tasa_pago.montoTasa) / tasa_configuracion_valor \
                        if pago.idTasa.idMoneda != moneda_configuracion else Decimal(pago.monto)
                    print(f"Monto Pago Convertido: {monto_pago_convertido}")

                    if saldo_nota == 0:
                        return JsonResponse({
                            'success': False,
                            'message': 'El pago no se registró porque la nota ya está solvente.'
                        }, status=400)

                    if monto_pago_convertido > saldo_nota:
                        return JsonResponse({
                            'success': False,
                            'message': f'El monto del pago excede el saldo pendiente de la nota. '
                                       f'Saldo pendiente: {saldo_nota :.2f}.'
                        }, status=400)

                    # Obtener la cuenta del Plan de Cuenta usada en el Debe del asiento principal de la nota
                    try:
                        asiento_principal = pago.idNota.idAsiento  # Obtener el asiento principal de la nota
                        detalle_debe = DetalleAsiento.objects.filter(idAsiento=asiento_principal, debe__gt=0).first()
                        if not detalle_debe:
                            return JsonResponse({
                                'success': False,
                                'message': 'No se encontró una cuenta asociada al Debe en el asiento principal de la nota.'
                            }, status=400)
                        plan_cuenta_haber = detalle_debe.idPlanCuenta  # Usar esta cuenta como el Haber para el pago
                    except Exception as e:
                        raise ValueError(f'Error al obtener la cuenta del Debe del asiento principal: {str(e)}')

                    # Crear el asiento contable para el pago
                    try:
                        # Verificar si ya existe un asiento para pagos relacionados a la nota
                        pagos_existentes = Pago.objects.filter(idNota=pago.idNota).count()
                        numero_asiento_pago = f"PAGO-{pago.idNota.numeroNota}"
                        if pagos_existentes > 0:
                            numero_asiento_pago += f"-{pagos_existentes + 1}"  # Agregar un sufijo para identificar el pago adicional

                        asiento_pago = AsientoContable.objects.create(
                            numeroAsiento=numero_asiento_pago,
                            fechaAsiento=pago.fechaPago,
                            conceptoAsiento=f"Asiento para el pago de la nota {pago.idNota.numeroNota}",
                            idPeriodo=periodo_activo
                        )
                    except Exception as e:
                        raise ValueError(f'Error al crear el asiento contable: {str(e)}')

                    # Crear los detalles del asiento contable
                    try:
                        DetalleAsiento.objects.create(
                            idAsiento=asiento_pago,
                            idPlanCuenta_id=request.POST['idPlanCuentaDebe'],  # Cuenta de ingresos seleccionada por el usuario
                            debe=pago.monto,
                            haber=0.00
                        )
                        DetalleAsiento.objects.create(
                            idAsiento=asiento_pago,
                            idPlanCuenta=plan_cuenta_haber,  # Cuenta asociada al Debe del asiento principal
                            debe=0.00,
                            haber=pago.monto
                        )
                    except Exception as e:
                        raise ValueError(f'Error al crear los detalles del asiento contable: {str(e)}')

                    # Asociar el asiento contable al pago
                    pago.idAsiento = asiento_pago
                    pago.save()

                    # Caso 1: El pago fue exitoso, pero aún hay deuda
                    if saldo_nota - monto_pago_convertido > 0:
                        return JsonResponse({
                            'success': True,
                            'message': 'El pago fue exitoso, aun posee deuda ¿Desea realizar otro pago adicional?',
                            'redirect_url': f"{reverse('pago_create')}?nota={pago.idNota.idNota}",
                            'pago': {
                                'idPago': pago.idPago,
                                'idNota': pago.idNota.numeroNota,
                                'monto': f"{float(pago.monto):.2f} {pago.idTasa.idMoneda.simboloMoneda}",
                                'fechaPago': pago.fechaPago.strftime('%d/%m/%Y'),
                                'formaPago': pago.formaPago,
                                'referencia': pago.referencia
                            }
                        })

                    # Caso 2: El pago fue exitoso, la deuda fue saldada y se cerró la nota
                    if saldo_nota - monto_pago_convertido == 0:
                        pago.idNota.estado = 'PAGADO'
                        pago.idNota.save()
                        return JsonResponse({
                            'success': True,
                            'message': 'Pago creado exitosamente y asiento contable generado. La nota ha sido pagada en su totalidad. Ya puede facturar.',
                            'redirect_url': reverse('factura_create', args=[pago.idNota.idNota]),
                            'pago': {
                                'idPago': pago.idPago,
                                'idNota': pago.idNota.numeroNota,
                               'monto': f"{float(pago.monto):.2f} {pago.idTasa.idMoneda.simboloMoneda}",
                                'fechaPago': pago.fechaPago.strftime('%d/%m/%Y'),
                                'formaPago': pago.formaPago,
                                'referencia': pago.referencia
                            }
                        })
            except ValueError as e:
                print(f"Error de valor: {e}")
                return JsonResponse({
                    'success': False,
                    'message': str(e)
                }, status=500)
            except Exception as e:
                import traceback
                print(f"Error inesperado: {e}")
                print(traceback.format_exc())
                return JsonResponse({
                    'success': False,
                    'message': f'Ocurrió un error inesperado: {str(e)}. '
                               'Por favor, contacte al administrador del sistema si el problema persiste.'
                }, status=500)
        else:
            print(f"Errores en el formulario: {form.errors}")
            return JsonResponse({
                'success': False,
                'message': 'El formulario contiene errores. Por favor, corríjalos e inténtelo nuevamente.',
                'errors': form.errors
            }, status=400)
    else:
        form = PagoForm()
    return render(request, 'factura/pago.html', {
        'form': form,
        'notas': notas_data,  # Pasar las notas con saldo pendiente al contexto
        'cuentas_banco': cuentas_banco,  # Pasar las cuentas bancarias al contexto
        'cuentas_plan': cuentas_plan,
        'monedas': tasas,
        'tasa_configuracion_valor': tasa_configuracion_valor  # Tasa de configuración

    })

@transaction.atomic
def pago_edit(request, pk):
    """
    Vista para editar un pago existente.
    """
    pago = get_object_or_404(Pago, pk=pk)
    facturas = Factura.objects.all()

    if request.method == 'POST':
        form = PagoForm(request.POST, instance=pago)
        if form.is_valid():
            form.save()
            return redirect('pago_list')
    else:
        form = PagoForm(instance=pago)
    return render(request, 'factura/pago.html', {
        'form': form,
        'facturas': facturas
    })

@transaction.atomic
def pago_delete(request, pk):
    """
    Vista para eliminar un pago existente.
    """
    pago = get_object_or_404(Pago, pk=pk)
    pago.delete()
    return redirect('pago_list')


# Parametros Tributarios

def parametro_tributario_list(request):
    """
    Vista para listar todos los parámetros tributarios.
    """
    parametros = ParametroTributario.objects.all()
    return render(request, 'factura/tablaParametrosTributarios.html', {'parametros': parametros})

def parametro_tributario_detail(request, pk):
    """
    Vista para mostrar los detalles de un parámetro tributario específico.
    """
    parametro = get_object_or_404(ParametroTributario, pk=pk)
    return render(request, 'factura/parametrosDetails.html', {'parametro': parametro})


@transaction.atomic
def parametro_tributario_create(request):
    """
    Vista para crear un nuevo parámetro tributario.
    """
    if request.method == 'POST':
        form = ParametroTributarioForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('parametro_tributario_list')
    else:
        form = ParametroTributarioForm()

    # Pasar las opciones al contexto
    context = {
        'form': form,
        'TIPO_PARAMETRO': ParametroTributario.TIPO_PARAMETRO,
        'TIPOS_APLICABLES': ParametroTributario.TIPOS_APLICABLES,
    }
    return render(request, 'factura/parametroTributario.html', context)

@transaction.atomic
def parametro_tributario_edit(request, pk):
    """
    Vista para editar un parámetro tributario existente.
    """
    parametro = get_object_or_404(ParametroTributario, pk=pk)
    # Obtener las opciones de tipos y aplicables del modelo para el formulario
    tipo_parametro = ParametroTributario.TIPO_PARAMETRO
    tipos_aplicables = ParametroTributario.TIPOS_APLICABLES

    if request.method == 'POST':
        form = ParametroTributarioForm(request.POST, instance=parametro)
        if form.is_valid():
            form.save()
            return redirect('parametro_tributario_list')
    else:
        form = ParametroTributarioForm(instance=parametro)
    return render(request, 'factura/editParametroTributario.html', {
        'form': form,
        'TIPO_PARAMETRO': tipo_parametro,
        'TIPOS_APLICABLES': tipos_aplicables,
        'parametro': parametro
    })
@require_POST
@transaction.atomic
def parametro_tributario_eliminar(request, pk):
    parametro = get_object_or_404(ParametroTributario, pk=pk)
    # Actualizamos el estado sin modificar el nombre u otros campos únicos
    parametro.activo = False  # Desactivamos el parámetro tributario
    # Intentamos guardar el objeto, lo que disparará la validación única
    try:
        parametro.save()  # Aquí se ejecuta la validación en save()
        return JsonResponse({'success': True, 'message': 'Parámetro tributario desactivado correctamente. ⛔'})
    except ValidationError as e:
        # Regresamos el mensaje de error; esto ocurriría si se dispara la validación única
        return JsonResponse({'success': False, 'message': e.messages})
    
@require_POST
@transaction.atomic
def parametro_tributario_reactivar(request, pk):
    parametro = get_object_or_404(ParametroTributario, pk=pk)
    parametro.activo = True
    try:
        parametro.save()
        return JsonResponse({'success': True, 'message': 'Parámetro tributario reactivado correctamente. ✅'})
    except ValidationError as e:
        return JsonResponse({'success': False, 'message': e.messages})    

def obtener_parametros_tributarios(request):
    # Agrupar parámetros por tipo para facilitar el acceso en el frontend
    parametros = ParametroTributario.objects.all()
    parametros_agrupados = {}
    
    for param in parametros:
        if param.tipo not in parametros_agrupados:
            parametros_agrupados[param.tipo] = []
        
        parametros_agrupados[param.tipo].append({
            'aplica_a': param.aplica_a,
            'porcentaje': float(param.porcentaje) if param.porcentaje is not None else 0,
            'valor_fijo': float(param.valor_fijo) if param.valor_fijo is not None else 0,
            'descripcion': param.descripcion
        })
    
    return JsonResponse(parametros_agrupados)

def reporte_facturas_pdf(request):
    # Selección de cantidad de registros
    start = int(request.GET.get('start', 1))
    end = int(request.GET.get('end', 0))
    facturas = list(Factura.objects.all().order_by('fechaEmision', 'numeroFactura'))
    if end == 0 or end > len(facturas):
        end = len(facturas)
    facturas = facturas[start-1:end]

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="reporte_notasdecobro.pdf"'

    # Para aumentar el tamaño de la hoja, define un tamaño personalizado (por ejemplo, más grande que letter)
    custom_width = 14 * inch  # ancho personalizado (por ejemplo, 14 pulgadas)
    custom_height = 9 * inch  # alto personalizado (por ejemplo, 9 pulgadas)
    page_size = (custom_width, custom_height)

    # Aquí se pone la hoja en horizontal usando landscape y el tamaño personalizado
    p = canvas.Canvas(response, pagesize=landscape(page_size))
    width, height = landscape(page_size)
    logo_width, logo_height, logo_margin = 100, 100, 15

    # Configuración institucional
    config = None
    try:
        config = Configuracion.objects.order_by('-fechaConfiguracion').first()
    except Exception:
        pass
    logo_path = config.logo.path if config and config.logo else None
    firma_path = config.firma.path if config and config.firma else None
    nombre_institucion = config.nombreInstitucion if config else "Institución"
    rif_institucion = config.rif if config else ""

    safe_left = logo_margin
    safe_right = width - logo_margin
    safe_width = safe_right - safe_left

    # --- Define encabezado y pie ---
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
        p.drawString(logo_margin, text_top, nombre_institucion)
        p.drawString(logo_margin, text_top - 20, f"RIF: {rif_institucion}")
        p.drawString(logo_margin, text_top - 40, "AV. ALBERTO RAVELL CON AV. INTERCOMUNAL JOSE ANTONIO PAEZ,")
        p.drawString(logo_margin, text_top - 60, "LOCAL UPTYAB, INDEPENDENCIA – EDO YARACUY")
        p.setFont("Helvetica-Bold", 13)
        p.drawCentredString(width / 2, text_top - 100, "Reporte de notas de Cobro")

    def draw_footer():
        if firma_path and os.path.exists(firma_path):
            p.drawImage(firma_path, width/2 - 60, 60, width=120, height=60, preserveAspectRatio=True, mask='auto')
            p.setFont("Helvetica-Oblique", 10)
            p.drawCentredString(width/2, 40, "Firma autorizada")

    # --- Datos de la tabla ---
    data = [
        [
            "ID",
            "N° Factura",
            "Fecha Emisión",
            "Cliente",
            "Tipo",
            "Subtotal Exento",
            "Subtotal Gravado",
            "IVA",
            "Total Venta",
            "Estado"
        ]
    ]
    for fac in facturas:
        data.append([
            str(getattr(fac, 'idFactura', '')),
            getattr(fac, 'numeroFactura', ''),
            fac.fechaEmision.strftime("%d/%m/%Y") if hasattr(fac, 'fechaEmision') and fac.fechaEmision else '',
            str(fac.idPersona) if fac.idPersona else '',
            dict(Factura.TIPOS_FACTURA).get(fac.tipoFactura, fac.tipoFactura),
            f"{fac.subtotalExento:.2f}",
            f"{fac.subtotalGravado:.2f}",
            f"{fac.iva:.2f}",
            f"{fac.totalVenta:.2f}",
            fac.estado,
        ])
    col_widths = [40, 120, 90, 120, 180, 100, 100, 60, 80, 60]
    table_width = sum(col_widths)

    # --- Cálculo de espacio ---
    header_height = 140
    footer_height = 160
    row_height = 22
    available_height = height - header_height - footer_height

    max_rows_per_page = int(available_height // row_height)
    if max_rows_per_page < 1:
        max_rows_per_page = 1

    total_rows = len(data) - 1
    page = 0

    for start_row in range(0, total_rows, max_rows_per_page):
        end_row = start_row + max_rows_per_page
        page_data = [data[0]] + data[start_row + 1:end_row + 1]
        if page > 0:
            p.showPage()
        draw_header()
        y = height - header_height
        # Centrar la tabla horizontalmente
        table_x = safe_left + (safe_width - table_width) / 2
        table = Table(page_data, colWidths=col_widths)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#fe8330")),
            ('TEXTCOLOR', (0,0), (-1,0), colors.white),
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('FONTSIZE', (0,0), (-1,0), 12),
            ('BOTTOMPADDING', (0,0), (-1,0), 10),
            ('BACKGROUND', (0,1), (-1,-1), colors.whitesmoke),
            ('GRID', (0,0), (-1,-1), 1, colors.black),
        ]))
        table.wrapOn(p, width, height)
        table.drawOn(p, table_x, y - row_height * len(page_data))
        draw_footer()
        page += 1

    p.save()
    return response


def reporte_factura_pdf(request, pk):
    factura = get_object_or_404(Factura, pk=pk)
    detalles = FacturaDetalle.objects.filter(idFactura=factura)

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="factura_{factura.numeroFactura}.pdf"'

    p = canvas.Canvas(response, pagesize=letter)
    width, height = letter

    # Encabezado
    p.setFont("Helvetica-Bold", 14)
    p.drawCentredString(width / 2, height - 50, "Nota de cobro")
    p.setFont("Helvetica", 10)
    p.drawString(50, height - 80, f"N°: {factura.numeroFactura}")
    p.drawString(50, height - 100, f"Fecha: {factura.fechaEmision.strftime('%d/%m/%Y')}")
    p.drawString(50, height - 120, f"Cliente: {factura.idPersona if factura.idPersona else ''}")
    p.drawString(50, height - 140, f"Empresa: {factura.idEmpresa if factura.idEmpresa else ''}")

    # Tabla de detalles
    data = [["Descripción", "Cantidad", "Precio Unitario", "Subtotal"]]
    for det in detalles:
        data.append([
            det.descripcion,
            str(det.cantidad),
            f"{det.precioUnitario:.2f}",
            f"{det.subtotal:.2f}"
        ])
    table = Table(data, colWidths=[200, 80, 100, 100])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#fe8330")),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,0), 11),
        ('BOTTOMPADDING', (0,0), (-1,0), 10),
        ('BACKGROUND', (0,1), (-1,-1), colors.whitesmoke),
        ('GRID', (0,0), (-1,-1), 1, colors.black),
    ]))
    table.wrapOn(p, width, height)
    table.drawOn(p, 50, height - 200 - 22 * len(data))

    # Totales
    p.setFont("Helvetica-Bold", 11)
    p.drawString(350, 100, f"Total Venta: {factura.totalVenta:.2f}")
    p.drawString(350, 80, f"Estado: {factura.estado}")

    p.showPage()
    p.save()
    return response