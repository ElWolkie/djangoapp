from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.db.models import Subquery
from django.db import transaction
from django.urls import reverse
from .models import PlanCuenta
from .forms import PlanCuentaForm
from apps.cuentaBanco.models import CuentaBanco, Banco

def plan_cuenta_list(request):
    """
    Vista para listar todos los planes de cuenta existentes.
    Filtra por estado activo y ordena por código de cuenta.
    """
    planes = PlanCuenta.objects.filter(estadoPlanCuenta=True).order_by('codigoPlanCuenta')
    return render(request, 'planCuenta/tablaPlanCuenta.html', {
        'planes': planes,
        'titulo': 'Listado de Planes de Cuenta'
    })

def plan_cuenta_detail(request, pk):
    """
    Vista para mostrar los detalles de un plan de cuenta específico.
    """
    plan = get_object_or_404(PlanCuenta, pk=pk)
    subcuentas = plan.subcuentas.filter(estadoPlanCuenta=True)
    return render(request, 'planCuenta/detallePlanCuenta.html', {
        'plan': plan,
        'subcuentas': subcuentas
    })



from django.db.models import Subquery, Q

def plan_cuenta_create(request):
    """
    Vista para crear un nuevo plan de cuenta.
    Excluye los registros de PlanCuenta que ya están referenciados en CuentaBanco
    o que están relacionados con los bancos.
    """
    if request.method == 'POST':
        form = PlanCuentaForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                plan = form.save()
                return JsonResponse({
                    'success': True,
                    'message': 'Plan de Cuenta creado exitosamente!',
                    'redirect_url': reverse('plan_cuenta_list')
                })
        else:
            return JsonResponse({
                'success': False,
                'errors': form.errors
            })
    else:
        form = PlanCuentaForm()
        
        # Subconsulta para obtener los IDs de PlanCuenta referenciados en CuentaBanco
        cuentas_referenciadas = CuentaBanco.objects.values('planCuenta_id')
        
        # Subconsulta para obtener los IDs de PlanCuenta relacionados con los bancos
        bancos_referenciados = Banco.objects.values('codigoPlanCuenta_id')
        
        # Excluir los registros de PlanCuenta que están referenciados en CuentaBanco o relacionados con los bancos
        cuentas_padre = PlanCuenta.objects.filter(
            estadoPlanCuenta=True
        ).exclude(
            Q(idPlanCuenta__in=Subquery(cuentas_referenciadas)) | Q(idPlanCuenta__in=Subquery(bancos_referenciados))
        ).order_by('codigoPlanCuenta')
        
        return render(request, 'planCuenta/planCuenta.html', {
            'form': form,
            'cuentas_padre': cuentas_padre,  # Se pasa correctamente al template
            'titulo': 'Nuevo Plan de Cuenta'
        })



def plan_cuenta_update(request, pk):
    """
    Vista para actualizar un plan de cuenta existente.
    """
    plan = get_object_or_404(PlanCuenta, pk=pk)
    
    if request.method == 'POST':
        form = PlanCuentaForm(request.POST, instance=plan)
        if form.is_valid():
            with transaction.atomic():
                form.save()
                return JsonResponse({
                    'success': True,
                    'message': 'Plan de Cuenta actualizado exitosamente!',
                    'redirect_url': reverse('plan_cuenta_list')
                })
        else:
            return JsonResponse({
                'success': False,
                'errors': form.errors
            })
    else:
        form = PlanCuentaForm(instance=plan)
        cuentas_padre = PlanCuenta.objects.filter(
            estadoPlanCuenta=True
        ).exclude(pk=pk).order_by('codigoPlanCuenta')
        
        return render(request, 'planCuenta/planCuenta.html', {
            'form': form,
            'cuentas_padre': cuentas_padre,
            'titulo': 'Editar Plan de Cuenta',
            'editar': True
        })

def plan_cuenta_delete(request, pk):
    """
    Vista para desactivar (eliminación lógica) un plan de cuenta.
    """
    plan = get_object_or_404(PlanCuenta, pk=pk)
    
    if request.method == 'POST':
        plan.estadoPlanCuenta = False
        plan.save()
        return JsonResponse({
            'success': True,
            'message': 'Plan de Cuenta desactivado exitosamente!',
            'redirect_url': reverse('plan_cuenta_list')
        })
    
    return render(request, 'planCuenta/confirmar_eliminacion.html', {
        'plan': plan
    })