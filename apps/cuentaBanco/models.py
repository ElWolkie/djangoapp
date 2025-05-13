from django.db import models
from apps.home.models import Banco, Moneda  # Importar las clases Banco y Moneda
from apps.planCuenta.models import PlanCuenta  # Importar la clase PlanCuenta
class cuentaBanco(models.Model):
    idCuentaBanco = models.AutoField(primary_key=True)  # Clave primaria autoincremental
    idBanco = models.ForeignKey(Banco, on_delete=models.CASCADE)  # Relación con Banco
    idPlanCuenta = models.ForeignKey(PlanCuenta, on_delete=models.CASCADE)  # Relación con PlanCuenta
    numeroCuentaBanco = models.CharField(max_length=20, unique=True)  # Número de cuenta
    tipoCuentaBanco = models.CharField(
        max_length=50,
        choices=[('ahorro', 'Ahorro'), ('corriente', 'Corriente')]
    )  # Tipo de cuenta (ej. Ahorro, Corriente)
    idMoneda = models.ForeignKey(Moneda, on_delete=models.CASCADE)  # Relación con Moneda
    fechaApertura = models.DateField()  # Fecha de apertura de la cuenta
    saldoDisponible = models.DecimalField(max_digits=15, decimal_places=2)  # Saldo disponible
    fechaRegistroCB = models.DateTimeField(auto_now_add=True)  # Fecha de registro
    fechaActualizadoCB = models.DateTimeField(auto_now=True)  # Fecha de última actualización
    estadoCB = models.BooleanField(default=True)  # Estado de la cuenta (activo/inactivo)

    def __str__(self):
        return f"{self.numeroCuentaBanco} - {self.idBanco.nombreBanco}"