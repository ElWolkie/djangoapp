from django.db.models.signals import post_save, post_delete, pre_save
from django.dispatch import receiver
from django.contrib.auth.signals import user_logged_in, user_logged_out
from django.contrib.auth import get_user_model
from .models import Bitacora
from .middleware import get_current_user, get_current_ip
from .utils import get_field_changes

UsuarioPersonalizado = get_user_model()

@receiver(post_save)
def log_guardado(sender, instance, created, **kwargs):
    # No registrar la bitácora sobre sí misma ni sobre sesiones
    if sender == Bitacora or sender.__name__ == "Session":
        return

    # Obtener usuario e IP
    usuario = get_current_user()
    # Evitar AnonymousUser en la FK
    if not getattr(usuario, 'is_authenticated', False):
        usuario = None
    ip = get_current_ip()

    # Si ni usuario ni IP, salimos
    if not (usuario or ip):
        return

    # Determinar tipo de acción y metadatos
    accion = 'C' if created else 'A'
    modelo = sender.__name__

    # Obtener el ID del objeto
    objeto_id = getattr(instance, 'id', None) or getattr(instance, 'pk', None) or getattr(instance, 'uuid', None)

    # Montar descripción base
    descripcion = f"{'Creó' if created else 'Actualizó'} {modelo}"
    if objeto_id:
        descripcion += f" con ID {objeto_id}"

    # Severidad por defecto
    severidad = 'INFO'

    # Si es actualización, calcular cambios y ajustar severidad
    cambios = None
    if not created and hasattr(instance, '_estado_previo'):
        try:
            campos_excluidos = ['password', 'token', 'firma_digital']
            campos = [
                f.name for f in sender._meta.fields 
                if f.name not in campos_excluidos and not f.auto_created
            ]
            cambios = get_field_changes(instance, instance._estado_previo, campos)
            if cambios:
                # Crear un resumen de valores anteriores→nuevos
                resumen = []
                for datos in cambios.values():
                    ant = (datos['anterior'] or '')[:20]
                    nue = (datos['nuevo'] or '')[:20]
                    resumen.append(f"{ant}→{nue}")
                descripcion += " | " + " ".join(resumen)
                severidad = 'WARNING'
        except Exception as e:
            print(f"Error detectando cambios: {e}")

    # Finalmente, crear el registro de bitácora para creación o modificación
    try:
        Bitacora.objects.create(
            severidad=severidad,
            accion=accion,
            usuario=usuario,
            modelo_afectado=modelo,
            objeto_id=objeto_id,
            cambios=cambios,
            descripcion=descripcion,
            ip=ip,
            estado='S'
        )
    except Exception as e:
        print(f"Error registrando en bitácora: {e}")


@receiver(post_delete)
def log_eliminacion(sender, instance, **kwargs):
    # Evitar registrar acciones sobre ciertos modelos
    if sender == Bitacora or sender.__name__ == "Session":
        return
    
    severidad = 'WARNING'
    usuario = get_current_user()
    ip = get_current_ip()
    
    if usuario or ip:
        modelo = sender.__name__
        
        # Manejo de diferentes tipos de identificadores
        objeto_id = None
        if hasattr(instance, 'id'):
            objeto_id = instance.id
        elif hasattr(instance, 'pk'):
            objeto_id = instance.pk
        elif hasattr(instance, 'uuid'):
            objeto_id = instance.uuid
        
        # Construir descripción segura
        try:
            descripcion = f"Eliminó {modelo}"
            if objeto_id:
                descripcion += f" con ID {objeto_id}"
        except Exception:
            descripcion = f"Eliminó {modelo}"
        
        try:
            Bitacora.objects.create(
                severidad=severidad,
                accion='E',
                usuario=usuario,
                modelo_afectado=modelo,
                objeto_id=objeto_id,
                descripcion=descripcion,
                ip=ip
            )
        except Exception as e:
            print(f"Error registrando en bitácora: {str(e)}")

@receiver(user_logged_in)
def log_login(sender, request, user, **kwargs):
    severidad = 'INFO'
    try:
        usuario_personalizado = UsuarioPersonalizado.objects.get(pk=user.pk)
        Bitacora.objects.create(
            severidad=severidad,
            accion='I',
            usuario=usuario_personalizado,
            modelo_afectado='Auth',
            descripcion='Inicio de sesión exitoso',
            ip=request.META.get('REMOTE_ADDR'),
            estado='S'
        )
    except Exception as e:
        print(f"Error registrando login en bitácora: {str(e)}")

@receiver(user_logged_out)
def log_logout(sender, request, user, **kwargs):
    severidad = 'INFO'
    try:
        if user and not user.is_anonymous:
            usuario_personalizado = UsuarioPersonalizado.objects.get(pk=user.pk)
            Bitacora.objects.create(
                severidad=severidad,
                accion='O',
                usuario=usuario_personalizado,
                modelo_afectado='Auth',
                descripcion='Cierre de sesión',
                ip=request.META.get('REMOTE_ADDR')
            )
    except Exception as e:
        print(f"Error registrando logout en bitácora: {str(e)}")

def registrar_login_fallido(username, ip):
    severidad = 'WARNING'
    try:
        Bitacora.objects.create(
            severidad=severidad,
            accion='I',
            usuario=None,
            modelo_afectado='Auth',
            descripcion=f"Intento fallido: usuario {username}",
            ip=ip,
            estado='F'
        )
    except Exception as e:
        print(f"Error registrando login fallido: {str(e)}")

# Almacenar instancia previa antes de guardar
@receiver(pre_save, sender=None)
def capturar_estado_previo(sender, instance, **kwargs):
    if sender == Bitacora or sender.__name__ == "Session":
        return
    
    if instance.pk:
        try:
            instance._estado_previo = sender.objects.get(pk=instance.pk)
        except sender.DoesNotExist:
            pass