from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from .models import cuentaBanco
from .forms import cuentaBancoForm
from apps.home.models import Banco, Moneda  # Importar las clases Banco y Moneda
from apps.planCuenta.models import PlanCuenta  # Importar el modelo PlanCuenta

def cuentaBanco_list(request):
    cuentas = cuentaBanco.objects.all()
    return render(request, 'cuentaBanco/tablaCuentaBanco.html', {'cuentas': cuentas})
def cuentaBanco_create(request):
    bancos = Banco.objects.all()  # Consulta los bancos disponibles
    monedas = Moneda.objects.all()  # Consulta las monedas disponibles
    planes = PlanCuenta.objects.filter(estadoPlanCuenta=True)  # Filtrar planes de cuenta activos

    if request.method == 'POST':
        form = cuentaBancoForm(request.POST)
        if form.is_valid():
            form.save()
            # Respuesta JSON en caso de éxito
            return JsonResponse({'success': True, 'message': 'Cuenta bancaria creada exitosamente.'})
        else:
            # Respuesta JSON en caso de error
            return JsonResponse({'success': False, 'errors': form.errors})
    else:
        # Renderizar el formulario para solicitudes normales y AJAX
        form = cuentaBancoForm()
        return render(request, 'cuentaBanco/cuentaBanco.html', {
            'form': form,
            'bancos': bancos,
            'monedas': monedas,
            'planes': planes
        })
def cuentaBanco_edit(request, id):
    cuenta = get_object_or_404(cuentaBanco, id=id)
    if request.method == 'POST':
        form = cuentaBancoForm(request.POST, instance=cuenta)
        if form.is_valid():
            form.save()
            return JsonResponse({'success': True, 'message': 'Cuenta bancaria actualizada exitosamente.'})
        else:
            return JsonResponse({'success': False, 'errors': form.errors})
    else:
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            form = cuentaBancoForm(instance=cuenta)
            return render(request, 'cuentaBanco/cuentaBanco.html', {'form': form})
        else:
            return JsonResponse({'success': False, 'message': 'Solicitud no válida.'}, status=400)