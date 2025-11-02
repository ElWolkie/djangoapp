from django.contrib import admin
from .models import Backup, BackupTask, BackupAudit


@admin.register(Backup)
class BackupAdmin(admin.ModelAdmin):
    list_display = ('name', 'fecha_creacion', 'usuario', 'tipo', 'tamaño')
    search_fields = ('name', 'usuario', 'checksum')
    list_filter = ('tipo',)


@admin.register(BackupTask)
class BackupTaskAdmin(admin.ModelAdmin):
    list_display = ('id', 'backup', 'status', 'created_at', 'started_at', 'finished_at')
    search_fields = ('task_id', 'backup__name')


@admin.register(BackupAudit)
class BackupAuditAdmin(admin.ModelAdmin):
    list_display = ('backup', 'action', 'usuario', 'timestamp')
    search_fields = ('usuario', 'action')
