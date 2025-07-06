from django.db import models
from django.forms import ValidationError
from apps.honorario.models import Honorario
from apps.inscripcion.models import Inscripcion
from apps.persona.models import Personas
from apps.empresa.models import empresa
from apps.periodoContable.models import periodoContable
from apps.asientoContable.models import AsientoContable
from apps.home.models import Moneda, Tasa
from apps.cuentaBanco.models import CuentaBanco
from apps.solicitud.models import Solicitud

class Nota(models.Model):
    TIPOS_NOTA = [
        ('COBRO', 'Nota de Cobro'),
        ('PAGO', 'Nota de Pago'),
    ]

    TIPOS_FACTURA = [
        ('HONORARIO_PROFESOR', 'Pagos a Proveedores - Honorarios Profesionales'), # esto es un pago
        ('SERVICIO_GENERAL', 'Pagos a Proveedores - Servicios Generales (Internet, Luz, etc.)'), # esto es un pago
        ('COMPRA_BIENES', 'Pagos a Proveedores - Compra de Bienes/Materiales'), # esto es un pago
        ('INSCRIPCION', 'Ingresos de Estudiantes - Inscripción'), # esto es un cobro
        ('SOLICITUD', 'Ingresos de Estudiantes - Solicitud de Trámites'), # esto es un cobro
    ]

    idNota = models.AutoField(primary_key=True)
    tipoNota = models.CharField(max_length=10, choices=TIPOS_NOTA, editable=False)  # Automático
    idAsiento = models.ForeignKey(
        AsientoContable, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        verbose_name="Asiento Contable"
    )
    idPersona = models.ForeignKey(Personas, on_delete=models.CASCADE, blank=True, null=True)
    idEmpresa = models.ForeignKey(empresa, on_delete=models.CASCADE, blank=True, null=True)
    tipoFactura = models.CharField(max_length=50, choices=TIPOS_FACTURA)
    numeroNota = models.CharField(max_length=50)  # Renombrado desde numeroFactura
    codigoControl = models.CharField(max_length=50, blank=True, null=True)
    fechaEmision = models.DateField()
    fechaVencimiento = models.DateField(blank=True, null=True)
    formaPago = models.CharField(max_length=50)
    plazoCredito = models.IntegerField(blank=True, null=True)
    subtotalExento = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    subtotalGravado = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    iva = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    ivaRetenido = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    islrRetenido = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    descuento = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    totalNota = models.DecimalField(max_digits=10, decimal_places=2)  # Renombrado desde totalVenta
    idTasa = models.ForeignKey(Tasa, on_delete=models.CASCADE)
    estado = models.CharField(max_length=20, default='Pendiente')
    observaciones = models.TextField(blank=True, null=True)
    fechaCreacion = models.DateTimeField(auto_now_add=True)
    fechaActualizacion = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        # Automáticamente definir si es COBRO o PAGO basado en tipoFactura
        if self.tipoFactura in ['INSCRIPCION', 'SOLICITUD']:
            self.tipoNota = 'COBRO'
        elif self.tipoFactura in ['HONORARIO_PROFESOR', 'SERVICIO_GENERAL', 'COMPRA_BIENES']:
            self.tipoNota = 'PAGO'
        else:
            raise ValueError(f"El tipoFactura '{self.tipoFactura}' no es válido para determinar tipoNota.")
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Nota {self.numeroNota} - {self.tipoNota}"

class NotaRelacionada(models.Model):
    idNota = models.ForeignKey(Nota, on_delete=models.CASCADE, related_name='relaciones')
    idInscripcion = models.ForeignKey(Inscripcion, on_delete=models.SET_NULL, null=True, blank=True, related_name='notas')
    idHonorario = models.ForeignKey(Honorario, on_delete=models.SET_NULL, null=True, blank=True, related_name='notas')
    idSolicitud = models.ForeignKey(Solicitud, on_delete=models.SET_NULL, null=True, blank=True, related_name='notas')

    def clean(self):
        if not (self.idInscripcion or self.idHonorario or self.idSolicitud):
            raise ValidationError("Debe especificar al menos una relación: Inscripción, Honorario o Solicitud.")

    def __str__(self):
        relaciones = []
        if self.idInscripcion:
            relaciones.append(f"Inscripción {self.idInscripcion.idInscripcion}")
        if self.idHonorario:
            relaciones.append(f"Honorario {self.idHonorario.idHonorario}")
        if self.idSolicitud:
            relaciones.append(f"Solicitud {self.idSolicitud.idSoli}")
        return f"Nota {self.idNota.idNota} relacionada con: {', '.join(relaciones)}"


class Factura(models.Model):
    TIPOS_FACTURA = [
        ('HONORARIO_PROFESOR', 'Pagos a Proveedores - Honorarios Profesionales'),
        ('SERVICIO_GENERAL', 'Pagos a Proveedores - Servicios Generales (Internet, Luz, etc.)'),
        ('COMPRA_BIENES', 'Pagos a Proveedores - Compra de Bienes/Materiales'),
        ('INSCRIPCION', 'Ingresos de Estudiantes - Inscripción'),
        ('SOLICITUD', 'Ingresos de Estudiantes - Solicitud de Trámites'),
    ]

    idFactura = models.AutoField(primary_key=True)
    numeroFactura = models.CharField(max_length=50, unique=True)  # Número único de factura
    tipoFactura = models.CharField(max_length=50, choices=TIPOS_FACTURA)  # Tipo de factura
    idPersona = models.ForeignKey(Personas, on_delete=models.CASCADE, blank=True, null=True)  # Cliente o profesor
    idEmpresa = models.ForeignKey(empresa, on_delete=models.CASCADE, blank=True, null=True)  # Fundación emisora
    fechaEmision = models.DateField(auto_now_add=True)  # Fecha de emisión de la factura
    notas = models.ManyToManyField('Nota', related_name='facturas')  # Relación con las notas asociadas
    subtotalExento = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)  # Suma de subtotales exentos de las notas
    subtotalGravado = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)  # Suma de subtotales gravados de las notas
    iva = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)  # Suma de IVA de las notas
    ivaRetenido = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)  # Suma de IVA retenido de las notas
    islrRetenido = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)  # Suma de ISLR retenido de las notas
    descuento = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)  # Suma de descuentos de las notas
    totalVenta = models.DecimalField(max_digits=10, decimal_places=2)  # Total consolidado de las notas
    estado = models.CharField(max_length=20, default='Generada')  # Estado de la factura (e.g., Generada, Cancelada)
    observaciones = models.TextField(blank=True, null=True)  # Observaciones adicionales
    fechaCreacion = models.DateTimeField(auto_now_add=True)  # Fecha de creación
    fechaActualizacion = models.DateTimeField(auto_now=True)  # Fecha de última actualización

    def __str__(self):
        return f"Factura {self.numeroFactura} - {self.tipoFactura}"
    
class FacturaDetalle(models.Model):
    idDetalle = models.AutoField(primary_key=True)
    idFactura = models.ForeignKey(Factura, on_delete=models.CASCADE, related_name='detalles')
    tipoItem = models.CharField(max_length=90)  # Bien o servicio
    descripcion = models.TextField()
    cantidad = models.DecimalField(max_digits=10, decimal_places=2)
    precioUnitario = models.DecimalField(max_digits=10, decimal_places=2)
    exento = models.BooleanField(default=False)
    descuentoItem = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)
    ivaItem = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    totalItem = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"Detalle {self.idDetalle} de Factura {self.idFactura.numeroFactura}"

class Pago(models.Model):
    idPago = models.AutoField(primary_key=True)
    idNota = models.ForeignKey(Nota, on_delete=models.CASCADE, related_name='pagos')
    idAsiento = models.ForeignKey(AsientoContable, on_delete=models.CASCADE)
    idCuentaBanco = models.ForeignKey(CuentaBanco, on_delete=models.CASCADE)
    monto = models.DecimalField(max_digits=10, decimal_places=2)
    fechaPago = models.DateField()
    formaPago = models.CharField(max_length=50)
    referencia = models.CharField(max_length=100, blank=True, null=True)
    idTasa = models.ForeignKey(Tasa, on_delete=models.CASCADE)
    observaciones = models.TextField(blank=True, null=True)
    fechaRegistro = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Pago {self.idPago} de Factura {self.idFactura.numeroFactura}"
    
class ParametroTributario(models.Model):
    # Opciones para tipos de factura (consistentes con tu formulario)
    TIPOS_APLICABLES = [
        ('HONORARIO_PROFESOR', 'Honorarios Profesionales'),
        ('SERVICIO_GENERAL', 'Servicios Generales'),
        ('COMPRA_BIENES', 'Compra de Bienes'),
        ('INSCRIPCION', 'Inscripción'),
        ('SOLICITUD', 'Solicitud de Trámites'),
    ]
    
    # Opciones de parámetros tributarios (ampliadas)
    TIPO_PARAMETRO = [
        # IVA
        ('IVA_GENERAL', 'IVA General'),
        ('IVA_EXENTO', 'IVA Exento'),
        
        # Retenciones IVA
        ('IVA_RETENIDO_SERVICIOS', 'Retención IVA para servicios'),
        ('IVA_RETENIDO_COMPRAS', 'Retención IVA para compras'),
        
        # Retenciones ISLR
        ('ISLR_HONORARIOS', 'Retención ISLR honorarios'),
        ('ISLR_SERVICIOS', 'Retención ISLR servicios generales'),
        ('ISLR_COMPRAS', 'Retención ISLR compras'),
        
        # Exenciones
        ('MONTO_EXENCION_ISLR', 'Monto mínimo para retención ISLR'),
        ('MONTO_EXENCION_IVA', 'Monto mínimo para aplicación de IVA'),
        
        # Otros
        ('TASA_MUNICIPAL', 'Tasa municipal'),
    ]
    
    idPT = models.AutoField(primary_key=True)
    tipo = models.CharField(max_length=30, choices=TIPO_PARAMETRO)
    aplica_a = models.CharField(
        max_length=20, 
        choices=TIPOS_APLICABLES,
        verbose_name="Aplica a",
        help_text="Tipo de factura al que aplica este parámetro"
    )
    porcentaje = models.DecimalField(
        max_digits=5, 
        decimal_places=2,
        help_text="Porcentaje a aplicar (0 para exenciones)"
    )
    valor_fijo = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Valor fijo (si aplica, en lugar de porcentaje)"
    )
    fecha_inicio = models.DateField(verbose_name="Fecha de inicio de vigencia")
    fecha_fin = models.DateField(
        null=True, 
        blank=True,
        verbose_name="Fecha de fin de vigencia"
    )
    activo = models.BooleanField(default=True)
    descripcion = models.TextField(blank=True)
    
    class Meta:
        verbose_name = "Parámetro Tributario"
        verbose_name_plural = "Parámetros Tributarios"
        ordering = ['tipo', 'aplica_a', '-fecha_inicio']
        unique_together = ['tipo', 'aplica_a', 'fecha_inicio']
    
    def __str__(self):
        return f"{self.get_tipo_display()} ({self.get_aplica_a_display()}) - {self.porcentaje}%"