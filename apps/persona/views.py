from django.http import JsonResponse, HttpResponse, HttpResponseRedirect
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.template import loader
from django.db.models import OuterRef, Subquery, Max
from django.urls import reverse
from django.contrib import messages

from django.template.loader import render_to_string
from .forms import TipoPersonaForm, PersonaForm
from .models import PersonaTP, Personas, TipoPersona

@login_required(login_url="/login/")
def tipo_persona_modal(request):
    if request.method == 'POST':
        form = TipoPersonaForm(request.POST)
        if form.is_valid():
            form.save()
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({'success': True, 'message': 'Registro exitoso.'})
            messages.success(request, "Tipo de persona registrado correctamente.")
            return redirect('listado_tipos_persona')
        else:
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'errors': form.errors})
        # sólo renderizamos el formulario en GET o si hay errores no-AJAX
    form = TipoPersonaForm()
    return render(request, 'persona/tablaTipoPersona.html', {'form': form})

@csrf_exempt
def edit_persona(request, pk):
    instance = get_object_or_404(Personas, pk=pk)
    if request.method == 'POST':
        form = PersonaForm(request.POST, instance=instance)
        if form.is_valid():
            persona = form.save()
            # Manejar relaciones de tipos de persona
            selected_types = request.POST.getlist('tipoPersona')
            current_types = instance.personatp_set.all()
            
            # Eliminar relaciones no seleccionadas
            for pt in current_types:
                if str(pt.idTP.idTP) not in selected_types:
                    pt.delete()
            
            # Agregar nuevas relaciones
            existing_types = set(str(pt.idTP.idTP) for pt in current_types)
            for tipo_id in selected_types:
                if tipo_id not in existing_types:
                    PersonaTP.objects.create(
                        idPersona=persona, 
                        idTP=TipoPersona.objects.get(idTP=tipo_id)
                    )
            
            return JsonResponse({'success': True, 'message': 'Persona actualizada'})
        return JsonResponse({'success': False, 'errors': form.errors})
    
    # GET request
    tipos_asignados = [str(tp.idTP.idTP) for tp in instance.personatp_set.all()]
    return render(request, 'persona/editPersona.html', {
        'persona': instance,
        'tipopersonas': TipoPersona.objects.all(),
        'tipos_asignados': tipos_asignados
    })
@csrf_exempt
def delete_persona(request, pk):
    instance = get_object_or_404(Personas, pk=pk)
    instance.estadoPersona = "INACTIVO"
    instance.save()
    return JsonResponse({'success': True, 'message': 'Eliminación exitosa.'})

@csrf_exempt
def reactivate_persona(request, pk):
    instance = get_object_or_404(Personas, pk=pk)
    instance.estadoPersona = "ACTIVO"
    instance.save()
    return JsonResponse({'success': True, 'message': 'Reactivación exitosa.'})

@login_required(login_url='/login/')
def registro_tipo_persona(request):
    
    form = TipoPersonaForm() # Crea una instancia vacía del formulario
    return render(request, 'persona/tipoPersona.html', {'form': form})

@login_required(login_url='/login/')
def listado_tipos_persona(request):
    # Leemos el parámetro ?mostrar_inactivos=true/false
    mostrar = request.GET.get('mostrar_inactivos', 'false').lower() == 'true'

    if mostrar:
        tipopersonas = TipoPersona.objects.all().order_by('-fechaTP', 'nombreTP')
    else:
        tipopersonas = TipoPersona.objects.filter(
            estadoTP__iexact='ACTIVO'
        ).order_by('-fechaTP', 'nombreTP')

    context = {
        'tipopersonas': tipopersonas,
        'mostrar_inactivos': mostrar
    }
    return render(request, 'persona/tablaTipoPersona.html', context)

@login_required(login_url="/login/")
def edit_tipo_persona(request, pk):
    tp = get_object_or_404(TipoPersona, pk=pk)
    if request.method == 'POST':
        form = TipoPersonaForm(request.POST, instance=tp)
        if form.is_valid():
            form.save()
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({'success': True, 'message': 'Edición exitosa.'})
            messages.success(request, "Tipo de persona actualizado correctamente.")
            return redirect('listado_tipos_persona')
        else:
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'errors': form.errors})
    else:
        form = TipoPersonaForm(instance=tp)
    return render(request, 'persona/editTipoPersona.html', {'form': form, 'tipopersona': tp})

@login_required(login_url="/login/")
def delete_tipo_persona(request, pk):
    tp = get_object_or_404(TipoPersona, pk=pk)
    tp.estadoTP = 'INACTIVO'
    tp.save()
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({'success': True})
    messages.warning(request)
    return redirect('listado_tipos_persona')

@login_required(login_url="/login/")
def reactivate_tipo_persona(request, pk):
    tp = get_object_or_404(TipoPersona, pk=pk)
    tp.estadoTP = 'ACTIVO'
    tp.save()
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({'success': True})
    messages.success(request)
    return redirect('listado_tipos_persona')

@login_required(login_url="/login/")
def solicitud_view(request):
     return render(request, 'home/solicitud.html')

@login_required(login_url="/login/")
def pages(request):
    context = {}
    try:
        load_template = request.path.split("/")[-1]

        if load_template == "admin":
            return HttpResponseRedirect(reverse("admin:index"))
        if load_template == "persona.html":
            if request.method == 'POST':
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':  # Verificar si es una solicitud AJAX
                    form = PersonaForm(request.POST)
                    if form.is_valid():
                        # Guardar la persona
                        persona = form.save()

                        # Obtener los tipos de persona seleccionados
                        tipos_persona_ids = request.POST.getlist('tipoPersona')

                        # Asignar los tipos a la persona
                        for tipo_id in tipos_persona_ids:
                            tipo = TipoPersona.objects.get(idTP=tipo_id)
                            PersonaTP.objects.create(idPersona=persona, idTP=tipo)

                        return JsonResponse({'success': True, 'message': 'Registro exitoso.'})
                    else:
                        # Devolver errores de validación
                        errors = {field: error[0] for field, error in form.errors.items()}
                        return JsonResponse({'success': False, 'errors': errors})
                else:
                    form = PersonaForm()
            else:
                form = PersonaForm()
            # Pasar el formulario y los tipos de persona al contexto
            context['form'] = form
            context['tipopersonas'] = TipoPersona.objects.all()  # Lista de tipos de persona
        
        if load_template == "tablaPersona.html":
            personas = Personas.objects.all()
            context['personas'] = personas

     
        if load_template == "tablaTipoPersona.html":
            tipopersonas = TipoPersona.objects.all()
            context['tipopersonas'] = tipopersonas

        context["segment"] = load_template
        
        if load_template == "persona.html":
            tipopersonas = TipoPersona.objects.all()
            context['tipopersonas'] = tipopersonas

        context["segment"] = load_template
        html_template = loader.get_template("persona/" + load_template)
        return HttpResponse(html_template.render(context, request))

    except loader.TemplateDoesNotExist:
        html_template = loader.get_template("home/page-404.html")
        return HttpResponse(html_template.render(context, request))

    except Exception as e:
        messages.error(request, f'Error inesperado: {e}')
        html_template = loader.get_template("home/page-500.html")
        return HttpResponse(html_template.render(context, request))




