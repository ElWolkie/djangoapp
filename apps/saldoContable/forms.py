# apps/saldoContable/forms.py

from django import forms
from .models import SaldoContable
from apps.planCuenta.models import PlanCuenta
from apps.periodoContable.models import periodoContable

class SaldoContableForm(forms.ModelForm):
    # Debemos usar exactamente el nombre del campo FK que tiene el modelo:
    id_plan_cuenta = forms.ModelChoiceField(
        queryset=PlanCuenta.objects.filter(estadoPlanCuenta=True),
        label="Plan de Cuenta",
        error_messages={
            'required': 'Por favor seleccione un Plan de Cuenta.'
        }
    )
    id_periodo = forms.ModelChoiceField(
        queryset=periodoContable.objects.filter(estadoPeriodo=True),
        label="Periodo Contable",
        error_messages={
            'required': 'Por favor seleccione un Periodo Contable.'
        }
    )

    class Meta:
        model = SaldoContable
        # Aquí también usamos los nombres reales del modelo, sin "_id"
        fields = ['id_plan_cuenta', 'id_periodo', 'saldo_inicial', 'saldo_final']
        labels = {
            'saldo_inicial': 'Saldo Inicial',
            'saldo_final': 'Saldo Final',
        }
        error_messages = {
            'saldo_inicial': {
                'required': 'Ingrese el Saldo Inicial.',
                'invalid': 'Ingrese un número válido para el Saldo Inicial.',
            },
            'saldo_final': {
                'required': 'Ingrese el Saldo Final.',
                'invalid': 'Ingrese un número válido para el Saldo Final.',
            }
        }

    def clean(self):
        cleaned_data = super().clean()
        plan = cleaned_data.get('id_plan_cuenta')
        periodo = cleaned_data.get('id_periodo')
        saldo_inicial = cleaned_data.get('saldo_inicial')
        saldo_final = cleaned_data.get('saldo_final')

        # 1) Validar duplicado de (plan, periodo)
        if plan and periodo:
            existe = SaldoContable.objects.filter(
                id_plan_cuenta=plan,
                id_periodo=periodo
            )
            if existe.exists():
                raise forms.ValidationError(
                    "Ya existe un Saldo Contable para ese Plan de Cuenta y Periodo."
                )

        # 2) Validar que saldo_final >= saldo_inicial
        if saldo_inicial is not None and saldo_final is not None:
            if saldo_final < saldo_inicial:
                self.add_error(
                    'saldo_final',
                    "El Saldo Final no puede ser menor que el Saldo Inicial."
                )

        return cleaned_data
