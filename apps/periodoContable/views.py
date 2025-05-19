from django.shortcuts import render, get_object_or_404
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
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import redirect

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
def desactivar_periodo_contable(request, id):
    periodo = get_object_or_404(periodoContable, idPeriodo=id)
    if request.method == 'POST':
        periodo.estadoPeriodo = False
        periodo.save()
        return JsonResponse({'success': True, 'message': f'⛔ Periodo Contable {getattr(periodo, "nombrePeriodo", periodo.pk)} desactivado'})
    return JsonResponse({'success': False, 'message': 'Solicitud no válida.'}, status=400)

@login_required(login_url='login')
def reactivar_periodo_contable(request, id):
    periodo = get_object_or_404(periodoContable, idPeriodo=id)
    if request.method == 'POST':
        periodo.estadoPeriodo = True
        periodo.save()
        return JsonResponse({'success': True, 'message': f'✅ Periodo Contable {getattr(periodo, "nombrePeriodo", periodo.pk)} activado'})
    return JsonResponse({'success': False, 'message': 'Solicitud no válida.'}, status=400)

def reporte_periodos_pdf(request):
    # Selección de cantidad de registros
    start = int(request.GET.get('start', 1))
    end = int(request.GET.get('end', 0))
    periodos = list(periodoContable.objects.all())
    if end == 0 or end > len(periodos):
        end = len(periodos)
    periodos = periodos[start-1:end]

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="reporte_periodos.pdf"'
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
        p.drawString( logo_margin, text_top - 40, "AV. ALBERTO RAVELL CON AV. INTERCOMUNAL JOSE ANTONIO PAEZ,")
        p.drawString( logo_margin, text_top - 60, "LOCAL UPTYAB, INDEPENDENCIA – EDO YARACUY")
        # Título alineado a la izquierda
        p.setFont("Helvetica-Bold", 13)
        p.drawCentredString(width / 2, text_top - 100, "Reporte de Cargos")

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
            "Fecha Inicio",
            "Fecha Fin",
            "Estado",
            "Fecha Digital"
        ]
    ]
    for per in periodos:
        data.append([
            str(getattr(per, 'idPeriodo', '')),
            getattr(per, 'nombrePeriodo', ''),
            per.fechaInicioPeriodo.strftime("%d/%m/%Y") if hasattr(per, 'fechaInicioPeriodo') else '',
            per.fechaFinPeriodo.strftime("%d/%m/%Y") if hasattr(per, 'fechaFinPeriodo') else '',
            "Activo" if getattr(per, 'estadoPeriodo', False) else "Inactivo",
            per.fechaPeriodoDigital.strftime("%d/%m/%Y %H:%M") if hasattr(per, 'fechaPeriodoDigital') else ''
        ])
    col_widths = [40, 120, 80, 80, 60, 100]
    table_width = sum(col_widths)

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