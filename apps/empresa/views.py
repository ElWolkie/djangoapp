from datetime import datetime
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse, HttpResponse
from django.contrib.auth.decorators import login_required, permission_required
from .models import empresa
from apps.home.models import Configuracion
from .forms import empresaForm
import os
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter, landscape
from reportlab.platypus import Table, TableStyle
from reportlab.lib import colors

@login_required(login_url='login')
@permission_required("empresa.view_empresa", raise_exception=True)
def empresa_list(request):
    mostrar_inactivos = request.GET.get('mostrar_inactivos') == 'true'
    if mostrar_inactivos:
        empresas = empresa.objects.all()
    else:
        empresas = empresa.objects.filter(estadoEmpresa=True)
    return render(request, 'empresa/tablaEmpresa.html', {
        'empresas': empresas,
        'mostrar_inactivos': mostrar_inactivos
    })                                          

@login_required(login_url='login')
@permission_required("empresa.add_empresa", raise_exception=True)
def empresa_create(request):
    if request.method == 'POST':
        form = empresaForm(request.POST)
        if form.is_valid():
            form.save()
            return JsonResponse({'success': True, 'message': 'Empresa registrada exitosamente.'})
        else:
            return JsonResponse({'success': False, 'errors': form.errors})
    else:
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            form = empresaForm()
            return render(request, 'empresa/empresa.html', {'form': form})
        else:
            return JsonResponse({'success': False, 'message': 'Solicitud no válida.'}, status=400)

@login_required(login_url='login')
@permission_required("empresa.change_empresa", raise_exception=True)
def editar_empresa(request, id):
    empresa_obj = get_object_or_404(empresa, idEmpresa=id)
    if request.method == 'POST':
        form = empresaForm(request.POST, instance=empresa_obj)
        if form.is_valid():
            form.save()
            return JsonResponse({'success': True, 'message': 'Empresa actualizada exitosamente.'})
        else:
            return JsonResponse({'success': False, 'errors': form.errors})
    else:
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            form = empresaForm(instance=empresa_obj)
            return render(request, 'empresa/editarEmpresa.html', {
                'form': form,
                'empresa': empresa_obj,
                'idEmpresa': empresa_obj.idEmpresa,
                'nombreEmpresa': empresa_obj.nombreEmpresa,
                'rifEmpresa': empresa_obj.rifEmpresa,
                'direccionEmpresa': empresa_obj.direccionEmpresa,
                'correoEmpresa': empresa_obj.correoEmpresa,
                'telefonoEmpresa': empresa_obj.telefonoEmpresa,
                'estadoEmpresa': empresa_obj.estadoEmpresa,
                'fechaEmpresa': empresa_obj.fechaEmpresa,
            })
        else:
            return JsonResponse({'success': False, 'message': 'Solicitud no válida.'}, status=400)

@login_required(login_url='login')
@permission_required("empresa.change_empresa", raise_exception=True)
def desactivar_empresa(request, id):
    empresa_obj = get_object_or_404(empresa, idEmpresa=id)
    if request.method == 'POST':
        empresa_obj.estadoEmpresa = False
        empresa_obj.save()
        return JsonResponse({'success': True, 'message': f'⛔ Empresa {getattr(empresa_obj, "nombreEmpresa", empresa_obj.idEmpresa)} desactivada'})
    return JsonResponse({'success': False, 'message': 'Solicitud no válida.'}, status=400)

@login_required(login_url='login')
@permission_required("empresa.change_empresa", raise_exception=True)
def reactivar_empresa(request, id):
    empresa_obj = get_object_or_404(empresa, idEmpresa=id)
    if request.method == 'POST':
        empresa_obj.estadoEmpresa = True
        empresa_obj.save()
        return JsonResponse({'success': True, 'message': f'✅  {getattr(empresa_obj, "nombreEmpresa", empresa_obj.idEmpresa)} reactivada'})
    return JsonResponse({'success': False, 'message': 'Solicitud no válida.'}, status=400)

@login_required(login_url='login')
def reporte_empresas_pdf(request):
    # Manejo de parámetros de paginación
    start = int(request.GET.get('start', 1))
    end = int(request.GET.get('end', 0))
    empresas = list(empresa.objects.all())
    
    if end == 0 or end > len(empresas):
        end = len(empresas)
    empresas = empresas[start-1:end]

    # Configuración inicial del PDF
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'inline; filename="reporte_empresas.pdf"'
    p = canvas.Canvas(response, pagesize=letter)
    width, height = letter
    logo_width, logo_height, logo_margin = 80, 80, 15  # Reducir tamaño del logo

    # Obtener configuración institucional
    config = Configuracion.objects.order_by('-fechaConfiguracion').first()
    logo_path = config.logo.path if config and config.logo else None
    firma_path = config.firma.path if config and config.firma else None
    nombre_institucion = config.nombreInstitucion if config else "Institución"
    rif_institucion = config.rif if config else ""
    direccion1 = "AV. ALBERTO RAVELL CON AV. INTERCOMUNAL JOSE ANTONIO PAEZ"  # Dirección fija
    direccion2 = "LOCAL UPTYAB, INDEPENDENCIA – EDO YARACUY"  # Dirección fija

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
        p.drawCentredString(safe_center, text_top - 85, "REPORTE DE EMPRESAS")

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
    headers = ["ID", "NOMBRE", "RIF", "TELÉFONO", "ESTADO", "FECHA"]
    data = [headers]
    
    for emp in empresas:
        data.append([
            str(emp.idEmpresa),
            emp.nombreEmpresa,
            emp.rifEmpresa,
            emp.telefonoEmpresa,
            "Activo" if emp.estadoEmpresa else "Inactivo",
            emp.fechaEmpresa.strftime("%d/%m/%Y") if emp.fechaEmpresa else ''
        ])
    
    # Configuración de la tabla con espacios aumentados
    col_widths = [30, 230, 70, 80, 70, 70]  # Anchos ajustados
    table_width = sum(col_widths)
    
    # Espaciado vertical aumentado
    header_height = 150  # Más espacio para encabezado
    footer_height = 100  # Más espacio para pie de página
    row_height = 25  # Aumentar altura de filas
    cell_padding = 5  # Padding interno en celdas
    
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
            ('FONTSIZE', (0,0), (-1,0), 9),  # Tamaño reducido
            ('ALIGN', (0,0), (-1,0), 'CENTER'),
            ('VALIGN', (0,0), (-1,0), 'MIDDLE'),
            ('BOTTOMPADDING', (0,0), (-1,0), cell_padding),
            
            # Cuerpo de la tabla
            ('FONTSIZE', (0,1), (-1,-1), 8),  # Tamaño reducido
            ('ALIGN', (0,1), (-1,-1), 'CENTER'),
            ('ALIGN', (1,1), (1,-1), 'LEFT'),  # Alinear nombre a izquierda
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
            elif estado_valor == "inactivo":
                color = colors.HexColor("#dc3545")  # Rojo
            else:
                color = colors.black
            table_style.add('TEXTCOLOR', (4, i), (4, i), color)
        
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