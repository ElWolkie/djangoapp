from django.db import models

# Create your models here.
from django.db import models
from apps.planCuenta.models import PlanCuenta
from apps.periodoContable.models import periodoContable  # Asegúrate de que el modelo Periodo esté en esta app

class AsientoContable(models.Model):
    """
    Modelo que representa un asiento contable.
    """
    idAsiento = models.AutoField(primary_key=True, verbose_name="ID Asiento")
    numeroAsiento = models.CharField(max_length=50, unique=True, verbose_name="Número de Asiento")
    fechaAsiento = models.DateField(verbose_name="Fecha del Asiento")
    conceptoAsiento = models.TextField(verbose_name="Concepto del Asiento")
    idPeriodo = models.ForeignKey(periodoContable, on_delete=models.CASCADE, verbose_name="Periodo Contable")
    fechaAsientoDigital = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de Creación Digital")

    class Meta:
        verbose_name = "Asiento Contable"
        verbose_name_plural = "Asientos Contables"
        ordering = ['fechaAsiento', 'numeroAsiento']

    def __str__(self):
        return f"Asiento {self.numeroAsiento} - {self.conceptoAsiento}"


class DetalleAsiento(models.Model):
    """
    Modelo que representa el detalle de un asiento contable.
    """
    idDetalle = models.AutoField(primary_key=True, verbose_name="ID Detalle")
    idAsiento = models.ForeignKey(AsientoContable, on_delete=models.CASCADE, related_name="detalles", verbose_name="Asiento Contable")
    idPlanCuenta = models.ForeignKey(PlanCuenta, on_delete=models.CASCADE, verbose_name="Plan de Cuenta")
    debe = models.DecimalField(max_digits=15, decimal_places=2, default=0.00, verbose_name="Debe")
    haber = models.DecimalField(max_digits=15, decimal_places=2, default=0.00, verbose_name="Haber")
    estadoDetalle = models.BooleanField(default=True, verbose_name="Estado Activo")
    fechaDetalle = models.DateField(auto_now_add=True, verbose_name="Fecha del Detalle")

    class Meta:
        verbose_name = "Detalle de Asiento"
        verbose_name_plural = "Detalles de Asiento"
        ordering = ['idAsiento', 'idDetalle']

    def __str__(self):
        return f"Detalle {self.idDetalle} - Asiento {self.idAsiento.numeroAsiento}"


