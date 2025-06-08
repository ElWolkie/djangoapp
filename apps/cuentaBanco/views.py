from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, permission_required
from django.core.exceptions import ValidationError
from django.http import JsonResponse
from django.db.models import Max

from django.urls import reverse
from django.db import transaction
from apps.asientoContable.models import AsientoContable, DetalleAsiento
from datetime import date
from apps.periodoContable.models import periodoContable
from .models import Banco, CuentaBanco
from .forms import BancoForm, CuentaBancoForm
from apps.planCuenta.models import PlanCuenta
from apps.home.models import Moneda
from django.contrib import messages # Importar messages

@login_required(login_url='login')
@permission_required("cuentaBanco.view_banco", raise_exception=True)
def banco_list(request):
    mostrar = request.GET.get('mostrar_inactivos', 'false') == 'true'
    if mostrar:
        bancos = Banco.objects.all()
    else:
        bancos = Banco.objects.filter(estadoBanco=True).order_by('nombreBanco')
    return render(request, 'bancos/tablaBancos.html', {
        'bancos': bancos,
        'titulo': 'Listado de Bancos',
        'mostrar_inactivos': mostrar,
    })

@login_required(login_url='login')
@permission_required("cuentaBanco.view_banco", raise_exception=True)
def banco_detail(request, pk):
    """
    Vista para mostrar los detalles de un banco y sus cuentas asociadas.
    """
    banco = get_object_or_404(Banco, pk=pk)
    cuentas = banco.cuentabanco_set.filter(estado=True)
    return render(request, 'bancos/detalleBanco.html', {
        'banco': banco,
        'cuentas': cuentas
    })

@login_required(login_url='login')
@permission_required("cuentaBanco.add_banco", raise_exception=True)
def banco_create(request):
    if request.method == 'POST':
        form = BancoForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                banco = form.save()
                return JsonResponse({
                    'success': True,
                    'message': 'Banco registrado exitosamente.',
                    'redirect_url': reverse('banco_list')
                })
        else:
            return JsonResponse({
                'success': False,
                'errors': form.errors
            })
    else:
        form = BancoForm()
        planes = PlanCuenta.objects.filter(estadoPlanCuenta=True).order_by('codigoPlanCuenta')
        return render(request, 'bancos/banco.html', {
            'form': form,
            'planes': planes,
            'titulo': 'Registrar Banco'
        })
    

def is_ajax(request):
    return request.META.get('HTTP_X_REQUESTED_WITH') == 'XMLHttpRequest'

@login_required(login_url='login')
@permission_required("cuentaBanco.change_banco", raise_exception=True)
def banco_update(request, pk):
    """
    Vista para actualizar un banco existente (GET devuelve el modal, POST via AJAX guarda).
    """
    banco  = get_object_or_404(Banco, pk=pk)
    planes = PlanCuenta.objects.all()  # para los selectores

    # POST vía AJAX: procesar el formulario
    if request.method == 'POST' and is_ajax(request):
        form = BancoForm(request.POST, instance=banco)
        if form.is_valid():
            with transaction.atomic():
                form.save()
            return JsonResponse({
                'success': True,
                'message': 'Banco actualizado exitosamente!',
                'redirect_url': reverse('banco_list')
            })
        else:
            return JsonResponse({
                'success': False,
                'errors': form.errors
            })

    # GET: renderizamos el fragmento HTML para el modal
    form = BancoForm(instance=banco)
    return render(request, 'bancos/modales/editBanco.html', {
        'form': form,
        'banco': banco,
        'planes': planes,
        'titulo': 'Editar Banco',
        'editar': True,
    })

@login_required(login_url='login')
@permission_required("cuentaBanco.change_banco", raise_exception=True)
def banco_delete(request, pk):
    banco = get_object_or_404(Banco, pk=pk)
    # Actualizamos el estado sin modificar el nombre u otros campos únicos
    banco.estadoBanco = False
    try:
        banco.save()  # Aquí se ejecuta la validación en save()
        return JsonResponse({'success': True, 'message': 'Banco desactivado correctamente. ⛔'})
    except ValidationError as e:
        # Regresamos el mensaje de error; esto ocurriría si se dispara la validación única
        return JsonResponse({'success': False, 'message': e.messages})

@login_required(login_url='login')
@permission_required("cuentaBanco.change_banco", raise_exception=True)
def banco_reactivate(request, pk):
    banco = get_object_or_404(Banco, pk=pk)
    # Actualizamos el estado sin modificar el nombre u otros campos únicos
    banco.estadoBanco = True
    try:
        # Banco.objects.filter(pk=pk).update(estadoBanco=True)
        banco.save()  # Aquí se ejecuta la validación en save()
        return JsonResponse({'success': True, 'message': 'Banco reactivado correctamente. ✅'})
    except ValidationError as e:
        # Regresamos el mensaje de error; esto ocurriría si se dispara la validación única
        return JsonResponse({'success': False, 'message': e.messages})

@login_required(login_url='login')
@permission_required("cuentaBanco.view_cuentabanco", raise_exception=True)
def cuenta_banco_list(request):
    mostrar = request.GET.get('mostrar_inactivos', 'false') == 'true'
    if mostrar:
        cuentas = CuentaBanco.objects.all()
    else:
        cuentas = CuentaBanco.objects.filter(estado=True).select_related('banco', 'moneda', 'planCuenta').order_by('banco__nombreBanco', 'numeroCuentaBanco')

    return render(request, 'bancos/tablaCuentaBanco.html', {
        'cuentas': cuentas,
        'titulo': 'Listado de Cuentas Bancarias',
        'mostrar_inactivos': mostrar,
    })

@login_required(login_url='login')
@permission_required("cuentaBanco.view_cuentabanco", raise_exception=True)
def cuenta_banco_detail(request, pk):
    """
    Vista para mostrar los detalles de una cuenta bancaria.
    """
    cuenta = get_object_or_404(CuentaBanco, pk=pk)
    return render(request, 'bancos/detalleCuentaBanco.html', {
        'cuenta': cuenta
    })
@login_required(login_url='login')
@permission_required("cuentaBanco.add_cuentabanco", raise_exception=True)
def cuenta_banco_create(request):
    if request.method == 'POST':
        form = CuentaBancoForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                cuenta = form.save(commit=False)
                
                try:
                    # Convertir a entero
                    plan_cuenta_credito = int(request.POST.get('planCuentaCredito'))
                except (TypeError, ValueError):
                    return JsonResponse({
                        'success': False,
                        'message': 'ID de plan de cuenta crédito inválido'
                    }, status=400)
    
                print(f"Plan Cuenta Crédito recibido: {plan_cuenta_credito}")

                if not PlanCuenta.objects.filter(idPlanCuenta=plan_cuenta_credito).exists():
                    return JsonResponse({
                        'success': False,
                        'message': 'El plan de cuenta crédito no existe'
                    }, status=400)

                # Crear plan de cuenta si no existe
                if not cuenta.planCuenta_id:
                    try:
                        nombre_producto = {
                            'corriente': "CUENTAS CORRIENTES",
                            'ahorro': "CUENTAS DE AHORRO",
                            'plazo_fijo': "DEPÓSITOS A PLAZO",
                            'prestamo': "PRÉSTAMOS BANCARIOS",
                            'inversion': "FONDOS DE INVERSIÓN"
                        }.get(cuenta.tipoProducto, "OTRAS CUENTAS")
                        
                        cuenta_producto, created = PlanCuenta.objects.get_or_create(
                            nombrePlanCuenta=nombre_producto,
                            tipoPlanCuenta=cuenta.banco.codigoPlanCuenta.tipoPlanCuenta,
                            nivelPlanCuenta=cuenta.banco.codigoPlanCuenta.nivelPlanCuenta + 1,
                            cuentaPadre=cuenta.banco.codigoPlanCuenta,
                            defaults={'codigoPlanCuenta': _generate_product_code(cuenta)}
                        )
                        
                        new_code = _generate_account_code(cuenta, cuenta_producto)
                        
                        plan_cuenta = PlanCuenta.objects.create(
                            codigoPlanCuenta=new_code,
                            nombrePlanCuenta=f"{cuenta.get_tipoProducto_display()} {cuenta.numeroCuentaBanco}",
                            tipoPlanCuenta=cuenta.banco.codigoPlanCuenta.tipoPlanCuenta,
                            nivelPlanCuenta=cuenta_producto.nivelPlanCuenta + 1,
                            cuentaPadre=cuenta_producto
                        )
                        cuenta.planCuenta = plan_cuenta
                        print(f"Nuevo plan de cuenta creado: {plan_cuenta.idPlanCuenta}")
                    except Exception as e:
                        print(f"Error creando plan de cuenta: {e}")
                        return JsonResponse({
                            'success': False,
                            'message': f'Error al crear plan de cuenta: {str(e)}'
                        }, status=400)

                # Guardar la cuenta bancaria
                cuenta.save()
                print(f"Cuenta bancaria guardada ID: {cuenta.idCuentaBanco}")

                # Lógica para registrar el asiento contable inicial
                if cuenta.saldoDisponible != 0:
                    periodo_activo = periodoContable.objects.filter(estadoPeriodo=True).first()
                    if not periodo_activo:
                        periodo_activo = periodoContable.objects.order_by('-idPeriodo').first()
                    
                    if periodo_activo:
                        try:
                            asiento = AsientoContable.objects.create(
                                numeroAsiento=f"INI-{cuenta.idCuentaBanco}-{date.today().strftime('%Y%m%d')}",
                                fechaAsiento=date.today(),
                                conceptoAsiento=f"Apertura de cuenta bancaria {cuenta.numeroCuentaBanco}, saldo inicial",
                                idPeriodo=periodo_activo
                            )

                            DetalleAsiento.objects.create(
                                idAsiento=asiento,
                                idPlanCuenta_id=cuenta.planCuenta.idPlanCuenta,
                                debe=cuenta.saldoDisponible,
                                haber=0.00
                            )

                            DetalleAsiento.objects.create(
                                idAsiento=asiento,
                                idPlanCuenta_id=plan_cuenta_credito,
                                debe=0.00,
                                haber=cuenta.saldoDisponible
                            )
                            print("Asiento contable creado exitosamente")
                        except Exception as e:
                            print(f"Error creando asiento contable: {e}")
                            # IMPORTANTE: Esto no debe impedir la creación de la cuenta
                            # Solo registra el error pero continúa
                    else:
                        print("Advertencia: No hay período contable activo, no se creará asiento")

                # SIEMPRE devuelve éxito si la cuenta se creó
                return JsonResponse({
                    'success': True,
                    'message': 'Cuenta bancaria creada exitosamente!',
                    'redirect_url': reverse('cuenta_banco_list')
                })
        else:
            # Manejo de errores de formulario
            return JsonResponse({
                'success': False,
                'errors': form.errors
            }, status=400)
    else:
        form = CuentaBancoForm()
        bancos = Banco.objects.filter(estadoBanco=True).order_by('nombreBanco')
        monedas = Moneda.objects.filter(estadoMoneda="ACTIVO").order_by('nombreMoneda')
        cuentas_plan = PlanCuenta.objects.filter(estadoPlanCuenta=True).order_by('codigoPlanCuenta')

        return render(request, 'bancos/cuentaBanco.html', {
            'form': form,
            'bancos': bancos,
            'monedas': monedas,
            'cuentas_plan': cuentas_plan,
            'titulo': 'Nueva Cuenta Bancaria'
        })

def _generate_product_code(cuenta):
    try:
        last_product = PlanCuenta.objects.filter(
            cuentaPadre=cuenta.banco.codigoPlanCuenta
        ).aggregate(Max('codigoPlanCuenta'))
        
        if last_product['codigoPlanCuenta__max']:
            last_num = int(last_product['codigoPlanCuenta__max'][-2:])
            new_code = f"{cuenta.banco.codigoPlanCuenta.codigoPlanCuenta}{last_num + 1:02d}"
        else:
            new_code = f"{cuenta.banco.codigoPlanCuenta.codigoPlanCuenta}01"
        
        print(f"[DEBUG] Código de producto generado correctamente: {new_code}")
        return new_code
    except Exception as e:
        print(f"[ERROR] Error al generar el código de producto: {e}")
        raise


def _generate_account_code(cuenta, cuenta_producto):
    try:
        last_account = PlanCuenta.objects.filter(
            cuentaPadre=cuenta_producto
        ).aggregate(Max('codigoPlanCuenta'))
        
        if last_account['codigoPlanCuenta__max']:
            last_num = int(last_account['codigoPlanCuenta__max'][-2:])
            new_code = f"{cuenta_producto.codigoPlanCuenta}{last_num + 1:02d}"
        else:
            new_code = f"{cuenta_producto.codigoPlanCuenta}01"
        
        print(f"[DEBUG] Código de cuenta bancaria generado correctamente: {new_code}")
        return new_code
    except Exception as e:
        print(f"[ERROR] Error al generar el código de cuenta bancaria: {e}")
        raise

def cuenta_banco_update(request, pk):
    cuenta = get_object_or_404(CuentaBanco, pk=pk)
    bancos = Banco.objects.filter(estadoBanco=True)

    if request.method == 'POST':
        form = CuentaBancoForm(request.POST, instance=cuenta)
        if form.is_valid():
            form.save()
            # Verificar si la solicitud es AJAX
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'message': 'Cuenta bancaria actualizada correctamente.',
                    'redirect_url': reverse('cuenta_banco_list') # Asegúrate que este nombre de URL sea correcto
                })
            else:
                # Solicitud POST no-AJAX exitosa
                messages.success(request, 'Cuenta bancaria actualizada correctamente.')
                return redirect(reverse('cuenta_banco_list')) # Redirigir a la lista
        else: # El formulario no es válido
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'errors': form.errors})
            else:
                messages.error(request, "Por favor, corrija los errores a continuación.")
                context = {
                    'form': form, # El formulario con errores y datos POST
                    'cuenta': cuenta,
                    'bancos': bancos, # Para el selector de banco si es necesario
                    'is_post_error_page': True # Flag opcional
                }
                return render(request, 'bancos/modales/editCuentaBanco.html', context)
    else: # Solicitud GET
        form = CuentaBancoForm(instance=cuenta)

    context = {
        'form': form,
        'cuenta': cuenta,
        'bancos': bancos, # Para el selector de banco
    }
    return render(request, 'bancos/modales/editCuentaBanco.html', context)


def cuenta_banco_delete(request, pk):
    """
    Vista para desactivar (eliminación lógica) una cuenta bancaria.
    """
    cuenta = get_object_or_404(CuentaBanco, pk=pk)
    
    if request.method == 'POST':
        cuenta.estado = False
        cuenta.save()
        return JsonResponse({
            'success': True,
            'message': 'Cuenta bancaria desactivada exitosamente!',
            'redirect_url': reverse('cuenta_banco_list')
        })

@login_required(login_url='login')
@permission_required("cuentaBanco.change_cuentabanco", raise_exception=True)
def cuenta_banco_reactivate(request, pk):
    cuenta = get_object_or_404(CuentaBanco, pk=pk)
    
    if request.method == 'POST':
        cuenta.estado = True
        cuenta.save()
        return JsonResponse({
            'success': True,
            'message': 'Cuenta bancaria activada exitosamente!',
            'redirect_url': reverse('cuenta_banco_list')
        })