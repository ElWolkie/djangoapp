from django import forms  
from .models import  Inscripcion
from django.core.exceptions import ValidationError


class InscripcionForm(forms.ModelForm):
    class Meta:
        model = Inscripcion
        fields = ['idInscripcion', 'idPersona', 'idCohorte', 'idTF', 'idFormacion']

    def clean(self):
        cleaned_data = super().clean()  # Siempre llamar al clean() padre primero
        idPersona = cleaned_data.get('idPersona')
        idCohorte = cleaned_data.get('idCohorte')
        idTF = cleaned_data.get('idTF')
        idFormacion = cleaned_data.get('idFormacion')

        if not all([idPersona, idCohorte, idTF, idFormacion]):
            return  # Si falta algún campo, no validar duplicados

        qs = Inscripcion.objects.filter(
            idPersona=idPersona,
            idCohorte=idCohorte,
            idTF=idTF,
            idFormacion=idFormacion,
        )

        if self.instance.pk:  # Si es una edición, excluir la instancia actual
            qs = qs.exclude(pk=self.instance.pk)

        if qs.exists():
            raise ValidationError('Esta combinación Persona/Cohorte/Formación ya existe')