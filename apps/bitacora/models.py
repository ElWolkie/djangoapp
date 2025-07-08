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

class ConfiguracionBitacora(models.Model):
    OPCIONES_RETENCION = [
        ('diario', 'Diario (1 día)'),
        ('semanal', 'Semanal (7 días)'),
        ('mensual', 'Mensual (30 días)'),
        ('anual', 'Anual (365 días)'),
        ('personalizado', 'Personalizado'),
    ]
    
    retencion = models.CharField(
        max_length=20,
        choices=OPCIONES_RETENCION,
        default='anual',
        help_text="Período de retención para los registros de la bitácora"
    )
    
    dias_personalizados = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Días de retención para la opción personalizada"
    )
    
    exportar_antes_limpieza = models.BooleanField(
        default=True,
        help_text="Exportar registros antes de eliminarlos"
    )
    
    directorio_exportacion = models.CharField(
        max_length=255,
        default='backups/bitacora/',
        help_text="Directorio donde se guardarán los archivos exportados"
    )
    
    ultima_limpieza = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Fecha y hora de la última limpieza automática"
    )
    
    def __str__(self):
        return f"Configuración Bitácora ({self.get_retencion_display()})"
    
    def get_dias_retencion(self):
        if self.retencion == 'diario':
            return 1
        elif self.retencion == 'semanal':
            return 7
        elif self.retencion == 'mensual':
            return 30
        elif self.retencion == 'anual':
            return 365
        elif self.retencion == 'personalizado' and self.dias_personalizados:
            return self.dias_personalizados
        return 365  # Valor por defecto
    
    class Meta:
        verbose_name = "Configuración de Bitácora"
        verbose_name_plural = "Configuración de Bitácora"