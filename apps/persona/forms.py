from django import forms  
from .models import TipoPersona, Personas, PersonaTP

class TipoPersonaForm(forms.ModelForm):  
    estadoTP = forms.CharField(widget=forms.HiddenInput(), initial='ACTIVO')  

    class Meta:  
        model = TipoPersona  
        fields = ['nombreTP', 'estadoTP']  


class PersonaForm(forms.ModelForm):  
    estadoPersona = forms.CharField(widget=forms.HiddenInput(), initial='ACTIVO')  

    class Meta:  
        model = Personas  
        fields = ['cedula', 'nombres', 'apellidos', 'telefono', 'correo', 'estadoPersona']  

class PersonaTPForm(forms.ModelForm):
    class Meta:
        model = PersonaTP
        fields = ['idPersona', 'idTP']


