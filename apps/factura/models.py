from django.db import models
from apps.persona.models import Personas
from apps.empresa.models import empresa
from apps.periodoContable.models import periodoContable
from apps.asientoContable.models import AsientoContable
from apps.home.models import Moneda, Tasa
from apps.cuentaBanco.models import CuentaBanco

class Factura(models.Model):
    idFactura = models.AutoField(primary_key=True)
    idPersona = models.ForeignKey(Personas, on_delete=models.CASCADE)
    idEmpresa = models.ForeignKey(empresa, on_delete=models.CASCADE)
    idPeriodo = models.ForeignKey(periodoContable, on_delete=models.CASCADE)
    idAsiento = models.ForeignKey(AsientoContable, on_delete=models.CASCADE)
    numeroFactura = models.CharField(max_length=50)
    codigoControl = models.CharField(max_length=50, blank=True, null=True)
    fechaEmision = models.DateField()
    fechaVencimiento = models.DateField(blank=True, null=True)
    formaPago = models.CharField(max_length=50)
    plazoCredito = models.IntegerField(blank=True, null=True)
    subtotalExento = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    subtotalGravado = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    iva = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    ivaRetenido = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    descuento = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    totalVenta = models.DecimalField(max_digits=10, decimal_places=2)
    idTasa = models.ForeignKey(Tasa, on_delete=models.CASCADE)
    estado = models.CharField(max_length=20, default='Pendiente')
    observaciones = models.TextField(blank=True, null=True)
    fechaCreacion = models.DateTimeField(auto_now_add=True)
    fechaActualizacion = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Factura {self.numeroFactura}"

class FacturaDetalle(models.Model):
    idDetalle = models.AutoField(primary_key=True)
    idFactura = models.ForeignKey(Factura, on_delete=models.CASCADE, related_name='detalles')
    tipoItem = models.CharField(max_length=50)
    idReferencia = models.IntegerField()  # Ajustar según el modelo relacionado
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
    idFactura = models.ForeignKey(Factura, on_delete=models.CASCADE, related_name='pagos')
    idAsiento = models.ForeignKey(AsientoContable, on_delete=models.CASCADE)
    idCuentaBanco = models.ForeignKey(CuentaBanco, on_delete=models.CASCADE)
    monto = models.DecimalField(max_digits=10, decimal_places=2)
    fechaPago = models.DateField()
    formaPago = models.CharField(max_length=50)
    referencia = models.CharField(max_length=100, blank=True, null=True)
    idMoneda = models.ForeignKey(Moneda, on_delete=models.CASCADE)
    tasaCambio = models.DecimalField(max_digits=10, decimal_places=4, default=1.0000)
    observaciones = models.TextField(blank=True, null=True)
    fechaRegistro = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Pago {self.idPago} de Factura {self.idFactura.numeroFactura}"