from django.http import JsonResponse, HttpResponse, HttpResponseRedirect, HttpResponseForbidden
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, permission_required
from django.template import loader
from django.urls import reverse
from django.contrib import messages
from django.db import transaction

from apps.home.models import Usuarios

from .forms import TipoPersonaForm, PersonaForm
from .models import PersonaTP, Personas, TipoPersona

@login_required(login_url='login')
@permission_required("persona.add_personas", raise_exception=True)
def persona_modal(request):
    tipo_persona = request.GET.get('idTP', '')  # Obtener el parámetro de la URL
    tipo_texto = "Registro"  # Valor por defecto
    
    if tipo_persona == '2':
        tipo_texto = "Cliente"
    elif tipo_persona == '3':
        tipo_texto = "Proveedor"
        
    if request.method == 'POST':
        # 1) Recogemos la lista de tipos seleccionados ANTES de guardar nada
        tipos_ids = request.POST.getlist('tipoPersona')
        if not tipos_ids:
            return JsonResponse({
                'success': False,
                'errors': {'tipoPersona': ['Debes seleccionar al menos un tipo de persona.']}
            })

        # 2) Procesamos el formulario
        form = PersonaForm(request.POST)
        if not form.is_valid():
            return JsonResponse({'success': False, 'errors': form.errors})

        # 3) Todo OK: guardamos dentro de una transacción
        with transaction.atomic():
            persona = form.save()
            # 4) Creamos las relaciones PersonaTP
            for tid in tipos_ids:
                try:
                    tp = TipoPersona.objects.get(pk=int(tid))
                    PersonaTP.objects.create(idPersona=persona, idTP=tp)
                except (TipoPersona.DoesNotExist, ValueError):
                    print(f"⚠️ TipoPersona inválido: {tid}")  # ni interrumpe ni duplica nada

        # 5) Devolvemos éxito
        return JsonResponse({
            'success': True,
            'message': 'Persona registrada exitosamente.',
            'cedula': persona.cedula,
            'persona_id': persona.idPersona
        })

    # Si es GET, devolvemos el template normal
    tipos_persona = TipoPersona.objects.filter(estadoTP='ACTIVO')
    return render(request, 'persona/persona.html', {
        'tipos_persona': tipos_persona,
        'form': PersonaForm(),
        'tipo_texto': tipo_texto,
    })


@login_required(login_url='login')
@permission_required("persona.change_personas", raise_exception=True)
def edit_persona(request, pk):
    persona = get_object_or_404(Personas, pk=pk)

    # 1) Verificar si es superusuario
    persona_is_super = Usuarios.objects.filter(idPersona=persona, is_superuser=True).exists()
    
    # Bloquear acceso si:
    if persona_is_super and not (request.user.is_superuser and request.user.idPersona.idPersona == persona.idPersona):
        return HttpResponseForbidden("No puedes editar superusuarios")

    if request.method == 'POST':
        form = PersonaForm(request.POST, instance=persona)
        if form.is_valid():
            persona = form.save()
            # sincronizar tipos...
            selected = request.POST.getlist('tipoPersona')
            actuales = persona.personatp_set.all()
            actuales_ids = { str(pt.idTP.idTP) for pt in actuales }
            for pt in actuales:
                if str(pt.idTP.idTP) not in selected:
                    pt.delete()
            for tipo_id in selected:
                if tipo_id not in actuales_ids:
                    tp = TipoPersona.objects.get(idTP=tipo_id)
                    PersonaTP.objects.create(idPersona=persona, idTP=tp)

            # Si es AJAX devolvemos JSON
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'message': 'Persona actualizada.',
                    'redirect_url': reverse('tabla_persona')
                })
            # Si NO es AJAX, redirigimos con mensaje
            messages.success(request, 'Persona actualizada.')
            return redirect('tabla_persona')

        # errores de validación
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'errors': form.errors})
        # fallback normal (no AJAX)
        return render(request, 'persona/editPersona.html', {
            'form': form, 'persona': persona,
            'tipos_persona': TipoPersona.objects.filter(estadoTP='ACTIVO'),
            'tipos_seleccionados': list(persona.personatp_set.values_list("idTP", flat=True)),
            'persona_is_super': persona_is_super,
        })

    # GET: renderizamos modal
    tipos_sel = list(persona.personatp_set.values_list("idTP", flat=True))
    form = PersonaForm(instance=persona)
    return render(request, 'persona/editPersona.html', {
        'form': form,
        'persona': persona,
        'tipos_persona': TipoPersona.objects.filter(estadoTP='ACTIVO'),
        'tipos_seleccionados': tipos_sel,
        'persona_is_super': persona_is_super,
    })


@login_required(login_url='login')
@permission_required("persona.change_personas", raise_exception=True)
def delete_persona(request, pk):
    instance = get_object_or_404(Personas, pk=pk)
    instance.estadoPersona = "INACTIVO"
    instance.save()
    return JsonResponse({'success': True, 'message': 'Eliminación exitosa.'})

@login_required(login_url='login')
@permission_required('persona.change_personas', raise_exception=True)
def desactivar_persona(request, pk):
    persona = get_object_or_404(Personas, pk=pk)

    # 1) Si existe un usuario asociado…
    try:
        user = Usuarios.objects.get(idPersona=persona)
        if user.is_superuser:
            return JsonResponse({'success': False,
                                 'message': '❌ No puedes desactivar al superusuario.'})
        if user.is_active:
            return JsonResponse({'success': False,
                                 'message': '❌ Primero desactiva la cuenta de usuario asociada.'})
    except Usuarios.DoesNotExist:
        pass

    if request.method == 'POST':
        persona.estadoPersona = "INACTIVO"
        persona.save()
        msg = f"⛔ {persona.nombres} desactivado"
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'success': True, 'message': msg})
        messages.success(request, msg)
        return redirect(request.POST.get('next', 'tabla_persona'))

    return HttpResponseForbidden()

@login_required(login_url='login')
@permission_required('persona.change_personas', raise_exception=True)
def reactivate_persona(request, pk):
    persona = get_object_or_404(Personas, pk=pk)

    # 1) Impedir reactivar al superusuario
    try:
        user = Usuarios.objects.get(idPersona=persona)
        if user.is_superuser:
            return JsonResponse({'success': False,
                                 'message': '❌ No puedes reactivar al superusuario aquí.'})
    except Usuarios.DoesNotExist:
        pass

    if request.method == 'POST':
        persona.estadoPersona = "ACTIVO"
        persona.save()
        msg = f"✅ {persona.nombres} reactivado"
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'success': True, 'message': msg})
        messages.success(request, msg)
        return redirect(request.POST.get('next', 'tabla_persona'))

    return HttpResponseForbidden()

def seleccionar_tipo_consulta(request):
    tipo = request.GET.get('tipo', '')
    
    # Validar y guardar en sesión
    if tipo in ['2', '3']:
        request.session['tipo_consulta'] = tipo
    return redirect('tabla_persona')

@login_required(login_url='login')
@permission_required("persona.view_personas", raise_exception=True)
def tabla_persona(request):
    tipo_consulta = request.session.get('tipo_consulta', None)
    mostrar = request.GET.get('mostrar_inactivos', 'false') == 'true'

    # Inicializar queryset
    personas = Personas.objects.all()

    # Filtrar por tipo (Cliente/Proveedor)
    if tipo_consulta in ['2', '3']:
        personas = personas.filter(personatp__idTP=tipo_consulta).distinct()

    # Filtrar por estado (activo/inactivo)
    if not mostrar:
        personas = personas.filter(estadoPersona='ACTIVO')

    # Determinar texto para el título
    tipo_texto = "Clientes" if tipo_consulta == '2' else "Proveedores" if tipo_consulta == '3' else "Personas"

    return render(request, 'persona/tablaPersona.html', {
        'personas': personas,
        'mostrar_inactivos': mostrar,
        'tipo_texto': tipo_texto,
    })

#TIPO PERSONA
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




