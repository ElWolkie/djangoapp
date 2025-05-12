from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.urls import reverse
from django.db import transaction
from .models import Banco, CuentaBanco
from .forms import BancoForm, CuentaBancoForm
from apps.planCuenta.models import PlanCuenta
from apps.home.models import Moneda

def banco_list(request):
    """
    Vista para listar todos los bancos activos.
    """
    bancos = Banco.objects.filter(estadoBanco=True).order_by('nombreBanco')
    return render(request, 'bancos/tablaBancos.html', {
        'bancos': bancos,
        'titulo': 'Listado de Bancos'
    })

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

from django.http import JsonResponse

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
    

def banco_update(request, pk):
    """
    Vista para actualizar un banco existente.
    """
    banco = get_object_or_404(Banco, pk=pk)
    
    if request.method == 'POST':
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
    else:
        form = BancoForm(instance=banco)
        return render(request, 'bancos/banco.html', {
            'form': form,
            'titulo': 'Editar Banco',
            'editar': True
        })

def banco_delete(request, pk):
    """
    Vista para desactivar (eliminación lógica) un banco.
    """
    banco = get_object_or_404(Banco, pk=pk)
    
    if request.method == 'POST':
        banco.estadoBanco = False
        banco.save()
        return JsonResponse({
            'success': True,
            'message': 'Banco desactivado exitosamente!',
            'redirect_url': reverse('banco_list')
        })
    
    return render(request, 'bancos/confirmar_eliminacion.html', {
        'banco': banco
    })

def cuenta_banco_list(request):
    """
    Vista para listar todas las cuentas bancarias activas.
    """
    cuentas = CuentaBanco.objects.filter(estado=True).select_related(
        'banco', 'moneda', 'planCuenta'
    ).order_by('banco__nombreBanco', 'numeroCuentaBanco')
    
    return render(request, 'bancos/tablaCuentaBanco.html', {
        'cuentas': cuentas,
        'titulo': 'Listado de Cuentas Bancarias'
    })

def cuenta_banco_detail(request, pk):
    """
    Vista para mostrar los detalles de una cuenta bancaria.
    """
    cuenta = get_object_or_404(CuentaBanco, pk=pk)
    return render(request, 'bancos/detalleCuentaBanco.html', {
        'cuenta': cuenta
    })
def cuenta_banco_create(request):
    """
    Vista para crear una nueva cuenta bancaria con su cuenta contable asociada.
    """
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
        monedas = Moneda.objects.filter(estadoMoneda="ACTIVO").order_by('nombreMoneda')  # Obtener monedas activas
        return render(request, 'bancos/cuentaBanco.html', {
            'form': form,
            'bancos': bancos,
            'monedas': monedas,  # Pasar las monedas al contexto
            'titulo': 'Nueva Cuenta Bancaria'
        })

def cuenta_banco_update(request, pk):
    """
    Vista para actualizar una cuenta bancaria existente.
    """
    cuenta = get_object_or_404(CuentaBanco, pk=pk)
    
    if request.method == 'POST':
        form = CuentaBancoForm(request.POST, instance=cuenta)
        if form.is_valid():
            with transaction.atomic():
                form.save()
                return JsonResponse({
                    'success': True,
                    'message': 'Cuenta bancaria actualizada exitosamente!',
                    'redirect_url': reverse('cuenta_banco_list')
                })
        else:
            return JsonResponse({
                'success': False,
                'errors': form.errors
            })
    else:
        form = CuentaBancoForm(instance=cuenta)
        return render(request, 'bancos/cuentaBanco.html', {
            'form': form,
            'titulo': 'Editar Cuenta Bancaria',
            'editar': True
        })

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
    
    return render(request, 'bancos/confirmar_eliminacion.html', {
        'cuenta': cuenta
    })