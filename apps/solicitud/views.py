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
from apps.home.models import Configuracion
from apps.solicitud.models import Solicitud  # Usamos Solicitud en vez de Honorario
from apps.requisitoCliente.models import RequisitoCliente 
from apps.home.models import Requisito
from apps.factura.models import NotaRelacionada, Factura #Usada para la redireccion y obtencion de estados
#Libreria para generar PDF
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter, landscape
from reportlab.platypus import Table, TableStyle
from reportlab.lib import colors
from datetime import datetime
import os

#SOLICITUD
@login_required(login_url='login')
@permission_required("solicitud.add_solicitud", raise_exception=True)
def solicitud_modal(request):
    if request.method == 'POST':
        form = SolicitudForm(request.POST)
        if form.is_valid():
            solicitud = form.save()  # Guardar la solicitud y obtener la instancia
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
             idSolicitud = solicitud.pk
            return JsonResponse({
                    'success': True,
                    'message': 'Registro exitoso.',
                    'redirect_url': reverse('nota_administrativa_create') + f"?solicitud={solicitud.montoTotal}&idP={solicitud.idPersona.idPersona}&idS={idSolicitud}"
                })
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
    personas = Personas.objects.filter(
        personatp__idTP=2,  # Relación con TipoPersona idTP=2
        estadoPersona='ACTIVO'  # Estado activo
    ).distinct()
    return render(request, 'solicitud/solicitud.html', {
        'form': SolicitudForm(),
        'tramites': tramites,
        'servicios': servicios,
        'personas': personas,
        'segment': 'solicitud'
    })

@login_required(login_url='login')
@permission_required("solicitud.change_solicitud", raise_exception=True)
def edit_solicitud(request, pk):
    instance = get_object_or_404(Solicitud, pk=pk)
    if request.method == 'POST':
        form = SolicitudForm(request.POST, instance=instance)
        if form.is_valid():
            form.save()
            return JsonResponse({'success': True, 'message': 'Solicitud actualizada.'})
        else:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                errors = {field: error[0] for field, error in form.errors.items()}
                return JsonResponse({'success': False, 'errors': errors})
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
@permission_required("solicitud.change_solicitud", raise_exception=True)
def delete_solicitud(request, pk):
    instance = get_object_or_404(Solicitud, pk=pk)
    instance.estadoSolicitud = 'INACTIVO'
    instance.save()
    return JsonResponse({'success': True, 'message': 'Eliminación lógica exitosa.'})

@login_required
@permission_required('solicitud.change_solicitud', raise_exception=True)
def desactivar_solicitud(request, pk):
    solicitud = get_object_or_404(Solicitud, pk=pk)
    if request.method == 'POST':
        solicitud.estadoSolicitud = "INACTIVO"
        solicitud.save()
        messages.success(request, f'Solicitud {solicitud.idSoli} desactivada')
        return redirect(request.POST.get('next', 'tabla_solicitud'))
    return redirect('tabla_solicitud')

@login_required(login_url='login')
@permission_required("solicitud.change_solicitud", raise_exception=True)
def reactivate_solicitud(request, pk):
    solicitud = get_object_or_404(Solicitud, pk=pk)
    if request.method == 'POST':
        solicitud.estadoSolicitud = "ACTIVO"
        solicitud.save()
        messages.success(request, f'Solicitud {solicitud.idSoli} activada')
        return redirect(request.POST.get('next', 'tabla_solicitud'))
    return redirect('tabla_solicitud')

@login_required(login_url='login')
@permission_required("solicitud.view_solicitud", raise_exception=True)
def tabla_solicitud(request):
    mostrar = request.GET.get('mostrar_inactivos', 'false') == 'true'
    # Query base
    qs = Solicitud.objects.all()
    # Aplicar filtro por estado si no se piden inactivos
    if not mostrar:
        qs = qs.filter(estadoSolicitud='ACTIVO')

    # Obtener IDs de solicitudes que tienen notas y facturas
    
    # Obtener todas las solicitudes con notas
    solicitudes_con_nota = NotaRelacionada.objects.filter(
        idSolicitud__in=qs
    ).values_list('idSolicitud_id', flat=True)
    
    # Obtener solicitudes que tienen factura (nota con factura)
    solicitudes_con_factura = NotaRelacionada.objects.filter(
        idSolicitud__in=qs,
        idNota__factura__isnull=False
    ).values_list('idSolicitud_id', flat=True)
    
    # Convertir a sets para búsqueda más eficiente
    solicitudes_con_nota_set = set(solicitudes_con_nota)
    solicitudes_con_factura_set = set(solicitudes_con_factura)

    # Mensajes informativos
    if mostrar:
        hay_inactivos = qs.exclude(estadoSolicitud='ACTIVO').exists()
        if not hay_inactivos:
            messages.info(request, 'No hay solicitudes inactivas para mostrar.')
    else:
        if not qs.exists():
            messages.info(request, 'No hay solicitudes activas para mostrar.')

    return render(request, 'solicitud/tablaSolicitud.html', {
        'solicitudes': qs,
        'mostrar_inactivos': mostrar,
        'solicitudes_con_nota': solicitudes_con_nota_set,
        'solicitudes_con_factura': solicitudes_con_factura_set,
    })

@login_required(login_url='login')
def reporte_solicitudes_pdf(request):
    # Manejo de parámetros de paginación
    start = int(request.GET.get('start', 1))
    end = int(request.GET.get('end', 0))
    solicitudes = list(Solicitud.objects.select_related('idPersona', 'idTramite', 'idServicio').all())
    
    if end == 0 or end > len(solicitudes):
        end = len(solicitudes)
    solicitudes = solicitudes[start-1:end]

    # Configuración inicial del PDF
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'inline; filename="reporte_solicitudes.pdf"'
    pagesize = landscape(letter)  # Esto intercambia width y height
    p = canvas.Canvas(response, pagesize=pagesize)
    p.setTitle("Reporte de Solicitudes")
    width, height = pagesize
    
    # Tamaños reducidos para mejor espacio
    logo_width, logo_height = 70, 70
    logo_margin = 15

    # Obtener configuración institucional
    config = Configuracion.objects.order_by('-fechaConfiguracion').first()
    logo_path = config.logo.path if config and config.logo else None
    firma_path = config.firma.path if config and config.firma else None
    nombre_institucion = config.nombreInstitucion if config else "Institución"
    rif_institucion = config.rif if config else ""
    direccion1 = "AV. ALBERTO RAVELL CON AV. INTERCOMUNAL JOSE ANTONIO PAEZ"
    direccion2 = "LOCAL UPTYAB, INDEPENDENCIA – EDO YARACUY"

    # Definir márgenes seguros más amplios
    min_margin = 25
    safe_left = min_margin
    safe_right = width - min_margin
    safe_width = safe_right - safe_left
    safe_center = width / 2

    # Espacios fijos para evitar solapamiento
    header_height = 130
    footer_height = 120
    row_height = 20
    cell_padding = 3

    def draw_header():
        """Dibuja el encabezado en cada página"""
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
        text_top = height - logo_margin - 12
        p.setFont("Helvetica-Bold", 9)
        p.drawString(min_margin, text_top, nombre_institucion)
        p.drawString(min_margin, text_top - 12, f"RIF: {rif_institucion}")
        p.setFont("Helvetica", 8)
        p.drawString(min_margin, text_top - 24, direccion1)
        p.drawString(min_margin, text_top - 36, direccion2)
        
        # Título centrado
        p.setFont("Helvetica-Bold", 12)
        p.drawCentredString(safe_center, text_top - 70, "REPORTE DE SOLICITUDES")

    def draw_footer(current_page, total_pages):
        """Dibuja el pie de página en cada página"""
        # Espacio seguro antes de la firma
        footer_start_y = footer_height - 40
        
        # Firma centrada en el pie de página
        if firma_path and os.path.exists(firma_path):
            p.drawImage(
                firma_path,
                width/2 - 45,
                footer_start_y,
                width=90,
                height=45,
                preserveAspectRatio=True,
                mask='auto'
            )
            p.setFont("Helvetica-Oblique", 8)
            p.drawCentredString(width/2, footer_start_y - 20, "Firma autorizada")
        
        # Información de página
        p.setFont("Helvetica", 8)
        pagination_text = f"Página {current_page} de {total_pages}"
        p.drawCentredString(width/2, footer_start_y - 35, pagination_text)
        
        # Fecha de generación
        fecha_generacion = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        p.drawString(min_margin, 20, f"Generado el: {fecha_generacion}")

    # Preparar datos de la tabla
    headers = ["ID", "PERSONA", "TRÁMITE", "SERVICIO", "ESTADO", "FECHA"]
    data = [headers]
    
    for solicitud in solicitudes:
        persona = f"{solicitud.idPersona.nombres} {solicitud.idPersona.apellidos}" if solicitud.idPersona else ""
        tramite = solicitud.idTramite.nombreTramite if solicitud.idTramite else ""
        servicio = solicitud.idServicio.nombreServicio if solicitud.idServicio else ""
        estado = solicitud.estadoSolicitud
        fecha = solicitud.fechaSolicitud.strftime("%d/%m/%Y") if solicitud.fechaSolicitud else ""
        
        data.append([
            str(solicitud.idSoli),
            persona[:50] + "..." if len(persona) > 50 else persona,  # Truncar texto largo
            tramite[:40] + "..." if len(tramite) > 40 else tramite,
            servicio[:40] + "..." if len(servicio) > 40 else servicio,
            estado,
            fecha
        ])
    
    # Configuración de la tabla responsive
    col_widths = [
        max(30, safe_width * 0.08),    # ID: 8%
        max(120, safe_width * 0.32),   # Persona: 32%
        max(200, safe_width * 0.22),    # Trámite: 22%
        max(200, safe_width * 0.22),    # Servicio: 22%
        max(50, safe_width * 0.08),    # Estado: 8%
        max(50, safe_width * 0.08)     # Fecha: 8%
    ]
    
    # Ajustar si la suma excede el ancho seguro
    total_table_width = sum(col_widths)
    if total_table_width > safe_width:
        scale_factor = safe_width / total_table_width
        col_widths = [w * scale_factor for w in col_widths]
        total_table_width = safe_width
    
    # Calcular espacio disponible para la tabla
    available_height = height - header_height - footer_height
    max_rows_per_page = max(1, int(available_height // row_height))
    total_rows = len(data) - 1
    
    # Calcular número total de páginas
    total_pages = (total_rows + max_rows_per_page - 1) // max_rows_per_page
    current_page = 0

    # Generar páginas
    for start_row in range(0, total_rows, max_rows_per_page):
        end_row = min(start_row + max_rows_per_page, total_rows)
        page_data = [data[0]] + data[start_row + 1:end_row + 1]
        
        if current_page > 0:
            p.showPage()
        
        draw_header()
        
        # Posición Y inicial para la tabla (con margen seguro)
        table_start_y = height - header_height - 20
        
        # Centrar tabla horizontalmente
        table_x = safe_left + (safe_width - total_table_width) / 2
        
        # Crear tabla
        table = Table(page_data, colWidths=col_widths, rowHeights=[row_height] * len(page_data))
        
        # Estilo de la tabla mejorado
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
            ('ALIGN', (0,1), (0,-1), 'CENTER'),  # ID centrado
            ('ALIGN', (1,1), (3,-1), 'LEFT'),    # Texto a izquierda
            ('ALIGN', (4,1), (-1,-1), 'CENTER'), # Estado y fecha centrados
            ('VALIGN', (0,1), (-1,-1), 'MIDDLE'),
            ('BACKGROUND', (0,1), (-1,-1), colors.whitesmoke),
            ('GRID', (0,0), (-1,-1), 0.5, colors.lightgrey),
            ('BOX', (0,0), (-1,-1), 0.5, colors.black),
            ('TOPPADDING', (0,1), (-1,-1), cell_padding),
            ('BOTTOMPADDING', (0,1), (-1,-1), cell_padding),
        ])
        
        # Resaltar estados con colores
        for i in range(1, len(page_data)):
            estado_valor = page_data[i][4].strip().lower()
            if estado_valor in ["aprobado", "aprobada"]:
                color = colors.HexColor("#28a745")  # Verde
            elif estado_valor in ["rechazado", "rechazada"]:
                color = colors.HexColor("#dc3545")  # Rojo
            elif estado_valor == "pendiente":
                color = colors.HexColor("#ffc107")  # Amarillo
            elif estado_valor in ["procesando", "en proceso"]:
                color = colors.HexColor("#17a2b8")  # Azul
            else:
                color = colors.black
            table_style.add('TEXTCOLOR', (4,i), (4,i), color)
            table_style.add('FONTNAME', (4,i), (4,i), 'Helvetica-Bold')
        
        table.setStyle(table_style)
        
        # Calcular altura de la tabla
        table_height = row_height * len(page_data)
        
        # Posición Y final de la tabla (asegurar que no se solape con el footer)
        table_y = table_start_y - table_height
        
        # Verificar que haya espacio suficiente
        min_safe_bottom = footer_height + 30
        if table_y < min_safe_bottom:
            # Reducir altura de filas si es necesario
            available_table_height = table_start_y - min_safe_bottom
            if available_table_height > row_height:  # Mínimo una fila
                adjusted_row_height = available_table_height / len(page_data)
                table = Table(page_data, colWidths=col_widths, rowHeights=[adjusted_row_height] * len(page_data))
                table.setStyle(table_style)
                table_height = adjusted_row_height * len(page_data)
                table_y = table_start_y - table_height
        
        # Asegurar posición mínima
        table_y = max(table_y, min_safe_bottom)
        
        # **CORRECCIÓN DEL ERROR: Primero wrap, luego draw**
        table.wrapOn(p, width, height)
        table.drawOn(p, table_x, table_y)
        
        # Información de registros
        p.setFont("Helvetica", 8)
        records_text = f"Registros {start_row + 1} a {end_row} de {total_rows}"
        p.drawCentredString(
            safe_center, 
            table_y - 15,
            records_text
        )
        
        # Dibujar pie de página (siempre en posición fija)
        draw_footer(current_page + 1, total_pages)
        current_page += 1

    p.save()
    return response

@login_required
def requisitos_solicitud_modal(request, pk):
    solicitud = get_object_or_404(Solicitud, pk=pk)
    # Requisitos ya entregados para esta solicitud
    entregados_qs = RequisitoCliente.objects.filter(idSolicitud=solicitud, entregado=True)
    entregados = list(entregados_qs.values_list('idRequisito_id', flat=True))

    # Intentar detectar el nombre del campo que indica estado/activo en el modelo Requisito
    field_names = [f.name for f in Requisito._meta.get_fields()]
    candidates = ['estadoRequisito', 'estado', 'activo', 'estado_requisito', 'is_active']
    active_field = next((c for c in candidates if c in field_names), None)

    if active_field:
        # Determinar tipo interno del campo para usar el valor apropiado al filtrar
        field_type = Requisito._meta.get_field(active_field).get_internal_type()
        if field_type in ('BooleanField', 'NullBooleanField'):
            # Mostrar requisitos activos o aquellos inactivos que ya fueron entregados
            requisitos = Requisito.objects.filter(**{active_field: True}) | Requisito.objects.filter(pk__in=entregados)
        else:
            # Asumir que el campo es string y que el valor activo es 'ACTIVO'
            requisitos = Requisito.objects.filter(**{active_field: 'ACTIVO'}) | Requisito.objects.filter(pk__in=entregados)
        requisitos = requisitos.distinct()
    else:
        # Si no se detecta un campo de estado, no filtrar (fallback seguro)
        requisitos = Requisito.objects.all()

    context = {
        'solicitud': solicitud,
        'requisitos': requisitos,
        'requisitos_entregados': entregados,
    }
    return render(request, 'requisitoCliente/requisitoCliente.html', context)

@login_required
def guardar_requisitos_solicitud(request, pk):
    solicitud = get_object_or_404(Solicitud, pk=pk)
    if request.method == 'POST':
        entregados = request.POST.getlist('requisitos_entregados')
        # Marca todos como no entregados
        RequisitoCliente.objects.filter(idSolicitud=solicitud).update(entregado=False)
        # Marca como entregados los seleccionados
        for id_req in entregados:
            rc, created = RequisitoCliente.objects.get_or_create(
                idSolicitud=solicitud,
                idRequisito_id=id_req,
                defaults={'entregado': True}
            )
            if not created:
                rc.entregado = True
                rc.save()
        return JsonResponse({'success': True, 'message': 'Requisitos actualizados correctamente.'})
    return JsonResponse({'success': False, 'message': 'Método no permitido.'}, status=405)

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

@login_required(login_url='login')
def redirigir_a_nota_solicitud(request, pk):
    """
    Redirige a la nota específica de una solicitud (cuando tiene nota pero no factura)
    """
  
    try:
        # Buscar la nota relacionada con esta solicitud
        nota_relacionada = NotaRelacionada.objects.filter(idSolicitud_id=pk).first()
        
        if nota_relacionada and nota_relacionada.idNota:
            nota = nota_relacionada.idNota
            # Redirigir a la lista de notas (ajusta según tu estructura)
            messages.info(request, f'Solicitud tiene nota asociada: {nota.numeroNota}')
            return HttpResponseRedirect(reverse('nota_list'))
        else:
            messages.error(request, 'No se encontró nota para esta solicitud.')
            return HttpResponseRedirect(reverse('tabla_solicitud'))
            
    except Exception as e:
        messages.error(request, f'Error al buscar la nota: {str(e)}')
        return HttpResponseRedirect(reverse('tabla_solicitud'))

@login_required(login_url='login')
def redirigir_a_factura_solicitud(request, pk):
    """
    Redirige a la factura específica de una solicitud (cuando tiene nota Y factura)
    """
    
    try:
        # Buscar la nota relacionada con esta solicitud
        nota_relacionada = NotaRelacionada.objects.filter(idSolicitud_id=pk).first()
        
        if nota_relacionada and nota_relacionada.idNota:
            nota = nota_relacionada.idNota
            
            # Buscar si existe factura para esta nota
            try:
                factura = Factura.objects.get(nota=nota)
                return HttpResponseRedirect(reverse('factura_generar_pdf', args=[factura.pk]))
            except Factura.DoesNotExist:
                # Si no hay factura, redirigir a la nota
                messages.info(request, 'Esta solicitud tiene nota pero no factura. Redirigiendo a la nota.')
                return HttpResponseRedirect(reverse('redirigir_nota_solicitud', args=[pk]))
        else:
            messages.error(request, 'No se encontró nota para esta solicitud.')
            return HttpResponseRedirect(reverse('tabla_solicitud'))
            
    except Exception as e:
        messages.error(request, f'Error al buscar la factura: {str(e)}')
        return HttpResponseRedirect(reverse('tabla_solicitud'))