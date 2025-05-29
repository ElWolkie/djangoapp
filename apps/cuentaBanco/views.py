from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, permission_required
from django.core.exceptions import ValidationError
from django.http import JsonResponse

from django.urls import reverse
from django.db import transaction
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
                cuenta = form.save()
                return JsonResponse({
                    'success': True,
                    'message': 'Cuenta bancaria creada exitosamente!',
                    'redirect_url': reverse('cuenta_banco_list')
                })
        else:
            return JsonResponse({
                'success': False,
                'errors': form.errors
            })
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

@login_required(login_url='login')
@permission_required("cuentaBanco.change_cuentabanco", raise_exception=True)
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