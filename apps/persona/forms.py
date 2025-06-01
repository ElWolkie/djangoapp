import re
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
        fields = ['cedula', 'nombres', 'apellidos', 'telefono', 'correo', 'rif', 'direccion', 'estadoPersona']
        widgets = {
            'estadoPersona': forms.HiddenInput(),
            'cedula': forms.TextInput(attrs={'maxlength': 15}),
        }

    def clean_cedula(self):
        cedula = self.cleaned_data.get('cedula')
        
        # Validar formato
        if not re.match(r'^[VJEGP]-\d{5,15}$', cedula):
            raise forms.ValidationError("Formato inválido. Use: [V|J|E|G|P]-[números]")
        
        # Extraer parte numérica
        numeros_cedula = cedula.split('-', 1)[-1]  # Obtiene todo después del primer guión
        
        # Buscar si existe alguna cédula con la misma parte numérica
        qs = Personas.objects.exclude(pk=self.instance.pk)
        for persona in qs.iterator():
            # Obtener parte numérica de la cédula existente
            numeros_existentes = persona.cedula.split('-', 1)[-1]
            
            if numeros_existentes == numeros_cedula:
                raise forms.ValidationError(
                    f"La parte numérica de esta cédula ya está registrada como: {persona.cedula}"
                )
        return cedula

    def clean_correo(self):
        correo = self.cleaned_data.get('correo')
        # Validar unicidad del correo
        qs = Personas.objects.filter(correo=correo).exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError("Este correo electrónico ya está registrado.")
        return correo

class PersonaTPForm(forms.ModelForm):
    class Meta:
        model = PersonaTP
        fields = ['idPersona', 'idTP']


