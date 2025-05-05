from django.db import models  
from django.contrib.auth.models import User  
from django.db import models
from apps.persona.models import Personas
from apps.home.models import Cargo, Cohorte, Materia
from django.core.exceptions import ValidationError

class Honorario(models.Model):  
    idHonorario = models.AutoField(primary_key=True)  # Clave primaria para Honorario  
    idPersona = models.ForeignKey(Personas, on_delete=models.CASCADE)  # Clave foránea a Personas  
    idCargo = models.ForeignKey(Cargo, on_delete=models.CASCADE)  # Clave foránea a Cargo  
    idCohorte = models.ForeignKey(Cohorte, on_delete=models.CASCADE)  # Clave foránea a Cohorte  
    idMateria = models.ForeignKey(Materia, on_delete=models.CASCADE)  # Clave foránea a Materia  
    horas = models.FloatField()  # Número de horas trabajadas  
    estadoHonorario = models.CharField(max_length=10)  # Estado del Honorario  
    fechaHonorario = models.DateField(auto_now_add=True)  # Fecha de creación del Honorario  

    class Meta:  
        verbose_name = "Honorario"  
        verbose_name_plural = "Honorarios"  

    def clean(self):
        # Evita duplicados: una persona no puede tener más de un honorario para la misma cohorte, cargo y materia
        qs = Honorario.objects.filter(
            idPersona=self.idPersona,
            idCohorte=self.idCohorte,
            idCargo=self.idCargo,
            idMateria=self.idMateria,
        )
        # Excluye el propio registro si es edición
        if self.pk:
            qs = qs.exclude(pk=self.pk)
        if qs.exists():
            raise ValidationError({'__all__': 'Este honorario ya está registrado para esta persona, cohorte, cargo y materia.'})

    def __str__(self):
        return f"Honorario {self.idHonorario} - {self.idPersona}"