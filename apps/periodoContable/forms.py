from django import forms
from .models import periodoContable

class periodoContableForm(forms.ModelForm):
    class Meta:
        model = periodoContable
        exclude = ['estadoPeriodo']

    def clean(self):
        cleaned_data = super().clean()
        fecha_inicio = cleaned_data.get('fechaInicioPeriodo')
        fecha_fin = cleaned_data.get('fechaFinPeriodo')

        if fecha_inicio and fecha_fin and fecha_inicio > fecha_fin:
            raise forms.ValidationError("La fecha de inicio no puede ser posterior a la fecha de fin.")

        return cleaned_data