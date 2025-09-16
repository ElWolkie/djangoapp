from datetime import datetime
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required, permission_required
from django.http import JsonResponse
from .models import periodoContable
from .forms import periodoContableForm
from django.http import HttpResponse
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import landscape, letter
from reportlab.platypus import Table, TableStyle
from reportlab.lib import colors
import os
from apps.home.models import Configuracion

@login_required(login_url='login')
@permission_required("periodoContable.view_periodocontable", raise_exception=True)
def periodo_contable_list(request):
    mostrar_inactivos = request.GET.get('mostrar_inactivos') == 'true'
    if mostrar_inactivos:
        periodos = periodoContable.objects.all()
    else:
        periodos = periodoContable.objects.filter(estadoPeriodo=True)
    return render(request, 'periodoContable/tablaPeriodoContable.html', {
        'periodos': periodos,
        'mostrar_inactivos': mostrar_inactivos
    })

@login_required(login_url='login')
@permission_required("periodoContable.add_periodocontable", raise_exception=True)
def periodo_contable_create(request):
    if request.method == 'POST':
        form = periodoContableForm(request.POST)
        if form.is_valid():
            form.save()
            return JsonResponse({'success': True, 'message': 'Periodo Contable registrado exitosamente.'})
        else:
            return JsonResponse({'success': False, 'errors': form.errors})
    else:
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            form = periodoContableForm()
            return render(request, 'periodoContable/periodoContable.html', {'form': form})
        else:
            return JsonResponse({'success': False, 'message': 'Solicitud no válida.'}, status=400)

@login_required(login_url='login')
@permission_required("periodoContable.change_periodocontable", raise_exception=True)
def periodo_contable_edit(request, id):
    periodo = get_object_or_404(periodoContable, idPeriodo=id)
    if request.method == 'POST':
        form = periodoContableForm(request.POST, instance=periodo)
        if form.is_valid():
            form.save()
            return JsonResponse({'success': True, 'message': 'Periodo Contable actualizado exitosamente.'})
        else:
            return JsonResponse({'success': False, 'errors': form.errors})
    else:
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            form = periodoContableForm(instance=periodo)
            return render(
                request,
                'periodoContable/editarPeriodoContable.html',
                {
                    'form': form,
                    'periodo': periodo,
                    'nombrePeriodo': periodo.nombrePeriodo,
                    'fechaInicio': periodo.fechaInicioPeriodo,
                    'fechaFin': periodo.fechaFinPeriodo,
                }
            )
        else:
            return JsonResponse({'success': False, 'message': 'Solicitud no válida.'}, status=400)

@login_required(login_url='login')
@permission_required("periodoContable.change_periodocontable", raise_exception=True)
def desactivar_periodo_contable(request, id):
    periodo = get_object_or_404(periodoContable, idPeriodo=id)
    if request.method == 'POST':
        periodo.estadoPeriodo = False
        periodo.save()
        return JsonResponse({'success': True, 'message': f'⛔ Periodo Contable {getattr(periodo, "nombrePeriodo", periodo.pk)} desactivado'})
    return JsonResponse({'success': False, 'message': 'Solicitud no válida.'}, status=400)

@login_required(login_url='login')
@permission_required("periodoContable.change_periodocontable", raise_exception=True)
def reactivar_periodo_contable(request, id):
    periodo = get_object_or_404(periodoContable, idPeriodo=id)
    if request.method == 'POST':
        periodo.estadoPeriodo = True
        periodo.save()
        return JsonResponse({'success': True, 'message': f'✅ Periodo Contable {getattr(periodo, "nombrePeriodo", periodo.pk)} activado'})
    return JsonResponse({'success': False, 'message': 'Solicitud no válida.'}, status=400)


@login_required(login_url='login')
def reporte_periodos_pdf(request):
    # Manejo de parámetros de paginación
    start = int(request.GET.get('start', 1))
    end = int(request.GET.get('end', 0))
    periodos = list(periodoContable.objects.all())
    
    if end == 0 or end > len(periodos):
        end = len(periodos)
    periodos = periodos[start-1:end]

    # Configuración inicial del PDF
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'inline; filename="reporte_periodos_contables.pdf"'
    p = canvas.Canvas(response, pagesize=letter)
    width, height = letter
    logo_width, logo_height, logo_margin = 80, 80, 15  # Reducir tamaño del logo

    # Obtener configuración institucional
    config = None
    try:
        config = Configuracion.objects.order_by('-fechaConfiguracion').first()
    except Exception:
        pass
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
        p.drawCentredString(safe_center, text_top - 85, "REPORTE DE PERÍODOS CONTABLES")

    def draw_footer(current_y):
        # Calcular posición dinámica para la firma
        firma_y = min(current_y - 50, 100)  # Asegurar que no se solape
        
        if firma_path and os.path.exists(firma_path):
            p.drawImage(
                firma_path,
                width/2 - 50,
                firma_y,
                width=100,
                height=50,
                preserveAspectRatio=True,
                mask='auto'
            )
            p.setFont("Helvetica-Oblique", 9)
            p.drawCentredString(width/2, firma_y - 15, "Firma autorizada")
        
        # Fecha de generación en posición fija abajo
        p.setFont("Helvetica", 8)
        fecha_generacion = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        p.drawString(min_margin, 20, f"Generado el: {fecha_generacion}")

    # Preparar datos de la tabla
    headers = ["ID", "NOMBRE", "FECHA INICIO", "FECHA FIN", "ESTADO", "FECHA DIGITAL"]
    data = [headers]
    
    for per in periodos:
        data.append([
            str(per.idPeriodo),
            per.nombrePeriodo,
            per.fechaInicioPeriodo.strftime("%d/%m/%Y") if per.fechaInicioPeriodo else '',
            per.fechaFinPeriodo.strftime("%d/%m/%Y") if per.fechaFinPeriodo else '',
            "Activo" if per.estadoPeriodo else "Inactivo",
            per.fechaPeriodoDigital.strftime("%d/%m/%Y %H:%M") if per.fechaPeriodoDigital else ''
        ])
    
    # Configuración de la tabla
    col_widths = [40, 120, 80, 80, 60, 100]
    table_width = sum(col_widths)
    
    # Espaciado vertical
    header_height = 150
    footer_height = 120  # Aumentado para evitar solapamiento
    row_height = 25
    cell_padding = 5
    
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
        
        # Estilo de la tabla
        table_style = TableStyle([
            # Encabezado
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#fe8330")),
            ('TEXTCOLOR', (0,0), (-1,0), colors.white),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('FONTSIZE', (0,0), (-1,0), 9),
            ('ALIGN', (0,0), (-1,0), 'CENTER'),
            ('VALIGN', (0,0), (-1,0), 'MIDDLE'),
            ('BOTTOMPADDING', (0,0), (-1,0), cell_padding),
            
            # Cuerpo de la tabla
            ('FONTSIZE', (0,1), (-1,-1), 8),
            ('ALIGN', (0,1), (-1,-1), 'CENTER'),
            ('ALIGN', (1,1), (1,-1), 'LEFT'),
            ('VALIGN', (0,1), (-1,-1), 'MIDDLE'),
            ('BACKGROUND', (0,1), (-1,-1), colors.whitesmoke),
            ('GRID', (0,0), (-1,-1), 0.5, colors.lightgrey),
            ('BOX', (0,0), (-1,-1), 0.5, colors.black),
            ('TOPPADDING', (0,1), (-1,-1), cell_padding),
            ('BOTTOMPADDING', (0,1), (-1,-1), cell_padding),
        ])
        
        # Resaltar estados
        for i in range(1, len(page_data)):
            estado_valor = page_data[i][4].strip().lower()
            if estado_valor == "activo":
                color = colors.HexColor("#28a745")  # Verde
            else:
                color = colors.HexColor("#dc3545")  # Rojo
            table_style.add('TEXTCOLOR', (4, i), (4, i), color)
        
        table.setStyle(table_style)
        table.wrapOn(p, width, height)
        table.drawOn(p, table_x, y_position - row_height * len(page_data) - 10)
        
        # Calcular posición Y actual después de dibujar la tabla
        current_y = y_position - row_height * len(page_data) - 30

        # Información de paginación
        p.setFont("Helvetica", 8)
        pagination_text = f"Página {page + 1} - Registros {start_row + 1} a {end_row} de {total_rows}"
        p.drawCentredString(
            safe_center, 
            current_y - 10,
            pagination_text
        )
        
        # Dibujar footer con posición dinámica
        draw_footer(current_y - 20)
        page += 1

    p.save()
    return response