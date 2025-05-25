from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponse
from django.contrib.auth.decorators import login_required
from django.db.models import Subquery, Q
from django.db import transaction
from django.urls import reverse
from .models import PlanCuenta
from .forms import PlanCuentaForm
from apps.cuentaBanco.models import CuentaBanco, Banco
import os
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter, landscape
from reportlab.platypus import Table, TableStyle
from reportlab.lib import colors
from apps.home.models import Configuracion

def plan_cuenta_list(request):
    """
    Vista para listar todos los planes de cuenta existentes.
    Permite mostrar también los inactivos si se solicita.
    """
    mostrar_inactivos = request.GET.get('mostrar_inactivos') == 'true'
    if mostrar_inactivos:
        planes = PlanCuenta.objects.all().order_by('codigoPlanCuenta')
    else:
        planes = PlanCuenta.objects.filter(estadoPlanCuenta=True).order_by('codigoPlanCuenta')
    return render(request, 'planCuenta/tablaPlanCuenta.html', {
        'planes': planes,
        'mostrar_inactivos': mostrar_inactivos,
        'titulo': 'Listado de Planes de Cuenta'
    })

def plan_cuenta_detail(request, pk):
    """
    Vista para mostrar los detalles de un plan de cuenta específico.
    """
    plan = get_object_or_404(PlanCuenta, pk=pk)
    subcuentas = plan.subcuentas.filter(estadoPlanCuenta=True)
    return render(request, 'planCuenta/detallePlanCuenta.html', {
        'plan': plan,
        'subcuentas': subcuentas
    })


def plan_cuenta_create(request):
    """
    Vista para crear un nuevo plan de cuenta.
    Excluye los registros de PlanCuenta que ya están referenciados en CuentaBanco
    o que están relacionados con los bancos.
    """
    if request.method == 'POST':
        form = PlanCuentaForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                plan = form.save()
                return JsonResponse({
                    'success': True,
                    'message': 'Plan de Cuenta creado exitosamente!',
                    'redirect_url': reverse('plan_cuenta_list')
                })
        else:
            return JsonResponse({
                'success': False,
                'errors': form.errors
            })
    else:
        form = PlanCuentaForm()
        
        # Subconsulta para obtener los IDs de PlanCuenta referenciados en CuentaBanco
        cuentas_referenciadas = CuentaBanco.objects.values('planCuenta_id')
        
        # Subconsulta para obtener los IDs de PlanCuenta relacionados con los bancos
        bancos_referenciados = Banco.objects.values('codigoPlanCuenta_id')
        
        # Excluir los registros de PlanCuenta que están referenciados en CuentaBanco o relacionados con los bancos
        cuentas_padre = PlanCuenta.objects.filter(
            estadoPlanCuenta=True
        ).exclude(
            Q(idPlanCuenta__in=Subquery(cuentas_referenciadas)) | Q(idPlanCuenta__in=Subquery(bancos_referenciados))
        ).order_by('codigoPlanCuenta')
        
        return render(request, 'planCuenta/planCuenta.html', {
            'form': form,
            'cuentas_padre': cuentas_padre,  # Se pasa correctamente al template
            'titulo': 'Nuevo Plan de Cuenta'
        })



def editar_plan(request, pk):
    plan_obj = get_object_or_404(PlanCuenta, idPlanCuenta=pk)
    if request.method == 'POST':
        form = PlanCuentaForm(request.POST, instance=plan_obj)
        if form.is_valid():
            form.save()
            return JsonResponse({
                'success': True,
                'message': 'Plan de Cuenta actualizado exitosamente.',
                'redirect_url': reverse('plan_cuenta_list')
            })
        else:
            return JsonResponse({'success': False, 'errors': form.errors})
    else:
        form = PlanCuentaForm(instance=plan_obj)
        # Solo mostrar como posibles padres:
        # - cuentas activas
        # - nivel menor al de la cuenta actual
        # - que no sean la cuenta actual
        nivel_actual = plan_obj.nivelPlanCuenta
        cuentas_padre = PlanCuenta.objects.filter(
            estadoPlanCuenta=True,
            nivelPlanCuenta__lt=nivel_actual  # Solo niveles menores
        ).exclude(
            idPlanCuenta=plan_obj.idPlanCuenta  # No puede ser su propio padre
        ).order_by('codigoPlanCuenta')
        return render(request, 'planCuenta/editarPlanCuenta.html', {
            'form': form,
            'plan': plan_obj,
            'cuentas_padre': cuentas_padre,
            'idPlan': plan_obj.idPlanCuenta,
            'nombrePlan': plan_obj.nombrePlanCuenta,
            'codigoPlan': plan_obj.codigoPlanCuenta,
            'tipoPlan': plan_obj.tipoPlanCuenta,
            'nivelPlan': plan_obj.nivelPlanCuenta,
            'cuentaPadre': plan_obj.cuentaPadre,
            'estadoPlan': plan_obj.estadoPlanCuenta,
            'fechaPlan': plan_obj.fechaPlanCuenta,
        })

@login_required(login_url='login')
def desactivar_plan(request, id):
    plan_obj = get_object_or_404(PlanCuenta, idPlanCuenta=id)
    if request.method == 'POST':
        plan_obj.estadoPlanCuenta = False
        plan_obj.save()
        return JsonResponse({'success': True, 'message': f'⛔ Plan de Cuenta {getattr(plan_obj, "nombre", plan_obj.idPlanCuenta)} desactivado'})
    return JsonResponse({'success': False, 'message': 'Solicitud no válida.'}, status=400)

@login_required(login_url='login')
def reactivar_plan(request, id):
    plan_obj = get_object_or_404(PlanCuenta, idPlanCuenta=id)
    if request.method == 'POST':
        plan_obj.estadoPlanCuenta = True
        plan_obj.save()
        return JsonResponse({'success': True, 'message': f'✅  {getattr(plan_obj, "nombre", plan_obj.idPlanCuenta)} reactivada'})
    return JsonResponse({'success': False, 'message': 'Solicitud no válida.'}, status=400)

def reporte_planes_pdf(request):
    # Selección de cantidad de registros
    start = int(request.GET.get('start', 1))
    end = int(request.GET.get('end', 0))
    planes = list(PlanCuenta.objects.all())
    if end == 0 or end > len(planes):
        end = len(planes)
    planes = planes[start-1:end]

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="reporte_planes.pdf"'
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
        p.drawCentredString(width / 2, text_top - 100, "Reporte de planes")

    def draw_footer():
        if firma_path and os.path.exists(firma_path):
            p.drawImage(firma_path, width/2 - 60, 60, width=120, height=60, preserveAspectRatio=True, mask='auto')
            p.setFont("Helvetica-Oblique", 10)
            p.drawCentredString(width/2, 40, "Firma autorizada")

    # --- Datos de la tabla ---
    data = [
        [
            "CODIGO",
            "NOMBRE",
            "TIPO",
            "NIVEL",
            "ESTADO",
            "Fecha"
        ]
    ]
    for plan in planes:
        data.append([
            str(getattr(plan, 'codigoPlanCuenta', '')),
            getattr(plan, 'nombrePlanCuenta', ''),
            getattr(plan, 'tipoPlanCuenta', ''),
            getattr(plan, 'nivelPlanCuenta', ''),
            "Activo" if getattr(plan, 'estadoPlanCuenta', False) else "Inactivo",
            plan.fechaPlanCuenta.strftime("%d/%m/%Y %H:%M") if hasattr(plan, 'fechaPlanCuenta') and plan.fechaPlanCuenta else ''
        ])
    # Definir el ancho de cada columna (ajustar según necesidad)
    col_widths = [80, 200, 100, 60, 80, 120]
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
