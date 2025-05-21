from django import forms
from .models import PlanCuenta

class PlanCuentaForm(forms.ModelForm):
    """
    Formulario para la creación y edición de Planes de Cuenta.
    Incluye validación de la jerarquía de cuentas.
    """
    class Meta:
        model = PlanCuenta
        fields = '__all__'
        widgets = {
            'cuentaPadre': forms.Select(attrs={'class': 'form-control'}),
            'tipoPlanCuenta': forms.Select(attrs={'class': 'form-control'}),
            'naturalezaPlanCuenta': forms.Select(attrs={'class': 'form-control'}),
        }
        exclude = ['codigoPlanCuenta', 'estadoPlanCuenta']  # Excluir el campo generado automáticamente

    def clean(self):
        """
        Valida que la estructura jerárquica sea correcta:
        - Cuentas de nivel 1 no pueden tener padre
        - El nivel debe ser coherente con la cuenta padre
        - La naturaleza debe ser coherente con el tipo de cuenta, salvo excepciones
        """
        cleaned_data = super().clean()
        nivel = cleaned_data.get('nivelPlanCuenta')
        cuenta_padre = cleaned_data.get('cuentaPadre')
        tipo_cuenta = cleaned_data.get('tipoPlanCuenta')
        naturaleza = cleaned_data.get('naturalezaPlanCuenta')

        # Validar cuenta de nivel 1
        if nivel == 1 and cuenta_padre is not None:
            raise forms.ValidationError("Las cuentas de nivel 1 no pueden tener cuenta padre.")

        # Validar coherencia de tipo con cuenta padre
        if cuenta_padre and tipo_cuenta != cuenta_padre.tipoPlanCuenta:
            raise forms.ValidationError(
                f"El tipo de cuenta debe coincidir con el tipo de la cuenta principal/dependiente ({cuenta_padre.get_tipoPlanCuenta_display()})."
            )

        # Validar nivel coherente con cuenta padre
        if cuenta_padre and nivel != cuenta_padre.nivelPlanCuenta + 1:
            raise forms.ValidationError(
                f"El nivel debe ser exactamente 1 mayor que el nivel de la cuenta padre (Nivel {cuenta_padre.nivelPlanCuenta} + 1)."
            )

        # Validar coherencia de naturaleza con tipo de cuenta
        naturaleza_map = {
            'activo': 'deudora',
            'gasto': 'deudora',
            'pasivo': 'acreedora',
            'patrimonio': 'acreedora',
            'ingreso': 'acreedora',
        }
        naturaleza_esperada = naturaleza_map.get(tipo_cuenta)
        if naturaleza != naturaleza_esperada:
            raise forms.ValidationError(
                f"La naturaleza de la cuenta ({naturaleza}) no coincide con la naturaleza esperada para el tipo de cuenta '{tipo_cuenta}' ({naturaleza_esperada})."
            )

        return cleaned_data