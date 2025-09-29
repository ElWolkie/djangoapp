import os
import re
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

from .models import (
    TIPOS_ARTICULO, Factura, FacturaDetalle, NotaRelacionada, Pago, ParametroTributario, Nota, PlanArticulo
)
from .forms import (
    FacturaForm, FacturaDetalleForm, PagoForm, ParametroTributarioForm, NotaForm, PlanArticuloForm
)
from .templatetags.decimal_filters import to_decimal


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
    Vista para listar todos los pagos.
    """
    notas = Nota.objects.all()
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
                        conceptoAsiento=f"Asiento para la nota administrativa {numero_nota}",
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

    # Solo crea el registro si alguno de los IDs está presente
    if id_inscripcion or id_honorario or id_solicitud:
        NotaRelacionada.objects.create(
            idNota=nota,
            idInscripcion_id=id_inscripcion if id_inscripcion else None,
            idHonorario_id=id_honorario if id_honorario else None,
            idSolicitud_id=id_solicitud if id_solicitud else None
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
    try:
        # Filtrar las notas según el ID proporcionado o estado 'PAGADO'
        notas = Nota.objects.filter(idNota=nota_id) if nota_id else Nota.objects.filter(estado='PAGADO')

        if not notas.exists():
            return JsonResponse({
                'success': False,
                'message': 'No se encontraron notas para generar la factura.'
            }, status=400)

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

        # Redirigir a la página de carga para la primera factura creada
        if facturas_creadas:
            return redirect('factura_cargando', pk=facturas_creadas[0].id)
        
        # Si no se crearon facturas (todas ya existían)
        return JsonResponse({
            'success': False,
            'message': 'No se crearon nuevas facturas. Todas las notas ya tienen facturas asociadas.'
        }, status=400)

    except Exception as e:
        import traceback
        print(f"Error inesperado: {e}")
        print(traceback.format_exc())
        return JsonResponse({
            'success': False,
            'message': f'Ocurrió un error inesperado: {str(e)}. '
                       'Por favor, contacte al administrador del sistema si el problema persiste.'
        }, status=500)
    
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

def pago_create(request, pk=None):
    """
    Vista para crear un nuevo pago y generar un asiento contable asociado.
    """
    # Filtrar notas según el estado y el ID proporcionado
    if pk:
        notas = Nota.objects.filter(idNota=pk, estado__in=['PENDIENTE', 'PARCIAL']).order_by('numeroNota')
    else:
        # Traer las notas excluyendo las pagadas y agregando el símbolo de la moneda
        notas = Nota.objects.select_related('idTasa__idMoneda').exclude(estado='PAGADO').order_by('numeroNota')
        # Agregar el símbolo de la moneda a cada nota
        for nota in notas:
            nota.simbolo_moneda = nota.idTasa.idMoneda.simboloMoneda if hasattr(nota.idTasa, 'idMoneda') and hasattr(nota.idTasa.idMoneda, 'simboloMoneda') else ""
            print(f"Nota {nota.numeroNota} símbolo moneda: {nota.simbolo_moneda}")

    cuentas_banco = CuentaBanco.objects.filter(estado=True).order_by('idCuentaBanco')  # Filtrar cuentas bancarias activas
    tasas = Tasa.objects.select_related('idMoneda') \
        .values('idMoneda__idMoneda', 'idMoneda__nombreMoneda', 'idMoneda__simboloMoneda') \
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

    tasa_configuracion_valor = to_decimal_precise(tasa_configuracion.montoTasa)  # Convertir a Decimal de forma precisa
    print(f"Tasa de configuración ({moneda_configuracion.nombreMoneda}): {tasa_configuracion_valor}")

    # Calcular el saldo pendiente de cada nota
    notas_data = []
    for nota in notas:
        pagos_relacionados = Pago.objects.filter(idNota=nota)
        total_pagado = calcular_total_pagado_preciso(pagos_relacionados, moneda_configuracion, tasa_configuracion_valor)
        
        total_nota = to_decimal_precise(nota.totalNota)
        saldo_pendiente = (total_nota - total_pagado).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        
        print(f"Nota {nota.numeroNota}: Total Nota: {total_nota}, Total Pagado: {total_pagado}, Saldo Pendiente: {saldo_pendiente}")
        notas_data.append({
            'idNota': nota.idNota,
            'numeroNota': nota.numeroNota,
            'totalNota': float(total_nota),
            'saldoPendiente': float(saldo_pendiente),  # Ya está en la moneda de configuración
            'idPersona': nota.idPersona.cedula if nota.idPersona else "N/A",  # Incluye la cédula del cliente
            'idEmpresa': nota.idEmpresa.nombreEmpresa if nota.idEmpresa else "N/A",  # Incluye la nombre de la empresa
            'estado': nota.estado,
            'simbolo_moneda': moneda_configuracion.simboloMoneda  # Usar el símbolo de la moneda de configuración
        })

    if request.method == 'POST':
        # Procesar el campo monto para convertirlo a formato decimal
        post_data = request.POST.copy()
        monto_str = post_data.get('monto', '')
        if monto_str:
            # Usar la función precisa de conversión
            monto_decimal = to_decimal_precise(monto_str)
            post_data['monto'] = str(monto_decimal)

        form = PagoForm(post_data)        
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
                    total_pagado = calcular_total_pagado_preciso(pagos_relacionados, moneda_configuracion, tasa_configuracion_valor)
                    
                    total_nota = to_decimal_precise(pago.idNota.totalNota)
                    saldo_nota = (total_nota - total_pagado).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
                    
                    print(f"Saldo Nota (preciso): {saldo_nota}")

                    # Convertir el monto del pago a la moneda de configuración
                    tasa_pago = Tasa.objects.filter(idMoneda=pago.idTasa.idMoneda).order_by('-idTasa').first()
                    if not tasa_pago:
                        return JsonResponse({
                            'success': False,
                            'message': f'No se encontró una tasa registrada para la moneda del pago ({pago.idTasa.idMoneda.nombreMoneda}).'
                        }, status=400)

                    # Validar tasas antes de realizar cálculos
                    try:
                        validar_tasas(tasa_configuracion_valor, to_decimal_precise(tasa_pago.montoTasa))
                    except ValueError as e:
                        return JsonResponse({
                            'success': False,
                            'message': str(e)
                        }, status=400)

                    # Asegurar precisión en la conversión de monedas
                    try:
                        monto_pago_decimal = to_decimal_precise(pago.monto)
                        tasa_pago_monto = to_decimal_precise(tasa_pago.montoTasa)
                        
                        if pago.idTasa.idMoneda != moneda_configuracion:
                            monto_pago_convertido = (monto_pago_decimal * tasa_pago_monto / tasa_configuracion_valor)
                        else:
                            monto_pago_convertido = monto_pago_decimal
                        
                        monto_pago_convertido = monto_pago_convertido.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
                        print(f"Monto Pago Convertido (preciso): {monto_pago_convertido}")
                    except (InvalidOperation, ZeroDivisionError) as e:
                        return JsonResponse({
                            'success': False,
                            'message': f'Error en la conversión de monedas: {str(e)}. Verifique las tasas de cambio y los montos ingresados.'
                        }, status=400)
                    
                    if saldo_nota <= Decimal('0.0'):
                        return JsonResponse({
                            'success': False,
                            'message': 'El pago no se registró porque la nota ya está solvente.'
                        }, status=400)

                    if monto_pago_convertido > saldo_nota:
                        return JsonResponse({
                            'success': False,
                            'message': f'El monto del pago excede el saldo pendiente de la nota. '
                                       f'Saldo pendiente: {saldo_nota:.2f}.'
                        }, status=400)
                    
                    print(f"Monto del Pago: {monto_pago_decimal}")
                    print(f"Tasa de Pago: {tasa_pago_monto}")
                    print(f"Tasa de Configuración: {tasa_configuracion_valor}")
                    print(f"Total Nota: {total_nota}")
                    print(f"Total Pagado: {total_pagado}")
                    print(f"Saldo Nota: {saldo_nota}")
                    print(f"Monto Pago Convertido: {monto_pago_convertido}")
                    
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

                    # Obtener el plan de cuenta según la forma de pago
                    if pago.formaPago == 'EFECTIVO':
                        plan_cuenta_debe = PlanCuenta.objects.filter(codigoPlanCuenta='11000101').first()
                        print(f"Plan de cuenta para pagos en efectivo: {plan_cuenta_debe}")
                        if not plan_cuenta_debe:
                            return JsonResponse({
                                'success': False,
                                'message': 'No se encontró un plan de cuenta con el código 1101 para pagos en efectivo.'
                            }, status=400)
                    else:
                        plan_cuenta_debe = PlanCuenta.objects.get(pk=request.POST['idPlanCuentaDebe'])
                        if not plan_cuenta_debe:
                            return JsonResponse({
                                'success': False,
                                'message': 'No se encontró un plan de cuenta válido para la forma de pago seleccionada.'
                            }, status=400)

                    # Crear los detalles del asiento contable
                    try:
                        DetalleAsiento.objects.create(
                            idAsiento=asiento_pago,
                            idPlanCuenta=plan_cuenta_debe,  # Cuenta de ingresos seleccionada por el usuario
                            debe=float(monto_pago_decimal),  # Usar el monto preciso
                            haber=0.00
                        )
                        DetalleAsiento.objects.create(
                            idAsiento=asiento_pago,
                            idPlanCuenta=plan_cuenta_haber,  # Cuenta asociada al Debe del asiento principal
                            debe=0.00,
                            haber=float(monto_pago_decimal)  # Usar el monto preciso
                        )
                    except Exception as e:
                        raise ValueError(f'Error al crear los detalles del asiento contable: {str(e)}')

                    # Asociar el asiento contable al pago
                    pago.idAsiento = asiento_pago
                    pago.save()

                    # Caso 1: El pago fue exitoso, pero aún hay deuda
                    diferencia = saldo_nota - monto_pago_convertido
                    if diferencia > Decimal('0.0'):
                        pago.idNota.estado = 'PARCIAL'
                        pago.idNota.save()

                        # Verificar el tipo de asociación de la nota usando las relaciones
                        nota_relacionada = NotaRelacionada.objects.filter(idNota=pago.idNota).first()
                        if nota_relacionada:
                            match nota_relacionada:
                                case _ if nota_relacionada.idInscripcion:
                                    inscripcion = nota_relacionada.idInscripcion
                                    inscripcion.estadoPago = 'PARCIAL'
                                    inscripcion.save()
                                case _ if nota_relacionada.idCuota:
                                    cuota = nota_relacionada.idCuota
                                    cuota.estadoPago = 'PARCIAL'
                                    cuota.save()
                                case _ if nota_relacionada.idSolicitud:
                                    solicitud = nota_relacionada.idSolicitud
                                    solicitud.estadoPago = 'PARCIAL'
                                    solicitud.save()
                                case _ if nota_relacionada.idHonorario:
                                    honorario = nota_relacionada.idHonorario
                                    honorario.estadoPago = 'PARCIAL'
                                    honorario.save()
                                case _:
                                    print("Tipo de asociación desconocido")
                        else:
                            print("No se encontró una relación para la nota.")

                        return JsonResponse({
                            'success': True,
                            'message': 'El pago fue exitoso, aun posee deuda ¿Desea realizar otro pago adicional?',
                            'redirect_url': f"{reverse('pago_create')}?nota={pago.idNota.idNota}",
                            'pago': {
                                'idPago': pago.idPago,
                                'idNota': pago.idNota.numeroNota,
                                'monto': f"{float(monto_pago_decimal):.2f} {pago.idTasa.idMoneda.simboloMoneda}",
                                'fechaPago': pago.fechaPago.strftime('%d/%m/%Y'),
                                'formaPago': pago.formaPago,
                                'referencia': pago.referencia
                            }
                        })      
                    else:
                        # Caso 2: El pago fue exitoso, la deuda fue saldada y se cerró la nota
                        if es_cero_con_tolerancia(diferencia):
                            pago.idNota.estado = 'PAGADO'
                            pago.idNota.save()

                            # Verificar el tipo de asociación de la nota usando las relaciones
                            nota_relacionada = NotaRelacionada.objects.filter(idNota=pago.idNota).first()
                            relaciones = {}  # Diccionario para almacenar las llaves relacionadas

                            if nota_relacionada:
                                match nota_relacionada:
                                    case _ if nota_relacionada.idInscripcion:
                                        inscripcion = nota_relacionada.idInscripcion
                                        inscripcion.estadoPago = 'PAGADO'
                                        inscripcion.save()

                                        # Obtener las cuotas relacionadas y marcarlas como pagadas
                                        cuotas_pagadas = InscripcionCuota.objects.filter(
                                            idInscripcion=inscripcion, estadoPago='PENDIENTE'
                                        )
                                        for cuota in cuotas_pagadas:
                                            cuota.estadoPago = 'PAGADO'
                                            cuota.save()

                                        relaciones['inscripcion'] = inscripcion.idInscripcion
                                        relaciones['cuotas'] = [cuota.idCuota.idCuota for cuota in cuotas_pagadas]

                                    case _ if nota_relacionada.idCuota:
                                        cuota = nota_relacionada.idCuota
                                        cuota.estadoPago = 'PAGADO'
                                        cuota.save()
                                        relaciones['cuota'] = cuota.idCuota

                                    case _ if nota_relacionada.idSolicitud:
                                        solicitud = nota_relacionada.idSolicitud
                                        solicitud.estadoPago = 'PAGADO'
                                        solicitud.save()
                                        relaciones['solicitud'] = solicitud.idSoli

                                    case _ if nota_relacionada.idHonorario:
                                        honorario = nota_relacionada.idHonorario
                                        honorario.estadoPago = 'PAGADO'
                                        honorario.save()
                                        relaciones['honorario'] = honorario.idHonorario

                                    case _:
                                        print("Tipo de asociación desconocido")
                            else:
                                print("No se encontró una relación para la nota.")

                            # GENERAR FACTURA AUTOMÁTICAMENTE
                            factura_generada = False
                            factura_id = None
                            try:
                                # Nota: necesitarías implementar generar_numero_factura_unico()
                                factura = Factura.objects.create(
                                    numeroFactura=f"FACT-{pago.idNota.numeroNota}",  # Temporal
                                    idPersona=pago.idNota.idPersona,
                                    idEmpresa=pago.idNota.idEmpresa,
                                    fechaEmision=datetime.now().date(),
                                    totalVenta=float(total_nota),
                                    subtotalExento=float(to_decimal_precise(pago.idNota.subtotalExento)),
                                    subtotalGravado=float(to_decimal_precise(pago.idNota.subtotalGravado)),
                                    iva=float(to_decimal_precise(pago.idNota.iva)),
                                    ivaRetenido=float(to_decimal_precise(pago.idNota.ivaRetenido)),
                                    islrRetenido=float(to_decimal_precise(pago.idNota.islrRetenido)),
                                    descuento=float(to_decimal_precise(pago.idNota.descuento)),
                                    estado='GENERADA'
                                )
                                FacturaDetalle.objects.create(
                                    idFactura=factura,
                                    idNota=pago.idNota,
                                    tipoItem=pago.idNota.tipoArticulo,
                                    descripcion=f"Nota {pago.idNota.numeroNota}",
                                    cantidad=1,
                                    precioUnitario=float(total_nota),
                                    exento=to_decimal_precise(pago.idNota.subtotalExento) > Decimal('0'),
                                    descuentoItem=float(to_decimal_precise(pago.idNota.descuento)),
                                    subtotal=float(to_decimal_precise(pago.idNota.subtotalGravado) + to_decimal_precise(pago.idNota.subtotalExento)),
                                    ivaItem=float(to_decimal_precise(pago.idNota.iva)),
                                    totalItem=float(total_nota)
                                )
                                # Actualizar estado de la nota
                                pago.idNota.estado = 'FACTURADO'
                                pago.idNota.save()
                                
                                factura_generada = True
                                factura_id = factura.idFactura
                            except Exception as e:
                                print(f"Error al generar factura automáticamente: {str(e)}")
                                # Si hay error, mantener el estado PAGADO y no FACTURADO
                                pass

                            return JsonResponse({
                                'success': True,
                                'message': 'Pago creado exitosamente. La nota ha sido pagada en su totalidad y facturada automáticamente.',
                                'redirect_url': reverse('factura_cargando', args=[factura_id]) if factura_generada else reverse('factura_list'),
                                'factura_generada': factura_generada,
                                'factura_id': factura_id,
                                'relaciones': relaciones,
                                'pago': {
                                    'idPago': pago.idPago,
                                    'idNota': pago.idNota.numeroNota,
                                    'monto': f"{float(monto_pago_decimal):.2f} {pago.idTasa.idMoneda.simboloMoneda}",
                                    'fechaPago': pago.fechaPago.strftime('%d/%m/%Y'),
                                    'formaPago': pago.formaPago,
                                    'referencia': pago.referencia
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
        'tasa_configuracion_valor': float(tasa_configuracion_valor)  # Tasa de configuración
    })
@transaction.atomic
def pago_edit(request, pk):
    """
    Vista para editar un pago existente.
    """
    pago = get_object_or_404(Pago, pk=pk)
    notas = Nota.objects.all()
    cuentas_banco = CuentaBanco.objects.filter(estado=True)
    tasas = Tasa.objects.select_related('idMoneda') \
        .values('idTasa', 'idMoneda__nombreMoneda', 'montoTasa')
    cuentas_plan = PlanCuenta.objects.filter(estadoPlanCuenta=True)
    today_date = datetime.now().strftime('%Y-%m-%d')

    if request.method == 'POST':
        form = PagoForm(request.POST, instance=pago)
        if form.is_valid():
            form.save()
            return redirect('pago_list')
    else:
        form = PagoForm(instance=pago)

    return render(request, 'factura/pago_edit.html', {
        'form': form,
        'pago': pago,
        'notas': notas,
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
    pagos = Pago.objects.filter(idNota=nota)
    config = Configuracion.objects.order_by('-fechaConfiguracion').first()

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="factura_{factura.numeroFactura}.pdf"'
    p = canvas.Canvas(response, pagesize=letter)
    p.setTitle("Reporte de Factura Indivual")
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
    for det in detalles:
        p.drawString(40, y, det.descripcion[:40])
        y -= 14
        p.setFont("Helvetica-Oblique", 9)
        p.drawString(50, y, f"Artículo: {det.tipoItem}")
        p.setFont("Helvetica", 10)
        p.drawRightString(300, y, f"{det.cantidad:.2f}")
        p.drawRightString(400, y, f"{det.precioUnitario:.2f}")
        p.drawRightString(510, y, f"{det.subtotal:.2f}")
        y -= 18
        if y < 120:
            p.showPage()
            y = height - 80
    p.line(30, y, width - 30, y)
    y -= 20

    # --- Totales y resumen ---
    p.setFont("Helvetica", 10)
    p.drawRightString(510, y, f"Subtotal Exento:      {factura.subtotalExento:.2f}")
    y -= 16
    p.drawRightString(510, y, f"Subtotal Gravado:     {factura.subtotalGravado:.2f}")
    y -= 16
    p.drawRightString(510, y, f"IVA (16%):            {factura.iva:.2f}")
    y -= 16
    p.drawRightString(510, y, f"IVA Retenido (75%):   {factura.ivaRetenido if factura.ivaRetenido else 0:.2f}")
    y -= 16
    p.drawRightString(510, y, f"ISLR Retenido (3%):   {factura.islrRetenido if factura.islrRetenido else 0:.2f}")
    y -= 16
    p.drawRightString(510, y, f"Descuento:            {factura.descuento:.2f}")
    y -= 16
    p.line(250, y, width - 30, y)
    y -= 18
    p.setFont("Helvetica-Bold", 11)
    p.drawRightString(510, y, f"TOTAL:                {factura.totalVenta:.2f}")
    y -= 20
    p.line(30, y, width - 30, y)
    y -= 20

    # --- Pagos realizados ---
    p.setFont("Helvetica-Bold", 10)
    p.drawString(40, y, "Pagos realizados:")
    y -= 16
    p.setFont("Helvetica", 10)
    if pagos.exists():
        for pago in pagos:
            moneda_simbolo = pago.idTasa.idMoneda.simboloMoneda if pago.idTasa and pago.idTasa.idMoneda else ""
            p.drawString(50, y, f"Fecha: {pago.fechaPago.strftime('%d/%m/%Y')} | Monto: {pago.monto:.2f} {moneda_simbolo} | Forma: {pago.formaPago} | Referencia: {pago.referencia or ''}")
            y -= 14
            if y < 80:
                p.showPage()
                y = height - 80
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