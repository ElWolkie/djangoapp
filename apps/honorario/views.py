from datetime import datetime
from django.http import JsonResponse, HttpResponse, HttpResponseRedirect
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, permission_required
from django.template import loader
from django.urls import reverse
from django.contrib import messages
from django.db.models import Q, Prefetch
from django.core.paginator import Paginator

from .forms import HonorarioForm
from .models import Honorario
from apps.persona.models import Personas
from apps.home.models import Cargo, Cohorte, Materia, Configuracion
#Libreria para generar PDF
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.platypus import Table, TableStyle
from reportlab.lib import colors
import os
from django.db import IntegrityError

#HONORARIO
@login_required(login_url='login')
@permission_required("honorario.add_honorario", raise_exception=True)
def honorario_modal(request):
    if request.method == 'POST':
        form = HonorarioForm(request.POST)
        if form.is_valid():
            try:
                honorario = form.save()
            except IntegrityError:
                return JsonResponse({
                    'success': False,
                    'errors': {'__all__': ['Ya existe un honorario idéntico en la base de datos.']}
                })
            monto = honorario.monto
            idHonorario = honorario.pk

            return JsonResponse({
                'success': True,
                'message': 'Registro exitoso.',
                'redirect_url': f"{reverse('nota_create')}?honorario={monto}&idP={honorario.idPersona.idPersona}&idH={idHonorario}"
            })
        else:
            # Empaquetar errores de campo y non-field
            errors = {}
            for f, errs in form.errors.items():
                errors[f] = errs.get_json_data(escape_html=True) if hasattr(errs, 'get_json_data') else errs
            non_field = form.non_field_errors()
            if non_field:
                errors['__all__'] = non_field
            return JsonResponse({'success': False, 'errors': errors})

    # GET: solo personas con idTipoPersona = 3
    personas = Personas.objects.filter(
        personatp__idTP=3,  # Relación con TipoPersona idTP=2
        estadoPersona='ACTIVO'  # Estado activo
    ).distinct()
    cargos    = Cargo.objects.filter(estadoCargo='ACTIVO')
    materias  = Materia.objects.filter(estadoMateria='ACTIVO')
    cohortes  = Cohorte.objects.filter(estadoCohorte='ACTIVO')
    form      = HonorarioForm()

    return render(request, 'honorario/honorario2.html', {
        'form': form,
        'personas': personas,
        'cargos': cargos,
        'materias': materias,
        'cohortes': cohortes,
    })

@login_required(login_url='login')
@permission_required("honorario.change_honorario", raise_exception=True)
def edit_honorario(request, pk):
    instance = get_object_or_404(Honorario, pk=pk)
    if request.method == 'POST':
        form = HonorarioForm(request.POST, instance=instance)
        if form.is_valid():
            form.save()
            return JsonResponse({'success': True, 'message': 'Honorario actualizado.'})
        else:
            errors = {field: error for field, error in form.errors.items()}
            return JsonResponse({'success': False, 'errors': errors})
    else:
        form = HonorarioForm(instance=instance)
        # Obtener datos relacionados para los dropdowns
        personas = Personas.objects.all()
        cargos = Cargo.objects.all()
        materias = Materia.objects.all()
        cohortes = Cohorte.objects.all()
        
    return render(request, 'honorario/editHonorario.html', {
        'form': form,
        'honorario': instance,
        'personas': personas,
        'cargos': cargos,
        'materias': materias,
        'cohortes': cohortes
    })

@login_required(login_url='login')
@permission_required("honorario.change_honorario", raise_exception=True)
def delete_honorario(request, pk):
    instance = get_object_or_404(Honorario, pk=pk)
    instance.estadoHonorario = 'INACTIVO'
    instance.save()
    return JsonResponse({'success': True, 'message': 'Eliminación lógica exitosa.'})

@login_required
@permission_required('honorario.change_honorario', raise_exception=True)
def desactivar_honorario(request, pk):
    honorarios = get_object_or_404(Honorario, pk=pk)
    if request.method == 'POST':
        honorarios.estadoHonorario = "INACTIVO"
        honorarios.save()
        messages.success(request, f'⛔ Honorario {honorarios.idHonorario} desactivado')
        return redirect(request.POST.get('next', 'tabla_honorarios'))
    return redirect('tabla_honorarios')

@login_required(login_url='login')
@permission_required("honorario.change_honorario", raise_exception=True)
def reactivate_honorario(request, pk):
    honorarios = get_object_or_404(Honorario, pk=pk)
    if request.method == 'POST':
        honorarios.estadoHonorario = "ACTIVO"
        honorarios.save()
        messages.success(request, f'✅ Honorario {honorarios.idHonorario} activado')
        return redirect(request.POST.get('next', 'tabla_honorarios'))
    return redirect('tabla_honorarios')

@login_required(login_url='login')
@permission_required("honorario.view_honorario", raise_exception=True)
def tabla_honorarios(request):
    mostrar = request.GET.get('mostrar_inactivos', 'false') == 'true'
    search_query = request.GET.get('search', '').strip()  # Obtener el término de búsqueda

    if mostrar:
        honorarios = Honorario.objects.all()
    else:
        honorarios = Honorario.objects.filter(estadoHonorario='ACTIVO')

          # Filtrar por el término de búsqueda si existe BUSCADOR
    if search_query:
        honorarios = honorarios.filter(
            Q(idHonorario__icontains=search_query) |
            Q(idPersona__cedula__icontains=search_query) |
            Q(idPersona__nombres__icontains=search_query) |
            Q(idPersona__apellidos__icontains=search_query) |
            Q(idCargo__nombreCargo__icontains=search_query) |
            Q(idCohorte__nombreCohorte__icontains=search_query) |
            Q(idMateria__nombreMateria__icontains=search_query) |
            Q(horas__icontains=search_query) |
            Q(monto__icontains=search_query) |
            Q(estadoHonorario__icontains=search_query) |
            Q(fechaHonorario__icontains=search_query)
        )
    # Paginación 
    paginator = Paginator(honorarios, 2)  # 10 cuotas por página
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'honorario/tablaHonorarios.html', {
        'honorarios': page_obj,
        'mostrar_inactivos': mostrar,
        'search_query': search_query,  # Pasar el término de búsqueda al template

    })

@login_required(login_url='login')
def reporte_honorarios_pdf(request):
    # Manejo de parámetros de paginación
    start = int(request.GET.get('start', 1))
    end = int(request.GET.get('end', 0))
    honorarios = list(Honorario.objects.all())
    
    if end == 0 or end > len(honorarios):
        end = len(honorarios)
    honorarios = honorarios[start-1:end]

    # Configuración inicial del PDF
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'inline; filename="reporte_honorarios.pdf"'
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
        p.drawCentredString(safe_center, text_top - 85, "REPORTE DE HONORARIOS")

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
    headers = ["ID", "CÉDULA", "NOMBRE", "CARGO", "MATERIA", "HORAS", "COHORTE", "ESTADO", "FECHA"]
    data = [headers]
    
    for honorario in honorarios:
        # Manejar posibles valores nulos
        cedula = f"{honorario.idPersona.cedula}" if honorario.idPersona else ""
        nombre = f"{honorario.idPersona.nombres} {honorario.idPersona.apellidos}" if honorario.idPersona else ""
        cargo = honorario.idCargo.nombreCargo if honorario.idCargo else ""
        materia = honorario.idMateria.nombreMateria if honorario.idMateria else ""
        cohorte = honorario.idCohorte.nombreCohorte if honorario.idCohorte else ""
        fecha = honorario.fechaHonorario.strftime("%d/%m/%Y") if honorario.fechaHonorario else ""
        
        data.append([
            str(honorario.idHonorario),
            cedula,
            nombre,
            cargo,
            materia,
            str(honorario.horas),
            cohorte,
            honorario.estadoHonorario,
            fecha
        ])
    
    # Configuración de la tabla con espacios aumentados
    # Anchos ajustados para caber en página horizontal
    col_widths = [25, 50, 80, 130, 130, 35, 45, 40, 50]
    table_width = sum(col_widths)
    
    # Espaciado vertical aumentado
    header_height = 150
    footer_height = 100
    row_height = 22  # Altura ligeramente menor para más filas por página
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
            ('FONTSIZE', (0,0), (-1,0), 8),  # Tamaño más pequeño
            ('ALIGN', (0,0), (-1,0), 'CENTER'),
            ('VALIGN', (0,0), (-1,0), 'MIDDLE'),
            ('BOTTOMPADDING', (0,0), (-1,0), cell_padding),
            
            # Cuerpo de la tabla
            ('FONTSIZE', (0,1), (-1,-1), 7),  # Tamaño más pequeño
            ('ALIGN', (0,1), (-1,-1), 'CENTER'),
            ('ALIGN', (1,1), (2,-1), 'LEFT'),  # Alinear nombres a izquierda
            ('VALIGN', (0,1), (-1,-1), 'MIDDLE'),
            ('BACKGROUND', (0,1), (-1,-1), colors.whitesmoke),
            ('GRID', (0,0), (-1,-1), 0.5, colors.lightgrey),
            ('BOX', (0,0), (-1,-1), 0.5, colors.black),
            ('TOPPADDING', (0,1), (-1,-1), cell_padding),
            ('BOTTOMPADDING', (0,1), (-1,-1), cell_padding),
        ])
        
        # Resaltar estados
        for i in range(1, len(page_data)):
            estado_valor = page_data[i][7].strip().lower()  # Estado en columna 7 (índice 7)
            if estado_valor == "activo":
                color = colors.HexColor("#28a745")  # Verde
            elif estado_valor == "inactivo":
                color = colors.HexColor("#dc3545")  # Rojo
            else:
                color = colors.black  # Negro para otros estados
            table_style.add('TEXTCOLOR', (7,i), (7,i), color)
        
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
       
        if load_template in [ "honorario.html", "honorario2.html", "tablaContratos.html", "tablaHonorarios.html"]:
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



        context["segment"] = load_template
        html_template = loader.get_template("honorario/" + load_template)
        return HttpResponse(html_template.render(context, request))



    except loader.TemplateDoesNotExist:
        html_template = loader.get_template("home/page-404.html")
        return HttpResponse(html_template.render(context, request))

    except Exception as e:
        messages.error(request, f'Error inesperado: {e}')
        html_template = loader.get_template("home/page-500.html")
        return HttpResponse(html_template.render(context, request))




