from django.db import models
from django.core.exceptions import ValidationError
from apps.persona.models import Personas
from apps.home.models import Cohorte, TipoFormacion, Formacion

class Inscripcion(models.Model):
    idInscripcion = models.AutoField(primary_key=True)  # Clave primaria para Inscripcion
    idPersona = models.ForeignKey(Personas, on_delete=models.CASCADE)  # Relación con Personas
    idCohorte = models.ForeignKey(Cohorte, on_delete=models.CASCADE)  # Relación con Cohorte
    idTF = models.ForeignKey(TipoFormacion, on_delete=models.CASCADE)  # Relación con TipoFormacion
    idFormacion = models.ForeignKey(Formacion, on_delete=models.CASCADE)  # Relación con Formacion
    is_active = models.BooleanField(default=True)  # Estado de la Inscripcion
    fechaInscripcion = models.DateField(auto_now_add=True)  # Fecha de inscripción

    class Meta:
        verbose_name = "Inscripción"
        verbose_name_plural = "Inscripciones"

    def clean(self):
        # Evita duplicados: una persona no puede inscribirse dos veces en la misma cohorte, formación y tipo de formación
        qs = Inscripcion.objects.filter(
            idPersona=self.idPersona,
            idCohorte=self.idCohorte,
            idTF=self.idTF,
            idFormacion=self.idFormacion,
        )
        # Excluye el propio registro si es edición
        if self.pk:
            qs = qs.exclude(pk=self.pk)
        if qs.exists():
            raise ValidationError({'__all__': 'Esta inscripción ya está registrada.'})        

    def __str__(self):
        return f"Inscripción {self.idInscripcion} - {self.idPersona}"