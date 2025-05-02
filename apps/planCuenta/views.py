from django.shortcuts import render, redirect
from .models import PlanCuenta
from .forms import PlanCuentaForm
from django.http import JsonResponse

def plan_cuenta_list(request):
    planes = PlanCuenta.objects.all()
    return render(request, 'planCuenta/tablaPlanCuenta.html', {'planes': planes})

def plan_cuenta_create(request):
    if request.method == 'POST':
        form = PlanCuentaForm(request.POST)
        if form.is_valid():
            form.save()
            return JsonResponse({'success': True, 'message': 'Plan de Cuenta registrado exitosamente.'})
        else:
            return JsonResponse({'success': False, 'errors': form.errors})
    else:
        form = PlanCuentaForm()
        cuentas = PlanCuenta.objects.all()  # Obtén todas las cuentas existentes
        return render(request, 'planCuenta/planCuenta.html', {'form': form, 'cuentas': cuentas})