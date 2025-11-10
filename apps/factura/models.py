from django.db import models
from django.forms import ValidationError
from apps.honorario.models import Honorario
from apps.inscripcion.models import Inscripcion, InscripcionCuota
from apps.persona.models import Personas
from apps.empresa.models import empresa
from apps.periodoContable.models import periodoContable
from apps.asientoContable.models import AsientoContable, DetalleAsiento
from apps.home.models import CuotaFormacion, Moneda, Tasa
from apps.cuentaBanco.models import CuentaBanco
from apps.solicitud.models import Solicitud
from django.utils.timezone import now
from apps.planCuenta.models import PlanCuenta
from django.db import transaction
import re



TIPOS_ARTICULO = [
        ('HONORARIO_PROFESOR', 'Pagos a Proveedores - Honorarios Profesionales'), # esto es un pago
        ('SERVICIO_GENERAL', 'Pagos a Proveedores - Servicios Generales (Internet, Luz, etc.)'), # esto es un pago
        ('COMPRA_BIENES', 'Pagos a Proveedores - Compra de Bienes/Materiales'), # esto es un pago
        ('INSCRIPCION', 'Ingresos de Estudiantes - Inscripción'), # esto es un cobro
        ('CUOTA', 'Ingresos de Estudiantes - Cuota'), # esto es un cobro
        ('SOLICITUD', 'Ingresos de Estudiantes - Solicitud de Trámites'), # esto es un cobro
    ]


class Nota(models.Model):
    TIPO_OPERACION = [
        ('COBRO', 'Nota de Cobro'),
        ('PAGO', 'Nota de Pago'),
    ]

    idNota = models.AutoField(primary_key=True)
    tipoOperacion = models.CharField(max_length=10, choices=TIPO_OPERACION, editable=False)  # Automático
    idAsiento = models.ForeignKey(
        AsientoContable, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        verbose_name="Asiento Contable"
    )
    idPersona = models.ForeignKey(Personas, on_delete=models.CASCADE, blank=True, null=True)
    idEmpresa = models.ForeignKey(empresa, on_delete=models.CASCADE, blank=True, null=True)
    tipoArticulo = models.CharField(max_length=50, choices=TIPOS_ARTICULO)
    numeroNota = models.CharField(max_length=50)  # Renombrado desde numeroFactura
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
    estado = models.CharField(max_length=20, default='PENDIENTE')
    observaciones = models.TextField(blank=True, null=True)
    fechaCreacion = models.DateTimeField(auto_now_add=True)
    fechaActualizacion = models.DateTimeField(auto_now=True)

    def clean(self):
        """
        Validación para asegurar que al menos uno de los dos campos (idPersona o idEmpresa) esté lleno.
        """
        if not self.idPersona and not self.idEmpresa:
            raise ValidationError("Debe especificar al menos un valor para 'idPersona' o 'idEmpresa'.")
    def save(self, *args, **kwargs):
            # Automáticamente definir si es COBRO o PAGO basado en tipoArticulo
            if self.tipoArticulo in ['INSCRIPCION', 'SOLICITUD', 'CUOTA']:
                self.tipoOperacion = 'COBRO'
            elif self.tipoArticulo in ['HONORARIO_PROFESOR', 'SERVICIO_GENERAL', 'COMPRA_BIENES']:
                self.tipoOperacion = 'PAGO'
            else:
                raise ValueError(f"El tipoArticulo '{self.tipoArticulo}' no es válido para determinar tipoOperacion.")
            super().save(*args, **kwargs)

    def __str__(self):
        return f"Nota {self.numeroNota} - {self.tipoOperacion}"
class NotaRelacionada(models.Model):
    idNota = models.ForeignKey(Nota, on_delete=models.CASCADE, related_name='relaciones')
    idInscripcion = models.ForeignKey(Inscripcion, on_delete=models.SET_NULL, null=True, blank=True, related_name='notas')
    idCuota = models.ForeignKey(InscripcionCuota, on_delete=models.SET_NULL, null=True, blank=True, related_name='notas')
    idHonorario = models.ForeignKey(Honorario, on_delete=models.SET_NULL, null=True, blank=True, related_name='notas')
    idSolicitud = models.ForeignKey(Solicitud, on_delete=models.SET_NULL, null=True, blank=True, related_name='notas')

    def clean(self):
        """
        Validación para asegurar que al menos una relación esté especificada.
        """
        if not (self.idInscripcion or self.idCuota or self.idHonorario or self.idSolicitud):
            raise ValidationError("Debe especificar al menos una relación: Inscripción, Cuota, Honorario o Solicitud.")

    def __str__(self):
        """
        Representación en cadena de la instancia, mostrando las relaciones asociadas.
        """
        relaciones = []
        if self.idInscripcion:
            relaciones.append(f"Inscripción {self.idInscripcion.idInscripcion}")
        if self.idCuota:
            relaciones.append(f"Cuota {self.idCuota.idCuota}")
        if self.idHonorario:
            relaciones.append(f"Honorario {self.idHonorario.idHonorario}")
        if self.idSolicitud:
            relaciones.append(f"Solicitud {self.idSolicitud.idSolicitud}")
        return f"Nota {self.idNota.idNota} relacionada con: {', '.join(relaciones)}"


class Factura(models.Model):
    numeroFactura = models.CharField(max_length=50, unique=True)  # Número único de factura
    fechaEmision = models.DateField(default=now)  # Fecha de emisión
    nota = models.OneToOneField(Nota, on_delete=models.CASCADE, related_name='factura')  # Relación con Nota
    estado = models.CharField(max_length=20, default='PENDIENTE')  # Estado de la factura

    class Meta:
        verbose_name = "Factura"
        verbose_name_plural = "Facturas"

    def __str__(self):
        return f"Factura {self.numeroFactura} - {self.estado}"

    @property
    def idPersona(self):
        """Obtiene el cliente desde la nota asociada."""
        return self.nota.idPersona

    @property
    def idEmpresa(self):
        """Obtiene la empresa desde la nota asociada."""
        return self.nota.idEmpresa

    @property
    def subtotalExento(self):
        """Obtiene el subtotal exento desde la nota asociada."""
        return self.nota.subtotalExento

    @property
    def subtotalGravado(self):
        """Obtiene el subtotal gravado desde la nota asociada."""
        return self.nota.subtotalGravado

    @property
    def iva(self):
        """Obtiene el IVA desde la nota asociada."""
        return self.nota.iva

    @property
    def ivaRetenido(self):
        """Obtiene la retención de IVA desde la nota asociada."""
        return self.nota.ivaRetenido

    @property
    def islrRetenido(self):
        """Obtiene la retención de ISLR desde la nota asociada."""
        return self.nota.islrRetenido

    @property
    def descuento(self):
        """Obtiene el descuento desde la nota asociada."""
        return self.nota.descuento

    @property
    def totalVenta(self):
        """Calcula el total de la factura basado en la nota asociada."""
        return self.nota.totalNota
    
class FacturaDetalle(models.Model):
    idDetalle = models.AutoField(primary_key=True)
    idFactura = models.ForeignKey(Factura, on_delete=models.CASCADE, related_name='detalles')
    idNota = models.ForeignKey(Nota, on_delete=models.CASCADE, related_name='detalles_factura')  # Relación directa con la nota
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
        return f"Detalle {self.idDetalle} de Factura {self.idFactura.numeroFactura} relacionado con Nota {self.idNota.numeroNota}"

class Pago(models.Model):
    idPago = models.AutoField(primary_key=True)
    idNota = models.ForeignKey(Nota, on_delete=models.CASCADE, related_name='pagos')
    idAsiento = models.ForeignKey(AsientoContable, on_delete=models.CASCADE)
    idCuentaBanco = models.ForeignKey(CuentaBanco, on_delete=models.CASCADE, null=True, blank=True)
    monto = models.DecimalField(max_digits=60, decimal_places=4)
    fechaPago = models.DateField()
    formaPago = models.CharField(max_length=50)
    referencia = models.CharField(max_length=100, blank=True, null=True)
    idTasa = models.ForeignKey(Tasa, on_delete=models.CASCADE)
    observaciones = models.TextField(blank=True, null=True)
    fechaRegistro = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Pago {self.idPago} de Factura {self.idFactura.numeroFactura}"
    

class PagoTemporal(models.Model):
    idPagoTemporal = models.AutoField(primary_key=True)
    idNota = models.ForeignKey(Nota, on_delete=models.CASCADE, related_name='pagos_temporales')
    idCuentaBanco = models.ForeignKey(CuentaBanco, on_delete=models.CASCADE, null=True, blank=True)
    monto = models.DecimalField(max_digits=60, decimal_places=4)
    referencia = models.CharField(max_length=100, blank=True, null=True)
    idTasa = models.ForeignKey(Tasa, on_delete=models.CASCADE)
    observaciones = models.TextField(blank=True, null=True)
    fechaPago = models.DateTimeField(auto_now_add=True)
    confirmado = models.BooleanField(default=False, help_text="Indica si el pago ha sido confirmado")

    @transaction.atomic
    def confirmar_pago(self):
        """
        Confirma el pago temporal, lo mueve a la tabla principal `Pago` y realiza los registros dependientes.
        """
        # Validar si el pago ya fue confirmado
        if self.confirmado:
            raise ValueError("El pago ya ha sido confirmado.")

        # Validar que el monto sea positivo
        if self.monto <= 0:
            raise ValueError("El monto del pago debe ser mayor a cero.")

        # Validar que la nota asociada exista
        if not self.idNota:
            raise ValueError("Debe asociar una nota válida al pago.")

        # Validar que la cuenta bancaria exista y tenga un plan de cuenta asociado
        if not self.idCuentaBanco:
            raise ValueError("Debe seleccionar una cuenta bancaria válida.")

        # Debugging: Verificar el tipo y atributos de idCuentaBanco
        print(f"idCuentaBanco: {self.idCuentaBanco}")
        print(f"idCuentaBanco type: {type(self.idCuentaBanco)}")
        print(f"idCuentaBanco attributes: {dir(self.idCuentaBanco)}")

        if not self.idCuentaBanco.planCuenta:
            raise ValueError("La cuenta bancaria seleccionada no tiene un plan de cuenta asociado.")

        # Verificar si hay un periodo contable activo
        periodo_activo = periodoContable.objects.filter(estadoPeriodo=True).first()
        if not periodo_activo:
            raise ValueError("No hay ningún periodo contable registrado o activo en el sistema.")

        # Evitar duplicados en el nombre del asiento contable
        base_numero_asiento = f"PAGO-{self.idNota.numeroNota}"
        asientos_similares = AsientoContable.objects.filter(
            numeroAsiento__startswith=base_numero_asiento
        ).values_list('numeroAsiento', flat=True)

        # Determinar número de asiento único
        if base_numero_asiento not in asientos_similares:
            numero_asiento_pago = base_numero_asiento
        else:
            sufijos = []
            patron = re.compile(rf"^{re.escape(base_numero_asiento)}-(\d+)$")
            for n in asientos_similares:
                match = patron.match(n)
                if match:
                    sufijos.append(int(match.group(1)))
            nuevo_sufijo = max(sufijos) + 1 if sufijos else 1
            numero_asiento_pago = f"{base_numero_asiento}-{nuevo_sufijo}"

        # Crear el asiento contable para el pago
        asiento_pago = AsientoContable.objects.create(
            numeroAsiento=numero_asiento_pago,
            fechaAsiento=self.fechaPago,
            conceptoAsiento=f"Pago de {self.idNota.numeroNota}",
            idPeriodo=periodo_activo
        )

        # Obtener la cuenta del Plan de Cuenta usada en el Debe del asiento principal de la nota
        asiento_principal = self.idNota.idAsiento
        detalle_debe = DetalleAsiento.objects.filter(idAsiento=asiento_principal, debe__gt=0).first()
        if not detalle_debe:
            raise ValueError("No se encontró la cuenta por cobrar en el asiento principal de la nota.")
        plan_cuenta_haber = detalle_debe.idPlanCuenta

        # Obtener el plan de cuenta para el Debe (Caja/Banco) según la cuenta bancaria
        plan_cuenta_debe = self.idCuentaBanco.planCuenta

        # Crear los detalles del asiento contable
        DetalleAsiento.objects.create(
            idAsiento=asiento_pago,
            idMoneda= '1',  # Asumiendo moneda local con ID 1
            idPlanCuenta=plan_cuenta_debe,
            debe=float(self.monto),
            haber=0.00
        )
        DetalleAsiento.objects.create(
            idAsiento=asiento_pago,
            idMoneda= '1',  # Asumiendo moneda local con ID 1
            idPlanCuenta=plan_cuenta_haber,
            debe=0.00,
            haber=float(self.monto)
        )

        # Crear el registro en la tabla principal `Pago`
        pago = Pago.objects.create(
            idNota=self.idNota,
            idAsiento=asiento_pago,  # Asignar el asiento contable creado
            idCuentaBanco=self.idCuentaBanco,
            monto=self.monto,
            fechaPago=self.fechaPago,
            formaPago="TRANSFERENCIA",  # Siempre será transferencia
            referencia=self.referencia,
            idTasa=self.idTasa,
            observaciones=self.observaciones
        )

        # Actualizar el estado de la nota
        self.idNota.estado = 'PAGADO'
        self.idNota.save()

        # Marcar el pago temporal como confirmado
        self.confirmado = True
        self.save()

        return pago

    def __str__(self):
        return f"Pago Temporal {self.idPagoTemporal} - {'Confirmado' if self.confirmado else 'Pendiente'}"
      
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
    

class PlanArticulo(models.Model):
        
    """
    Modelo para definir los planes a los que aplica un artículo.
    """
    idPlanArti = models.AutoField(primary_key=True)
    tipoArticulo = models.CharField(max_length=50, choices=TIPOS_ARTICULO)
    idPlanCuenta = models.ForeignKey(PlanCuenta, on_delete=models.CASCADE, verbose_name="Plan de Cuenta")
    tipo = models.BooleanField(default=False)
    fecha = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de inicio")

    def __str__(self):
        return f"Plan {self.idPlan} - {self.get_articulo_display()}"
