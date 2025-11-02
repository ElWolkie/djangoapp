import os
import pathlib
import hashlib
from django.conf import settings
from django.contrib.admin.views.decorators import staff_member_required
from django.http import HttpResponseRedirect, HttpResponse, JsonResponse
from django.shortcuts import render
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.core.paginator import Paginator
from datetime import timedelta
from .models import Backup, BackupTask, BackupAudit

BACKUP_DIR = getattr(settings, 'BACKUP_DIR', None) or os.path.join(settings.BASE_DIR, 'backups')
pathlib.Path(BACKUP_DIR).mkdir(parents=True, exist_ok=True)

def compute_checksum(file_path):
    """Calcula el checksum SHA256 de un archivo"""
    h = hashlib.sha256()
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            h.update(chunk)
    return h.hexdigest()

def get_user_display_name(user):
    """
    Obtiene el nombre para mostrar del usuario de forma compatible
    con modelos de usuario personalizados
    """
    # Primero intenta con username (estándar de Django)
    if hasattr(user, 'username') and user.username:
        return user.username
    
    # Luego intenta con email
    if hasattr(user, 'email') and user.email:
        return user.email
    
    # Luego intenta con first_name + last_name
    if hasattr(user, 'first_name') and user.first_name:
        name = user.first_name
        if hasattr(user, 'last_name') and user.last_name:
            name += f" {user.last_name}"
        return name
    
    # Finalmente usa la representación string
    return str(user)

def backup_list(request):
    # Obtener parámetros de filtrado
    desde = request.GET.get('desde', '')
    hasta = request.GET.get('hasta', '')
    search = request.GET.get('search', '')
    page_number = request.GET.get('page', 1)
    
    # Aplicar filtros
    backups = Backup.objects.all().order_by('-fecha_creacion')
    
    if desde:
        backups = backups.filter(fecha_creacion__gte=desde)
    if hasta:
        backups = backups.filter(fecha_creacion__lte=hasta)
    if search:
        backups = backups.filter(name__icontains=search)
    
    # Paginación
    paginator = Paginator(backups, 10)  # 10 items por página
    page_obj = paginator.get_page(page_number)
    
    context = {
        'backups': page_obj,
        'page_obj': page_obj,
        'desde': desde,
        'hasta': hasta,
        'search': search,
    }
    
    return render(request, 'backup/list.html', context)

@require_POST
def create_backup(request):
    from django.core import management
    timestamp = timezone.now().strftime('%Y%m%d%H%M%S')
    name = f'db_backup_{timestamp}.dump'
    out = os.path.join(BACKUP_DIR, name)
    
    try:
        # Crear el backup físico
        management.call_command('dbbackup', output=out)
        
        # Crear registro en la base de datos
        file_size = os.path.getsize(out)
        checksum = compute_checksum(out)
        
        # Obtener el nombre de usuario de forma compatible
        username = get_user_display_name(request.user)
        
        backup = Backup.objects.create(
            name=name,
            usuario=username,
            tipo='full',
            ruta_storage=out,
            tamaño=file_size,
            checksum=checksum
        )
        
        # Crear auditoría
        BackupAudit.objects.create(
            backup=backup,
            usuario=username,
            action='create',
            notes=f'Backup creado exitosamente. Tamaño: {file_size} bytes'
        )
        
        return HttpResponseRedirect('/backup/?success=1')
        
    except Exception as e:
        print(f"Error creando backup: {str(e)}")
        import traceback
        traceback.print_exc()
        return HttpResponseRedirect('/backup/?error=1')

@require_POST
def restore_backup(request, backup_id):
    """Vista principal para restaurar backups - usa la misma lógica que la API"""
    try:
        backup = Backup.objects.get(id=backup_id)
        
        # Obtener el nombre de usuario de forma compatible
        username = get_user_display_name(request.user)
        
        # Crear tarea de restauración
        task = BackupTask.objects.create(
            backup=backup,
            status='pending',
            usuario=username
        )
        
        def restore_task():
            try:
                task.started_at = timezone.now()
                task.status = 'running'
                task.save()
                
                # Lógica real de restauración usando el comando dbrestore
                from django.core import management
                management.call_command('dbrestore', input=backup.ruta_storage)
                
                task.finished_at = timezone.now()
                task.status = 'success'
                task.result = 'Restauración completada exitosamente'
                task.save()
                
                # Crear auditoría
                BackupAudit.objects.create(
                    backup=backup,
                    usuario=task.usuario,
                    action='restore',
                    notes='Restauración completada exitosamente'
                )
                
            except Exception as e:
                task.finished_at = timezone.now()
                task.status = 'error'
                task.result = f'Error: {str(e)}'
                task.save()
                
                # Crear auditoría de error
                BackupAudit.objects.create(
                    backup=backup,
                    usuario=task.usuario,
                    action='restore',
                    notes=f'Error en restauración: {str(e)}'
                )
        
        import threading
        thread = threading.Thread(target=restore_task)
        thread.daemon = True
        thread.start()
        
        # Redirigir a la página de backups con un mensaje de éxito
        return HttpResponseRedirect('/backup/?restore_started=1')
        
    except Backup.DoesNotExist:
        return HttpResponseRedirect('/backup/?error=Backup no encontrado')
    except Exception as e:
        print(f"Error en restore_backup: {str(e)}")
        return HttpResponseRedirect('/backup/?error=Error en restauración')

# Mantenemos las APIs solo para las acciones AJAX (restaurar y descargar)
def api_restore_backup(request, backup_id):
    try:
        backup = Backup.objects.get(id=backup_id)
        
        # Obtener el nombre de usuario de forma compatible
        username = get_user_display_name(request.user)
        
        # Crear tarea de restauración
        task = BackupTask.objects.create(
            backup=backup,
            status='pending',
            usuario=username
        )
        
        # Eliminamos el hilo y hacemos la restauración en el mismo hilo
        try:
            task.started_at = timezone.now()
            task.status = 'running'
            task.save()
            
            # Lógica real de restauración usando el comando dbrestore
            from django.core import management
            management.call_command('dbrestore', input=backup.ruta_storage)
            
            task.finished_at = timezone.now()
            task.status = 'success'
            task.result = 'Restauración completada exitosamente'
            task.save()
            
            # Crear auditoría
            BackupAudit.objects.create(
                backup=backup,
                usuario=task.usuario,
                action='restore',
                notes='Restauración completada exitosamente'
            )
            
            return HttpResponseRedirect('/backup/?restore_success=1')
            
        except Exception as e:
            task.finished_at = timezone.now()
            task.status = 'error'
            task.result = f'Error: {str(e)}'
            task.save()
            
            # Crear auditoría de error
            BackupAudit.objects.create(
                backup=backup,
                usuario=task.usuario,
                action='restore',
                notes=f'Error en restauración: {str(e)}'
            )
            
            return HttpResponseRedirect('/backup/?restore_error=1')
        
    except Backup.DoesNotExist:
        return HttpResponseRedirect('/backup/?error=Backup no encontrado')
    except Exception as e:
        print(f"Error en restore_backup: {str(e)}")
        return HttpResponseRedirect('/backup/?error=Error en restauración')

def download_backup(request, backup_id):
    try:
        backup = Backup.objects.get(id=backup_id)
        file_path = backup.ruta_storage
        
        if os.path.exists(file_path):
            with open(file_path, 'rb') as fh:
                response = HttpResponse(fh.read(), content_type="application/octet-stream")
                response['Content-Disposition'] = f'attachment; filename="{os.path.basename(file_path)}"'
                return response
        else:
            return JsonResponse({'error': 'Archivo no encontrado'}, status=404)
            
    except Backup.DoesNotExist:
        return JsonResponse({'error': 'Backup no encontrado'}, status=404)

def get_backup_task(request, task_id):
    try:
        task = BackupTask.objects.get(id=task_id)
        return JsonResponse({
            'id': task.id,
            'status': task.status,
            'result': task.result,
            'started_at': task.started_at.isoformat() if task.started_at else None,
            'finished_at': task.finished_at.isoformat() if task.finished_at else None
        })
    except BackupTask.DoesNotExist:
        return JsonResponse({'error': 'Tarea no encontrada'}, status=404)