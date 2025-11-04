from datetime import datetime, timedelta
from django.http import JsonResponse, HttpResponse, HttpResponseRedirect
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required, permission_required
from django.template import loader
from django.db.models import Exists, OuterRef
from django.db.models import Count
from django.db import models
from django.db.models import OuterRef, Count, Q
from django.core.exceptions import FieldError
from django.urls import reverse
from django.contrib import messages
from .forms import InscripcionForm
from .models import Inscripcion, CuotaFormacion, InscripcionCuota
from apps.persona.models import Personas
from apps.home.models import Cargo, Cohorte, Materia, TipoFormacion, Formacion, Configuracion
from apps.requisitoCliente.models import RequisitoCliente
from apps.requisitoCliente.models import Requisito
from apps.factura.models import NotaRelacionada, Factura
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.platypus import Table, TableStyle
from reportlab.lib import colors
import os
import json
from django.core.paginator import Paginator

@login_required(login_url='login')
@permission_required("inscripcion.add_inscripcion", raise_exception=True)
def inscripcion_modal(request):
    if request.method == 'POST':
        form = InscripcionForm(request.POST)
        if form.is_valid():
            inscripcion = form.save(commit=False)
            inscripcion.is_active = True  # Establecer como activo
            inscripcion.save()

            # Obtener el valor de la formación seleccionada
            formacion = inscripcion.idCohorte.idFormacion
            valor_inscripcion = getattr(formacion, 'valorInscripcion', 0)  # Obtener valor de inscripción
          
            cuotas = inscripcion.idCohorte.idFormacion.cuotas.filter(is_active=True)
            print(cuotas)  # Verifica las cuotas activas asociadas
            for cuota in cuotas:
                InscripcionCuota.objects.create(
                    idInscripcion=inscripcion,
                    idCuota=cuota,
                    estadoPago='EN ESPERA',
                    montoPagado=0
                )

            return JsonResponse({
                'success': True,
                'message': 'Inscripción registrada exitosamente.',
            'redirect_url': f"{reverse('nota_create')}?inscripcion={valor_inscripcion}&idP={inscripcion.idPersona.idPersona}&id={inscripcion.idInscripcion}"
            })
        else:
            errors = {field: error for field, error in form.errors.items()}
            return JsonResponse({'success': False, 'errors': errors})

    # Si es una solicitud GET, preparar datos para el formulario
    formaciones = Formacion.objects.filter(estadoFormacion='ACTIVO').annotate(
        cuotas_activas=Exists(
            CuotaFormacion.objects.filter(
                idFormacion=OuterRef('pk'),
                is_active=True
            )
        ),
        cantidad_cuotas=Count('cuotas', filter=models.Q(cuotas__is_active=True))  # Contar cuotas activas
    ).prefetch_related('cuotas')

    # Filter formations based on inscription period
    available_formaciones = []
    today = datetime.now().date()
    for formacion in formaciones:
        cohortes = Cohorte.objects.filter(idFormacion=formacion, estadoCohorte='ACTIVO')
        for cohorte in cohortes:
            if cohorte.fechaInicio <= today <= (cohorte.fechaInicio + timedelta(days=cohorte.lapsoInscripcion)):
                formacion.cohorte = cohorte  # Attach the cohort to the formation
                available_formaciones.append(formacion)
                break

    # Debug: imprimir las cuotas que se están enviando al template
    print(f"[DEBUG] Enviando {len(available_formaciones)} formaciones disponibles al template")
    for f in available_formaciones:
        cuotas_list = list(f.cuotas.filter(is_active=True).values('idCuota', 'nombreCuota', 'valorCuota', 'orden'))
        print(f"[DEBUG] Formacion pk={getattr(f, 'pk', None)} nombre={getattr(f, 'nombreFormacion', None)} cuotas={cuotas_list}")

    tipos_formacion = TipoFormacion.objects.filter(estadoTipoFormacion='ACTIVO')
    cohortes = Cohorte.objects.filter(estadoCohorte='ACTIVO')
    materias = Materia.objects.filter(estadoMateria='ACTIVO')
    personas = Personas.objects.filter(
        personatp__idTP=2,  # Relación con TipoPersona idTP=2
        estadoPersona='ACTIVO'  # Estado activo
    ).distinct()

    # Serializar cuotas a JSON correctamente
    for formacion in available_formaciones:
        formacion.cuotas_json = json.dumps([
            {
                'idCuota': cuota.idCuota,
                'nombreCuota': cuota.nombreCuota,
                'valorCuota': float(cuota.valorCuota),
                'orden': cuota.orden
            }
            for cuota in formacion.cuotas.filter(is_active=True)
        ])
    
    return render(request, 'inscripcion/inscripcion.html', {
        'formaciones': available_formaciones,
        'tipos_formacion': tipos_formacion,
        'cohortes': cohortes,
        'materias': materias,
        'personas': personas,
        
    })
@login_required(login_url='login')
@permission_required("inscripcion.change_inscripcion", raise_exception=True)
def edit_inscripcion(request, pk):
    instance = get_object_or_404(Inscripcion, pk=pk)
    
    if request.method == 'POST':
        form = InscripcionForm(request.POST, instance=instance)
        if form.is_valid():
            # Guardar sin modificar el estado is_active
            form.save()
            return JsonResponse({
                'success': True,
                'message': 'Inscripción actualizada correctamente',
                'redirect_url': reverse('tabla_inscripciones')
            })
        else:
            # Mejor formato para errores incluyendo todos los mensajes
            errors = {field: error[0] for field, error in form.errors.get_json_data().items()}
            return JsonResponse({
                'success': False, 
                'errors': errors
            }, status=400)
    
    # GET: Mostrar formulario de edición (solo para carga inicial)
    form = InscripcionForm(instance=instance)
    
    # Obtener TODAS las formaciones activas (similar a inscripcion_modal)
    formaciones = Formacion.objects.filter(estadoFormacion='ACTIVO').annotate(
        cuotas_activas=Exists(
            CuotaFormacion.objects.filter(
                idFormacion=OuterRef('pk'),
                is_active=True
            )
        ),
        cantidad_cuotas=Count('cuotas', filter=models.Q(cuotas__is_active=True))
    ).prefetch_related('cuotas')

    # Filtrar cohortes activas para las formaciones
    today = datetime.now().date()
    available_formaciones = []
    for formacion in formaciones:
        cohortes = Cohorte.objects.filter(idFormacion=formacion, estadoCohorte='ACTIVO')
        for cohorte in cohortes:
            # En edición, mostramos todas las cohortes activas sin restricción de fecha
            formacion.cohorte = cohorte
            available_formaciones.append(formacion)
            break

    # Serializar cuotas a JSON correctamente
    for formacion in available_formaciones:
        formacion.cuotas_json = json.dumps([
            {
                'idCuota': cuota.idCuota,
                'nombreCuota': cuota.nombreCuota,
                'valorCuota': float(cuota.valorCuota),
                'orden': cuota.orden
            }
            for cuota in formacion.cuotas.filter(is_active=True)
        ])
    
    context = {
        'form': form,
        'inscripcion': instance,
        'personas': Personas.objects.all(),
        'cargos': Cargo.objects.all(),
        'materias': Materia.objects.all(),
        'cohortes': Cohorte.objects.all(),
        'formaciones': available_formaciones,  # Formaciones disponibles
        'tipos_formacion': TipoFormacion.objects.all()
    }
    
    return render(request, 'inscripcion/editInscripcion.html', context)

@login_required(login_url='login')
@permission_required("inscripcion.change_inscripcion", raise_exception=True)
def delete_inscripcion(request, pk):
    instance = get_object_or_404(Inscripcion, pk=pk)
    instance.is_active = False
    instance.save()
    return JsonResponse({'success': True, 'message': 'Eliminación lógica exitosa.'})

@login_required
@permission_required('inscripcion.change_inscripcion', raise_exception=True)
def desactivar_inscripcion(request, pk):
    inscripcion = get_object_or_404(Inscripcion, pk=pk)
    if request.method == 'POST':
        inscripcion.is_active = False
        inscripcion.save()
        return JsonResponse({'success': True, 'message': 'Inscripción desactivada.'})
    # Si no es POST, la lógica AJAX no debería llegar aquí, pero por si acaso:
    return JsonResponse({'success': False, 'message': 'Método no permitido.'}, status=405)

@login_required
@permission_required('inscripcion.change_inscripcion', raise_exception=True)
def reactivate_inscripcion(request, pk):
    inscripcion = get_object_or_404(Inscripcion, pk=pk)
    if request.method == 'POST':
        inscripcion.is_active = True
        inscripcion.save()
        return JsonResponse({'success': True, 'message': 'Inscripción reactivada.'})
    return JsonResponse({'success': False, 'message': 'Método no permitido.'}, status=405)

@login_required(login_url='login')
@permission_required("inscripcion.view_inscripcion", raise_exception=True)
def tabla_inscripciones(request):
    mostrar = request.GET.get('mostrar_inactivos', 'false') == 'true'
    search_query = request.GET.get('search', '').strip()

    # Filtrar inscripciones según estado
    if mostrar:
        inscripciones = Inscripcion.objects.prefetch_related(
            'requisitocliente_set__idRequisito'
        ).all()
    else:
        inscripciones = Inscripcion.objects.filter(is_active=True).prefetch_related(
            'requisitocliente_set__idRequisito'
        )
    
    # Obtener todas las inscripciones con notas
    inscripciones_con_nota = NotaRelacionada.objects.filter(
        idInscripcion__in=inscripciones
    ).values_list('idInscripcion_id', flat=True)
    
    # Obtener inscripciones que tienen factura (nota con factura)
    inscripciones_con_factura = NotaRelacionada.objects.filter(
        idInscripcion__in=inscripciones,
        idNota__factura__isnull=False
    ).values_list('idInscripcion_id', flat=True)
    
    # Convertir a sets para búsqueda más eficiente
    inscripciones_con_nota_set = set(inscripciones_con_nota)
    inscripciones_con_factura_set = set(inscripciones_con_factura)

    # Preparar diccionario de requisitos entregados
    requisitos_entregados_dict = {}
    for inscripcion in inscripciones:
        requisitos = [
            rc.idRequisito.nombreRequisito 
            for rc in inscripcion.requisitocliente_set.all()
            if rc.entregado
        ]
        requisitos_entregados_dict[inscripcion.idInscripcion] = requisitos

    # Filtrar por el término de búsqueda si existe
    if search_query:
        inscripciones = inscripciones.filter(
            Q(idInscripcion__icontains=search_query) |
            Q(idPersona__cedula__icontains=search_query) |
            Q(idPersona__nombres__icontains=search_query) |
            Q(idPersona__apellidos__icontains=search_query) |
            Q(idCohorte__nombreCohorte__icontains=search_query) |
            Q(idTF__nombreTipoFormacion__icontains=search_query) |
            Q(idFormacion__nombreFormacion__icontains=search_query) |
            Q(estadoPago__icontains=search_query) |
            Q(montoPagado__icontains=search_query) |
            Q(fechaInscripcion__icontains=search_query)
        )

    # Mensajes informativos
    if mostrar:
        hay_inactivos = inscripciones.filter(is_active=False).exists()
        if not hay_inactivos:
            messages.info(request, 'No hay inscripciones inactivas para mostrar.')
    else:
        if not inscripciones.exists():
            messages.info(request, 'No hay inscripciones activas para mostrar.')

    # Paginación 
    paginator = Paginator(inscripciones, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'inscripcion/tablaInscripciones.html', {
        'requisitos_entregados_dict': requisitos_entregados_dict,
        'mostrar_inactivos': mostrar,
        'inscripciones': page_obj,
        'search_query': search_query,
        'inscripciones_con_nota': inscripciones_con_nota_set,
        'inscripciones_con_factura': inscripciones_con_factura_set,
    })

@login_required(login_url='login')
def redirigir_a_nota_inscripcion(request, pk):
    """
    Redirige a la nota específica de una inscripción (cuando tiene nota pero no factura)
    """
    
    try:
        # Buscar la nota relacionada con esta inscripción
        nota_relacionada = NotaRelacionada.objects.filter(idInscripcion_id=pk).first()
        
        if nota_relacionada and nota_relacionada.idNota:
            nota = nota_relacionada.idNota
            # Redirigir a la lista de notas (ajusta según tu estructura)
            messages.info(request, f'Inscripción tiene nota asociada: {nota.numeroNota}')
            return HttpResponseRedirect(reverse('nota_list'))
        else:
            messages.error(request, 'No se encontró nota para esta inscripción.')
            return HttpResponseRedirect(reverse('tabla_inscripciones'))
            
    except Exception as e:
        messages.error(request, f'Error al buscar la nota: {str(e)}')
        return HttpResponseRedirect(reverse('tabla_inscripciones'))

@login_required(login_url='login')
def redirigir_a_factura_inscripcion(request, pk):
    """
    Redirige a la factura específica de una inscripción (cuando tiene nota Y factura)
    """
    
    try:
        # Buscar la nota relacionada con esta inscripción
        nota_relacionada = NotaRelacionada.objects.filter(idInscripcion_id=pk).first()
        
        if nota_relacionada and nota_relacionada.idNota:
            nota = nota_relacionada.idNota
            
            # Buscar si existe factura para esta nota
            try:
                factura = Factura.objects.get(nota=nota)
                return HttpResponseRedirect(reverse('factura_generar_pdf', args=[factura.pk]))
            except Factura.DoesNotExist:
                # Si no hay factura, redirigir a la nota
                messages.info(request, 'Esta inscripción tiene nota pero no factura. Redirigiendo a la nota.')
                return HttpResponseRedirect(reverse('redirigir_nota_inscripcion', args=[pk]))
        else:
            messages.error(request, 'No se encontró nota para esta inscripción.')
            return HttpResponseRedirect(reverse('tabla_inscripciones'))
            
    except Exception as e:
        messages.error(request, f'Error al buscar la factura: {str(e)}')
        return HttpResponseRedirect(reverse('tabla_inscripciones'))
# @login_required(login_url='login')
# @permission_required("inscripcion.add_pagocuota", raise_exception=True)
# def registrar_pago_cuota(request, pk):
#     cuota = get_object_or_404(PagoCuota, pk=pk)
#     if request.method == 'POST':
#         form = PagoCuotaForm(request.POST, instance=cuota)
#         if form.is_valid():
#             pago = form.save(commit=False)
#             if pago.estado == 'PAGADO' and not pago.fecha:
#                 pago.fechaPago = timezone.now().date()
#             pago.save()
#             return JsonResponse({'success': True, 'message': 'Pago registrado correctamente.'})
#         else:
#             errors = {field: error for field, error in form.errors.items()}
#             return JsonResponse({'success': False, 'errors': errors}, status=400)
#     form = PagoCuotaForm(instance=cuota)
#     return render(request, 'inscripcion/registrarPagoCuota.html', {'form': form})


# def generar_pagos_cuotas(inscripcion):
#     """Genera los registros de PagoCuota para una inscripción."""
#     cuotas = inscripcion.idFormacion.cuotas.filter(is_active=True).order_by('orden')
#     for cuota in cuotas:
#         PagoCuota.objects.create(
#             idInscripcion=inscripcion,
#             idCuota=cuota,
#             monto=cuota.valorCuota,
#             estado='PENDIENTE'
#         )




@login_required(login_url='login')
def reporte_inscripcion_pdf(request):
    # Manejo de parámetros de paginación
    start = int(request.GET.get('start', 1))
    end = int(request.GET.get('end', 0))
    inscripciones = list(Inscripcion.objects.select_related('idPersona', 'idCohorte', 'idTF', 'idFormacion').all())
    
    if end == 0 or end > len(inscripciones):
        end = len(inscripciones)
    inscripciones = inscripciones[start-1:end]

    # Configuración inicial del PDF (usar orientación horizontal)
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'inline; filename="reporte_inscripciones.pdf"'
    p = canvas.Canvas(response, pagesize=letter)
    width, height = letter
    logo_width, logo_height, logo_margin = 80, 80, 15  # Tamaño reducido del logo

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
        p.drawCentredString(safe_center, text_top - 85, "REPORTE DE INSCRIPCIONES")

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
    headers = ["ID", "CÉDULA", "COHORTE", "TIPO FORMACIÓN", "FORMACIÓN", "ESTADO", "FECHA"]
    data = [headers]
    
    for ins in inscripciones:
        persona = f"{ins.idPersona.cedula}" if ins.idPersona else ""
        cohorte = ins.idCohorte.nombreCohorte if ins.idCohorte else ""
        tipo_formacion = ins.idTF.nombreTipoFormacion if ins.idTF else ""
        formacion = ins.idFormacion.nombreFormacion if ins.idFormacion else ""
        estado = ins.estado if hasattr(ins, 'estado') else "ACTIVO"
        fecha = ins.fechaInscripcion.strftime("%d/%m/%Y") if ins.fechaInscripcion else ""
        
        data.append([
            str(ins.pk),
            persona,
            cohorte,
            tipo_formacion,
            formacion,
            estado,
            fecha
        ])
    
    # Configuración de la tabla con espacios aumentados
    col_widths = [30, 50, 50, 100, 170, 50, 60]  # Anchos ajustados
    table_width = sum(col_widths)
    
    # Espaciado vertical aumentado
    header_height = 150
    footer_height = 100
    row_height = 22
    cell_padding = 4
    
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
            ('FONTSIZE', (0,0), (-1,0), 8),
            ('ALIGN', (0,0), (-1,0), 'CENTER'),
            ('VALIGN', (0,0), (-1,0), 'MIDDLE'),
            ('BOTTOMPADDING', (0,0), (-1,0), cell_padding),
            
            # Cuerpo de la tabla
            ('FONTSIZE', (0,1), (-1,-1), 7),
            ('ALIGN', (0,1), (-1,-1), 'CENTER'),
            ('ALIGN', (1,1), (4,-1), 'LEFT'),  # Alinear texto a izquierda
            ('VALIGN', (0,1), (-1,-1), 'MIDDLE'),
            ('BACKGROUND', (0,1), (-1,-1), colors.whitesmoke),
            ('GRID', (0,0), (-1,-1), 0.5, colors.lightgrey),
            ('BOX', (0,0), (-1,-1), 0.5, colors.black),
            ('TOPPADDING', (0,1), (-1,-1), cell_padding),
            ('BOTTOMPADDING', (0,1), (-1,-1), cell_padding),
        ])
        
        # Resaltar estados
        for i in range(1, len(page_data)):
            estado_valor = page_data[i][5].strip().lower()  # Estado en columna 5 (índice 5)
            if estado_valor == "activo":
                color = colors.HexColor("#28a745")  # Verde
            elif estado_valor == "inactivo":
                color = colors.HexColor("#dc3545")  # Rojo
            else:
                color = colors.black  # Negro para otros estados
            table_style.add('TEXTCOLOR', (5,i), (5,i), color)
        
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

@login_required
def requisitos_inscripcion_modal(request, pk):
    inscripcion = get_object_or_404(Inscripcion, pk=pk)
    requisitos = Requisito.objects.all()
    entregados = RequisitoCliente.objects.filter(idInscripcion=inscripcion, entregado=True).values_list('idRequisito_id', flat=True)
    context = {
        'inscripcion': inscripcion,
        'requisitos': requisitos,
        'requisitos_entregados': list(entregados),
    }
    return render(request, 'requisitoCliente/requisitoCliente.html', context)

@login_required
def guardar_requisitos_inscripcion(request, pk):
    inscripcion = get_object_or_404(Inscripcion, pk=pk)
    if request.method == 'POST':
        entregados = request.POST.getlist('requisitos_entregados')
        # Primero, marca todos como no entregados
        RequisitoCliente.objects.filter(idInscripcion=inscripcion).update(entregado=False)
        # Luego, marca como entregados los seleccionados
        for id_req in entregados:
            rc, created = RequisitoCliente.objects.get_or_create(
                idInscripcion=inscripcion,
                idRequisito_id=id_req,
                defaults={'entregado': True}
            )
            if not created:
                rc.entregado = True
                rc.save()
        # Redireccionar a la tabla de inscripciones usando render
        inscripciones = Inscripcion.objects.all()
        return render(request, 'inscripcion/tablaInscripciones.html', {
            'inscripciones': inscripciones,
            'success': True,
            'message': 'Requisitos actualizados correctamente.'
        })

@login_required(login_url="/login/")
def pages(request):
    context = {}
    try:
        load_template = request.path.split("/")[-1]

        if load_template == "admin":
            return HttpResponseRedirect(reverse("admin:index"))
       
        if load_template in [ "inscripcion.html", "inscripcion2.html", "tablaContratos.html", "tablaInscripcions.html"]:
            personas = Personas.objects.all()
            context['personas'] = personas
            cargos = Cargo.objects.all()
            context['cargos'] = cargos
            materias = Materia.objects.all()
            context['materias'] = materias
            cohortes = Cohorte.objects.all()
            context['cohortes'] = cohortes
            inscripciones = Inscripcion.objects.all()
            context['inscripciones'] = inscripciones
            formaciones = Formacion.objects.all()
            context['formaciones'] = formaciones  
            tipos_formacion = TipoFormacion.objects.all()
            context['tipos_formacion'] = tipos_formacion
        context["segment"] = load_template

        context["segment"] = load_template
        html_template = loader.get_template("inscripcion/" + load_template)
        return HttpResponse(html_template.render(context, request))

    except loader.TemplateDoesNotExist:
        html_template = loader.get_template("home/page-404.html")
        return HttpResponse(html_template.render(context, request))

    except Exception as e:
        messages.error(request, f'Error inesperado: {e}')
        html_template = loader.get_template("home/page-500.html")
        return HttpResponse(html_template.render(context, request))

@login_required(login_url='login')
@permission_required("inscripcion.view_inscripcion", raise_exception=True)
def ver_cuotas_inscripcion(request, pk):
    inscripcion = get_object_or_404(Inscripcion, pk=pk)
    cuotas = InscripcionCuota.objects.filter(idInscripcion=inscripcion).select_related('idCuota')

    cuotas_data = [
        {
            'id': cuota.idCuota.idCuota,
            'nombre': cuota.idCuota.nombreCuota,
            'valor': float(cuota.idCuota.valorCuota),
            'estado': cuota.estadoPago,
            'monto_pagado': float(cuota.montoPagado),
            'fecha_pago': cuota.fechaPago.strftime('%Y-%m-%d') if cuota.fechaPago else None,
            'idPersona': cuota.idInscripcion.idPersona.idPersona if cuota.idInscripcion.idPersona else None
        }
        for cuota in cuotas
    ]

    return JsonResponse({'success': True, 'cuotas': cuotas_data})



