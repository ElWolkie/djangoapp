from django.db import models  
from django.contrib.auth.models import User  
from django.db import models
from apps.persona.models import Personas
from apps.home.models import Cargo, Cohorte, Materia

class Honorario(models.Model):  
    idHonorario = models.AutoField(primary_key=True)  # Clave primaria para Honorario  
    idPersona = models.ForeignKey(Personas, on_delete=models.CASCADE)  # Clave foránea a Personas  
    idCargo = models.ForeignKey(Cargo, on_delete=models.CASCADE)  # Clave foránea a Cargo  
    idCohorte = models.ForeignKey(Cohorte, on_delete=models.CASCADE)  # Clave foránea a Cohorte  
    idMateria = models.ForeignKey(Materia, on_delete=models.CASCADE)  # Clave foránea a Materia  
    horas = models.FloatField()  # Número de horas trabajadas  
    estadoHonorario = models.CharField(max_length=10, db_index=True)  # Estado del Honorario  
    fechaHonorario = models.DateField(auto_now_add=True)  # Fecha de creación del Honorario  

    class Meta:  
        verbose_name = "Honorario"  
        verbose_name_plural = "Honorarios"  
    
    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['idPersona', 'idMateria', 'idCohorte', 'horas'],
                name='unique_honorario_per_persona_materia_cohorte_horas'
            )
        ]

