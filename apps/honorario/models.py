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
    horas = models.PositiveIntegerField()  # Número de horas trabajadas (debe ser un número entero positivo)
    monto = models.DecimalField(max_digits=15, decimal_places=2)  # Monto del Honorario  
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

   
    def clean(self):
        # Evitar duplicados exactos
        qs = Honorario.objects.filter(
            idPersona=self.idPersona,
            idCargo=self.idCargo,
            idCohorte=self.idCohorte,
            idMateria=self.idMateria,
            horas=self.horas,
            monto=self.monto,
            estadoHonorario=self.estadoHonorario
        )
        # Excluir el propio registro si es una edición
        if self.pk:
            qs = qs.exclude(pk=self.pk)
        if qs.exists():
            raise ValidationError({'__all__': 'Ya existe un registro exactamente igual.'})

    def __str__(self):
        return f"Honorario {self.idHonorario} - {self.idPersona}"