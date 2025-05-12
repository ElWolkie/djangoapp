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
        widgets = {
            'estadoPersona': forms.HiddenInput(),
        }

    def clean_cedula(self):
        cedula = self.cleaned_data.get('cedula')
        # Si es una creación (self.instance.pk es None) y la cédula ya existe
        if not self.instance.pk and Personas.objects.filter(cedula=cedula).exists():
            raise forms.ValidationError("Esta cédula ya está registrada.")
        # Aquí puedes añadir más validaciones para el formato de la cédula si es necesario
        return cedula

    def clean_correo(self):
        correo = self.cleaned_data.get('correo')
        # Validar unicidad del correo si es necesario
        if not self.instance.pk and Personas.objects.filter(correo=correo).exists():
            raise forms.ValidationError("Este correo electrónico ya está registrado.")
        return correo

class PersonaTPForm(forms.ModelForm):
    class Meta:
        model = PersonaTP
        fields = ['idPersona', 'idTP']


