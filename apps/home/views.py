from django.http import JsonResponse, HttpResponse, HttpResponseRedirect
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import render, redirect
from django.contrib.auth.models import User
from django.template import loader
from django.urls import reverse
from django.contrib import messages

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny

from .forms import TipoPersonaForm, PersonaForm, TipoOfertaForm, OfertaForm,CuotaForm, MateriaForm, CohorteForm, CargoForm, ContratoForm, HonorarioForm, RequisitoForm, ServicioForm, TramiteForm, SolicitudForm, DenominacionForm, BancoForm, MonedaForm, TasaForm, TipoIngresoForm, TipoEgresoForm
from .models import Personas, TipoPersona,  Cuota, TipoOferta, Ofertas, Materia, Cohorte, Cargo, Contrato, Honorario, Requisito, Servicio, Tramite, Solicitud, Denominacion, Banco, Moneda, Tasa, TipoIngreso, TipoEgreso

@csrf_exempt
def index_view(request):
    # Renderiza el template SIN verificar autenticación tradicional
    return render(request, "home/index.html")

@api_view(['POST'])
@permission_classes([AllowAny])  # Permitir acceso sin autenticación (solo para pruebas)
@csrf_exempt
def tipo_persona_modal(request):
    if request.method == 'POST':
        form = TipoPersonaForm(request.POST)
        if form.is_valid():
            tipo_persona = form.save()
            return JsonResponse({
                'success': True,
                'message': 'Registro exitoso.',
                'idTP': tipo_persona.idTP,
                'nombreTP': tipo_persona.nombreTP
            })
        else:
            errors = {field: error[0] for field, error in form.errors.items()}
            return JsonResponse({'success': False, 'errors': errors})
    else:
        return JsonResponse({'success': False, 'message': 'Método no permitido.'})
    

def register_view(request):
    if request.method == 'POST':
        username = request.POST['username']
        email = request.POST['email']
        password = request.POST['password']

        # Verifica que el usuario no exista ya
        if User.objects.filter(username=username).exists():
            messages.error(request, 'El nombre de usuario ya está en uso.')
        elif User.objects.filter(email=email).exists():
            messages.error(request, 'El correo electrónico ya está en uso.')
        else:
            user = User.objects.create_user(username=username, email=email, password=password)
            user.save()
            messages.success(request, 'Registro exitoso. Ahora puede iniciar sesión.')
            return redirect('login')

    return render(request, 'registration/register.html')


@csrf_exempt
def oferta_modal(request):
    if request.method == 'POST':
        form = OfertaForm(request.POST)
        if form.is_valid():
            form.save()
            return JsonResponse({'success': True, 'message': 'Registro exitoso.'})
        else:
            errors = {field: error for field, error in form.errors.items()}
            return JsonResponse({'success': False, 'errors': errors})
    else:
        form = OfertaForm()
    return render(request, 'home/oferta_modal.html', {'form': form})

@csrf_exempt
def tipo_oferta_modal(request):
    if request.method == 'POST':
        form = TipoOfertaForm(request.POST)
        if form.is_valid():
            form.save()
            return JsonResponse({'success': True, 'message': 'Registro exitoso.'})
        else:
            errors = {field: error for field, error in form.errors.items()}
            return JsonResponse({'success': False, 'errors': errors})
    else:
        form = TipoOfertaForm()
    return render(request, 'home/tipo_oferta_modal.html', {'form': form})

@csrf_exempt
def cuota_modal(request):
    if request.method == 'POST':
        form = CuotaForm(request.POST)
        if form.is_valid():
            form.save()
            return JsonResponse({'success': True, 'message': 'Registro exitoso.'})
        else:
            errors = {field: error for field, error in form.errors.items()}
            return JsonResponse({'success': False, 'errors': errors})
    else:
        form = CuotaForm()
    return render(request, 'home/cuota_modal.html', {'form': form})

@csrf_exempt
def materia_modal(request):
    if request.method == 'POST':
        form = MateriaForm(request.POST)
        if form.is_valid():
            form.save()
            return JsonResponse({'success': True, 'message': 'Registro exitoso.'})
        else:
            errors = {field: error for field, error in form.errors.items()}
            return JsonResponse({'success': False, 'errors': errors})
    else:
        form = MateriaForm()
    return render(request, 'home/materia_modal.html', {'form': form})

@csrf_exempt
def cohorte_modal(request):
    if request.method == 'POST':
        form = CohorteForm(request.POST)
        if form.is_valid():
            form.save()
            return JsonResponse({'success': True, 'message': 'Registro exitoso.'})
        else:
            errors = {field: error for field, error in form.errors.items()}
            return JsonResponse({'success': False, 'errors': errors})
    else:
        form = CuotaForm()
    return render(request, 'home/cohorte_modal.html', {'form': form})


@csrf_exempt
def cargo_modal(request):
    if request.method == 'POST':
        form = CargoForm(request.POST)
        if form.is_valid():
            form.save()
            return JsonResponse({'success': True, 'message': 'Registro exitoso.'})
        else:
            errors = {field: error for field, error in form.errors.items()}
            return JsonResponse({'success': False, 'errors': errors})
    else:
        form = CuotaForm()
    return render(request, 'home/cargo_modal.html', {'form': form})
@csrf_exempt
def contrato_modal(request):
    if request.method == 'POST':
        form = ContratoForm(request.POST)
        if form.is_valid():
            form.save()
            return JsonResponse({'success': True, 'message': 'Registro exitoso.'})
        else:
            print(form.errors)  # esto para depurar errores
            errors = {field: error for field, error in form.errors.items()}
            return JsonResponse({'success': False, 'errors': errors})
    else:
        form = ContratoForm()
    return render(request, 'home/contrato_modal.html', {'form': form})

@csrf_exempt
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
    return render(request, 'home/honorario_modal.html', {'form': form})

@csrf_exempt
def requisito_modal(request):
    if request.method == 'POST':
        form = RequisitoForm(request.POST)
        if form.is_valid():
            form.save()
            return JsonResponse({'success': True, 'message': 'Registro exitoso.'})
        else:
            print(form.errors)  # esto para depurar errores
            errors = {field: error for field, error in form.errors.items()}
            return JsonResponse({'success': False, 'errors': errors})
    else:
        form = RequisitoForm()
    return render(request, 'home/requisito_modal.html', {'form': form})


@csrf_exempt
def servicio_modal(request):
    if request.method == 'POST':
        form = ServicioForm(request.POST)
        if form.is_valid():
            form.save()
            return JsonResponse({'success': True, 'message': 'Registro exitoso.'})
        else:
            print(form.errors)  # esto para depurar errores
            errors = {field: error for field, error in form.errors.items()}
            return JsonResponse({'success': False, 'errors': errors})
    else:
        form = ServicioForm()
    return render(request, 'home/servicio_modal.html', {'form': form})


@csrf_exempt
def tramite_modal(request):
    if request.method == 'POST':
        form = TramiteForm(request.POST)
        if form.is_valid():
            form.save()
            return JsonResponse({'success': True, 'message': 'Registro exitoso.'})
        else:
            print(form.errors)  # esto para depurar errores
            errors = {field: error for field, error in form.errors.items()}
            return JsonResponse({'success': False, 'errors': errors})
    else:
        form = TramiteForm()
    return render(request, 'home/tramite_modal.html', {'form': form})

@csrf_exempt
def denominacion_modal(request):
    if request.method == 'POST':
        form = DenominacionForm(request.POST)
        if form.is_valid():
            form.save()
            return JsonResponse({'success': True, 'message': 'Registro exitoso.'})
        else:
            print(form.errors)  # esto para depurar errores
            errors = {field: error for field, error in form.errors.items()}
            return JsonResponse({'success': False, 'errors': errors})
    else:
        form = DenominacionForm()
    return render(request, 'home/denominacion_modal.html', {'form': form})


@csrf_exempt
def banco_modal(request):
    if request.method == 'POST':
        form = BancoForm(request.POST)
        if form.is_valid():
            form.save()
            return JsonResponse({'success': True, 'message': 'Registro exitoso.'})
        else:
           # print(form.errors)  # esto para depurar errores
            errors = {field: error for field, error in form.errors.items()}
            return JsonResponse({'success': False, 'errors': errors})
    else:
        form = BancoForm()
    return render(request, 'home/banco_modal.html', {'form': form})

@csrf_exempt
def moneda_modal(request):
    if request.method == 'POST':
        form = MonedaForm(request.POST)
        if form.is_valid():
            form.save()
            return JsonResponse({'success': True, 'message': 'Registro exitoso.'})
        else:
           # print(form.errors)  # esto para depurar errores
            errors = {field: error for field, error in form.errors.items()}
            return JsonResponse({'success': False, 'errors': errors})
    else:
        form = MonedaForm()
    return render(request, 'home/moneda_modal.html', {'form': form})


@csrf_exempt
def tasa_modal(request):
    if request.method == 'POST':
        form = TasaForm(request.POST)
        if form.is_valid():
            form.save()
            return JsonResponse({'success': True, 'message': 'Registro exitoso.'})
        else:
           # print(form.errors)  # esto para depurar errores
            errors = {field: error for field, error in form.errors.items()}
            return JsonResponse({'success': False, 'errors': errors})
    else:
        form = TasaForm()
    return render(request, 'home/tasa_modal.html', {'form': form})

@csrf_exempt
def tipoIngreso_modal(request):
    if request.method == 'POST':
        form = TipoIngresoForm(request.POST)
        if form.is_valid():
            form.save()
            return JsonResponse({'success': True, 'message': 'Registro exitoso.'})
        else:
           # print(form.errors)  # esto para depurar errores
            errors = {field: error for field, error in form.errors.items()}
            return JsonResponse({'success': False, 'errors': errors})
    else:
        form = TipoIngresoForm()
    return render(request, 'home/tipoIngreso_modal.html', {'form': form})

@csrf_exempt
def tipoEgreso_modal(request):
    if request.method == 'POST':
        form = TipoEgresoForm(request.POST)
        if form.is_valid():
            form.save()
            return JsonResponse({'success': True, 'message': 'Registro exitoso.'})
        else:
           # print(form.errors)  # esto para depurar errores
            errors = {field: error for field, error in form.errors.items()}
            return JsonResponse({'success': False, 'errors': errors})
    else:
        form = TipoEgresoForm()
    return render(request, 'home/tipoEgreso_modal.html', {'form': form})


# @login_required(login_url="/login/")
def index(request):
    context = {"segment": "index"}

    html_template = loader.get_template("home/index.html")
    return HttpResponse(html_template.render(context, request))

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



        if load_template == "solicitud.html":
            if request.method == 'POST':
                form = SolicitudForm(request.POST)
                if form.is_valid():
                    form.save()
                    messages.success(request, 'Registro exitoso.')
                    return redirect('solicitud.html')  # Redirige a una URL de éxito
                else:
                    for field, errors in form.errors.items():
                        for error in errors:
                            messages.error(request, f"Error en el campo {field}: {error}")
            else:
                form = SolicitudForm()
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

        if load_template == "tablaCuotas.html":
            cuotas = Cuota.objects.all()
            context['cuota'] = cuotas

        context["segment"] = load_template


        if load_template == "tablaTipoOfertas.html":
            tipoOfertas = TipoOferta.objects.all()
            context['tipoOferta'] = tipoOfertas

        context["segment"] = load_template


        if load_template == "oferta.html":
            tipoOfertas = TipoOferta.objects.all()
            context['tipoOferta'] = tipoOfertas
        context["segment"] = load_template

        if load_template == "tipoOferta.html":
            cuotas = Cuota.objects.all()
            context['cuota'] = cuotas
        context["segment"] = load_template

        if load_template == "tablaMaterias.html":
            materias = Materia.objects.all()
            context['materias'] = materias

        context["segment"] = load_template
        
        if load_template in ["materia.html", "tablaOfertas.html"]:
            ofertas = Ofertas.objects.all()
            context['ofertas'] = ofertas
        else:
            context['ofertas'] = None  # O alguna lógica alternativa

        context["segment"] = load_template
        if load_template == "tablaCohortes.html":
            cohortes = Cohorte.objects.all()
            context['cohortes'] = cohortes

        context["segment"] = load_template

        if load_template == "tablaCargos.html":
            cargos = Cargo.objects.all()
            context['cargos'] = cargos

        context["segment"] = load_template

        if load_template in [ "contrato.html", "honorario.html", "tablaContratos.html", "tablaHonorarios.html"]:
            personas = Personas.objects.all()
            context['personas'] = personas
            cargos = Cargo.objects.all()
            context['cargos'] = cargos
            materias = Materia.objects.all()
            context['materias'] = materias
            cohortes = Cohorte.objects.all()
            context['cohortes'] = cohortes
            contratos = Contrato.objects.all()
            context['contratos'] = contratos
            honorarios = Honorario.objects.all()
            context['honorarios'] = honorarios
        context["segment"] = load_template



        if load_template == "tablaRequisitos.html":
            requisitos = Requisito.objects.all()
            context['requisitos'] = requisitos

        context["segment"] = load_template


        if load_template == "tablaServicios.html":
            servicios = Servicio.objects.all()
            context['servicios'] = servicios

        context["segment"] = load_template


        if load_template == "tablaTramites.html":
            tramites = Tramite.objects.all()
            context['tramites'] = tramites

        context["segment"] = load_template


        if load_template in [ "solicitud.html", "tablaSolicitud.html"]:
            solicitudes = Solicitud.objects.all()
            context['solicitudes'] = solicitudes
            tramites = Tramite.objects.all()
            context['tramites'] = tramites
            servicios = Servicio.objects.all()
            context['servicios'] = servicios
            personas = Personas.objects.all()
            context['personas'] = personas
        context["segment"] = load_template

        if load_template == "tablaDenominaciones.html":
            denominaciones = Denominacion.objects.all()
            context['denominaciones'] = denominaciones

        context["segment"] = load_template

        if load_template == "tablaBancos.html":
            bancos = Banco.objects.all()
            context['bancos'] = bancos

        context["segment"] = load_template

        if load_template == "tablaMonedas.html":
            monedas = Moneda.objects.all()
            context['monedas'] = monedas

        context["segment"] = load_template

        if load_template in [ "tablaTasas.html", "tasa.html"]:
            tasas = Tasa.objects.all()
            context['tasas'] = tasas
            monedas = Moneda.objects.all()
            context['monedas'] = monedas
        context["segment"] = load_template
        
        if load_template == "tablaTipoIngresos.html":
            tipoIngresos = TipoIngreso.objects.all()
            context['tipoIngresos'] = tipoIngresos

        context["segment"] = load_template
       
        if load_template == "tablaTipoEgresos.html":
            tipoEgresos = TipoEgreso.objects.all()
            context['tipoEgresos'] = tipoEgresos

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