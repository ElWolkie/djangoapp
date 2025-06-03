from django.http import JsonResponse, HttpResponse, HttpResponseRedirect
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, permission_required
from django.template import loader
from django.urls import reverse
from django.contrib import messages
from .forms import SolicitudForm
from .models import Solicitud
from apps.persona.models import Personas
from apps.home.models import Tramite, Servicio
from apps.home.models import Configuracion
from apps.solicitud.models import Solicitud  # Usamos Solicitud en vez de Honorario
#Libreria para generar PDF
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.platypus import Table, TableStyle
from reportlab.lib import colors
import os
#SOLICITUD
@login_required(login_url='login')
@permission_required("solicitud.add_solicitud", raise_exception=True)
def solicitud_modal(request):
    if request.method == 'POST':
        form = SolicitudForm(request.POST)
        if form.is_valid():
            solicitud = form.save()  # Guardar la solicitud y obtener la instancia
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'message': 'Registro exitoso.',
                    'redirect_url': f"{reverse('factura_create')}?inscripcion={solicitud.montoTotal}"
                })
            messages.success(request, 'Registro exitoso.')
            return redirect('tabla_solicitud')
        else:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                errors = {field: error[0] for field, error in form.errors.items()}
                return JsonResponse({'success': False, 'errors': errors})
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"Error en el campo {field}: {error}")
    
    # Cargar datos para los dropdowns
    tramites = Tramite.objects.all()
    servicios = Servicio.objects.all()
    personas = Personas.objects.filter(
        personatp__idTP=2,  # Relación con TipoPersona idTP=2
        estadoPersona='ACTIVO'  # Estado activo
    ).distinct()
    return render(request, 'solicitud/solicitud.html', {
        'form': SolicitudForm(),
        'tramites': tramites,
        'servicios': servicios,
        'personas': personas,
        'segment': 'solicitud'
    })

@login_required(login_url='login')
@permission_required("solicitud.change_solicitud", raise_exception=True)
def edit_solicitud(request, pk):
    instance = get_object_or_404(Solicitud, pk=pk)
    if request.method == 'POST':
        form = SolicitudForm(request.POST, instance=instance)
        if form.is_valid():
            form.save()
            return JsonResponse({'success': True, 'message': 'Solicitud actualizada.'})
        else:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                errors = {field: error[0] for field, error in form.errors.items()}
                return JsonResponse({'success': False, 'errors': errors})
            errors = {field: error for field, error in form.errors.items()}
            return JsonResponse({'success': False, 'errors': errors})
    else:
        form = SolicitudForm(instance=instance)
        # Obtener datos necesarios para los dropdowns
        tramites = Tramite.objects.all()  # Agregado
        servicios = Servicio.objects.all()  # Agregado
        personas = Personas.objects.all()
        
    return render(request, 'solicitud/editSolicitud.html', {
        'form': form,
        'solicitud': instance,
        'tramites': tramites,  
        'servicios': servicios,  
        'personas': personas
    })

@login_required(login_url='login')
@permission_required("solicitud.change_solicitud", raise_exception=True)
def delete_solicitud(request, pk):
    instance = get_object_or_404(Solicitud, pk=pk)
    instance.estadoSolicitud = 'INACTIVO'
    instance.save()
    return JsonResponse({'success': True, 'message': 'Eliminación lógica exitosa.'})

@login_required
@permission_required('home.change_servicio', raise_exception=True)
def desactivar_solicitud(request, pk):
    solicitud = get_object_or_404(Solicitud, pk=pk)
    if request.method == 'POST':
        solicitud.estadoSolicitud = "INACTIVO"
        solicitud.save()
        messages.success(request, f'⛔ Solicitud {solicitud.idSoli} desactivada')
        return redirect(request.POST.get('next', 'tabla_solicitud'))
    return redirect('tabla_solicitud')

@login_required(login_url='login')
@permission_required("solicitud.change_solicitud", raise_exception=True)
def reactivate_solicitud(request, pk):
    solicitud = get_object_or_404(Solicitud, pk=pk)
    if request.method == 'POST':
        solicitud.estadoSolicitud = "ACTIVO"
        solicitud.save()
        messages.success(request, f'✅ Solicitud {solicitud.idSoli} activada')
        return redirect(request.POST.get('next', 'tabla_solicitud'))
    return redirect('tabla_solicitud')

@login_required(login_url='login')
@permission_required("solicitud.view_solicitud", raise_exception=True)
def tabla_solicitud(request):
    mostrar = request.GET.get('mostrar_inactivos', 'false') == 'true'
    if mostrar:
        solicitudes = Solicitud.objects.all()
    else:
        solicitudes = Solicitud.objects.filter(estadoSolicitud='ACTIVO')
    return render(request, 'solicitud/tablaSolicitud.html', {
        'solicitudes': solicitudes,
        'mostrar_inactivos': mostrar,
    })

@login_required(login_url='login')
def reporte_solicitudes_pdf(request):
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="reporte_solicitudes.pdf"'
    p = canvas.Canvas(response, pagesize=letter)
    width, height = letter
    logo_width, logo_height, logo_margin = 100, 100, 15

    try:
        config = Configuracion.objects.order_by('-fechaConfiguracion').first()
        logo_path = config.logo.path if config and config.logo else None
        firma_path = config.firma.path if config and config.firma else None
        nombre_institucion = config.nombreInstitucion if config else "Institución"
        rif_institucion = config.rif if config else ""
    except Exception:
        logo_path = None
        firma_path = None
        nombre_institucion = "Institución"
        rif_institucion = ""

    safe_left = logo_margin + logo_width
    safe_right = width - logo_margin - logo_width
    safe_width = safe_right - safe_left
    safe_center = safe_left + safe_width / 2

    if logo_path and os.path.exists(logo_path):
        p.drawImage(logo_path, width - logo_width - logo_margin, height - logo_height - logo_margin, width=logo_width, height=logo_height, preserveAspectRatio=True, mask='auto')

    text_top = height - logo_margin - 22
    p.setFont("Helvetica-Bold", 12)
    p.drawCentredString(safe_center, text_top, nombre_institucion)
    p.drawCentredString(safe_center, text_top - 20, f"RIF: {rif_institucion}")
    p.drawCentredString(safe_center, text_top - 40, "REPORTE DE SOLICITUDES")

    if firma_path and os.path.exists(firma_path):
        p.drawImage(firma_path, width/2 - 60, 60, width=120, height=60, preserveAspectRatio=True, mask='auto')
        p.setFont("Helvetica-Oblique", 10)
        p.drawCentredString(width/2, 25, "Firma autorizada")

    # Obtener las solicitudes
    solicitudes = Solicitud.objects.all()
    data = [["ID", "Persona", "Trámite", "Servicio", "Estado", "Fecha"]]
    for solicitud in solicitudes:
        data.append([
            solicitud.id,
            f"{solicitud.idPersona.nombres} {solicitud.idPersona.apellidos}" if hasattr(solicitud, 'idPersona') else "",
            solicitud.idTramite.nombreTramite if hasattr(solicitud, 'idTramite') else "",
            solicitud.idServicio.nombreServicio if hasattr(solicitud, 'idServicio') else "",
            solicitud.estadoSolicitud,
            solicitud.fechaSolicitud.strftime("%d/%m/%Y") if getattr(solicitud, 'fechaSolicitud', None) else "",
        ])

    col_widths = [40, 120, 100, 100, 60, 60]  # Ajusta según tus campos
    table_width = sum(col_widths)
    x = safe_left + (safe_width - table_width) / 2
    y = height - logo_margin - 100

    table = Table(data, colWidths=col_widths)
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
    table.drawOn(p, x, y - 25 * len(data))
    p.showPage()
    p.save()
    return response


@login_required(login_url="/login/")
def pages(request):
    context = {}
    try:
        load_template = request.path.split("/")[-1]

        if load_template == "admin":
            return HttpResponseRedirect(reverse("admin:index"))

        # Load data for specific templates
        if load_template in ["solicitud.html", "solicitud2.html", "tablaSolicitud.html"]:
            context.update({
                'solicitudes': Solicitud.objects.all(),
                'tramites': Tramite.objects.all(),
                'servicios': Servicio.objects.all(),
                'personas': Personas.objects.all(),
            })

        context["segment"] = load_template
        html_template = loader.get_template(f"solicitud/{load_template}")
        return HttpResponse(html_template.render(context, request))

    except loader.TemplateDoesNotExist:
        html_template = loader.get_template("home/page-404.html")
        return HttpResponse(html_template.render(context, request))

    except Exception as e:
        messages.error(request, f'Error inesperado: {e}')
        html_template = loader.get_template("home/page-500.html")
        return HttpResponse(html_template.render(context, request))
