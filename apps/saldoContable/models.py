# apps/saldoContable/models.py
from django.db import models
from apps.planCuenta.models import PlanCuenta
from apps.periodoContable.models import periodoContable

class SaldoContable(models.Model):
    idSaldo = models.AutoField(primary_key=True, verbose_name="ID Saldo")
    id_plan_cuenta = models.ForeignKey(
        PlanCuenta,
        on_delete=models.PROTECT,
        verbose_name="Plan de Cuenta",
        related_name="saldos_contables"
    )
    
    id_periodo = models.ForeignKey(
        periodoContable,
        on_delete=models.PROTECT,
        verbose_name="Periodo Contable",
        related_name="saldos_periodo"
    )
    
    saldo_inicial = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0.00,
        verbose_name="Saldo Inicial"
    )
    
    saldo_final = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0.00,
        verbose_name="Saldo Final"
    )

    class Meta:
        verbose_name = "Saldo Contable"
        verbose_name_plural = "Saldos Contables"
        unique_together = ('id_plan_cuenta', 'id_periodo')  # Evita duplicados
        indexes = [
            models.Index(fields=['id_plan_cuenta', 'id_periodo']),
        ]

    def __str__(self):
        return f"{self.id_plan_cuenta} | {self.id_periodo} | Final: {self.saldo_final}"