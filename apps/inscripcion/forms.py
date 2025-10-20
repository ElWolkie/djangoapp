from django import forms  
from .models import Inscripcion, CuotaFormacion
from django.core.exceptions import ValidationError


class InscripcionForm(forms.ModelForm):
    class Meta:
        model = Inscripcion
        fields = ['idInscripcion', 'idPersona', 'idCohorte']

    def clean(self):
        cleaned_data = super().clean()  # Siempre llamar al clean() padre primero
        idPersona = cleaned_data.get('idPersona')
        idCohorte = cleaned_data.get('idCohorte')

        if not all([idPersona, idCohorte]):
            return cleaned_data  # Si falta algún campo, no validar duplicados

        # Corregir acceso a idFormacion a través de idCohorte
        idFormacion = idCohorte.idFormacion if idCohorte else None

        qs = Inscripcion.objects.filter(
            idPersona=idPersona,
            idCohorte=idCohorte
        )

        if self.instance.pk:  # Si es una edición, excluir la instancia actual
            qs = qs.exclude(pk=self.instance.pk)

        if qs.exists():
            raise ValidationError('Esta combinación Persona/Cohorte/Formación ya existe')

        # Validar que la formación tenga cuotas activas si se requiere
        if idFormacion and idFormacion.tieneCuotas:
            cuotas_activas = CuotaFormacion.objects.filter(idFormacion=idFormacion, is_active=True)
            if not cuotas_activas.exists():
                raise ValidationError('La formación seleccionada requiere cuotas, pero no tiene ninguna activa.')

        return cleaned_data

