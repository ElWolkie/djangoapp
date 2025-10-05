from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required, permission_required
from django.urls import reverse
from django.contrib import messages
from django.db import transaction, IntegrityError
from django.http import JsonResponse
from .models import SaldoContable
from .forms import SaldoContableForm
from apps.planCuenta.models import PlanCuenta
from apps.periodoContable.models import periodoContable

from apps.home.models import Configuracion

from django.http import HttpResponse
from reportlab.lib.pagesizes import letter, landscape
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.platypus import Table, TableStyle
import os

def saldos_existentes_api(request):
    periodo_id = request.GET.get('periodo')
    if not periodo_id:
        return JsonResponse({}, status=400)
    saldos = SaldoContable.objects.filter(
        id_periodo_id=periodo_id
    ).values_list('id_plan_cuenta_id', flat=True)
    return JsonResponse({str(cuenta_id): True for cuenta_id in saldos})


@login_required(login_url='login')
@permission_required("saldoContable.add_saldocontable", raise_exception=True)
def saldo_contable_create(request):
    # Obtener datos que se usan en ambos casos (GET y POST)
    planes_cuenta = PlanCuenta.objects.filter(estadoPlanCuenta=True).order_by('codigoPlanCuenta')
    periodos = periodoContable.objects.filter(estadoPeriodo=False).order_by('-fechaInicioPeriodo')
    advertencia_text = (
        "Nota: Los saldos para períodos activos se generan automáticamente al crear el período. "
        "Solo puede crear saldos manualmente para períodos inactivos."
    )

    if request.method == 'POST':
        # Hacemos una copia mutable de request.POST
        post_data = request.POST.copy()
        # Convertir comas a puntos en los campos de saldo
        if 'saldo_inicial' in post_data:
            post_data['saldo_inicial'] = post_data['saldo_inicial'].replace(',', '.')
        if 'saldo_final' in post_data:
            post_data['saldo_final'] = post_data['saldo_final'].replace(',', '.')

        form = SaldoContableForm(post_data)
        is_ajax = request.headers.get('x-requested-with') == 'XMLHttpRequest'

        if form.is_valid():
            try:
                with transaction.atomic():
                    saldo = form.save()
                    
                    # Mensaje de éxito con contexto adicional
                    success_message = (
                        "Saldo Contable creado exitosamente. "
                        f"Plan: {saldo.id_plan_cuenta}, "
                        f"Período: {saldo.id_periodo}"
                    )
                    
                    if is_ajax:
                        return JsonResponse({
                            'success': True,
                            'message': success_message,
                            'redirect_url': reverse('saldo_contable_list')
                        })
                    
                    messages.success(request, success_message)
                    return redirect('saldo_contable_list')
            
            except IntegrityError as e:
                texto_error = str(e).lower()
                if 'unique' in texto_error or 'violates unique' in texto_error:
                    friendly = "Ya existe un Saldo Contable para ese Plan de Cuenta y Periodo."
                else:
                    friendly = "Ocurrió un error inesperado al guardar. Intente nuevamente."
                
                if is_ajax:
                    return JsonResponse({'success': False, 'message': friendly})
                
                messages.error(request, friendly)
        
        else:
            # Manejo de errores con mensajes específicos
            errores = form.errors.as_data()
            
            if is_ajax:
                errores_friendly = {
                    campo: [str(e.message) for e in lista]
                    for campo, lista in errores.items()
                }
                return JsonResponse({'success': False, 'errors': errores_friendly})
            
            for campo, lista in errores.items():
                for e in lista:
                    messages.error(request, e)
    
    else:
        form = SaldoContableForm()

    return render(request, 'saldoContable/saldoContable.html', {
        'form': form,
        'periodos': periodos,
        'planes_cuenta': planes_cuenta,
        'titulo': 'Nuevo Saldo Contable',
        'advertencia': advertencia_text
    })


@login_required(login_url='login')
@permission_required("saldoContable.view_saldocontable", raise_exception=True)
def saldo_contable_list(request):
    saldos = SaldoContable.objects.all().order_by('saldo_inicial', 'saldo_final')
    return render(request, 'saldoContable/tablaSaldoContable.html', {'saldos': saldos})

@login_required(login_url='login')
def reporte_saldos_pdf(request):
    # Selección de cantidad de registros
    start = int(request.GET.get('start', 1))
    end = int(request.GET.get('end', 0))
    saldos = list(SaldoContable.objects.select_related('id_plan_cuenta', 'id_periodo').all())
    
    if end == 0 or end > len(saldos):
        end = len(saldos)
    saldos = saldos[start-1:end]

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'inline; filename="reporte_saldos_contables.pdf"'
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
        p.drawCentredString(width / 2, text_top - 100, "Reporte de Saldos Contables")

    def draw_footer():
        if firma_path and os.path.exists(firma_path):
            p.drawImage(firma_path, width/2 - 60, 60, width=120, height=60, preserveAspectRatio=True, mask='auto')
            p.setFont("Helvetica-Oblique", 10)
            p.drawCentredString(width/2, 40, "Firma autorizada")

    # --- Datos de la tabla ---
    data = [
        [
            "ID",
            "PLAN DE CUENTA",
            "PERIODO",
            "SALDO INICIAL",
            "SALDO FINAL"
        ]
    ]
    
    for saldo in saldos:
        plan_cuenta = f"{saldo.id_plan_cuenta.codigoPlanCuenta} - {saldo.id_plan_cuenta.nombrePlanCuenta}"
        periodo = f"{saldo.id_periodo.nombrePeriodo} ({saldo.id_periodo.fechaInicioPeriodo.strftime('%d/%m/%Y')} - {saldo.id_periodo.fechaFinPeriodo.strftime('%d/%m/%Y')})"
        
        data.append([
            str(saldo.idSaldo),
            plan_cuenta,
            periodo,
            f"${saldo.saldo_inicial:,.2f}",
            f"${saldo.saldo_final:,.2f}"
        ])
    
    # Definir el ancho de cada columna (ajustar según necesidad)
    col_widths = [50, 250, 180, 100, 100]
    
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
        end_row = min(start_row + max_rows_per_page, total_rows)
        page_data = [data[0]] + data[start_row + 1:end_row + 1]
        
        if page > 0:
            p.showPage()
        
        draw_header()
        y = height - header_height
        
        # Centrar la tabla horizontalmente
        table_x = safe_left + (safe_width - table_width) / 2
        table = Table(page_data, colWidths=col_widths)
        
        # Estilos de la tabla
        table_style = TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#fe8330")),  # Encabezado naranja
            ('TEXTCOLOR', (0,0), (-1,0), colors.white),
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('ALIGN', (1,0), (1,-1), 'LEFT'),  # Alinear Plan de Cuenta a la izquierda
            ('ALIGN', (2,0), (2,-1), 'LEFT'),   # Alinear Periodo a la izquierda
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('FONTSIZE', (0,0), (-1,0), 10),
            ('FONTSIZE', (0,1), (-1,-1), 9),
            ('BOTTOMPADDING', (0,0), (-1,0), 10),
            ('BACKGROUND', (0,1), (-1,-1), colors.whitesmoke),
            ('GRID', (0,0), (-1,-1), 0.5, colors.black),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ])
        
        # Colores para los saldos
        for i in range(1, len(page_data)):
            # Saldo inicial en verde
            table_style.add('TEXTCOLOR', (3,i), (3,i), colors.HexColor("#28a745"))
            # Saldo final en azul
            table_style.add('TEXTCOLOR', (4,i), (4,i), colors.HexColor("#007bff"))
        
        table.setStyle(table_style)
        table.wrapOn(p, width, height)
        table.drawOn(p, table_x, y - row_height * len(page_data))
        
        # Información de rango de registros
        p.setFont("Helvetica", 9)
        p.drawString(table_x, y - row_height * len(page_data) - 20, 
                     f"Mostrando registros {start_row + 1} a {end_row} de {total_rows}")
        
        draw_footer()
        page += 1

    p.save()
    return response
