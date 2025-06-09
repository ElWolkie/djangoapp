from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, HttpResponse
from django.urls import reverse
from django.contrib.auth.decorators import login_required
from .models import AsientoContable, DetalleAsiento
from .forms import AsientoContableForm, DetalleAsientoForm
from django.db import transaction
from apps.periodoContable.models import periodoContable  # Importa el modelo de Periodos Contables
from apps.planCuenta.models import PlanCuenta  # Importa el modelo PlanCuenta
from apps.home.models import Configuracion
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter, landscape
from reportlab.platypus import Table, TableStyle
from reportlab.lib import colors
import os

def asiento_contable_detalles(request, pk):
    """
    Vista para obtener los detalles de un asiento contable en formato JSON.
    """
    try:
        asiento = get_object_or_404(AsientoContable, pk=pk)
        detalles = asiento.detalles.select_related('idPlanCuenta').all()
        detalles_data = [
            {
                'codigoPlanCuenta': detalle.idPlanCuenta.codigoPlanCuenta,
                'nombrePlanCuenta': detalle.idPlanCuenta.nombrePlanCuenta,
                'debe': float(detalle.debe),
                'haber': float(detalle.haber),
            }
            for detalle in detalles
        ]
        return JsonResponse({'success': True, 'detalles': detalles_data})
    except AsientoContable.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'El asiento contable no existe.'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'error': f'Ocurrió un error inesperado: {str(e)}'}, status=500)

def asiento_contable_list(request):
    """
    Vista para listar todos los asientos contables.
    """
    asientos = AsientoContable.objects.all().order_by('fechaAsiento', 'numeroAsiento')
    return render(request, 'asientoContable/tablaAsientoContable.html', {'asientos': asientos})

@login_required(login_url='login')
def asiento_contable_create(request):
    """
    Vista para crear un nuevo asiento contable.
    """
    periodos = periodoContable.objects.all()  # Obtén todos los periodos contables
    if request.method == 'POST':
        form = AsientoContableForm(request.POST)
        if form.is_valid():
            asiento = form.save()
            # Redirigir a detalle_asiento_create con el pk del asiento recién creado
            return JsonResponse({
                'success': True,
                'message': 'Asiento contable registrado exitosamente.',
                'redirect_url': reverse('detalle_asiento_create', kwargs={'pk': asiento.idAsiento})
            })
        else:
            return JsonResponse({
                'success': False,
                'errors': form.errors
            })
    else:
        form = AsientoContableForm()
    return render(request, 'asientoContable/asientoContable.html', {
        'form': form,
        'titulo': 'Nuevo Asiento Contable',
        'periodos': periodos  # Pasa los periodos al contexto
    })

def asiento_contable_detail(request, pk):
    """
    Vista para mostrar los detalles de un asiento contable.
    """
    asiento = get_object_or_404(AsientoContable, pk=pk)
    detalles = asiento.detalles.all()
    return render(request, 'asientoContable/detalleAsiento.html', {'asiento': asiento, 'detalles': detalles})

@login_required(login_url='login')
def editar_asiento(request, pk):
    """
    Vista para actualizar un asiento contable.
    """
    asiento = get_object_or_404(AsientoContable, idAsiento=pk)
    periodos = periodoContable.objects.all()  # Trae todos los periodos contables

    if request.method == 'POST':
        form = AsientoContableForm(request.POST, instance=asiento)
        if form.is_valid():
            form.save()
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'message': 'Asiento editado correctamente.',
                    'redirect_url': reverse('asiento_contable_list')
                })
            else:
                return redirect('asiento_contable_list')
        else:
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': False,
                    'errors': form.errors
                })
    else:
        form = AsientoContableForm(instance=asiento)

    context = {
        'form': form,
        'titulo': 'Editar Asiento Contable',
        'asiento': asiento,
        'periodos': periodos,
    }
    return render(request, 'asientoContable/editarAsientoContable.html', context)


def detalle_asiento_create(request, pk):
    """
    Vista para agregar un detalle a un asiento contable.
    """
    asiento = get_object_or_404(AsientoContable, pk=pk)
    planes_cuenta = PlanCuenta.objects.filter(estadoPlanCuenta=True)  # Obtén solo los planes de cuenta activos
    if request.method == 'POST':
        form = DetalleAsientoForm(request.POST)
        if form.is_valid():
            try:
                detalle = form.save(commit=False)
                detalle.idAsiento = asiento
                detalle.save()
                return JsonResponse({
                    'success': True,
                    'message': 'Detalle de asiento registrado correctamente.',
                    'redirect_url': reverse('asiento_contable_list')  # Cambiar a la lista de asientos
                })
            except Exception as e:
                if 'duplicate' in str(e).lower():
                    return JsonResponse({
                        'success': False,
                        'error': 'Ya existe un registro con los mismos datos. Por favor, verifica la información.'
                    })
                return JsonResponse({
                    'success': False,
                    'error': f'Ocurrió un error inesperado: {str(e)}'
                })
        else:
            return JsonResponse({
                'success': False,
                'errors': form.errors
            })
    else:
        form = DetalleAsientoForm()
    return render(request, 'asientoContable/detalleAsiento.html', {
        'form': form,
        'asiento': asiento,
        'planes_cuenta': planes_cuenta,  # Pasa los planes de cuenta al contexto
        'titulo': 'Agregar Detalle'
    })


def editar_asiento_detalle(request, pk):
    """
    Vista para actualizar un detalle de asiento contable.
    """
    detalle = get_object_or_404(DetalleAsiento, pk=pk)
    planes_cuenta = PlanCuenta.objects.filter(estadoPlanCuenta=True)  # Obtén solo los planes de cuenta activos
    if request.method == 'POST':
        form = DetalleAsientoForm(request.POST, instance=detalle)
        if form.is_valid():
            form.save()
            return redirect('asiento_contable_detail', pk=detalle.idAsiento.idAsiento)
    else:
        form = DetalleAsientoForm(instance=detalle)
    return render(request, 'asientoContable/detalleAsiento.html', {
        'form': form,
        'detalle': detalle,
        'planes_cuenta': planes_cuenta,  # Pasa los planes de cuenta al contexto
        'titulo': 'Editar Detalle'
    })

@login_required(login_url='login')
def desactivar_asiento(request, id):
    asiento_obj = get_object_or_404(AsientoContable, idAsiento=id)
    if request.method == 'POST':
        asiento_obj.estadoAsiento = False
        asiento_obj.save()
        return JsonResponse({'success': True, 'message': f'⛔ Asiento {getattr(asiento_obj, "nombre", asiento_obj.idAsiento)} desactivado'})
    return JsonResponse({'success': False, 'message': 'Solicitud no válida.'}, status=400)

@login_required(login_url='login')
def reactivar_asiento(request, id):
    asiento_obj = get_object_or_404(AsientoContable, idAsiento=id)
    if request.method == 'POST':
        asiento_obj.estadoAsiento = True
        asiento_obj.save()
        return JsonResponse({'success': True, 'message': f'✅  {getattr(asiento_obj, "nombre", asiento_obj.idAsiento)} reactivado'})
    return JsonResponse({'success': False, 'message': 'Solicitud no válida.'}, status=400)

def reporte_asientos_pdf(request):
    # Selección de cantidad de registros
    start = int(request.GET.get('start', 1))
    end = int(request.GET.get('end', 0))
    asientos = list(AsientoContable.objects.all())
    if end == 0 or end > len(asientos):
        end = len(asientos)
    asientos = asientos[start-1:end]

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="reporte_asientos.pdf"'
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
        p.drawCentredString(width / 2, text_top - 100, "Reporte de Asientos Contables")

    def draw_footer():
        if firma_path and os.path.exists(firma_path):
            p.drawImage(firma_path, width/2 - 60, 60, width=120, height=60, preserveAspectRatio=True, mask='auto')
            p.setFont("Helvetica-Oblique", 10)
            p.drawCentredString(width/2, 40, "Firma autorizada")

    # --- Datos de la tabla ---
    data = [
        [
            "Número",
            "Fecha",
            "Concepto",
            "Periodo",
        ]
    ]
    for asiento in asientos:
        data.append([
            str(getattr(asiento, 'idAsiento', '')),
            asiento.fechaAsiento.strftime("%d/%m/%Y %H:%M") if hasattr(asiento, 'fechaAsiento') and asiento.fechaAsiento else '',
            getattr(asiento, 'conceptoAsiento', ''),
            getattr(asiento.idPeriodo, 'nombrePeriodo', '') if hasattr(asiento, 'idPeriodo') and asiento.idPeriodo else '',
        ])
    # Definir el ancho de cada columna (ajustar según necesidad)
    col_widths = [60, 100, 80, 70]
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

def tabla_asiento(request):
    mostrar = request.GET.get('mostrar_inactivos', 'false') == 'true'
    if mostrar:
        asientos = AsientoContable.objects.all()
    else:
        asientos = AsientoContable.objects.filter(estadoAsientoContable='ACTIVO')
    return render(request, 'asiento/tablaAsientoContable.html', {
        'asientos': asientos,
        'mostrar_inactivos': mostrar,
    })
