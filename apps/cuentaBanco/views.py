import io
import os
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, permission_required
from django.core.exceptions import ValidationError
from django.http import JsonResponse
from django.db.models import Max

from django.urls import reverse
from django.db import transaction
from apps.asientoContable.models import AsientoContable, DetalleAsiento
from datetime import date, datetime
from apps.periodoContable.models import periodoContable
from .models import Banco, CuentaBanco
from .forms import BancoForm, CuentaBancoForm
from apps.planCuenta.models import PlanCuenta
from apps.home.models import Configuracion, Moneda
from django.contrib import messages # Importar messages

from django.http import JsonResponse, HttpResponse
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Spacer
from reportlab.lib.units import mm
from django.core.paginator import Paginator
from django.db.models import Q

@login_required(login_url='login')
@permission_required("cuentaBanco.view_banco", raise_exception=True)
def banco_list(request):
    mostrar = request.GET.get('mostrar_inactivos', 'false') == 'true'
    search_query = request.GET.get('search', '').strip()  # Obtener el término de búsqueda

    if mostrar:
        bancos = Banco.objects.all()
    else:
        bancos = Banco.objects.filter(estadoBanco=True).order_by('nombreBanco')
    

          # Filtrar por el término de búsqueda si existe BUSCADOR
    if search_query:
        bancos = bancos.filter(
            Q(nombreBanco__icontains=search_query) |
            Q(codLocalBanco__icontains=search_query) |
            Q(codSwiftBanco__icontains=search_query) |
            Q(codigoPlanCuenta__codigoPlanCuenta__icontains=search_query) |
            Q(estadoBanco__icontains=search_query) |
            Q(fechaBanco__icontains=search_query)
        )
    paginator = Paginator(bancos, 10)  # 10 cuotas por página
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    return render(request, 'bancos/tablaBancos.html', {
        'bancos': page_obj,
        'titulo': 'Listado de Bancos',
        'mostrar_inactivos': mostrar,
        'search_query': search_query,  # Pasar el término de búsqueda al template

    })

@login_required(login_url='login')
@permission_required("cuentaBanco.view_banco", raise_exception=True)
def banco_detail(request, pk):
    """
    Vista para mostrar los detalles de un banco y sus cuentas asociadas.
    """
    banco = get_object_or_404(Banco, pk=pk)
    cuentas = banco.cuentabanco_set.filter(estado=True)
    return render(request, 'bancos/detalleBanco.html', {
        'banco': banco,
        'cuentas': cuentas
    })

@login_required(login_url='login')
@permission_required("cuentaBanco.add_banco", raise_exception=True)
def banco_create(request):
    if request.method == 'POST':
        form = BancoForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                banco = form.save()
                return JsonResponse({
                    'success': True,
                    'message': 'Banco registrado exitosamente.',
                    'redirect_url': reverse('banco_list')
                })
        else:
            return JsonResponse({
                'success': False,
                'errors': form.errors
            })
    else:
        form = BancoForm()
        planes = PlanCuenta.objects.filter(estadoPlanCuenta=True).order_by('codigoPlanCuenta')
        return render(request, 'bancos/banco.html', {
            'form': form,
            'planes': planes,
            'titulo': 'Registrar Banco'
        })
    

def is_ajax(request):
    return request.META.get('HTTP_X_REQUESTED_WITH') == 'XMLHttpRequest'

@login_required(login_url='login')
@permission_required("cuentaBanco.change_banco", raise_exception=True)
def banco_update(request, pk):
    """
    Vista para actualizar un banco existente (GET devuelve el modal, POST via AJAX guarda).
    """
    banco  = get_object_or_404(Banco, pk=pk)
    planes = PlanCuenta.objects.all()  # para los selectores

    # POST vía AJAX: procesar el formulario
    if request.method == 'POST' and is_ajax(request):
        form = BancoForm(request.POST, instance=banco)
        if form.is_valid():
            with transaction.atomic():
                form.save()
            return JsonResponse({
                'success': True,
                'message': 'Banco actualizado exitosamente!',
                'redirect_url': reverse('banco_list')
            })
        else:
            return JsonResponse({
                'success': False,
                'errors': form.errors
            })

    # GET: renderizamos el fragmento HTML para el modal
    form = BancoForm(instance=banco)
    return render(request, 'bancos/modales/editBanco.html', {
        'form': form,
        'banco': banco,
        'planes': planes,
        'titulo': 'Editar Banco',
        'editar': True,
    })

@login_required(login_url='login')
@permission_required("cuentaBanco.change_banco", raise_exception=True)
def banco_delete(request, pk):
    banco = get_object_or_404(Banco, pk=pk)
    # Actualizamos el estado sin modificar el nombre u otros campos únicos
    banco.estadoBanco = False
    try:
        banco.save()  # Aquí se ejecuta la validación en save()
        return JsonResponse({'success': True, 'message': 'Banco desactivado correctamente. ⛔'})
    except ValidationError as e:
        # Regresamos el mensaje de error; esto ocurriría si se dispara la validación única
        return JsonResponse({'success': False, 'message': e.messages})

@login_required(login_url='login')
@permission_required("cuentaBanco.change_banco", raise_exception=True)
def banco_reactivate(request, pk):
    banco = get_object_or_404(Banco, pk=pk)
    # Actualizamos el estado sin modificar el nombre u otros campos únicos
    banco.estadoBanco = True
    try:
        # Banco.objects.filter(pk=pk).update(estadoBanco=True)
        banco.save()  # Aquí se ejecuta la validación en save()
        return JsonResponse({'success': True, 'message': 'Banco reactivado correctamente. ✅'})
    except ValidationError as e:
        # Regresamos el mensaje de error; esto ocurriría si se dispara la validación única
        return JsonResponse({'success': False, 'message': e.messages})
    
@login_required(login_url='login')
@permission_required("cuentaBanco.view_banco", raise_exception=True)
def reporte_bancos_pdf(request):
    # Rango de registros (1-based inclusive)
    start = int(request.GET.get('start', 1))
    end = int(request.GET.get('end', 0))
    todos = list(Banco.objects.all().order_by('nombreBanco'))

    if end == 0 or end > len(todos):
        end = len(todos)
    bancos = todos[start - 1:end]

    # --- Preparar buffer y documento ---
    buffer = io.BytesIO()
    page_width, page_height = letter

    # Márgenes y áreas de header/footer (en pts)
    min_margin = 30  # margen izquierdo/derecho
    header_height = 120  # espacio reservado para encabezado (ajustable)
    footer_height = 70   # espacio reservado para pie (ajustable)

    # Construir el documento: el contenido (tabla) quedará dentro del frame entre top/bottom margins
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        leftMargin=min_margin,
        rightMargin=min_margin,
        topMargin=header_height + 10,    # contenido comienza después del encabezado reservado
        bottomMargin=footer_height + 10  # contenido termina antes del pie reservado
    )

    # Obtener configuración institucional
    config = Configuracion.objects.order_by('-fechaConfiguracion').first()
    logo_path = config.logo.path if config and getattr(config, 'logo', None) else None
    firma_path = config.firma.path if config and getattr(config, 'firma', None) else None
    nombre_institucion = config.nombreInstitucion if config and getattr(config, 'nombreInstitucion', None) else "Institución"
    rif_institucion = config.rif if config and getattr(config, 'rif', None) else ""
    direccion1 = "AV. ALBERTO RAVELL CON AV. INTERCOMUNAL JOSE ANTONIO PAEZ"
    direccion2 = "LOCAL UPTYAB, INDEPENDENCIA – EDO YARACUY"

    # Logos y tamaños (en pts)
    logo_width, logo_height, logo_margin = 80, 80, 15
    firma_width, firma_height = 100, 50

    safe_left = min_margin
    safe_right = page_width - min_margin
    safe_width = safe_right - safe_left
    safe_center = page_width / 2

    # --- Función que dibuja encabezado y pie en cada página ---
    def draw_header_footer(canvas, doc_obj):
        # Encabezado: logo derecha, texto izquierda, título centrado
        canvas.saveState()
        # Logo (si existe)
        if logo_path and os.path.exists(logo_path):
            try:
                canvas.drawImage(
                    logo_path,
                    page_width - logo_width - logo_margin,
                    page_height - logo_height - logo_margin,
                    width=logo_width,
                    height=logo_height,
                    preserveAspectRatio=True,
                    mask='auto'
                )
            except Exception:
                # si falla la carga de la imagen, no romper el PDF
                pass

        # Texto institucional (alineado a la izquierda, dentro del área segura)
        text_top = page_height - logo_margin - 10
        canvas.setFont("Helvetica-Bold", 10)
        canvas.drawString(min_margin, text_top, nombre_institucion)
        canvas.setFont("Helvetica", 9)
        canvas.drawString(min_margin, text_top - 13, f"RIF: {rif_institucion}")
        canvas.setFont("Helvetica", 8)
        canvas.drawString(min_margin, text_top - 26, direccion1)
        canvas.drawString(min_margin, text_top - 39, direccion2)

        # Título centrado (por debajo del bloque de texto)
        canvas.setFont("Helvetica-Bold", 12)
        canvas.drawCentredString(safe_center, page_height - header_height + 30, "REPORTE DE BANCOS")

        # Pie: firma centrada (si existe) y fecha a la izquierda
        if firma_path and os.path.exists(firma_path):
            try:
                canvas.drawImage(
                    firma_path,
                    safe_center - (firma_width / 2),
                    footer_height - 10,  # coordenada Y del pie, ajustable
                    width=firma_width,
                    height=firma_height,
                    preserveAspectRatio=True,
                    mask='auto'
                )
                canvas.setFont("Helvetica-Oblique", 9)
                canvas.drawCentredString(safe_center, footer_height - 18, "Firma autorizada")
            except Exception:
                pass

        # Fecha de generación a la izquierda abajo
        canvas.setFont("Helvetica", 8)
        fecha_generacion = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        canvas.drawString(min_margin, 10, f"Generado el: {fecha_generacion}")

        # Número de página centrado abajo (p. X)
        try:
            page_num = canvas.getPageNumber()
            canvas.drawCentredString(safe_center, 10, f"Página {page_num}")
        except Exception:
            pass

        canvas.restoreState()

    # --- Preparar datos de la tabla ---
    headers = ["Código Local", "Código SWIFT", "Código Contable", "Nombre", "Estado", "Fecha"]
    data = [headers]

    for b in bancos:
        cod_cont = b.codigoPlanCuenta.codigoPlanCuenta if getattr(b, 'codigoPlanCuenta', None) else ""
        estado = "Activo" if b.estadoBanco else "Inactivo"
        fecha_str = b.fechaBanco.strftime("%d/%m/%Y") if getattr(b, 'fechaBanco', None) else ""
        data.append([
            b.codLocalBanco or '',
            b.codSwiftBanco or '',
            cod_cont or '',
            b.nombreBanco or '',
            estado,
            fecha_str
        ])

    # Col widths (en pts). Ajusta si es necesario.
    col_widths = [60, 70, 90, 180, 60, 60]

    # Crear la tabla como flowable; repetir encabezado en cada página
    table = Table(data, colWidths=col_widths, repeatRows=1)

    # Estilo similar al que tenías
    table_style = TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#fe8330")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 9),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('VALIGN', (0, 0), (-1, 0), 'MIDDLE'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 6),

        ('FONTSIZE', (0, 1), (-1, -1), 8),
        ('ALIGN', (0, 1), (-1, -1), 'CENTER'),
        ('ALIGN', (3, 1), (3, -1), 'LEFT'),  # nombre a la izquierda
        ('VALIGN', (0, 1), (-1, -1), 'MIDDLE'),
        ('BACKGROUND', (0, 1), (-1, -1), colors.whitesmoke),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.lightgrey),
        ('BOX', (0, 0), (-1, -1), 0.5, colors.black),
        ('TOPPADDING', (0, 1), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 6),
    ])

    # Resaltar columna "Estado" con color por fila (verde/rojo)
    for row_idx in range(1, len(data)):
        estado_valor = (data[row_idx][4] or '').strip().lower()
        if estado_valor == "activo":
            color = colors.HexColor("#28a745")
        elif estado_valor == "inactivo":
            color = colors.HexColor("#dc3545")
        else:
            color = colors.black
        table_style.add('TEXTCOLOR', (4, row_idx), (4, row_idx), color)

    table.setStyle(table_style)

    # --- Armamos el story (contenido) ---
    story = []
    # Un pequeño espaciador opcional arriba
    story.append(Spacer(1, 6))
    story.append(table)

    # --- Build PDF ---
    doc.build(story, onFirstPage=draw_header_footer, onLaterPages=draw_header_footer)

    # Volcar buffer al HttpResponse
    pdf = buffer.getvalue()
    buffer.close()

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'inline; filename="reporte_bancos.pdf"'
    response.write(pdf)
    return response

@login_required(login_url='login')
@permission_required("cuentaBanco.view_cuentabanco", raise_exception=True)
def cuenta_banco_list(request):
    mostrar = request.GET.get('mostrar_inactivos', 'false') == 'true'
    if mostrar:
        cuentas = CuentaBanco.objects.all()
    else:
        cuentas = CuentaBanco.objects.filter(estado=True).select_related('banco', 'moneda', 'planCuenta').order_by('banco__nombreBanco', 'numeroCuentaBanco')

    return render(request, 'bancos/tablaCuentaBanco.html', {
        'cuentas': cuentas,
        'titulo': 'Listado de Cuentas Bancarias',
        'mostrar_inactivos': mostrar,
    })

@login_required(login_url='login')
@permission_required("cuentaBanco.view_cuentabanco", raise_exception=True)
def cuenta_banco_detail(request, pk):
    """
    Vista para mostrar los detalles de una cuenta bancaria.
    """
    cuenta = get_object_or_404(CuentaBanco, pk=pk)
    return render(request, 'bancos/detalleCuentaBanco.html', {
        'cuenta': cuenta
    })
@login_required(login_url='login')
@permission_required("cuentaBanco.add_cuentabanco", raise_exception=True)
def cuenta_banco_create(request):
    if request.method == 'POST':
        form = CuentaBancoForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                cuenta = form.save(commit=False)
                
                try:
                    # Convertir a entero
                    plan_cuenta_credito = int(request.POST.get('planCuentaCredito'))
                except (TypeError, ValueError):
                    return JsonResponse({
                        'success': False,
                        'message': 'ID de plan de cuenta crédito inválido'
                    }, status=400)
    
                print(f"Plan Cuenta Crédito recibido: {plan_cuenta_credito}")

                if not PlanCuenta.objects.filter(idPlanCuenta=plan_cuenta_credito).exists():
                    return JsonResponse({
                        'success': False,
                        'message': 'El plan de cuenta crédito no existe'
                    }, status=400)

                # La cuenta bancaria será hija directa del banco (no se crea plan de cuenta de producto)
                # Asignar el plan de cuenta padre directamente del banco
                # Si tu modelo requiere que planCuenta sea obligatorio, asegúrate que el formulario lo provea

                cuenta.save()
                print(f"Cuenta bancaria guardada ID: {cuenta.idCuentaBanco}")

                # Lógica para registrar el asiento contable inicial
                if cuenta.saldoDisponible != 0:
                    periodo_activo = periodoContable.objects.filter(estadoPeriodo=True).first()
                    if not periodo_activo:
                        periodo_activo = periodoContable.objects.order_by('-idPeriodo').first()
                    
                    if periodo_activo:
                        try:
                            asiento = AsientoContable.objects.create(
                                numeroAsiento=f"INI-{cuenta.idCuentaBanco}-{date.today().strftime('%Y%m%d')}",
                                fechaAsiento=date.today(),
                                conceptoAsiento=f"Apertura de cuenta bancaria {cuenta.numeroCuentaBanco}, saldo inicial",
                                idPeriodo=periodo_activo
                            )

                            DetalleAsiento.objects.create(
                                idAsiento=asiento,
                                idPlanCuenta_id=cuenta.planCuenta.idPlanCuenta,
                                debe=cuenta.saldoDisponible,
                                haber=0.00
                            )

                            DetalleAsiento.objects.create(
                                idAsiento=asiento,
                                idPlanCuenta_id=plan_cuenta_credito,
                                debe=0.00,
                                haber=cuenta.saldoDisponible
                            )
                            print("Asiento contable creado exitosamente")
                        except Exception as e:
                            print(f"Error creando asiento contable: {e}")
                            # IMPORTANTE: Esto no debe impedir la creación de la cuenta
                            # Solo registra el error pero continúa
                    else:
                        print("Advertencia: No hay período contable activo, no se creará asiento")

                # SIEMPRE devuelve éxito si la cuenta se creó
                return JsonResponse({
                    'success': True,
                    'message': 'Cuenta bancaria creada exitosamente!',
                    'redirect_url': reverse('cuenta_banco_list')
                })
        else:
            # Manejo de errores de formulario
            return JsonResponse({
                'success': False,
                'errors': form.errors
            }, status=400)
    else:
        form = CuentaBancoForm()
        bancos = Banco.objects.filter(estadoBanco=True).order_by('nombreBanco')
        monedas = Moneda.objects.filter(estadoMoneda="ACTIVO").order_by('nombreMoneda')
        cuentas_plan = PlanCuenta.objects.filter(estadoPlanCuenta=True).order_by('codigoPlanCuenta')

        return render(request, 'bancos/cuentaBanco.html', {
            'form': form,
            'bancos': bancos,
            'monedas': monedas,
            'cuentas_plan': cuentas_plan,
            'titulo': 'Nueva Cuenta Bancaria'
        })

def cuenta_banco_update(request, pk):
    cuenta = get_object_or_404(CuentaBanco, pk=pk)
    bancos = Banco.objects.filter(estadoBanco=True)

    if request.method == 'POST':
        form = CuentaBancoForm(request.POST, instance=cuenta)
        if form.is_valid():
            form.save()
            # Verificar si la solicitud es AJAX
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'message': 'Cuenta bancaria actualizada correctamente.',
                    'redirect_url': reverse('cuenta_banco_list') # Asegúrate que este nombre de URL sea correcto
                })
            else:
                # Solicitud POST no-AJAX exitosa
                messages.success(request, 'Cuenta bancaria actualizada correctamente.')
                return redirect(reverse('cuenta_banco_list')) # Redirigir a la lista
        else: # El formulario no es válido
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'errors': form.errors})
            else:
                messages.error(request, "Por favor, corrija los errores a continuación.")
                context = {
                    'form': form, # El formulario con errores y datos POST
                    'cuenta': cuenta,
                    'bancos': bancos, # Para el selector de banco si es necesario
                    'is_post_error_page': True # Flag opcional
                }
                return render(request, 'bancos/modales/editCuentaBanco.html', context)
    else: # Solicitud GET
        form = CuentaBancoForm(instance=cuenta)

    context = {
        'form': form,
        'cuenta': cuenta,
        'bancos': bancos, # Para el selector de banco
    }
    return render(request, 'bancos/modales/editCuentaBanco.html', context)


def cuenta_banco_delete(request, pk):
    """
    Vista para desactivar (eliminación lógica) una cuenta bancaria.
    """
    cuenta = get_object_or_404(CuentaBanco, pk=pk)
    
    if request.method == 'POST':
        cuenta.estado = False
        cuenta.save()
        return JsonResponse({
            'success': True,
            'message': 'Cuenta bancaria desactivada exitosamente!',
            'redirect_url': reverse('cuenta_banco_list')
        })

@login_required(login_url='login')
@permission_required("cuentaBanco.change_cuentabanco", raise_exception=True)
def cuenta_banco_reactivate(request, pk):
    cuenta = get_object_or_404(CuentaBanco, pk=pk)
    
    if request.method == 'POST':
        cuenta.estado = True
        cuenta.save()
        return JsonResponse({
            'success': True,
            'message': 'Cuenta bancaria activada exitosamente!',
            'redirect_url': reverse('cuenta_banco_list')
        })

@login_required(login_url='login')
@permission_required("cuentaBanco.view_cuentabanco", raise_exception=True)
def reporte_cuentas_banco_pdf(request):
    # Obtener datos
    cuentas = CuentaBanco.objects.select_related(
        'banco', 'moneda', 'planCuenta'
    ).all().order_by('banco__nombreBanco')
    
    # Configuración del PDF
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'inline; filename="reporte_cuentas_bancarias.pdf"'
    p = canvas.Canvas(response, pagesize=letter)
    width, height = letter
    logo_width, logo_height, logo_margin = 80, 80, 15

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
        p.drawCentredString(safe_center, text_top - 85, "REPORTE DE CUENTAS BANCARIAS")

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
    headers = ["Banco", "Número Cuenta", "Tipo", "Moneda", "Saldo", "Estado"]
    data = [headers]
    
    for cuenta in cuentas:
        estado = "Activo" if cuenta.estado else "Inactivo"
        data.append([
            cuenta.banco.nombreBanco,
            cuenta.numeroCuentaBanco,
            cuenta.get_tipoProducto_display(),
            cuenta.moneda.nombreMoneda,
            f"{cuenta.saldoDisponible:,.2f}",
            estado
        ])
    
    # Configuración de la tabla
    col_widths = [120, 100, 90, 95, 85, 60]  # Anchos ajustados
    table_width = sum(col_widths)
    
    # Espaciado vertical
    header_height = 150
    footer_height = 100
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
            ('ALIGN', (0,1), (0,-1), 'LEFT'),  # Alinear banco a izquierda
            ('ALIGN', (4,1), (4,-1), 'RIGHT'),  # Alinear saldo a derecha
            ('VALIGN', (0,1), (-1,-1), 'MIDDLE'),
            ('BACKGROUND', (0,1), (-1,-1), colors.whitesmoke),
            ('GRID', (0,0), (-1,-1), 0.5, colors.lightgrey),
            ('BOX', (0,0), (-1,-1), 0.5, colors.black),
            ('TOPPADDING', (0,1), (-1,-1), cell_padding),
            ('BOTTOMPADDING', (0,1), (-1,-1), cell_padding),
        ])
        
        # Resaltar estados
        for i in range(1, len(page_data)):
            estado_valor = page_data[i][5].strip().lower()
            if estado_valor == "activo":
                color = colors.HexColor("#28a745")  # Verde
            elif estado_valor == "inactivo":
                color = colors.HexColor("#dc3545")  # Rojo
            else:
                color = colors.black
            table_style.add('TEXTCOLOR', (5, i), (5, i), color)
        
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