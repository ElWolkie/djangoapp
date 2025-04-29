import requests
from django.http import JsonResponse, HttpResponse, HttpResponseRedirect
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import render, redirect, get_object_or_404
from django.template import loader
from django.db.models import OuterRef, Subquery, Max, Count, Sum, F
from django.urls import reverse
from django.contrib import messages
from django.utils import timezone # Importar timezone

from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.hashers import make_password
from django.db import IntegrityError

from django.template.loader import render_to_string
#Libreria para PDF
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter, landscape
from reportlab.lib import colors
from reportlab.platypus import Table, TableStyle
from reportlab.lib.units import inch
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
import os
#
from django.db.models.functions import ExtractMonth

from .forms import TipoFormacionForm, FormacionForm, MateriaForm, CohorteForm, CargoForm, RequisitoForm, ServicioForm, TramiteForm, DenominacionForm, BancoForm, MonedaForm, TasaForm, TipoMovimientoForm, MovimientoForm, ConfiguracionForm
from .models import Personas, Usuarios, TipoFormacion, Formacion, Materia, Cohorte, Cargo, Requisito, Servicio, Tramite, Denominacion, Banco, Moneda, Tasa, Movimiento, TipoMovimiento, Configuracion

from apps.persona.models import PersonaTP, TipoPersona
from .forms import TipoFormacionForm, FormacionForm, MateriaForm, CohorteForm, CargoForm, RequisitoForm, ServicioForm, TramiteForm, DenominacionForm, BancoForm, MonedaForm, TasaForm, TipoMovimientoForm, MovimientoForm
from .models import  TipoFormacion, Formacion, Materia, Cohorte, Cargo, Requisito, Servicio, Tramite, Denominacion, Banco, Moneda, Tasa,Movimiento, TipoMovimiento
from apps.persona.models import Personas, PersonaTP, TipoPersona
from apps.persona.forms import TipoPersonaForm, PersonaForm
from apps.honorario.models import Honorario
from apps.solicitud.models import Solicitud

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny

# Vista única para el dashboard
@login_required(login_url='login')
def home(request):
    # Solicitudes
    total_solicitudes = Solicitud.objects.filter(estadoSolicitud='ACTIVO').count()
    ultima_solicitud = Solicitud.objects.order_by('-fechaSolicitud').first()
    
    # Servicios
    total_servicios = Servicio.objects.filter(estadoServicio='ACTIVO').count()
    try:
        servicio_popular = Servicio.objects.annotate(
            total_solicitudes=Count('solicitud')
        ).order_by('-total_solicitudes').first().nombreServicio
    except AttributeError:
        servicio_popular = "N/A"
    
    # Honorarios
    honorarios_data = Honorario.objects.filter(estadoHonorario='ACTIVO').aggregate(
        total=Count('idHonorario'),
        horas=Sum('horas')
    )
    
    # Cohortes
    cohorte_reciente = Cohorte.objects.order_by('-fechaCohorte').first()
    
    # Gráfico de solicitudes por mes
    meses = [0]*12
    solicitudes_por_mes = Solicitud.objects.annotate(
        month=ExtractMonth('fechaSolicitud')
    ).values('month').annotate(total=Count('idSoli'))

    for mes in solicitudes_por_mes:
        # Restamos 1 porque los meses en la lista van de 0 (Enero) a 11 (Diciembre)
        meses[mes['month'] - 1] = mes['total']
    
    context = {
        'total_solicitudes': total_solicitudes,
        'ultima_solicitud': ultima_solicitud.fechaSolicitud if ultima_solicitud else None,
        'total_servicios': total_servicios,
        'servicio_popular': servicio_popular,
        'total_honorarios': honorarios_data['total'],
        'total_horas': honorarios_data['horas'] or 0,
        'total_cohortes': Cohorte.objects.filter(estadoCohorte='ACTIVO').count(),
        'cohorte_reciente': cohorte_reciente.nombreCohorte if cohorte_reciente else "N/A",
        'chart_data': meses,
    }

    print("Contexto enviado:", context)

    return render(request, 'home/index.html', context)

# Vista de logout
def logout_view(request):
    logout(request)
    return redirect('login')

# Vista de login
def login_view(request):
    if request.user.is_authenticated:
        return redirect('home')
    
    next_param = request.GET.get('next', 'home')  # Obtener next de la URL
    
    if request.method == 'POST':
        cedula = request.POST.get('cedula')
        password = request.POST.get('password')
        next_param = request.POST.get('next', 'home')  # Obtener next del POST
        
        try:
            persona = Personas.objects.get(cedula=cedula)
            user = authenticate(request, idPersona=persona.idPersona, password=password)
            
            if user is not None:
                login(request, user)
                return redirect(next_param)
            else:
                messages.error(request, "Contraseña incorrecta")
        except Personas.DoesNotExist:
            messages.error(request, "No existe un usuario con esta cédula")
        except Exception as e:
            messages.error(request, f"Error al iniciar sesión: {str(e)}")
    
    return render(request, 'home/login.html', {'next': next_param})

# Vista para el superuser
def es_superuser(user):
    return user.is_superuser

@login_required(login_url='login')
@user_passes_test(es_superuser)
def registrar_usuario(request):
    if request.method == 'POST':
        cedula = request.POST.get('cedula')
        password = request.POST.get('password')
        pregunta = request.POST.get('preguntaSeguridad')
        respuesta = request.POST.get('respuestaSeguridad')
        
        try:
            # Obtener la persona por cédula
            persona = Personas.objects.get(cedula=cedula)
            
            # Verificar si ya existe un usuario para esta persona
            if Usuarios.objects.filter(idPersona=persona).exists():
                messages.error(request, 'Ya existe un usuario para esta cédula')
                return render(request, 'usuario.html')
            
            # Usar el manager para crear el usuario CORRECTAMENTE
            usuario = Usuarios.objects.create_user(
                idPersona=persona.idPersona,  # Pasar el ID numérico
                password=password,
                preguntaSeguridad=pregunta,
                respuestaSeguridad=respuesta,
                coloresUsuario='default',
                is_active=True,
                is_staff=False,
                is_superuser=False
            )
            
            messages.success(request, '¡Usuario registrado exitosamente!')
            return redirect('lista_usuarios')
            
        except Personas.DoesNotExist:
            messages.error(request, 'Cédula no registrada en Personas')
        except IntegrityError as e:
            messages.error(request, 'Error: Posible usuario duplicado o datos inválidos')
            print(f"Error de integridad: {str(e)}")
        except Exception as e:
            messages.error(request, f'Error inesperado: {str(e)}')
            print(f"Error detallado: {str(e)}")
    
    return render(request, 'home/usuario.html')

@login_required(login_url='login')
def lista_usuarios(request):
    # Trae todos los usuarios con su persona asociada en una sola consulta
    usuarios = Usuarios.objects.select_related('idPersona').all()
    return render(request, 'home/tablaUsuario.html', {
        'usuarios': usuarios
    })

# PARA LA RECUPERACION DE CONTRASEÑA
def recover_password(request):
    context = {}
    cedula = request.POST.get('cedula') if request.method == 'POST' else None

    if request.method == 'POST':

        # --- Validación básica de Cédula ---
        if not cedula:
             messages.error(request, "Por favor, ingrese su cédula.")
             return render(request, 'home/login.html', {'show_recover_form': True}) # Mostrar recover form

        try:
            persona = Personas.objects.get(cedula=cedula)
            usuario = Usuarios.objects.select_related('idPersona').get(idPersona=persona)

        except Personas.DoesNotExist:
            messages.error(request, "La cédula no se encuentra registrada.")
            context['cedula'] = cedula
            context['show_recover_form'] = True # Mantener vista recover
            return render(request, 'home/login.html', context)
        except Usuarios.DoesNotExist:
            messages.error(request, "No existe un usuario vinculado a esta cédula.")
            context['cedula'] = cedula
            context['show_recover_form'] = True # Mantener vista recover
            return render(request, 'home/login.html', context)
        except Exception as e:
             messages.error(request, "Ocurrió un error buscando la información del usuario.")
             print(f"Error buscando usuario/persona: {e}")
             context['cedula'] = cedula
             context['show_recover_form'] = True # Mantener vista recover
             return render(request, 'home/login.html', context)

        # --- Lógica de Pasos ---
        respuesta_input = request.POST.get('respuestaSeguridad')
        nueva_contrasenia_input = request.POST.get('nueva_contrasenia')
        confirmar_contrasenia_input = request.POST.get('confirmar_contrasenia')

        # Paso 3: Procesar cambio de contraseña
        if nueva_contrasenia_input is not None and confirmar_contrasenia_input is not None:
            context['security_question'] = usuario.preguntaSeguridad
            context['cedula'] = cedula
            context['show_password_fields'] = True
            context['show_recover_form'] = True # <-- Mantener flip

            if nueva_contrasenia_input != confirmar_contrasenia_input:
                messages.error(request, "Las contraseñas no coinciden.")
                return render(request, 'home/login.html', context)
            elif len(nueva_contrasenia_input) < 8: # <-- Validación longitud
                messages.error(request, "La nueva contraseña debe tener al menos 8 caracteres.")
                return render(request, 'home/login.html', context)
            else:
                # (Opcional: añadir validación de complejidad aquí con validate_password)
                try:
                    usuario.set_password(nueva_contrasenia_input)
                    usuario.save()
                    messages.success(request, "Contraseña actualizada exitosamente. Por favor, inicie sesión.")
                    return redirect('login')
                except Exception as e:
                     messages.error(request, "Error al guardar la nueva contraseña.")
                     print(f"Error guardando contraseña: {e}")
                     return render(request, 'home/login.html', context)

        # Paso 2: Procesar respuesta de seguridad
        elif respuesta_input is not None:
            context['cedula'] = cedula
            context['security_question'] = usuario.preguntaSeguridad
            context['show_recover_form'] = True # <-- Mantener flip

            if usuario.respuestaSeguridad and usuario.respuestaSeguridad.lower() == respuesta_input.lower():
                context['show_password_fields'] = True
                messages.success(request, "Respuesta correcta. Ingrese su nueva contraseña.")
            else:
                context['show_password_fields'] = False
                messages.error(request, "Respuesta de seguridad incorrecta. Intente nuevamente.")
            return render(request, 'home/login.html', context)

        # Paso 1: Mostrar pregunta de seguridad
        else:
            context['security_question'] = usuario.preguntaSeguridad
            context['cedula'] = cedula
            context['show_recover_form'] = True # <-- Mantener flip
            messages.info(request, "Usuario encontrado. Por favor, ingrese la respuesta de seguridad.")
            return render(request, 'home/login.html', context)

    # Para peticiones GET
    else:
        # Si se accede a /recover-password/ directamente con GET,
        # podríamos querer mostrar el formulario de recuperación directamente.
        context['show_recover_form'] = True # <-- Mostrar lado recover por defecto en GET
        return render(request, 'home/login.html', context)


@login_required(login_url='login')
@user_passes_test(es_superuser)
def formacion_modal(request):
    if request.method == 'POST':
        form = FormacionForm(request.POST)
        if form.is_valid():
            try:
                form.save()
                return JsonResponse({'success': True, 'message': 'Registro exitoso.'})
            except ValidationError as e:
                # Capturar errores del método clean y devolverlos como JSON
                return JsonResponse({'success': False, 'errors': {'non_field_errors': e.messages}})
        else:
            print(form.errors)
            errors = {field: error for field, error in form.errors.items()}
            return JsonResponse({'success': False, 'errors': errors})
    else:
        form = FormacionForm()
        tipos_formacion = TipoFormacion.objects.all()  # Obtener los tipos de formación
    return render(request, 'home/formaciones.html', {'form': form, 'tipos_formacion': tipos_formacion})

@login_required(login_url='login')
@user_passes_test(es_superuser)
def edit_formacion(request, pk):
    formacion = get_object_or_404(Formacion, pk=pk)
    if request.method == 'POST':
        form = FormacionForm(request.POST, instance=formacion)
        if form.is_valid():
            form.save()
            return JsonResponse({'success': True, 'message': 'Formación actualizada exitosamente.'})
        else:
            errors = {field: error for field, error in form.errors.items()}
            return JsonResponse({'success': False, 'errors': errors})
    else:
        form = FormacionForm(instance=formacion)
        tipos_formacion = TipoFormacion.objects.all()
        return render(request, 'home/modales/editFormaciones.html', {
            'form': form,
            'formacion': formacion,
            'tipos_formacion': tipos_formacion
        })

@login_required(login_url='login')
@user_passes_test(es_superuser)
def delete_formacion(request, pk):
    instance = get_object_or_404(Formacion, pk=pk)
    instance.estadoFormacion = 'INACTIVO'
    instance.save()
    return JsonResponse({'success': True, 'message': 'Eliminación lógica exitosa.'})


@login_required(login_url='login')
@user_passes_test(es_superuser)
def reactivate_formacion(request, pk):
    instance = get_object_or_404(Formacion, pk=pk)
    instance.estadoFormacion = 'ACTIVO'
    instance.save()
    return JsonResponse({'success': True, 'message': 'Reactivación exitosa.'})

@login_required(login_url='login')
@user_passes_test(es_superuser)
def tabla_formaciones(request):
    if request.user.is_superuser:
        formaciones = Formacion.objects.select_related('idTF').all().distinct  # Usar select_related para optimizar la consulta
    else:
        formaciones = Formacion.objects.select_related('idTF').filter(estadoFormacion='ACTIVO').distinct  # Filtrar solo las activas
    return render(request, 'home/tablaFormaciones.html', {'formaciones': formaciones})

# Tipo de formación
@csrf_exempt
def tipo_formacion_modal(request):
    if request.method == 'POST':
        form = TipoFormacionForm(request.POST)
        if form.is_valid():
            form.save()
            return JsonResponse({'success': True, 'message': 'Registro exitoso.'})
        else:
            errors = {field: error for field, error in form.errors.items()}
            return JsonResponse({'success': False, 'errors': errors})
    else:
        form = TipoFormacionForm()
    return render(request, 'home/tipoFormacion.html', {'form': form})

@csrf_exempt
def edit_tipo_formacion(request, pk):
    instance = get_object_or_404(TipoFormacion, pk=pk)
    if request.method == 'POST':
        form = TipoFormacionForm(request.POST, instance=instance)
        if form.is_valid():
            form.save()
            return JsonResponse({'success': True, 'message': 'Edición exitosa.'})  # Respuesta JSON
        else:
            errors = {field: error for field, error in form.errors.items()}
            return JsonResponse({'success': False, 'errors': errors})  # Respuesta JSON con errores
    else:
        form = TipoFormacionForm(instance=instance)
    return render(request, 'home/modales/editTipoFormacion.html', {'form': form, 'tipoFormacion': instance})


@csrf_exempt
def delete_tipo_formacion(request, pk):
    instance = get_object_or_404(TipoFormacion, pk=pk)
    instance.estadoTipoFormacion = 'INACTIVO'
    instance.save()
    return JsonResponse({'success': True, 'message': 'Eliminación lógica exitosa.'})

@csrf_exempt
def reactivate_tipo_formacion(request, pk):
    instance = get_object_or_404(TipoFormacion, pk=pk)
    instance.estadoTipoFormacion = 'ACTIVO'
    instance.save()
    return JsonResponse({'success': True, 'message': 'Reactivación exitosa.'})

def tabla_tipo_formaciones(request):
    tipo_formaciones = TipoFormacion.objects.all()

    return render(request, 'home/tablaTipoFormaciones.html', {'tipo_formaciones': tipo_formaciones})


#Materia
@csrf_exempt
def materia_modal(request):
    if request.method == 'POST':
        form = MateriaForm(request.POST)
        if form.is_valid():
            form.save()
            return JsonResponse({'success': True, 'message': 'Registro exitoso.'})
        else:
            errors = {field: error for field, error in form.errors.items()}
            return JsonResponse({'success': False, 'errors': errors})
    else:
        form = MateriaForm()
    return render(request, 'home/materia_modal.html', {'form': form})

@csrf_exempt
def edit_materias(request, pk):
    instance = get_object_or_404(Materia, pk=pk)
    if request.method == 'POST':
        form = MateriaForm(request.POST, instance=instance)
        if form.is_valid():
            form.save()
            return JsonResponse({'success': True, 'message': 'Edición exitosa.'})
        else:
            errors = {field: error for field, error in form.errors.items()}
            return JsonResponse({'success': False, 'errors': errors})
    else:
        form = MateriaForm(instance=instance)
        formaciones = Formacion.objects.all()  # Corregir nombre de variable

    return render(request, 'home/modales/editMaterias.html', {   
        'form': form,
        'formaciones': formaciones, 
        'materia': instance  
    })

@csrf_exempt
def delete_materias(request, pk):
    instance = get_object_or_404(Materia, pk=pk)
    instance.estadoMateria = 'INACTIVO'
    instance.save()
    return JsonResponse({'success': True, 'message': 'Eliminación lógica exitosa.'})

@csrf_exempt
def reactivate_materias(request, pk):
    instance = get_object_or_404(Materia, pk=pk)
    instance.estadoMateria = 'ACTIVO'
    instance.save()
    return JsonResponse({'success': True, 'message': 'Reactivación exitosa.'})

def tabla_materias(request):
    materias = Materia.objects.all()

    return render(request, 'home/tablaMaterias.html', {'materias': materias})

#Cohorte
@csrf_exempt
def cohorte_modal(request):
    if request.method == 'POST':
        form = CohorteForm(request.POST)
        if form.is_valid():
            form.save()
            return JsonResponse({'success': True, 'message': 'Registro exitoso.'})
        else:
            errors = {field: error for field, error in form.errors.items()}
            return JsonResponse({'success': False, 'errors': errors})
    else:
        form = CohorteForm()
    return render(request, 'home/cohorte_modal.html', {'form': form})


@csrf_exempt
def edit_cohorte(request, pk):
    cohorte = get_object_or_404(Cohorte, pk=pk)
    if request.method == 'POST':
        form = CohorteForm(request.POST, instance=cohorte)
        if form.is_valid():
            form.save()
            return JsonResponse({'success': True, 'message': 'Cohorte actualizada.'})
        else:
            return JsonResponse({'success': False, 'errors': form.errors})
    else:
        form = CohorteForm(instance=cohorte)
    return render(request, 'home/modales/editCohorte.html', {'form': form, 'cohorte':cohorte})

@csrf_exempt
def delete_cohorte(request, pk):
    instance = get_object_or_404(Cohorte, pk=pk)
    instance.estadoCohorte = 'INACTIVO'
    instance.save()
    return JsonResponse({'success': True, 'message': 'Eliminación lógica exitosa.'})

@csrf_exempt
def reactivate_cohorte(request, pk):
    instance = get_object_or_404(Cohorte, pk=pk)
    instance.estadoCohorte = 'ACTIVO'
    instance.save()
    return JsonResponse({'success': True, 'message': 'Reactivación exitosa.'})

@csrf_exempt
def tabla_cohortes(request):
    cohortes = Cohorte.objects.all()
    return render(request, 'home/tablaCohortes.html', {'cohortes': cohortes})

#Cargo
@csrf_exempt
def cargo_modal(request):
    if request.method == 'POST':
        form = CargoForm(request.POST)
        if form.is_valid():
            form.save()
            return JsonResponse({'success': True, 'message': 'Registro exitoso.'})
        else:
            errors = {field: error for field, error in form.errors.items()}
            return JsonResponse({'success': False, 'errors': errors})
    else:
        form = CargoForm()
    return render(request, 'home/cargo_modal.html', {'form': form})

@csrf_exempt
def edit_cargo(request, pk):
    cargo = get_object_or_404(Cargo, pk=pk)
    if request.method == 'POST':
        form = CargoForm(request.POST, instance=cargo)
        if form.is_valid():
            form.save()
            return JsonResponse({'success': True, 'message': 'Cargo actualizado.'})
        else:
            return JsonResponse({'success': False, 'errors': form.errors})
    else:
        form = CargoForm(instance=cargo)
    return render(request, 'home/modales/editCargo.html', {'form': form, 'cargo':cargo})

@csrf_exempt
def delete_cargo(request, pk):
    instance = get_object_or_404(Cargo, pk=pk)
    instance.estadoCargo = 'INACTIVO'
    instance.save()
    return JsonResponse({'success': True, 'message': 'Eliminación lógica exitosa.'})


@csrf_exempt
def reactivate_cargo(request, pk):
    instance = get_object_or_404(Cargo, pk=pk)
    instance.estadoCargo = 'ACTIVO'
    instance.save()
    return JsonResponse({'success': True, 'message': 'Reactivación exitosa.'})

@csrf_exempt
def tabla_cargos(request):
    cargos = Cargo.objects.all()
    return render(request, 'home/tablaCargos.html', {'cargos': cargos})

@csrf_exempt
def reporte_cargos_pdf(request):
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="reporte_cargos.pdf"'

    p = canvas.Canvas(response, pagesize=letter)
    width, height = letter
    logo_width = 100
    logo_height = 170
    logo_margin = 15
    

    # Obtener configuración institucional
    config = Configuracion.objects.order_by('-fechaConfiguracion').first()
    logo_path = config.logo.path if config and config.logo else None
    firma_path = config.firma.path if config and config.firma else None
    nombre_institucion = config.nombreInstitucion if config else "Institución"
    rif_institucion = config.rif if config else ""

    # --- Encabezado: Logo y nombre ---
    if logo_path and os.path.exists(logo_path):
        # Ajusta ancho/alto según tu logo
     p.drawImage(logo_path, width - logo_width - logo_margin,  # X: margen derecho
        height - logo_height - logo_margin,  # Y: margen superior
        width=logo_width,
        height=logo_height, 
        preserveAspectRatio=True, mask='auto')
     
     safe_right = width - logo_width - logo_margin - 10  # 10px extra de separación
     safe_left = logo_margin + logo_margin
     safe_width = safe_right - safe_left
     safe_center = safe_left + safe_width / 2
       
    text_top = height - logo_margin - 60

    p.setFont("Helvetica-Bold", 12)
    p.drawCentredString( safe_center, text_top , nombre_institucion)
    p.drawCentredString( safe_center, text_top - 20, f"RIF: {rif_institucion}")
    p.drawCentredString( safe_center, text_top - 40, "AV. ALBERTO RAVELL CON AV. INTERCOMUNAL JOSE ANTONIO PAEZ,")
    p.drawCentredString( safe_center, text_top - 60, "LOCAL UPTYAB, INDEPENDENCIA – EDO YARACUY")
    p.setFont("Helvetica", 12) 
    p.drawCentredString( safe_center, text_top - 100, "Reporte de Cargos")

    # --- Pie de página: Firma ---
    if firma_path and os.path.exists(firma_path):
        # Ajusta ancho/alto según tu firma
        p.drawImage(firma_path, width/2 - 60, 60, width=120, height=100, preserveAspectRatio=True, mask='auto')
        p.setFont("Helvetica-Oblique", 10)
        p.drawCentredString(width/2, 25, "Firma autorizada")

    # --- Tabla de cargos ---
    cargos = Cargo.objects.all()
    data = [["ID", "Nombre", "Estado", "Fecha"]]
    for cargo in cargos:
        data.append([
            str(cargo.idCargo),
            cargo.nombreCargo,
            cargo.estadoCargo,
            cargo.fechaCargo.strftime("%d/%m/%Y")
        ])

    col_widths = [60, 180, 80, 80]
    table_width = sum(col_widths)
    x = (width - table_width) / 2
    y = height - 160  # Debajo del encabezado

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

#Requisito
@csrf_exempt
def requisito_modal(request):
    if request.method == 'POST':
        form = RequisitoForm(request.POST)
        if form.is_valid():
            form.save()
            return JsonResponse({'success': True, 'message': 'Registro exitoso.'})
        else:
            print(form.errors)  # esto para depurar errores
            errors = {field: error for field, error in form.errors.items()}
            return JsonResponse({'success': False, 'errors': errors})
    else:
        form = RequisitoForm()
    return render(request, 'home/requisito_modal.html', {'form': form})

@csrf_exempt
def edit_requisito(request, pk):
    requisito = get_object_or_404(Requisito, pk=pk)
    if request.method == 'POST':
        form = RequisitoForm(request.POST, instance=requisito)
        if form.is_valid():
            form.save()
            return JsonResponse({'success': True, 'message': 'requisito actualizado.'})
        else:
            return JsonResponse({'success': False, 'errors': form.errors})
    else:
        form = RequisitoForm(instance=requisito)
    return render(request, 'home/modales/editRequisito.html', {'form': form, 'requisito':requisito})

@csrf_exempt
def delete_requisito(request, pk):
    instance = get_object_or_404(Requisito, pk=pk)
    instance.estadoRequisito = 'INACTIVO'
    instance.save()
    return JsonResponse({'success': True, 'message': 'Eliminación lógica exitosa.'})


@csrf_exempt
def reactivate_requisito(request, pk):
    instance = get_object_or_404(Requisito, pk=pk)
    instance.estadoRequisito = 'ACTIVO'
    instance.save()
    return JsonResponse({'success': True, 'message': 'Reactivación exitosa.'})

@csrf_exempt
def tabla_requisitos(request):
    requisitos = Requisito.objects.all()
    return render(request, 'home/tablaRequisitos.html', {'requisitos': requisitos})


#Servicio
@csrf_exempt
def servicio_modal(request):
    if request.method == 'POST':
        form = ServicioForm(request.POST)
        if form.is_valid():
            form.save()
            return JsonResponse({'success': True, 'message': 'Registro exitoso.'})
        else:
            print(form.errors)  # esto para depurar errores
            errors = {field: error for field, error in form.errors.items()}
            return JsonResponse({'success': False, 'errors': errors})
    else:
        form = ServicioForm()
    return render(request, 'home/servicio_modal.html', {'form': form})

@csrf_exempt
def edit_servicio(request, pk):
    servicio = get_object_or_404(Servicio, pk=pk)
    if request.method == 'POST':
        form = ServicioForm(request.POST, instance=servicio)
        if form.is_valid():
            form.save()
            return JsonResponse({'success': True, 'message': 'servicio actualizado.'})
        else:
            return JsonResponse({'success': False, 'errors': form.errors})
    else:
        form = ServicioForm(instance=servicio)
    return render(request, 'home/modales/editServicio.html', {'form': form, 'servicio':servicio})


@csrf_exempt
def delete_servicio(request, pk):
    instance = get_object_or_404(Servicio, pk=pk)
    instance.estadoServicio = 'INACTIVO'
    instance.save()
    return JsonResponse({'success': True, 'message': 'Eliminación lógica exitosa.'})

@csrf_exempt
def reactivate_servicio(request, pk):
    instance = get_object_or_404(Servicio, pk=pk)
    instance.estadoServicio = 'ACTIVO'
    instance.save()
    return JsonResponse({'success': True, 'message': 'Reactivación exitosa.'})

@csrf_exempt
def tabla_servicios(request):
    servicios = Servicio.objects.all()
    return render(request, 'home/tablaServicios.html', {'servicios': servicios})

#Tramite
@csrf_exempt
def tramite_modal(request):
    if request.method == 'POST':
        form = TramiteForm(request.POST)
        if form.is_valid():
            form.save()
            return JsonResponse({'success': True, 'message': 'Registro exitoso.'})
        else:
            print(form.errors)  # esto para depurar errores
            errors = {field: error for field, error in form.errors.items()}
            return JsonResponse({'success': False, 'errors': errors})
    else:
        form = TramiteForm()
    return render(request, 'home/tramite_modal.html', {'form': form})

def edit_tramite(request, pk):
    tramite = get_object_or_404(Tramite, pk=pk)
    if request.method == 'POST':
        form = TramiteForm(request.POST, instance=tramite)
        if form.is_valid():
            form.save()
            return JsonResponse({'success': True, 'message': 'tramite actualizado.'})
        else:
            return JsonResponse({'success': False, 'errors': form.errors})
    else:
        form = TramiteForm(instance=tramite)
    return render(request, 'home/modales/editTramite.html', {'form': form, 'tramite':tramite})

@csrf_exempt
def delete_tramite(request, pk):
    instance = get_object_or_404(Tramite, pk=pk)
    instance.estadoTramite = 'INACTIVO'
    instance.save()
    return JsonResponse({'success': True, 'message': 'Eliminación lógica exitosa.'})

@csrf_exempt
def reactivate_tramite(request, pk):
    instance = get_object_or_404(Tramite, pk=pk)
    instance.estadoTramite = 'ACTIVO'
    instance.save()
    return JsonResponse({'success': True, 'message': 'Reactivación exitosa.'})

@csrf_exempt
def tabla_tramites(request):
    servicios = Servicio.objects.all()
    return render(request, 'home/tablaTramites.html', {'servicios': servicios})

#Denominacion
@csrf_exempt
def denominacion_modal(request):
    if request.method == 'POST':
        form = DenominacionForm(request.POST)
        if form.is_valid():
            form.save()
            return JsonResponse({'success': True, 'message': 'Registro exitoso.'})
        else:
            print(form.errors)  # esto para depurar errores
            errors = {field: error for field, error in form.errors.items()}
            return JsonResponse({'success': False, 'errors': errors})
    else:
        form = DenominacionForm()
    return render(request, 'home/denominacion_modal.html', {'form': form})

@csrf_exempt
def edit_denominacion(request, pk):
    instance = get_object_or_404(Denominacion, pk=pk)
    if request.method == 'POST':
        form = DenominacionForm(request.POST, instance=instance)
        if form.is_valid():
            form.save()
            return JsonResponse({'success': True, 'message': 'Edición exitosa.'})  # Respuesta JSON
        else:
            errors = {field: error for field, error in form.errors.items()}
            return JsonResponse({'success': False, 'errors': errors})  # Respuesta JSON con errores
    else:
        form = DenominacionForm(instance=instance)
    return render(request, 'home/modales/editDenominacion.html', {'form': form, 'denominacion': instance})

@csrf_exempt
def delete_denominacion(request, pk):
    instance = get_object_or_404(Denominacion, pk=pk)
    instance.estadoDenominacion = 'INACTIVO'
    instance.save()
    return JsonResponse({'success': True, 'message': 'Eliminación lógica exitosa.'})

@csrf_exempt
def reactivate_denominacion(request, pk):
    instance = get_object_or_404(Denominacion, pk=pk)
    instance.estadoDenominacion = 'ACTIVO'
    instance.save()
    return JsonResponse({'success': True, 'message': 'Reactivación exitosa.'})

def tabla_denominaciones(request):
    denominaciones = Banco.objects.all()

    return render(request, 'home/tablaDenominaciones.html', {'denominaciones': denominaciones})

#Banco
@csrf_exempt
def banco_modal(request):
    if request.method == 'POST':
        form = BancoForm(request.POST)
        if form.is_valid():
            form.save()
            return JsonResponse({'success': True, 'message': 'Registro exitoso.'})
        else:
           # print(form.errors)  # esto para depurar errores
            errors = {field: error for field, error in form.errors.items()}
            return JsonResponse({'success': False, 'errors': errors})
    else:
        form = BancoForm()
    return render(request, 'home/banco_modal.html', {'form': form})

@csrf_exempt
def edit_banco(request, pk):
    instance = get_object_or_404(Banco, pk=pk)
    if request.method == 'POST':
        form = BancoForm(request.POST, instance=instance)
        if form.is_valid():
            form.save()
            return JsonResponse({'success': True, 'message': 'Edición exitosa.'})  # Respuesta JSON
        else:
            errors = {field: error for field, error in form.errors.items()}
            return JsonResponse({'success': False, 'errors': errors})  # Respuesta JSON con errores
    else:
        form = BancoForm(instance=instance)
    return render(request, 'home/modales/editBanco.html', {'form': form, 'banco': instance})

@csrf_exempt
def delete_banco(request, pk):
    instance = get_object_or_404(Banco, pk=pk)
    instance.estadoBanco = 'INACTIVO'
    instance.save()
    return JsonResponse({'success': True, 'message': 'Eliminación lógica exitosa.'})

@csrf_exempt
def reactivate_banco(request, pk):
    instance = get_object_or_404(Banco, pk=pk)
    instance.estadoBanco = 'ACTIVO'
    instance.save()
    return JsonResponse({'success': True, 'message': 'Reactivación exitosa.'})

def tabla_bancos(request):
    bancos = Banco.objects.all()

    return render(request, 'home/tablaBancos.html', {'bancos': bancos})

#Moneda
@csrf_exempt
def moneda_modal(request):
    if request.method == 'POST':
        form = MonedaForm(request.POST)
        if form.is_valid():
            m = form.save()
            return JsonResponse({
                'success': True,
                'message': 'Moneda registrada.',
                'idMoneda': m.idMoneda,
                'nombreMoneda': m.nombreMoneda,
                'simboloMoneda': getattr(m, 'simboloMoneda', '')
            })
        return JsonResponse({'success': False, 'errors': form.errors})
    else:
        form = MonedaForm()
    return render(request, 'home/moneda.html', {'form': form})

@csrf_exempt
def edit_moneda(request, pk):
    instance = get_object_or_404(Moneda, pk=pk)
    if request.method == 'POST':
        form = MonedaForm(request.POST, instance=instance)
        if form.is_valid():
            form.save()
            return JsonResponse({'success': True, 'message': 'Edición exitosa.'})  # Respuesta JSON
        else:
            errors = {field: error for field, error in form.errors.items()}
            return JsonResponse({'success': False, 'errors': errors})  # Respuesta JSON con errores
    else:
        form = MonedaForm(instance=instance)
    return render(request, 'home/modales/editMoneda.html', {'form': form, 'moneda': instance})

@csrf_exempt
def delete_moneda(request, pk):
    instance = get_object_or_404(Moneda, pk=pk)
    instance.estadoMoneda = 'INACTIVO'
    instance.save()
    return JsonResponse({'success': True, 'message': 'Eliminación lógica exitosa.'})

@csrf_exempt
def reactivate_moneda(request, pk):
    instance = get_object_or_404(Moneda, pk=pk)
    instance.estadoMoneda = 'ACTIVO'
    instance.save()
    return JsonResponse({'success': True, 'message': 'Reactivación exitosa.'})

def tabla_monedas(request):
    monedas = Moneda.objects.all()

    return render(request, 'home/tablaMonedas.html', {'monedas': monedas})

#Tasa
@csrf_exempt
def tasa_modal(request):
    if request.method == 'POST':
        form = TasaForm(request.POST)
        if form.is_valid():
            form.save()
            return JsonResponse({'success': True, 'message': 'Registro exitoso.'})
        else:
           # print(form.errors)  # esto para depurar errores
            errors = {field: error for field, error in form.errors.items()}
            return JsonResponse({'success': False, 'errors': errors})
    else:
        form = TasaForm()
    return render(request, 'home/tasa_modal.html', {'form': form})

@csrf_exempt
def edit_tasa(request, pk):
    instance = get_object_or_404(Tasa, pk=pk)
    if request.method == 'POST':
        form = TasaForm(request.POST, instance=instance)
        if form.is_valid():
            form.save()
            return JsonResponse({'success': True, 'message': 'Edición exitosa.'})  # Respuesta JSON
        else:
            errors = {field: error for field, error in form.errors.items()}
            return JsonResponse({'success': False, 'errors': errors})  # Respuesta JSON con errores
    else:
        form = TasaForm(instance=instance)
        monedas = Moneda.objects.all()
    return render(request, 'home/modales/editTasa.html', {'form': form, 'tasa': instance,'monedas':monedas})

@csrf_exempt
def delete_tasa(request, pk):
    instance = get_object_or_404(Tasa, pk=pk)
    instance.estadoTasa = 'INACTIVO'
    instance.save()
    return JsonResponse({'success': True, 'message': 'Eliminación lógica exitosa.'})

@csrf_exempt
def reactivate_tasa(request, pk):
    instance = get_object_or_404(Tasa, pk=pk)
    instance.estadoTasa = 'ACTIVO'
    instance.save()
    return JsonResponse({'success': True, 'message': 'Reactivación exitosa.'})

def tabla_tasas(request):
    tasas = Tasa.objects.all()

    return render(request, 'home/tablaTasas.html', {'tasas': tasas})
#Tipo Movimiento
@csrf_exempt
def tipoMovimiento_modal(request):
    if request.method == 'POST':
        form = TipoMovimientoForm(request.POST)
        if form.is_valid():
            form.save()
            return JsonResponse({'success': True, 'message': 'Registro exitoso.'})
        else:
           # print(form.errors)  # esto para depurar errores
            errors = {field: error for field, error in form.errors.items()}
            return JsonResponse({'success': False, 'errors': errors})
    else:
        form = TipoMovimientoForm()
    return render(request, 'home/tipoMovimiento_modal.html', {'form': form})

@csrf_exempt
def edit_tipoMovimiento(request, pk):
    instance = get_object_or_404(TipoMovimiento, pk=pk)
    if request.method == 'POST':
        form = TipoMovimientoForm(request.POST, instance=instance)
        if form.is_valid():
            form.save()
            return JsonResponse({'success': True, 'message': 'Edición exitosa.'})  # Respuesta JSON
        else:
            errors = {field: error for field, error in form.errors.items()}
            return JsonResponse({'success': False, 'errors': errors})  # Respuesta JSON con errores
    else:
        form = TipoMovimientoForm(instance=instance)
    return render(request, 'home/modales/editTipoMovimiento.html', {'form': form, 'TipoMovimiento': instance})

@csrf_exempt
def delete_tipoMovimiento(request, pk):
    instance = get_object_or_404(TipoMovimiento, pk=pk)
    instance.estadoTipoMovimiento = 'INACTIVO'
    instance.save()
    return JsonResponse({'success': True, 'message': 'Eliminación lógica exitosa.'})

@csrf_exempt
def reactivate_tipoMovimiento(request, pk):
    instance = get_object_or_404(TipoMovimiento, pk=pk)
    instance.estadoTipoMovimiento = 'ACTIVO'
    instance.save()
    return JsonResponse({'success': True, 'message': 'Reactivación exitosa.'})

def tabla_tipoMovimientos(request):
    TipoMovimiento = TipoMovimiento.objects.all()

    return render(request, 'home/tablaTipoMovimiento.html', {'TipoMovimiento': TipoMovimiento})

#Movimientos
@csrf_exempt
def movimiento_modal(request):
    if request.method == 'POST':
        form = MovimientoForm(request.POST)
        if form.is_valid():
            form.save()
            return JsonResponse({'success': True, 'message': 'Registro exitoso.'})
        else:
            # Agrega esta línea para depurar errores
            print(form.errors)  # Esto imprimirá los errores en la consola
            errors = {field: error for field, error in form.errors.items()}
            return JsonResponse({'success': False, 'errors': errors})
    else:
        form = MovimientoForm()
      
    return render(request, 'home/movimiento_modal.html')

@csrf_exempt
def edit_movimiento(request, pk):
    movimiento = get_object_or_404(Movimiento, pk=pk)
    if request.method == 'POST':
        form = MovimientoForm(request.POST, instance=movimiento)
        if form.is_valid():
            form.save()
            return JsonResponse({'success': True})
        return JsonResponse({'errors': form.errors}, status=400)
    else:
        form = MovimientoForm(instance=movimiento)
        tipoMovimientos = TipoMovimiento.objects.all()
        denominaciones = Denominacion.objects.all()
        bancos = Banco.objects.all()
        # Agregar 'ultima_tasa' a la subconsulta
        monedas = Moneda.objects.annotate(
            ultima_idTasa=Subquery(
                Tasa.objects.filter(idMoneda=OuterRef('idMoneda'))
                .order_by('-fechaTasa')
                .values('idTasa')[:1]
            ),
            ultima_tasa=Subquery(
                Tasa.objects.filter(idMoneda=OuterRef('idMoneda'))
                .order_by('-fechaTasa')
                .values('montoTasa')[:1]
            )
        )
        return render(request, 'home/modales/editMovimiento.html', {
            'form': form,
            'movimiento': movimiento,
            'tipoMovimientos': tipoMovimientos,
            'denominaciones': denominaciones,
            'bancos': bancos,
            'monedas': monedas,
            'naturaleza': movimiento.naturaleza
        })
@csrf_exempt
def delete_movimiento(request, pk):
    movimiento = get_object_or_404(Movimiento, pk=pk)
    movimiento.estadoMovimiento = 'INACTIVO'
    movimiento.save()
    return JsonResponse({'success': True, 'message': 'Movimiento desactivado'})

@csrf_exempt
def reactivate_movimiento(request, pk):
    movimiento = get_object_or_404(Movimiento, pk=pk)
    movimiento.estadoMovimiento = 'ACTIVO'
    movimiento.save()
    return JsonResponse({'success': True, 'message': 'Movimiento reactivado'})


#Fin 


@login_required(login_url="/login/")
def index(request):
    context = {"segment": "index"}

@csrf_exempt
def configuracion(request):
    config_existente = Configuracion.objects.order_by('-fechaConfiguracion').first()
    monedas = Moneda.objects.filter(estadoMoneda='ACTIVO')

    if request.method == 'POST':
        # Si hay config_existente, pasamos 'instance' para actualizarla, sino, se crea una nueva.
        form = ConfiguracionForm(request.POST, request.FILES, instance=config_existente)
        if form.is_valid():
            try:
                configuracion_guardada = form.save()
                messages.success(request, f'Configuración institucional {"actualizada" if config_existente else "guardada"} exitosamente.')
                return redirect('configuracion') # Redirige a la misma página para ver los cambios
            except Exception as e:
                 messages.error(request, f'Ocurrió un error al guardar la configuración: {e}. Por favor, intente de nuevo.')

        else:
            messages.error(request, 'Por favor corrige los errores indicados en el formulario.')
    else:
        form = ConfiguracionForm(instance=config_existente)

    # Prepara el contexto para el template
    context = {
        'form': form,
        'monedas': monedas, # La lista de monedas activas para el select
        'configuracion_actual': config_existente # El objeto de configuración actual (o None)
        
    }
    return render(request, 'home/configuracion.html', context)

def tabla_monedas(request):
    monedas = Moneda.objects.all()
    return render(request, 'home/tablaMonedas.html', {'monedas': monedas})

# Vista para actualizar monedas desde la API
def actualizar_monedas_api(request):
    # Solo permitir método POST para esta acción que modifica datos
    if request.method != 'POST':
        messages.error(request, "Método no permitido.")
        return redirect('configuracion') # O a donde quieras redirigir

    # URL de la API (puedes ponerla en settings.py si prefieres)
    CURRENCY_API_URL = 'https://openexchangerates.org/api/currencies.json'
    nuevas_monedas_contador = 0
    monedas_fallidas = []

    try:
        # --- 1. Llamada a la API ---
        print(f"DEBUG: Llamando a la API: {CURRENCY_API_URL}") # Debug
        response = requests.get(CURRENCY_API_URL, timeout=15) # Timeout de 15 segundos
        response.raise_for_status() # Lanza un error si la respuesta no es 2xx (OK)

        # --- 2. Procesar Respuesta JSON ---
        api_currencies = response.json()
        print(f"DEBUG: Recibidas {len(api_currencies)} monedas de la API.") # Debug

        # --- 3. Obtener Símbolos Existentes en BD ---
        # Usamos values_list y flat=True para obtener una lista plana de símbolos
        # y set() para búsquedas rápidas (O(1) en promedio)
        codigos_existentes = set(Moneda.objects.values_list('simboloMoneda', flat=True))
        print(f"DEBUG: {len(codigos_existentes)} códigos de moneda existentes en BD.") # Debug

        # --- 4. Comparar y Añadir Nuevas Monedas ---
        monedas_para_crear = []
        for codigo, nombre in api_currencies.items():
            # Limitar longitud si es necesario (aunque los códigos suelen ser 3 chars)
            codigo_limpio = codigo.strip()[:5]
            nombre_limpio = nombre.strip()[:100]

            if codigo_limpio not in codigos_existentes:
                # Añadir a la lista para creación masiva (más eficiente)
                monedas_para_crear.append(
                    Moneda(
                        nombreMoneda=nombre_limpio,
                        simboloMoneda=codigo_limpio,
                        estadoMoneda='ACTIVO' # Estado por defecto al crear
                        # fechaMoneda se añade automáticamente
                    )
                )
                codigos_existentes.add(codigo_limpio) # Añadir al set para evitar duplicados en este lote

        # --- 5. Guardar Nuevas Monedas en BD (si hay) ---
        if monedas_para_crear:
            try:
                # bulk_create es más eficiente para insertar muchos objetos
                Moneda.objects.bulk_create(monedas_para_crear)
                nuevas_monedas_contador = len(monedas_para_crear)
                print(f"DEBUG: Añadidas {nuevas_monedas_contador} nuevas monedas.") # Debug
                messages.success(request, f'¡Actualización completada! Se añadieron {nuevas_monedas_contador} nuevas monedas.')
            except Exception as db_error: # Captura errores de BD (ej. violación de unique)
                print(f"ERROR DB al guardar monedas: {db_error}") # Debug
                messages.error(request, f'Error al guardar las nuevas monedas en la base de datos: {db_error}')
        else:
            print("DEBUG: No se encontraron nuevas monedas para añadir.") # Debug
            messages.info(request, '¡Todo al día! No se encontraron nuevas monedas en la API.')

    except requests.exceptions.RequestException as e:
        print(f"ERROR API: {e}") # Debug
        messages.error(request, f"Error al conectar con la API de monedas: {e}")
    except Exception as e: # Captura otros errores (ej. JSON inválido, etc.)
        print(f"ERROR General: {e}") # Debug
        messages.error(request, f"Ocurrió un error inesperado durante la actualización: {e}")

    # --- 6. Redirigir de vuelta ---
    return redirect('tabla_monedas') # Redirige a la página de moneda


def tabla_bancos(request):
    bancos = Banco.objects.all()
    return render(request, 'home/tablaBancos.html', {'bancos': bancos})

# Vista para actualizar Bancos de Venezuela desde fuente externa
def actualizar_bancos_api(request):
    # Solo permitir método POST
    if request.method != 'POST':
        messages.error(request, "Método no permitido.")
        return redirect('configuracion') # O a donde prefieras

    # Usaremos un archivo JSON conocido de un repositorio de GitHub
    # Siempre apunta al enlace "Raw" del archivo
    BANK_API_URL = 'https://raw.githubusercontent.com/andresmdev/bankListVEN/refs/heads/master/bankVEN.json'
    nuevos_bancos_contador = 0

    try:
        # --- 1. Llamada a la "API" (Archivo JSON) ---
        print(f"DEBUG: Obteniendo datos de bancos desde: {BANK_API_URL}") # Debug
        response = requests.get(BANK_API_URL, timeout=15)
        response.raise_for_status() # Verifica si la descarga fue exitosa (código 2xx)

        # --- 2. Procesar Respuesta JSON ---
        api_bancos = response.json()
        print(f"DEBUG: Recibidos {len(api_bancos)} bancos de la fuente.") # Debug

        # --- 3. Obtener Códigos Existentes en BD ---
        codigos_existentes = set(Banco.objects.values_list('codBanco', flat=True))
        print(f"DEBUG: {len(codigos_existentes)} códigos de banco existentes en BD.") # Debug

        # --- 4. Comparar y Añadir Nuevos Bancos ---
        bancos_para_crear = []
        for banco_data in api_bancos:
            # Extraer código y nombre, asegurándose que existan
            codigo = banco_data.get('code')
            nombre = banco_data.get('shortName')

            if codigo and nombre: # Solo procesar si tenemos ambos datos
                codigo_limpio = codigo.strip()[:4] # Limitar a 4 caracteres
                nombre_limpio = nombre.strip()[:150] # Limitar a la longitud del modelo

                if codigo_limpio not in codigos_existentes:
                    bancos_para_crear.append(
                        Banco(
                            nombreBanco=nombre_limpio,
                            codBanco=codigo_limpio,
                            codContable='0000', # Valor por defecto
                            estadoBanco='ACTIVO', # Valor por defecto
                            # fechaBanco usa default=timezone.now
                        )
                    )
                    # Añadir al set para evitar intentar crear duplicados en este mismo lote
                    codigos_existentes.add(codigo_limpio)
            else:
                 print(f"DEBUG: Dato de banco incompleto ignorado: {banco_data}") # Debug

        # --- 5. Guardar Nuevos Bancos en BD (si hay) ---
        if bancos_para_crear:
            try:
                Banco.objects.bulk_create(bancos_para_crear)
                nuevos_bancos_contador = len(bancos_para_crear)
                print(f"DEBUG: Añadidos {nuevos_bancos_contador} nuevos bancos.") # Debug
                messages.success(request, f'¡Actualización completada! Se añadieron {nuevos_bancos_contador} nuevos bancos.')
            except Exception as db_error:
                print(f"ERROR DB al guardar bancos: {db_error}") # Debug
                messages.error(request, f'Error al guardar los nuevos bancos en la base de datos: {db_error}')
        else:
            print("DEBUG: No se encontraron nuevos bancos para añadir.") # Debug
            messages.info(request, '¡Todo al día! No se encontraron nuevos bancos en la fuente de datos.')

    except requests.exceptions.RequestException as e:
        print(f"ERROR API/Red: {e}") # Debug
        messages.error(request, f"Error al obtener los datos de los bancos: {e}")
    except Exception as e: # Otros errores (JSON inválido, etc.)
        print(f"ERROR General: {e}") # Debug
        messages.error(request, f"Ocurrió un error inesperado durante la actualización: {e}")

    # --- 6. Redirigir de vuelta ---
    return redirect('tabla_bancos') # Redirige al banco



def pages(request):
    context = {}
    try:
        load_template = request.path.split("/")[-1]

        if load_template == "admin":
            return HttpResponseRedirect(reverse("admin:index"))
##################################################################################################
        
        tipoFormaciones = None  # Inicializar tipoFormaciones
        if load_template == "tablaTipoFormaciones.html":
            tipoFormaciones = TipoFormacion.objects.all()
            context['tipoFormaciones'] = tipoFormaciones

        context["segment"] = load_template

        if load_template == "formacion.html":
            formaciones = TipoFormacion.objects.all()
            context['formaciones'] = formaciones
        context["segment"] = load_template


        if load_template == "tablaMaterias.html":
            materias = Materia.objects.all()
            context['materias'] = materias

        context["segment"] = load_template
        
        if load_template in ["materia.html", "tablaFormaciones.html"]:
            formaciones = Formacion.objects.all()
            context['formaciones'] = formaciones
        else:
            context['formaciones'] = None  # O alguna lógica alternativa

        context["segment"] = load_template

        context["segment"] = load_template
        if load_template == "tablaCohortes.html":
            cohortes = Cohorte.objects.all()
            context['cohortes'] = cohortes

        context["segment"] = load_template

        if load_template == "tablaCargos.html":
            cargos = Cargo.objects.all()
            context['cargos'] = cargos

        context["segment"] = load_template

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



        if load_template == "tablaRequisitos.html":
            requisitos = Requisito.objects.all()
            context['requisitos'] = requisitos

        context["segment"] = load_template


        if load_template == "tablaServicios.html":
            servicios = Servicio.objects.all()
            context['servicios'] = servicios

        context["segment"] = load_template


        if load_template == "tablaTramites.html":
            tramites = Tramite.objects.all()
            context['tramites'] = tramites

        context["segment"] = load_template


        if load_template == "tablaDenominaciones.html":
            denominaciones = Denominacion.objects.all()
            context['denominaciones'] = denominaciones

        context["segment"] = load_template

        if load_template == "tablaBancos.html":
            bancos = Banco.objects.all()
            context['bancos'] = bancos

        context["segment"] = load_template

        if load_template == "tablaMonedas.html":
            monedas = Moneda.objects.all()
            context['monedas'] = monedas

        context["segment"] = load_template

        if load_template in [ "tablaTasas.html", "tasa.html"]:
            tasas = Tasa.objects.all()
            context['tasas'] = tasas
            monedas = Moneda.objects.all()
            context['monedas'] = monedas
        context["segment"] = load_template
        if load_template == "tablaTipoIngresos.html":
            tipoMovimientos = TipoMovimiento.objects.filter(naturaleza="ingreso")
            context['tipoMovimientos'] = tipoMovimientos

        context["segment"] = load_template
        if load_template == "tablaTipoEgresos.html":
            tipoMovimientos = TipoMovimiento.objects.filter(naturaleza="egreso")
            context['tipoMovimientos'] = tipoMovimientos

        context["segment"] = load_template


        if load_template in [ "tablaIngresos.html", "movimiento.html"]:   
            tipoMovimientos = TipoMovimiento.objects.all()
            context['tipoMovimientos'] = tipoMovimientos
            movimientos = Movimiento.objects.filter(naturaleza="ingreso")
            context['movimientos'] = movimientos
            denominaciones = Denominacion.objects.all()
            context['denominaciones'] = denominaciones   
            bancos = Banco.objects.all()
            context['bancos'] = bancos
           
            # Subconsulta para encontrar la última tasa por moneda
            subconsulta = Tasa.objects.filter(idMoneda=OuterRef('idMoneda')).order_by('-fechaTasa')

            # Obtener todas las monedas con su última tasa
            monedas_con_ultimas_tasas = Moneda.objects.annotate(
                ultima_idTasa=Subquery(subconsulta.values('idTasa')[:1]),  # Último monto de tasa
                ultima_tasa=Subquery(subconsulta.values('montoTasa')[:1]),  # Último monto de tasa
                ultima_fecha=Subquery(subconsulta.values('fechaTasa')[:1])  # Última fecha de tasa
            )

                # Imprimir las monedas y sus últimas tasas en la consola
            for moneda in monedas_con_ultimas_tasas:
                print(f"Moneda: {moneda.nombreMoneda}, Última Tasa: {moneda.ultima_tasa}, Fecha: {moneda.ultima_fecha},  Fecha: {moneda.ultima_idTasa}")

            # Agregar las monedas con sus últimas tasas al contexto
            context['monedas'] = monedas_con_ultimas_tasas

           
        context["segment"] = load_template



        if load_template in [ "tablaEgresos.html", "movimiento.html"]:   
            tipoMovimientos = TipoMovimiento.objects.all()
            context['tipoMovimientos'] = tipoMovimientos
            movimientos = Movimiento.objects.filter(naturaleza="egreso")
            context['movimientos'] = movimientos
            denominaciones = Denominacion.objects.all()
            context['denominaciones'] = denominaciones   
            bancos = Banco.objects.all()
            context['bancos'] = bancos
           
            # Subconsulta para encontrar la última tasa por moneda
            subconsulta = Tasa.objects.filter(idMoneda=OuterRef('idMoneda')).order_by('-fechaTasa')

            # Obtener todas las monedas con su última tasa
            monedas_con_ultimas_tasas = Moneda.objects.annotate(
                ultima_idTasa=Subquery(subconsulta.values('idTasa')[:1]),  # Último monto de tasa
                ultima_tasa=Subquery(subconsulta.values('montoTasa')[:1]),  # Último monto de tasa
                ultima_fecha=Subquery(subconsulta.values('fechaTasa')[:1])  # Última fecha de tasa
            )

                # Imprimir las monedas y sus últimas tasas en la consola
            for moneda in monedas_con_ultimas_tasas:
                print(f"Moneda: {moneda.nombreMoneda}, Última Tasa: {moneda.ultima_tasa}, Fecha: {moneda.ultima_fecha},  Fecha: {moneda.ultima_idTasa}")

            # Agregar las monedas con sus últimas tasas al contexto
            context['monedas'] = monedas_con_ultimas_tasas

           
        context["segment"] = load_template
        html_template = loader.get_template("home/" + load_template)
        return HttpResponse(html_template.render(context, request))

    except loader.TemplateDoesNotExist:
        html_template = loader.get_template("home/page-404.html")
        return HttpResponse(html_template.render(context, request))

    except Exception as e:
        messages.error(request, f'Error inesperado: {e}')
        html_template = loader.get_template("home/page-500.html")
        return HttpResponse(html_template.render(context, request))