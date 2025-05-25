from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse, HttpResponse
from django.contrib.auth.decorators import login_required
from .models import empresa
from apps.home.models import Configuracion
from .forms import empresaForm
import os
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter, landscape
from reportlab.platypus import Table, TableStyle
from reportlab.lib import colors

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
def desactivar_empresa(request, id):
    empresa_obj = get_object_or_404(empresa, idEmpresa=id)
    if request.method == 'POST':
        empresa_obj.estadoEmpresa = False
        empresa_obj.save()
        return JsonResponse({'success': True, 'message': f'⛔ Empresa {getattr(empresa_obj, "nombre", empresa_obj.idEmpresa)} desactivada'})
    return JsonResponse({'success': False, 'message': 'Solicitud no válida.'}, status=400)

@login_required(login_url='login')
def reactivar_empresa(request, id):
    empresa_obj = get_object_or_404(empresa, idEmpresa=id)
    if request.method == 'POST':
        empresa_obj.estadoEmpresa = True
        empresa_obj.save()
        return JsonResponse({'success': True, 'message': f'✅  {getattr(empresa_obj, "nombre", empresa_obj.idEmpresa)} reactivada'})
    return JsonResponse({'success': False, 'message': 'Solicitud no válida.'}, status=400)

def reporte_empresas_pdf(request):
    # Selección de cantidad de registros
    start = int(request.GET.get('start', 1))
    end = int(request.GET.get('end', 0))
    empresas = list(empresa.objects.all())
    if end == 0 or end > len(empresas):
        end = len(empresas)
    empresas = empresas[start-1:end]

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="reporte_empresas.pdf"'
    p = canvas.Canvas(response, pagesize=landscape(letter))
    width, height = landscape(letter)
    logo_width, logo_height, logo_margin = 100, 100, 15

    config = None
    try:
        config = Configuracion.objects.order_by('-fechaConfiguracion').first()
    except Exception:
        pass
    logo_path = config.logo.path if config and config.logo else None
    firma_path = config.firma.path if config and config.firma else None
    nombre_institucion = config.nombreInstitucion if config else "Institución"
    rif_institucion = config.rif if config else ""

    safe_left = logo_margin
    safe_right = width - logo_margin
    safe_width = safe_right - safe_left

    # --- Define encabezado y pie ---
    def draw_header():
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
        text_top = height - logo_margin - 15

        p.setFont("Helvetica-Bold", 10)
        p.drawString(logo_margin, text_top, nombre_institucion)
        p.drawString(logo_margin, text_top - 20, f"RIF: {rif_institucion}")
        p.drawString(logo_margin, text_top - 40, "AV. ALBERTO RAVELL CON AV. INTERCOMUNAL JOSE ANTONIO PAEZ,")
        p.drawString(logo_margin, text_top - 60, "LOCAL UPTYAB, INDEPENDENCIA – EDO YARACUY")
        # Título alineado a la izquierda
        p.setFont("Helvetica-Bold", 13)
        p.drawCentredString(width / 2, text_top - 100, "Reporte de Empresas")

    def draw_footer():
        if firma_path and os.path.exists(firma_path):
            p.drawImage(firma_path, width/2 - 60, 60, width=120, height=60, preserveAspectRatio=True, mask='auto')
            p.setFont("Helvetica-Oblique", 10)
            p.drawCentredString(width/2, 40, "Firma autorizada")

    # --- Datos de la tabla ---
    data = [
        [
            "ID",
            "Nombre",
            "RIF",
            "Dirección",
            "Correo",
            "Teléfono",
            "Estado",
            "Fecha Registro"
        ]
    ]
    for emp in empresas:
        data.append([
            str(getattr(emp, 'idEmpresa', '')),
            getattr(emp, 'nombreEmpresa', ''),
            getattr(emp, 'rifEmpresa', ''),
            getattr(emp, 'direccionEmpresa', ''),
            getattr(emp, 'correoEmpresa', ''),
            getattr(emp, 'telefonoEmpresa', ''),
            "Activo" if getattr(emp, 'estadoEmpresa', False) else "Inactivo",
            emp.fechaEmpresa.strftime("%d/%m/%Y %H:%M") if hasattr(emp, 'fechaEmpresa') and emp.fechaEmpresa else ''
        ])
    # Definir el ancho de cada columna (ajustar según necesidad)
    col_widths = [40, 100, 140, 200, 140, 100, 80, 100]
    # Ajustar márgenes y tamaño de hoja dinámicamente según el ancho de la tabla
    min_margin = 30
    table_width = sum(col_widths)
    default_width, default_height = landscape(letter)

    # Si la tabla es más ancha que la hoja menos márgenes, aumentar el ancho de la hoja
    if table_width + 2 * min_margin > default_width:
        width = table_width + 2 * min_margin
    else:
        width = default_width
    height = default_height
    safe_left = min_margin
    safe_right = width - min_margin
    safe_width = safe_right - safe_left

    # Reiniciar el canvas con el nuevo tamaño si cambió el ancho
    if width != default_width:
        p._pagesize = (width, height)

    # --- Cálculo de espacio ---
    header_height = 140
    footer_height = 160
    row_height = 22
    available_height = height - header_height - footer_height

    max_rows_per_page = int(available_height // row_height)
    if max_rows_per_page < 1:
        max_rows_per_page = 1

    total_rows = len(data) - 1
    page = 0

    for start_row in range(0, total_rows, max_rows_per_page):
        end_row = start_row + max_rows_per_page
        page_data = [data[0]] + data[start_row + 1:end_row + 1]
        if page > 0:
            p.showPage()
        draw_header()
        y = height - header_height
        # Centrar la tabla horizontalmente
        table_x = safe_left + (safe_width - table_width) / 2
        table = Table(page_data, colWidths=col_widths)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#fe8330")),
            ('TEXTCOLOR', (0,0), (-1,0), colors.white),
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('FONTSIZE', (0,0), (-1,0), 12),
            ('BOTTOMPADDING', (0,0), (-1,0), 10),
            ('BACKGROUND', (0,1), (-1,-1), colors.whitesmoke),
            ('GRID', (0,0), (-1,-1), 1, colors.black),
        ]))
        table.wrapOn(p, width, height)
        table.drawOn(p, table_x, y - row_height * len(page_data))
        draw_footer()
        page += 1

    p.save()
    return response