from django import forms
from .models import empresa

class empresaForm(forms.ModelForm):
    class Meta:
        model = empresa
        exclude = ['estadoEmpresa']  # Excluir el campo de estado
               
    def clean(self):
        cleaned_data = super().clean()
        telefono = cleaned_data.get('telefonoEmpresa')

        # Validar que el teléfono tenga solo números o guiones
        if telefono and not all(char.isdigit() or char == '-' for char in telefono):
            raise forms.ValidationError("El teléfono debe contener solo números o guiones.")

        return cleaned_data