from datetime import datetime
from django.shortcuts import render, get_object_or_404
from django.http import HttpResponseRedirect, JsonResponse, HttpResponse
from django.contrib.auth.decorators import login_required, permission_required
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

@login_required(login_url='login')
@permission_required("planCuenta.view_plancuenta", raise_exception=True)
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

@login_required(login_url='login')
@permission_required("planCuenta.view_plancuenta", raise_exception=True)
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

@login_required(login_url='login')
@permission_required("planCuenta.add_plancuenta", raise_exception=True)
def plan_cuenta_create(request):
    """
    Vista para crear un nuevo plan de cuenta.
    Excluye los registros de PlanCuenta que ya están referenciados en CuentaBanco
    o que están relacionados con los bancos.
    """
    print("plan_cuenta_create: request.method =", request.method)
    if request.method == 'POST':
        print("POST data:", dict(request.POST))
        form = PlanCuentaForm(request.POST)
        if form.is_valid():
            print("Form válido. Guardando nuevo PlanCuenta...")
            with transaction.atomic():
                plan = form.save()
                print("Plan creado con id:", getattr(plan, 'idPlanCuenta', None))
                return JsonResponse({
                    'success': True,
                    'message': 'Plan de Cuenta creado exitosamente!',
                    'redirect_url': reverse('plan_cuenta_list')
                })
        else:
            print("Form inválido. Errores:", form.errors)
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
        
        # Imprimo información de depuración sobre lo que se obtiene
        try:
            print("SQL cuentas_referenciadas:", str(cuentas_referenciadas.query))
        except Exception as e:
            print("No se pudo obtener SQL de cuentas_referenciadas:", e)
        try:
            print("SQL bancos_referenciados:", str(bancos_referenciados.query))
        except Exception as e:
            print("No se pudo obtener SQL de bancos_referenciados:", e)

        # Muestras limitadas para no traer todo a memoria
        try:
            cuentas_muestra = list(CuentaBanco.objects.values_list('planCuenta_id', flat=True)[:20])
            bancos_muestra = list(Banco.objects.values_list('codigoPlanCuenta_id', flat=True)[:20])
            print("Muestra cuentas_referenciadas (hasta 20 ids):", cuentas_muestra)
            print("Muestra bancos_referenciados (hasta 20 ids):", bancos_muestra)
        except Exception as e:
            print("Error al obtener muestras de ids:", e)
        
        # Excluir los registros de PlanCuenta que están referenciados en CuentaBanco o relacionados con los bancos
        cuentas_padre = PlanCuenta.objects.filter(
            estadoPlanCuenta=True
        ).exclude(
            Q(idPlanCuenta__in=Subquery(cuentas_referenciadas)) | Q(idPlanCuenta__in=Subquery(bancos_referenciados))
        ).order_by('codigoPlanCuenta')
        
        try:
            print("Query cuentas_padre (SQL):", str(cuentas_padre.query))
            print("Cantidad cuentas_padre resultantes:", cuentas_padre.count())
            print("Primeras 10 cuentas_padre (id, codigo, nombre):",
                  list(cuentas_padre.values_list('idPlanCuenta', 'codigoPlanCuenta', 'nombrePlanCuenta')[:10]))
        except Exception as e:
            print("Error al evaluar cuentas_padre:", e)
        
        return render(request, 'planCuenta/planCuenta.html', {
            'form': form,
            'cuentas_padre': cuentas_padre,  # Se pasa correctamente al template
            'titulo': 'Nuevo Plan de Cuenta'
        })

@login_required(login_url='login')
@permission_required("planCuenta.change_plancuenta", raise_exception=True)
def editar_plan(request, pk):
    plan_obj = get_object_or_404(PlanCuenta, idPlanCuenta=pk)
    if request.method == 'POST':
        form = PlanCuentaForm(request.POST, instance=plan_obj)
        if form.is_valid():
            form.save()
            # Si es AJAX devolver JSON (para el handler JS)
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'message': 'Plan de Cuenta actualizado exitosamente.',
                    'redirect_url': reverse('plan_cuenta_list')
                })
            # Si no es AJAX, redirigir normalmente
            return HttpResponseRedirect(reverse('plan_cuenta_list'))
        else:
            # Errores: si AJAX enviamos JSON con errores, si no, renderizamos la plantilla con errores
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                # convertir errores QueryDict->listas para JSON si hace falta
                errors = {k: list(v) for k, v in form.errors.items()}
                return JsonResponse({'success': False, 'errors': errors}, status=400)
            else:
                # render con errores (para envío tradicional)
                nivel_actual = plan_obj.nivelPlanCuenta
                cuentas_padre = PlanCuenta.objects.filter(
                    estadoPlanCuenta=True,
                    nivelPlanCuenta__lt=nivel_actual
                ).exclude(idPlanCuenta=plan_obj.idPlanCuenta).order_by('codigoPlanCuenta')
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
    else:
        form = PlanCuentaForm(instance=plan_obj)
        nivel_actual = plan_obj.nivelPlanCuenta
        cuentas_padre = PlanCuenta.objects.filter(
            estadoPlanCuenta=True,
            nivelPlanCuenta__lt=nivel_actual
        ).exclude(idPlanCuenta=plan_obj.idPlanCuenta).order_by('codigoPlanCuenta')
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
@permission_required("planCuenta.change_plancuenta", raise_exception=True)
def desactivar_plan(request, id):
    plan_obj = get_object_or_404(PlanCuenta, idPlanCuenta=id)
    if request.method == 'POST':
        plan_obj.estadoPlanCuenta = False
        plan_obj.save()
        return JsonResponse({'success': True, 'message': f'⛔ Plan de Cuenta {getattr(plan_obj, "nombre", plan_obj.idPlanCuenta)} desactivado'})
    return JsonResponse({'success': False, 'message': 'Solicitud no válida.'}, status=400)

@login_required(login_url='login')
@permission_required("planCuenta.change_plancuenta", raise_exception=True)
@login_required(login_url='login')
def reactivar_plan(request, id):
    plan_obj = get_object_or_404(PlanCuenta, idPlanCuenta=id)
    if request.method == 'POST':
        plan_obj.estadoPlanCuenta = True
        plan_obj.save()
        return JsonResponse({'success': True, 'message': f'✅  {getattr(plan_obj, "nombre", plan_obj.idPlanCuenta)} reactivada'})
    return JsonResponse({'success': False, 'message': 'Solicitud no válida.'}, status=400)


@login_required(login_url='login')
def reporte_planes_pdf(request):
    # Manejo de parámetros de paginación
    start = int(request.GET.get('start', 1))
    end = int(request.GET.get('end', 0))
    planes = list(PlanCuenta.objects.all())
    
    if end == 0 or end > len(planes):
        end = len(planes)
    planes = planes[start-1:end]

    # Configuración inicial del PDF
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'inline; filename="reporte_planes_cuenta.pdf"'
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
        p.drawCentredString(safe_center, text_top - 85, "REPORTE DE PLAN DE CUENTAS")

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
    headers = ["CÓDIGO", "NOMBRE", "TIPO", "NIVEL", "ESTADO", "FECHA"]
    data = [headers]
    
    for plan in planes:
        data.append([
            str(plan.codigoPlanCuenta),
            plan.nombrePlanCuenta,
            plan.tipoPlanCuenta.capitalize(),
            str(plan.nivelPlanCuenta),
            "Activo" if plan.estadoPlanCuenta else "Inactivo",
            plan.fechaPlanCuenta.strftime("%d/%m/%Y")
        ])
    
    # Configuración de la tabla
    col_widths = [70, 200, 80, 50, 60, 70]
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
