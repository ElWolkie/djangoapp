from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.urls import reverse
from .models import AsientoContable, DetalleAsiento
from .forms import AsientoContableForm, DetalleAsientoForm
from django.db import transaction
from apps.periodoContable.models import periodoContable  # Importa el modelo de Periodo Contable
from apps.planCuenta.models import PlanCuenta  # Importa el modelo PlanCuenta
from django.http import JsonResponse

def asiento_contable_detalles(request, pk):
    """
    Vista para obtener los detalles de un asiento contable en formato JSON.
    """
    try:
        asiento = get_object_or_404(AsientoContable, pk=pk)
        detalles = asiento.detalles.select_related('idPlanCuenta').all()
        detalles_data = [
            {
                'codigoPlanCuenta': detalle.idPlanCuenta.codigoPlanCuenta,
                'nombrePlanCuenta': detalle.idPlanCuenta.nombrePlanCuenta,
                'debe': float(detalle.debe),
                'haber': float(detalle.haber),
            }
            for detalle in detalles
        ]
        return JsonResponse({'success': True, 'detalles': detalles_data})
    except AsientoContable.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'El asiento contable no existe.'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'error': f'Ocurrió un error inesperado: {str(e)}'}, status=500)

def asiento_contable_list(request):
    """
    Vista para listar todos los asientos contables.
    """
    asientos = AsientoContable.objects.all().order_by('fechaAsiento', 'numeroAsiento')
    return render(request, 'asientoContable/tablaAsientoContable.html', {'asientos': asientos})

def asiento_contable_create(request):
    """
    Vista para crear un nuevo asiento contable.
    """
    periodos = periodoContable.objects.all()  # Obtén todos los periodos contables
    if request.method == 'POST':
        form = AsientoContableForm(request.POST)
        if form.is_valid():
            asiento = form.save()
            # Redirigir a detalle_asiento_create con el pk del asiento recién creado
            return JsonResponse({
                'success': True,
                'message': 'Asiento contable registrado exitosamente.',
                'redirect_url': reverse('detalle_asiento_create', kwargs={'pk': asiento.idAsiento})
            })
        else:
            return JsonResponse({
                'success': False,
                'errors': form.errors
            })
    else:
        form = AsientoContableForm()
    return render(request, 'asientoContable/asientoContable.html', {
        'form': form,
        'titulo': 'Nuevo Asiento Contable',
        'periodos': periodos  # Pasa los periodos al contexto
    })

def asiento_contable_detail(request, pk):
    """
    Vista para mostrar los detalles de un asiento contable.
    """
    asiento = get_object_or_404(AsientoContable, pk=pk)
    detalles = asiento.detalles.all()
    return render(request, 'asientoContable/detalleAsiento.html', {'asiento': asiento, 'detalles': detalles})

def asiento_contable_update(request, pk):
    """
    Vista para actualizar un asiento contable.
    """
    asiento = get_object_or_404(AsientoContable, pk=pk)
    if request.method == 'POST':
        form = AsientoContableForm(request.POST, instance=asiento)
        if form.is_valid():
            form.save()
            return redirect('asiento_contable_list', pk=asiento.idAsiento)
    else:
        form = AsientoContableForm(instance=asiento)
    return render(request, 'asientoContable/asientoContable.html', {'form': form, 'titulo': 'Editar Asiento Contable'})

def detalle_asiento_create(request, pk):
    """
    Vista para agregar un detalle a un asiento contable.
    """
    asiento = get_object_or_404(AsientoContable, pk=pk)
    planes_cuenta = PlanCuenta.objects.filter(estadoPlanCuenta=True)  # Obtén solo los planes de cuenta activos
    if request.method == 'POST':
        form = DetalleAsientoForm(request.POST)
        if form.is_valid():
            try:
                detalle = form.save(commit=False)
                detalle.idAsiento = asiento
                detalle.save()
                return JsonResponse({
                    'success': True,
                    'message': 'Detalle de asiento registrado correctamente.',
                    'redirect_url': reverse('asiento_contable_list')  # Cambiar a la lista de asientos
                })
            except Exception as e:
                if 'duplicate' in str(e).lower():
                    return JsonResponse({
                        'success': False,
                        'error': 'Ya existe un registro con los mismos datos. Por favor, verifica la información.'
                    })
                return JsonResponse({
                    'success': False,
                    'error': f'Ocurrió un error inesperado: {str(e)}'
                })
        else:
            return JsonResponse({
                'success': False,
                'errors': form.errors
            })
    else:
        form = DetalleAsientoForm()
    return render(request, 'asientoContable/detalleAsiento.html', {
        'form': form,
        'asiento': asiento,
        'planes_cuenta': planes_cuenta,  # Pasa los planes de cuenta al contexto
        'titulo': 'Agregar Detalle'
    })


def detalle_asiento_update(request, pk):
    """
    Vista para actualizar un detalle de asiento contable.
    """
    detalle = get_object_or_404(DetalleAsiento, pk=pk)
    planes_cuenta = PlanCuenta.objects.filter(estadoPlanCuenta=True)  # Obtén solo los planes de cuenta activos
    if request.method == 'POST':
        form = DetalleAsientoForm(request.POST, instance=detalle)
        if form.is_valid():
            form.save()
            return redirect('asiento_contable_detail', pk=detalle.idAsiento.idAsiento)
    else:
        form = DetalleAsientoForm(instance=detalle)
    return render(request, 'asientoContable/detalleAsiento.html', {
        'form': form,
        'detalle': detalle,
        'planes_cuenta': planes_cuenta,  # Pasa los planes de cuenta al contexto
        'titulo': 'Editar Detalle'
    })