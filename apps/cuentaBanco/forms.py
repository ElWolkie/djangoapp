from django import forms
from .models import cuentaBanco

class cuentaBancoForm(forms.ModelForm):
    class Meta:
        model = cuentaBanco
        fields = '__all__'

    def clean(self):
        cleaned_data = super().clean()
        numero_cuenta = cleaned_data.get('numeroCuentaBanco')

        # Validar que el número de cuenta tenga solo números
        if numero_cuenta and not numero_cuenta.isdigit():
            raise forms.ValidationError("El número de cuenta debe contener solo números.")

        return cleaned_data