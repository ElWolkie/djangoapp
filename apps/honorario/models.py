from django.db import models
from apps.persona.models import Personas
from apps.home.models import Cargo, Cohorte, Materia

class Honorario(models.Model):
    idHonorario = models.AutoField(primary_key=True)
    idPersona = models.ForeignKey(Personas, on_delete=models.CASCADE)
    idCargo = models.ForeignKey(Cargo, on_delete=models.CASCADE)
    idCohorte = models.ForeignKey(Cohorte, on_delete=models.CASCADE)
    idMateria = models.ForeignKey(Materia, on_delete=models.CASCADE)
    horas = models.PositiveIntegerField()
    monto = models.DecimalField(max_digits=15, decimal_places=2)
    estadoHonorario = models.CharField(max_length=10, db_index=True)
    fechaHonorario = models.DateField(auto_now_add=True)

    class Meta:
        verbose_name = "Honorario"
        verbose_name_plural = "Honorarios"
        constraints = [
            models.UniqueConstraint(
                fields=['idPersona', 'idMateria', 'idCohorte', 'fechaHonorario', 'monto', 'estadoHonorario'],
                name='unique_honorario_per_persona_materia_cohorte_fecha'
            )
        ]

    def __str__(self):
        return f"Honorario {self.idHonorario} - {self.idPersona}"