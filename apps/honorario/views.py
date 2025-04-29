from django.http import JsonResponse, HttpResponse, HttpResponseRedirect
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test, permission_required
from django.template import loader
from django.db.models import OuterRef, Subquery, Max
from django.urls import reverse
from django.contrib import messages

from django.template.loader import render_to_string
from .forms import HonorarioForm
from .models import Honorario
from apps.persona.models import Personas
from apps.home.models import Cargo, Cohorte, Materia

#HONORARIO
@login_required(login_url='login')
@permission_required("honorario.add_honorario", raise_exception=True)
def honorario_modal(request):
    if request.method == 'POST':
        form = HonorarioForm(request.POST)
        if form.is_valid():
            form.save()
            return JsonResponse({'success': True, 'message': 'Registro exitoso.'})
        else:
            print(form.errors)  # esto para depurar errores
            errors = {field: error for field, error in form.errors.items()}
            return JsonResponse({'success': False, 'errors': errors})
    else:
        form = HonorarioForm()
    return render(request, 'honorario/honorario_modal.html', {'form': form})

@login_required(login_url='login')
@permission_required("honorario.change_honorario", raise_exception=True)
def edit_honorario(request, pk):
    instance = get_object_or_404(Honorario, pk=pk)
    if request.method == 'POST':
        form = HonorarioForm(request.POST, instance=instance)
        if form.is_valid():
            form.save()
            return JsonResponse({'success': True, 'message': 'Honorario actualizado.'})
        else:
            errors = {field: error for field, error in form.errors.items()}
            return JsonResponse({'success': False, 'errors': errors})
    else:
        form = HonorarioForm(instance=instance)
        # Obtener datos relacionados para los dropdowns
        personas = Personas.objects.all()
        cargos = Cargo.objects.all()
        materias = Materia.objects.all()
        cohortes = Cohorte.objects.all()
        
    return render(request, 'honorario/editHonorario.html', {
        'form': form,
        'honorario': instance,
        'personas': personas,
        'cargos': cargos,
        'materias': materias,
        'cohortes': cohortes
    })

@login_required(login_url='login')
@permission_required("honorario.change_honorario", raise_exception=True)
def delete_honorario(request, pk):
    instance = get_object_or_404(Honorario, pk=pk)
    instance.estadoHonorario = 'INACTIVO'
    instance.save()
    return JsonResponse({'success': True, 'message': 'Eliminación lógica exitosa.'})

@login_required(login_url='login')
@permission_required("honorario.change_honorario", raise_exception=True)
def reactivate_honorario(request, pk):
    instance = get_object_or_404(Honorario, pk=pk)
    instance.estadoHonorario = 'ACTIVO'
    instance.save()
    return JsonResponse({'success': True, 'message': 'Reactivación exitosa.'})

@login_required(login_url='login')
@permission_required("honorario.view_honorario", raise_exception=True)
def tabla_honorarios(request):
    honorarios = Honorario.objects.all()
    return render(request, 'honorario/tablaHonorarios.html', {'honorarios': honorarios})

@login_required(login_url="/login/")
def pages(request):
    context = {}
    try:
        load_template = request.path.split("/")[-1]

        if load_template == "admin":
            return HttpResponseRedirect(reverse("admin:index"))
       
        if load_template in [ "honorario.html", "honorario2.html", "tablaContratos.html", "tablaHonorarios.html"]:
            personas = Personas.objects.all()
            context['personas'] = personas
            cargos = Cargo.objects.all()
            context['cargos'] = cargos
            materias = Materia.objects.all()
            context['materias'] = materias
            cohortes = Cohorte.objects.all()
            context['cohortes'] = cohortes
            honorarios = Honorario.objects.all()
            context['honorarios'] = honorarios
        context["segment"] = load_template



        context["segment"] = load_template
        html_template = loader.get_template("honorario/" + load_template)
        return HttpResponse(html_template.render(context, request))



    except loader.TemplateDoesNotExist:
        html_template = loader.get_template("home/page-404.html")
        return HttpResponse(html_template.render(context, request))

    except Exception as e:
        messages.error(request, f'Error inesperado: {e}')
        html_template = loader.get_template("home/page-500.html")
        return HttpResponse(html_template.render(context, request))




