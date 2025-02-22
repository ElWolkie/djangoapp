from django import forms
from .models import TipoPersona, Personas

class TipoPersonaForm(forms.ModelForm):
    estadoTP = forms.CharField(widget=forms.HiddenInput(), initial='ACTIVO')

    class Meta:
        model = TipoPersona
        fields = ['nombreTP', 'estadoTP']

class PersonaForm(forms.ModelForm):
    estadoPersona = forms.CharField(widget=forms.HiddenInput(), initial='ACTIVO')

    class Meta:
        model = Personas
        fields = ['idTP', 'cedula', 'nombres', 'apellidos', 'telefono', 'correo', 'estadoPersona']