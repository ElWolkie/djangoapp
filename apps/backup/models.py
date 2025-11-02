from django.db import models
from django.conf import settings
from django.utils import timezone
from datetime import datetime, timedelta


class Backup(models.Model):
    TYPE_CHOICES = [
        ("full", "Full"),
        ("data-only", "Data only"),
        ("wal", "WAL"),
    ]

    name = models.CharField(max_length=255)
    fecha_creacion = models.DateTimeField(default=timezone.now, db_index=True)
    usuario = models.CharField(max_length=150, blank=True, null=True)
    tipo = models.CharField(max_length=20, choices=TYPE_CHOICES, db_index=True)
    checksum = models.CharField(max_length=128, blank=True, null=True)
    ruta_storage = models.TextField()
    notas = models.TextField(blank=True, null=True)
    tamaño = models.BigIntegerField(default=0)

    class Meta:
        ordering = ["-fecha_creacion"]

    def __str__(self):
        return f"{self.name} ({self.fecha_creacion:%Y-%m-%d %H:%M:%S})"
    
    expiracion = models.DateTimeField(null=True, blank=True)
    
    def save(self, *args, **kwargs):
        if not self.expiracion:
            # Por defecto, los backups expiran en 30 días
            self.expiracion = timezone.now() + timedelta(days=30)
        super().save(*args, **kwargs)
    
    @property
    def esta_expirado(self):
        return self.expiracion and timezone.now() > self.expiracion


class BackupTask(models.Model):
    STATUS = [("pending", "Pending"), ("running", "Running"), ("success", "Success"), ("error", "Error")]
    backup = models.ForeignKey(Backup, on_delete=models.CASCADE, related_name="tasks")
    created_at = models.DateTimeField(default=timezone.now)
    started_at = models.DateTimeField(blank=True, null=True)
    finished_at = models.DateTimeField(blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS, default="pending")
    result = models.TextField(blank=True, null=True)
    task_id = models.CharField(max_length=64, blank=True, null=True)
    usuario = models.CharField(max_length=150, blank=True, null=True)

    def __str__(self):
        return f"Task {self.id} - {self.backup.name} - {self.status}"


class BackupAudit(models.Model):
    ACTIONS = [("create", "Create"), ("delete", "Delete"), ("restore", "Restore")]
    backup = models.ForeignKey(Backup, on_delete=models.CASCADE, related_name="audits")
    usuario = models.CharField(max_length=150, blank=True, null=True)
    action = models.CharField(max_length=20, choices=ACTIONS)
    timestamp = models.DateTimeField(default=timezone.now)
    notes = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ["-timestamp"]

    def __str__(self):
        return f"{self.action} by {self.usuario} on {self.timestamp}"
