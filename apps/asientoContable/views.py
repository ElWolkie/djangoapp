from datetime import datetime
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, HttpResponse
from django.urls import reverse
from django.contrib.auth.decorators import login_required, permission_required
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

@login_required(login_url='login')
@permission_required("asientoContable.view_asientocontable", raise_exception=True)
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

@login_required(login_url='login')
@permission_required("asientoContable.view_asientocontable", raise_exception=True)
def asiento_contable_list(request):
    """
    Vista para listar todos los asientos contables.
    """
    asientos = AsientoContable.objects.all().order_by('fechaAsiento', 'numeroAsiento')
    return render(request, 'asientoContable/tablaAsientoContable.html', {'asientos': asientos})

@login_required(login_url='login')
@permission_required("asientoContable.add_asientocontable", raise_exception=True)
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

@login_required(login_url='login')
@permission_required("asientoContable.view_asientocontable", raise_exception=True)
def asiento_contable_detail(request, pk):
    """
    Vista para mostrar los detalles de un asiento contable.
    """
    asiento = get_object_or_404(AsientoContable, pk=pk)
    detalles = asiento.detalles.all()
    return render(request, 'asientoContable/detalleAsiento.html', {'asiento': asiento, 'detalles': detalles})

@login_required(login_url='login')
@permission_required("asientoContable.change_asientocontable", raise_exception=True)
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

@login_required(login_url='login')
@permission_required("asientoContable.add_detalleasiento", raise_exception=True)
def detalle_asiento_create(request, pk):
    """
    Vista para agregar un detalle a un asiento contable.
    """
    asiento = get_object_or_404(AsientoContable, pk=pk)
    planes_cuenta = PlanCuenta.objects.filter(estadoPlanCuenta=True)  # Obtén solo los planes de cuenta activos
    detalles = asiento.detalles.select_related('idPlanCuenta').all()  # Obtener los detalles del asiento

    # Transformar los detalles para incluir los atributos necesarios
    detalles_data = [
        {
            'codigoPlanCuenta': detalle.idPlanCuenta.codigoPlanCuenta,
            'nombrePlanCuenta': detalle.idPlanCuenta.nombrePlanCuenta,
            'debe': detalle.debe,
            'haber': detalle.haber,
        }
        for detalle in detalles
    ]

    if request.method == 'POST':
        form = DetalleAsientoForm(request.POST)
        if form.is_valid():
            if detalles.count() >= 2 and not request.POST.get('confirmar', False):
                return JsonResponse({
                    'success': False,
                    'confirm_required': True,
                    'message': 'El asiento ya posee dos registros de detalles asociados. ¿Desea continuar?'
                })
            try:
                detalle = form.save(commit=False)
                detalle.idAsiento = asiento
                detalle.save()
                return JsonResponse({
                    'success': True,
                    'message': 'Detalle registrado exitosamente.',
                    'redirect_url': reverse('asiento_contable_list')
                })
            except Exception as e:
                return JsonResponse({
                    'success': False,
                    'errors': str(e)
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
        'detalles': detalles_data,  # Pasa los detalles transformados al contexto
        'titulo': 'Agregar Detalle'
    })

@login_required(login_url='login')
@permission_required("asientoContable.change_detalleasiento", raise_exception=True)
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
@permission_required("asientoContable.change_asientocontable", raise_exception=True)
def desactivar_asiento(request, id):
    asiento_obj = get_object_or_404(AsientoContable, idAsiento=id)
    if request.method == 'POST':
        asiento_obj.estadoAsiento = False
        asiento_obj.save()
        return JsonResponse({'success': True, 'message': f'⛔ Asiento {getattr(asiento_obj, "nombre", asiento_obj.idAsiento)} desactivado'})
    return JsonResponse({'success': False, 'message': 'Solicitud no válida.'}, status=400)

@login_required(login_url='login')
@permission_required("asientoContable.change_asientocontable", raise_exception=True)
def reactivar_asiento(request, id):
    asiento_obj = get_object_or_404(AsientoContable, idAsiento=id)
    if request.method == 'POST':
        asiento_obj.estadoAsiento = True
        asiento_obj.save()
        return JsonResponse({'success': True, 'message': f'✅  {getattr(asiento_obj, "nombre", asiento_obj.idAsiento)} reactivado'})
    return JsonResponse({'success': False, 'message': 'Solicitud no válida.'}, status=400)

@login_required(login_url='login')
def reporte_asientos_pdf(request):
    # Manejo de parámetros de paginación
    start = int(request.GET.get('start', 1))
    end = int(request.GET.get('end', 0))
    asientos = list(AsientoContable.objects.all())
    
    if end == 0 or end > len(asientos):
        end = len(asientos)
    asientos = asientos[start-1:end]

    # Configuración inicial del PDF
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'inline; filename="reporte_asientos_contables.pdf"'
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
        p.drawCentredString(safe_center, text_top - 85, "REPORTE DE ASIENTOS CONTABLES")

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
    headers = ["NÚMERO", "FECHA", "CONCEPTO", "PERIODO"]
    data = [headers]
    
    for asiento in asientos:
        data.append([
            str(asiento.idAsiento),
            asiento.fechaAsiento.strftime("%d/%m/%Y") if asiento.fechaAsiento else '',
            asiento.conceptoAsiento[:50] + '...' if len(asiento.conceptoAsiento) > 50 else asiento.conceptoAsiento,
            asiento.idPeriodo.nombrePeriodo if asiento.idPeriodo else ''
        ])
    
    # Configuración de la tabla
    col_widths = [70, 80, 200, 100]  # Anchos ajustados
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
            ('ALIGN', (2,1), (2,-1), 'LEFT'),
            ('VALIGN', (0,1), (-1,-1), 'MIDDLE'),
            ('BACKGROUND', (0,1), (-1,-1), colors.whitesmoke),
            ('GRID', (0,0), (-1,-1), 0.5, colors.lightgrey),
            ('BOX', (0,0), (-1,-1), 0.5, colors.black),
            ('TOPPADDING', (0,1), (-1,-1), cell_padding),
            ('BOTTOMPADDING', (0,1), (-1,-1), cell_padding),
        ])
        
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
