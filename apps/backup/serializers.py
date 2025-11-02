from rest_framework import serializers
from .models import Backup, BackupTask


class BackupSerializer(serializers.ModelSerializer):
    class Meta:
        model = Backup
        fields = ['id', 'name', 'fecha_creacion', 'usuario', 'tipo', 'checksum', 'ruta_storage', 'notas', 'tamaño']


class BackupTaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = BackupTask
        fields = ['id', 'backup', 'created_at', 'started_at', 'finished_at', 'status', 'result', 'task_id', 'usuario']
