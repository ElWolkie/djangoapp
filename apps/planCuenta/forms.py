from django import forms
from .models import PlanCuenta

class PlanCuentaForm(forms.ModelForm):
    class Meta:
        model = PlanCuenta
        fields = '__all__'

    def clean(self):
        cleaned_data = super().clean()
        nivel = cleaned_data.get('nivelPlanCuenta')
        cuenta_padre = cleaned_data.get('cuentaPadre')

        # Si el nivel es 1, cuentaPadre debe ser None
        if nivel == 1 and cuenta_padre is not None:
            cleaned_data['cuentaPadre'] = None

        return cleaned_data