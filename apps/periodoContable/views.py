from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from .models import periodoContable
from .forms import periodoContableForm

def periodo_contable_list(request):
    periodos = periodoContable.objects.all()
    return render(request, 'periodoContable/tablaPeriodoContable.html', {'periodos': periodos})
def periodo_contable_create(request):
    if request.method == 'POST':
        form = periodoContableForm(request.POST)
        if form.is_valid():
            form.save()
            return JsonResponse({'success': True, 'message': 'Periodo Contable registrado exitosamente.'})
        else:
            return JsonResponse({'success': False, 'errors': form.errors})
    else:
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            form = periodoContableForm()
            return render(request, 'periodoContable/periodoContable.html', {'form': form})
        else:
            return JsonResponse({'success': False, 'message': 'Solicitud no válida.'}, status=400)

def periodo_contable_edit(request, id):
    periodo = get_object_or_404(periodoContable, id=id)
    if request.method == 'POST':
        form = periodoContableForm(request.POST, instance=periodo)
        if form.is_valid():
            form.save()
            return JsonResponse({'success': True, 'message': 'Periodo Contable actualizado exitosamente.'})
        else:
            return JsonResponse({'success': False, 'errors': form.errors})
    else:
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            form = periodoContableForm(instance=periodo)
            return render(request, 'periodoContable/periodoContable.html', {'form': form})
        else:
            return JsonResponse({'success': False, 'message': 'Solicitud no válida.'}, status=400)