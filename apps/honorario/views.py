from django.http import JsonResponse, HttpResponse, HttpResponseRedirect
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, permission_required
from django.template import loader
from django.urls import reverse
from django.contrib import messages

from .forms import HonorarioForm
from .models import Honorario
from apps.persona.models import Personas
from apps.home.models import Cargo, Cohorte, Materia, Configuracion
#Libreria para generar PDF
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.platypus import Table, TableStyle
from reportlab.lib import colors
import os

#HONORARIO
@login_required(login_url='login')
@permission_required("home.add_honorario", raise_exception=True)
def honorario_modal(request):
    # POST: procesar AJAX de registro…
    if request.method == 'POST':
        form = HonorarioForm(request.POST)
        if form.is_valid():
            form.save()
            return JsonResponse({'success': True, 'message': 'Honorario registrado.'})
        else:
            return JsonResponse({
                    'success': False,
                    'errors': {'__all__': ['Ya existe un registro idéntico.']}
                })
            
    # GET: mostrar el formulario
    form = HonorarioForm()
    # Aquí cargas TODOS los dropdowns que necesitas
    cargos     = Cargo.objects.filter(estadoCargo='ACTIVO')
    materias   = Materia.objects.filter(estadoMateria='ACTIVO')
    cohortes   = Cohorte.objects.filter(estadoCohorte='ACTIVO')
    personas   = Personas.objects.all()
    return render(request, 'honorario/honorario.html', {
        'form'      : form,
        'cargos'    : cargos,
        'materias'  : materias,
        'cohortes'  : cohortes,
        'personas'  : personas,
    })

@login_required(login_url='login')
@permission_required("honorario.change_honorario", raise_exception=True)
def edit_honorario(request, pk):
    instance = get_object_or_404(Honorario, pk=pk)
    if request.method == 'POST':
        form = HonorarioForm(request.POST, instance=instance)
        if form.is_valid():
            form.save()
            return JsonResponse({'success': True, 'message': 'Honorario actualizado.'})
        else:
            errors = {field: error for field, error in form.errors.items()}
            return JsonResponse({'success': False, 'errors': errors})
    else:
        form = HonorarioForm(instance=instance)
        # Obtener datos relacionados para los dropdowns
        personas = Personas.objects.all()
        cargos = Cargo.objects.all()
        materias = Materia.objects.all()
        cohortes = Cohorte.objects.all()
        
    return render(request, 'honorario/editHonorario.html', {
        'form': form,
        'honorario': instance,
        'personas': personas,
        'cargos': cargos,
        'materias': materias,
        'cohortes': cohortes
    })

@login_required(login_url='login')
@permission_required("honorario.change_honorario", raise_exception=True)
def delete_honorario(request, pk):
    instance = get_object_or_404(Honorario, pk=pk)
    instance.estadoHonorario = 'INACTIVO'
    instance.save()
    return JsonResponse({'success': True, 'message': 'Eliminación lógica exitosa.'})

@login_required
@permission_required('home.change_honorario', raise_exception=True)
def desactivar_honorario(request, pk):
    honorarios = get_object_or_404(Honorario, pk=pk)
    if request.method == 'POST':
        honorarios.estadoHonorario = "INACTIVO"
        honorarios.save()
        messages.success(request, f'⛔ Honorario {honorarios.idHonorario} desactivado')
        return redirect(request.POST.get('next', 'tabla_honorarios'))
    return redirect('tabla_honorarios')

@login_required(login_url='login')
@permission_required("honorario.change_honorario", raise_exception=True)
def reactivate_honorario(request, pk):
    honorarios = get_object_or_404(Honorario, pk=pk)
    if request.method == 'POST':
        honorarios.estadoHonorario = "ACTIVO"
        honorarios.save()
        messages.success(request, f'✅ Honorario {honorarios.idHonorario} activado')
        return redirect(request.POST.get('next', 'tabla_honorarios'))
    return redirect('tabla_honorarios')

@login_required(login_url='login')
@permission_required("honorario.view_honorario", raise_exception=True)
def tabla_honorarios(request):
    mostrar = request.GET.get('mostrar_inactivos', 'false') == 'true'
    if mostrar:
        honorarios = Honorario.objects.all()
    else:
        honorarios = Honorario.objects.filter(estadoHonorario='ACTIVO')
    return render(request, 'honorario/tablaHonorarios.html', {
        'honorarios': honorarios,
        'mostrar_inactivos': mostrar,
    })

@login_required(login_url='login')
def reporte_honorarios_pdf(request):
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


    # Obtener los honorarios
    honorarios = Honorario.objects.all()
    data = [["ID", "Cedula", "Nombre", "Cargo", "Materia","Horas", "Cohorte", "Estado", "Fecha"]]
    for honorario in honorarios:
        data.append([
            honorario.idHonorario,
            f"{honorario.idPersona.cedula}",
            f"{honorario.idPersona.nombres} {honorario.idPersona.apellidos}",
            honorario.idCargo.nombreCargo,
            honorario.idMateria.nombreMateria,
            honorario.horas,
            honorario.idCohorte.nombreCohorte,
            honorario.estadoHonorario,
            honorario.fechaHonorario.strftime("%d/%m/%Y") if getattr(honorario, 'fechaHonorario', None) else "",
        ])

    col_widths = [40, 60, 90, 80, 80, 40, 60, 45, 60]  #9 columnas
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
       
        if load_template in [ "honorario.html", "honorario2.html", "tablaContratos.html", "tablaHonorarios.html"]:
            personas = Personas.objects.all()
            context['personas'] = personas
            cargos = Cargo.objects.all()
            context['cargos'] = cargos
            materias = Materia.objects.all()
            context['materias'] = materias
            cohortes = Cohorte.objects.all()
            context['cohortes'] = cohortes
            honorarios = Honorario.objects.all()
            context['honorarios'] = honorarios
        context["segment"] = load_template



        context["segment"] = load_template
        html_template = loader.get_template("honorario/" + load_template)
        return HttpResponse(html_template.render(context, request))



    except loader.TemplateDoesNotExist:
        html_template = loader.get_template("home/page-404.html")
        return HttpResponse(html_template.render(context, request))

    except Exception as e:
        messages.error(request, f'Error inesperado: {e}')
        html_template = loader.get_template("home/page-500.html")
        return HttpResponse(html_template.render(context, request))




