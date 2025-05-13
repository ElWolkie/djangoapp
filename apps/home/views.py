import requests
from django import forms
from django.http import JsonResponse, HttpResponse, HttpResponseRedirect
from django.shortcuts import render, redirect, get_object_or_404
from django.template import loader
from django.db.models import OuterRef, Subquery, Max, Count, Sum, F, Q, Prefetch
from django.urls import reverse
from django.contrib import messages
from django.utils import timezone
from django.core.exceptions import PermissionDenied, ValidationError, ValidationError
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required, permission_required
from django.db import IntegrityError
from django.contrib.auth.models import Group
from collections import defaultdict # Para agrupar

from django.core.cache import cache
from django.db import models  # Para el output_field en Sum

from django.template.loader import render_to_string
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter, landscape
from reportlab.lib import colors
from reportlab.platypus import Table, TableStyle
from reportlab.lib.units import inch
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
import os
from django.db.models.functions import ExtractMonth

from .forms import AsignarGrupoForm, UsuarioForm, TipoFormacionForm, FormacionForm, MateriaForm, CohorteForm, CargoForm, RequisitoForm, ServicioForm, TramiteForm, DenominacionForm, BancoForm, MonedaForm, TasaForm, TipoMovimientoForm, MovimientoForm, ConfiguracionForm
from .models import Personas, Usuarios, TipoFormacion, Formacion, Materia, Cohorte, Cargo, Requisito, Servicio, Tramite, Denominacion, Banco, Moneda, Tasa, Movimiento, TipoMovimiento, Configuracion

from apps.persona.forms import TipoPersonaForm, PersonaForm
from apps.honorario.models import Honorario
from apps.solicitud.models import Solicitud
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny

from django.shortcuts import get_object_or_404

def contabilidad_view(request):
    return render(request, 'home/index2.html')

# Vista optimizada para el dashboard
@login_required(login_url='login')
def home(request):
    solicitudes = Solicitud.objects.filter(estadoSolicitud='ACTIVO')
    servicios = Servicio.objects.filter(estadoServicio='ACTIVO')
    cohortes = Cohorte.objects.filter(estadoCohorte='ACTIVO')

    counts = {
        'total_solicitudes': solicitudes.count(),
        'total_servicios': servicios.count(),
        'total_cohortes': cohortes.count(),
    }

    try:
        ultima_solicitud = solicitudes.select_related('idServicio').latest('fechaSolicitud')
    except Solicitud.DoesNotExist:
        ultima_solicitud = None

    try:
        cohorte_reciente = cohortes.latest('fechaCohorte')
    except Cohorte.DoesNotExist:
        cohorte_reciente = None

    servicio_popular = cache.get('servicio_popular')
    if not servicio_popular:
        try:
            servicio_popular = servicios.prefetch_related(
                Prefetch('solicitud_set', queryset=Solicitud.objects.only('idServicio'))
            ).annotate(
                total_solicitudes=Count('solicitud')
            ).order_by('-total_solicitudes').first().nombreServicio
        except AttributeError:
            servicio_popular = "N/A"
        cache.set('servicio_popular', servicio_popular, 3600)

    honorarios_data = Honorario.objects.filter(estadoHonorario='ACTIVO').aggregate(
        total=Count('idHonorario'),
        horas=Sum('horas', output_field=models.IntegerField())
    )

    chart_data = cache.get('solicitudes_por_mes')
    if not chart_data:
        meses = [0]*12
        solicitudes_por_mes = solicitudes.annotate(
            month=ExtractMonth('fechaSolicitud')
        ).values('month').annotate(total=Count('idSoli'))
        
        for mes in solicitudes_por_mes:
            meses[mes['month'] - 1] = mes['total']
        chart_data = meses
        cache.set('solicitudes_por_mes', chart_data, 86400)

    context = {
        **counts,
        'ultima_solicitud': ultima_solicitud.fechaSolicitud if ultima_solicitud else None,
        'servicio_popular': servicio_popular,
        'total_honorarios': honorarios_data['total'],
        'total_horas': honorarios_data['horas'] or 0,
        'cohorte_reciente': cohorte_reciente.nombreCohorte if cohorte_reciente else "N/A",
        'chart_data': chart_data,
    }

    return render(request, 'home/index.html', context)

# Vista de logout
def logout_view(request):
    logout(request)
    return redirect('login')

# Vista de login
# @ratelimit(key='post:cedula', rate='5/15m')  # 5 intentos por 15 minutos
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
@permission_required("home.add_usuarios", login_url='page-403', raise_exception=True)
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
@permission_required("home.change_usuarios", raise_exception=True)
def editar_usuario(request, pk):
    usuario = get_object_or_404(Usuarios, pk=pk)
    
    if request.method == 'POST':
        form = UsuarioForm(request.POST, instance=usuario)
        
        if form.is_valid():
            usuario = form.save(commit=False)
            
            # Manejar campos booleanos
            usuario.is_active = form.cleaned_data.get('is_active', False)
            usuario.is_staff = form.cleaned_data.get('is_staff', False)
            usuario.is_superuser = form.cleaned_data.get('is_superuser', False)

            # Guardar cambios
            usuario.save()  # Esto disparará la señal post_save
            
            # Manejar seguridad
            nueva_pregunta = form.cleaned_data.get('nueva_pregunta')
            nueva_respuesta = form.cleaned_data.get('nueva_respuesta')
            if nueva_pregunta and nueva_respuesta:
                usuario.preguntaSeguridad = nueva_pregunta
                usuario.respuestaSeguridad = nueva_respuesta
            
            usuario.save()
            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'message': 'Usuario actualizado exitosamente!'
                })
            return redirect('lista_usuarios')
        else:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': False,
                    'message': 'Error en el formulario',
                    'errors': form.errors.get_json_data()
                }, status=400)
            return render(request, 'home/modales/editar_usuario.html', {
                'form': form,
                'usuario': usuario,
            })
    
    else:
        form = UsuarioForm(instance=usuario)
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            html = render_to_string('home/modales/editar_usuario.html', {
                'form': form,
                'usuario': usuario,
            }, request=request)
            return HttpResponse(html)
        return render(request, 'home/modales/editar_usuario.html', {
            'form': form,
            'usuario': usuario,
        })

@login_required
@permission_required('home.change_usuarios', raise_exception=True)
def desactivar_usuario(request, pk):
    usuario = get_object_or_404(Usuarios, pk=pk)
    
    if usuario.is_superuser and not request.user.is_superuser:
        messages.error(request, "No tienes permiso para desactivar superusuarios")
        return redirect('lista_usuarios')
    
    if request.method == 'POST':
        usuario.is_active = False
        usuario.save()
        messages.success(request, f'✅ Usuario {usuario.idPersona.nombres} desactivado')
        return redirect(request.POST.get('next', 'lista_usuarios'))

@login_required(login_url='login')
@permission_required('home.delete_usuarios', raise_exception=True)
def eliminar_usuario(request, pk):
    usuario = get_object_or_404(Usuarios, pk=pk)
    
    if not request.user.is_superuser:
        messages.error(request, "❌ Solo superusuarios pueden eliminar permanentemente")
        return redirect('lista_usuarios')
    
    if request.method == 'POST':
        nombre_completo = f"{usuario.idPersona.nombres} {usuario.idPersona.apellidos}"
        usuario.delete()
        messages.success(request, f'🗑️ Usuario {nombre_completo} eliminado permanentemente')
        return redirect(request.POST.get('next', 'lista_usuarios'))


@login_required(login_url='login')
@permission_required("home.view_usuarios", login_url='page-403', raise_exception=True)
def lista_usuarios(request):
    mostrar_inactivos = request.GET.get('mostrar_inactivos', 'false') == 'true'
    
    return render(request, 'home/tablaUsuario.html', {
        'usuarios': Usuarios.objects.select_related('idPersona')
                                   .filter(is_active=True if not mostrar_inactivos else Q())
                                   .order_by('-fechaUsuario'),
        'mostrar_inactivos': mostrar_inactivos
    })

# Vista para el Error 403
def page_403(request):
    return render(request, 'home/page-403.html')

def verificar_cedula(request):
    cedula = request.GET.get('cedula', '')
    
    # Asegurar respuesta consistente
    try:
        existe_persona = Personas.objects.filter(cedula=cedula).exists()
        existe_usuario = Usuarios.objects.filter(idPersona__cedula=cedula).exists()
        
        return JsonResponse({
            'existe_en_personas': existe_persona,
            'existe_en_usuarios': existe_usuario
        })
        
    except Exception as e:
        return JsonResponse({
            'error': str(e)
        }, status=500)

@login_required(login_url='login')
@permission_required("home.change_usuarios", raise_exception=True)
def asignar_grupos(request, idUsuario):
    usuario = get_object_or_404(Usuarios, pk=idUsuario)
    todos_los_grupos = Group.objects.all().order_by('name')
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'

    if request.method == "POST":
        form = AsignarGrupoForm(
            request.POST or None,
            initial={"grupos": usuario.groups.all()},
            grupos_qs=todos_los_grupos
        )
        if form.is_valid():
            usuario.groups.set(form.cleaned_data["grupos"])
            messages.success(request, f"Permisos actualizados para {usuario.idPersona}.")
            return JsonResponse({'success': True,  'message': 'Grupos asignados correctamente.'}) if is_ajax else redirect('lista_usuarios')
        else:
            if is_ajax:
                return JsonResponse({'success': False, 'errors': form.errors}, status=400)
            messages.error(request, "Error al procesar el formulario.")
    else:
        form = AsignarGrupoForm(
            initial={"grupos": usuario.groups.all()},
            grupos_qs=todos_los_grupos
        )

    # --- Agrupación de permisos ---
    grupo_admin = None
    admin_group_name = 'Administrador'
    categorias_stems = {
        'Bancos': 'Banco',
        'Cargos': 'Cargo',
        'Clientes-Proveedores': 'Cliente-Proveedor',
        'Cohortes': 'Cohorte',
        'Configuracion': 'Configuracion',
        'Denominaciones': 'Denominacion',
        'Formaciones': 'Formacion',
        'Honorarios': 'Honorario',
        'Ingresos': 'Ingreso',
        'Inscripciones': 'Inscripcion',
        'Materias': 'Materia',
        'Monedas': 'Moneda',
        'Requisitos': 'Requisito',
        'Servicios': 'Servicio',
        'Solicitudes': 'Solicitud',
        'Tasas': 'Tasa',
        'Tramites': 'Tramite',
        'Tipo Formaciones': 'Tipo Formacion',
        'Tipo Ingresos': 'Tipo Ingreso',
        'Tipo Movimientos': 'Tipo Movimiento',
        'Tipo Personas': 'Tipo Persona',
        'Asignacion Tipo Personas': 'Asignacion Tipo Persona',
        'Usuarios': 'Usuario',
    }
    action_order_map = {
        'GestionTotal': {'order': 0, 'label': 'Control Total', 'icon': 'fas fa-star text-warning'},
        'Registrar':    {'order': 1, 'label': 'Registrar', 'icon': 'fas fa-plus-circle text-success'},
        'Visualizar':   {'order': 2, 'label': 'Consultar', 'icon': 'fas fa-eye text-info'},
        'Editar':       {'order': 3, 'label': 'Editar', 'icon': 'fas fa-edit text-primary'},
        'Eliminar':     {'order': 4, 'label': 'Eliminar', 'icon': 'fas fa-trash-alt text-danger'},
    }

    grupos_categorizados = defaultdict(lambda: {'total': None, 'acciones': []})

    for grupo in todos_los_grupos:
        if grupo.name == admin_group_name:
            grupo_admin = grupo
            continue

        categorizado = False
        for cat_nombre, cat_prefijo in categorias_stems.items():
            if grupo.name == cat_nombre:
                grupos_categorizados[cat_nombre]['total'] = {
                    'grupo': grupo, 'accion': 'GestionTotal',
                    'label': 'Control Total', 'icon': 'fas fa-star text-warning',
                    'order': 0
                }
                categorizado = True
                break

        if not categorizado:
            for cat_nombre, cat_prefijo in categorias_stems.items():
                if grupo.name.startswith(cat_prefijo):
                    action_part = grupo.name[len(cat_prefijo):].strip()
                    action_info = action_order_map.get(action_part)
                    if action_info:
                        grupos_categorizados[cat_nombre]['acciones'].append({
                            'grupo': grupo,
                            'accion': action_part,
                            'label': action_info['label'],
                            'icon': action_info['icon'],
                            'order': action_info['order']
                        })
                        categorizado = True
                        break

        if not categorizado:
            grupos_categorizados['Otros']['acciones'].append({
                'grupo': grupo,
                'accion': grupo.name,
                'label': grupo.name,
                'icon': 'fas fa-cogs text-secondary',
                'order': 99
            })

    for data in grupos_categorizados.values():
        data['acciones'].sort(key=lambda x: x['order'])

    # Acomodar 'Otros' al final
    grupos_categorizados = dict(sorted(
        grupos_categorizados.items(),
        key=lambda i: (i[0] == 'Otros', i[0])
    ))

    context = {
        "form": form,
        "usuario": usuario,
        "grupo_admin": grupo_admin,
        "grupo_admin_id": grupo_admin.pk if grupo_admin else None,
        "grupos_categorizados": grupos_categorizados,
    }
    return render(request, 'home/asignar_grupos.html', context)


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

# FORMACION
@login_required(login_url='login')
@permission_required("home.add_formacion", raise_exception=True)
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
@permission_required("home.change_formacion", raise_exception=True)
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
@permission_required("home.change_formacion", raise_exception=True)
def delete_formacion(request, pk):
    instance = get_object_or_404(Formacion, pk=pk)
    instance.estadoFormacion = 'INACTIVO'
    instance.save()
    return JsonResponse({'success': True, 'message': 'Eliminación lógica exitosa.'})

@login_required(login_url='login')
@permission_required('home.change_formacion', raise_exception=True)
def desactivar_formacion(request, pk):
    Formaciones = get_object_or_404(Formacion, pk=pk)
    if request.method == 'POST':
        Formaciones.estadoFormacion = "INACTIVO"
        Formaciones.save()
        messages.success(request, f'⛔ Formación {Formaciones.nombreFormacion} desactivada')
        return redirect(request.POST.get('next', 'tabla_formaciones'))
    return redirect('tabla_formaciones')

@login_required(login_url='login')
@permission_required('home.change_formacion', raise_exception=True)
def reactivate_formacion(request, pk):
    Formaciones = get_object_or_404(Formacion, pk=pk)
    if request.method == 'POST':
        Formaciones.estadoFormacion = "ACTIVO"
        Formaciones.save()
        messages.success(request, f'✅ Formación {Formaciones.nombreFormacion} activada')
        return redirect(request.POST.get('next', 'tabla_formaciones'))
    return redirect('tabla_formaciones')

@login_required(login_url='login')
@permission_required("home.view_formacion", raise_exception=True)
def tabla_formaciones(request):
    mostrar = request.GET.get('mostrar_inactivos', 'false') == 'true'
    if mostrar:
        formaciones = Formacion.objects.all()
    else:
        formaciones = Formacion.objects.filter(estadoFormacion='ACTIVO')
    tipo_formaciones = TipoFormacion.objects.filter(estadoTipoFormacion='ACTIVO')

    return render(request, 'home/tablaFormaciones.html', {
        'formaciones': formaciones,
        'tipoFormaciones': tipo_formaciones,
        'mostrar_inactivos': mostrar,
    })

@login_required(login_url='login')
def reporte_formaciones_pdf(request):
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="reporte_formaciones.pdf"'
    p = canvas.Canvas(response, pagesize=letter)
    width, height = letter
    logo_width, logo_height, logo_margin = 100, 100, 15

    config = Configuracion.objects.order_by('-fechaConfiguracion').first()
    logo_path = config.logo.path if config and config.logo else None
    firma_path = config.firma.path if config and config.firma else None
    nombre_institucion = config.nombreInstitucion if config else "Institución"
    rif_institucion = config.rif if config else ""

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
    p.drawCentredString(safe_center, text_top - 40, "REPORTE DE FORMACIONES")

    if firma_path and os.path.exists(firma_path):
        p.drawImage(firma_path, width/2 - 60, 60, width=120, height=60, preserveAspectRatio=True, mask='auto')
        p.setFont("Helvetica-Oblique", 10)
        p.drawCentredString(width/2, 25, "Firma autorizada")

    formaciones = Formacion.objects.select_related('idTF').all()
    data = [["ID", "Tipo", "Nombre", "Duración", "Valor", "Estado", "Fecha"]]
    for f in formaciones:
        data.append([
            str(f.idFormacion),
            f.idTF.nombreTipoFormacion if f.idTF else "",
            f.nombreFormacion,
            f.duracion,
            f.valorFormacion, 
            f.estadoFormacion,
            f.fechaFormacion.strftime("%d/%m/%Y")
        ])
    col_widths = [40, 100, 120, 60, 60, 60, 60]
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


# Tipo de formación
@login_required(login_url='login')
@permission_required("home.add_tipoformacion", raise_exception=True)
def tipoFormacion_modal(request):
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

@login_required(login_url='login')
@permission_required("home.change_tipoformacion", raise_exception=True)
def edit_tipoFormacion(request, pk):
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

@login_required(login_url='login')
@permission_required("home.change_tipoformacion", raise_exception=True)
def delete_tipoFormacion(request, pk):
    instance = get_object_or_404(TipoFormacion, pk=pk)
    instance.estadoTipoFormacion = 'INACTIVO'
    instance.save()
    return JsonResponse({'success': True, 'message': 'Eliminación lógica exitosa.'})

@login_required
@permission_required('home.change_tipoformacion', raise_exception=True)
def desactivar_tipoFormacion(request, pk):
    tipoFormaciones = get_object_or_404(TipoFormacion, pk=pk)
    if request.method == 'POST':
        tipoFormaciones.estadoTipoFormacion = "INACTIVO"
        tipoFormaciones.save()
        messages.success(request, f'⛔ Tipo Formación {tipoFormaciones.nombreTipoFormacion} desactivada')
        return redirect(request.POST.get('next', 'tabla_tipoFormacion'))
    return redirect('tabla_tipoFormacion')

@login_required(login_url='login')
@permission_required("home.change_tipoformacion", raise_exception=True)
def reactivate_tipoFormacion(request, pk):
    tipoFormaciones = get_object_or_404(TipoFormacion, pk=pk)
    if request.method == 'POST':
        tipoFormaciones.estadoTipoFormacion = "ACTIVO"
        tipoFormaciones.save()
        messages.success(request, f'✅ Tipo Formación {tipoFormaciones.nombreTipoFormacion} activada')
        return redirect(request.POST.get('next', 'tabla_tipoFormacion'))
    return redirect('tabla_tipoFormacion')

@login_required(login_url='login')
@permission_required("home.view_tipoformacion", raise_exception=True)
def tabla_tipoFormacion(request):
    mostrar = request.GET.get('mostrar_inactivos', 'false') == 'true'
    if mostrar:
        tipoFormaciones = TipoFormacion.objects.all()
    else:
        tipoFormaciones = TipoFormacion.objects.filter(estadoTipoFormacion='ACTIVO')

    return render(request, 'home/tablaTipoFormaciones.html', {
        'tipoFormaciones': tipoFormaciones,
        'mostrar_inactivos': mostrar,
    })

@login_required(login_url='login')
def reporte_tipo_formacion_pdf(request):
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="reporte_tipo_formacion.pdf"'
    p = canvas.Canvas(response, pagesize=letter)
    width, height = letter
    logo_width, logo_height, logo_margin = 100, 100, 15

    config = Configuracion.objects.order_by('-fechaConfiguracion').first()
    logo_path = config.logo.path if config and config.logo else None
    firma_path = config.firma.path if config and config.firma else None
    nombre_institucion = config.nombreInstitucion if config else "Institución"
    rif_institucion = config.rif if config else ""

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
    p.drawCentredString(safe_center, text_top - 40, "REPORTE DE TIPOS DE FORMACIÓN")

    if firma_path and os.path.exists(firma_path):
        p.drawImage(firma_path, width/2 - 60, 60, width=120, height=60, preserveAspectRatio=True, mask='auto')
        p.setFont("Helvetica-Oblique", 10)
        p.drawCentredString(width/2, 25, "Firma autorizada")

    tipos = TipoFormacion.objects.all()
    data = [["ID", "Nombre", "Estado", "Fecha"]]
    for t in tipos:
        data.append([
            str(t.idTF),
            t.nombreTipoFormacion,
            t.estadoTipoFormacion,
            t.fechaTipoFormacion.strftime("%d/%m/%Y")
        ])
    col_widths = [40, 120, 60, 60]
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


#MATERIA
login_required(login_url='login')
@permission_required("home.add_materia", raise_exception=True)
def materia_modal(request):
    formaciones = Formacion.objects.filter(estadoFormacion='ACTIVO')
    
    if request.method == 'POST':
        form = MateriaForm(request.POST)
        if form.is_valid():
            form.save()
            return JsonResponse({'success': True, 'message': 'Registro de materia exitoso.'})
        else:
            errors = {field: error for field, error in form.errors.items()}
            return JsonResponse({'success': False, 'errors': errors})
    else:
        form = MateriaForm()

    return render(request, 'home/materia.html', {
        'form': form,
        'formaciones': formaciones,
    })

@login_required(login_url='login')
@permission_required("home.change_materia", raise_exception=True)
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

@login_required(login_url='login')
@permission_required("home.change_materia", raise_exception=True)
def delete_materias(request, pk):
    instance = get_object_or_404(Materia, pk=pk)
    instance.estadoMateria = 'INACTIVO'
    instance.save()
    return JsonResponse({'success': True, 'message': 'Eliminación lógica exitosa.'})

@login_required
@permission_required('home.change_materia', raise_exception=True)
def desactivar_materias(request, pk):
    materias = get_object_or_404(Materia, pk=pk)
    if request.method == 'POST':
        materias.estadoMateria = "INACTIVO"
        materias.save()
        messages.success(request, f'⛔ Materia {materias.nombreMateria} desactivada')
        return redirect(request.POST.get('next', 'tabla_materias'))
    return redirect('tabla_materias')

@login_required
@permission_required('home.change_materia', raise_exception=True)
def reactivate_materias(request, pk):
    materias = get_object_or_404(Materia, pk=pk)
    if request.method == 'POST':
        materias.estadoMateria = "ACTIVO"
        materias.save()
        messages.success(request, f'✅ Materia {materias.nombreMateria} activada')
        return redirect(request.POST.get('next', 'tabla_materias'))
    return redirect('tabla_materias')

@login_required(login_url='login')
@permission_required("home.view_materia", raise_exception=True)
def tabla_materias(request):
    mostrar = request.GET.get('mostrar_inactivos', 'false') == 'true'
    if mostrar:
        materias = Materia.objects.all()
    else:
        materias = Materia.objects.filter(estadoMateria='ACTIVO')

    return render(request, 'home/tablaMaterias.html', {
        'materias': materias,
        'mostrar_inactivos': mostrar,
    })

@login_required(login_url='login')
def reporte_materias_pdf(request):
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="reporte_materias.pdf"'
    p = canvas.Canvas(response, pagesize=letter)
    width, height = letter
    logo_width, logo_height, logo_margin = 100, 100, 15

    config = Configuracion.objects.order_by('-fechaConfiguracion').first()
    logo_path = config.logo.path if config and config.logo else None
    firma_path = config.firma.path if config and config.firma else None
    nombre_institucion = config.nombreInstitucion if config else "Institución"
    rif_institucion = config.rif if config else ""

    # Área útil para centrar
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
    p.drawCentredString(safe_center, text_top - 40, "REPORTE DE MATERIAS")

    if firma_path and os.path.exists(firma_path):
        p.drawImage(firma_path, width/2 - 60, 60, width=120, height=60, preserveAspectRatio=True, mask='auto')
        p.setFont("Helvetica-Oblique", 10)
        p.drawCentredString(width/2, 25, "Firma autorizada")

    materias = Materia.objects.select_related('idFormacion').all()
    data = [["ID", "Formación", "Nombre", "Estado", "Fecha"]]
    for m in materias:
        data.append([
            str(m.idMateria),
            m.idFormacion.nombreFormacion if m.idFormacion else "",
            m.nombreMateria,
            m.estadoMateria,
            m.fechaMateria.strftime("%d/%m/%Y")
        ])
    col_widths = [40, 120, 120, 60, 60]
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

#COHORTE
@login_required(login_url='login')
@permission_required("home.add_cohorte", raise_exception=True)
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
    return render(request, 'home/cohorte.html', {'form': form})

@login_required
@permission_required('home.change_cohorte', raise_exception=True)
def edit_cohorte(request, pk):
    cohorte = get_object_or_404(Cohorte, pk=pk)
    if request.method == 'POST':
        form = CohorteForm(request.POST, instance=cohorte)
        if form.is_valid():
            form.save()
            return JsonResponse({'success': True, 'message': 'Cohorte actualizado.'})
        else:
            return JsonResponse({'success': False, 'errors': form.errors})
    else:
        form = CohorteForm(instance=cohorte)
    return render(request, 'home/modales/editCohorte.html', {
        'form': form,
        'cohorte': cohorte
    })

@login_required(login_url='login')
@permission_required("home.change_cohorte", raise_exception=True)
def delete_cohorte(request, pk):
    instance = get_object_or_404(Cohorte, pk=pk)
    instance.estadoCohorte = 'INACTIVO'
    instance.save()
    return JsonResponse({'success': True, 'message': 'Eliminación lógica exitosa.'})

@login_required
@permission_required('home.change_cohorte', raise_exception=True)
def desactivar_cohorte(request, pk):
    cohortes = get_object_or_404(Cohorte, pk=pk)
    if request.method == 'POST':
        cohortes.estadoCohorte = "INACTIVO"
        cohortes.save()
        messages.success(request, f'⛔ Cohorte {cohortes.nombreCohorte} desactivada')
        return redirect(request.POST.get('next', 'tabla_cohortes'))
    return redirect('tabla_cohortes')

@login_required
@permission_required('home.change_cohorte', raise_exception=True)
def reactivate_cohorte(request, pk):
    cohortes = get_object_or_404(Cohorte, pk=pk)
    if request.method == 'POST':
        cohortes.estadoCohorte = "ACTIVO"
        cohortes.save()
        messages.success(request, f'✅ Cohorte {cohortes.nombreCohorte} activada')
        return redirect(request.POST.get('next', 'tabla_cohortes'))
    return redirect('tabla_cohortes')

@login_required(login_url='login')
@permission_required("home.view_cohorte", raise_exception=True)
def tabla_cohortes(request):
    mostrar = request.GET.get('mostrar_inactivos', 'false') == 'true'
    if mostrar:
        cohortes = Cohorte.objects.all()
    else:
        cohortes = Cohorte.objects.filter(estadoCohorte='ACTIVO')

    return render(request, 'home/tablaCohortes.html', {
        'cohortes': cohortes,
        'mostrar_inactivos': mostrar,
    })

@login_required(login_url='login')
def reporte_cohortes_pdf(request):
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="reporte_cohortes.pdf"'
    p = canvas.Canvas(response, pagesize=letter)
    width, height = letter
    logo_width, logo_height, logo_margin = 100, 100, 15

    config = Configuracion.objects.order_by('-fechaConfiguracion').first()
    logo_path = config.logo.path if config and config.logo else None
    firma_path = config.firma.path if config and config.firma else None
    nombre_institucion = config.nombreInstitucion if config else "Institución"
    rif_institucion = config.rif if config else ""

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
    p.drawCentredString(safe_center, text_top - 40, "REPORTE DE COHORTES")

    if firma_path and os.path.exists(firma_path):
        p.drawImage(firma_path, width/2 - 60, 60, width=120, height=60, preserveAspectRatio=True, mask='auto')
        p.setFont("Helvetica-Oblique", 10)
        p.drawCentredString(width/2, 25, "Firma autorizada")

    cohortes = Cohorte.objects.all()
    data = [["ID", "Nombre", "Estado", "Fecha"]]
    for c in cohortes:
        data.append([
            str(c.idCohorte),
            c.nombreCohorte,
            c.estadoCohorte,
            c.fechaCohorte.strftime("%d/%m/%Y")
        ])
    col_widths = [40, 120, 60, 60]
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


#CARGO
@login_required(login_url='login')
@permission_required("home.add_cargo", raise_exception=True)
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
    return render(request, 'home/cargo.html', {'form': form})

@login_required(login_url='login')
@permission_required("home.change_cargo", raise_exception=True)
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

@login_required(login_url='login')
@permission_required("home.change_cargo", raise_exception=True)
def delete_cargo(request, pk):
    instance = get_object_or_404(Cargo, pk=pk)
    instance.estadoCargo = 'INACTIVO'
    instance.save()
    return JsonResponse({'success': True, 'message': 'Eliminación lógica exitosa.'})

@login_required
@permission_required('home.change_cargo', raise_exception=True)
def desactivar_cargo(request, pk):
    cargos = get_object_or_404(Cargo, pk=pk)
    if request.method == 'POST':
        cargos.estadoCargo = "INACTIVO"
        cargos.save()
        messages.success(request, f'⛔ Cargo {cargos.nombreCargo} desactivado')
        return redirect(request.POST.get('next', 'tabla_cargos'))
    return redirect('tabla_cargos')

@login_required(login_url='login')
@permission_required("home.change_cargo", raise_exception=True)
def reactivate_cargo(request, pk):
    cargos = get_object_or_404(Cargo, pk=pk)
    if request.method == 'POST':
        cargos.estadoCargo = "ACTIVO"
        cargos.save()
        messages.success(request, f'✅ Cargo {cargos.nombreCargo} activado')
        return redirect(request.POST.get('next', 'tabla_cargos'))
    return redirect('tabla_cargos')

@login_required(login_url='login')
@permission_required("home.view_cargo", raise_exception=True)
def tabla_cargos(request):
    mostrar = request.GET.get('mostrar_inactivos', 'false') == 'true'
    if mostrar:
        cargos = Cargo.objects.all()
    else:
        cargos = Cargo.objects.filter(estadoCargo='ACTIVO')
    return render(request, 'home/tablaCargos.html', {
        'cargos': cargos,
        'mostrar_inactivos': mostrar,
    })
    cargos = Cargo.objects.all()
    return render(request, 'home/tablaCargos.html', {'cargos': cargos})

@login_required(login_url='login')
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
    p.drawCentredString( safe_center, text_top - 80, "Reporte de Cargos")

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


#REQUISITO
@login_required(login_url='login')
@permission_required("home.add_requisito", raise_exception=True)
#Requisito
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
    return render(request, 'home/requisito.html', {'form': form})

@login_required(login_url='login')
@permission_required("home.change_requisito", raise_exception=True)
def edit_requisito(request, pk):
    requisito = get_object_or_404(Requisito, pk=pk)
    if request.method == 'POST':
        form = RequisitoForm(request.POST, instance=requisito)
        if form.is_valid():
            form.save()
            return JsonResponse({'success': True, 'message': 'Requisito actualizado.'})
        else:
            return JsonResponse({'success': False, 'errors': form.errors})
    else:
        form = RequisitoForm(instance=requisito)
    return render(request, 'home/modales/editRequisito.html', {'form': form, 'requisito':requisito})

@login_required(login_url='login')
@permission_required("home.change_requisito", raise_exception=True)
def delete_requisito(request, pk):
    instance = get_object_or_404(Requisito, pk=pk)
    instance.estadoRequisito = 'INACTIVO'
    instance.save()
    return JsonResponse({'success': True, 'message': 'Eliminación lógica exitosa.'})

@login_required
@permission_required('home.change_requisito', raise_exception=True)
def desactivar_requisito(request, pk):
    requisitos = get_object_or_404(Requisito, pk=pk)
    if request.method == 'POST':
        requisitos.estadoRequisito = "INACTIVO"
        requisitos.save()
        messages.success(request, f'⛔ Requisito {requisitos.nombreRequisito} desactivado')
        return redirect(request.POST.get('next', 'tabla_requisitos'))
    return redirect('tabla_requisitos')

@login_required(login_url='login')
@permission_required("home.change_requisito", raise_exception=True)
def reactivate_requisito(request, pk):
    requisitos = get_object_or_404(Requisito, pk=pk)
    if request.method == 'POST':
        requisitos.estadoRequisito = "ACTIVO"
        requisitos.save()
        messages.success(request, f'✅ Requisito {requisitos.nombreRequisito} activado')
        return redirect(request.POST.get('next', 'tabla_requisitos'))
    return redirect('tabla_requisitos')

@login_required(login_url='login')
@permission_required("home.view_requisito", raise_exception=True)
def tabla_requisitos(request):
    mostrar = request.GET.get('mostrar_inactivos', 'false') == 'true'
    if mostrar:
        requisitos = Requisito.objects.all()
    else:
        requisitos = Requisito.objects.filter(estadoRequisito='ACTIVO')
    return render(request, 'home/tablaRequisitos.html', {
        'requisitos': requisitos,
        'mostrar_inactivos': mostrar,
    })

@login_required(login_url='login')
def reporte_requisitos_pdf(request):
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="reporte_requisitos.pdf"'
    p = canvas.Canvas(response, pagesize=letter)
    width, height = letter
    logo_width, logo_height, logo_margin = 100, 100, 15

    config = Configuracion.objects.order_by('-fechaConfiguracion').first()
    logo_path = config.logo.path if config and config.logo else None
    firma_path = config.firma.path if config and config.firma else None
    nombre_institucion = config.nombreInstitucion if config else "Institución"
    rif_institucion = config.rif if config else ""

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
    p.drawCentredString(safe_center, text_top - 40, "REPORTE DE REQUISITOS")

    if firma_path and os.path.exists(firma_path):
        p.drawImage(firma_path, width/2 - 60, 60, width=120, height=60, preserveAspectRatio=True, mask='auto')
        p.setFont("Helvetica-Oblique", 10)
        p.drawCentredString(width/2, 25, "Firma autorizada")

    requisitos = Requisito.objects.all()
    data = [["ID", "Nombre", "Estado", "Fecha"]]
    for r in requisitos:
        data.append([
            str(r.idRequisito),
            r.nombreRequisito,
            r.estadoRequisito,
            r.fechaRequisito.strftime("%d/%m/%Y")
        ])

    col_widths = [40, 120, 60, 60]
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


#SERVICIO
@login_required(login_url='login')
@permission_required("home.add_servicio", raise_exception=True)
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
    return render(request, 'home/servicio.html', {'form': form})

@login_required(login_url='login')
@permission_required("home.change_servicio", raise_exception=True)
def edit_servicio(request, pk):
    servicio = get_object_or_404(Servicio, pk=pk)
    if request.method == 'POST':
        form = ServicioForm(request.POST, instance=servicio)
        if form.is_valid():
            form.save()
            return JsonResponse({'success': True, 'message': 'Servicio actualizado.'})
        else:
            return JsonResponse({'success': False, 'errors': form.errors})
    else:
        form = ServicioForm(instance=servicio)
    return render(request, 'home/modales/editServicio.html', {'form': form, 'servicio':servicio})

@login_required(login_url='login')
@permission_required("home.change_servicio", raise_exception=True)
def delete_servicio(request, pk):
    instance = get_object_or_404(Servicio, pk=pk)
    instance.estadoServicio = 'INACTIVO'
    instance.save()
    return JsonResponse({'success': True, 'message': 'Eliminación lógica exitosa.'})

@login_required
@permission_required('home.change_servicio', raise_exception=True)
def desactivar_servicio(request, pk):
    servicios = get_object_or_404(Servicio, pk=pk)
    if request.method == 'POST':
        servicios.estadoServicio = "INACTIVO"
        servicios.save()
        messages.success(request, f'⛔ Servicio {servicios.nombreServicio} desactivado')
        return redirect(request.POST.get('next', 'tabla_servicios'))
    return redirect('tabla_servicios')

@login_required(login_url='login')
@permission_required("home.change_servicio", raise_exception=True)
def reactivate_servicio(request, pk):
    servicios = get_object_or_404(Servicio, pk=pk)
    if request.method == 'POST':
        servicios.estadoServicio = "ACTIVO"
        servicios.save()
        messages.success(request, f'✅ Servicio {servicios.nombreServicio} activado')
        return redirect(request.POST.get('next', 'tabla_servicios'))
    return redirect('tabla_servicios')

@login_required(login_url='login')
@permission_required("home.view_servicio", raise_exception=True)
def tabla_servicios(request):
    mostrar = request.GET.get('mostrar_inactivos', 'false') == 'true'
    if mostrar:
        servicios = Servicio.objects.all()
    else:
        servicios = Servicio.objects.filter(estadoServicio='ACTIVO')
    return render(request, 'home/tablaServicios.html', {
        'servicios': servicios,
        'mostrar_inactivos': mostrar,
    })

@login_required(login_url='login')
def reporte_servicios_pdf(request):
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="reporte_servicios.pdf"'
    p = canvas.Canvas(response, pagesize=letter)
    width, height = letter
    logo_width, logo_height, logo_margin = 100, 100, 15

    config = Configuracion.objects.order_by('-fechaConfiguracion').first()
    logo_path = config.logo.path if config and config.logo else None
    firma_path = config.firma.path if config and config.firma else None
    nombre_institucion = config.nombreInstitucion if config else "Institución"
    rif_institucion = config.rif if config else ""

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
    p.drawCentredString(safe_center, text_top - 40, "REPORTE DE SERVICIOS")

    if firma_path and os.path.exists(firma_path):
        p.drawImage(firma_path, width/2 - 60, 60, width=120, height=60, preserveAspectRatio=True, mask='auto')
        p.setFont("Helvetica-Oblique", 10)
        p.drawCentredString(width/2, 25, "Firma autorizada")

    servicios = Servicio.objects.all()
    data = [["ID", "Nombre", "Tiempo", "Precio", "Estado", "Fecha"]]
    for s in servicios:
        data.append([
            str(s.idServicio),
            s.nombreServicio,
            s.tiempoServicio,
            s.precioServicio,
            s.estadoServicio,
            s.fechaServicio.strftime("%d/%m/%Y")
        ])
    col_widths = [40, 120, 80, 80, 60, 60]
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

#TRAMITE
@login_required(login_url='login')
@permission_required("home.add_tramite", raise_exception=True)
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
    return render(request, 'home/tramite.html', {'form': form})

@login_required(login_url='login')
@permission_required("home.change_tramite", raise_exception=True)
def edit_tramite(request, pk):
    tramite = get_object_or_404(Tramite, pk=pk)
    if request.method == 'POST':
        form = TramiteForm(request.POST, instance=tramite)
        if form.is_valid():
            form.save()
            return JsonResponse({'success': True, 'message': 'Trámite actualizado.'})
        else:
            return JsonResponse({'success': False, 'errors': form.errors})
    else:
        form = TramiteForm(instance=tramite)
    return render(request, 'home/modales/editTramite.html', {'form': form, 'tramite':tramite})

@login_required(login_url='login')
@permission_required("home.change_tramite", raise_exception=True)
def delete_tramite(request, pk):
    instance = get_object_or_404(Tramite, pk=pk)
    instance.estadoTramite = 'INACTIVO'
    instance.save()
    return JsonResponse({'success': True, 'message': 'Eliminación lógica exitosa.'})

@login_required
@permission_required('home.change_tramite', raise_exception=True)
def desactivar_tramite(request, pk):
    tramites = get_object_or_404(Tramite, pk=pk)
    if request.method == 'POST':
        tramites.estadoTramite = "INACTIVO"
        tramites.save()
        messages.success(request, f'⛔ Trámite {tramites.nombreTramite} desactivado')
        return redirect(request.POST.get('next', 'tabla_tramites'))
    return redirect('tabla_tramites')

@login_required(login_url='login')
@permission_required("home.change_tramite", raise_exception=True)
def reactivate_tramite(request, pk):
    tramites = get_object_or_404(Tramite, pk=pk)
    if request.method == 'POST':
        tramites.estadoTramite = "ACTIVO"
        tramites.save()
        messages.success(request, f'✅ Trámite {tramites.nombreTramite} activado')
        return redirect(request.POST.get('next', 'tabla_tramites'))
    return redirect('tabla_tramites')

@login_required(login_url='login')
@permission_required("home.view_tramite", raise_exception=True)
def tabla_tramites(request):
    mostrar = request.GET.get('mostrar_inactivos', 'false') == 'true'
    if mostrar:
        tramites = Tramite.objects.all()
    else:
        tramites = Tramite.objects.filter(estadoTramite='ACTIVO')
    return render(request, 'home/tablaTramites.html', {
        'tramites': tramites,
        'mostrar_inactivos': mostrar,
    })


@login_required(login_url='login')
def reporte_tramites_pdf(request):
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="reporte_tramites.pdf"'
    p = canvas.Canvas(response, pagesize=letter)
    width, height = letter
    logo_width, logo_height, logo_margin = 100, 100, 15

    config = Configuracion.objects.order_by('-fechaConfiguracion').first()
    logo_path = config.logo.path if config and config.logo else None
    firma_path = config.firma.path if config and config.firma else None
    nombre_institucion = config.nombreInstitucion if config else "Institución"
    rif_institucion = config.rif if config else ""

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
    p.drawCentredString(safe_center, text_top - 40, "REPORTE DE TRÁMITES")

    if firma_path and os.path.exists(firma_path):
        p.drawImage(firma_path, width/2 - 60, 60, width=120, height=60, preserveAspectRatio=True, mask='auto')
        p.setFont("Helvetica-Oblique", 10)
        p.drawCentredString(width/2, 25, "Firma autorizada")

    tramites = Tramite.objects.all()
    data = [["ID", "Nombre", "Tiempo", "Precio", "Estado", "Fecha"]]
    for t in tramites:
        data.append([
            str(t.idTramite),
            t.nombreTramite,
            t.diasTramite,
            t.precioTramite,
            t.estadoTramite,
            t.fechaTramite.strftime("%d/%m/%Y")
        ])
    col_widths = [40, 120, 80, 80, 60, 60]
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


#DENOMINACION
@login_required(login_url='login')
@permission_required("home.add_denominacion", raise_exception=True)
def denominacion_modal(request):
    denominaciones = Denominacion.objects.filter(estadoDenominacion='ACTIVO')  # Filtrar denominaciones activas
    if request.method == 'POST':
        form = DenominacionForm(request.POST)
        if form.is_valid():
            form.save()
            return JsonResponse({'success': True, 'message': 'Registro exitoso.'})
        else:
           # print(form.errors)  # esto para depurar errores
            errors = {field: error for field, error in form.errors.items()}
            return JsonResponse({'success': False, 'errors': errors})
    else:
        form = DenominacionForm()
    return render(request, 'home/denominacion.html', {
        'form': form,
        'denominaciones': denominaciones,
    })

@login_required(login_url='login')
@permission_required("home.change_denominacion", raise_exception=True)
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

@login_required
@permission_required('home.change_denominacion', raise_exception=True)
def desactivar_denominacion(request, pk):
    denominaciones = get_object_or_404(Denominacion, pk=pk)
    if request.method == 'POST':
        denominaciones.estadoDenominacion = "INACTIVO"
        denominaciones.save()
        messages.success(request, f'✅ Denominación {denominaciones.nombreDenominacion} desactivada')
        return redirect(request.POST.get('next', 'tabla_denominaciones'))
    return redirect('tabla_denominaciones')

@login_required(login_url='login')
@permission_required("home.change_denominacion", raise_exception=True)
def delete_denominacion(request, pk):
    instance = get_object_or_404(Denominacion, pk=pk)
    instance.estadoDenominacion = 'INACTIVO'
    instance.save()
    return JsonResponse({'success': True, 'message': 'Eliminación lógica exitosa.'})

@login_required(login_url='login')
@permission_required("home.change_denominacion", raise_exception=True)
def reactivate_denominacion(request, pk):
    denominaciones = get_object_or_404(Denominacion, pk=pk)
    if request.method == 'POST':
        denominaciones.estadoDenominacion = "ACTIVO"
        denominaciones.save()
        messages.success(request, f'✅ Denominación {denominaciones.nombreDenominacion} activada')
        return redirect(request.POST.get('next', 'tabla_denominaciones'))
    return redirect('tabla_denominaciones')

@login_required(login_url='login')
@permission_required("home.view_denominacion", raise_exception=True)
def tabla_denominaciones(request):
    mostrar = request.GET.get('mostrar_inactivos', 'false') == 'true'
    if mostrar:
        denominaciones = Denominacion.objects.all()
    else:
        denominaciones = Denominacion.objects.filter(estadoDenominacion='ACTIVO')
    return render(request, 'home/tablaDenominaciones.html', {
        'denominaciones': denominaciones,
        'mostrar_inactivos': mostrar,
    })

@login_required(login_url='login')
@permission_required("home.view_denominacion", raise_exception=True)
def reporte_denominaciones_pdf(request):
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="reporte_denominaciones.pdf"'
    p = canvas.Canvas(response, pagesize=letter)
    width, height = letter
    logo_width, logo_height, logo_margin = 100, 100, 15

    config = Configuracion.objects.order_by('-fechaConfiguracion').first()
    logo_path = config.logo.path if config and config.logo else None
    nombre_institucion = config.nombreInstitucion if config else "Institución"
    rif_institucion = config.rif if config else ""

    # Área útil para centrar
    safe_left = logo_margin + logo_width
    safe_right = width - logo_margin - logo_width
    safe_width = safe_right - safe_left
    safe_center = safe_left + safe_width / 2

    # Mostrar el logo si existe
    if logo_path and os.path.exists(logo_path):
        p.drawImage(logo_path, width - logo_width - logo_margin, height - logo_height - logo_margin, width=logo_width, height=logo_height, preserveAspectRatio=True, mask='auto')

    text_top = height - logo_margin - 22
    p.setFont("Helvetica-Bold", 11)
    p.drawCentredString(safe_center, text_top, nombre_institucion)
    p.drawCentredString(safe_center, text_top - 20, f"RIF: {rif_institucion}")
    p.drawCentredString(safe_center, text_top - 40, "REPORTE DE DENOMINACIONES")

    denominaciones = Denominacion.objects.all()
    data = [["ID", "Nombre", "Estado", "Fecha"]]
    for d in denominaciones:
        data.append([
            str(d.idDenominacion),
            d.nombreDenominacion,
            d.estadoDenominacion,
            d.fechaDenominacion.strftime("%d/%m/%Y")
        ])
    col_widths = [40, 120, 60, 60]
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


#BANCO
@login_required(login_url='login')
@permission_required("home.add_banco", raise_exception=True)
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
    return render(request, 'home/banco.html', {'form': form})

@login_required(login_url='login')
@permission_required("home.change_banco", raise_exception=True)
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

@login_required
@permission_required('home.change_moneda', raise_exception=True)
def desactivar_banco(request, pk):
    banco = get_object_or_404(Banco, pk=pk)
    # Actualizamos el estado sin modificar el nombre u otros campos únicos
    banco.estadoBanco = 'INACTIVO'
    try:
        banco.save()  # Aquí se ejecuta la validación en save()
        return JsonResponse({'success': True, 'message': 'Banco desactivado correctamente. ✅'})
    except ValidationError as e:
        # Regresamos el mensaje de error; esto ocurriría si se dispara la validación única
        return JsonResponse({'success': False, 'message': e.messages})

@login_required(login_url='login')
@permission_required("home.change_banco", raise_exception=True)
def delete_banco(request, pk):
    instance = get_object_or_404(Banco, pk=pk)
    instance.estadoBanco = 'INACTIVO'
    instance.save()
    return JsonResponse({'success': True, 'message': 'Eliminación lógica exitosa.'})

@login_required(login_url='login')
@permission_required("home.change_banco", raise_exception=True)
def reactivate_banco(request, pk):
    banco = get_object_or_404(Banco, pk=pk)
    # Actualizamos el estado sin modificar el nombre u otros campos únicos
    banco.estadoBanco = 'ACTIVO'
    try:
        banco.save()  # Aquí se ejecuta la validación en save()
        return JsonResponse({'success': True, 'message': 'Banco reactivado correctamente. ✅'})
    except ValidationError as e:
        # Regresamos el mensaje de error; esto ocurriría si se dispara la validación única
        return JsonResponse({'success': False, 'message': e.messages})

@login_required
@permission_required('home.view_banco', raise_exception=True)
def tabla_bancos(request):
    mostrar = request.GET.get('mostrar_inactivos', 'false') == 'true'
    if mostrar:
        bancos = Banco.objects.all()
    else:
        bancos = Banco.objects.filter(estadoBanco='ACTIVO')
    return render(request, 'home/tablaBancos.html', {
        'bancos': bancos,
        'mostrar_inactivos': mostrar,
    })

@login_required(login_url='login')
@permission_required("home.view_banco", raise_exception=True)
def reporte_bancos_pdf(request):
    #Seleccion de cantidad de registros
    start = int(request.GET.get('start', 1))
    end = int(request.GET.get('end', 0))
    bancos = list(Banco.objects.all())
    if end == 0 or end > len(bancos):
        end = len(bancos)
    bancos = bancos[start-1:end]

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="reporte_bancos.pdf"'
    p = canvas.Canvas(response, pagesize=letter)
    width, height = letter
    logo_width, logo_height, logo_margin = 100, 100, 15

    config = Configuracion.objects.order_by('-fechaConfiguracion').first()
    logo_path = config.logo.path if config and config.logo else None
    firma_path = config.firma.path if config and config.firma else None
    nombre_institucion = config.nombreInstitucion if config else "Institución"
    rif_institucion = config.rif if config else ""

    safe_left = logo_margin + logo_width
    safe_right = width - logo_margin - logo_width
    safe_width = safe_right - safe_left
    safe_center = safe_left + safe_width / 2

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
        p.drawString(logo_margin, text_top - 100, "REPORTE DE BANCOS")

    def draw_footer():
        if firma_path and os.path.exists(firma_path):
            p.drawImage(firma_path, width/2 - 60, 60, width=120, height=60, preserveAspectRatio=True, mask='auto')
            p.setFont("Helvetica-Oblique", 10)
            p.drawCentredString(width/2, 40, "Firma autorizada")

    # --- Datos de la tabla ---
    data = [["ID", "Nombre", "Código", "Contable", "Estado", "Fecha"]]
    for b in bancos:
        data.append([
            str(b.idBanco),
            b.nombreBanco,
            b.codBanco,
            b.codContable,
            b.estadoBanco,
            b.fechaBanco.strftime("%d/%m/%Y")
        ])
    col_widths = [40, 120, 60, 60, 60, 60]
    table_width = sum(col_widths)

    # --- Cálculo de espacio ---
    header_height = 100  # Altura total del encabezado (ajusta según tu diseño)
    footer_height = 160  # Altura total del pie de página
    row_height = 22      # Altura de cada fila de la tabla (ajusta si usas más o menos padding)
    available_height = height - header_height - footer_height

    max_rows_per_page = int(available_height // row_height)
    if max_rows_per_page < 1:
        max_rows_per_page = 1

    total_rows = len(data) - 1  # Excluye encabezado
    page = 0

    for start in range(0, total_rows, max_rows_per_page):
        end = start + max_rows_per_page
        page_data = [data[0]] + data[start + 1:end + 1]
        if page > 0:
            p.showPage()
        draw_header()
        # Y de inicio: justo debajo del encabezado
        y = height - header_height
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
        table.drawOn(p, safe_left + (safe_width - table_width) / 2, y - row_height * len(page_data))
        draw_footer()
        page += 1

    p.save()
    return response


#MONEDA
@login_required(login_url='login')
@permission_required("home.add_moneda", raise_exception=True)
def moneda_modal(request):
    monedas = Moneda.objects.filter(estadoMoneda='ACTIVO')  # Filtrar monedas activas
    if request.method == 'POST':
        form = MonedaForm(request.POST)
        if form.is_valid():
            form.save()
            return JsonResponse({'success': True, 'message': 'Registro exitoso.'})
        else:
           # print(form.errors)  # esto para depurar errores
            errors = {field: error for field, error in form.errors.items()}
            return JsonResponse({'success': False, 'errors': errors})
    else:
        form = MonedaForm()
    return render(request, 'home/moneda.html', {
        'form': form,
        'monedas': monedas,
    })

@login_required(login_url='login')
@permission_required("home.change_moneda", raise_exception=True)
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

@login_required
@permission_required('home.change_moneda', raise_exception=True)
def desactivar_moneda(request, pk):
    moneda = get_object_or_404(Moneda, pk=pk)
    if request.method == 'POST':
        moneda.estadoMoneda = "INACTIVO"
        moneda.save()
        messages.success(request, f'✅ Moneda {moneda.nombreMoneda} desactivada')
        return redirect(request.POST.get('next', 'tabla_monedas'))
    return redirect('tabla_monedas')

@login_required(login_url='login')
@permission_required("home.change_moneda", raise_exception=True)
def delete_moneda(request, pk):
    instance = get_object_or_404(Moneda, pk=pk)
    instance.estadoMoneda = 'INACTIVO'
    instance.save()
    return JsonResponse({'success': True, 'message': 'Eliminación lógica exitosa.'})

@login_required(login_url='login')
@permission_required("home.change_moneda", raise_exception=True)
def reactivate_moneda(request, pk):
    moneda = get_object_or_404(Moneda, pk=pk)
    if request.method == 'POST':
        moneda.estadoMoneda = "ACTIVO"
        moneda.save()
        messages.success(request, f'✅ Moneda {moneda.nombreMoneda} activada')
        return redirect(request.POST.get('next', 'tabla_monedas'))
    return redirect('tabla_monedas')

@login_required(login_url='login')
@permission_required("home.view_moneda", raise_exception=True)
def tabla_monedas(request):
    mostrar = request.GET.get('mostrar_inactivos', 'false') == 'true'
    if mostrar:
        monedas = Moneda.objects.all()
    else:
        monedas = Moneda.objects.filter(estadoMoneda='ACTIVO')
    return render(request, 'home/tablaMonedas.html', {
        'monedas': monedas,
        'mostrar_inactivos': mostrar,
    })

@login_required(login_url='login')
def reporte_monedas_pdf(request):
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="reporte_monedas.pdf"'
    p = canvas.Canvas(response, pagesize=letter)
    width, height = letter
    logo_width, logo_height, logo_margin = 100, 100, 15

    config = Configuracion.objects.order_by('-fechaConfiguracion').first()
    logo_path = config.logo.path if config and config.logo else None
    nombre_institucion = config.nombreInstitucion if config else "Institución"
    rif_institucion = config.rif if config else ""

    # Encabezado alineado a la izquierda (más de 4 campos)
    x_title = 40
    p.setFont("Helvetica-Bold", 12)
    p.drawString(x_title, height - 40, nombre_institucion)
    p.drawString(x_title, height - 60, f"RIF: {rif_institucion}")
    p.drawString(x_title, height - 80, "REPORTE DE MONEDAS")

    monedas = Moneda.objects.all()
    data = [["ID", "Nombre", "Símbolo", "Estado", "Fecha"]]
    for m in monedas:
        data.append([
            str(m.idMoneda),
            m.nombreMoneda,
            m.simboloMoneda,
            m.estadoMoneda,
            m.fechaMoneda.strftime("%d/%m/%Y")
        ])
    col_widths = [40, 120, 60, 60, 60]
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
    table.drawOn(p, x_title, height - 120 - 25 * len(data))
    p.showPage()
    p.save()
    return response

#TASA
@login_required(login_url='login')
@permission_required("home.add_tasa", raise_exception=True)
def tasa_modal(request):
    monedas = Moneda.objects.filter(estadoMoneda='ACTIVO')  # Filtrar monedas activas
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
    return render(request, 'home/tasa.html', {
        'form': form,
        'monedas': monedas,
    })

@login_required(login_url='login')
@permission_required("home.change_tasa", raise_exception=True)
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

@login_required
@permission_required('home.change_tasa', raise_exception=True)
def desactivar_tasa(request, pk):
    tasa = get_object_or_404(Tasa, pk=pk)
    if request.method == 'POST':
        tasa.estadoTasa = "INACTIVO"
        tasa.save()
        messages.success(request, f'✅ Moneda {tasa.idMoneda.nombreMoneda} desactivada')
        return redirect(request.POST.get('next', 'tabla_tasas'))
    return redirect('tabla_tasas')

@login_required(login_url='login')
@permission_required("home.change_tasa", raise_exception=True)
def delete_tasa(request, pk):
    instance = get_object_or_404(Tasa, pk=pk)
    instance.estadoTasa = 'INACTIVO'
    instance.save()
    return JsonResponse({'success': True, 'message': 'Eliminación lógica exitosa.'})

@login_required(login_url='login')
@permission_required("home.change_tasa", raise_exception=True)
def reactivate_tasa(request, pk):
    tasa = get_object_or_404(Tasa, pk=pk)
    if request.method == 'POST':
        tasa.estadoTasa = "ACTIVO"
        tasa.save()
        messages.success(request, f'✅ Moneda {tasa.idMoneda.nombreMoneda} activada')
        return redirect(request.POST.get('next', 'tabla_tasas'))
    return redirect('tabla_tasas')

@login_required(login_url='login')
@permission_required("home.view_tasa", raise_exception=True)
def tabla_tasas(request):
    mostrar = request.GET.get('mostrar_inactivos', 'false') == 'true'
    if mostrar:
        tasas = Tasa.objects.all()
    else:
        tasas = Tasa.objects.filter(estadoTasa='ACTIVO')
    return render(request, 'home/tablaTasas.html', {
        'tasas': tasas,
        'mostrar_inactivos': mostrar,
    })

@login_required(login_url='login')
def reporte_tasas_pdf(request):
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="reporte_tasas.pdf"'
    p = canvas.Canvas(response, pagesize=letter)
    width, height = letter
    logo_width, logo_height, logo_margin = 100, 100, 15

    config = Configuracion.objects.order_by('-fechaConfiguracion').first()
    logo_path = config.logo.path if config and config.logo else None
    nombre_institucion = config.nombreInstitucion if config else "Institución"
    rif_institucion = config.rif if config else ""

    # Encabezado alineado a la izquierda (menos de 5 campos)
    x_title = 40
    p.setFont("Helvetica-Bold", 12)
    p.drawString(x_title, height - 40, nombre_institucion)
    p.drawString(x_title, height - 60, f"RIF: {rif_institucion}")
    p.drawString(x_title, height - 80, "REPORTE DE TASAS CAMBIARIAS")

    tasas = Tasa.objects.select_related('idMoneda').all()
    data = [["ID", "Moneda", "Monto", "Estado", "Fecha"]]
    for t in tasas:
        data.append([
            str(t.idTasa),
            t.idMoneda.nombreMoneda if t.idMoneda else "",
            t.montoTasa,
            t.estadoTasa,
            t.fechaTasa.strftime("%d/%m/%Y")
        ])
    col_widths = [40, 120, 80, 60, 60]
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
    table.drawOn(p, x_title, height - 120 - 25 * len(data))
    p.showPage()
    p.save()
    return response


#TIPO MOVIMIENTO
@login_required(login_url='login')
@permission_required("home.add_tipomovimiento", raise_exception=True)
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
    return render(request, 'home/tipoMovimiento.html', {'form': form})

@login_required(login_url='login')
@permission_required("home.change_tipomovimiento", raise_exception=True)
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

@login_required
@permission_required('home.change_tipomovimiento', raise_exception=True)
def desactivar_tipoMovimiento(request, pk):
    tipoMovimientos = get_object_or_404(TipoMovimiento, pk=pk)
    if request.method == 'POST':
        tipoMovimientos.estadoTipoMovimiento = "INACTIVO"
        tipoMovimientos.save()
        messages.success(request, f'✅ Movimiento {tipoMovimientos.nombreTipoMovimiento} desactivado')
        return redirect(request.POST.get('next', 'tabla_tipoMovimiento'))
    return redirect('tabla_tipoMovimiento')

@login_required(login_url='login')
@permission_required("home.change_tipomovimiento", raise_exception=True)
def delete_tipoMovimiento(request, pk):
    instance = get_object_or_404(TipoMovimiento, pk=pk)
    instance.estadoTipoMovimiento = 'INACTIVO'
    instance.save()
    return JsonResponse({'success': True, 'message': 'Eliminación lógica exitosa.'})

@login_required(login_url='login')
@permission_required("home.change_tipomovimiento", raise_exception=True)
def reactivate_tipoMovimiento(request, pk):
    instance = get_object_or_404(TipoMovimiento, pk=pk)
    instance.estadoTipoMovimiento = 'ACTIVO'
    instance.save()
    return JsonResponse({'success': True, 'message': 'Reactivación exitosa.'})

@login_required(login_url='login')
@permission_required("home.view_tipomovimiento", raise_exception=True)
def tabla_tipoMovimiento(request):
    TipoMovimiento = TipoMovimiento.objects.all()
    return render(request, 'home/tablaTipoMovimiento.html', {'TipoMovimiento': TipoMovimiento})

#TIPO EGRESO
@login_required(login_url='login')
@permission_required("home.view_tipomovimiento", raise_exception=True)
def tabla_tipoEgresos(request):
    mostrar = request.GET.get('mostrar_inactivos', 'false') == 'true'
    naturaleza = 'egreso'  # Filtro fijo para solo mostrar egresos
    
    base_query = TipoMovimiento.objects.filter(naturaleza=naturaleza)
    
    if mostrar:
        tipoMovimientos = base_query.all()
    else:
        tipoMovimientos = base_query.filter(estadoTipoMovimiento='ACTIVO')
    
    return render(request, 'home/tablaTipoEgresos.html', {
        'tipoMovimientos': tipoMovimientos,
        'mostrar_inactivos': mostrar,
        'naturaleza_actual': naturaleza  # Enviamos la naturaleza al template
    })

@login_required(login_url='login')
@permission_required("home.add_tipomovimiento", raise_exception=True)
def tipoEgreso_modal(request):
    if request.method == 'POST':
        form = TipoMovimientoForm(request.POST)
        if form.is_valid():
            # Crear instancia pero no guardar aún
            instance = form.save(commit=False)
            # Forzar naturaleza egreso
            instance.naturaleza = 'egreso'
            # Guardar en base de datos
            instance.save()
            return JsonResponse({'success': True, 'message': '✅ Tipo de egreso registrado exitosamente'})
        else:
            errors = {field: error.get_json_data()[0]['message'] for field, error in form.errors.items()}
            return JsonResponse({'success': False, 'errors': errors})
    
    # Si es GET, crear form con naturaleza oculta
    form = TipoMovimientoForm(initial={'naturaleza': 'egreso'})
    # Ocultar campo naturaleza en el template
    form.fields['naturaleza'].widget = forms.HiddenInput()
    
    return render(request, 'home/tipoMovimiento.html', {'form': form})

@login_required(login_url='login')
@permission_required("home.change_tipomovimiento", raise_exception=True)
def edit_tipoEgresos(request, pk):
    instance = get_object_or_404(TipoMovimiento, pk=pk, naturaleza='egreso')  # Filtro adicional
    if request.method == 'POST':
        form = TipoMovimientoForm(request.POST, instance=instance, naturaleza='egreso')  # Fijamos naturaleza
        if form.is_valid():
            edited = form.save(commit=False)
            edited.naturaleza = 'egreso'  # Forzamos naturaleza
            edited.save()
            return JsonResponse({'success': True, 'message': 'Tipo de egreso editado correctamente.'})
        else:
            errors = {field: error for field, error in form.errors.items()}
            return JsonResponse({'success': False, 'errors': errors})
    else:
        form = TipoMovimientoForm(instance=instance)
        form.fields['naturaleza'].disabled = True  # Deshabilitar campo en el template
    return render(request, 'home/modales/editTipoMovimiento.html', {
        'form': form,
        'TipoMovimiento': instance,
        'naturaleza': 'egreso'  # Enviar contexto al template
    })

@login_required(login_url='login')
@permission_required('home.change_tipomovimiento', raise_exception=True)
def desactivar_tipoEgreso(request, pk):
    egreso = get_object_or_404(TipoMovimiento, pk=pk, naturaleza='egreso')
    
    if request.method == 'POST':
        egreso.estadoTipoMovimiento = "INACTIVO"
        egreso.save()
        
        # Cambia esto para devolver JSON
        return JsonResponse({
            'success': True,
            'message': f'⛔ Egreso "{egreso.nombreTipoMovimiento}" desactivado'
        })
    
    return JsonResponse({'success': False, 'error': 'Método no permitido'}, status=405)

# Reactivar Egreso
@login_required(login_url='login')
@permission_required("home.change_tipomovimiento", raise_exception=True)
def reactivate_tipoEgreso(request, pk):
    egreso = get_object_or_404(TipoMovimiento, pk=pk, naturaleza='egreso')
    
    if request.method == 'POST':
        egreso.estadoTipoMovimiento = 'ACTIVO'
        egreso.save()
        return JsonResponse({
            'success': True,
            'message': f'✅ Egreso "{egreso.nombreTipoMovimiento}" reactivado exitosamente'
        })
    
    return JsonResponse({'success': False, 'error': 'Método no permitido'}, status=405)

# Eliminación Física (Opcional - Si necesitas borrado real)
@login_required(login_url='login')
@permission_required("home.delete_tipomovimiento", raise_exception=True)
def delete_tipoEgreso(request, pk):
    egreso = get_object_or_404(TipoMovimiento, pk=pk, naturaleza='egreso')
    
    if request.method == 'POST':
        try:
            nombre = egreso.nombreTipoMovimiento
            egreso.delete()
            return JsonResponse({
                'success': True,
                'message': f'🗑️ Egreso "{nombre}" eliminado permanentemente'
            })
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': f'Error al eliminar: {str(e)}'
            }, status=500)
    
    return JsonResponse({'success': False, 'error': 'Método no permitido'}, status=405)

#EGRESO
@login_required(login_url='login')
@permission_required("home.add_movimiento", raise_exception=True)
def tabla_egreso(request):
    mostrar = request.GET.get('mostrar_inactivos', 'false') == 'true'
    naturaleza = 'egreso'  # Filtro fijo para solo mostrar egresos
    
    base_query = Movimiento.objects.filter(naturaleza=naturaleza)
    
    if mostrar:
        movimientos = base_query.all()
    else:
        movimientos = base_query.filter(estadoMovimiento='ACTIVO')
    
    return render(request, 'home/tablaEgresos.html', {
        'movimientos': movimientos,
        'mostrar_inactivos': mostrar,
        'naturaleza_actual': naturaleza  # Enviamos la naturaleza al template
    })

@login_required(login_url='login')
@permission_required("home.add_movimiento", raise_exception=True)
def egreso_modal(request):
    naturaleza = 'egreso'
    action_url = reverse('egreso_modal')  # Obtiene la URL de la vista actual

    if request.method == 'POST':
        form = MovimientoForm(request.POST, initial={'naturaleza': naturaleza})
        if form.is_valid():
            instance = form.save()
            return JsonResponse({'success': True, 'message': '✅ Egreso registrado exitosamente'})
        else:
            errors = {field: error[0] for field, error in form.errors.items()}
            print(form.errors)
            return JsonResponse({'success': False, 'errors': errors})

    else:
        form = MovimientoForm(initial={'naturaleza': naturaleza})

    tasas = Tasa.objects.select_related('idMoneda') \
        .values('idMoneda__idMoneda', 'idMoneda__nombreMoneda') \
        .annotate(ultima_idTasa=Max('idTasa'), ultima_tasa=Max('montoTasa'))

    context = {
        'form': form,
        'bancos': Banco.objects.filter(estadoBanco='ACTIVO'),
        'tipoMovimientos': TipoMovimiento.objects.filter(naturaleza=naturaleza, estadoTipoMovimiento='ACTIVO'),
        'denominaciones': Denominacion.objects.filter(estadoDenominacion='ACTIVO'),
        'monedas': tasas,
        'naturaleza': naturaleza,
        'action_url': action_url  # Agrega la URL al contexto
    }

    return render(request, 'home/movimiento.html', context)

@login_required(login_url='login')
@permission_required("home.change_movimiento", raise_exception=True)
def edit_egreso(request, naturaleza, idMovimiento):
    instance = get_object_or_404(Movimiento, idMovimiento=idMovimiento, naturaleza=naturaleza)

    monedas = Moneda.objects.annotate(
        ultima_tasa_id=Subquery(
            Tasa.objects.filter(idMoneda=OuterRef('idMoneda'))
            .order_by('-fechaTasa')
            .values('idTasa')[:1]
        ),
        ultima_tasa_valor=Subquery(
            Tasa.objects.filter(idMoneda=OuterRef('idMoneda'))
            .order_by('-fechaTasa')
            .values('montoTasa')[:1]
        )
    )

    if request.method == 'POST':
        form = MovimientoForm(request.POST, instance=instance, naturaleza=naturaleza)
        if form.is_valid():
            edited = form.save(commit=False)
            edited.naturaleza = naturaleza
            edited.save()
            return JsonResponse({'success': True, 'message': f'{naturaleza.title()} actualizado correctamente'})
        return JsonResponse({'success': False, 'errors': form.errors.get_json_data()})

    form = MovimientoForm(instance=instance)
    form.fields['naturaleza'].disabled = True

    return render(request, 'home/modales/editMovimiento.html', {
        'form': form,
        'movimiento': instance,
        'naturaleza': naturaleza,
        'bancos': Banco.objects.filter(estadoBanco='ACTIVO'),
        'tipoMovimientos': TipoMovimiento.objects.filter(naturaleza=naturaleza, estadoTipoMovimiento='ACTIVO'),
        'denominaciones': Denominacion.objects.filter(estadoDenominacion='ACTIVO'),
        'monedas': monedas,
    })

@login_required(login_url='login')
@permission_required('home.change_tipomovimiento', raise_exception=True)
def desactivar_egreso(request, pk):
    egreso = get_object_or_404(Movimiento, pk=pk, naturaleza='egreso')
    
    if request.method == 'POST':
        egreso.estadoMovimiento = "INACTIVO"
        egreso.save()
        
        # Cambia esto para devolver JSON
        return JsonResponse({
            'success': True,
            'message': f'⛔ Egreso "{egreso.idMovimiento}" desactivado'
        })
    
    return JsonResponse({'success': False, 'error': 'Método no permitido'}, status=405)

# Reactivar Egreso
@login_required(login_url='login')
@permission_required("home.change_movimiento", raise_exception=True)
def reactivate_egreso(request, pk):
    egreso = get_object_or_404(Movimiento, pk=pk, naturaleza='egreso')
    
    if request.method == 'POST':
        egreso.estadoMovimiento = 'ACTIVO'
        egreso.save()
        return JsonResponse({
            'success': True,
            'message': f'✅ Egreso "{egreso.idMovimiento}" reactivado exitosamente'
        })
    
    return JsonResponse({'success': False, 'error': 'Método no permitido'}, status=405)

# Eliminación Física (Opcional - Si necesitas borrado real)
@login_required(login_url='login')
@permission_required("home.delete_tipomovimiento", raise_exception=True)
def delete_egreso(request, pk):
    egreso = get_object_or_404(Movimiento, pk=pk, naturaleza='egreso')
    
    if request.method == 'POST':
        try:
            nombre = egreso.idMovimiento
            egreso.delete()
            return JsonResponse({
                'success': True,
                'message': f'🗑️ Egreso "{nombre}" eliminado permanentemente'
            })
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': f'Error al eliminar: {str(e)}'
            }, status=500)
    
    return JsonResponse({'success': False, 'error': 'Método no permitido'}, status=405)



#TIPO INGRESO
@login_required(login_url='login')
@permission_required("home.view_tipomovimiento", raise_exception=True)
def tabla_tipoIngresos(request):
    mostrar = request.GET.get('mostrar_inactivos', 'false') == 'true'
    naturaleza = 'ingreso'  # Filtro fijo para solo mostrar egresos
    
    base_query = TipoMovimiento.objects.filter(naturaleza=naturaleza)
    
    if mostrar:
        tipoMovimientos = base_query.all()
    else:
        tipoMovimientos = base_query.filter(estadoTipoMovimiento='ACTIVO')
    
    return render(request, 'home/tablaTipoIngresos.html', {
        'tipoMovimientos': tipoMovimientos,
        'mostrar_inactivos': mostrar,
        'naturaleza_actual': naturaleza  # Enviamos la naturaleza al template
    })

@login_required(login_url='login')
@permission_required("home.add_tipomovimiento", raise_exception=True)
def tipoIngreso_modal(request):
    if request.method == 'POST':
        form = TipoMovimientoForm(request.POST, naturaleza='ingreso')
        if form.is_valid():
            try:
                instance = form.save(commit=False)
                instance.naturaleza = 'ingreso'
                instance.save()
                return JsonResponse({
                    'success': True,
                    'message': 'Tipo de ingreso registrado exitosamente'
                })
            except Exception as e:
                return JsonResponse({
                    'success': False,
                    'error': str(e)
                }, status=500)
        else:
            return JsonResponse({
                'success': False,
                'errors': form.errors.get_json_data()
            }, status=400)
    
    form = TipoMovimientoForm(naturaleza='ingreso')
    return render(request, 'home/tipoMovimiento.html', {'form': form})

@login_required(login_url='login')
@permission_required('home.change_tipomovimiento', raise_exception=True)
def edit_tipoIngresos(request, pk):
    instance = get_object_or_404(TipoMovimiento, pk=pk, naturaleza='ingreso')
    
    if request.method == 'POST':
        # Pasar naturaleza al formulario
        form = TipoMovimientoForm(request.POST, instance=instance, naturaleza='ingreso')
        if form.is_valid():
            edited = form.save()
            return JsonResponse({'success': True, 'message': 'Tipo de ingreso editado correctamente.'})
        else:
            return JsonResponse({'success': False, 'errors': form.errors.get_json_data()})
    else:
        # Inicializar formulario con naturaleza
        form = TipoMovimientoForm(instance=instance, naturaleza='ingreso')
        
    return render(request, 'home/modales/editTipoMovimiento.html', {
        'form': form,
        'TipoMovimiento': instance
    })

@login_required(login_url='login')
@permission_required('home.change_tipomovimiento', raise_exception=True)
def desactivar_tipoIngreso(request, pk):
    ingreso = get_object_or_404(TipoMovimiento, pk=pk, naturaleza='ingreso')
    
    if request.method == 'POST':
        ingreso.estadoTipoMovimiento = "INACTIVO"
        ingreso.save()
        
        # Cambia esto para devolver JSON
        return JsonResponse({
            'success': True,
            'message': f'⛔ Ingreso "{ingreso.nombreTipoMovimiento}" desactivado'
        })
    
    return JsonResponse({'success': False, 'error': 'Método no permitido'}, status=405)

# Reactivar Ingreso
@login_required(login_url='login')
@permission_required("home.change_tipomovimiento", raise_exception=True)
def reactivate_tipoIngreso(request, pk):
    ingreso = get_object_or_404(TipoMovimiento, pk=pk, naturaleza='ingreso')
    
    if request.method == 'POST':
        ingreso.estadoTipoMovimiento = 'ACTIVO'
        ingreso.save()
        return JsonResponse({
            'success': True,
            'message': f'✅ Ingreso "{ingreso.nombreTipoMovimiento}" reactivado exitosamente'
        })
    
    return JsonResponse({'success': False, 'error': 'Método no permitido'}, status=405)

# Eliminación Física (Opcional - Si necesitas borrado real)
@login_required(login_url='login')
@permission_required("home.delete_tipomovimiento", raise_exception=True)
def delete_tipoIngreso(request, pk):
    ingreso = get_object_or_404(TipoMovimiento, pk=pk, naturaleza='ingreso')
    
    if request.method == 'POST':
        try:
            nombre = ingreso.nombreTipoMovimiento
            ingreso.delete()
            return JsonResponse({
                'success': True,
                'message': f'🗑️ Ingreso "{nombre}" eliminado permanentemente'
            })
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': f'Error al eliminar: {str(e)}'
            }, status=500)
    
    return JsonResponse({'success': False, 'error': 'Método no permitido'}, status=405)


#INGRESO
@login_required(login_url='login')
@permission_required("home.add_movimiento", raise_exception=True)
def tabla_ingreso(request):
    mostrar = request.GET.get('mostrar_inactivos', 'false') == 'true'
    naturaleza = 'ingreso'  # Filtro fijo para solo mostrar ingresos
    
    base_query = Movimiento.objects.filter(naturaleza=naturaleza)
    
    if mostrar:
        movimientos = base_query.all()
    else:
        movimientos = base_query.filter(estadoMovimiento='ACTIVO')
    
    return render(request, 'home/tablaIngresos.html', {
        'movimientos': movimientos,
        'mostrar_inactivos': mostrar,
        'naturaleza_actual': naturaleza  # Enviamos la naturaleza al template
    })

@login_required(login_url='login')
@permission_required("home.add_movimiento", raise_exception=True)
def ingreso_modal(request):
    naturaleza = 'ingreso'
    action_url = reverse('ingreso_modal')  # Obtiene la URL de la vista actual

    if request.method == 'POST':
        form = MovimientoForm(request.POST, initial={'naturaleza': naturaleza})
        if form.is_valid():
            instance = form.save()
            return JsonResponse({'success': True, 'message': '✅ Ingreso registrado exitosamente'})
        else:
            errors = {field: error[0] for field, error in form.errors.items()}
            print(form.errors)
            return JsonResponse({'success': False, 'errors': errors})

    else:
        form = MovimientoForm(initial={'naturaleza': naturaleza})

    tasas = Tasa.objects.select_related('idMoneda') \
        .values('idMoneda__idMoneda', 'idMoneda__nombreMoneda') \
        .annotate(ultima_idTasa=Max('idTasa'), ultima_tasa=Max('montoTasa'))

    context = {
        'form': form,
        'bancos': Banco.objects.filter(estadoBanco='ACTIVO'),
        'tipoMovimientos': TipoMovimiento.objects.filter(naturaleza=naturaleza, estadoTipoMovimiento='ACTIVO'),
        'denominaciones': Denominacion.objects.filter(estadoDenominacion='ACTIVO'),
        'monedas': tasas,
        'naturaleza': naturaleza,
        'action_url': action_url  # Agrega la URL al contexto
    }

    return render(request, 'home/movimiento.html', context)

@login_required(login_url='login')
@permission_required("home.change_movimiento", raise_exception=True)
def edit_ingreso(request, naturaleza, idMovimiento):
    instance = get_object_or_404(Movimiento, idMovimiento=idMovimiento, naturaleza=naturaleza)

    monedas = Moneda.objects.annotate(
        ultima_tasa_id=Subquery(
            Tasa.objects.filter(idMoneda=OuterRef('idMoneda'))
            .order_by('-fechaTasa')
            .values('idTasa')[:1]
        ),
        ultima_tasa_valor=Subquery(
            Tasa.objects.filter(idMoneda=OuterRef('idMoneda'))
            .order_by('-fechaTasa')
            .values('montoTasa')[:1]
        )
    )

    if request.method == 'POST':
        form = MovimientoForm(request.POST, instance=instance, naturaleza=naturaleza)
        if form.is_valid():
            edited = form.save(commit=False)
            edited.naturaleza = naturaleza
            edited.save()
            return JsonResponse({'success': True, 'message': f'{naturaleza.title()} actualizado correctamente'})
        return JsonResponse({'success': False, 'errors': form.errors.get_json_data()})

    form = MovimientoForm(instance=instance)
    form.fields['naturaleza'].disabled = True

    return render(request, 'home/modales/editMovimiento.html', {
        'form': form,
        'movimiento': instance,
        'naturaleza': naturaleza,
        'bancos': Banco.objects.filter(estadoBanco='ACTIVO'),
        'tipoMovimientos': TipoMovimiento.objects.filter(naturaleza=naturaleza, estadoTipoMovimiento='ACTIVO'),
        'denominaciones': Denominacion.objects.filter(estadoDenominacion='ACTIVO'),
        'monedas': monedas,
    })

@login_required(login_url='login')
@permission_required('home.change_tipomovimiento', raise_exception=True)
def desactivar_ingreso(request, pk):
    ingreso = get_object_or_404(Movimiento, pk=pk, naturaleza='ingreso')
    
    if request.method == 'POST':
        ingreso.estadoMovimiento = "INACTIVO"
        ingreso.save()
        
        # Cambia esto para devolver JSON
        return JsonResponse({
            'success': True,
            'message': f'⛔ Ingreso "{ingreso.idMovimiento}" desactivado'
        })
    
    return JsonResponse({'success': False, 'error': 'Método no permitido'}, status=405)

# Reactivar Egreso
@login_required(login_url='login')
@permission_required("home.change_movimiento", raise_exception=True)
def reactivate_ingreso(request, pk):
    ingreso = get_object_or_404(Movimiento, pk=pk, naturaleza='ingreso')
    
    if request.method == 'POST':
        ingreso.estadoMovimiento = 'ACTIVO'
        ingreso.save()
        return JsonResponse({
            'success': True,
            'message': f'✅ Ingreso "{ingreso.idMovimiento}" reactivado exitosamente'
        })
    
    return JsonResponse({'success': False, 'error': 'Método no permitido'}, status=405)

# Eliminación Física (Opcional - Si necesitas borrado real)
@login_required(login_url='login')
@permission_required("home.delete_tipomovimiento", raise_exception=True)
def delete_ingreso(request, pk):
    ingreso = get_object_or_404(Movimiento, pk=pk, naturaleza='ingreso')
    
    if request.method == 'POST':
        try:
            nombre = ingreso.idMovimiento
            ingreso.delete()
            return JsonResponse({
                'success': True,
                'message': f'🗑️ Ingreso "{nombre}" eliminado permanentemente'
            })
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': f'Error al eliminar: {str(e)}'
            }, status=500)
    
    return JsonResponse({'success': False, 'error': 'Método no permitido'}, status=405)

#MOVIMIENTOS
@login_required(login_url='login')
@permission_required("home.add_movimiento", raise_exception=True)
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
      
    return render(request, 'home/movimiento.html')

@login_required(login_url='login')
@permission_required("home.change_movimiento", raise_exception=True)
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

@login_required(login_url='login')
@permission_required("home.change_movimiento", raise_exception=True)
def delete_movimiento(request, pk):
    movimiento = get_object_or_404(Movimiento, pk=pk)
    movimiento.estadoMovimiento = 'INACTIVO'
    movimiento.save()
    return JsonResponse({'success': True, 'message': 'Movimiento desactivado'})

@login_required(login_url='login')
@permission_required("home.change_movimiento", raise_exception=True)
def reactivate_movimiento(request, pk):
    movimiento = get_object_or_404(Movimiento, pk=pk)
    movimiento.estadoMovimiento = 'ACTIVO'
    movimiento.save()
    return JsonResponse({'success': True, 'message': 'Movimiento reactivado'})


#FIN 

@login_required(login_url="/login/")
def index(request):
    context = {"segment": "index"}

@login_required(login_url='login')
@permission_required("home.add_configuracion", raise_exception=True)
@permission_required("home.change_configuracion", raise_exception=True)
@permission_required("home.view_configuracion", raise_exception=True)
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


# Vista para actualizar monedas desde la API
@login_required(login_url='login')
@permission_required("home.add_moneda", raise_exception=True)
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
                        estadoMoneda='INACTIVO' # Estado por defecto al crear
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


# Vista para actualizar Bancos de Venezuela desde fuente externa
@login_required(login_url='login')
@permission_required("home.add_banco", raise_exception=True)
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
                            estadoBanco='INACTIVO', # Valor por defecto
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


#PAGES OTRAS
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
        if load_template in [ "tablaBancos.html", "cuentaBanco.html", "tablaCuentaBanco.html"]:
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