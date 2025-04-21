from django.http import JsonResponse, HttpResponse, HttpResponseRedirect
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.template import loader
from django.db.models import OuterRef, Subquery, Max
from django.urls import reverse
from django.contrib import messages

from django.template.loader import render_to_string
from .forms import InscripcionForm
from .models import Inscripcion
from apps.persona.models import Personas
from apps.home.models import Cargo, Cohorte, Materia, TipoFormacion, Formacion


def tabla_inscripciones(request):
    return render(request, 'inscripcion/tablaInscripcions.html')
#Honarario
@csrf_exempt
def inscripcion_modal(request):
    if request.method == 'POST':
        form = InscripcionForm(request.POST)
        if form.is_valid():
            form.save()
            return JsonResponse({'success': True, 'message': 'Registro exitoso.'})
        else:
            print(form.errors)  # esto para depurar errores
            errors = {field: error for field, error in form.errors.items()}
            return JsonResponse({'success': False, 'errors': errors})
    else:
        form = InscripcionForm()
    return render(request, 'inscripcion/inscripcion_modal.html', {'form': form})

@csrf_exempt
def edit_inscripcion(request, pk):
    instance = get_object_or_404(Inscripcion, pk=pk)
    if request.method == 'POST':
        form = InscripcionForm(request.POST, instance=instance)
        if form.is_valid():
            form.save()
            return JsonResponse({'success': True, 'message': 'Inscripcion actualizado.'})
        else:
            errors = {field: error for field, error in form.errors.items()}
            return JsonResponse({'success': False, 'errors': errors})
    else:
        form = InscripcionForm(instance=instance)
        # Obtener datos relacionados para los dropdowns
        personas = Personas.objects.all()
        cargos = Cargo.objects.all()
        materias = Materia.objects.all()
        cohortes = Cohorte.objects.all()
        formaciones = Formacion.objects.all()
        tipos_formacion = TipoFormacion.objects.all()
    return render(request, 'inscripcion/editInscripcion.html', {
        'form': form,
        'inscripcion': instance,
        'personas': personas,
        'cargos': cargos,
        'materias': materias,
        'cohortes': cohortes,
        'formaciones': formaciones,
        'tipos_formacion': tipos_formacion
    })

@csrf_exempt
def delete_inscripcion(request, pk):
    instance = get_object_or_404(Inscripcion, pk=pk)
    instance.is_active = False
    instance.save()
    return JsonResponse({'success': True, 'message': 'Eliminación lógica exitosa.'})

@csrf_exempt
def reactivate_inscripcion(request, pk):
    instance = get_object_or_404(Inscripcion, pk=pk)
    instance.is_active = True
    instance.save()
    return JsonResponse({'success': True, 'message': 'Reactivación exitosa.'})

@csrf_exempt
def tabla_inscripciones(request):
    inscripciones = Inscripcion.objects.all()
    return render(request, 'inscripcion/tablaInscripciones.html', {'inscripciones': inscripciones})

@login_required(login_url="/login/")
def pages(request):
    context = {}
    try:
        load_template = request.path.split("/")[-1]

        if load_template == "admin":
            return HttpResponseRedirect(reverse("admin:index"))
       
        if load_template in [ "inscripcion.html", "inscripcion2.html", "tablaContratos.html", "tablaInscripcions.html"]:
            personas = Personas.objects.all()
            context['personas'] = personas
            cargos = Cargo.objects.all()
            context['cargos'] = cargos
            materias = Materia.objects.all()
            context['materias'] = materias
            cohortes = Cohorte.objects.all()
            context['cohortes'] = cohortes
            inscripciones = Inscripcion.objects.all()
            context['inscripciones'] = inscripciones
            formaciones = Formacion.objects.all()
            context['formaciones'] = formaciones  
            tipos_formacion = TipoFormacion.objects.all()
            context['tipos_formacion'] = tipos_formacion
        context["segment"] = load_template



        context["segment"] = load_template
        html_template = loader.get_template("inscripcion/" + load_template)
        return HttpResponse(html_template.render(context, request))



    except loader.TemplateDoesNotExist:
        html_template = loader.get_template("home/page-404.html")
        return HttpResponse(html_template.render(context, request))

    except Exception as e:
        messages.error(request, f'Error inesperado: {e}')
        html_template = loader.get_template("home/page-500.html")
        return HttpResponse(html_template.render(context, request))




