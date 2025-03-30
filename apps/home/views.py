from django.http import JsonResponse, HttpResponse, HttpResponseRedirect
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.template import loader
from django.db.models import OuterRef, Subquery, Max
from django.urls import reverse
from django.contrib import messages
from .forms import TipoPersonaForm, PersonaForm, TipoFormacionForm, FormacionForm, MateriaForm, CohorteForm, CargoForm, HonorarioForm, RequisitoForm, ServicioForm, TramiteForm, SolicitudForm, DenominacionForm, BancoForm, MonedaForm, TasaForm
from .models import Personas, TipoPersona, PersonaTipoPersona,   TipoFormacion, Formacion, Materia, Cohorte, Cargo, Honorario, Requisito, Servicio, Tramite, Solicitud, Denominacion, Banco, Moneda, Tasa
from django.template.loader import render_to_string
from .forms import TipoPersonaForm, PersonaForm,TipoFormacionForm, FormacionForm, MateriaForm, CohorteForm, CargoForm, HonorarioForm, RequisitoForm, ServicioForm, TramiteForm, SolicitudForm, DenominacionForm, BancoForm, MonedaForm, TasaForm, TipoMovimientoForm, MovimientoForm
from .models import Personas, TipoPersona, PersonaTipoPersona,TipoFormacion, Formacion, Materia, Cohorte, Cargo, Honorario, Requisito, Servicio, Tramite, Solicitud, Denominacion, Banco, Moneda, Tasa,Movimiento, TipoMovimiento

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
    return render(request, 'home/tipoPersona.html', {'form': form})

@csrf_exempt
def formacion_modal(request):
    if request.method == 'POST':
        form = FormacionForm(request.POST)
        if form.is_valid():
            form.save()
            return JsonResponse({'success': True, 'message': 'Registro exitoso.'})
        else:
            errors = {field: error for field, error in form.errors.items()}
            return JsonResponse({'success': False, 'errors': errors})
    else:
        form = FormacionForm()
        tipos_formacion = TipoFormacion.objects.all()  # Obtener los tipos de formación
    return render(request, 'home/formaciones.html', {'form': form, 'tipos_formacion': tipos_formacion})

@csrf_exempt
def edit_formacion(request, pk):
    formacion = get_object_or_404(Formacion, pk=pk)
    if request.method == 'POST':
        form = FormacionForm(request.POST, instance=formacion)
        if form.is_valid():
            form.save()
            return JsonResponse({'success': True, 'message': 'Formación actualizada exitosamente.'})
        else:
            errors = {field: error for field, error in form.errors.items()}
            return JsonResponse({'success': False, 'errors': errors})
    else:
        form = FormacionForm(instance=formacion)
        tipos_formacion = TipoFormacion.objects.all()
        return render(request, 'home/modales/editFormaciones.html', {
            'form': form,
            'formacion': formacion,
            'tipos_formacion': tipos_formacion
        })

@csrf_exempt
def delete_formacion(request, pk):
    instance = get_object_or_404(Formacion, pk=pk)
    instance.estadoFormacion = 'INACTIVO'
    instance.save()
    return JsonResponse({'success': True, 'message': 'Eliminación lógica exitosa.'})

@csrf_exempt
def reactivate_formacion(request, pk):
    instance = get_object_or_404(Formacion, pk=pk)
    instance.estadoFormacion = 'ACTIVO'
    instance.save()
    return JsonResponse({'success': True, 'message': 'Reactivación exitosa.'})

def tabla_formaciones(request):
    if request.user.is_superuser:
        formaciones = Formacion.objects.select_related('idTF').all().distinct  # Usar select_related para optimizar la consulta
    else:
        formaciones = Formacion.objects.select_related('idTF').filter(estadoFormacion='ACTIVO').distinct  # Filtrar solo las activas
    return render(request, 'home/tablaFormaciones.html', {'formaciones': formaciones})

# Tipo de formación
@csrf_exempt
def tipo_formacion_modal(request):
    if request.method == 'POST':
        form = TipoFormacionForm(request.POST)
        if form.is_valid():
            form.save()
            return JsonResponse({'success': True, 'message': 'Registro exitoso.'})
        else:
            errors = {field: error for field, error in form.errors.items()}
            return JsonResponse({'success': False, 'errors': errors})
    else:
        form = TipoFormacionForm()
    return render(request, 'home/tipoFormacion.html', {'form': form})

@csrf_exempt
def edit_tipo_formacion(request, pk):
    instance = get_object_or_404(TipoFormacion, pk=pk)
    if request.method == 'POST':
        form = TipoFormacionForm(request.POST, instance=instance)
        if form.is_valid():
            form.save()
            return JsonResponse({'success': True, 'message': 'Edición exitosa.'})  # Respuesta JSON
        else:
            errors = {field: error for field, error in form.errors.items()}
            return JsonResponse({'success': False, 'errors': errors})  # Respuesta JSON con errores
    else:
        form = TipoFormacionForm(instance=instance)
    return render(request, 'home/modales/editTipoFormacion.html', {'form': form, 'tipoFormacion': instance})

@csrf_exempt
def delete_tipo_formacion(request, pk):
    instance = get_object_or_404(TipoFormacion, pk=pk)
    instance.estadoTipoFormacion = 'INACTIVO'
    instance.save()
    return JsonResponse({'success': True, 'message': 'Eliminación lógica exitosa.'})

@csrf_exempt
def reactivate_tipo_formacion(request, pk):
    instance = get_object_or_404(TipoFormacion, pk=pk)
    instance.estadoTipoFormacion = 'ACTIVO'
    instance.save()
    return JsonResponse({'success': True, 'message': 'Reactivación exitosa.'})

def tabla_tipo_formaciones(request):
    tipo_formaciones = TipoFormacion.objects.all()

    return render(request, 'home/tablaTipoFormaciones.html', {'tipo_formaciones': tipo_formaciones})


#Materia
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
        form = CohorteForm()
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
        form = CargoForm()
    return render(request, 'home/cargo_modal.html', {'form': form})

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
def tipoMovimiento_modal(request):
    if request.method == 'POST':
        form = TipoMovimientoForm(request.POST)
        if form.is_valid():
            form.save()
            return JsonResponse({'success': True, 'message': 'Registro exitoso.'})
        else:
           # print(form.errors)  # esto para depurar errores
            errors = {field: error for field, error in form.errors.items()}
            return JsonResponse({'success': False, 'errors': errors})
    else:
        form = TipoMovimientoForm()
    return render(request, 'home/tipoMovimiento_modal.html', {'form': form})
@csrf_exempt
def movimiento_modal(request):
    if request.method == 'POST':
        form = MovimientoForm(request.POST)
        if form.is_valid():
            form.save()
            return JsonResponse({'success': True, 'message': 'Registro exitoso.'})
        else:
            # Agrega esta línea para depurar errores
            print(form.errors)  # Esto imprimirá los errores en la consola
            errors = {field: error for field, error in form.errors.items()}
            return JsonResponse({'success': False, 'errors': errors})
    else:
        form = MovimientoForm()
      
    return render(request, 'home/movimiento_modal.html')
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
                    # Guardar la persona
                    persona = form.save()

                    # Obtener los tipos de persona seleccionados
                    tipos_persona_ids = request.POST.getlist('tipos_persona')

                    # Asignar los tipos a la persona
                    for tipo_id in tipos_persona_ids:
                        tipo = TipoPersona.objects.get(idTP=tipo_id)
                        PersonaTipoPersona.objects.create(idPersona=persona, idTP=tipo)

                    messages.success(request, 'Registro exitoso.')
                    return redirect('tablaPersona.html')  # Redirige a una URL de éxito
                else:
                    # Mostrar errores de validación del formulario
                    for field, errors in form.errors.items():
                        for error in errors:
                            messages.error(request, f"Error en el campo {field}: {error}")
            else:
                form = PersonaForm()

            # Pasar el formulario y los tipos de persona al contexto
            context['form'] = form
            context['tipopersonas'] = TipoPersona.objects.all()  # Lista de tipos de persona



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

 

        if load_template == "tablaTipoFormaciones.html":
            tipoFormaciones = TipoFormacion.objects.all()
            context['tipoFormaciones'] = tipoFormaciones

        context["segment"] = load_template

        if load_template == "formacion.html":
            formaciones = TipoFormacion.objects.all()
            context['formaciones'] = formaciones
        context["segment"] = load_template


        if load_template == "tablaMaterias.html":
            materias = Materia.objects.all()
            context['materias'] = materias

        context["segment"] = load_template
        
        if load_template in ["materia.html", "tablaFormaciones.html"]:
            formaciones = Formacion.objects.all()
            context['formaciones'] = formaciones
        else:
            context['formaciones'] = None  # O alguna lógica alternativa

        context["segment"] = load_template

        context["segment"] = load_template
        if load_template == "tablaCohortes.html":
            cohortes = Cohorte.objects.all()
            context['cohortes'] = cohortes

        context["segment"] = load_template

        if load_template == "tablaCargos.html":
            cargos = Cargo.objects.all()
            context['cargos'] = cargos

        context["segment"] = load_template

        if load_template in [ "honorario.html", "tablaContratos.html", "tablaHonorarios.html"]:
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
            tipoMovimientos = TipoMovimiento.objects.filter(naturaleza="ingreso")
            context['tipoMovimientos'] = tipoMovimientos

        context["segment"] = load_template
        if load_template == "tablaTipoEgresos.html":
            tipoMovimientos = TipoMovimiento.objects.filter(naturaleza="egreso")
            context['tipoMovimientos'] = tipoMovimientos

        context["segment"] = load_template


        if load_template in [ "tablaIngresos.html", "movimiento.html"]:   
            tipoMovimientos = TipoMovimiento.objects.all()
            context['tipoMovimientos'] = tipoMovimientos
            movimientos = Movimiento.objects.filter(naturaleza="ingreso")
            context['movimientos'] = movimientos
            denominaciones = Denominacion.objects.all()
            context['denominaciones'] = denominaciones   
            bancos = Banco.objects.all()
            context['bancos'] = bancos
           
            # Subconsulta para encontrar la última tasa por moneda
            subconsulta = Tasa.objects.filter(idMoneda=OuterRef('idMoneda')).order_by('-fechaTasa')

            # Obtener todas las monedas con su última tasa
            monedas_con_ultimas_tasas = Moneda.objects.annotate(
                ultima_idTasa=Subquery(subconsulta.values('idTasa')[:1]),  # Último monto de tasa
                ultima_tasa=Subquery(subconsulta.values('montoTasa')[:1]),  # Último monto de tasa
                ultima_fecha=Subquery(subconsulta.values('fechaTasa')[:1])  # Última fecha de tasa
            )

                # Imprimir las monedas y sus últimas tasas en la consola
            for moneda in monedas_con_ultimas_tasas:
                print(f"Moneda: {moneda.nombreMoneda}, Última Tasa: {moneda.ultima_tasa}, Fecha: {moneda.ultima_fecha},  Fecha: {moneda.ultima_idTasa}")

            # Agregar las monedas con sus últimas tasas al contexto
            context['monedas'] = monedas_con_ultimas_tasas

           
        context["segment"] = load_template



        if load_template in [ "tablaEgresos.html", "movimiento.html"]:   
            tipoMovimientos = TipoMovimiento.objects.all()
            context['tipoMovimientos'] = tipoMovimientos
            movimientos = Movimiento.objects.filter(naturaleza="egreso")
            context['movimientos'] = movimientos
            denominaciones = Denominacion.objects.all()
            context['denominaciones'] = denominaciones   
            bancos = Banco.objects.all()
            context['bancos'] = bancos
           
            # Subconsulta para encontrar la última tasa por moneda
            subconsulta = Tasa.objects.filter(idMoneda=OuterRef('idMoneda')).order_by('-fechaTasa')

            # Obtener todas las monedas con su última tasa
            monedas_con_ultimas_tasas = Moneda.objects.annotate(
                ultima_idTasa=Subquery(subconsulta.values('idTasa')[:1]),  # Último monto de tasa
                ultima_tasa=Subquery(subconsulta.values('montoTasa')[:1]),  # Último monto de tasa
                ultima_fecha=Subquery(subconsulta.values('fechaTasa')[:1])  # Última fecha de tasa
            )

                # Imprimir las monedas y sus últimas tasas en la consola
            for moneda in monedas_con_ultimas_tasas:
                print(f"Moneda: {moneda.nombreMoneda}, Última Tasa: {moneda.ultima_tasa}, Fecha: {moneda.ultima_fecha},  Fecha: {moneda.ultima_idTasa}")

            # Agregar las monedas con sus últimas tasas al contexto
            context['monedas'] = monedas_con_ultimas_tasas

           
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