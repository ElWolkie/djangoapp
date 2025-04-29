from django.http import JsonResponse, HttpResponse, HttpResponseRedirect
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, permission_required
from django.template import loader
from django.urls import reverse
from django.contrib import messages
from .forms import SolicitudForm
from .models import Solicitud
from apps.persona.models import Personas
from apps.home.models import Tramite, Servicio

#SOLICITUD
@login_required(login_url='login')
@permission_required("home.add_solicitud", raise_exception=True)
def registrar_solicitud(request):
    if request.method == 'POST':
        form = SolicitudForm(request.POST)
        if form.is_valid():
            form.save()
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': True, 'message': 'Registro exitoso.'})
            messages.success(request, 'Registro exitoso.')
            return redirect('tabla_solicitud')
        else:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                errors = {field: error[0] for field, error in form.errors.items()}
                return JsonResponse({'success': False, 'errors': errors})
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"Error en el campo {field}: {error}")
    
    # Cargar datos para los dropdowns
    tramites = Tramite.objects.all()
    servicios = Servicio.objects.all()
    personas = Personas.objects.all()
    
    return render(request, 'solicitud/solicitud.html', {
        'form': SolicitudForm(),
        'tramites': tramites,
        'servicios': servicios,
        'personas': personas,
        'segment': 'solicitud'
    })

@login_required(login_url='login')
@permission_required("home.change_solicitud", raise_exception=True)
def edit_solicitud(request, pk):
    instance = get_object_or_404(Solicitud, pk=pk)
    if request.method == 'POST':
        form = SolicitudForm(request.POST, instance=instance)
        if form.is_valid():
            form.save()
            return JsonResponse({'success': True, 'message': 'Solicitud actualizada.'})
        else:
            errors = {field: error for field, error in form.errors.items()}
            return JsonResponse({'success': False, 'errors': errors})
    else:
        form = SolicitudForm(instance=instance)
        # Obtener datos necesarios para los dropdowns
        tramites = Tramite.objects.all()  # Agregado
        servicios = Servicio.objects.all()  # Agregado
        personas = Personas.objects.all()
        
    return render(request, 'solicitud/editSolicitud.html', {
        'form': form,
        'solicitud': instance,
        'tramites': tramites,  
        'servicios': servicios,  
        'personas': personas
    })

@login_required(login_url='login')
@permission_required("home.change_solicitud", raise_exception=True)
def delete_solicitud(request, pk):
    instance = get_object_or_404(Solicitud, pk=pk)
    instance.estadoSolicitud = 'INACTIVO'
    instance.save()
    return JsonResponse({'success': True, 'message': 'Eliminación lógica exitosa.'})

@login_required(login_url='login')
@permission_required("home.change_solicitud", raise_exception=True)
def reactivate_solicitud(request, pk):
    instance = get_object_or_404(Solicitud, pk=pk)
    instance.estadoSolicitud = 'ACTIVO'
    instance.save()
    return JsonResponse({'success': True, 'message': 'Reactivación exitosa.'})

@login_required(login_url='login')
@permission_required("home.view_solicitud", raise_exception=True)
def tabla_solicitud(request):
    solicitudes = Solicitud.objects.all()
    return render(request, 'solicitud/tablaSolicitud.html', {'solicitudes': solicitudes})


@login_required(login_url="/login/")
def pages(request):
    context = {}
    try:
        load_template = request.path.split("/")[-1]

        if load_template == "admin":
            return HttpResponseRedirect(reverse("admin:index"))

        # Load data for specific templates
        if load_template in ["solicitud.html", "solicitud2.html", "tablaSolicitud.html"]:
            context.update({
                'solicitudes': Solicitud.objects.all(),
                'tramites': Tramite.objects.all(),
                'servicios': Servicio.objects.all(),
                'personas': Personas.objects.all(),
            })

        context["segment"] = load_template
        html_template = loader.get_template(f"solicitud/{load_template}")
        return HttpResponse(html_template.render(context, request))

    except loader.TemplateDoesNotExist:
        html_template = loader.get_template("home/page-404.html")
        return HttpResponse(html_template.render(context, request))

    except Exception as e:
        messages.error(request, f'Error inesperado: {e}')
        html_template = loader.get_template("home/page-500.html")
        return HttpResponse(html_template.render(context, request))
