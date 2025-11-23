import json
import os
from pyexpat.errors import messages
import re
import traceback
import uuid
import random
from decimal import Decimal, ROUND_HALF_UP, InvalidOperation
from datetime import datetime

from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, HttpResponse
from django.db import transaction
from django.db.models import Max
from django.urls import reverse
from django.utils.timezone import now
from django.core.exceptions import ValidationError
from django.views.decorators.http import require_POST

from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import landscape, letter
from reportlab.platypus import Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.units import inch

from apps.cuentaBanco.models import CuentaBanco
from apps.honorario.models import Honorario
from apps.inscripcion.models import Inscripcion, InscripcionCuota
from apps.periodoContable.models import periodoContable
from apps.solicitud.models import Solicitud
from apps.home.models import Configuracion, CuotaFormacion, Moneda, Tasa
from apps.persona.models import Personas
from apps.empresa.models import empresa
from apps.planCuenta.models import PlanCuenta
from apps.asientoContable.models import AsientoContable, DetalleAsiento
from .templatetags.decimal_filters import to_decimal
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models import Q

from .models import (
    TIPOS_ARTICULO, Factura, FacturaDetalle, NotaRelacionada, Pago, PagoIGTF, ParametroTributario, Nota, PlanArticulo, PagoTemporal
)
from .forms import (
    FacturaForm, FacturaDetalleForm, PagoForm, ParametroTributarioForm, NotaForm, PlanArticuloForm, 
)
from .templatetags.decimal_filters import to_decimal

"""
Clase para serializar objetos Decimal a JSON.
"""
class DecimalEncoder(json.JSONEncoder):
    """
    Serializa objetos Decimal a string para evitar errores de JSON y preservar la precisión.
    """
    def default(self, obj):
        if isinstance(obj, Decimal):
            return str(obj)
        return json.JSONEncoder.default(self, obj)

def create_plan_articulo(request):
    """
    Vista para crear dos registros de PlanArticulo: uno para Debe (tipo=1) y otro para Haber (tipo=0).
    """
    cuentas_plan = PlanCuenta.objects.filter(estadoPlanCuenta=True).order_by('codigoPlanCuenta')
    if request.method == 'POST':
        form = PlanArticuloForm(request.POST)
        if form.is_valid():
            try:
                plan_articulo_data = form.save(commit=False)
                
                # Obtener los valores de idPlanCuentaDebe y idPlanCuentaHaber desde request.POST
                id_plan_cuenta_debe = request.POST.get('idPlanCuentaDebe')
                id_plan_cuenta_haber = request.POST.get('idPlanCuentaHaber')

                if not id_plan_cuenta_debe or not id_plan_cuenta_haber:
                    return JsonResponse({
                        'success': False,
                        'message': "Debe seleccionar las cuentas contables para el Debe y el Haber."
                    }, status=400)

                # Crear registro para tipo=1 (Debe)
                plan_articulo_debe = PlanArticulo(
                    tipoArticulo=plan_articulo_data.tipoArticulo,
                    idPlanCuenta_id=id_plan_cuenta_debe,  # Usar el ID directamente
                    tipo=1  # Debe
                )
                plan_articulo_debe.save()

                # Crear registro para tipo=0 (Haber)
                plan_articulo_haber = PlanArticulo(
                    tipoArticulo=plan_articulo_data.tipoArticulo,
                    idPlanCuenta_id=id_plan_cuenta_haber,  # Usar el ID directamente
                    tipo=0  # Haber
                )
                plan_articulo_haber.save()

                return JsonResponse({
                    'success': True,
                    'message': "Planes de Artículo creados exitosamente.",
                    'url': reverse('plan_articulo_list')
                })
            except Exception as e:
                return JsonResponse({
                    'success': False,
                    'message': f"Error al crear los Planes de Artículo: {str(e)}"
                }, status=500)
        else:
            return JsonResponse({
                'success': False,
                'message': "Error en el formulario. Por favor, revise los datos ingresados.",
                'errors': form.errors
            }, status=400)
    else:
        form = PlanArticuloForm()
    return render(request, 'factura/planArticulo.html', {'form': form, 'cuentas_plan': cuentas_plan})

def edit_plan_articulo(request, pk):
    """
    Vista para editar un PlanArticulo existente.
    """
    plan_articulo = get_object_or_404(PlanArticulo, pk=pk)
    cuentas_plan = PlanCuenta.objects.filter(estadoPlanCuenta=True).order_by('codigoPlanCuenta')
    
    # Determinar si es debe o haber
    es_debe = plan_articulo.tipo
    tipo_texto = "Debe" if es_debe else "Haber"
    
    # Obtener cuenta actual para mostrar
    cuenta_actual = plan_articulo.idPlanCuenta
    nombre_cuenta_actual = f"{cuenta_actual.codigoPlanCuenta} - {cuenta_actual.nombrePlanCuenta}" if cuenta_actual else ""

    if request.method == 'POST':
        form = PlanArticuloForm(request.POST, instance=plan_articulo)
        if form.is_valid():
            try:
                # Solo actualizamos la cuenta contable
                plan_articulo.idPlanCuenta_id = request.POST.get('idPlanCuenta')
                plan_articulo.save()
                
                return JsonResponse({
                    'success': True,
                    'message': "Plan de Artículo actualizado exitosamente.",
                    'url': reverse('plan_articulo_list')
                })
            except Exception as e:
                return JsonResponse({
                    'success': False,
                    'message': f"Error al actualizar el Plan de Artículo: {str(e)}"
                }, status=500)
        else:
            return JsonResponse({
                'success': False,
                'message': "Error en el formulario. Por favor, revise los datos ingresados.",
                'errors': form.errors
            }, status=400)
    else:
        form = PlanArticuloForm(instance=plan_articulo)
    
    return render(request, 'factura/planArticuloEdit.html', {
        'form': form,
        'plan_articulo': plan_articulo,
        'cuentas_plan': cuentas_plan,
        'es_debe': es_debe,
        'tipo_texto': tipo_texto,
        'nombre_cuenta_actual': nombre_cuenta_actual,
        'id_plan_cuenta_actual': cuenta_actual.idPlanCuenta if cuenta_actual else None
    })

def plan_articulo_list(request):
    """
    Vista para listar todos los PlanArticulo.
    """
    plan_articulos = PlanArticulo.objects.all().order_by('idPlanArti')
    return render(request, 'factura/tablaPlanArticulo.html', {'planes': plan_articulos})



def factura_cargando(request, pk):
    """
    Vista que muestra una página de carga antes de generar el PDF de factura.
    """
    factura = get_object_or_404(Factura, pk=pk)
    context = {
        'factura': factura,
        'factura_pk': factura.id,  # Asegurarnos de pasar el ID correcto
        'pdf_url': reverse('factura_generar_pdf', args=[factura.id])
    }
    return render(request, 'factura/cargando.html', context)
def factura_list(request):
    """
    Vista para listar todas las facturas junto con sus detalles.
    """
    facturas = Factura.objects.prefetch_related('detalles').all()
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
# Notas
def nota_list(request):
    """
    Vista para listar todas las notas.
    """
    notas = Nota.objects.all().order_by('-idNota')
    return render(request, 'factura/tablaNotas.html', {'notas': notas})

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
def nota_create(request):
    personas = Personas.objects.all().order_by('-idPersona')
    empresas = empresa.objects.all().order_by('-idEmpresa')
    tasas = Tasa.objects.select_related('idMoneda') \
        .values('idMoneda__idMoneda', 'idMoneda__nombreMoneda') \
        .annotate(ultima_idTasa=Max('idTasa'), ultima_tasa=Max('montoTasa'))
    cuentas_plan = PlanCuenta.objects.filter(estadoPlanCuenta=True).order_by('codigoPlanCuenta')
    numero_nota = generar_numero_nota()  # Generar el número de nota
    empresas = empresa.objects.all()
    cuotas = InscripcionCuota.objects.filter(
        estadoPago='EN ESPERA'
    ).exclude(
        idCuota__in=NotaRelacionada.objects.values_list('idCuota', flat=True)
    ).order_by('idCuota')
    solicitudes = Solicitud.objects.filter(estadoSolicitud='ACTIVO').order_by('idSoli')
    honorarios = Honorario.objects.filter(estadoHonorario='ACTIVO').order_by('idHonorario')
    inscripciones = Inscripcion.objects.filter(is_active=True).order_by('idInscripcion')
    descuento= Configuracion.objects.first().descuento if Configuracion.objects.exists() else 0

    # Si necesitas el objeto Moneda a partir del id:
    # moneda_seleccionada = Moneda.objects.filter(pk=idMoneda).first() if idMoneda else None
    # Obtener la moneda de configuración
    configuracion = Configuracion.objects.first()
    if not configuracion:
        return JsonResponse({
            'success': False,
            'message': 'No se encontró una configuración activa en el sistema.'
        }, status=400)
    moneda_configuracion = configuracion.moneda
    tasa_configuracion = Tasa.objects.filter(idMoneda=moneda_configuracion).order_by('-idTasa').first()
    operacion = request.POST.get('tipoOperacion', '') 

    if not tasa_configuracion:
        return JsonResponse({
            'success': False,
            'message': f'No se encontró una tasa registrada para la moneda de configuración ({moneda_configuracion.nombreMoneda}).'
        }, status=400)
    print(f"DESCUENTO de configuración: {descuento}%")
    # Convertir a Decimal de forma segura (acepta cadenas con comas/miles)
    try:
        raw_tasa = str(tasa_configuracion.montoTasa or '0').replace('.', '').replace(',', '.')
        tasa_configuracion_valor = to_decimal(raw_tasa)
    except (InvalidOperation, ValueError):
        return JsonResponse({
            'success': False,
            'message': f'Valor de tasa inválido: {tasa_configuracion.montoTasa}'
        }, status=400)

    tasa_configuracion_id= tasa_configuracion.idTasa
    tasa_configuracion_valor = to_decimal(tasa_configuracion.montoTasa)  # Convertir a Decimal
    print(f"Tasa de configuración ({moneda_configuracion.nombreMoneda}): {tasa_configuracion_valor}")
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

                # # Verificar que las cuentas contables estén presentes en la solicitud
                # if 'idPlanCuentaDebe' not in request.POST or 'idPlanCuentaHaber' not in request.POST:
                #     return JsonResponse({
                #         'success': False,
                #         'message': 'Debe seleccionar las cuentas contables para el debe y el haber. '
                #                    'Asegúrese de que los campos "idPlanCuentaDebe" y "idPlanCuentaHaber" estén presentes.'
                #     }, status=400)

                # Crear el asiento contable
                try:

                    asiento = AsientoContable.objects.create(
                        numeroAsiento=f"NOTA-{numero_nota}",
                        fechaAsiento=nota.fechaEmision,
                        conceptoAsiento=f"{numero_nota} - Artículo: {nota.tipoArticulo} - Operación: {operacion}",
                        idPeriodo=periodo_activo
                    )
                    print(f"Creado AsientoContable con concepto: {asiento.conceptoAsiento} ")
                except Exception as e:
                    return JsonResponse({
                        'success': False,
                        'message': f'Error al crear el asiento contable: {str(e)}. '
                                   'Por favor, revise los datos ingresados e inténtelo nuevamente.'
                    }, status=500)

                # Crear los detalles del asiento contable
                try:
                    # Consultar los registros más recientes de PlanArticulo para el tipo de artículo seleccionado
                    plan_articulos = PlanArticulo.objects.filter(tipoArticulo=nota.tipoArticulo).order_by('-fecha')

                    # Filtrar para obtener un registro para el debe (tipo=1) y otro para el haber (tipo=0)
                    plan_articulo_debe = plan_articulos.filter(tipo=1).first()
                    plan_articulo_haber = plan_articulos.filter(tipo=0).first()

                    # Validar que se hayan encontrado ambos registros
                    if not plan_articulo_debe or not plan_articulo_haber:
                        return JsonResponse({
                            'success': False,
                            'message': 'No se encontraron cuentas contables válidas para el tipo de artículo seleccionado. '
                                    'Por favor, revise la configuración de los planes de artículo.'
                        }, status=400)

                    # Crear los detalles del asiento contable usando los registros encontrados
                    DetalleAsiento.objects.create(
                        idAsiento=asiento,
                        idMoneda=moneda_configuracion,
                        idPlanCuenta=plan_articulo_debe.idPlanCuenta,
                        debe=nota.totalNota,
                        haber=0.00
                    )
                    DetalleAsiento.objects.create(
                        idAsiento=asiento,
                        idMoneda=moneda_configuracion,
                        idPlanCuenta=plan_articulo_haber.idPlanCuenta,
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

                # Crear la relación en NotaRelacionada solo si alguno de los IDs está presente
                crear_relacion_nota(nota, request)

                id_inscripcion = request.POST.get('idInscripcion')
                print(f"ID Inscripcion recibido: {id_inscripcion}")

                if id_inscripcion:
                    inscripcion = Inscripcion.objects.filter(idInscripcion=id_inscripcion).first()
                    if inscripcion:
                        nota.idInscripcion = inscripcion
                        nota.save()
                        inscripcion.estadoPago = 'PENDIENTE'
                        inscripcion.save()
                    else:
                        print("No se encontró una inscripción con el ID proporcionado.")
                else:
                    print("ID Inscripcion no proporcionado en el formulario.")
                                
                # Si todo es exitoso, retornar una respuesta JSON
                return JsonResponse({
                    'success': True,
                    'message': 'Nota creada exitosamente.',
                    'lista': reverse('nota_list'),
                    'pagar': f"{reverse('pago_create')}?nota={nota.idNota}",
                    'nota': {
                        'idNota': nota.idNota,
                        'numeroNota': nota.numeroNota,
                        'tipoOperacion': nota.tipoOperacion,
                        'tipoArticulo': nota.tipoArticulo,
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
        'numero_nota': numero_nota,
        'cuotas': cuotas,
        'solicitudes': solicitudes,
        'honorarios': honorarios,
        'inscripciones': inscripciones,
        'tasa_configuracion_valor': tasa_configuracion_valor,
        'tasa_configuracion_id': tasa_configuracion_id,
        'moneda_configuracion': moneda_configuracion,
        'descuento': descuento
    })

@transaction.atomic
def nota_administrativa_create(request):
    personas = Personas.objects.all()
    empresas = empresa.objects.all()
    tasas = Tasa.objects.select_related('idMoneda') \
        .values('idMoneda__idMoneda', 'idMoneda__nombreMoneda') \
        .annotate(ultima_idTasa=Max('idTasa'), ultima_tasa=Max('montoTasa'))
    cuentas_plan = PlanCuenta.objects.filter(estadoPlanCuenta=True).order_by('codigoPlanCuenta')
    numero_nota = generar_numero_nota()  # Generar el número de nota
    empresas = empresa.objects.all()
    cuotas = InscripcionCuota.objects.filter(estadoPago='EN ESPERA').order_by('idCuota')
    solicitudes = Solicitud.objects.filter(estadoSolicitud='ACTIVO').order_by('idSoli')
    honorarios = Honorario.objects.filter(estadoHonorario='ACTIVO').order_by('idHonorario')
    inscripciones = Inscripcion.objects.filter(is_active=True).order_by('idInscripcion')
    
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

    # Convertir a Decimal de forma segura (acepta cadenas con comas/miles)
    try:
        raw_tasa = str(tasa_configuracion.montoTasa or '0').replace('.', '').replace(',', '.')
        tasa_configuracion_valor = to_decimal(raw_tasa)
    except (InvalidOperation, ValueError):
        return JsonResponse({
            'success': False,
            'message': f'Valor de tasa inválido: {tasa_configuracion.montoTasa}'
        }, status=400)

    tasa_configuracion_valor = to_decimal(tasa_configuracion.montoTasa)  # Convertir a Decimal
    print(f"Tasa de configuración ({moneda_configuracion.nombreMoneda}): {tasa_configuracion_valor}")

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

                # Crear el asiento contable
                try:
                    asiento = AsientoContable.objects.create(
                        numeroAsiento=f"NOTA-ADM-{numero_nota}",  # Diferenciar con prefijo ADM
                        fechaAsiento=nota.fechaEmision,
                        conceptoAsiento=f"Asiento ADM {numero_nota}",
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
                    # Consultar los registros más recientes de PlanArticulo para el tipo de artículo seleccionado
                    plan_articulos = PlanArticulo.objects.filter(tipoArticulo=nota.tipoArticulo).order_by('-fecha')

                    # Filtrar para obtener un registro para el debe (tipo=1) y otro para el haber (tipo=0)
                    plan_articulo_debe = plan_articulos.filter(tipo=1).first()
                    plan_articulo_haber = plan_articulos.filter(tipo=0).first()

                    # Validar que se hayan encontrado ambos registros
                    if not plan_articulo_debe or not plan_articulo_haber:
                        return JsonResponse({
                            'success': False,
                            'message': 'No se encontraron cuentas contables válidas para el tipo de artículo seleccionado. '
                                    'Por favor, revise la configuración de los planes de artículo.'
                        }, status=400)

                    # Crear los detalles del asiento contable usando los registros encontrados
                    DetalleAsiento.objects.create(
                        idAsiento=asiento,
                        idPlanCuenta=plan_articulo_debe.idPlanCuenta,
                        debe=nota.totalNota,
                        haber=0.00
                    )
                    DetalleAsiento.objects.create(
                        idAsiento=asiento,
                        idPlanCuenta=plan_articulo_haber.idPlanCuenta,
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
                nota.numeroNota = f"ADM-{numero_nota}"  # Prefijo para notas administrativas
                nota.save()

                # Crear la relación en NotaRelacionada solo si alguno de los IDs está presente
                crear_relacion_nota(nota, request)

                id_inscripcion = request.POST.get('idInscripcion')
                print(f"ID Inscripcion recibido: {id_inscripcion}")

                if id_inscripcion:
                    inscripcion = Inscripcion.objects.filter(idInscripcion=id_inscripcion).first()
                    if inscripcion:
                        nota.idInscripcion = inscripcion
                        nota.save()
                        inscripcion.estadoPago = 'PENDIENTE'
                        inscripcion.save()
                    else:
                        print("No se encontró una inscripción con el ID proporcionado.")
                else:
                    print("ID Inscripcion no proporcionado en el formulario.")
                                
                # Si todo es exitoso, retornar una respuesta JSON
                return JsonResponse({
                    'success': True,
                    'message': 'Nota administrativa creada exitosamente.',
                    'lista': reverse('nota_administrativa_list'),
                    'pagar': f"{reverse('pago_create')}?nota={nota.idNota}",
                    'nota': {
                        'idNota': nota.idNota,
                        'numeroNota': nota.numeroNota,
                        'tipoOperacion': nota.tipoOperacion,
                        'tipoArticulo': nota.tipoArticulo,
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
    return render(request, 'factura/nota_administrativa.html', {
        'form': form,
        'personas': personas,
        'empresas': empresas,
        'monedas': tasas,
        'cuentas_plan': cuentas_plan,
        'numero_nota': numero_nota,
        'cuotas': cuotas,
        'solicitudes': solicitudes,
        'honorarios': honorarios,
        'inscripciones': inscripciones
    })

def nota_administrativa_list(request):
    # Filtrar solo notas administrativas por el prefijo en el número
    notas = Nota.objects.filter(numeroNota__startswith='ADM-').order_by('-fechaEmision')
    
    return render(request, 'factura/tablaNotas_administrativas.html', {
        'notas': notas,
    })
    
def obtener_cuotas(request):
    id_persona = request.GET.get('idPersona')
    id_inscripcion = request.GET.get('idInscripcion')

    print(f"ID Persona recibido: {id_persona}")
    print(f"ID Inscripción recibido: {id_inscripcion}")

    if not id_persona:
        print("Error: ID de persona no proporcionado")
        return JsonResponse({'error': 'ID de persona no proporcionado'}, status=400)

    # Filtrar cuotas asociadas a inscripciones de la persona seleccionada
    cuotas = InscripcionCuota.objects.filter(estadoPago='EN ESPERA')
    print(f"Cuotas activas iniciales: {cuotas.count()}")

    if id_inscripcion and id_inscripcion != 'null':
        # Verificar que la inscripción esté asociada a la persona
        inscripcion = Inscripcion.objects.filter(idInscripcion=id_inscripcion, idPersona=id_persona).first()
        print(f"Inscripción encontrada: {inscripcion}")

        if not inscripcion:
            print("Error: La inscripción no está asociada a la persona proporcionada")
            return JsonResponse({'error': 'La inscripción no está asociada a la persona proporcionada'}, status=400)

        # Filtrar cuotas relacionadas directamente con la inscripción
        cuotas = cuotas.filter(idInscripcion=inscripcion)
        print(f"Cuotas relacionadas con la inscripción: {cuotas.count()}")
    else:
        # Filtrar cuotas asociadas a cualquier inscripción de la persona
        cuotas = cuotas.filter(idInscripcion__idPersona=id_persona).distinct()
        print(f"Cuotas relacionadas con la persona: {cuotas.count()}")

    # Si no hay cuotas con estado "EN ESPERA", verificar si hay cuotas con estado "SIN CONFIRMAR"
    if not cuotas.exists():
        cuotas_sin_confirmar = InscripcionCuota.objects.filter(estadoPago='SIN CONFIRMAR', idInscripcion__idPersona=id_persona)
        if cuotas_sin_confirmar.exists():
            print("Error: La inscripción no ha sido pagada")
            return JsonResponse({'error': 'La inscripción no ha sido pagada, por lo tanto no puede proceder con las cuotas.'}, status=400)

    # Serializar los datos de las cuotas
    cuotas_data = [
        {
            'idCuota': cuota.idCuota.idCuota,  # Acceder al ID de la cuota
            'inscripciones': [
                {
                    'idInscripcion': cuota.idInscripcion.idInscripcion,
                    'nombreFormacion': cuota.idInscripcion.idFormacion.nombreFormacion,  # Ejemplo de campo adicional
                }
            ],
            'nombreCuota': cuota.idCuota.nombreCuota,  # Acceder al nombre de la cuota
            'valorCuota': float(cuota.idCuota.valorCuota),  # Acceder al valor de la cuota
        }
        for cuota in cuotas
    ]

    print(f"Datos serializados de cuotas: {cuotas_data}")
    return JsonResponse({'cuotas': cuotas_data})
def crear_relacion_nota(nota, request):
    """
    Crea un registro en la tabla NotaRelacionada si alguno de los IDs está presente en el formulario.
    """
    id_inscripcion = request.POST.get('idInscripcion')
    id_honorario = request.POST.get('idHonorario')
    id_solicitud = request.POST.get('idSolicitud')
    id_cuota = request.POST.get('idCuota')  # Agregar idCuota

    # Solo crea el registro si alguno de los IDs está presente
    if id_inscripcion or id_honorario or id_solicitud or id_cuota:  # Incluir idCuota
        NotaRelacionada.objects.create(
            idNota=nota,
            idInscripcion_id=id_inscripcion if id_inscripcion else None,
            idHonorario_id=id_honorario if id_honorario else None,
            idSolicitud_id=id_solicitud if id_solicitud else None,
            idCuota_id=id_cuota if id_cuota else None  # Agregar idCuota
        )
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
def generar_numero_factura_unico(nota):
    """
    Genera un número único de factura basado en un prefijo y un número secuencial.
    """
    prefijo = "FAC"

    while True:
        # Obtener el último número secuencial basado en el campo numeroFactura
        ultimo = Factura.objects.aggregate(Max('numeroFactura'))['numeroFactura__max']

        # Convertir el último número a entero, manejando ceros a la izquierda
        if ultimo and ultimo.isdigit():
            nuevo = int(ultimo) + 1
        else:
            nuevo = 1

        # Formatear el nuevo número con ceros a la izquierda
        numero_secuencial = f"{nuevo:08d}"

        # Crear el número de factura
        numero_factura = f"{numero_secuencial}"

        # Verificar si el número ya existe en la base de datos
        if not Factura.objects.filter(numeroFactura=numero_factura).exists():
            return numero_factura
@transaction.atomic
def factura_create_notas(request, nota_id=None):
    """
    Vista para crear una factura basada en las notas relacionadas.
    """
    # Verificar si es una solicitud AJAX
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
    
    try:
        # Filtrar las notas según el ID proporcionado o estado 'PAGADO'
        notas = Nota.objects.filter(idNota=nota_id) if nota_id else Nota.objects.filter(estado='PAGADO')

        if not notas.exists():
            if is_ajax:
                return JsonResponse({
                    'success': False,
                    'message': 'No se encontraron notas para generar la factura.'
                }, status=400)
            else:
                messages.error(request, 'No se encontraron notas para generar la factura.')
                return redirect('nota_list')

        # Procesar según tipo de factura
        facturas_creadas = []
        with transaction.atomic():
            for nota in notas:
                # Verificar si ya existe una factura para esta nota (relación OneToOne)
                if hasattr(nota, 'factura'):
                    # Ya existe una factura para esta nota, saltar a la siguiente
                    continue
                
                # Crear la factura - solo establecer campos directos del modelo
                factura = Factura.objects.create(
                    numeroFactura=generar_numero_factura_unico(nota),
                    nota=nota,  # Establecer la relación OneToOne con la nota
                    estado='GENERADA'
                )

                # Crear el detalle de la factura
                FacturaDetalle.objects.create(
                    idFactura=factura,
                    idNota=nota,
                    tipoItem=nota.tipoArticulo,
                    descripcion=f"Nota {nota.numeroNota}",
                    cantidad=1,
                    precioUnitario=nota.totalNota,
                    exento=nota.subtotalExento > 0,
                    descuentoItem=nota.descuento,
                    subtotal=nota.subtotalGravado + nota.subtotalExento,
                    ivaItem=nota.iva,
                    totalItem=nota.totalNota
                )

                # Actualizar estado de la nota
                nota.estado = 'FACTURADO'
                nota.save()

                facturas_creadas.append(factura)

        # Si es AJAX, retornar JSON
        if is_ajax:
            return JsonResponse({
                'success': True,
                'message': f'Factura(s) generada(s) exitosamente. Total: {len(facturas_creadas)}',
                'facturas': [factura.numeroFactura for factura in facturas_creadas],
                'redirect_url': reverse('factura_cargando', args=[facturas_creadas[0].id]) if facturas_creadas else None
            })
        
        # Redirigir a la página de carga para la primera factura creada
        if facturas_creadas:
            return redirect('factura_cargando', pk=facturas_creadas[0].id)
        
        # Si no se crearon facturas (todas ya existían)
        if is_ajax:
            return JsonResponse({
                'success': False,
                'message': 'No se crearon nuevas facturas. Todas las notas ya tienen facturas asociadas.'
            }, status=400)
        else:
            messages.warning(request, 'No se crearon nuevas facturas. Todas las notas ya tienen facturas asociadas.')
            return redirect('nota_list')

    except Exception as e:
        import traceback
        print(f"Error inesperado: {e}")
        print(traceback.format_exc())
        
        if is_ajax:
            return JsonResponse({
                'success': False,
                'message': f'Ocurrió un error inesperado: {str(e)}. '
                           'Por favor, contacte al administrador del sistema si el problema persiste.'
            }, status=500)
        else:
            messages.error(request, f'Ocurrió un error inesperado: {str(e)}')
            return redirect('nota_list')
    
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
    pagos = Pago.objects.all().order_by('-idPago')
    return render(request, 'factura/tablaPago.html', {'pagos': pagos})

def pago_detail(request, pk):
    """
    Vista para mostrar los detalles de un pago específico.
    """
    pago = get_object_or_404(Pago, pk=pk)
    return render(request, 'factura/pago_detail.html', {'pago': pago})


def to_decimal_precise(value):
    """Convierte cualquier valor a Decimal de forma precisa"""
    if value is None:
        return Decimal('0.0')
    if isinstance(value, Decimal):
        return value
    if isinstance(value, float):
        return Decimal(str(value))
    if isinstance(value, int):
        return Decimal(value)
    if isinstance(value, str):
        # Limpiar y estandarizar formato
        cleaned = re.sub(r'[^\d.,-]', '', value.strip())
        if not cleaned:
            return Decimal('0.0')
        # Reemplazar: quitar puntos de mil y cambiar coma decimal por punto
        if ',' in cleaned and '.' in cleaned:
            # Formato con separadores de miles y decimales
            if cleaned.rfind(',') > cleaned.rfind('.'):
                # La coma es el separador decimal (1.000,00)
                cleaned = cleaned.replace('.', '').replace(',', '.')
            else:
                # El punto es el separador decimal (1,000.00)
                cleaned = cleaned.replace(',', '')
        else:
            # Solo un separador presente
            cleaned = cleaned.replace(',', '.')
        return Decimal(cleaned)
    return Decimal(str(value))

def calcular_total_pagado_preciso(pagos, moneda_configuracion, tasa_configuracion_valor):
    """Calcula el total pagado con máxima precisión"""
    total = Decimal('0.0')
    tasa_config = to_decimal_precise(tasa_configuracion_valor)
    
    for pago in pagos:
        monto = to_decimal_precise(pago.monto)
        tasa_pago = to_decimal_precise(pago.idTasa.montoTasa)
        
        if pago.idTasa.idMoneda != moneda_configuracion:
            # Calcular sin redondear intermedios
            conversion = (monto * tasa_pago / tasa_config)
        else:
            conversion = monto
        
        total += conversion
    
    # Redondear solo al final
    return total.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

def convertir_a_moneda_base(monto, moneda_origen, moneda_configuracion, tasa_configuracion_valor):
    """Convierte un monto a la moneda base de configuración"""
    monto_decimal = to_decimal_precise(monto)
    
    # Si ya está en la moneda de configuración, no hay conversión
    if moneda_origen == moneda_configuracion:
        return monto_decimal
    
    # Obtener la tasa de la moneda origen
    tasa_origen = Tasa.objects.filter(idMoneda=moneda_origen).order_by('-idTasa').first()
    if not tasa_origen:
        raise ValueError(f'No se encontró tasa para la moneda {moneda_origen.nombreMoneda}')
    
    tasa_origen_valor = to_decimal_precise(tasa_origen.montoTasa)
    
    # Validar tasas
    validar_tasas(tasa_configuracion_valor, tasa_origen_valor)
    
    # Convertir a moneda base: (monto * tasa_origen) / tasa_configuracion
    conversion = (monto_decimal * tasa_origen_valor / tasa_configuracion_valor)
    return conversion.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

def es_cero_con_tolerancia(decimal_val, tolerancia=Decimal('0.001')):
    """Compara decimales con tolerancia para evitar errores de punto flotante"""
    return abs(decimal_val) <= tolerancia

def validar_tasas(tasa_config, tasa_pago):
    """Valida que las tasas sean válidas para cálculos"""
    if tasa_config <= Decimal('0'):
        raise ValueError("La tasa de configuración debe ser mayor a cero")
    if tasa_pago <= Decimal('0'):
        raise ValueError("La tasa del pago debe ser mayor a cero")
    return True

def obtener_tasas_activas():
    """Obtiene todas las tasas activas con sus monedas"""
    return Tasa.objects.select_related('idMoneda') \
        .values('idMoneda__idMoneda', 'idMoneda__nombreMoneda', 'idMoneda__simboloMoneda') \
        .annotate(ultima_idTasa=Max('idTasa'), ultima_tasa=Max('montoTasa'))

def calcular_conversiones_multimoneda(deuda_base, moneda_base, tasa_base_valor, tasas_activas):
    """
    Calcula conversiones precisas de deuda a múltiples monedas
    Fórmula: deuda_base → moneda_nacional → otras_monedas
    """
    conversiones = {
        'moneda_base': {
            'monto': deuda_base,
            'moneda_id': moneda_base.idMoneda,
            'nombre': moneda_base.nombreMoneda,
            'simbolo': moneda_base.simboloMoneda
        },
        'moneda_nacional': None,
        'otras_monedas': []
    }
    
    # Buscar moneda nacional (ID=1)
    tasa_nacional = None
    for tasa in tasas_activas:
        if tasa['idMoneda__idMoneda'] == 1:  # Moneda nacional
            tasa_nacional = to_decimal_precise(tasa['ultima_tasa'])
            break
    
    if not tasa_nacional:
        print("ADVERTENCIA: No se encontró tasa para moneda nacional (ID=1)")
        return conversiones
    
    # Calcular deuda en moneda nacional
    # Fórmula: deuda_base * tasa_base / tasa_nacional
    deuda_nacional = (deuda_base * tasa_base_valor / tasa_nacional).quantize(
        Decimal('0.0001'), rounding=ROUND_HALF_UP
    )
    
    conversiones['moneda_nacional'] = {
        'monto': deuda_nacional,
        'moneda_id': 1,
        'nombre': next((tasa['idMoneda__nombreMoneda'] for tasa in tasas_activas 
                       if tasa['idMoneda__idMoneda'] == 1), 'Moneda Nacional'),
        'simbolo': next((tasa['idMoneda__simboloMoneda'] for tasa in tasas_activas 
                        if tasa['idMoneda__idMoneda'] == 1), 'BS')
    }
    
    # Calcular conversiones a otras monedas (excluyendo base y nacional)
    for tasa in tasas_activas:
        moneda_id = tasa['idMoneda__idMoneda']
        
        # Excluir moneda base y moneda nacional
        if moneda_id == moneda_base.idMoneda or moneda_id == 1:
            continue
        
        tasa_valor = to_decimal_precise(tasa['ultima_tasa'])
        
        # Validar tasa
        if tasa_valor <= Decimal('0'):
            print(f"ADVERTENCIA: Tasa inválida para {tasa['idMoneda__nombreMoneda']}: {tasa_valor}")
            continue
        
        # Fórmula: deuda_nacional / tasa_moneda_destino
        deuda_convertida = (deuda_nacional / tasa_valor).quantize(
            Decimal('0.0001'), rounding=ROUND_HALF_UP
        )
        
        conversiones['otras_monedas'].append({
            'monto': deuda_convertida,
            'moneda_id': moneda_id,
            'nombre': tasa['idMoneda__nombreMoneda'],
            'simbolo': tasa['idMoneda__simboloMoneda'],
            'tasa_aplicada': tasa_valor
        })
    
    return conversiones

def pago_create(request, pk=None):
    """
    Vista para crear un nuevo pago y generar un asiento contable asociado.
    """
    print("=== INICIANDO VISTA PAGO_CREATE ===")
    # Obtener idTasa desde el formulario y consultar la moneda relacionada
    id_tasa = request.POST.get('idTasa')
    IGTFF = request.POST.get('montoIGTF')
    moneda_pago = None
    id_moneda_pago = None
    if id_tasa:
        try:
            tasa_obj = Tasa.objects.select_related('idMoneda').filter(pk=id_tasa).first()
            if tasa_obj and tasa_obj.idMoneda:
                moneda_pago = tasa_obj.idMoneda              # objeto Moneda relacionado
                id_moneda_pago = tasa_obj.idMoneda.idMoneda  # id de la moneda
            else:
                print(f"No se encontró tasa o moneda para idTasa={id_tasa}")
        except Exception as e:
            print(f"Error al obtener tasa/moneda para idTasa={id_tasa}: {e}")

    # Filtrar notas según el estado y el ID proporcionado
    if pk:
        notas = Nota.objects.filter(idNota=pk, estado__in=['PENDIENTE', 'PARCIAL']).order_by('numeroNota')
        print(f"Filtrando notas por ID específico: {pk}")
    else:
        # Traer las notas excluyendo las pagadas y agregando el símbolo de la moneda
        notas = Nota.objects.select_related('idTasa__idMoneda').exclude(estado__in=['PAGADO', 'FACTURADO']).order_by('numeroNota')
        print(f"Obteniendo todas las notas pendientes/parciales: {notas.count()} notas encontradas")
        
        # Agregar el símbolo de la moneda a cada nota con más información
        for nota in notas:
            simbolo_original = nota.idTasa.idMoneda.simboloMoneda if hasattr(nota.idTasa, 'idMoneda') and hasattr(nota.idTasa.idMoneda, 'simboloMoneda') else ""
            nombre_moneda_original = nota.idTasa.idMoneda.nombreMoneda if hasattr(nota.idTasa, 'idMoneda') and hasattr(nota.idTasa.idMoneda, 'nombreMoneda') else ""
            print(f"Nota {nota.numeroNota} - Moneda original: {nombre_moneda_original} ({simbolo_original}), Total Original: {nota.totalNota}")

    cuentas_banco = CuentaBanco.objects.filter(estado=True).order_by('idCuentaBanco')
    print(f"Cuentas bancarias activas: {cuentas_banco.count()}")
    
    tasas_activas = obtener_tasas_activas()
    print(f"Tasas activas disponibles: {len(tasas_activas)} monedas")
    for tasa in tasas_activas:
        print(f"  - {tasa['idMoneda__nombreMoneda']} ({tasa['idMoneda__simboloMoneda']}): {tasa['ultima_tasa']}")
    
    cuentas_plan = PlanCuenta.objects.filter(estadoPlanCuenta=True).order_by('codigoPlanCuenta')
    print(f"Plan de cuentas activos: {cuentas_plan.count()}")

    # Obtener la moneda de configuración
    configuracion = Configuracion.objects.first()
    if not configuracion:
        print("ERROR: No se encontró configuración activa")
        return JsonResponse({
            'success': False,
            'message': 'No se encontró una configuración activa en el sistema.'
        }, status=400)
    
    moneda_configuracion = configuracion.moneda
    print(f"Moneda de configuración: {moneda_configuracion.nombreMoneda} ({moneda_configuracion.simboloMoneda})")
    
    tasa_configuracion = Tasa.objects.filter(idMoneda=moneda_configuracion).order_by('-idTasa').first()
    if not tasa_configuracion:
        print(f"ERROR: No se encontró tasa para moneda de configuración: {moneda_configuracion.nombreMoneda}")
        return JsonResponse({
            'success': False,
            'message': f'No se encontró una tasa registrada para la moneda de configuración ({moneda_configuracion.nombreMoneda}).'
        }, status=400)

    tasa_configuracion_valor = to_decimal_precise(tasa_configuracion.montoTasa)
    print(f"Tasa de configuración ({moneda_configuracion.nombreMoneda}): {tasa_configuracion_valor}")


    # Calcular el saldo pendiente de cada nota con conversiones multimoneda
    print("\n=== CALCULANDO SALDOS PENDIENTES CON CONVERSIONES MULTIMONEDA ===")
    notas_data = []
    for nota in notas:
        print(f"\n--- Procesando nota {nota.numeroNota} ---")
        
        pagos_relacionados = Pago.objects.filter(idNota=nota, igtf=False)
        print(f"Pagos relacionados: {pagos_relacionados.count()}")
        
        total_pagado = calcular_total_pagado_preciso(pagos_relacionados, moneda_configuracion, tasa_configuracion_valor)
        print(f"Total pagado (moneda base): {total_pagado}")
        
        # Convertir el total de la nota a moneda base
        print(f"Total nota original: {nota.totalNota} ({nota.idTasa.idMoneda.nombreMoneda})")
        total_nota_base = convertir_a_moneda_base(
            nota.totalNota, 
            nota.idTasa.idMoneda, 
            moneda_configuracion, 
            tasa_configuracion_valor
        )
        print(f"Total nota convertido a base: {total_nota_base} ({moneda_configuracion.nombreMoneda})")
        
        saldo_pendiente = (total_nota_base - total_pagado).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        print(f"Saldo pendiente calculado: {saldo_pendiente}")
        
        # CALCULAR CONVERSIONES MULTIMONEDA (Asumiendo que esta función ya devuelve los montos redondeados a 2 decimales, 
        # excepto que sean tasas o valores intermedios, como corregimos en la respuesta anterior)
        print(f"Calculando conversiones multimoneda para saldo: {saldo_pendiente}")
        conversiones = calcular_conversiones_multimoneda(
            saldo_pendiente, 
            moneda_configuracion, 
            tasa_configuracion_valor,
            tasas_activas
        )
        
        # Log de conversiones calculadas
        print(f"CONVERSIONES CALCULADAS:")
        print(f"  - Base: {conversiones['moneda_base']['monto']} {conversiones['moneda_base']['simbolo']}")
        if conversiones['moneda_nacional']:
            print(f"  - Nacional: {conversiones['moneda_nacional']['monto']} {conversiones['moneda_nacional']['simbolo']}")
        for conv in conversiones['otras_monedas']:
            print(f"  - {conv['nombre']}: {conv['monto']} {conv['simbolo']} (tasa: {conv['tasa_aplicada']})")
        
        # CORRECCIÓN CLAVE: Usar str() en todos los montos Decimal para evitar float()
        print(f"ENVIANDO AL FRONTEND - Total: {total_nota_base}, Saldo: {saldo_pendiente}, Símbolo: {moneda_configuracion.simboloMoneda}")
        
        notas_data.append({
            'idNota': nota.idNota,
            'numeroNota': nota.numeroNota,
            # ✅ CORRECCIÓN 1: Convertir Decimal a str
            'totalNota': str(total_nota_base),  # En moneda base, como string preciso
            # ✅ CORRECCIÓN 1: Convertir Decimal a str
            'saldoPendiente': str(saldo_pendiente),  # En moneda base, como string preciso
            'idPersona': nota.idPersona.cedula if nota.idPersona else "N/A",
            'idEmpresa': nota.idEmpresa.nombreEmpresa if nota.idEmpresa else "N/A",
            'estado': nota.estado,
            'simbolo_moneda': moneda_configuracion.simboloMoneda,  # Símbolo de moneda base
            'conversiones_multimoneda': {
                'moneda_base': {
                    # ✅ CORRECCIÓN 1: Convertir Decimal a str
                    'monto': str(conversiones['moneda_base']['monto']),
                    'moneda_id': conversiones['moneda_base']['moneda_id'],
                    'nombre': conversiones['moneda_base']['nombre'],
                    'simbolo': conversiones['moneda_base']['simbolo']
                },
                'moneda_nacional': {
                    # ✅ CORRECCIÓN 1: Convertir Decimal a str (con manejo de None)
                    'monto': str(conversiones['moneda_nacional']['monto']) if conversiones['moneda_nacional'] else '0.00',
                    'moneda_id': conversiones['moneda_nacional']['moneda_id'] if conversiones['moneda_nacional'] else None,
                    'nombre': conversiones['moneda_nacional']['nombre'] if conversiones['moneda_nacional'] else '',
                    'simbolo': conversiones['moneda_nacional']['simbolo'] if conversiones['moneda_nacional'] else ''
                },
                'otras_monedas': [
                    {
                        # ✅ CORRECCIÓN 1: Convertir Decimal a str
                        'monto': str(conv['monto']),
                        'moneda_id': conv['moneda_id'],
                        'nombre': conv['nombre'],
                        'simbolo': conv['simbolo'],
                        # ✅ CORRECCIÓN 1: Convertir Decimal a str
                        'tasa_aplicada': str(conv['tasa_aplicada']) 
                    }
                    for conv in conversiones['otras_monedas']
                ]
            }
        })


    print(f"\n=== RESUMEN NOTAS PROCESADAS ===")
    
    # 📝 Bucle de resumen corregido: Itera una sola vez sobre notas_data para el log.
    for nota_data in notas_data:
        # Los valores se acceden directamente del diccionario, ya sean str o float (para el log)
        print(f"Nota {nota_data['numeroNota']}: Total={nota_data['totalNota']} {nota_data['simbolo_moneda']}, Saldo={nota_data['saldoPendiente']} {nota_data['simbolo_moneda']}")
        
        # Accedemos a la estructura de conversiones para el log
        conversiones = nota_data['conversiones_multimoneda']
        
        if conversiones['moneda_nacional']:
            nacional = conversiones['moneda_nacional']
            print(f"  - Nacional: {nacional['monto']} {nacional['simbolo']}")
            
        for conv in conversiones['otras_monedas']:
            print(f"  - {conv['nombre']}: {conv['monto']} {conv['simbolo']}")

    if request.method == 'POST':
        print("\n=== PROCESANDO SOLICITUD POST ===")
        # Procesar el campo monto para convertirlo a formato decimal
        post_data = request.POST.copy()
        monto_str = post_data.get('monto', '')
        print(f"Monto recibido del formulario: '{monto_str}'")
        
        if monto_str:
            # Usar la función precisa de conversión
            monto_decimal = to_decimal_precise(monto_str)
            post_data['monto'] = str(monto_decimal)
            print(f"Monto convertido a decimal: {monto_decimal}")

        form = PagoForm(post_data)        
        if form.is_valid():
            print("Formulario válido, iniciando procesamiento...")
            try:
                # Iniciar una transacción atómica
                with transaction.atomic():
                    pago = form.save(commit=False)
                    print(f"Pago creado para nota: {pago.idNota.numeroNota}")

                    # Verificar si hay un periodo contable activo
                    periodo_activo = periodoContable.objects.filter(estadoPeriodo=True).first()
                    if not periodo_activo:
                        periodo_activo = periodoContable.objects.order_by('-idPeriodo').first()
                    if not periodo_activo:
                        print("ERROR: No hay periodo contable activo")
                        return JsonResponse({
                            'success': False,
                            'message': 'No hay ningún periodo contable registrado o activo en el sistema. '
                                       'Por favor, registre o active un periodo contable antes de continuar.'
                        }, status=400)
                    print(f"Periodo contable: {periodo_activo}")

                    # Verificar los pagos relacionados a la nota
                    pagos_relacionados = Pago.objects.filter(idNota=pago.idNota, igtf=False)
                    print(f"Pagos existentes para la nota: {pagos_relacionados.count()}")
                    
                    total_pagado = calcular_total_pagado_preciso(pagos_relacionados, moneda_configuracion, tasa_configuracion_valor)
                    print(f"Total pagado acumulado: {total_pagado}")
                    
                    # CORRECCIÓN: Usar la conversión a moneda base también aquí
                    total_nota_base = convertir_a_moneda_base(
                        pago.idNota.totalNota, 
                        pago.idNota.idTasa.idMoneda, 
                        moneda_configuracion, 
                        tasa_configuracion_valor
                    )
                    saldo_nota = (total_nota_base - total_pagado).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
                    
                    print(f"RESUMEN CÁLCULO SALDO:")
                    print(f"  - Total nota (base): {total_nota_base}")
                    print(f"  - Total pagado: {total_pagado}")
                    print(f"  - Saldo nota: {saldo_nota}")

                    # Convertir el monto del pago a la moneda de configuración
                    tasa_pago = Tasa.objects.filter(idMoneda=pago.idTasa.idMoneda).order_by('-idTasa').first()
                    if not tasa_pago:
                        print(f"ERROR: No se encontró tasa para moneda del pago: {pago.idTasa.idMoneda.nombreMoneda}")
                        return JsonResponse({
                            'success': False,
                            'message': f'No se encontró una tasa registrada para la moneda del pago ({pago.idTasa.idMoneda.nombreMoneda}).'
                        }, status=400)

                    print(f"Tasa del pago: {tasa_pago.montoTasa} ({pago.idTasa.idMoneda.nombreMoneda})")

                    # Validar tasas antes de realizar cálculos
                    try:
                        tasa_pago_valor = to_decimal_precise(tasa_pago.montoTasa)
                        print(f"Validando tasas - Config: {tasa_configuracion_valor}, Pago: {tasa_pago_valor}")
                        validar_tasas(tasa_configuracion_valor, tasa_pago_valor)
                        print("Tasas validadas correctamente")
                    except ValueError as e:
                        print(f"ERROR en validación de tasas: {e}")
                        return JsonResponse({
                            'success': False,
                            'message': str(e)
                        }, status=400)

                    # Asegurar precisión en la conversión de monedas
                    try:
                        monto_pago_decimal = to_decimal_precise(pago.monto)
                        tasa_pago_monto = to_decimal_precise(tasa_pago.montoTasa)
                        
                        print(f"CONVERSIÓN DE MONEDA:")
                        print(f"  - Monto pago original: {monto_pago_decimal} ({pago.idTasa.idMoneda.nombreMoneda})")
                        print(f"  - Tasa pago: {tasa_pago_monto}")
                        print(f"  - Tasa configuración: {tasa_configuracion_valor}")
                        
                        if pago.idTasa.idMoneda != moneda_configuracion:
                            monto_pago_convertido = (monto_pago_decimal * tasa_pago_monto / tasa_configuracion_valor)
                            print(f"  - Conversión necesaria: {monto_pago_decimal} * {tasa_pago_monto} / {tasa_configuracion_valor}")
                        else:
                            monto_pago_convertido = monto_pago_decimal
                            print(f"  - Sin conversión (misma moneda)")
                        
                        monto_pago_convertido = monto_pago_convertido.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
                        print(f"  - Monto convertido: {monto_pago_convertido} ({moneda_configuracion.nombreMoneda})")
                    except (InvalidOperation, ZeroDivisionError) as e:
                        print(f"ERROR en conversión de moneda: {e}")
                        return JsonResponse({
                            'success': False,
                            'message': f'Error en la conversión de monedas: {str(e)}. Verifique las tasas de cambio y los montos ingresados.'
                        }, status=400)
                    
                    # Validaciones de saldo
                    print(f"VALIDACIONES:")
                    print(f"  - Saldo nota: {saldo_nota}")
                    print(f"  - Monto pago convertido: {monto_pago_convertido}")
                    
                    if saldo_nota <= Decimal('0.0'):
                        print("ERROR: Nota ya está solvente")
                        return JsonResponse({
                            'success': False,
                            'message': 'El pago no se registró porque la nota ya está solvente.'
                        }, status=400)

                    if monto_pago_convertido > saldo_nota:
                        print(f"ERROR: Monto excede saldo. Saldo: {saldo_nota}, Pago: {monto_pago_convertido}")
                        return JsonResponse({
                            'success': False,
                            'message': f'El monto del pago excede el saldo pendiente de la nota. '
                                       f'Saldo pendiente: {saldo_nota:.2f}.'
                        }, status=400)
                    
                    print("VALIDACIONES PASADAS - Continuando con creación de asiento...")

                    print(f"Monto del Pago: {monto_pago_decimal}")
                    print(f"Tasa de Pago: {tasa_pago_monto}")
                    print(f"Tasa de Configuración: {tasa_configuracion_valor}")
                    print(f"Total Nota (base): {total_nota_base}")
                    print(f"Total Pagado: {total_pagado}")
                    print(f"Saldo Nota: {saldo_nota}")
                    print(f"Monto Pago Convertido: {monto_pago_convertido}")
                    
                    # Obtener la cuenta del Plan de Cuenta usada en el Debe del asiento principal de la nota
                    try:
                        # Obtener la cuenta del Plan de Cuenta usada en el Debe del asiento principal de la nota (la cuenta por cobrar)
                        try:
                            asiento_principal = pago.idNota.idAsiento
                            detalle_debe = DetalleAsiento.objects.filter(idAsiento=asiento_principal, debe__gt=0).first()
                            if not detalle_debe:
                                return JsonResponse({'success': False, 'message': 'No se encontró la cuenta por cobrar en el asiento principal de la nota.'}, status=400)
                            plan_cuenta_haber = detalle_debe.idPlanCuenta
                        except Exception as e:
                            raise ValueError(f'Error al obtener la cuenta por cobrar del asiento principal: {str(e)}')

                        # Crear el asiento contable para el pago
                        try:
                            pagos_existentes = Pago.objects.filter(idNota=pago.idNota).exclude(pk=pago.pk).count()
                            base_numero_asiento = f"PAGO-{pago.idNota.numeroNota}"

                            # Buscar todos los asientos con ese prefijo
                            asientos_similares = AsientoContable.objects.filter(
                                numeroAsiento__startswith=base_numero_asiento
                            ).values_list('numeroAsiento', flat=True)

                            # Inicialmente, intentamos el nombre base
                            if base_numero_asiento not in asientos_similares:
                                numero_asiento_pago = base_numero_asiento
                            else:
                                # Buscar todos los sufijos -N existentes
                                sufijos = []
                                patron = re.compile(rf"^{re.escape(base_numero_asiento)}-(\d+)$")
                                for n in asientos_similares:
                                    match = patron.match(n)
                                    if match:
                                        sufijos.append(int(match.group(1)))
                                if sufijos:
                                    nuevo_sufijo = max(sufijos) + 1
                                else:
                                    nuevo_sufijo = 1
                                numero_asiento_pago = f"{base_numero_asiento}-{nuevo_sufijo}"

                            asiento_pago = AsientoContable.objects.create(
                                numeroAsiento=numero_asiento_pago,
                                fechaAsiento=pago.fechaPago,
                                conceptoAsiento=f"Pago de {pago.idNota.numeroNota}",
                                idPeriodo=periodo_activo
                            )
                        except Exception as e:
                            raise ValueError(f'Error al crear el asiento contable: {str(e)}')

                        # Obtener el plan de cuenta para el Debe (Caja/Banco) según la forma de pago
                        plan_cuenta_debe = None
                        if pago.formaPago == 'EFECTIVO':
                            plan_cuenta_debe = PlanCuenta.objects.filter(codigoPlanCuenta='11000101').first()
                            if not plan_cuenta_debe:
                                return JsonResponse({'success': False, 'message': 'No se encontró el plan de cuenta con código 11000101 para Caja.'}, status=400)
                        else:
                            # Asegúrate de que 'idPlanCuentaDebe' se envíe en el POST cuando la forma de pago no es EFECTIVO
                            plan_cuenta_debe_id = request.POST.get('idPlanCuentaDebe')
                            if not plan_cuenta_debe_id:
                                return JsonResponse({'success': False, 'message': 'Debe seleccionar una cuenta bancaria para esta forma de pago.'}, status=400)
                            plan_cuenta_debe = PlanCuenta.objects.get(pk=plan_cuenta_debe_id)

                        # ==================================================================
                        # ### INICIO DE LA LÓGICA CONTABLE CORREGIDA ###
                        # ==================================================================

                        # 1. Definir la tolerancia para el ajuste por redondeo.
                        TOLERANCIA_REDONDEO = Decimal('0.05')  # Puedes ajustar este valor según tus políticas

                        # 2. Calcular la diferencia. Si es positiva, es un saldo pendiente.
                        diferencia_final = saldo_nota - monto_pago_convertido
                        print(f"Diferencia final calculada: {diferencia_final} (Saldo: {saldo_nota} - Pago: {monto_pago_convertido})")

                        # 3. Determinar el tipo de pago para crear el asiento correcto.
                        es_pago_final_con_ajuste = Decimal('0.0') < diferencia_final <= TOLERANCIA_REDONDEO
                        es_pago_final_exacto = es_cero_con_tolerancia(diferencia_final)
                        es_pago_parcial = diferencia_final > TOLERANCIA_REDONDEO
                       #=================================================================
                        #@@@@LOGICA IGTF CORREGIDA@@@@
                        #=================================================================
                        # Calcular y registrar IGTF de forma segura y precisa
                        try:
                            nota = pago.idNota
                            tipo_operacion = nota.tipoOperacion if nota else None

                            # Determinar si la moneda es nacional (idMoneda == 1)
                            moneda_pago = getattr(pago.idTasa, 'idMoneda', None)
                            moneda_nota = getattr(nota.idTasa, 'idMoneda', None)
                            es_nacional = False
                            if moneda_pago and getattr(moneda_pago, 'idMoneda', None) == 1:
                                es_nacional = True
                            elif moneda_nota and getattr(moneda_nota, 'idMoneda', None) == 1:
                                es_nacional = True

                            # Determinar tipo IGTF según operación y forma de pago
                            if tipo_operacion == 'COBRO':
                                if pago.formaPago == 'EFECTIVO':
                                    tipo_igtf = 'IGTF_NACIONAL_VENTAS_EFECTIVO' if es_nacional else 'IGTF_DIVISA_VENTAS_EFECTIVO'
                                else:
                                    tipo_igtf = 'IGTF_NACIONAL_VENTAS_DIGITAL' if es_nacional else 'IGTF_DIVISA_VENTAS_DIGITAL'
                            elif tipo_operacion == 'PAGO':
                                if pago.formaPago == 'EFECTIVO':
                                    tipo_igtf = 'IGTF_NACIONAL_COMPRAS_EFECTIVO' if es_nacional else 'IGTF_DIVISA_COMPRAS_EFECTIVO'
                                else:
                                    tipo_igtf = 'IGTF_NACIONAL_COMPRAS_DIGITAL' if es_nacional else 'IGTF_DIVISA_COMPRAS_DIGITAL'
                            else:
                                tipo_igtf = None

                            if not tipo_igtf:
                                # No hay tipo IGTF determinado; continuar sin IGTF
                                tipo_igtf = None

                            if tipo_igtf:
                                parametro_igtf = ParametroTributario.objects.filter(tipo=tipo_igtf, activo=True).first()
                            else:
                                parametro_igtf = None

                            if not parametro_igtf:
                                # No hay parámetro activo para este tipo; no aplicar IGTF
                                parametro_igtf = None

                            if parametro_igtf:
                                # Convertir valores a Decimal de forma segura
                                monto_pago_dec = to_decimal_precise(pago.monto)
                                porcentaje_dec = to_decimal_precise(parametro_igtf.porcentaje)

                                # monto_igtf en moneda del pago
                                monto_igtf = (monto_pago_dec * porcentaje_dec / Decimal('100')).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

                                # Si la nota tiene otra moneda y necesitamos convertir, usar tasas históricas
                                monto_igtf_convertido = monto_igtf
                                try:
                                    tasa_pago_obj = pago.idTasa
                                    tasa_nota_obj = nota.idTasa
                                    if tasa_pago_obj and tasa_nota_obj:
                                        tasa_pago_val = to_decimal_precise(tasa_pago_obj.montoTasa)
                                        tasa_nota_val = to_decimal_precise(tasa_nota_obj.montoTasa)
                                        if tasa_nota_val > Decimal('0'):
                                            monto_igtf_convertido = (monto_igtf * tasa_pago_val / tasa_nota_val).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
                                except Exception:
                                    # Si falla la conversión de tasas, mantener monto_igtf en moneda original
                                    monto_igtf_convertido = monto_igtf

                                # ✅ CORRECCIÓN: SIEMPRE sumar al igtfAplicado, excepto cuando ya está PAGADO
                                if nota.estadoIGTF != 'PAGADO':
                                    try:
                                        nota_igtf_actual = to_decimal_precise(nota.igtfAplicado)
                                    except Exception:
                                        nota_igtf_actual = Decimal('0.00')
                                    
                                    # Sumar el nuevo IGTF al acumulado
                                    nota.igtfAplicado = (nota_igtf_actual + monto_igtf_convertido).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
                                    
                                    # ✅ CORRECCIÓN: Actualizar estado IGTF según corresponda
                                    if monto_igtf_convertido > Decimal('0.00'):
                                        # Si hay IGTF aplicado, el estado debe ser PENDIENTE (a menos que ya esté PAGADO)
                                        if nota.estadoIGTF != 'PAGADO':
                                            nota.estadoIGTF = 'PENDIENTE'
                                    else:
                                        # Si no hay IGTF, marcar como NO_APLICA
                                        if nota.estadoIGTF in [None, '']:
                                            nota.estadoIGTF = 'NO_APLICA'
                                
                                nota.save()
                                print(f"[IGTF] Aplicado: {monto_igtf_convertido} | Acumulado: {nota.igtfAplicado} | Estado: {nota.estadoIGTF}")

                        except Exception as ex:
                            # No interrumpir el flujo por errores en IGTF; registrar en consola para debugging
                            print(f"Advertencia: error al calcular/registrar IGTF: {ex}")
                            import traceback
                            print(traceback.format_exc())
                        #===============================================FIN===============
                        DetalleAsiento.objects.filter(idAsiento=asiento_pago).delete()

                        if es_pago_final_con_ajuste:
                            # --- CASO 1: PAGO FINAL CON AJUSTE POR REDONDEO (Asiento Compuesto de 3 líneas) ---
                            print(f"AJUSTE: La diferencia {diferencia_final} está dentro de la tol=erancia. Se considera pago final.")

                            # ¡IMPORTANTE! Debes crear esta cuenta en tu plan de cuentas y usar el código correcto aquí.
                            cuenta_ajuste_gasto = PlanCuenta.objects.filter(codigoPlanCuenta='52000104').first()
                            if not cuenta_ajuste_gasto:
                                raise ValueError("No se encontró la cuenta contable para 'GASTOS POR REDONDEO DE CONVERSIÓN MONETARIA' (COD: 52000104).")

                            # Detalle 1: Ingreso a Caja/Banco (DEBE)
                            DetalleAsiento.objects.create(idAsiento=asiento_pago, idMoneda=moneda_pago, idPlanCuenta=plan_cuenta_debe, debe=float(monto_pago_convertido), haber=0.00)
                            # Detalle 2: Pérdida por Redondeo (DEBE) - ¡ESTA ES LA CORRECCIÓN CLAVE!
                            DetalleAsiento.objects.create(idAsiento=asiento_pago, idMoneda=moneda_pago, idPlanCuenta=cuenta_ajuste_gasto, debe=float(diferencia_final), haber=0.00)
                            # Detalle 3: Cancelación total de la Cuenta por Cobrar (HABER)
                            DetalleAsiento.objects.create(idAsiento=asiento_pago, idMoneda=moneda_pago, idPlanCuenta=plan_cuenta_haber, debe=0.00, haber=float(saldo_nota))

                            print(f"Asiento compuesto cuadrado. Total Debe: {monto_pago_convertido + diferencia_final}, Total Haber: {saldo_nota}")
                            # ✅ MODIFICACIÓN: Verificar estado IGTF antes de marcar como PAGADO
                            if pago.idNota.estadoIGTF in ['NO_APLICA', 'PAGADO']:
                                pago.idNota.estado = 'PAGADO'
                                print("Nota marcada como PAGADO (saldo e IGTF cubiertos)")
                            else:
                                pago.idNota.estado = 'PARCIAL'
                                print(f"Nota marcada como PARCIAL (saldo cubierto pero IGTF pendiente: {pago.idNota.estadoIGTF})")

                        elif es_pago_final_exacto:
                            # --- CASO 2: PAGO FINAL EXACTO (Asiento Simple de 2 líneas) ---
                            print("PAGO EXACTO: La nota se considera saldada.")

                            # Detalle 1: Ingreso a Caja/Banco (DEBE)
                            DetalleAsiento.objects.create(idAsiento=asiento_pago, idMoneda=moneda_pago, idPlanCuenta=plan_cuenta_debe, debe=float(monto_pago_convertido), haber=0.00)
                            # Detalle 2: Cancelación de la Cuenta por Cobrar (HABER)
                            DetalleAsiento.objects.create(idAsiento=asiento_pago, idMoneda=moneda_pago, idPlanCuenta=plan_cuenta_haber, debe=0.00, haber=float(monto_pago_convertido))

                             # ✅ MODIFICACIÓN: Verificar estado IGTF antes de marcar como PAGADO
                            if pago.idNota.estadoIGTF in ['NO_APLICA', 'PAGADO']:
                                pago.idNota.estado = 'PAGADO'
                                print("Nota marcada como PAGADO (saldo e IGTF cubiertos)")
                            else:
                                pago.idNota.estado = 'PARCIAL'
                                print(f"Nota marcada como PARCIAL (saldo cubierto pero IGTF pendiente: {pago.idNota.estadoIGTF})")

                        elif es_pago_parcial:
                            # --- CASO 3: PAGO PARCIAL (Asiento Simple de 2 líneas) ---
                            print("PAGO PARCIAL: Aún queda saldo pendiente.")

                            # Detalle 1: Ingreso a Caja/Banco (DEBE)
                            DetalleAsiento.objects.create(idAsiento=asiento_pago, idMoneda=moneda_pago, idPlanCuenta=plan_cuenta_debe, debe=float(monto_pago_convertido), haber=0.00)
                            # Detalle 2: Abono a la Cuenta por Cobrar (HABER)
                            DetalleAsiento.objects.create(idAsiento=asiento_pago, idMoneda=moneda_pago, idPlanCuenta=plan_cuenta_haber, debe=0.00, haber=float(monto_pago_convertido))

                            pago.idNota.estado = 'PARCIAL'

                        else:
                            # Caso de sobrepago (diferencia_final es negativa), que la validación inicial debería prevenir.
                            return JsonResponse({'success': False, 'message': f'Error: El monto del pago {monto_pago_convertido} excede el saldo de la deuda {saldo_nota}.'}, status=400)

                        # ==================================================================
                        # ### FIN DE LA LÓGICA CONTABLE CORREGIDA ###
                        # ==================================================================

                        # Asociar el asiento contable al pago y guardar cambios
                        pago.idAsiento = asiento_pago
                        pago.save()
                        pago.idNota.save() # Guardar el nuevo estado de la nota ('PAGADO' o 'PARCIAL')
                        try:
                            if IGTFF:
                                monto_igtf_dec = to_decimal_precise(IGTFF)
                                if monto_igtf_dec > Decimal('0'):
                                    # Reutilizar valores calculados anteriormente si existen
                                    tipo = locals().get('tipo_igtf') or request.POST.get('tipoIGTF')
                                    porcentaje = locals().get('porcentaje_dec')
                                    # Si no tenemos porcentaje, intentar obtenerlo desde ParametroTributario
                                    if porcentaje is None:
                                        parametro = ParametroTributario.objects.filter(tipo=tipo, activo=True).first() if tipo else None
                                        porcentaje = to_decimal_precise(parametro.porcentaje) if parametro and parametro.porcentaje is not None else Decimal('0.00')

                                    PagoIGTF.objects.create(
                                        idPago=pago,
                                        tipoIGTF=tipo,
                                        montoIGTF=monto_igtf_dec,
                                        porcentajeIGTF=porcentaje
                                    )

                        except Exception as e:
                            # No interrumpir el flujo; registrar para depuración
                            print(f"Advertencia: error creando PagoIGTF: {e}")
                        # --- LÓGICA POST-PAGO ---
                        # Ahora, basado en el estado final de la nota, ejecutamos las acciones correspondientes.

                        if pago.idNota.estado == 'PARCIAL':
                            # Determinar el motivo del estado PARCIAL
                            motivo_parcial = ""
                            if es_pago_parcial:
                                motivo_parcial = "aún posee deuda financiera"
                                pagar_igtf = False
                            else:
                                motivo_parcial = f"aún posee IGTF pendiente (estado: {pago.idNota.estadoIGTF})"
                                pagar_igtf = True

                                # Consultar el PlanArticulo para determinar las cuentas contables
                                plan_articulos = PlanArticulo.objects.filter(tipoArticulo='IGTF')
                                if not plan_articulos.exists():
                                    # Si no se encuentran planes de artículo para IGTF, no se realiza ninguna acción
                                    return

                                # Determinar las cuentas contables para el Debe y el Haber
                                cuenta_debe = plan_articulos.filter(tipo=True).first()  # `tipo=True` indica que es Debe
                                cuenta_haber = plan_articulos.filter(tipo=False).first()  # `tipo=False` indica que es Haber

                                if not cuenta_debe or not cuenta_haber:
                                    # Si no se encuentran las cuentas contables, no se realiza ninguna acción
                                    return
                                if monto_igtf > Decimal('0.00'):
                                    # 1. Crear NUEVO asiento para IGTF
                                    asiento_igtf = AsientoContable.objects.create(
                                        numeroAsiento=f"IGTF-{nota.numeroNota}",
                                        fechaAsiento=pago.fechaPago,  # o fecha actual
                                        conceptoAsiento=f"Pago IGTF - Nota {nota.numeroNota}",
                                        idPeriodo=periodo_activo
                                    )

                                    # 2.Crear los detalles en el NUEVO asiento
                                    plan_articulos = PlanArticulo.objects.filter(tipoArticulo='IGTF')
                                    if plan_articulos.exists():
                                        cuenta_debe = plan_articulos.filter(tipo=True).first()
                                        cuenta_haber = plan_articulos.filter(tipo=False).first()
                                        # Obtener el ID del asiento IGTF de manera segura
                                        asiento_igtf_id = getattr(asiento_igtf, 'idAsiento', None) or getattr(asiento_igtf, 'pk', None)

                                        if cuenta_debe and cuenta_haber:
                                            DetalleAsiento.objects.create(
                                                idAsiento_id=asiento_igtf_id,
                                                idMoneda=nota.idTasa.idMoneda,
                                                idPlanCuenta=cuenta_debe.idPlanCuenta,
                                                debe=float(monto_igtf),
                                                haber=0.00
                                            )

                                            DetalleAsiento.objects.create(
                                                idAsiento_id=asiento_igtf_id,
                                                idMoneda=nota.idTasa.idMoneda,
                                                idPlanCuenta=cuenta_haber.idPlanCuenta,
                                                debe=0.00,
                                                haber=float(monto_igtf)
                                            )

                                            # 3. Asociar el asiento IGTF a la nota
                                            IDasiento_igtf = AsientoContable.objects.get(pk=asiento_igtf_id)  # Obtén la instancia
                                            nota.asiento_igtf = IDasiento_igtf  # Asigna la instancia
                                            nota.estadoIGTF = 'PARCIAL'
                                            nota.save()
                                            

                            # Actualizar estado de entidades relacionadas a 'PARCIAL'
                            nota_relacionada = NotaRelacionada.objects.filter(idNota=pago.idNota).first()
                            if nota_relacionada:
                                match nota_relacionada:
                                    case _ if nota_relacionada.idInscripcion:
                                        nota_relacionada.idInscripcion.estadoPago = 'PARCIAL'
                                        nota_relacionada.idInscripcion.save()
                                    case _ if nota_relacionada.idCuota:
                                        nota_relacionada.idCuota.estadoPago = 'PARCIAL'
                                        nota_relacionada.idCuota.save()
                                    case _ if nota_relacionada.idSolicitud:
                                        nota_relacionada.idSolicitud.estadoPago = 'PARCIAL'
                                        nota_relacionada.idSolicitud.save()
                                    case _ if nota_relacionada.idHonorario:
                                        nota_relacionada.idHonorario.estadoPago = 'PARCIAL'
                                        nota_relacionada.idHonorario.save()

    
                            return JsonResponse({
                                'success': True,
                                'message': f'El pago fue exitoso, {motivo_parcial} ¿Desea realizar otro pago adicional?',
                                'redirect_url': f"{reverse('pago_create')}?nota={pago.idNota.idNota}",
                                'pago': {
                                    'idPago': pago.idPago,
                                    'idNota': pago.idNota.numeroNota,
                                    'monto': f"{float(monto_pago_decimal):.2f} {pago.idTasa.idMoneda.simboloMoneda}",
                                    'fechaPago': pago.fechaPago.strftime('%d/%m/%Y'),
                                    'formaPago': pago.formaPago,
                                    'referencia': pago.referencia,
                                    'estado_igtf': pago.idNota.estadoIGTF,
                                    'pagar_igtf': pagar_igtf,
                                    'monto_igtf': f"{float(monto_igtf):.2f} {pago.idTasa.idMoneda.simboloMoneda}"
                                },
                                'IGTF': pago.idNota.estadoIGTF,
                                'url_igtf': f"{reverse('pago_createigtf')}?nota={pago.idNota.idNota}"
                            })
                        
                        elif pago.idNota.estado == 'PAGADO':
                            # Actualizar estado de entidades relacionadas a 'PAGADO'
                            nota_relacionada = NotaRelacionada.objects.filter(idNota=pago.idNota).first()
                            if nota_relacionada:
                                # Usamos pattern matching para actualizar el estado de la entidad relacionada a 'PAGADO'
                                match nota_relacionada:
                                    case _ if nota_relacionada.idInscripcion:
                                        # Si la nota está relacionada a una inscripción, actualizamos su estado y el de sus cuotas pendientes
                                        inscripcion = nota_relacionada.idInscripcion
                                        inscripcion.estadoPago = 'PAGADO'
                                        inscripcion.save()
                                     
                                    case _ if nota_relacionada.idCuota:
                                        # Si la nota está relacionada a una cuota, actualizamos su estado a pagado
                                        nota_relacionada.idCuota.estadoPago = 'PAGADO'
                                        nota_relacionada.idCuota.save()
                                    case _ if nota_relacionada.idSolicitud:
                                        # Si la nota está relacionada a una solicitud, actualizamos su estado a pagado
                                        nota_relacionada.idSolicitud.estadoPago = 'PAGADO'
                                        nota_relacionada.idSolicitud.save()
                                    case _ if nota_relacionada.idHonorario:
                                        # Si la nota está relacionada a un honorario, actualizamos su estado a pagado
                                        nota_relacionada.idHonorario.estadoPago = 'PAGADO'
                                        nota_relacionada.idHonorario.save()

                            return JsonResponse({
                                'success': True,
                                'message': 'Pago creado exitosamente. La nota ha sido pagada en su totalidad.',
                                'redirect_url': reverse('nota_list'), # Redirige a la lista de notas o donde prefieras
                                'pago': {
                                    'idPago': pago.idPago,
                                    'idNota': pago.idNota.numeroNota,
                                    'monto': f"{float(monto_pago_decimal):.2f} {pago.idTasa.idMoneda.simboloMoneda}",
                                    'fechaPago': pago.fechaPago.strftime('%d/%m/%Y'),
                                    'formaPago': pago.formaPago,
                                    'referencia': pago.referencia,
                                    'IGTF': pago.idNota.estadoIGTF
                                }
                            })

                        else:
                            # Caso donde el pago es mayor al saldo (no debería ocurrir por validación previa)
                            return JsonResponse({
                                'success': False,
                                'message': 'Error inesperado en el cálculo del saldo.'
                            }, status=400)
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
        'notas': notas_data, 
        'cuentas_banco': cuentas_banco,
        'cuentas_plan': cuentas_plan,
        'monedas': tasas_activas,
        'notas_json': json.dumps(notas_data, cls=DecimalEncoder) 
    })

def pago_createigtf(request, pk=None):
    """
    Vista para crear un nuevo pago y generar un asiento contable asociado.
    """
    print("=== INICIANDO VISTA PAGO_CREATE ===")
    # Obtener idTasa desde el formulario y consultar la moneda relacionada
    id_tasa = request.POST.get('idTasa')
    IGTFF = request.POST.get('montoIGTF')
    moneda_pago = None
    id_moneda_pago = None
    if id_tasa:
        try:
            tasa_obj = Tasa.objects.select_related('idMoneda').filter(pk=id_tasa).first()
            if tasa_obj and tasa_obj.idMoneda:
                moneda_pago = tasa_obj.idMoneda              # objeto Moneda relacionado
                id_moneda_pago = tasa_obj.idMoneda.idMoneda  # id de la moneda
            else:
                print(f"No se encontró tasa o moneda para idTasa={id_tasa}")
        except Exception as e:
            print(f"Error al obtener tasa/moneda para idTasa={id_tasa}: {e}")

    # Filtrar notas según el estado y el ID proporcionado
    if pk:
        notas = Nota.objects.filter(idNota=pk, estado__in=['PENDIENTE', 'PARCIAL']).order_by('numeroNota')
        print(f"Filtrando notas por ID específico: {pk}")
    else:
        # Traer las notas excluyendo las pagadas y agregando el símbolo de la moneda
        notas = Nota.objects.select_related('idTasa__idMoneda').exclude(estado__in=['PAGADO', 'FACTURADO']).order_by('numeroNota')
        print(f"Obteniendo todas las notas pendientes/parciales: {notas.count()} notas encontradas")
        
        # Agregar el símbolo de la moneda a cada nota con más información
        for nota in notas:
            simbolo_original = nota.idTasa.idMoneda.simboloMoneda if hasattr(nota.idTasa, 'idMoneda') and hasattr(nota.idTasa.idMoneda, 'simboloMoneda') else ""
            nombre_moneda_original = nota.idTasa.idMoneda.nombreMoneda if hasattr(nota.idTasa, 'idMoneda') and hasattr(nota.idTasa.idMoneda, 'nombreMoneda') else ""
            print(f"Nota {nota.numeroNota} - Moneda original: {nombre_moneda_original} ({simbolo_original}), Total Original: {nota.igtfAplicado}")

    cuentas_banco = CuentaBanco.objects.filter(estado=True).order_by('idCuentaBanco')
    print(f"Cuentas bancarias activas: {cuentas_banco.count()}")
    
    tasas_activas = obtener_tasas_activas()
    print(f"Tasas activas disponibles: {len(tasas_activas)} monedas")
    for tasa in tasas_activas:
        print(f"  - {tasa['idMoneda__nombreMoneda']} ({tasa['idMoneda__simboloMoneda']}): {tasa['ultima_tasa']}")
    
    cuentas_plan = PlanCuenta.objects.filter(estadoPlanCuenta=True).order_by('codigoPlanCuenta')
    print(f"Plan de cuentas activos: {cuentas_plan.count()}")

    # Obtener la moneda de configuración
    configuracion = Configuracion.objects.first()
    if not configuracion:
        print("ERROR: No se encontró configuración activa")
        return JsonResponse({
            'success': False,
            'message': 'No se encontró una configuración activa en el sistema.'
        }, status=400)
    
    moneda_configuracion = configuracion.moneda
    print(f"Moneda de configuración: {moneda_configuracion.nombreMoneda} ({moneda_configuracion.simboloMoneda})")
    
    tasa_configuracion = Tasa.objects.filter(idMoneda=moneda_configuracion).order_by('-idTasa').first()
    if not tasa_configuracion:
        print(f"ERROR: No se encontró tasa para moneda de configuración: {moneda_configuracion.nombreMoneda}")
        return JsonResponse({
            'success': False,
            'message': f'No se encontró una tasa registrada para la moneda de configuración ({moneda_configuracion.nombreMoneda}).'
        }, status=400)

    tasa_configuracion_valor = to_decimal_precise(tasa_configuracion.montoTasa)
    print(f"Tasa de configuración ({moneda_configuracion.nombreMoneda}): {tasa_configuracion_valor}")


    # Calcular el saldo pendiente de cada nota con conversiones multimoneda
    print("\n=== CALCULANDO SALDOS PENDIENTES CON CONVERSIONES MULTIMONEDA ===")
    notas_data = []
    for nota in notas:
        print(f"\n--- Procesando nota {nota.numeroNota} ---")
        
        pagos_relacionados = Pago.objects.filter(idNota=nota, igtf=True)
        print(f"Pagos relacionados: {pagos_relacionados.count()}")
        
        total_pagado = calcular_total_pagado_preciso(pagos_relacionados, moneda_configuracion, tasa_configuracion_valor)
        print(f"Total pagado (moneda base): {total_pagado}")
        
        # Convertir el total de la nota a moneda base
        print(f"Total nota original: {nota.igtfAplicado} ({nota.idTasa.idMoneda.nombreMoneda})")
        total_nota_base = convertir_a_moneda_base(
            nota.igtfAplicado, 
            nota.idTasa.idMoneda, 
            moneda_configuracion, 
            tasa_configuracion_valor
        )
        print(f"Total nota convertido a base: {total_nota_base} ({moneda_configuracion.nombreMoneda})")
        
        saldo_pendiente = (total_nota_base - total_pagado).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        print(f"Saldo pendiente calculado: {saldo_pendiente}")
        
        # CALCULAR CONVERSIONES MULTIMONEDA (Asumiendo que esta función ya devuelve los montos redondeados a 2 decimales, 
        # excepto que sean tasas o valores intermedios, como corregimos en la respuesta anterior)
        print(f"Calculando conversiones multimoneda para saldo: {saldo_pendiente}")
        conversiones = calcular_conversiones_multimoneda(
            saldo_pendiente, 
            moneda_configuracion, 
            tasa_configuracion_valor,
            tasas_activas
        )
        
        # Log de conversiones calculadas
        print(f"CONVERSIONES CALCULADAS:")
        print(f"  - Base: {conversiones['moneda_base']['monto']} {conversiones['moneda_base']['simbolo']}")
        if conversiones['moneda_nacional']:
            print(f"  - Nacional: {conversiones['moneda_nacional']['monto']} {conversiones['moneda_nacional']['simbolo']}")
        for conv in conversiones['otras_monedas']:
            print(f"  - {conv['nombre']}: {conv['monto']} {conv['simbolo']} (tasa: {conv['tasa_aplicada']})")
        
        # CORRECCIÓN CLAVE: Usar str() en todos los montos Decimal para evitar float()
        print(f"ENVIANDO AL FRONTEND - Total: {total_nota_base}, Saldo: {saldo_pendiente}, Símbolo: {moneda_configuracion.simboloMoneda}")
        
        notas_data.append({
            'idNota': nota.idNota,
            'numeroNota': nota.numeroNota,
            # ✅ CORRECCIÓN 1: Convertir Decimal a str
            'igtfAplicado': str(total_nota_base),  # En moneda base, como string preciso
            # ✅ CORRECCIÓN 1: Convertir Decimal a str
            'saldoPendiente': str(saldo_pendiente),  # En moneda base, como string preciso
            'idPersona': nota.idPersona.cedula if nota.idPersona else "N/A",
            'idEmpresa': nota.idEmpresa.nombreEmpresa if nota.idEmpresa else "N/A",
            'estado': nota.estado,
            'simbolo_moneda': moneda_configuracion.simboloMoneda,  # Símbolo de moneda base
            'conversiones_multimoneda': {
                'moneda_base': {
                    # ✅ CORRECCIÓN 1: Convertir Decimal a str
                    'monto': str(conversiones['moneda_base']['monto']),
                    'moneda_id': conversiones['moneda_base']['moneda_id'],
                    'nombre': conversiones['moneda_base']['nombre'],
                    'simbolo': conversiones['moneda_base']['simbolo']
                },
                'moneda_nacional': {
                    # ✅ CORRECCIÓN 1: Convertir Decimal a str (con manejo de None)
                    'monto': str(conversiones['moneda_nacional']['monto']) if conversiones['moneda_nacional'] else '0.00',
                    'moneda_id': conversiones['moneda_nacional']['moneda_id'] if conversiones['moneda_nacional'] else None,
                    'nombre': conversiones['moneda_nacional']['nombre'] if conversiones['moneda_nacional'] else '',
                    'simbolo': conversiones['moneda_nacional']['simbolo'] if conversiones['moneda_nacional'] else ''
                },
                'otras_monedas': [
                    {
                        # ✅ CORRECCIÓN 1: Convertir Decimal a str
                        'monto': str(conv['monto']),
                        'moneda_id': conv['moneda_id'],
                        'nombre': conv['nombre'],
                        'simbolo': conv['simbolo'],
                        # ✅ CORRECCIÓN 1: Convertir Decimal a str
                        'tasa_aplicada': str(conv['tasa_aplicada']) 
                    }
                    for conv in conversiones['otras_monedas']
                ]
            }
        })


    print(f"\n=== RESUMEN NOTAS PROCESADAS ===")
    
    # 📝 Bucle de resumen corregido: Itera una sola vez sobre notas_data para el log.
    for nota_data in notas_data:
        # Los valores se acceden directamente del diccionario, ya sean str o float (para el log)
        print(f"Nota {nota_data['numeroNota']}: Total={nota_data['igtfAplicado']} {nota_data['simbolo_moneda']}, Saldo={nota_data['saldoPendiente']} {nota_data['simbolo_moneda']}")
        
        # Accedemos a la estructura de conversiones para el log
        conversiones = nota_data['conversiones_multimoneda']
        
        if conversiones['moneda_nacional']:
            nacional = conversiones['moneda_nacional']
            print(f"  - Nacional: {nacional['monto']} {nacional['simbolo']}")
            
        for conv in conversiones['otras_monedas']:
            print(f"  - {conv['nombre']}: {conv['monto']} {conv['simbolo']}")

    if request.method == 'POST':
        print("\n=== PROCESANDO SOLICITUD POST ===")
        # Procesar el campo monto para convertirlo a formato decimal
        post_data = request.POST.copy()
        monto_str = post_data.get('monto', '')
        print(f"Monto recibido del formulario: '{monto_str}'")
        
        if monto_str:
            # Usar la función precisa de conversión
            monto_decimal = to_decimal_precise(monto_str)
            post_data['monto'] = str(monto_decimal)
            print(f"Monto convertido a decimal: {monto_decimal}")

        form = PagoForm(post_data)        
        if form.is_valid():
            print("Formulario válido, iniciando procesamiento...")
            try:
                # Iniciar una transacción atómica
                with transaction.atomic():
                    pago = form.save(commit=False)
                    print(f"Pago creado para nota: {pago.idNota.numeroNota}")

                    # Verificar si hay un periodo contable activo
                    periodo_activo = periodoContable.objects.filter(estadoPeriodo=True).first()
                    if not periodo_activo:
                        periodo_activo = periodoContable.objects.order_by('-idPeriodo').first()
                    if not periodo_activo:
                        print("ERROR: No hay periodo contable activo")
                        return JsonResponse({
                            'success': False,
                            'message': 'No hay ningún periodo contable registrado o activo en el sistema. '
                                       'Por favor, registre o active un periodo contable antes de continuar.'
                        }, status=400)
                    print(f"Periodo contable: {periodo_activo}")

                    # Verificar los pagos relacionados a la nota
                    pagos_relacionados = Pago.objects.filter(idNota=pago.idNota, igtf=True)
                    print(f"Pagos existentes para la nota: {pagos_relacionados.count()}")
                    
                    total_pagado = calcular_total_pagado_preciso(pagos_relacionados, moneda_configuracion, tasa_configuracion_valor)
                    print(f"Total pagado acumulado: {total_pagado}")
                    
                    # CORRECCIÓN: Usar la conversión a moneda base también aquí
                    total_nota_base = convertir_a_moneda_base(
                        pago.idNota.igtfAplicado, 
                        pago.idNota.idTasa.idMoneda, 
                        moneda_configuracion, 
                        tasa_configuracion_valor
                    )
                    saldo_nota = (total_nota_base - total_pagado).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
                    
                    print(f"RESUMEN CÁLCULO SALDO:")
                    print(f"  - Total nota (base): {total_nota_base}")
                    print(f"  - Total pagado: {total_pagado}")
                    print(f"  - Saldo nota: {saldo_nota}")

                    # Convertir el monto del pago a la moneda de configuración
                    tasa_pago = Tasa.objects.filter(idMoneda=pago.idTasa.idMoneda).order_by('-idTasa').first()
                    if not tasa_pago:
                        print(f"ERROR: No se encontró tasa para moneda del pago: {pago.idTasa.idMoneda.nombreMoneda}")
                        return JsonResponse({
                            'success': False,
                            'message': f'No se encontró una tasa registrada para la moneda del pago ({pago.idTasa.idMoneda.nombreMoneda}).'
                        }, status=400)

                    print(f"Tasa del pago: {tasa_pago.montoTasa} ({pago.idTasa.idMoneda.nombreMoneda})")

                    # Validar tasas antes de realizar cálculos
                    try:
                        tasa_pago_valor = to_decimal_precise(tasa_pago.montoTasa)
                        print(f"Validando tasas - Config: {tasa_configuracion_valor}, Pago: {tasa_pago_valor}")
                        validar_tasas(tasa_configuracion_valor, tasa_pago_valor)
                        print("Tasas validadas correctamente")
                    except ValueError as e:
                        print(f"ERROR en validación de tasas: {e}")
                        return JsonResponse({
                            'success': False,
                            'message': str(e)
                        }, status=400)

                    # Asegurar precisión en la conversión de monedas
                    try:
                        monto_pago_decimal = to_decimal_precise(pago.monto)
                        tasa_pago_monto = to_decimal_precise(tasa_pago.montoTasa)
                        
                        print(f"CONVERSIÓN DE MONEDA:")
                        print(f"  - Monto pago original: {monto_pago_decimal} ({pago.idTasa.idMoneda.nombreMoneda})")
                        print(f"  - Tasa pago: {tasa_pago_monto}")
                        print(f"  - Tasa configuración: {tasa_configuracion_valor}")
                        
                        if pago.idTasa.idMoneda != moneda_configuracion:
                            monto_pago_convertido = (monto_pago_decimal * tasa_pago_monto / tasa_configuracion_valor)
                            print(f"  - Conversión necesaria: {monto_pago_decimal} * {tasa_pago_monto} / {tasa_configuracion_valor}")
                        else:
                            monto_pago_convertido = monto_pago_decimal
                            print(f"  - Sin conversión (misma moneda)")
                        
                        monto_pago_convertido = monto_pago_convertido.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
                        print(f"  - Monto convertido: {monto_pago_convertido} ({moneda_configuracion.nombreMoneda})")
                    except (InvalidOperation, ZeroDivisionError) as e:
                        print(f"ERROR en conversión de moneda: {e}")
                        return JsonResponse({
                            'success': False,
                            'message': f'Error en la conversión de monedas: {str(e)}. Verifique las tasas de cambio y los montos ingresados.'
                        }, status=400)
                    
                    # Validaciones de saldo
                    print(f"VALIDACIONES:")
                    print(f"  - Saldo nota: {saldo_nota}")
                    print(f"  - Monto pago convertido: {monto_pago_convertido}")
                    
                    if saldo_nota <= Decimal('0.0'):
                        print("ERROR: Nota ya está solvente")
                        return JsonResponse({
                            'success': False,
                            'message': 'El pago no se registró porque la nota ya está solvente.'
                        }, status=400)

                    if monto_pago_convertido > saldo_nota:
                        print(f"ERROR: Monto excede saldo. Saldo: {saldo_nota}, Pago: {monto_pago_convertido}")
                        return JsonResponse({
                            'success': False,
                            'message': f'El monto del pago excede el saldo pendiente de la nota. '
                                       f'Saldo pendiente: {saldo_nota:.2f}.'
                        }, status=400)
                    
                    print("VALIDACIONES PASADAS - Continuando con creación de asiento...")

                    print(f"Monto del Pago: {monto_pago_decimal}")
                    print(f"Tasa de Pago: {tasa_pago_monto}")
                    print(f"Tasa de Configuración: {tasa_configuracion_valor}")
                    print(f"Total Nota (base): {total_nota_base}")
                    print(f"Total Pagado: {total_pagado}")
                    print(f"Saldo Nota: {saldo_nota}")
                    print(f"Monto Pago Convertido: {monto_pago_convertido}")
                    
                    # Obtener la cuenta del Plan de Cuenta usada en el Debe del asiento principal de la nota
                    try:
                        # Obtener la cuenta del Plan de Cuenta usada en el Debe del asiento principal de la nota (la cuenta por cobrar)
                        try:
                            asiento_principal = pago.idNota.asiento_igtf
                            detalle_debe = DetalleAsiento.objects.filter(idAsiento=asiento_principal, debe__gt=0).first()
                            if not detalle_debe:
                                return JsonResponse({'success': False, 'message': 'No se encontró la cuenta por cobrar en el asiento principal de la nota.'}, status=400)
                            plan_cuenta_haber = detalle_debe.idPlanCuenta
                        except Exception as e:
                            raise ValueError(f'Error al obtener la cuenta por cobrar del asiento principal: {str(e)}')

                        # Crear el asiento contable para el pago
                        try:
                            pagos_existentes = Pago.objects.filter(idNota=pago.idNota).exclude(pk=pago.pk).count()
                            base_numero_asiento = f"PAGO-{pago.idNota.numeroNota}"

                            # Buscar todos los asientos con ese prefijo
                            asientos_similares = AsientoContable.objects.filter(
                                numeroAsiento__startswith=base_numero_asiento
                            ).values_list('numeroAsiento', flat=True)

                            # Inicialmente, intentamos el nombre base
                            if base_numero_asiento not in asientos_similares:
                                numero_asiento_pago = base_numero_asiento
                            else:
                                # Buscar todos los sufijos -N existentes
                                sufijos = []
                                patron = re.compile(rf"^{re.escape(base_numero_asiento)}-(\d+)$")
                                for n in asientos_similares:
                                    match = patron.match(n)
                                    if match:
                                        sufijos.append(int(match.group(1)))
                                if sufijos:
                                    nuevo_sufijo = max(sufijos) + 1
                                else:
                                    nuevo_sufijo = 1
                                numero_asiento_pago = f"{base_numero_asiento}-{nuevo_sufijo}"

                            asiento_pago = AsientoContable.objects.create(
                                numeroAsiento=numero_asiento_pago,
                                fechaAsiento=pago.fechaPago,
                                conceptoAsiento=f"Pago de IGTF - {pago.idNota.numeroNota}",
                                idPeriodo=periodo_activo
                            )
                        except Exception as e:
                            raise ValueError(f'Error al crear el asiento contable: {str(e)}')

                        # Obtener el plan de cuenta para el Debe (Caja/Banco) según la forma de pago
                        plan_cuenta_debe = None
                        if pago.formaPago == 'EFECTIVO':
                            plan_cuenta_debe = PlanCuenta.objects.filter(codigoPlanCuenta='11000101').first()
                            if not plan_cuenta_debe:
                                return JsonResponse({'success': False, 'message': 'No se encontró el plan de cuenta con código 11000101 para Caja.'}, status=400)
                        else:
                            # Asegúrate de que 'idPlanCuentaDebe' se envíe en el POST cuando la forma de pago no es EFECTIVO
                            plan_cuenta_debe_id = request.POST.get('idPlanCuentaDebe')
                            if not plan_cuenta_debe_id:
                                return JsonResponse({'success': False, 'message': 'Debe seleccionar una cuenta bancaria para esta forma de pago.'}, status=400)
                            plan_cuenta_debe = PlanCuenta.objects.get(pk=plan_cuenta_debe_id)

                        # ==================================================================
                        # ### INICIO DE LA LÓGICA CONTABLE CORREGIDA ###
                        # ==================================================================

                        # 1. Definir la tolerancia para el ajuste por redondeo.
                        TOLERANCIA_REDONDEO = Decimal('0.05')  # Puedes ajustar este valor según tus políticas

                        # 2. Calcular la diferencia. Si es positiva, es un saldo pendiente.
                        diferencia_final = saldo_nota - monto_pago_convertido
                        print(f"Diferencia final calculada: {diferencia_final} (Saldo: {saldo_nota} - Pago: {monto_pago_convertido})")

                        # 3. Determinar el tipo de pago para crear el asiento correcto.
                        es_pago_final_con_ajuste = Decimal('0.0') < diferencia_final <= TOLERANCIA_REDONDEO
                        es_pago_final_exacto = es_cero_con_tolerancia(diferencia_final)
                        es_pago_parcial = diferencia_final > TOLERANCIA_REDONDEO

                        DetalleAsiento.objects.filter(idAsiento=asiento_pago).delete()

                        if es_pago_final_con_ajuste:
                            # --- CASO 1: PAGO FINAL CON AJUSTE POR REDONDEO (Asiento Compuesto de 3 líneas) ---
                            print(f"AJUSTE: La diferencia {diferencia_final} está dentro de la tolerancia. Se considera pago final.")

                            # ¡IMPORTANTE! Debes crear esta cuenta en tu plan de cuentas y usar el código correcto aquí.
                            cuenta_ajuste_gasto = PlanCuenta.objects.filter(codigoPlanCuenta='52000104').first()
                            if not cuenta_ajuste_gasto:
                                raise ValueError("No se encontró la cuenta contable para 'GASTOS POR REDONDEO DE CONVERSIÓN MONETARIA' (COD: 52000104).")

                            # Detalle 1: Ingreso a Caja/Banco (DEBE)
                            DetalleAsiento.objects.create(idAsiento=asiento_pago, idMoneda=moneda_pago, idPlanCuenta=plan_cuenta_debe, debe=float(monto_pago_convertido), haber=0.00)
                            # Detalle 2: Pérdida por Redondeo (DEBE) - ¡ESTA ES LA CORRECCIÓN CLAVE!
                            DetalleAsiento.objects.create(idAsiento=asiento_pago, idMoneda=moneda_pago, idPlanCuenta=cuenta_ajuste_gasto, debe=float(diferencia_final), haber=0.00)
                            # Detalle 3: Cancelación total de la Cuenta por Cobrar (HABER)
                            DetalleAsiento.objects.create(idAsiento=asiento_pago, idMoneda=moneda_pago, idPlanCuenta=plan_cuenta_haber, debe=0.00, haber=float(saldo_nota))

                            print(f"Asiento compuesto cuadrado. Total Debe: {monto_pago_convertido + diferencia_final}, Total Haber: {saldo_nota}")
                            
                            # ✅ CORRECCIÓN: Como es un pago de IGTF, siempre marcamos el estado IGTF como PAGADO
                            pago.idNota.estadoIGTF = 'PAGADO'
                            pago.idNota.estado = 'PAGADO'  # También podemos marcar la nota principal como pagada si corresponde
                            print("Nota marcada como PAGADO (IGTF completamente pagado)")

                        elif es_pago_final_exacto:
                            # --- CASO 2: PAGO FINAL EXACTO (Asiento Simple de 2 líneas) ---
                            print("PAGO EXACTO: La nota se considera saldada.")

                            # Detalle 1: Ingreso a Caja/Banco (DEBE)
                            DetalleAsiento.objects.create(idAsiento=asiento_pago, idMoneda=moneda_pago, idPlanCuenta=plan_cuenta_debe, debe=float(monto_pago_convertido), haber=0.00)
                            # Detalle 2: Cancelación de la Cuenta por Cobrar (HABER)
                            DetalleAsiento.objects.create(idAsiento=asiento_pago, idMoneda=moneda_pago, idPlanCuenta=plan_cuenta_haber, debe=0.00, haber=float(monto_pago_convertido))

                            # ✅ CORRECCIÓN: Como es un pago de IGTF, siempre marcamos el estado IGTF como PAGADO
                            pago.idNota.estadoIGTF = 'PAGADO'
                            pago.idNota.estado = 'PAGADO'
                            print("Nota marcada como PAGADO (IGTF completamente pagado)")

                        elif es_pago_parcial:
                            # --- CASO 3: PAGO PARCIAL (Asiento Simple de 2 líneas) ---
                            print("PAGO PARCIAL: Aún queda saldo pendiente.")

                            # Detalle 1: Ingreso a Caja/Banco (DEBE)
                            DetalleAsiento.objects.create(idAsiento=asiento_pago, idMoneda=moneda_pago, idPlanCuenta=plan_cuenta_debe, debe=float(monto_pago_convertido), haber=0.00)
                            # Detalle 2: Abono a la Cuenta por Cobrar (HABER)
                            DetalleAsiento.objects.create(idAsiento=asiento_pago, idMoneda=moneda_pago, idPlanCuenta=plan_cuenta_haber, debe=0.00, haber=float(monto_pago_convertido))

                            # ✅ CORRECCIÓN: Para pagos parciales de IGTF, mantenemos el estado como PENDIENTE
                            pago.idNota.estadoIGTF = 'PARCIAL'

                        else:
                            # Caso de sobrepago (diferencia_final es negativa), que la validación inicial debería prevenir.
                            return JsonResponse({'success': False, 'message': f'Error: El monto del pago {monto_pago_convertido} excede el saldo de la deuda {saldo_nota}.'}, status=400)

                        # ==================================================================
                        # ### FIN DE LA LÓGICA CONTABLE CORREGIDA ###
                        # ==================================================================

                        # Asociar el asiento contable al pago y guardar cambios
                        pago.idAsiento = asiento_pago
                        pago.save()
                        pago.idNota.save() # Guardar el nuevo estado de la nota

                        # --- LÓGICA POST-PAGO ---
                        # Ahora, basado en el estado final de la nota, ejecutamos las acciones correspondientes.

                        if pago.idNota.estadoIGTF == 'PARCIAL':
                            return JsonResponse({
                                'success': True,
                                'message': f'El pago de IGTF fue exitoso, pero queda saldo pendiente. ¿Desea realizar otro pago adicional?',
                                'redirect_url': f"{reverse('pago_createigtf')}?nota={pago.idNota.idNota}",
                                'pago': {
                                    'idPago': pago.idPago,
                                    'idNota': pago.idNota.numeroNota,
                                    'monto': f"{float(monto_pago_decimal):.2f} {pago.idTasa.idMoneda.simboloMoneda}",
                                    'fechaPago': pago.fechaPago.strftime('%d/%m/%Y'),
                                    'formaPago': pago.formaPago,
                                    'referencia': pago.referencia,
                                    'estado_igtf': pago.idNota.estadoIGTF
                                }
                            })
                        
                        elif pago.idNota.estado == 'PAGADO' or pago.idNota.estadoIGTF == 'PAGADO':
                            return JsonResponse({
                                'success': True,
                                'message': 'Pago de IGTF creado exitosamente. El IGTF ha sido pagado en su totalidad.',
                                'redirect_url': reverse('nota_list'),
                                'pago': {
                                    'idPago': pago.idPago,
                                    'idNota': pago.idNota.numeroNota,
                                    'monto': f"{float(monto_pago_decimal):.2f} {pago.idTasa.idMoneda.simboloMoneda}",
                                    'fechaPago': pago.fechaPago.strftime('%d/%m/%Y'),
                                    'formaPago': pago.formaPago,
                                    'referencia': pago.referencia,
                                    'estado_igtf': pago.idNota.estadoIGTF
                                }
                            })

                        else:
                            # Caso donde el pago es mayor al saldo (no debería ocurrir por validación previa)
                            return JsonResponse({
                                'success': False,
                                'message': 'Error inesperado en el cálculo del saldo.'
                            }, status=400)
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

    return render(request, 'factura/pago_IGTF.html', {
        'form': form,
        'notas': notas_data, 
        'cuentas_banco': cuentas_banco,
        'cuentas_plan': cuentas_plan,
        'monedas': tasas_activas,
        'notas_json': json.dumps(notas_data, cls=DecimalEncoder) 
    })

def obtener_tipo_igtf(request):
    """
    Vista para obtener el tipo de IGTF basado en la nota, la forma de pago y la moneda/tasa seleccionada.
    CORREGIDA: Ahora busca correctamente en ParametroTributario
    """
    id_nota = request.GET.get('idNota')
    forma_pago = request.GET.get('formaPago')
    id_tasa_param = request.GET.get('idTasa')
    moneda_id_param = request.GET.get('monedaId')
    es_nacional_param = request.GET.get('esNacional')

    print(f"[obtener_tipo_igtf] Parámetros recibidos -> idNota: {id_nota}, formaPago: {forma_pago}, idTasa: {id_tasa_param}, monedaId: {moneda_id_param}, esNacional: {es_nacional_param}")

    if not id_nota or not forma_pago:
        return JsonResponse({'error': 'Faltan parámetros idNota o formaPago'}, status=400)

    try:
        nota = get_object_or_404(Nota, idNota=id_nota)
        print(f"[obtener_tipo_igtf] Nota -> idNota: {nota.idNota}, numeroNota: {nota.numeroNota}, tipoOperacion: {nota.tipoOperacion}")

        # DETERMINAR SI ES NACIONAL O DIVISA
        es_nacional = False
        
        # 1. Prioridad: parámetro esNacional explícito
        if es_nacional_param is not None:
            es_nacional = str(es_nacional_param).strip().lower() in ('1', 'true', 't', 'yes', 'y')
        
        # 2. Parámetro monedaId
        elif moneda_id_param and moneda_id_param.isdigit():
            es_nacional = (int(moneda_id_param) == 1)
        
        # 3. Parámetro idTasa
        elif id_tasa_param and id_tasa_param.isdigit():
            if id_tasa_param == '1':
                es_nacional = True
            else:
                tasa_obj = Tasa.objects.filter(idTasa=id_tasa_param).select_related('idMoneda').first()
                if tasa_obj and tasa_obj.idMoneda:
                    es_nacional = (tasa_obj.idMoneda.idMoneda == 1)
        
        # 4. Fallback a moneda de la nota
        else:
            try:
                if nota.idTasa and nota.idTasa.idMoneda:
                    es_nacional = (nota.idTasa.idMoneda.idMoneda == 1)
            except Exception:
                es_nacional = False

        print(f"[obtener_tipo_igtf] es_nacional determinado: {es_nacional}")

        # DETERMINAR TIPO IGTF
        tipo_operacion = nota.tipoOperacion
        tipo_igtf = None
        
        if tipo_operacion == 'COBRO':
            if forma_pago == 'EFECTIVO':
                tipo_igtf = 'IGTF_NACIONAL_VENTAS_EFECTIVO' if es_nacional else 'IGTF_DIVISA_VENTAS_EFECTIVO'
            else:
                tipo_igtf = 'IGTF_NACIONAL_VENTAS_DIGITAL' if es_nacional else 'IGTF_DIVISA_VENTAS_DIGITAL'
        elif tipo_operacion == 'PAGO':
            if forma_pago == 'EFECTIVO':
                tipo_igtf = 'IGTF_NACIONAL_COMPRAS_EFECTIVO' if es_nacional else 'IGTF_DIVISA_COMPRAS_EFECTIVO'
            else:
                tipo_igtf = 'IGTF_NACIONAL_COMPRAS_DIGITAL' if es_nacional else 'IGTF_DIVISA_COMPRAS_DIGITAL'
        else:
            return JsonResponse({'error': 'Tipo de operación desconocido'}, status=400)

        print(f"[obtener_tipo_igtf] Tipo IGTF determinado: {tipo_igtf}")

        # BUSCAR PARÁMETRO TRIBUTARIO - CORRECCIÓN CLAVE
        parametro = ParametroTributario.objects.filter(tipo=tipo_igtf, activo=True).first()
        
        if parametro:
            porcentaje = float(parametro.porcentaje)
            print(f"[obtener_tipo_igtf] Parámetro encontrado: {parametro.tipo}, porcentaje: {porcentaje}%")
        else:
            porcentaje = 0.0
            print(f"[obtener_tipo_igtf] NO se encontró parámetro activo para: {tipo_igtf}")

        # Información de debug adicional
        print(f"[obtener_tipo_igtf] Parámetros buscados en DB: tipo={tipo_igtf}, activo=True")
        print(f"[obtener_tipo_igtf] Todos los parámetros activos:")
        for p in ParametroTributario.objects.filter(activo=True):
            print(f"  - {p.tipo}: {p.porcentaje}%")

        return JsonResponse({
            'tipoIGTF': tipo_igtf,
            'porcentaje': porcentaje,
            'esNacional': es_nacional,
            'monedaId': moneda_id_param
        })

    except Exception as e:
        print(f"[obtener_tipo_igtf] Error inesperado: {e}")
        import traceback
        print(traceback.format_exc())
        return JsonResponse({'error': 'Error interno del servidor'}, status=500)

@transaction.atomic
def pago_edit(request, pk):
    """
    Vista para editar un pago existente.
    """
    pago = get_object_or_404(Pago, pk=pk)
    
    # Obtener datos necesarios para el contexto
    cuentas_banco = CuentaBanco.objects.filter(estado=True)
    tasas = Tasa.objects.select_related('idMoneda').values('idTasa', 'idMoneda__nombreMoneda', 'montoTasa')
    cuentas_plan = PlanCuenta.objects.filter(estadoPlanCuenta=True)
    today_date = datetime.now().strftime('%Y-%m-%d')

    if request.method == 'POST':
        # Usar el formulario pero no permitir cambios en campos críticos
        form = PagoForm(request.POST, instance=pago)
        if form.is_valid():
            try:
                # Solo permitir actualizar campos editables
                pago_actualizado = form.save(commit=False)
                
                # Mantener los campos críticos sin cambios (por seguridad)
                pago_actualizado.idNota = pago.idNota
                pago_actualizado.idTasa = pago.idTasa
                pago_actualizado.monto = pago.monto
                pago_actualizado.formaPago = pago.formaPago
                pago_actualizado.fechaPago = pago.fechaPago
                
                # Solo actualizar campos permitidos
                if pago.formaPago != 'EFECTIVO':
                    pago_actualizado.idCuentaBanco = form.cleaned_data.get('idCuentaBanco')
                    # Buscar el plan de cuenta asociado a la cuenta bancaria
                    if pago_actualizado.idCuentaBanco and pago_actualizado.idCuentaBanco.planCuenta:
                        pago_actualizado.idPlanCuentaDebe = pago_actualizado.idCuentaBanco.planCuenta
                    pago_actualizado.referencia = form.cleaned_data.get('referencia', '')
                else:
                    pago_actualizado.idCuentaBanco = None
                    pago_actualizado.idPlanCuentaDebe = None
                    pago_actualizado.referencia = ''
                
                pago_actualizado.observaciones = form.cleaned_data.get('observaciones', '')
                
                pago_actualizado.save()
                
                return JsonResponse({
                    'success': True,
                    'message': 'Pago actualizado exitosamente.',
                    'redirect_url': reverse('pago_list')
                })
                
            except Exception as e:
                return JsonResponse({
                    'success': False,
                    'message': f'Error al actualizar el pago: {str(e)}'
                }, status=500)
        else:
            return JsonResponse({
                'success': False,
                'message': 'Errores en el formulario.',
                'errors': form.errors
            }, status=400)
    else:
        # Inicializar el formulario con los datos existentes
        form = PagoForm(instance=pago)

    return render(request, 'factura/pago_edit.html', {
        'form': form,
        'pago': pago,
        'cuentas_banco': cuentas_banco,
        'tasas': tasas,
        'cuentas_plan': cuentas_plan,
        'today_date': today_date,
    })

@transaction.atomic
def pago_delete(request, pk):
    """
    Vista para eliminar un pago existente.
    """
    pago = get_object_or_404(Pago, pk=pk)
    pago.delete()
    return redirect('pago_list')

########PAGOS POR CONFIRMAR DE LA APP###########################


def pagoApp_list(request):
    """
    Lista todos los pagos temporales con buscador y paginación.
    Agrega mensajes de depuración para mostrar qué recibe, cómo se purifica/compara y dónde se encontró la coincidencia.
    """
    query = request.GET.get('search', '')  # Obtener el término de búsqueda desde los parámetros GET

    # Mensaje de purificación: limpiar caracteres no deseados y mostrar ambos valores
    q_raw = query or ""
    q_clean = re.sub(r'[^\w\s\-\.,]', '', q_raw).strip()  # Purificar la entrada (permite letras, números, espacios, guión, punto y coma)
    q_clean_lower = q_clean.lower()
    print(f"[pagoApp_list] query_raw='{q_raw}' | query_clean='{q_clean}'")

    pagos_temporales_list = PagoTemporal.objects.all().order_by('-fechaPago')  # Consulta base

    # Aplicar filtros de búsqueda si hay un término
    if q_clean:
        print("[pagoApp_list] Aplicando filtro Q() sobre campos: idPagoTemporal, idNota.numeroNota, monto, referencia, observaciones, idCuentaBanco.nombreCuenta")
        pagos_temporales_list = pagos_temporales_list.filter(
            Q(idPagoTemporal__icontains=q_clean) |
            Q(idNota__numeroNota__icontains=q_clean) |
            Q(monto__icontains=q_clean) |
            Q(referencia__icontains=q_clean) |
            Q(observaciones__icontains=q_clean)
        )
    else:
        print("[pagoApp_list] No se aplicó filtro: término de búsqueda vacío tras purificación.")

    # Construir información de coincidencias por registro para depuración detallada
    matches_info = []
    if q_clean:
        for pago in pagos_temporales_list:
            matched_fields = []
            # Campos a comparar (obtenidos de forma segura)
            checks = [
                ('idPagoTemporal', getattr(pago, 'idPagoTemporal', getattr(pago, 'pk', None))),
                ('idNota.numeroNota', getattr(getattr(pago, 'idNota', None), 'numeroNota', None)),
                ('monto', getattr(pago, 'monto', None)),
                ('referencia', getattr(pago, 'referencia', None)),
                ('observaciones', getattr(pago, 'observaciones', None)),
                ('idCuentaBanco.nombreCuenta', getattr(getattr(pago, 'idCuentaBanco', None), 'nombreCuenta', None)),
            ]
            for fname, fval in checks:
                if fval is None:
                    continue
                s = str(fval)
                # comparar en minúsculas para simular icontains
                if q_clean_lower in s.lower():
                    matched_fields.append({'field': fname, 'value': s})
                    print(f"[pagoApp_list] Coincidencia encontrada -> Pago id={getattr(pago, 'idPagoTemporal', getattr(pago, 'pk', None))}: campo='{fname}' valor='{s}' contiene '{q_clean}'")
            if matched_fields:
                matches_info.append({
                    'pago_id': getattr(pago, 'idPagoTemporal', getattr(pago, 'pk', None)),
                    'matches': matched_fields
                })

        print(f"[pagoApp_list] Total registros que cumplen filtro: {pagos_temporales_list.count()}; detalles de coincidencias recopilados: {len(matches_info)}")
    else:
        print("[pagoApp_list] No hay término de búsqueda purificado; no se generaron detalles de coincidencias.")

    # Paginación
    page = request.GET.get('page', 1)  # Obtener el número de página desde los parámetros GET
    paginator = Paginator(pagos_temporales_list, 10)  # Mostrar 10 registros por página

    try:
        pagos_temporales = paginator.page(page)
    except PageNotAnInteger:
        pagos_temporales = paginator.page(1)  # Si el parámetro `page` no es un entero, mostrar la primera página
    except EmptyPage:
        pagos_temporales = paginator.page(paginator.num_pages)  # Si el número de página está fuera de rango, mostrar la última página

    return render(request, 'factura/tablaPagosApp.html', {
        'pagos_temporales': pagos_temporales,
        'query': query,  # Pasar el término de búsqueda al contexto para mantenerlo en el formulario
        'matches_info': matches_info  # Información de coincidencias para depuración en frontend si se desea mostrar
    })

@transaction.atomic
def pago_confirmar(request, pk):
    """
    Confirma un pago temporal y lo mueve a la tabla principal de pagos.
    Responde siempre en JSON.
    """
    pago_temporal = get_object_or_404(PagoTemporal, pk=pk)

    if pago_temporal.confirmado:
        return JsonResponse({
            'success': False,
            'message': "El pago ya ha sido confirmado."
        }, status=400)

    try:
        pago_temporal.confirmar_pago()
        return JsonResponse({
            'success': True,
            'message': "El pago ha sido confirmado exitosamente.",
            'redirect_url': reverse('pago_App_list')
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f"Error al confirmar el pago: {str(e)}"
        }, status=500)

@transaction.atomic
def pago_cancelar(request, pk):
    """
    Cancela (elimina) un pago temporal y responde en JSON.
    """
    pago_temporal = get_object_or_404(PagoTemporal, pk=pk)
    if pago_temporal.confirmado:
        return JsonResponse({
            'success': False,
            'message': "No se puede cancelar un pago ya confirmado."
        }, status=400)

    try:
        pago_temporal.delete()
        return JsonResponse({
            'success': True,
            'message': "El pago temporal ha sido cancelado exitosamente.",
            'redirect_url': reverse('pago_App_list')
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f"Error al cancelar el pago temporal: {str(e)}"
        }, status=500)

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

def nota_pago_pdf(request, pk):
    nota = get_object_or_404(Nota, pk=pk)
    detalles = FacturaDetalle.objects.filter(idNota=nota)
    config = Configuracion.objects.order_by('-fechaConfiguracion').first()

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="nota_pago_{nota.numeroNota}.pdf"'
    p = canvas.Canvas(response, pagesize=letter)
    p.setTitle("Reporte de nota de Pago")
    width, height = letter

    # --- Encabezado institucional ---
    y = height - 40
    p.setFont("Helvetica-Bold", 14)
    p.drawCentredString(width / 2, y, config.nombreInstitucion if config else "NOMBRE DE LA FUNDACIÓN")
    y -= 18
    p.setFont("Helvetica", 11)
    p.drawCentredString(width / 2, y, f"RIF: {config.rif if config else 'J-XXXXXXXX-X'}")
    y -= 16
    p.setFont("Helvetica", 10)
    p.drawCentredString(width / 2, y, "Dirección Fiscal:")
    y -= 14
    p.drawCentredString(width / 2, y, "AV. ALBERTO RAVELL CON AV. INTERCOMUNAL")
    y -= 14
    p.drawCentredString(width / 2, y, "JOSE ANTONIO PAEZ, LOCAL UPTYAB,")
    y -= 14
    p.drawCentredString(width / 2, y, "INDEPENDENCIA – EDO YARACUY")
    y -= 20
    p.line(30, y, width - 30, y)
    y -= 20

    # --- Datos de la factura/nota ---
    p.setFont("Helvetica-Bold", 11)
    p.drawString(40, y, f"N°: {nota.numeroNota}")
    y -= 16
    p.setFont("Helvetica", 10)
    p.drawString(40, y, f"Fecha de Emisión: {nota.fechaEmision.strftime('%d/%m/%Y')}")
    y -= 16
    # Determinar el cliente y sus datos correctamente
    if nota.idPersona:
        nombre_cliente = nota.idPersona.nombreCompleto if hasattr(nota.idPersona, 'nombreCompleto') else str(nota.idPersona)
        rif_cliente = nota.idPersona.cedula if hasattr(nota.idPersona, 'cedula') else ''
        direccion_cliente = nota.idPersona.direccion if hasattr(nota.idPersona, 'direccion') else ''
    elif nota.idEmpresa:
        nombre_cliente = nota.idEmpresa.nombreEmpresa if hasattr(nota.idEmpresa, 'nombreEmpresa') else str(nota.idEmpresa)
        rif_cliente = nota.idEmpresa.rif if hasattr(nota.idEmpresa, 'rif') else ''
        direccion_cliente = nota.idEmpresa.direccionEmpresa if hasattr(nota.idEmpresa, 'direccionEmpresa') else ''
    else:
        nombre_cliente = ''
        rif_cliente = ''
        direccion_cliente = ''

    p.drawString(40, y, f"Cliente: {nombre_cliente}")
    y -= 16
    p.drawString(40, y, f"RIF/Cédula: {rif_cliente}")
    y -= 16
    p.drawString(40, y, f"Dirección: {direccion_cliente}")
    y -= 20
    p.line(30, y, width - 30, y)
    y -= 20

    # --- Tabla de detalles ---
    p.setFont("Helvetica-Bold", 10)
    p.drawString(40, y, "Descripción")
    p.drawString(260, y, "Cantidad")
    p.drawString(330, y, "Precio Unitario")
    p.drawString(430, y, "Subtotal Exento")
    y -= 10
    p.line(30, y, width - 30, y)
    y -= 18
    p.setFont("Helvetica", 10)
    # Descripción principal
    p.drawString(40, y, nota.tipoOperacion[:40])
    y -= 14
    # Tipo de artículo debajo de la descripción
    p.setFont("Helvetica-Oblique", 9)

    tipo_articulo_display = dict(TIPOS_ARTICULO).get(nota.tipoArticulo, nota.tipoArticulo)    # Mostrar el tipo de artículo, haciendo salto de línea si es mayor de 30 caracteres
    if len(tipo_articulo_display) > 50:
        # Dividir el texto en partes de máximo 30 caracteres
        for i in range(0, len(tipo_articulo_display), 30):
            p.drawString(50, y, tipo_articulo_display[i:i+30])
            y -= 12  # Ajusta el salto de línea para cada parte
    else:
        p.drawString(50, y, tipo_articulo_display)
        y -= 12
    p.setFont("Helvetica", 10)
    # Cantidad, precio unitario y subtotal exento
    # Mostrar la cantidad como 1 por cada objeto relacionado en NotaRelacionada
    cantidad = 0
    nota_relacionadas = NotaRelacionada.objects.filter(idNota=nota)
    if nota_relacionadas.exists():
        # Si hay relaciones, cuenta cada una como cantidad 1
        cantidad = nota_relacionadas.count()
    else:
        # Si no hay relaciones, por defecto 1
        cantidad = 1
    p.drawRightString(295, 485, f"{cantidad:.2f}")
    # Obtener el símbolo de la moneda desde la configuración
    simbolo_moneda = config.moneda.simboloMoneda if config and hasattr(config, 'moneda') and hasattr(config.moneda, 'simboloMoneda') else ""
    p.drawRightString(385, 485, f"{nota.totalNota:.2f} {simbolo_moneda}")
    p.drawRightString(485, 485, f"{nota.subtotalExento:.2f}")
    y -= 18
    if y < 120:
        p.showPage()
        y = height - 80
    p.line(30, y, width - 30, y)
    y -= 20

    # --- Totales y resumen ---
    p.setFont("Helvetica", 10)
    p.drawRightString(510, y, f"Subtotal Exento:      {nota.subtotalExento:.2f}")
    y -= 16
    p.drawRightString(510, y, f"Subtotal Gravado:     {nota.subtotalGravado:.2f}")
    y -= 16
    p.drawRightString(510, y, f"IVA (16%):            {nota.iva:.2f}")
    y -= 16
    p.drawRightString(510, y, f"IVA Retenido (75%):   {nota.ivaRetenido if nota.ivaRetenido else 0:.2f}")
    y -= 16
    p.drawRightString(510, y, f"ISLR Retenido (3%):   {nota.islrRetenido if nota.islrRetenido else 0:.2f}")
    y -= 16
    p.drawRightString(510, y, f"Descuento:            {nota.descuento:.2f}")
    y -= 16
    p.line(250, y, width - 30, y)
    y -= 18
    p.setFont("Helvetica-Bold", 11)
    simbolo_moneda = config.moneda.simboloMoneda if config and hasattr(config, 'moneda') and hasattr(config.moneda, 'simboloMoneda') else ""
    p.drawRightString(510, y, f"TOTAL:                {nota.totalNota:.2f} {simbolo_moneda}")
    y -= 20
    p.line(30, y, width - 30, y)
    y -= 20

    # --- Forma de pago ---
    p.setFont("Helvetica", 10)
    p.drawString(40, y, f"Forma de Pago: {nota.formaPago}")
    y -= 20
    p.line(30, y, width - 30, y)
    y -= 40

    # --- Firma autorizada ---
    p.setFont("Helvetica-Bold", 11)
    p.drawCentredString(width / 2, y, f"FIRMA AUTORIZADA: ")
    y -= 20
    p.line(30, y, width - 30, y)

    p.showPage()
    p.save()
    return response
def reporte_facturas_pdf(request):
    # Selección de cantidad de registros
    start = int(request.GET.get('start', 1))
    end = int(request.GET.get('end', 0))
    facturas = list(Factura.objects.all().order_by('fechaEmision', 'numeroFactura'))
    if end == 0 or end > len(facturas):
        end = len(facturas)
    facturas = facturas[start-1:end]

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="reporte_facturas.pdf"'

    # Para aumentar el tamaño de la hoja, define un tamaño personalizado (por ejemplo, más grande que letter)
    custom_width = 14 * inch  # ancho personalizado (por ejemplo, 14 pulgadas)
    custom_height = 9 * inch  # alto personalizado (por ejemplo, 9 pulgadas)
    page_size = (custom_width, custom_height)

    # Aquí se pone la hoja en horizontal usando landscape y el tamaño personalizado
    p = canvas.Canvas(response, pagesize=landscape(page_size))
    p.setTitle("Reporte de Facturas")
    width, height = landscape(page_size)
    logo_width, logo_height, logo_margin = 100, 100, 15

    # Configuración institucional
    config = Configuracion.objects.order_by('-fechaConfiguracion').first()
    logo_path = config.logo.path if config and config.logo else None
    firma_path = config.firma.path if config and config.firma else None
    nombre_institucion = config.nombreInstitucion if config else "Institución"
    rif_institucion = config.rif if config else ""
    direccion1 = "AV. ALBERTO RAVELL CON AV. INTERCOMUNAL JOSE ANTONIO PAEZ"
    direccion2 = "LOCAL UPTYAB, INDEPENDENCIA – EDO YARACUY"

    safe_left = logo_margin
    safe_right = width - logo_margin
    safe_width = safe_right - safe_left
    safe_center = width / 2

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
        p.drawString(logo_margin, text_top - 15, f"RIF: {rif_institucion}")
        p.drawString(logo_margin, text_top - 30, direccion1)
        p.drawString(logo_margin, text_top - 45, direccion2)
        p.setFont("Helvetica-Bold", 13)
        p.drawCentredString(width / 2, text_top - 85, "Reporte de Facturas")

    def draw_footer():
        if firma_path and os.path.exists(firma_path):
            p.drawImage(firma_path, width/2 - 60, 60, width=120, height=60, preserveAspectRatio=True, mask='auto')
            p.setFont("Helvetica-Oblique", 10)
            p.drawCentredString(width/2, 40, "Firma autorizada")
        
        p.setFont("Helvetica", 8)
        fecha_generacion = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        p.drawString(logo_margin, 20, f"Generado el: {fecha_generacion}")

    # --- Datos de la tabla ---
    data = [
        [
            "N° Factura",
            "Fecha",
            "Cliente",
            "Empresa",
            "Total",
            "Estado"
        ]
    ]
    for fac in facturas:
        data.append([
            fac.numeroFactura,
            fac.fechaEmision.strftime("%d/%m/%Y"),
            str(fac.idPersona) if fac.idPersona else 'N/A',
            fac.idEmpresa.nombreEmpresa if fac.idEmpresa else 'N/A',
            f"{fac.totalVenta:.2f}",
            fac.estado
        ])
    
    # Colores para estados
    estado_colores = {
        'Generada': colors.HexColor("#2dce89"),
        'Pagada': colors.HexColor("#11cdef"),
        'Eliminada': colors.HexColor("#f5365c"),
        'Pendiente': colors.HexColor("#fb6340")
    }

    col_widths = [120, 80, 120, 120, 70, 70]
    table_width = sum(col_widths)

    # --- Cálculo de espacio ---
    header_height = 140
    footer_height = 100
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
        
        # Estilo de la tabla
        table_style = TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#5e72e4")),
            ('TEXTCOLOR', (0,0), (-1,0), colors.white),
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('FONTSIZE', (0,0), (-1,0), 10),
            ('BOTTOMPADDING', (0,0), (-1,0), 8),
            ('BACKGROUND', (0,1), (-1,-1), colors.whitesmoke),
            ('GRID', (0,0), (-1,-1), 0.5, colors.lightgrey),
            ('FONTSIZE', (0,1), (-1,-1), 9),
            ('ALIGN', (4,1), (4,-1), 'RIGHT'),
        ])
        
        # Aplicar colores a los estados
        for i in range(1, len(page_data)):
            estado = page_data[i][5]
            if estado in estado_colores:
                table_style.add('TEXTCOLOR', (5,i), (5,i), estado_colores[estado])
        
        table.setStyle(table_style)
        table.wrapOn(p, width, height)
        table.drawOn(p, table_x, y - row_height * len(page_data))
        
        # Información de paginación
        p.setFont("Helvetica", 8)
        p.drawCentredString(
            safe_center, 
            y - row_height * len(page_data) - 20,
            f"Página {page + 1} - Registros {start_row + 1} a {end_row} de {total_rows}"
        )
        
        draw_footer()
        page += 1

    p.save()
    return response

def factura_generar_pdf(request, pk):
    factura = get_object_or_404(Factura, pk=pk)
    nota = factura.nota
    detalles = FacturaDetalle.objects.filter(idFactura=factura)
    pagos = Pago.objects.filter(idNota=nota).order_by('fechaPago')
    config = Configuracion.objects.order_by('-fechaConfiguracion').first()

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="factura_{factura.numeroFactura}.pdf"'
    p = canvas.Canvas(response, pagesize=letter)
    p.setTitle("Reporte de Factura Individual")
    width, height = letter
    logo_width, logo_height, logo_margin = 80, 80, 15

    # --- Encabezado institucional ---
    y = height - 40
    p.setFont("Helvetica-Bold", 14)
    p.drawCentredString(width / 2, y, config.nombreInstitucion if config else "NOMBRE DE LA FUNDACIÓN")
    y -= 18
    p.setFont("Helvetica", 11)
    p.drawCentredString(width / 2, y, f"RIF: {config.rif if config else 'J-XXXXXXXX-X'}")
    y -= 16
    p.setFont("Helvetica", 10)
    p.drawCentredString(width / 2, y, "Dirección Fiscal:")
    y -= 14
    p.drawCentredString(width / 2, y, "AV. ALBERTO RAVELL CON AV. INTERCOMUNAL")
    y -= 14
    p.drawCentredString(width / 2, y, "JOSE ANTONIO PAEZ, LOCAL UPTYAB,")
    y -= 14
    p.drawCentredString(width / 2, y, "INDEPENDENCIA – EDO YARACUY")
    y -= 20
    p.line(30, y, width - 30, y)
    y -= 20

    # --- Datos de la factura ---
    p.setFont("Helvetica-Bold", 11)
    p.drawString(40, y, f"Factura N°: {factura.numeroFactura}")
    y -= 16
    p.setFont("Helvetica", 10)
    p.drawString(40, y, f"Fecha de Emisión: {factura.fechaEmision.strftime('%d/%m/%Y')}")
    y -= 16
    
    nombre_cliente = "N/A"
    rif_cliente = "N/A"
    direccion_cliente = "N/A"

    # Obtener información del cliente 
    if hasattr(nota, 'idPersona') and nota.idPersona:
        nombre_cliente = getattr(nota.idPersona, 'nombreCompleto', 
                                f"{getattr(nota.idPersona, 'nombres', '')} {getattr(nota.idPersona, 'apellidos', '')}".strip())
        rif_cliente = getattr(nota.idPersona, 'cedula', 'N/A')
        direccion_cliente = getattr(nota.idPersona, 'direccion', 'N/A')
    # Si no hay persona, intentar obtener información de la empresa
    elif hasattr(nota, 'idEmpresa') and nota.idEmpresa:
        nombre_cliente = getattr(nota.idEmpresa, 'nombreEmpresa', 'N/A')
        rif_cliente = getattr(nota.idEmpresa, 'rif', 'N/A')
        direccion_cliente = getattr(nota.idEmpresa, 'direccionEmpresa', 'N/A')
    p.drawString(40, y, f"Cliente: {nombre_cliente}")
    y -= 16
    p.drawString(40, y, f"RIF/Cédula: {rif_cliente}")
    y -= 16
    p.drawString(40, y, f"Dirección: {direccion_cliente}")
    y -= 20
    p.line(30, y, width - 30, y)
    y -= 20

    # --- Tabla de detalles de la factura ---
    p.setFont("Helvetica-Bold", 10)
    p.drawString(40, y, "Descripción")
    p.drawString(260, y, "Cantidad")
    p.drawString(330, y, "Precio Unitario")
    p.drawString(430, y, "Subtotal Exento")
    y -= 10
    p.line(30, y, width - 30, y)
    y -= 18
    p.setFont("Helvetica", 10)
    # Obtener el símbolo de la moneda desde la configuración
    moneda_simbolo = config.moneda.simboloMoneda if config and hasattr(config, 'moneda') and hasattr(config.moneda, 'simboloMoneda') else ""

    for det in detalles:
        p.drawString(40, y, det.descripcion[:40])
        y -= 14
        p.setFont("Helvetica-Oblique", 9)
        p.drawString(50, y, f"Artículo: {det.tipoItem}")
        p.setFont("Helvetica", 10)
        p.drawRightString(300, y, f"{det.cantidad:.2f}")
        p.drawRightString(400, y, f"{det.precioUnitario:.2f} {moneda_simbolo}")
        p.drawRightString(510, y, f"{det.subtotal:.2f} {moneda_simbolo}")
        y -= 18
        if y < 120:
            p.showPage()
            y = height - 80
    p.line(30, y, width - 30, y)
    y -= 20

    # --- Totales y resumen ---
    p.setFont("Helvetica", 10)
    p.drawRightString(510, y, f"Subtotal Exento:      {factura.subtotalExento:.2f} {moneda_simbolo}")
    y -= 16
    p.drawRightString(510, y, f"Subtotal Gravado:     {factura.subtotalGravado:.2f} {moneda_simbolo}")
    y -= 16
    p.drawRightString(510, y, f"IVA (16%):            {factura.iva:.2f} {moneda_simbolo}")
    y -= 16
    p.drawRightString(510, y, f"IVA Retenido (75%):   {factura.ivaRetenido if factura.ivaRetenido else 0:.2f} {moneda_simbolo}")
    y -= 16
    p.drawRightString(510, y, f"ISLR Retenido (3%):   {factura.islrRetenido if factura.islrRetenido else 0:.2f} {moneda_simbolo}")
    y -= 16
    p.drawRightString(510, y, f"Descuento:            {factura.descuento:.2f} {moneda_simbolo}")
    y -= 16
    p.line(250, y, width - 30, y)
    y -= 18
    p.setFont("Helvetica-Bold", 11)
    p.drawRightString(510, y - 8, f"TOTAL:                {factura.totalVenta:.2f} {moneda_simbolo}")
    y -= 16

    # --- CORRECCIÓN: USAR LA TASA DE LA NOTA PARA CONVERSIÓN A BOLÍVARES ---
    # Usar la tasa histórica de la nota (no buscar tasas activas)
    tasa_nota = nota.idTasa
    if tasa_nota and tasa_nota.idMoneda.idMoneda != 1:  # Si no es bolívares
        # Buscar tasa de bolívares en la fecha de emisión de la nota
        tasa_bolivares = Tasa.objects.filter(
            idMoneda__idMoneda=1,
            fechaTasa__lte=nota.fechaEmision
        ).order_by('-fechaTasa').first()
        
        if tasa_bolivares and to_decimal(tasa_bolivares.montoTasa) > Decimal('0'):
            # Calcular total en bolívares usando la tasa histórica de la nota
            total_bolivares = (factura.totalVenta * to_decimal(tasa_nota.montoTasa)) / to_decimal(tasa_bolivares.montoTasa)
            p.drawRightString(510, y -12, f"TOTAL EN Bs:          {total_bolivares:.2f} Bs")
            p.setFont("Helvetica-Oblique", 7.5)
            p.drawString(40, y - 12, f"(**) Usando tasa histórica de la nota: {tasa_nota.idMoneda.nombreMoneda} = {to_decimal(tasa_nota.montoTasa):.2f} Bs (fecha: {tasa_nota.fechaTasa.strftime('%d/%m/%Y')})")
            p.setFont("Helvetica", 10)
            y -= 16
    else:
        # Si ya está en bolívares, mostrar el mismo monto
        p.drawRightString(510, y - 14, f"TOTAL EN Bs:          {factura.totalVenta:.2f} Bs")
        y -= 16

    # --- CALCULAR TOTAL EN BOLÍVARES DE TODOS LOS PAGOS USANDO SUS TASAS HISTÓRICAS ---
    total_pagado_bs = Decimal('0.00')
    if pagos.exists():
        for pago in pagos:
            # USAR LA TASA HISTÓRICA DEL PAGO (pago.idTasa) - NO BUSCAR TASAS ACTIVAS
            tasa_pago = pago.idTasa  # Esta es la tasa histórica registrada en el pago
            
            if tasa_pago.idMoneda.idMoneda != 1:  # Si no es bolívares
                # Buscar tasa de bolívares en la fecha del pago
                tasa_bolivares_pago = Tasa.objects.filter(
                    idMoneda__idMoneda=1,
                    fechaTasa__lte=pago.fechaPago
                ).order_by('-fechaTasa').first()
                
                if tasa_bolivares_pago and to_decimal(tasa_bolivares_pago.montoTasa) > Decimal('0'):
                    # Convertir a bolívares usando la tasa histórica del pago
                    monto_pago_bs = (to_decimal(pago.monto) * to_decimal(tasa_pago.montoTasa)) / to_decimal(tasa_bolivares_pago.montoTasa)
                    total_pagado_bs += monto_pago_bs
            else:
                # Si ya es bolívares, sumar directamente
                total_pagado_bs += to_decimal(pago.monto)

        # Mostrar el total acumulado de todos los pagos en bolívares
        p.drawRightString(510, y -18, f"TOTAL PAGADO Bs:      {total_pagado_bs:.2f} Bs")
        p.setFont("Helvetica-Oblique", 7.5)
        p.drawString(40, y - 18, "(*) Incluye la suma de todos los pagos convertidos a Bs según tasa histórica de cada pago")
        p.setFont("Helvetica", 10)
        y -= 20

    y -= 17.5
    p.line(30, y, width - 30, y)
    y -= 17.5

    # --- Pagos realizados - USANDO TASAS HISTÓRICAS DE CADA PAGO ---
    p.setFont("Helvetica-Bold", 10)
    p.drawString(40, y, "Pagos realizados:")
    y -= 16
    p.setFont("Helvetica", 10)
    
    if pagos.exists():
        # Función para dividir texto en múltiples líneas
        def draw_wrapped_text(text, x, y, max_width, line_height=14):
            words = text.split()
            lines = []
            current_line = []
            
            for word in words:
                test_line = current_line + [word]
                test_text = ' '.join(test_line)
                text_width = p.stringWidth(test_text, "Helvetica", 10)
                
                if text_width <= max_width:
                    current_line.append(word)
                else:
                    if current_line:
                        lines.append(' '.join(current_line))
                    current_line = [word]
            
            if current_line:
                lines.append(' '.join(current_line))
            
            # Dibujar todas las líneas
            for line in lines:
                p.drawString(x, y, line)
                y -= line_height
                if y < 80:
                    p.showPage()
                    y = height - 80
                    p.setFont("Helvetica", 10)  # Restaurar fuente después del salto de página
            
            return y

        # Ancho máximo disponible para los textos de pago
        max_text_width = width - 100  # 50px izquierda + 50px derecha
        
        for pago in pagos:
            # CORRECCIÓN: USAR LA TASA HISTÓRICA DEL PAGO (pago.idTasa)
            tasa_pago = pago.idTasa  # Esta es la tasa histórica registrada en el pago
            moneda_simbolo = tasa_pago.idMoneda.simboloMoneda if tasa_pago and tasa_pago.idMoneda else ""
            tasa_pago_valor = to_decimal(tasa_pago.montoTasa) if tasa_pago else Decimal('0')
            fecha_tasa_pago = tasa_pago.fechaTasa.strftime('%d/%m/%Y') if tasa_pago and tasa_pago.fechaTasa else "N/A"

            # Calcular monto en bolívares usando la tasa histórica del pago
            monto_bolivares = ""
            if tasa_pago and tasa_pago.idMoneda.idMoneda != 1:
                # Buscar tasa de bolívares en la fecha del pago
                tasa_bolivares = Tasa.objects.filter(
                    idMoneda__idMoneda=1,
                    fechaTasa__lte=pago.fechaPago
                ).order_by('-fechaTasa').first()
                
                if tasa_bolivares:
                    tasa_bolivares_valor = to_decimal(tasa_bolivares.montoTasa)
                    monto_pago_valor = to_decimal(pago.monto)
                    if tasa_bolivares_valor > Decimal('0'):
                        monto_bolivares_valor = monto_pago_valor * tasa_pago_valor / tasa_bolivares_valor
                        monto_bolivares = f" | Monto Bs: {monto_bolivares_valor:.2f}"
                    else:
                        monto_bolivares = " | Monto Bs: Error (tasa cero)"
                else:
                    monto_bolivares = " | Monto Bs: No hay tasa BS"
            else:
                monto_bolivares = f" | Monto Bs: {to_decimal(pago.monto):.2f}"

            # Construir el texto completo del pago con la tasa histórica
            texto_pago = f"Fecha: {pago.fechaPago.strftime('%d/%m/%Y')} | Monto: {pago.monto:.2f} {moneda_simbolo} | Tasa: {tasa_pago_valor:.2f} | Fecha tasa: {fecha_tasa_pago} | Forma: {pago.formaPago} | Referencia: {pago.referencia or ''}{monto_bolivares}"
            
            # Dibujar el texto con wrap automático
            y = draw_wrapped_text(texto_pago, 50, y, max_text_width)
            
    else:
        p.drawString(50, y, "No se han registrado pagos para esta factura.")
        y -= 14
    p.line(30, y, width - 30, y)
    y -= 20

    # --- Firma autorizada ---
    p.setFont("Helvetica-Bold", 11)
    p.drawCentredString(width / 2, y, f"FIRMA AUTORIZADA: ")
    y -= 20
    p.line(30, y, width - 30, y)

    p.showPage()
    p.save()
    return response

def reporte_pagos_pdf(request):
    # Trae todos los pagos
    pagos = list(Pago.objects.select_related('idNota', 'idTasa', 'idCuentaBanco__banco').order_by('-fechaPago'))

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'inline; filename="reporte_pagos.pdf"'
    page_size = landscape(letter)
    p = canvas.Canvas(response, pagesize=page_size)
    p.setTitle("Reporte de Pagos")
    width, height = page_size

    # Encabezado institucional a la izquierda
    config = Configuracion.objects.order_by('-fechaConfiguracion').first()
    logo_path = config.logo.path if config and config.logo else None
    nombre_institucion = config.nombreInstitucion if config else "Institución"
    rif_institucion = config.rif if config else ""
    direccion1 = "AV. ALBERTO RAVELL CON AV. INTERCOMUNAL JOSE ANTONIO PAEZ"
    direccion2 = "LOCAL UPTYAB, INDEPENDENCIA – EDO YARACUY"

    def draw_header():
        y = height - 40
        if logo_path and os.path.exists(logo_path):
            p.drawImage(logo_path, width - 120, y - 60, width=80, height=65, preserveAspectRatio=True, mask='auto')
        p.setFont("Helvetica-Bold", 13)
        p.drawString(140, y, nombre_institucion)
        y -= 18
        p.setFont("Helvetica", 11)
        p.drawString(140, y, f"RIF: {rif_institucion}")
        y -= 16
        p.setFont("Helvetica", 10)
        p.drawString(140, y, direccion1)
        y -= 14
        p.drawString(140, y, direccion2)
        y -= 18
        p.setFont("Helvetica-Bold", 13)
        p.drawString(140, y, "REPORTE DE PAGOS")
        y -= 10
        p.line(30, y, width - 30, y)
        return y - 18

    def draw_footer(y):
        p.setFont("Helvetica", 8)
        fecha_generacion = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        p.drawString(40, 20, f"Generado el: {fecha_generacion}")
        p.setFont("Helvetica-Bold", 10)
        p.drawString(width - 200, 20, "Firma autorizada")

    # Datos de la tabla
    headers = [
        "ID Pago", "N° Nota", "Fecha Pago", "Monto", "Moneda", "Forma de Pago",
        "Referencia", "Banco", "Observaciones"
    ]
    data = [headers]
    for pago in pagos:
        banco_nombre = pago.idCuentaBanco.banco.nombreBanco if pago.idCuentaBanco and hasattr(pago.idCuentaBanco, 'banco') else "—"
        data.append([
            str(pago.idPago),
            pago.idNota.numeroNota if pago.idNota else "",
            pago.fechaPago.strftime("%d/%m/%Y"),
            f"{pago.monto:.2f}",
            pago.idTasa.idMoneda.simboloMoneda if pago.idTasa and pago.idTasa.idMoneda and hasattr(pago.idTasa.idMoneda, 'simboloMoneda') else "",
            pago.formaPago,
            pago.referencia or "—",
            banco_nombre,
            pago.observaciones or "—"
        ])
    col_widths = [50, 105, 70, 70, 60, 80, 80, 80, 130]
    table_width = sum(col_widths)

    header_height = 160
    footer_height = 60
    row_height = 25

    available_height = height - header_height - footer_height
    max_rows_per_page = max(1, int(available_height // row_height))
    total_rows = len(data) - 1
    page = 0

    for start_row in range(0, total_rows, max_rows_per_page):
        end_row = min(start_row + max_rows_per_page, total_rows)
        page_data = [data[0]] + data[start_row + 1:end_row + 1]
        if page > 0:
            p.showPage()
        y = draw_header()
        table_x = 40
        table = Table(page_data, colWidths=col_widths, rowHeights=[row_height]*len(page_data))
        table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#fe8330")),
            ('TEXTCOLOR', (0,0), (-1,0), colors.white),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('FONTSIZE', (0,0), (-1,0), 9),
            ('ALIGN', (0,0), (-1,0), 'CENTER'),
            ('VALIGN', (0,0), (-1,0), 'MIDDLE'),
            ('BOTTOMPADDING', (0,0), (-1,0), 6),
            ('FONTSIZE', (0,1), (-1,-1), 8),
            ('ALIGN', (0,1), (-1,-1), 'CENTER'),
            ('ALIGN', (8,1), (8,-1), 'LEFT'),
            ('VALIGN', (0,1), (-1,-1), 'MIDDLE'),
            ('BACKGROUND', (0,1), (-1,-1), colors.whitesmoke),
            ('GRID', (0,0), (-1,-1), 0.5, colors.lightgrey),
            ('BOX', (0,0), (-1,-1), 0.5, colors.black),
        ]))
        table.wrapOn(p, width, height)
        table.drawOn(p, table_x, y - row_height * len(page_data) - 10)
        draw_footer(y)
        page += 1

    p.save()
    return response

def pago_pdf(request, pk):
    """
    PDF individual de pago, horizontal, cabezal a la izquierda.
    """
    pago = get_object_or_404(Pago.objects.select_related('idNota', 'idTasa', 'idCuentaBanco__banco'), pk=pk)
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="pago_{pk}.pdf"'
    page_size = landscape(letter)
    p = canvas.Canvas(response, pagesize=page_size)
    p.setTitle("Reporte de Pago Individual")
    width, height = page_size

    config = Configuracion.objects.order_by('-fechaConfiguracion').first()
    logo_path = config.logo.path if config and config.logo else None
    nombre_institucion = config.nombreInstitucion if config else "Institución"
    rif_institucion = config.rif if config else ""
    direccion1 = "AV. ALBERTO RAVELL CON AV. INTERCOMUNAL JOSE ANTONIO PAEZ"
    direccion2 = "LOCAL UPTYAB, INDEPENDENCIA – EDO YARACUY"

    def draw_header():
        y = height - 40
        if logo_path and os.path.exists(logo_path):
            p.drawImage(logo_path, width - 120, y - 60, width=80, height=65, preserveAspectRatio=True, mask='auto')
        p.setFont("Helvetica-Bold", 13)
        p.drawString(140, y, nombre_institucion)
        y -= 18
        p.setFont("Helvetica", 11)
        p.drawString(140, y, f"RIF: {rif_institucion}")
        y -= 16
        p.setFont("Helvetica", 10)
        p.drawString(140, y, direccion1)
        y -= 14
        p.drawString(140, y, direccion2)
        y -= 18
        p.setFont("Helvetica-Bold", 13)
        p.drawString(140, y, "COMPROBANTE DE PAGO")
        y -= 10
        p.line(30, y, width - 30, y)
        return y - 18

    def draw_footer(y):
        p.setFont("Helvetica", 8)
        fecha_generacion = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        p.drawString(40, 20, f"Generado el: {fecha_generacion}")
        p.setFont("Helvetica-Bold", 10)
        p.drawString(width - 200, 20, "Firma autorizada")

    y = draw_header()
    left_col_x = 60
    line_height = 22

    p.setFont("Helvetica-Bold", 11)
    p.drawString(left_col_x, y, f"ID Pago:")
    p.setFont("Helvetica", 10)
    p.drawString(left_col_x + 120, y, str(pago.idPago))
    y -= line_height

    p.setFont("Helvetica-Bold", 11)
    p.drawString(left_col_x, y, f"Nota asociada:")
    p.setFont("Helvetica", 10)
    p.drawString(left_col_x + 120, y, f"{pago.idNota.numeroNota if pago.idNota else ''}")
    y -= line_height

    p.setFont("Helvetica-Bold", 11)
    p.drawString(left_col_x, y, f"Fecha de Pago:")
    p.setFont("Helvetica", 10)
    p.drawString(left_col_x + 120, y, pago.fechaPago.strftime('%d/%m/%Y'))
    y -= line_height

    p.setFont("Helvetica-Bold", 11)
    p.drawString(left_col_x, y, f"Monto:")
    p.setFont("Helvetica", 10)
    p.drawString(left_col_x + 120, y, f"{pago.monto:.2f} {pago.idTasa.idMoneda.simboloMoneda if pago.idTasa and pago.idTasa.idMoneda else ''}")
    y -= line_height

    p.setFont("Helvetica-Bold", 11)
    p.drawString(left_col_x, y, f"Forma de Pago:")
    p.setFont("Helvetica", 10)
    p.drawString(left_col_x + 120, y, pago.formaPago)
    y -= line_height

    p.setFont("Helvetica-Bold", 11)
    p.drawString(left_col_x, y, f"Referencia:")
    p.setFont("Helvetica", 10)
    p.drawString(left_col_x + 120, y, pago.referencia or "—")
    y -= line_height

    p.setFont("Helvetica-Bold", 11)
    p.drawString(left_col_x, y, f"Banco:")
    p.setFont("Helvetica", 10)
    banco_nombre = pago.idCuentaBanco.banco.nombreBanco if pago.idCuentaBanco and hasattr(pago.idCuentaBanco, 'banco') else "—"
    p.drawString(left_col_x + 120, y, banco_nombre)
    y -= line_height

    p.setFont("Helvetica-Bold", 11)
    p.drawString(left_col_x, y, f"Observaciones:")
    p.setFont("Helvetica", 10)
    obs = pago.observaciones or "—"
    obs_lines = [obs[i:i+70] for i in range(0, len(obs), 70)]
    for line in obs_lines:
        p.drawString(left_col_x + 120, y, line)
        y -= 16

    y -= 10
    p.line(30, y, width - 30, y)
    y -= 20

    draw_footer(y)
    p.showPage()
    p.save()
    return response