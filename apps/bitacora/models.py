from django.db import models
from django.utils import timezone
from apps.home.models import Usuarios  # Modelo  de usuarios

class Bitacora(models.Model):
    # Acciones posibles
    ACCIONES = (
        ('C', 'Creación'),
        ('A', 'Actualización'),
        ('E', 'Eliminación'),
        ('I', 'Inicio de sesión'),
        ('O', 'Cierre de sesión'),
        ('B', 'Copia de seguridad'),
        ('R', 'Restauración'),
    )
    
    # Estados posibles
    ESTADOS = (
        ('S', 'Éxito'),
        ('F', 'Fallido'),
    )

    SEVERIDAD_CHOICES = (
        ('DEBUG', 'Depuración'),
        ('INFO', 'Informativo'),
        ('WARNING', 'Advertencia'),
        ('ERROR', 'Error'),
        ('CRITICAL', 'Crítico'),
    )
    severidad = models.CharField(
        max_length=10, 
        choices=SEVERIDAD_CHOICES, 
        default='INFO',
        verbose_name="Nivel de Severidad"
    )
    
    accion = models.CharField(
        max_length=1, 
        choices=ACCIONES,
        verbose_name="Tipo de acción"
    )
    
    # Relación con modelo Usuarios
    usuario = models.ForeignKey(
        Usuarios,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Usuario involucrado",
        related_name='bitacoras'  # Opcional: para acceder desde Usuarios
    )
    
    fecha_hora = models.DateTimeField(
        default=timezone.now,
        verbose_name="Fecha y hora del evento"
    )
    
    modelo_afectado = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name="Tabla/modulo afectado"
    )
    
    objeto_id = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        verbose_name="ID del registro afectado"
    )

    cambios = models.JSONField(
        null=True, 
        blank=True, 
        verbose_name="Detalles de cambios"
    )
    
    descripcion = models.TextField(
        verbose_name="Detalles de la acción"
    )
    
    ip = models.GenericIPAddressField(
        blank=True,
        null=True,
        verbose_name="Dirección IP"
    )
    
    estado = models.CharField(
        max_length=1, 
        choices=ESTADOS,
        default='S',
        verbose_name="Resultado de la acción"
    )

    def __str__(self):
        return f"{self.get_accion_display()} - {self.fecha_hora}"

    class Meta:
        verbose_name = "Registro de Bitácora"
        verbose_name_plural = "Registros de Bitácora"
        ordering = ['-fecha_hora']