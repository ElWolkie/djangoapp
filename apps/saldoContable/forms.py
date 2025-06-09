from django import forms
from .models import SaldoContable
from apps.planCuenta.models import PlanCuenta
from apps.periodoContable.models import periodoContable

class SaldoContableForm(forms.ModelForm):
    id_plan_cuenta = forms.ModelChoiceField(
        queryset=PlanCuenta.objects.filter(estadoPlanCuenta=True),
        label="Plan de Cuenta",
        error_messages={
            'required': 'Por favor seleccione un Plan de Cuenta.'
        }
    )
    
    id_periodo = forms.ModelChoiceField(
        queryset=periodoContable.objects.filter(estadoPeriodo=False),  # Solo períodos inactivos
        label="Periodo Contable",
        error_messages={
            'required': 'Por favor seleccione un Periodo Contable.'
        },
        help_text="Solo puede crear saldos para períodos inactivos"
    )

    class Meta:
        model = SaldoContable
        fields = ['id_plan_cuenta', 'id_periodo', 'saldo_inicial', 'saldo_final']
        labels = {
            'saldo_inicial': 'Saldo Inicial',
            'saldo_final': 'Saldo Final',
        }
        widgets = {
            'saldo_inicial': forms.NumberInput(attrs={'step': '0.01', 'min': '0'}),
            'saldo_final': forms.NumberInput(attrs={'step': '0.01', 'min': '0'}),
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

        # Validar que el período esté inactivo
        if periodo and periodo.estadoPeriodo:
            raise forms.ValidationError(
                "No puede crear saldos para períodos activos. "
                "Los saldos para períodos activos se generan automáticamente al crear el período."
            )

        # Validar duplicado
        if plan and periodo:
            if SaldoContable.objects.filter(id_plan_cuenta=plan, id_periodo=periodo).exists():
                raise forms.ValidationError(
                    "Ya existe un saldo para este plan de cuenta en el período seleccionado."
                )

        # Validar que saldo_final >= saldo_inicial
        if saldo_inicial is not None and saldo_final is not None:
            if saldo_final < saldo_inicial:
                self.add_error(
                    'saldo_final',
                    "El Saldo Final no puede ser menor que el Saldo Inicial."
                )

        return cleaned_data