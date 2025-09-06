from datetime import datetime
import os
import requests
from django import forms
import re  # Para expresiones regulares
from django.http import JsonResponse, HttpResponse, HttpResponseRedirect
from django.shortcuts import render, redirect, get_object_or_404
from django.template import loader
from django.db.models import OuterRef, Subquery, Max, Count, Sum, Q, Prefetch
from django.urls import reverse
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required, permission_required
from django.db import IntegrityError, transaction
from django.views.decorators.http import require_POST
from django.contrib.auth.models import Group
from collections import defaultdict # Para agrupar
from django.core.paginator import Paginator

from django.core.cache import cache
from django.db import models  # Para el output_field en Sum

from django.template.loader import render_to_string
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import Table, TableStyle
from django.db.models.functions import ExtractMonth

from .forms import AsignarGrupoForm, UsuarioForm, TipoFormacionForm, FormacionForm, MateriaForm, CohorteForm, CargoForm, RequisitoForm, ServicioForm, TramiteForm, DenominacionForm, BancoForm, MonedaForm, TasaForm, TipoMovimientoForm, MovimientoForm, ConfiguracionForm, CuotaFormacionForm
from .models import Personas, Usuarios, TipoFormacion, Formacion, Materia, Cohorte, Cargo, Requisito, Servicio, Tramite, Denominacion, Banco, Moneda, Tasa, Movimiento, TipoMovimiento, Configuracion, CuotaFormacion

from apps.honorario.models import Honorario
from apps.solicitud.models import Solicitud
from apps.cuentaBanco.models import Banco, PlanCuenta, CuentaBanco
from apps.empresa.models import empresa
from apps.persona.models import PersonaTP
from apps.periodoContable.models import periodoContable

from apps.bitacora.signals import registrar_login_fallido

@login_required(login_url='login')
def contabilidad(request):
    # 1. Última cuenta bancaria
    try:
        ultima_cuenta = CuentaBanco.objects.latest('fechaActualizacion')
    except CuentaBanco.DoesNotExist:
        ultima_cuenta = None

    # 2. Última empresa
    try:
        ultima_empresa = empresa.objects.latest('fechaEmpresa')
    except empresa.DoesNotExist:
        ultima_empresa = None

    # 3. Periodo contable actual (el más reciente por fecha de inicio)
    try:
        periodo_actual = periodoContable.objects.filter(estadoPeriodo=True).latest('fechaInicioPeriodo')
    except periodoContable.DoesNotExist:
        periodo_actual = None

    context = {
        'ultima_cuenta': ultima_cuenta,
        'ultima_empresa': ultima_empresa,
        'periodo_actual': periodo_actual,  # Ahora mostramos el período actual
        'total_cuentas': CuentaBanco.objects.count(),
        'total_empresas': empresa.objects.count(),
        'total_periodos': periodoContable.objects.count(),
        'periodos_activos': periodoContable.objects.filter(estadoPeriodo=True).count()
    }
    
    return render(request, 'home/index2.html', context)

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
        if request.user.is_superuser:
            return redirect('home')
        elif request.user.groups.filter(name='Contable').exists():
            return redirect('contabilidad')
        else:
            return redirect('home')

    next_param = request.GET.get('next', 'home')

    if request.method == 'POST':
        cedula_input = request.POST.get('cedula', '').strip()
        password = request.POST.get('password')
        next_param = request.POST.get('next', 'home')

        # Extraer solo los dígitos de la cédula usando regex
        cedula_numerica = re.sub(r'\D', '', cedula_input)

        try:
            persona = Personas.objects.get(cedula__regex=r'[A-Z]-?' + cedula_numerica)
            user = authenticate(request, idPersona=persona.idPersona, password=password)

            if user is not None:
                login(request, user)
                # La señal user_logged_in se dispara automáticamente aquí
                
                if user.is_superuser:
                    return redirect('home')
                elif user.groups.filter(name='Contable').exists():
                    return redirect('contabilidad')
                else:
                    return redirect('home')
            else:
                # REGISTRAR INTENTO FALLIDO (CONTRASEÑA INCORRECTA)
                registrar_login_fallido(
                    username=cedula_input,
                    ip=request.META.get('REMOTE_ADDR')
                )
                messages.error(request, "Contraseña incorrecta")
        except Personas.DoesNotExist:
            # REGISTRAR INTENTO FALLIDO (USUARIO NO EXISTE)
            registrar_login_fallido(
                username=cedula_input,
                ip=request.META.get('REMOTE_ADDR')
            )
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
        cedula    = request.POST.get('cedula')
        password  = request.POST.get('password')
        pregunta  = request.POST.get('preguntaSeguridad')
        respuesta = request.POST.get('respuestaSeguridad')
        
        try:
            # 1) Obtener la persona por cédula
            persona = Personas.objects.get(cedula=cedula)
            
            # 2) Verificar que esa persona tenga asignado el TipoPersona "Usuario" (idTP = 1)
            existe_tipo_usuario = PersonaTP.objects.filter(
                idPersona=persona,
                idTP__idTP=1   # aquí asumimos que 'idTP' es PK de TipoPersona
            ).exists()
            
            if not existe_tipo_usuario:
                messages.error(request, 'Esa cédula no corresponde a un Tipo “Usuario”')
                return render(request, 'home/usuario.html')
            
            # 3) Verificar si ya existe un usuario para esta persona
            if Usuarios.objects.filter(idPersona=persona).exists():
                messages.error(request, 'Ya existe un usuario para esta cédula')
                return render(request, 'home/usuario.html')
            
            # 4) Crear el usuario mediante el manager (create_user)
            usuario = Usuarios.objects.create_user(
                idPersona=persona.idPersona,  # Pasar el ID numérico de la persona
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
            messages.error(request, 'Error: posible usuario duplicado o datos inválidos')
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
    persona = Personas.objects.get(cedula=cedula)
    
    # Asegurar respuesta consistente
    try:
        existe_persona = Personas.objects.filter(cedula=cedula).exists()
        existe_usuario = Usuarios.objects.filter(idPersona__cedula=cedula).exists()
        tiene_tipo_usuario = PersonaTP.objects.filter(idPersona=persona, idTP__idTP=1).exists()
        
        return JsonResponse({
            'existe_en_personas': existe_persona,
            'existe_en_usuarios': existe_usuario,
            'tiene_tipo_usuario': tiene_tipo_usuario
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
    grupo_contable = None
    contable_group_name = 'Contable'
    categorias_stems = {
        'Asiento Contables': 'Asiento Contable',
        'Bancos': 'Banco',
        'Cargos': 'Cargo',
        'Clientes-Proveedores': 'Cliente-Proveedor',
        'Cohortes': 'Cohorte',
        'Configuracion': 'Configuracion',
        'Cuenta Bancarias': 'Cuenta Bancaria',
        'Empresas': 'Empresa',
        'Formaciones': 'Formacion',
        'Honorarios': 'Honorario',
        'Inscripciones': 'Inscripcion',
        'Materias': 'Materia',
        'Monedas': 'Moneda',
        'Periodo Contables': 'Periodo Contable',
        'Plan Cuentas': 'Plan Cuenta',
        'Requisitos': 'Requisito',
        'Saldos Contable': 'Saldo Contable',
        'Servicios': 'Servicio',
        'Solicitudes': 'Solicitud',
        'Tasas': 'Tasa',
        'Tramites': 'Tramite',
        'Tipo Formaciones': 'Tipo Formacion',
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
        # Manejar grupos especiales primero
        if grupo.name == admin_group_name:
            grupo_admin = grupo
            continue  # <-- Este continue hacía que se salteara el contable
            
        if grupo.name == contable_group_name:
            grupo_contable = grupo
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
        "grupo_contable": grupo_contable,
        "grupo_admin_id": grupo_admin.pk if grupo_admin else None,
        "grupo_contable_id": grupo_contable.pk if grupo_contable else None,
        "grupos_categorizados": grupos_categorizados,
    }
    return render(request, 'home/asignar_grupos.html', context)


# PARA LA RECUPERACION DE CONTRASEÑA
def recover_password(request):
    context = {}
    cedula_input = request.POST.get('cedula') if request.method == 'POST' else None

    if request.method == 'POST':
        # --- Validación básica de Cédula ---
        if not cedula_input:
            messages.error(request, "Por favor, ingrese su cédula.")
            return render(request, 'home/login.html', {'show_recover_form': True})

        # Extraer solo los dígitos de la cédula (ej.: "V-12345678" → "12345678")
        cedula_numerica = re.sub(r'\D', '', cedula_input)

        # Construir un regex que busque en la BD el formato completo (letra-guion-dígitos)
        # Por ejemplo: r'^[VJ]-?12345678$'
        regex_busqueda = rf'^[A-Z]-?{cedula_numerica}$'

        try:
            # Buscamos el objeto Persona cuyo campo cedula coincida con el regex
            persona = Personas.objects.get(cedula__regex=regex_busqueda)
            usuario = Usuarios.objects.select_related('idPersona').get(idPersona=persona)

        except Personas.DoesNotExist:
            messages.error(request, "La cédula no se encuentra registrada.")
            context['cedula'] = cedula_input
            context['show_recover_form'] = True
            return render(request, 'home/login.html', context)

        except Usuarios.DoesNotExist:
            messages.error(request, "No existe un usuario vinculado a esta cédula.")
            context['cedula'] = cedula_input
            context['show_recover_form'] = True
            return render(request, 'home/login.html', context)

        except Exception as e:
            messages.error(request, "Ocurrió un error buscando la información del usuario.")
            print(f"Error buscando usuario/persona: {e}")
            context['cedula'] = cedula_input
            context['show_recover_form'] = True
            return render(request, 'home/login.html', context)

        # --- Lógica de Pasos ---
        respuesta_input = request.POST.get('respuestaSeguridad')
        nueva_contrasenia_input = request.POST.get('nueva_contrasenia')
        confirmar_contrasenia_input = request.POST.get('confirmar_contrasenia')

        # Paso 3: Procesar cambio de contraseña
        if nueva_contrasenia_input is not None and confirmar_contrasenia_input is not None:
            context['security_question'] = usuario.preguntaSeguridad
            context['cedula'] = cedula_input
            context['show_password_fields'] = True
            context['show_recover_form'] = True

            if nueva_contrasenia_input != confirmar_contrasenia_input:
                messages.error(request, "Las contraseñas no coinciden.")
                return render(request, 'home/login.html', context)
            elif len(nueva_contrasenia_input) < 8:
                messages.error(request, "La nueva contraseña debe tener al menos 8 caracteres.")
                return render(request, 'home/login.html', context)
            else:
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
            context['cedula'] = cedula_input
            context['security_question'] = usuario.preguntaSeguridad
            context['show_recover_form'] = True

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
            context['cedula'] = cedula_input
            context['show_recover_form'] = True
            messages.info(request, "Usuario encontrado. Por favor, ingrese la respuesta de seguridad.")
            return render(request, 'home/login.html', context)

    # Para peticiones GET
    else:
        context['show_recover_form'] = True
        return render(request, 'home/login.html', context)


#CUOTA FORMACION @¡########################################################
##################################################################

@login_required(login_url='login')
@permission_required("home.add_cuotaformacion", raise_exception=True)
def registrar_cuota_formacion(request, idFormacion=None):
    if idFormacion:
        formaciones = Formacion.objects.filter(idFormacion=idFormacion, estadoFormacion='ACTIVO')
    else:
        formaciones = Formacion.objects.filter(estadoFormacion='ACTIVO')
    
    if request.method == 'POST':
        # Crear instancia manualmente en lugar de usar ModelForm
        try:
            # Obtener datos del POST
            id_formacion = request.POST.get('idFormacion')
            if not id_formacion:
                return JsonResponse({
                    'success': False,
                    'message': "Debe seleccionar una formación."
                })
            
            # Convertir valor a decimal
            valor = request.POST['valorCuota'].replace('.', '').replace(',', '.')
            
            # Crear instancia de CuotaFormacion
            cuota = CuotaFormacion(
                idFormacion_id=id_formacion,  # Usar _id aquí
                nombreCuota=request.POST['nombreCuota'],
                tipoCuota=request.POST['tipoCuota'],
                valorCuota=valor,
                orden=request.POST['orden'],
                # fechaCuota se auto-completa y is_active tiene default
            )
            
            # Validar y guardar
            cuota.full_clean()
            cuota.save()
            
            return JsonResponse({
                'success': True,
                'message': "Cuota de formación registrada exitosamente.",
                'redirect_url': reverse('consultar_cuota_formacion')
            })
            
        except ValidationError as e:
            return JsonResponse({
                'success': False,
                'message': f"Error: {e.messages}"
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f"Error inesperado: {str(e)}"
            })
            
    else:
        return render(request, 'home/cuotaformacion.html', {
            'formaciones': formaciones,
            'tipos_cuota': CuotaFormacion.TIPOS_CUOTA,
        })
from django.core.paginator import Paginator

@login_required(login_url='login')
@permission_required("home.view_cuotaformacion", raise_exception=True)
def consultar_cuota_formacion(request):
    mostrar = request.GET.get('mostrar_inactivos', 'false') == 'true'
    if mostrar:
        cuotaFormaciones = CuotaFormacion.objects.select_related('idFormacion').all()
    else:
        cuotaFormaciones = CuotaFormacion.objects.select_related('idFormacion').filter(is_active=True)

    # Paginación 
    paginator = Paginator(cuotaFormaciones, 10)  # 10 cuotas por página
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'home/tablaCuotasFormaciones.html', {
        'cuotas': page_obj,  # Pasar el objeto de la página al template
        'mostrar_inactivos': mostrar,
    })
#EDITAR CUOTA
@login_required(login_url='login')
@permission_required("home.change_cuotaformacion", raise_exception=True)
def edit_cuota_formacion(request, pk):
    cuota = get_object_or_404(CuotaFormacion, pk=pk)
    if request.method == 'POST':
        post_data = request.POST.copy()
        post_data['idFormacion'] = str(cuota.idFormacion_id)

        valor = post_data.get('valorCuota', '')
        post_data['valorCuota'] = valor.replace('.', '').replace(',', '.')

        form = CuotaFormacionForm(post_data, instance=cuota)
        if form.is_valid():
            form.save()
            return JsonResponse({
              'success': True,
              'message': 'Cuota actualizada correctamente.',
              'redirect': ('tablaCuotasFormaciones.html')
            })
        else:
            errors = {f: e for f,e in form.errors.items()}
            return JsonResponse({'success': False, 'errors': errors})
    else:
        form = CuotaFormacionForm(instance=cuota)
        return render(request, 'home/modales/editCuotaFormacion.html', {
            'form': form, 'cuota': cuota
        })

# DESACTIVAR CUOTAS
@login_required(login_url='login')
@permission_required('home.change_cuotaformacion', raise_exception=True)
def desactivar_cuota_formacion(request, pk):
    cuota = get_object_or_404(CuotaFormacion, pk=pk)
    
    if request.method == 'POST':
        cuota.is_active = False
        cuota.save()
        
        response_data = {
            'success': True,
            'message': f"Cuota {cuota.nombreCuota} desactivada exitosamente."
        }
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse(response_data)
        else:
            messages.success(request, response_data['message'])
            return redirect('consultar_cuota_formacion')
    
    return JsonResponse({'success': False, 'message': 'Método no permitido'}, status=405)

# REACTIVAR CUOTAS
@login_required(login_url='login')
@permission_required('home.change_cuotaformacion', raise_exception=True)
def activar_cuota_formacion(request, pk):
    cuota = get_object_or_404(CuotaFormacion, pk=pk)
    
    if request.method == 'POST':
        cuota.is_active = True
        cuota.save()
        
        response_data = {
            'success': True,
            'message': f"Cuota {cuota.nombreCuota} activada exitosamente."
        }
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse(response_data)
        else:
            messages.success(request, response_data['message'])
            return redirect('consultar_cuota_formacion')
    
    return JsonResponse({'success': False, 'message': 'Método no permitido'}, status=405)

#REPORTE CUOTAS
@login_required(login_url='login')
@permission_required("home.view_cuotaformacion", raise_exception=True)
def reporte_cuotas_formacion_pdf(request):
    # Manejo de parámetros de paginación
    start = int(request.GET.get('start', 1))
    end = int(request.GET.get('end', 0))
    cuotas = list(CuotaFormacion.objects.select_related('idFormacion').all())
    
    if end == 0 or end > len(cuotas):
        end = len(cuotas)
    cuotas = cuotas[start-1:end]

    # Configuración inicial del PDF
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'inline; filename="reporte_cuotas_formacion.pdf"'
    p = canvas.Canvas(response, pagesize=letter)
    p.setTitle("Reporte de Cuotas de Formación")
    width, height = letter
    logo_width, logo_height, logo_margin = 80, 80, 15  # Reducir tamaño del logo

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
        p.drawCentredString(safe_center, text_top - 85, "REPORTE DE CUOTAS DE FORMACIÓN")

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
    headers = ["ID", "Formación", "Nombre", "Tipo", "Valor", "Orden", "Estado"]
    data = [headers]
    
    for cuota in cuotas:
        data.append([
            str(cuota.idCuota),
            cuota.idFormacion.nombreFormacion if cuota.idFormacion else "Sin formación",
            cuota.nombreCuota,
            cuota.get_tipoCuota_display(),
            f"{cuota.valorCuota:.2f}",
            cuota.orden,
            "Activo" if cuota.is_active else "Inactivo"
        ])
    
    # Configuración de la tabla con espacios aumentados
    col_widths = [40, 120, 100, 80, 60, 50, 60]  # Anchos ajustados
    table_width = sum(col_widths)
    
    # Espaciado vertical aumentado
    header_height = 150  # Más espacio para encabezado
    footer_height = 100  # Más espacio para pie de página
    row_height = 25  # Aumentar altura de filas
    cell_padding = 5  # Padding interno en celdas
    
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
            ('FONTSIZE', (0,0), (-1,0), 9),  # Tamaño reducido
            ('ALIGN', (0,0), (-1,0), 'CENTER'),
            ('VALIGN', (0,0), (-1,0), 'MIDDLE'),
            ('BOTTOMPADDING', (0,0), (-1,0), cell_padding),
            
            # Cuerpo de la tabla
            ('FONTSIZE', (0,1), (-1,-1), 8),  # Tamaño reducido
            ('ALIGN', (0,1), (-1,-1), 'CENTER'),
            ('ALIGN', (1,1), (2,-1), 'LEFT'),  # Alinear texto a izquierda
            ('VALIGN', (0,1), (-1,-1), 'MIDDLE'),
            ('BACKGROUND', (0,1), (-1,-1), colors.whitesmoke),
            ('GRID', (0,0), (-1,-1), 0.5, colors.lightgrey),
            ('BOX', (0,0), (-1,-1), 0.5, colors.black),
            ('TOPPADDING', (0,1), (-1,-1), cell_padding),
            ('BOTTOMPADDING', (0,1), (-1,-1), cell_padding),
        ])
        
        # Resaltar valores monetarios
        for i in range(1, len(page_data)):
            table_style.add('TEXTCOLOR', (4,i), (4,i), colors.HexColor("#007bff"))  # Azul para valores
            
        # RESALTAR ESTADOS
        for i in range(1, len(page_data)):
            # Obtener valor del estado (columna 6)
            estado_valor = page_data[i][6].strip().lower()
            
            # Determinar color según estado
            if estado_valor == "activo":
                color = colors.HexColor("#28a745")  # Verde
            elif estado_valor == "inactivo":
                color = colors.HexColor("#dc3545")  # Rojo
            else:
                color = colors.black  # Negro para otros valores
            
            # Aplicar color a la celda de estado (columna 6)
            table_style.add('TEXTCOLOR', (6, i), (6, i), color)
        
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

# FORMACION
@login_required(login_url='login')
@permission_required("home.add_formacion", raise_exception=True)
def formacion_modal(request):
    tipos_formacion = TipoFormacion.objects.filter(estadoTipoFormacion='ACTIVO')
    if request.method == 'POST':
        post_data = request.POST.copy()
        valor = post_data.get('valorInscripcion', '')
        valor = valor.replace('.', '').replace(',', '.')
        post_data['valorInscripcion'] = valor
        form = FormacionForm(post_data)  # Usa solo este formulario

        if form.is_valid():
            try:
                formacion = form.save()
                messages.success(request, "Formación registrada exitosamente.")
                if formacion.tieneCuotas:
                    return redirect('registrar_cuota_formacion', idFormacion=formacion.idFormacion)
                else:
                    return redirect('tabla_formaciones')
            except ValidationError as e:
                messages.error(request, f"Error: {e.messages}")
        else:
            messages.error(request, "Por favor, corrija los errores en el formulario.")
        return render(request, 'home/formaciones.html', {'form': form, 'tipos_formacion': tipos_formacion})
    else:
        form = FormacionForm()
        return render(request, 'home/formaciones.html', {'form': form, 'tipos_formacion': tipos_formacion})

@login_required(login_url='login')
@permission_required("home.change_formacion", raise_exception=True)
def edit_formacion(request, pk):
    formacion = get_object_or_404(Formacion, pk=pk)
    if request.method == 'POST':
        post_data = request.POST.copy()
        valor = post_data.get('valorInscripcion', '')
        valor = valor.replace('.', '').replace(',', '.')
        post_data['valorInscripcion'] = valor
        
        form = FormacionForm(post_data, instance=formacion)
        
        if form.is_valid():
            form.save()
            # Agregar mensaje de éxito y redirigir
            messages.success(request, 'Formación actualizada exitosamente.')
            return redirect('tabla_formaciones')  # Ajusta con tu nombre de URL
        else:
            # Para mostrar errores en el modal sin redirigir
            tipos_formacion = TipoFormacion.objects.all()
            return render(request, 'home/modales/editFormaciones.html', {
                'form': form,
                'formacion': formacion,
                'tipos_formacion': tipos_formacion
            })
    else:
        form = FormacionForm(instance=formacion)
        tipos_formacion = TipoFormacion.objects.all()
        return render(request, 'home/modales/editFormaciones.html', {
            'form': form,
            'formacion': formacion,
            'tipos_formacion': tipos_formacion
        })

@login_required(login_url='login')
@permission_required('home.change_formacion', raise_exception=True)
@require_POST
def desactivar_formacion(request, pk):
    formacion = get_object_or_404(Formacion, pk=pk)
    formacion.estadoFormacion = "INACTIVO"
    formacion.save(update_fields=['estadoFormacion'])
    messages.success(request, f'⛔ Formación {formacion.nombreFormacion} desactivada')
    return redirect(request.POST.get('next', 'tabla_formaciones'))

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
    search_query = request.GET.get('search', '').strip()  # Obtener el término de búsqueda

    if mostrar:
        formaciones = Formacion.objects.all()
    else:
        formaciones = Formacion.objects.filter(estadoFormacion='ACTIVO').order_by('-fechaFormacion')
  
    # Filtrar por el término de búsqueda si existe BUSCADOR
    if search_query:
        formaciones = formaciones.filter(
            Q(nombreFormacion__icontains=search_query) |
            Q(idTF__nombreTipoFormacion__icontains=search_query) |
            Q(valorInscripcion__icontains=search_query) |
            Q(duracion__icontains=search_query)
        )

  
    tipo_formaciones = TipoFormacion.objects.filter(estadoTipoFormacion='ACTIVO')

    formacionesCuotas = Formacion.objects.select_related('idTF')\
        .prefetch_related(Prefetch('cuotas', queryset=CuotaFormacion.objects.order_by('orden')))

    for f in formacionesCuotas:
        cuotas_qs = f.cuotas.all()  # related_name='cuotas'
        if f.tieneCuotas and cuotas_qs.exists():
            cuotas = list(cuotas_qs)
            tipos = {c.tipoCuota for c in cuotas}                # códigos (ej. 'MENSUAL')
            # si todas las cuotas comparten el mismo tipo usamos su display, sino 'Mixto'
            tipo_display = cuotas[0].get_tipoCuota_display() if len(tipos) == 1 else "Mixto"
            # montos formateados con 2 decimales
            montos = ", ".join(f"{c.valorCuota:.2f}" for c in cuotas)
            f.cuotas_count = len(cuotas)
            f.cuotas_list = montos
            f.cuotas_tipo = tipo_display
            f.cuotas_text = f"Sí - {tipo_display} ({f.cuotas_count} cuotas: {montos})"
        elif f.tieneCuotas:
            # tiene el flag pero no hay cuotas creadas
            f.cuotas_count = 0
            f.cuotas_list = ""
            f.cuotas_tipo = ""
            f.cuotas_text = "Sí - (No hay cuotas registradas)"
        else:
            f.cuotas_count = 0
            f.cuotas_list = ""
            f.cuotas_tipo = ""
            f.cuotas_text = "No"
   # Paginación 
    paginator = Paginator(formaciones, 3)  # 10 cuotas por página
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    return render(request, 'home/tablaFormaciones.html', {
        'formaciones':page_obj,
        'tipoFormaciones': tipo_formaciones,
        'mostrar_inactivos': mostrar,
        'search_query': search_query,  # Pasar el término de búsqueda al template

    })

@login_required(login_url='login')
def reporte_formaciones_pdf(request):

    # Manejo de parámetros de paginación
    start = int(request.GET.get('start', 1))
    end = int(request.GET.get('end', 0))
    formaciones = list(Formacion.objects.select_related('idTF').all())
    
    if end == 0 or end > len(formaciones):
        end = len(formaciones)
    formaciones = formaciones[start-1:end]

    # Configuración inicial del PDF
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'inline; filename="reporte_formaciones.pdf"'
    p = canvas.Canvas(response, pagesize=letter)
    p.setTitle("Reporte de Formaciones")
    width, height = letter
    logo_width, logo_height, logo_margin = 80, 80, 15  # Reducir tamaño del logo

    # Obtener configuración institucional
    config = Configuracion.objects.order_by('-fechaConfiguracion').first()
    logo_path = config.logo.path if config and config.logo else None
    firma_path = config.firma.path if config and config.firma else None
    nombre_institucion = config.nombreInstitucion if config else "Institución"
    rif_institucion = config.rif if config else ""
    direccion1 = "AV. ALBERTO RAVELL CON AV. INTERCOMUNAL JOSE ANTONIO PAEZ"  # Dirección fija
    direccion2 = "LOCAL UPTYAB, INDEPENDENCIA – EDO YARACUY"  # Dirección fija

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
        p.drawCentredString(safe_center, text_top - 85, "REPORTE DE FORMACIONES")

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
    headers = ["ID", "TIPO", "NOMBRE", "DURACIÓN", "VALOR", "ESTADO", "FECHA"]
    data = [headers]
    
    for f in formaciones:
        data.append([
            str(f.idFormacion),
            f.idTF.nombreTipoFormacion if f.idTF else "Sin tipo",
            f.nombreFormacion,
            f.duracion,
            f"${float(f.valorInscripcion):,.2f}" if f.valorInscripcion is not None else "-",
            f.estadoFormacion,
            f.fechaFormacion.strftime("%d/%m/%Y")
        ])
    
    # Configuración de la tabla con espacios aumentados
    col_widths = [35, 140, 180, 70, 60, 50, 60]  # Anchos ajustados
    table_width = sum(col_widths)
    
    # Espaciado vertical aumentado
    header_height = 150  # Más espacio para encabezado
    footer_height = 100  # Más espacio para pie de página
    row_height = 25  # Aumentar altura de filas
    cell_padding = 5  # Padding interno en celdas
    
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
            ('FONTSIZE', (0,0), (-1,0), 9),  # Tamaño reducido
            ('ALIGN', (0,0), (-1,0), 'CENTER'),
            ('VALIGN', (0,0), (-1,0), 'MIDDLE'),
            ('BOTTOMPADDING', (0,0), (-1,0), cell_padding),
            
            # Cuerpo de la tabla
            ('FONTSIZE', (0,1), (-1,-1), 8),  # Tamaño reducido
            ('ALIGN', (0,1), (-1,-1), 'CENTER'),
            ('ALIGN', (1,1), (2,-1), 'LEFT'),  # Alinear texto a izquierda
            ('VALIGN', (0,1), (-1,-1), 'MIDDLE'),
            ('BACKGROUND', (0,1), (-1,-1), colors.whitesmoke),
            ('GRID', (0,0), (-1,-1), 0.5, colors.lightgrey),
            ('BOX', (0,0), (-1,-1), 0.5, colors.black),
            ('TOPPADDING', (0,1), (-1,-1), cell_padding),
            ('BOTTOMPADDING', (0,1), (-1,-1), cell_padding),
        ])
        
        # Resaltar valores monetarios
        for i in range(1, len(page_data)):
            table_style.add('TEXTCOLOR', (4,i), (4,i), colors.HexColor("#007bff"))  # Azul para valores
        
         # RESALTAR ESTADOS
        for i in range(1, len(page_data)):
            # Obtener valor del estado (columna 5)
            estado_valor = page_data[i][5].strip().lower()
            
            # Determinar color según estado
            if estado_valor == "activo":
                color = colors.HexColor("#28a745")  # Verde
            elif estado_valor == "inactivo":
                color = colors.HexColor("#dc3545")  # Rojo
            else:
                color = colors.black  # Negro para otros valores
            
            # Aplicar color a la celda de estado (columna 3)
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
    # Manejo de parámetros de paginación
    start = int(request.GET.get('start', 1))
    end = int(request.GET.get('end', 0))
    tipos = list(TipoFormacion.objects.all())
    
    if end == 0 or end > len(tipos):
        end = len(tipos)
    tipos = tipos[start-1:end]

    # Configuración inicial del PDF
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'inline; filename="reporte_tipos_formacion.pdf"'
    p = canvas.Canvas(response, pagesize=letter)
    p.setTitle("Reporte de Tipos Formaciones")
    width, height = letter
    logo_width, logo_height, logo_margin = 80, 80, 15  # Tamaño reducido del logo

    # Obtener configuración institucional
    config = Configuracion.objects.order_by('-fechaConfiguracion').first()
    logo_path = config.logo.path if config and config.logo else None
    firma_path = config.firma.path if config and config.firma else None
    nombre_institucion = config.nombreInstitucion if config else "Institución"
    rif_institucion = config.rif if config else ""
    direccion1 = "AV. ALBERTO RAVELL CON AV. INTERCOMUNAL JOSE ANTONIO PAEZ"  # Dirección fija
    direccion2 = "LOCAL UPTYAB, INDEPENDENCIA – EDO YARACUY"  # Dirección fija

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
        p.drawCentredString(safe_center, text_top - 85, "REPORTE DE TIPOS DE FORMACIÓN")

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
    headers = ["ID", "NOMBRE", "ESTADO", "FECHA"]
    data = [headers]
    
    for t in tipos:
        data.append([
            str(t.idTF),
            t.nombreTipoFormacion,
            t.estadoTipoFormacion,
            t.fechaTipoFormacion.strftime("%d/%m/%Y")
        ])
    
    # Configuración de la tabla con espacios aumentados
    col_widths = [40, 280, 80, 80]  # Anchos ajustados (más espacio para nombres)
    table_width = sum(col_widths)
    
    # Espaciado vertical aumentado
    header_height = 150  # Más espacio para encabezado
    footer_height = 100  # Más espacio para pie de página
    row_height = 25  # Aumentar altura de filas
    cell_padding = 5  # Padding interno en celdas
    
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
            ('FONTSIZE', (0,0), (-1,0), 9),  # Tamaño reducido
            ('ALIGN', (0,0), (-1,0), 'CENTER'),
            ('VALIGN', (0,0), (-1,0), 'MIDDLE'),
            ('BOTTOMPADDING', (0,0), (-1,0), cell_padding),
            
            # Cuerpo de la tabla
            ('FONTSIZE', (0,1), (-1,-1), 8),  # Tamaño reducido
            ('ALIGN', (0,1), (-1,-1), 'CENTER'),
            ('ALIGN', (1,1), (1,-1), 'CENTER'),  # Alinear nombre a izquierda
            ('VALIGN', (0,1), (-1,-1), 'MIDDLE'),
            ('BACKGROUND', (0,1), (-1,-1), colors.whitesmoke),
            ('GRID', (0,0), (-1,-1), 0.5, colors.lightgrey),
            ('BOX', (0,0), (-1,-1), 0.5, colors.black),
            ('TOPPADDING', (0,1), (-1,-1), cell_padding),
            ('BOTTOMPADDING', (0,1), (-1,-1), cell_padding),
        ])
        
         # RESALTAR ESTADOS
        for i in range(1, len(page_data)):
            # Obtener valor del estado (columna 2)
            estado_valor = page_data[i][2].strip().lower()
            
            # Determinar color según estado
            if estado_valor == "activo":
                color = colors.HexColor("#28a745")  # Verde
            elif estado_valor == "inactivo":
                color = colors.HexColor("#dc3545")  # Rojo
            else:
                color = colors.black  # Negro para otros valores
            
            # Aplicar color a la celda de estado (columna 3)
            table_style.add('TEXTCOLOR', (2, i), (2, i), color)
        
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
    # Manejo de parámetros de paginación
    start = int(request.GET.get('start', 1))
    end = int(request.GET.get('end', 0))
    materias = list(Materia.objects.select_related('idFormacion').all())
    
    if end == 0 or end > len(materias):
        end = len(materias)
    materias = materias[start-1:end]

    # Configuración inicial del PDF
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'inline; filename="reporte_materias.pdf"'
    p = canvas.Canvas(response, pagesize=letter)
    p.setTitle("Reporte de Materias")
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
        p.drawCentredString(safe_center, text_top - 85, "REPORTE DE MATERIAS")

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
    headers = ["ID", "FORMACIÓN", "NOMBRE", "ESTADO", "FECHA"]
    data = [headers]
    
    for m in materias:
        data.append([
            str(m.idMateria),
            m.idFormacion.nombreFormacion if m.idFormacion else "Sin formación",
            m.nombreMateria,
            m.estadoMateria,
            m.fechaMateria.strftime("%d/%m/%Y")
        ])
    
    # Configuración de la tabla con espacios aumentados
    col_widths = [40, 180, 180, 70, 70]  # Anchos ajustados
    table_width = sum(col_widths)
    
    # Espaciado vertical aumentado
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
        
        # Estilo de la tabla con más espacio
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
            ('ALIGN', (1,1), (2,-1), 'LEFT'),  # Alinear nombres a izquierda
            ('VALIGN', (0,1), (-1,-1), 'MIDDLE'),
            ('BACKGROUND', (0,1), (-1,-1), colors.whitesmoke),
            ('GRID', (0,0), (-1,-1), 0.5, colors.lightgrey),
            ('BOX', (0,0), (-1,-1), 0.5, colors.black),
            ('TOPPADDING', (0,1), (-1,-1), cell_padding),
            ('BOTTOMPADDING', (0,1), (-1,-1), cell_padding),
        ])
        
         # RESALTAR ESTADOS
        for i in range(1, len(page_data)):
            # Obtener valor del estado (columna 3)
            estado_valor = page_data[i][3].strip().lower()
            
            # Determinar color según estado
            if estado_valor == "activo":
                color = colors.HexColor("#28a745")  # Verde
            elif estado_valor == "inactivo":
                color = colors.HexColor("#dc3545")  # Rojo
            else:
                color = colors.black  # Negro para otros valores
            
            # Aplicar color a la celda de estado (columna 3)
            table_style.add('TEXTCOLOR', (3, i), (3, i), color)

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
        'cohortes': cohortes.order_by('-idCohorte'),
        'mostrar_inactivos': mostrar,
    })

@login_required(login_url='login')
def reporte_cohortes_pdf(request):
    # Manejo de parámetros de paginación
    start = int(request.GET.get('start', 1))
    end = int(request.GET.get('end', 0))
    cohortes = list(Cohorte.objects.all())
    
    if end == 0 or end > len(cohortes):
        end = len(cohortes)
    cohortes = cohortes[start-1:end]

    # Configuración inicial del PDF
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'inline; filename="reporte_cohortes.pdf"'
    p = canvas.Canvas(response, pagesize=letter)
    p.setTitle("Reporte de Cohortes")
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
        p.drawCentredString(safe_center, text_top - 85, "REPORTE DE COHORTES")

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
    headers = ["ID", "NOMBRE", "ESTADO", "FECHA"]
    data = [headers]
    
    for c in cohortes:
        data.append([
            str(c.idCohorte),
            c.nombreCohorte,
            c.estadoCohorte,
            c.fechaCohorte.strftime("%d/%m/%Y")
        ])
    
    # Configuración de la tabla con espacios aumentados
    col_widths = [40, 280, 80, 80]  # Anchos ajustados (más espacio para nombres)
    table_width = sum(col_widths)
    
    # Espaciado vertical aumentado
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
        
        # Estilo de la tabla con más espacio
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
            ('ALIGN', (1,1), (1,-1), 'CENTER'),  # Alinear nombre al centro
            ('VALIGN', (0,1), (-1,-1), 'MIDDLE'),
            ('BACKGROUND', (0,1), (-1,-1), colors.whitesmoke),
            ('GRID', (0,0), (-1,-1), 0.5, colors.lightgrey),
            ('BOX', (0,0), (-1,-1), 0.5, colors.black),
            ('TOPPADDING', (0,1), (-1,-1), cell_padding),
            ('BOTTOMPADDING', (0,1), (-1,-1), cell_padding),
        ])
        
        # Resaltar estados
        for i in range(1, len(page_data)):
            estado_valor = page_data[i][2].strip().lower()
            if estado_valor == "activo":
                color = colors.HexColor("#28a745")  # Verde
            elif estado_valor == "inactivo":
                color = colors.HexColor("#dc3545")  # Rojo
            else:
                color = colors.black  # Negro para otros estados
            table_style.add('TEXTCOLOR', (2,i), (2,i), color)
        
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

@login_required(login_url='login')
def reporte_cargos_pdf(request):
    # Manejo de parámetros de paginación
    start = int(request.GET.get('start', 1))
    end = int(request.GET.get('end', 0))
    cargos = list(Cargo.objects.all())
    
    if end == 0 or end > len(cargos):
        end = len(cargos)
    cargos = cargos[start-1:end]

    # Configuración inicial del PDF
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'inline; filename="reporte_cargos.pdf"'
    p = canvas.Canvas(response, pagesize=letter)
    p.setTitle("Reporte de Cargos")
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
        p.drawCentredString(safe_center, text_top - 85, "REPORTE DE CARGOS")

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
    headers = ["ID", "NOMBRE", "ESTADO", "FECHA"]
    data = [headers]
    
    for cargo in cargos:
        data.append([
            str(cargo.idCargo),
            cargo.nombreCargo,
            cargo.estadoCargo,
            cargo.fechaCargo.strftime("%d/%m/%Y")
        ])
    
    # Configuración de la tabla con espacios aumentados
    col_widths = [40, 280, 80, 80]  # Anchos ajustados (más espacio para nombres)
    table_width = sum(col_widths)
    
    # Espaciado vertical aumentado
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
        
        # Estilo de la tabla con más espacio
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
            ('ALIGN', (1,1), (1,-1), 'LEFT'),  # Alinear nombre a izquierda
            ('VALIGN', (0,1), (-1,-1), 'MIDDLE'),
            ('BACKGROUND', (0,1), (-1,-1), colors.whitesmoke),
            ('GRID', (0,0), (-1,-1), 0.5, colors.lightgrey),
            ('BOX', (0,0), (-1,-1), 0.5, colors.black),
            ('TOPPADDING', (0,1), (-1,-1), cell_padding),
            ('BOTTOMPADDING', (0,1), (-1,-1), cell_padding),
        ])
        
        # Resaltar estados
        for i in range(1, len(page_data)):
            estado_valor = page_data[i][2].strip().lower()
            if estado_valor == "activo":
                color = colors.HexColor("#28a745")  # Verde
            elif estado_valor == "inactivo":
                color = colors.HexColor("#dc3545")  # Rojo
            else:
                color = colors.black  # Negro para otros estados
            table_style.add('TEXTCOLOR', (2,i), (2,i), color)
        
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
        'requisitos': requisitos.order_by('-idRequisito'),
        'mostrar_inactivos': mostrar,
    })

@login_required(login_url='login')
def reporte_requisitos_pdf(request):
    # Manejo de parámetros de paginación
    start = int(request.GET.get('start', 1))
    end = int(request.GET.get('end', 0))
    requisitos = list(Requisito.objects.all())
    
    if end == 0 or end > len(requisitos):
        end = len(requisitos)
    requisitos = requisitos[start-1:end]

    # Configuración inicial del PDF
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'inline; filename="reporte_requisitos.pdf"'
    p = canvas.Canvas(response, pagesize=letter)
    p.setTitle("Reporte de Requisitos")
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
        p.drawCentredString(safe_center, text_top - 85, "REPORTE DE REQUISITOS")

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
    headers = ["ID", "NOMBRE", "ESTADO", "FECHA"]
    data = [headers]
    
    for r in requisitos:
        data.append([
            str(r.idRequisito),
            r.nombreRequisito,
            r.estadoRequisito,
            r.fechaRequisito.strftime("%d/%m/%Y") if r.fechaRequisito else ""
        ])
    
    # Configuración de la tabla con espacios aumentados
    col_widths = [40, 300, 80, 80]  # Anchos ajustados (más espacio para nombres)
    table_width = sum(col_widths)
    
    # Espaciado vertical aumentado
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
        
        # Estilo de la tabla con más espacio
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
            ('ALIGN', (1,1), (1,-1), 'LEFT'),  # Alinear nombre a izquierda
            ('VALIGN', (0,1), (-1,-1), 'MIDDLE'),
            ('BACKGROUND', (0,1), (-1,-1), colors.whitesmoke),
            ('GRID', (0,0), (-1,-1), 0.5, colors.lightgrey),
            ('BOX', (0,0), (-1,-1), 0.5, colors.black),
            ('TOPPADDING', (0,1), (-1,-1), cell_padding),
            ('BOTTOMPADDING', (0,1), (-1,-1), cell_padding),
        ])
        
        # Resaltar estados
        for i in range(1, len(page_data)):
            estado_valor = page_data[i][2].strip().lower()
            if estado_valor == "activo":
                color = colors.HexColor("#28a745")  # Verde
            elif estado_valor == "inactivo":
                color = colors.HexColor("#dc3545")  # Rojo
            else:
                color = colors.black  # Negro para otros estados
            table_style.add('TEXTCOLOR', (2,i), (2,i), color)
        
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
    # Manejo de parámetros de paginación
    start = int(request.GET.get('start', 1))
    end = int(request.GET.get('end', 0))
    servicios = list(Servicio.objects.all())
    
    if end == 0 or end > len(servicios):
        end = len(servicios)
    servicios = servicios[start-1:end]

    # Configuración inicial del PDF
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'inline; filename="reporte_servicios.pdf"'
    p = canvas.Canvas(response, pagesize=letter)
    p.setTitle("Reporte de Servicios")
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
        p.drawCentredString(safe_center, text_top - 85, "REPORTE DE SERVICIOS")

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
    headers = ["ID", "NOMBRE", "TIEMPO", "PRECIO", "ESTADO", "FECHA"]
    data = [headers]
    
    for s in servicios:
        # Manejar el precio de forma segura
        try:
            precio_num = float(s.precioServicio)
            precio_str = f"${precio_num:,.2f}"
        except (TypeError, ValueError):
            precio_str = str(s.precioServicio)
        
        data.append([
            str(s.idServicio),
            s.nombreServicio,
            s.tiempoServicio,
            precio_str,
            s.estadoServicio,
            s.fechaServicio.strftime("%d/%m/%Y") if s.fechaServicio else ""
        ])
    
    # Configuración de la tabla con espacios aumentados
    col_widths = [40, 180, 80, 90, 60, 60]  # Anchos ajustados
    table_width = sum(col_widths)
    
    # Espaciado vertical aumentado
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
        
        # Estilo de la tabla con más espacio
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
            ('ALIGN', (1,1), (1,-1), 'LEFT'),  # Alinear nombre a izquierda
            ('VALIGN', (0,1), (-1,-1), 'MIDDLE'),
            ('BACKGROUND', (0,1), (-1,-1), colors.whitesmoke),
            ('GRID', (0,0), (-1,-1), 0.5, colors.lightgrey),
            ('BOX', (0,0), (-1,-1), 0.5, colors.black),
            ('TOPPADDING', (0,1), (-1,-1), cell_padding),
            ('BOTTOMPADDING', (0,1), (-1,-1), cell_padding),
        ])
        
        # Resaltar estados y precios
        for i in range(1, len(page_data)):
            # Estado
            estado_valor = page_data[i][4].strip().lower()
            if estado_valor == "activo":
                color_estado = colors.HexColor("#28a745")  # Verde
            elif estado_valor == "inactivo":
                color_estado = colors.HexColor("#dc3545")  # Rojo
            else:
                color_estado = colors.black
            table_style.add('TEXTCOLOR', (4,i), (4,i), color_estado)
            
            # Precio (columna 3) en azul si es numérico
            if str(page_data[i][3]).startswith('$'):
                table_style.add('TEXTCOLOR', (3,i), (3,i), colors.HexColor("#007bff"))
        
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
        'tramites': tramites.order_by('-idTramite'),
        'mostrar_inactivos': mostrar,
    })


@login_required(login_url='login')
def reporte_tramites_pdf(request):
    # Manejo de parámetros de paginación
    start = int(request.GET.get('start', 1))
    end = int(request.GET.get('end', 0))
    tramites = list(Tramite.objects.all())
    
    if end == 0 or end > len(tramites):
        end = len(tramites)
    tramites = tramites[start-1:end]

    # Configuración inicial del PDF
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'inline; filename="reporte_tramites.pdf"'
    p = canvas.Canvas(response, pagesize=letter)
    p.setTitle("Reporte de Tramites")
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
        p.drawCentredString(safe_center, text_top - 85, "REPORTE DE TRÁMITES")

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
    headers = ["ID", "NOMBRE", "TIEMPO", "PRECIO", "ESTADO", "FECHA"]
    data = [headers]
    
    for t in tramites:
        # Manejar el precio de forma segura
        try:
            # Intentar convertir a número
            precio_num = float(t.precioTramite)
            precio_str = f"${precio_num:,.2f}"
        except (TypeError, ValueError):
            # Si falla la conversión, usar el valor original
            precio_str = str(t.precioTramite)
        
        data.append([
            str(t.idTramite),
            t.nombreTramite,
            t.diasTramite,
            precio_str,  # Usar el precio formateado o el valor original
            t.estadoTramite,
            t.fechaTramite.strftime("%d/%m/%Y") if t.fechaTramite else ""
        ])
    
    # Configuración de la tabla con espacios aumentados
    col_widths = [40, 180, 70, 90, 60, 60]  # Anchos ajustados
    table_width = sum(col_widths)
    
    # Espaciado vertical aumentado
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
        
        # Estilo de la tabla con más espacio
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
            ('ALIGN', (1,1), (1,-1), 'LEFT'),  # Alinear nombre a izquierda
            ('VALIGN', (0,1), (-1,-1), 'MIDDLE'),
            ('BACKGROUND', (0,1), (-1,-1), colors.whitesmoke),
            ('GRID', (0,0), (-1,-1), 0.5, colors.lightgrey),
            ('BOX', (0,0), (-1,-1), 0.5, colors.black),
            ('TOPPADDING', (0,1), (-1,-1), cell_padding),
            ('BOTTOMPADDING', (0,1), (-1,-1), cell_padding),
        ])
        
        # Resaltar estados y precios
        for i in range(1, len(page_data)):
            # Estado
            estado_valor = page_data[i][4].strip().lower()
            if estado_valor == "activo":
                color_estado = colors.HexColor("#28a745")  # Verde
            elif estado_valor == "inactivo":
                color_estado = colors.HexColor("#dc3545")  # Rojo
            else:
                color_estado = colors.black
            table_style.add('TEXTCOLOR', (4,i), (4,i), color_estado)
            
            # Precio (columna 3) en azul
            # Solo si parece un valor numérico (contiene $ o es convertible)
            if str(page_data[i][3]).startswith('$'):
                table_style.add('TEXTCOLOR', (3,i), (3,i), colors.HexColor("#007bff"))
        
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
    # Manejo de parámetros de paginación
    start = int(request.GET.get('start', 1))
    end = int(request.GET.get('end', 0))
    monedas = list(Moneda.objects.all())
    
    if end == 0 or end > len(monedas):
        end = len(monedas)
    monedas = monedas[start-1:end]

    # Configuración inicial del PDF
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'inline; filename="reporte_monedas.pdf"'
    p = canvas.Canvas(response, pagesize=letter)
    p.setTitle("Reporte de Monedas")
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
        p.drawCentredString(safe_center, text_top - 85, "REPORTE DE MONEDAS")

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
    headers = ["ID", "NOMBRE", "SÍMBOLO", "ESTADO", "FECHA"]
    data = [headers]
    
    for m in monedas:
        data.append([
            str(m.idMoneda),
            m.nombreMoneda,
            m.simboloMoneda,
            m.estadoMoneda,
            m.fechaMoneda.strftime("%d/%m/%Y") if m.fechaMoneda else ""
        ])
    
    # Configuración de la tabla con espacios aumentados
    col_widths = [40, 180, 70, 90, 90]  # Anchos ajustados para las columnas
    table_width = sum(col_widths)
    
    # Espaciado vertical aumentado
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
        
        # Estilo de la tabla con más espacio
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
            ('ALIGN', (1,1), (1,-1), 'LEFT'),  # Alinear nombre a izquierda
            ('VALIGN', (0,1), (-1,-1), 'MIDDLE'),
            ('BACKGROUND', (0,1), (-1,-1), colors.whitesmoke),
            ('GRID', (0,0), (-1,-1), 0.5, colors.lightgrey),
            ('BOX', (0,0), (-1,-1), 0.5, colors.black),
            ('TOPPADDING', (0,1), (-1,-1), cell_padding),
            ('BOTTOMPADDING', (0,1), (-1,-1), cell_padding),
        ])
        
        # Resaltar estados
        for i in range(1, len(page_data)):
            estado_valor = page_data[i][3].strip().lower()
            if estado_valor == "activo":
                color_estado = colors.HexColor("#28a745")  # Verde
            elif estado_valor == "inactivo":
                color_estado = colors.HexColor("#dc3545")  # Rojo
            else:
                color_estado = colors.black
            table_style.add('TEXTCOLOR', (3,i), (3,i), color_estado)
        
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
    search_query = request.GET.get('search', '').strip()  # Obtener el término de búsqueda

    if mostrar:
        tasas = Tasa.objects.all()
    else:
        tasas = Tasa.objects.filter(estadoTasa='ACTIVO').order_by('-fechaTasa')

          # Filtrar por el término de búsqueda si existe BUSCADOR
    if search_query:
        tasas = tasas.filter(
            Q(idMoneda__nombreMoneda__icontains=search_query) |
            Q(idMoneda__simboloMoneda__icontains=search_query) |
            Q(montoTasa__icontains=search_query) |
            Q(estadoTasa__icontains=search_query) |
            Q(fechaTasa__icontains=search_query)
        )
    paginator = Paginator(tasas, 10)  # 10 tasas por página
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    return render(request, 'home/tablaTasas.html', {
        'tasas':page_obj,
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
        form = ConfiguracionForm(request.POST, request.FILES, instance=config_existente)
        
        if form.is_valid():
            try:
                configuracion_guardada = form.save()
                messages.success(
                    request, 
                    f'Configuración institucional {"actualizada" if config_existente else "guardada"} exitosamente.'
                )
                return redirect('configuracion')
            except Exception as e:
                messages.error(
                    request, 
                    f'Ocurrió un error al guardar la configuración: {e}. Por favor, intente de nuevo.'
                )
        else:
            # Mostrar errores específicos
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
    else:
        form = ConfiguracionForm(instance=config_existente)

    context = {
        'form': form,
        'monedas': monedas,
        'configuracion_actual': config_existente
    }
    return render(request, 'home/configuracion.html', context)


# Vista para actualizar monedas desde la API
@login_required(login_url='login')
@permission_required("home.add_moneda", raise_exception=True)
def actualizar_monedas_api(request):
    # Solo permitir método POST para esta acción que modifica datos
    if request.method != 'POST':
        messages.error(request, "Método no permitido.")
        return redirect('tabla_monedas')  # O a donde quieras redirigir

    # URL de la API (puedes ponerla en settings.py si prefieres)
    CURRENCY_API_URL = 'https://openexchangerates.org/api/currencies.json'
    nuevas_monedas_contador = 0
    monedas_fallidas = []

    try:
        # --- 1. Llamada a la API ---
        print(f"DEBUG: Llamando a la API: {CURRENCY_API_URL}")
        response = requests.get(CURRENCY_API_URL, timeout=15)
        response.raise_for_status()

        # --- 2. Procesar Respuesta JSON ---
        api_currencies = response.json()
        print(f"DEBUG: Recibidas {len(api_currencies)} monedas de la API.")

        # --- 3. Obtener Símbolos y Nombres Existentes en BD (normalizados) ---
        codigos_existentes = set(Moneda.objects.values_list('simboloMoneda', flat=True))
        # Normalizamos nombres a lower + strip para comparar insensible a mayúsc/minúsc
        nombres_existentes = set(
            (n.strip().lower() for n in Moneda.objects.values_list('nombreMoneda', flat=True) if n)
        )

        print(f"DEBUG: {len(codigos_existentes)} códigos existentes en BD.")
        print(f"DEBUG: {len(nombres_existentes)} nombres existentes en BD (normalizados).")

        # --- 4. Comparar y Añadir Nuevas Monedas (lista para crear) ---
        monedas_para_crear = []
        for codigo, nombre in api_currencies.items():
            codigo_limpio = codigo.strip()[:5]
            nombre_limpio = nombre.strip()[:100]
            nombre_key = nombre_limpio.lower()

            # Si ya existe por código o por nombre (insensible a mayúsc/minúsc), saltamos
            if codigo_limpio in codigos_existentes or nombre_key in nombres_existentes:
                # DEBUG opcional:
                # print(f"DEBUG: Saltando {codigo_limpio} - {nombre_limpio} (existente)")
                continue

            monedas_para_crear.append(
                Moneda(
                    nombreMoneda=nombre_limpio,
                    simboloMoneda=codigo_limpio,
                    estadoMoneda='INACTIVO'  # Estado por defecto al crear
                )
            )
            # Añadimos inmediatamente a los sets para evitar duplicados dentro del mismo lote
            codigos_existentes.add(codigo_limpio)
            nombres_existentes.add(nombre_key)

        # --- 5. Guardar Nuevas Monedas en BD (si hay) ---
        if monedas_para_crear:
            try:
                # Intentamos bulk_create con ignore_conflicts si la versión de Django lo soporta.
                # Esto evita excepciones por claves únicas que ya hayan aparecido en concurrencia.
                Moneda.objects.bulk_create(monedas_para_crear, ignore_conflicts=True)
                # Si ignore_conflicts se usa, no podemos saber exactamente cuántas se crearon vs ignoradas,
                # pero podemos asumir que intentamos insertar len(monedas_para_crear). Para precisión, podríamos
                # comparar conteos previos/posteriores.
                nuevas_monedas_contador = len(monedas_para_crear)
                print(f"DEBUG: Intentadas {nuevas_monedas_contador} inserciones con bulk_create(ignore_conflicts=True).")
                messages.success(request, f'¡Actualización completada! Se procesaron {nuevas_monedas_contador} monedas (las duplicadas se omitieron).')
            except TypeError:
                # Si la versión de Django no soporta ignore_conflicts en bulk_create, fallback:
                try:
                    with transaction.atomic():
                        Moneda.objects.bulk_create(monedas_para_crear)
                    nuevas_monedas_contador = len(monedas_para_crear)
                    messages.success(request, f'¡Actualización completada! Se añadieron {nuevas_monedas_contador} nuevas monedas.')
                except IntegrityError as e:
                    # Ocurrió una violación de unicidad (posible condición de carrera o inconsistencia).
                    print(f"WARNING: IntegrityError durante bulk_create: {e}. Aplicando inserción segura por fila.")
                    creadas = 0
                    for m in monedas_para_crear:
                        try:
                            # Intentamos crear sólo si no existe; get_or_create evita excepción por unique
                            obj, created_flag = Moneda.objects.get_or_create(
                                simboloMoneda=m.simboloMoneda,
                                defaults={
                                    'nombreMoneda': m.nombreMoneda,
                                    'estadoMoneda': m.estadoMoneda
                                }
                            )
                            if created_flag:
                                creadas += 1
                        except Exception as e2:
                            monedas_fallidas.append(f"{m.simboloMoneda} - {str(e2)}")
                    nuevas_monedas_contador = creadas
                    msg = f'¡Actualización completada! Se añadieron {nuevas_monedas_contador} nuevas monedas.'
                    if monedas_fallidas:
                        msg += f' Algunas no pudieron guardarse: {len(monedas_fallidas)}.'
                    messages.success(request, msg)
            except Exception as db_error:
                # Otro error inesperado de BD
                print(f"ERROR DB al guardar monedas: {db_error}")
                messages.error(request, f'Error al guardar las nuevas monedas en la base de datos: {db_error}')
        else:
            print("DEBUG: No se encontraron nuevas monedas para añadir.")
            messages.info(request, '¡Todo al día! No se encontraron nuevas monedas en la API.')

    except requests.exceptions.RequestException as e:
        print(f"ERROR API: {e}")
        messages.error(request, f"Error al conectar con la API de monedas: {e}")
    except Exception as e:
        print(f"ERROR General: {e}")
        messages.error(request, f"Ocurrió un error inesperado durante la actualización: {e}")

    # --- 6. Redirigir de vuelta ---
    return redirect('tabla_monedas')


@login_required(login_url='login')
@permission_required("home.add_banco", raise_exception=True)
def actualizar_bancos_api(request):
    if request.method != 'POST':
        # Si es AJAX devolvemos JSON, si no redirigimos con message
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({
                'success': False,
                'type': 'error',
                'message': "Método no permitido."
            }, status=405)
        messages.error(request, "Método no permitido.")
        return redirect('banco_list')

    BANK_API_URL = 'https://raw.githubusercontent.com/andresmdev/bankListVEN/refs/heads/master/bankVEN.json'
    nuevos = 0

    try:
        resp = requests.get(BANK_API_URL, timeout=15)
        resp.raise_for_status()
        api_bancos = resp.json()

        cuenta_padre = PlanCuenta.objects.first()
        if not cuenta_padre:
            msg = "No hay cuentas contables padre configuradas."
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'type': 'error', 'message': msg}, status=400)
            messages.error(request, msg)
            return redirect('banco_list')

        # Códigos locales existentes
        cod_exist = set(Banco.objects.values_list('codLocalBanco', flat=True))

        nuevos_list = []
        for item in api_bancos:
            code = (item.get('code') or '').strip()
            name = (item.get('shortName') or '').strip()
            if not code or not name:
                continue

            cod_local = code[:10]
            if cod_local in cod_exist:
                continue

            cod_swift_placeholder = f"SW-N/A-{cod_local}"

            b = Banco(
                nombreBanco=name[:100],
                codLocalBanco=cod_local,
                codSwiftBanco=cod_swift_placeholder,
                cuentaPadre=cuenta_padre,
                estadoBanco=False
            )
            nuevos_list.append(b)
            cod_exist.add(cod_local)

        if nuevos_list:
            Banco.objects.bulk_create(nuevos_list)
            nuevos = len(nuevos_list)
            msg = f"¡Actualización completa! Se añadieron {nuevos} nuevos bancos."
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({'success': True, 'type': 'success', 'added': nuevos, 'message': msg})
            messages.success(request, msg)
        else:
            # No hay nuevos bancos
            msg = "¡Todo al día! No se encontraron bancos nuevos."
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({'success': True, 'type': 'info', 'added': 0, 'message': msg})
            messages.info(request, msg)

    except requests.exceptions.RequestException as e:
        msg = f"Error al obtener datos de bancos: {e}"
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'type': 'error', 'message': msg}, status=502)
        messages.error(request, msg)
    except Exception as e:
        msg = f"Error inesperado al actualizar bancos: {e}"
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'type': 'error', 'message': msg}, status=500)
        messages.error(request, msg)

    return redirect('banco_list')


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