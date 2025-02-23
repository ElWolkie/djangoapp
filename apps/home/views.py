from django.http import JsonResponse, HttpResponse, HttpResponseRedirect
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.template import loader
from django.urls import reverse
from django.contrib import messages
from .forms import TipoPersonaForm, PersonaForm
from .models import Personas, TipoPersona

@csrf_exempt
def tipo_persona_modal(request):
    if request.method == 'POST':
        form = TipoPersonaForm(request.POST)
        if form.is_valid():
            form.save()
            return JsonResponse({'success': True, 'message': 'Registro exitoso.'})
        else:
            errors = {field: error for field, error in form.errors.items()}
            return JsonResponse({'success': False, 'errors': errors})
    else:
        form = TipoPersonaForm()
    return render(request, 'home/tipo_persona_modal.html', {'form': form})

@login_required(login_url="/login/")
def index(request):
    context = {"segment": "index"}

    html_template = loader.get_template("home/index.html")
    return HttpResponse(html_template.render(context, request))

@login_required(login_url="/login/")
def pages(request):
    context = {}
    try:
        load_template = request.path.split("/")[-1]

        if load_template == "admin":
            return HttpResponseRedirect(reverse("admin:index"))

        if load_template == "persona.html":
            if request.method == 'POST':
                form = PersonaForm(request.POST)
                if form.is_valid():
                    form.save()
                    messages.success(request, 'Registro exitoso.')
                    return redirect('tablaPersona.html')  # Redirige a una URL de éxito
                else:
                    for field, errors in form.errors.items():
                        for error in errors:
                            messages.error(request, f"Error en el campo {field}: {error}")
            else:
                form = PersonaForm()
            context['form'] = form

        if load_template == "tipoPersona.html":
            if request.method == 'POST':
                form = TipoPersonaForm(request.POST)
                if form.is_valid():
                    form.save()
                    messages.success(request, 'Registro exitoso.')
                    return redirect('tipoPersona.html')  # Redirige a una URL de éxito
                else:
                    for field, errors in form.errors.items():
                        for error in errors:
                            messages.error(request, f"Error en el campo {field}: {error}")
            else:
                form = TipoPersonaForm()
            context['form'] = form

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

        html_template = loader.get_template("home/" + load_template)
        return HttpResponse(html_template.render(context, request))

    except loader.TemplateDoesNotExist:
        html_template = loader.get_template("home/page-404.html")
        return HttpResponse(html_template.render(context, request))

    except Exception as e:
        messages.error(request, f'Error inesperado: {e}')
        html_template = loader.get_template("home/page-500.html")
        return HttpResponse(html_template.render(context, request))