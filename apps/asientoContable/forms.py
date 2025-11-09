from django import forms
from .models import AsientoContable, DetalleAsiento

class AsientoContableForm(forms.ModelForm):
    """
    Formulario para la creación y edición de Asientos Contables.
    """
    class Meta:
        model = AsientoContable
        fields = ['numeroAsiento', 'fechaAsiento', 'conceptoAsiento', 'idPeriodo']
        widgets = {
            'numeroAsiento': forms.TextInput(attrs={'class': 'form-control'}),
            'fechaAsiento': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'conceptoAsiento': forms.Textarea(attrs={'class': 'form-control'}),
            'idPeriodo': forms.Select(attrs={'class': 'form-control'}),
        }

class DetalleAsientoForm(forms.ModelForm):
    """
    Formulario para la creación y edición de Detalles de Asientos Contables.
    """
    class Meta:
        model = DetalleAsiento
        fields = ['idPlanCuenta', 'debe', 'haber', 'estadoDetalle', 'idMoneda']
        widgets = {
            'idPlanCuenta': forms.Select(attrs={'class': 'form-control'}),
            'debe': forms.NumberInput(attrs={'class': 'form-control'}),
            'haber': forms.NumberInput(attrs={'class': 'form-control'}),
            'estadoDetalle': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'idMoneda': forms.Select(attrs={'class': 'form-control'}),
        }