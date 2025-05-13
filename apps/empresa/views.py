from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from .models import empresa
from .forms import empresaForm

def empresa_list(request):
    empresas = empresa.objects.all()
    return render(request, 'empresa/tablaEmpresa.html', {'empresas': empresas})

def empresa_create(request):
    if request.method == 'POST':
        form = empresaForm(request.POST)
        if form.is_valid():
            form.save()
            return JsonResponse({'success': True, 'message': 'Empresa registrada exitosamente.'})
        else:
            return JsonResponse({'success': False, 'errors': form.errors})
    else:
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            form = empresaForm()
            return render(request, 'empresa/empresa.html', {'form': form})
        else:
            return JsonResponse({'success': False, 'message': 'Solicitud no válida.'}, status=400)

def empresa_edit(request, id):
    empresa = get_object_or_404(empresa, id=id)
    if request.method == 'POST':
        form = empresaForm(request.POST, instance=empresa)
        if form.is_valid():
            form.save()
            return JsonResponse({'success': True, 'message': 'Empresa actualizada exitosamente.'})
        else:
            return JsonResponse({'success': False, 'errors': form.errors})
    else:
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            form = empresaForm(instance=empresa)
            return render(request, 'empresa/empresa.html', {'form': form})
        else:
            return JsonResponse({'success': False, 'message': 'Solicitud no válida.'}, status=400)