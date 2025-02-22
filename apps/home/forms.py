from django import forms
from .models import Personas

class PersonaForm(forms.ModelForm):
    estadoPersona = forms.CharField(widget=forms.HiddenInput(), initial='ACTIVO')

    class Meta:
        model = Personas
        fields = ['idTP', 'cedula', 'nombres', 'apellidos', 'telefono', 'correo', 'estadoPersona']