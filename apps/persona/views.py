from datetime import datetime
from django.http import JsonResponse, HttpResponse, HttpResponseRedirect, HttpResponseForbidden
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, permission_required
from django.template import loader
from django.urls import reverse
from django.contrib import messages
from django.db import transaction
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import Table, TableStyle
from reportlab.pdfgen import canvas
from apps.home.models import Usuarios, Configuracion
from .forms import TipoPersonaForm, PersonaForm
from .models import PersonaTP, Personas, TipoPersona
import os

@login_required(login_url='login')
@permission_required("persona.add_personas", raise_exception=True)
def persona_modal(request):
    tipo_persona = request.GET.get('idTP', '')   # vendrá '1', '2', '3' o ''
    tipo_texto = "Registro"

    if tipo_persona == '1':
        tipo_texto = "Usuario"
    elif tipo_persona == '2':
        tipo_texto = "Cliente"
    elif tipo_persona == '3':
        tipo_texto = "Proveedor"

    if request.method == 'POST':
        # Combinar tipo y número de cédula
        tipo_cedula = request.POST.get('tipo_cedula', 'V')
        numero_cedula = request.POST.get('numero_cedula', '')
        cedula_completa = f"{tipo_cedula}-{numero_cedula}"
        
        # Crear copia mutable del POST
        data = request.POST.copy()
        data['cedula'] = cedula_completa
        
        # 1) Recogemos la lista de tipos seleccionados
        tipos_ids = data.getlist('tipoPersona')
        if not tipos_ids:
            return JsonResponse({
                'success': False,
                'errors': {'tipoPersona': ['Debes seleccionar al menos un tipo de persona.']}
            })

        # 2) Procesamos el formulario
        form = PersonaForm(data)
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
                    print(f"⚠️ TipoPersona inválido: {tid}")

        # 5) Devolvemos éxito con la cédula completa
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
                                 'message': 'No puedes desactivar al superusuario.'})
        if user.is_active:
            return JsonResponse({'success': False,
                                 'message': 'Primero desactiva la cuenta de usuario asociada.'})
    except Usuarios.DoesNotExist:
        pass

    if request.method == 'POST':
        persona.estadoPersona = "INACTIVO"
        persona.save()
        msg = f"{persona.nombres} {persona.apellidos} Desactivado correctamente."
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
                                 'message': 'No puedes reactivar al superusuario aquí.'})
    except Usuarios.DoesNotExist:
        pass

    if request.method == 'POST':
        persona.estadoPersona = "ACTIVO"
        persona.save()
        msg = f"{persona.nombres} {persona.apellidos} Reactivado correctamente."
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'success': True, 'message': msg})
        messages.success(request, msg)
        return redirect(request.POST.get('next', 'tabla_persona'))

    return HttpResponseForbidden()

def seleccionar_tipo_consulta(request):
    tipo = request.GET.get('tipo', '')
    
    # Validar y guardar en sesión
    if tipo in ['1', '2', '3']:
        request.session['tipo_consulta'] = tipo
    return redirect('tabla_persona')

@login_required(login_url='login')
@permission_required("persona.view_personas", raise_exception=True)
def tabla_persona(request):
    tipo_consulta = request.session.get('tipo_consulta', None)
    mostrar = request.GET.get('mostrar_inactivos', 'false') == 'true'

    # Query inicial
    qs = Personas.objects.all()

    # Filtrar por tipo (Cliente/Proveedor/Usuario)
    if tipo_consulta in ['1', '2', '3']:
        qs = qs.filter(personatp__idTP=tipo_consulta).distinct()

    # Si está pidiendo mostrar inactivos, comprobamos si existen inactivos
    if mostrar:
        # ¿hay al menos un registro inactivo en el queryset ya filtrado por tipo?
        hay_inactivos = qs.exclude(estadoPersona='ACTIVO').exists()
        if not hay_inactivos:
            # Notificar al usuario que no hay inactivos (se mostrará en la plantilla)
            messages.info(request, 'No hay personas inactivas para mostrar.')
        # dejamos qs tal cual (muestra activos + inactivos)
        personas = qs
    else:
        # Solo mostrar activos
        personas = qs.filter(estadoPersona='ACTIVO')

    # Determinar texto para el título
    tipo_texto = "Usuarios" if tipo_consulta == '1' else "Clientes" if tipo_consulta == '2' else "Proveedores" if tipo_consulta == '3' else "Personas"

    return render(request, 'persona/tablaPersona.html', {
        'personas': personas,
        'mostrar_inactivos': mostrar,
        'tipo_texto': tipo_texto,
        'tipo_consulta': tipo_consulta,
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

    # Query base (con orden original)
    qs = TipoPersona.objects.all().order_by('-fechaTP', 'nombreTP')

    # Si no pedimos inactivos, filtramos solo activos (case-insensitive)
    if not mostrar:
        qs = qs.filter(estadoTP__iexact='ACTIVO').order_by('-fechaTP', 'nombreTP')

    # Mensajes informativos
    if mostrar:
        # ¿hay inactivos dentro del queryset actual?
        hay_inactivos = qs.exclude(estadoTP__iexact='ACTIVO').exists()
        if not hay_inactivos:
            messages.info(request, 'No hay tipos de persona inactivos para mostrar.')
    else:
        if not qs.exists():
            messages.info(request, 'No hay tipos de persona activos para mostrar.')

    context = {
        'tipopersonas': qs,
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

@login_required(login_url='login')
def reporte_personas_pdf(request):
    # Obtener el tipo de persona desde la URL
    tipo_filtro = request.GET.get('tipo', '')
    
    # Manejo de parámetros de paginación
    start = int(request.GET.get('start', 1))
    end = int(request.GET.get('end', 0))
    
    # Filtrar personas según el tipo
    if tipo_filtro:
        personas_list = list(Personas.objects.filter(
            personatp__idTP=tipo_filtro
        ).distinct().select_related())
    else:
        personas_list = list(Personas.objects.all().select_related())
    
    if end == 0 or end > len(personas_list):
        end = len(personas_list)
    personas = personas_list[start-1:end]

    # Configuración inicial del PDF
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'inline; filename="reporte_personas.pdf"'
    p = canvas.Canvas(response, pagesize=letter)
    width, height = letter
    logo_width, logo_height, logo_margin = 80, 80, 15  # Tamaño reducido del logo

    # Obtener configuración institucional
    config = Configuracion.objects.order_by('-fechaConfiguracion').first()
    logo_path = config.logo.path if config and config.logo else None
    firma_path = config.firma.path if config and config.firma else None
    nombre_institucion = config.nombreInstitucion if config else "Institución"
    rif_institucion = config.rif if config else ""
    direccion1 = "AV. ALBERTO RAVELL CON AV. INTERCOMUNAL JOSE ANTONIO PAEZ"
    direccion2 = "LOCAL UPTYAB, INDEPENDENCIA – EDO YARACUY"

    # Definir márgenes seguros
    min_margin = 30
    safe_left = min_margin
    safe_right = width - min_margin
    safe_width = safe_right - safe_left
    safe_center = width / 2

    # Determinar el título según el tipo
    titulo = "REPORTE DE PERSONAS"
    if tipo_filtro:
        if tipo_filtro == "1":  # Ajusta estos valores según tus tipos
            titulo = "REPORTE DE USUARIOS"
        elif tipo_filtro == "2":
            titulo = "REPORTE DE CLIENTES"
        elif tipo_filtro == "3":
            titulo = "REPORTE DE PROVEEDORES"

    # Funciones para encabezado y pie de página
    def draw_header():
        # Logo a la derecha
        if logo_path and os.path.exists(logo_path):
            p.drawImage(
                logo_path,
                width - logo_width - logo_margin,
                height - logo_height - logo_margin,
                width=logo_width,
                height=logo_height,
                preserveAspectRatio=True,
                mask='auto'
            )
        
        # Texto institucional a la izquierda
        text_top = height - logo_margin - 15
        p.setFont("Helvetica-Bold", 10)
        p.drawString(min_margin, text_top, nombre_institucion)
        p.drawString(min_margin, text_top - 15, f"RIF: {rif_institucion}")
        p.drawString(min_margin, text_top - 30, direccion1)
        p.drawString(min_margin, text_top - 45, direccion2)
        
        # Título centrado
        p.setFont("Helvetica-Bold", 11)
        p.drawCentredString(safe_center, text_top - 85, titulo)

    def draw_footer():
        # Firma centrada en el pie de página
        if firma_path and os.path.exists(firma_path):
            p.drawImage(
                firma_path,
                width/2 - 50,
                60,
                width=100,
                height=50,
                preserveAspectRatio=True,
                mask='auto'
            )
            p.setFont("Helvetica-Oblique", 9)
            p.drawCentredString(width/2, 35, "Firma autorizada")
        
        # Fecha de generación
        p.setFont("Helvetica", 8)
        fecha_generacion = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        p.drawString(min_margin, 20, f"Generado el: {fecha_generacion}")

    # Preparar datos de la tabla
    headers = ["CÉDULA", "NOMBRES", "APELLIDOS", "TELÉFONO", "DIRECCIÓN", "CORREO", "ESTADO"]
    data = [headers]
    
    for persona in personas:
        data.append([
            persona.cedula or "—",
            persona.nombres or "—",
            persona.apellidos or "—",
            persona.telefono or "—",
            persona.direccion or "—",
            persona.correo or "—",
            persona.estadoPersona or "—"
        ])
    
    # Configuración de la tabla con espacios aumentados
    col_widths = [60, 80, 80, 60, 120, 100, 50]  # Anchos ajustados
    table_width = sum(col_widths)
    
    # Espaciado vertical aumentado
    header_height = 150
    footer_height = 100
    row_height = 22
    cell_padding = 4
    
    # Calcular espacio disponible
    available_height = height - header_height - footer_height
    max_rows_per_page = max(1, int(available_height // row_height))
    total_rows = len(data) - 1
    page = 0

    # Generar páginas
    for start_row in range(0, total_rows, max_rows_per_page):
        end_row = min(start_row + max_rows_per_page, total_rows)
        page_data = [data[0]] + data[start_row + 1:end_row + 1]
        
        if page > 0:
            p.showPage()
        
        draw_header()
        y_position = height - header_height
        
        # Centrar tabla horizontalmente
        table_x = safe_left + (safe_width - table_width) / 2
        table = Table(page_data, colWidths=col_widths, rowHeights=[row_height]*len(page_data))
        
        # Estilo de la tabla con más espacio
        table_style = TableStyle([
            # Encabezado
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#fe8330")),
            ('TEXTCOLOR', (0,0), (-1,0), colors.white),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('FONTSIZE', (0,0), (-1,0), 8),
            ('ALIGN', (0,0), (-1,0), 'CENTER'),
            ('VALIGN', (0,0), (-1,0), 'MIDDLE'),
            ('BOTTOMPADDING', (0,0), (-1,0), cell_padding),
            
            # Cuerpo de la tabla
            ('FONTSIZE', (0,1), (-1,-1), 7),
            ('ALIGN', (0,1), (-1,-1), 'CENTER'),
            ('ALIGN', (1,1), (5,-1), 'LEFT'),  # Alinear texto a izquierda para algunas columnas
            ('VALIGN', (0,1), (-1,-1), 'MIDDLE'),
            ('BACKGROUND', (0,1), (-1,-1), colors.whitesmoke),
            ('GRID', (0,0), (-1,-1), 0.5, colors.lightgrey),
            ('BOX', (0,0), (-1,-1), 0.5, colors.black),
            ('TOPPADDING', (0,1), (-1,-1), cell_padding),
            ('BOTTOMPADDING', (0,1), (-1,-1), cell_padding),
        ])
        
        # Resaltar estados
        for i in range(1, len(page_data)):
            estado_valor = page_data[i][6].strip().lower()  # Estado en columna 6 (índice 6)
            if estado_valor == "activo":
                color = colors.HexColor("#28a745")  # Verde
            elif estado_valor == "inactivo":
                color = colors.HexColor("#dc3545")  # Rojo
            else:
                color = colors.black  # Negro para otros estados
            table_style.add('TEXTCOLOR', (6,i), (6,i), color)
        
        table.setStyle(table_style)
        table.wrapOn(p, width, height)
        table.drawOn(p, table_x, y_position - row_height * len(page_data) - 10)
        
        # Información de paginación
        p.setFont("Helvetica", 8)
        pagination_text = f"Página {page + 1} - Registros {start_row + 1} a {end_row} de {total_rows}"
        p.drawCentredString(
            safe_center, 
            y_position - row_height * len(page_data) - 25,
            pagination_text
        )
        
        draw_footer()
        page += 1

    p.save()
    return response

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




