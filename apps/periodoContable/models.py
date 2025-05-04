from django.db import models

class periodoContable(models.Model):
    idPeriodo = models.AutoField(primary_key=True)  # Clave primaria autoincremental
    nombrePeriodo = models.CharField(max_length=255)  # Nombre del periodo contable
    fechaInicioPeriodo = models.DateField()  # Fecha de inicio del periodo
    fechaFinPeriodo = models.DateField()  # Fecha de fin del periodo
    estadoPeriodo = models.BooleanField(default=True)  # Estado del periodo (activo/inactivo)
    fechaPeriodoDigital = models.DateTimeField(auto_now_add=True)  # Fecha de creación del registro

    def __str__(self):
        return self.nombrePeriodo