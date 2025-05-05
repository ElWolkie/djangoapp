from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from .models import cuentaBanco
from .forms import cuentaBancoForm
from apps.home.models import Banco, Moneda  # Importar las clases Banco y Moneda

def cuentaBanco_list(request):
    cuentas = cuentaBanco.objects.all()
    return render(request, 'cuentaBanco/tablaCuentaBanco.html', {'cuentas': cuentas})

def cuentaBanco_create(request):
    bancos = Banco.objects.all()  # Consulta los bancos disponibles
    if request.method == 'POST':
        form = cuentaBancoForm(request.POST)
        if form.is_valid():
            form.save()
            # Redirigir a la lista después de guardar
            return redirect('cuentaBanco_list')
        else:
            # Si hay errores, renderizar el formulario con errores
            return render(request, 'cuentaBanco/cuentaBanco.html', {'form': form, 'bancos': bancos})
    else:
        # Manejar solicitudes GET normales
        form = cuentaBancoForm()
        return render(request, 'cuentaBanco/cuentaBanco.html', {'form': form, 'bancos': bancos})
    
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