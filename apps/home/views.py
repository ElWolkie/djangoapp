from django.http import HttpResponse, HttpResponseRedirect
from django.template import loader
from django.urls import reverse
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .forms import PersonaForm

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
                    return redirect('persona.html')  # Redirige a una URL de éxito
                else:
                    for field, errors in form.errors.items():
                        for error in errors:
                            messages.error(request, f"Error en el campo {field}: {error}")
            else:
                form = PersonaForm()
            context['form'] = form

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