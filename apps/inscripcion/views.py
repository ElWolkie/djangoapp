from django.http import JsonResponse, HttpResponse, HttpResponseRedirect
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test, permission_required
from django.template import loader
from django.db.models import OuterRef, Subquery, Max
from django.urls import reverse
from django.contrib import messages
from django.template.loader import render_to_string
from .forms import InscripcionForm
from .models import Inscripcion
from apps.persona.models import Personas
from apps.home.models import Cargo, Cohorte, Materia, TipoFormacion, Formacion, Configuracion
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.platypus import Table, TableStyle
from reportlab.lib import colors
import os

@login_required(login_url='login')
@permission_required("inscripcion.add_inscripcion", raise_exception=True)
def inscripcion_modal(request):
    if request.method == 'POST':
        form = InscripcionForm(request.POST)
        if form.is_valid():
            inscripcion = form.save(commit=False)
            inscripcion.is_active = True  # ⬅️ Establecer como activo
            inscripcion.save()

            # Obtener el valor de la formación seleccionada
            formacion = inscripcion.idFormacion
            valor_formacion = getattr(formacion, 'valorFormacion', 0)  # 'valor'
            print (f"Valor de la formación: {valor_formacion}")
            # Redirigir a la vista de factura con el valor de la formación
            return JsonResponse({
                'success': True,
                'message': 'Registro exitoso.',
                'redirect_url': f"{reverse('factura_create')}?valor_formacion={valor_formacion}"
            })
        else:
            errors = {field: error for field, error in form.errors.items()}
            return JsonResponse({'success': False, 'errors': errors})

    # GET: cargar datos para el modal...
    formaciones      = Formacion.objects.filter(estadoFormacion='ACTIVO')
    tipos_formacion  = TipoFormacion.objects.filter(estadoTipoFormacion='ACTIVO')
    cohortes         = Cohorte.objects.filter(estadoCohorte='ACTIVO')
    materias         = Materia.objects.filter(estadoMateria='ACTIVO')
    personas = Personas.objects.filter(
        personatp__idTP=2,  # Relación con TipoPersona idTP=2
        estadoPersona='ACTIVO'  # Estado activo
    ).distinct()
    return render(request, 'inscripcion/inscripcion.html', {
        'formaciones'     : formaciones,
        'tipos_formacion' : tipos_formacion,
        'cohortes'        : cohortes,
        'materias'        : materias,
        'personas'        : personas,
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
    
    # Obtener datos relacionados
    context = {
        'form': form,
        'inscripcion': instance,
        'personas': Personas.objects.all(),
        'cargos': Cargo.objects.all(),
        'materias': Materia.objects.all(),
        'cohortes': Cohorte.objects.all(),
        'formaciones': Formacion.objects.all(),
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
    if mostrar:
        inscripciones = Inscripcion.objects.all()
    else:
        inscripciones = Inscripcion.objects.filter(is_active=True)

    return render(request, 'inscripcion/tablaInscripciones.html', {
        'inscripciones': inscripciones,
        'mostrar_inactivos': mostrar,
    })

@login_required(login_url='login')
def reporte_inscripcion_pdf(request):
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="reporte_inscripciones.pdf"'
    p = canvas.Canvas(response, pagesize=letter)
    width, height = letter
    logo_width, logo_height, logo_margin = 100, 100, 15

    # Si tienes un modelo Configuracion para logo/firma, ajusta el import y uso
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
    p.drawCentredString(safe_center, text_top - 40, "REPORTE DE INSCRIPCIONES")

    if firma_path and os.path.exists(firma_path):
        p.drawImage(firma_path, width/2 - 60, 60, width=120, height=60, preserveAspectRatio=True, mask='auto')
        p.setFont("Helvetica-Oblique", 10)
        p.drawCentredString(width/2, 25, "Firma autorizada")

    inscripciones = Inscripcion.objects.select_related('idPersona', 'idCohorte', 'idTF', 'idFormacion').all()
    data = [["ID", "Cedula", "Cohorte", "Tipo Formación", "Formación", "Estado", "Fecha"]]
    for ins in inscripciones:
        persona = getattr(ins.idPersona, 'cedula', str(ins.idPersona)) if getattr(ins, 'idPersona', None) else ""
        cohorte = getattr(ins.idCohorte, 'nombreCohorte', '') if getattr(ins, 'idCohorte', None) else ""
        tipo_formacion = getattr(ins.idTF, 'nombreTipoFormacion', '') if getattr(ins, 'idTF', None) else ""
        formacion = getattr(ins.idFormacion, 'nombreFormacion', '') if getattr(ins, 'idFormacion', None) else ""
        estado = getattr(ins, 'estado', "ACTIVO") if hasattr(ins, 'estado') else "ACTIVO"
        fecha = ins.fechaInscripcion.strftime("%d/%m/%Y") if getattr(ins, 'fechaInscripcion', None) else ""

        data.append([
            str(ins.pk),
            persona,
            cohorte,
            tipo_formacion,
            formacion,
            estado,
            fecha
        ])

    col_widths = [40, 60, 60, 80, 100, 60, 60]  # 7 columns
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




