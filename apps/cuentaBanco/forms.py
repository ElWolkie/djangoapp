from django import forms
from .models import Banco, CuentaBanco
from apps.planCuenta.models import PlanCuenta

class BancoForm(forms.ModelForm):
    """
    Formulario para la creación y edición de Bancos.
    Incluye validación de códigos y relación con plan de cuentas.
    """
    
    class Meta:
        model = Banco
        exclude = ['estadoBanco']

        fields = [
            'nombreBanco',
            'codLocalBanco',
            'codSwiftBanco',
            'cuentaPadre',
        ]
        widgets = {
            'tipoCuenta': forms.Select(attrs={'class': 'form-control'}),
            'cuentaPadre': forms.Select(attrs={'class': 'form-control'}),
        }
        labels = {
            'tipoCuenta': 'Clasificación Contable',
            'cuentaPadre': 'Cuenta Contable Padre'
        }

    def clean_codLocalBanco(self):
        """Valida que el código local solo contenga caracteres alfanuméricos."""
        cod_local = self.cleaned_data['codLocalBanco']
        if not cod_local.isalnum():
            raise forms.ValidationError("El código local solo puede contener letras y números.")
        return cod_local

    def clean_codSwiftBanco(self):
        """Valida el formato básico del código SWIFT/BIC."""
        cod_swift = self.cleaned_data['codSwiftBanco']
        if len(cod_swift) != 8 and len(cod_swift) != 11:
            raise forms.ValidationError("El código SWIFT/BIC debe tener 8 u 11 caracteres.")
        return cod_swift

class CuentaBancoForm(forms.ModelForm):
    """
    Formulario para la creación y edición de Cuentas Bancarias.
    Incluye validación de número de cuenta y coherencia con tipo de producto.
    """
    
    class Meta:
        model = CuentaBanco
        exclude = ['planCuenta','estado']
        widgets = {
            'banco': forms.Select(attrs={'class': 'form-control'}),
            'moneda': forms.Select(attrs={'class': 'form-control'}),
            'tipoCuenta': forms.Select(attrs={'class': 'form-control'}),
            'tipoProducto': forms.Select(attrs={'class': 'form-control'}),
            'fechaApertura': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        }
        labels = {
            'tipoCuenta': 'Clasificación Contable',
            'tipoProducto': 'Tipo de Producto Bancario'
        }

    def clean_numeroCuentaBanco(self):
        """Valida el formato del número de cuenta."""
        numero_cuenta = self.cleaned_data['numeroCuentaBanco']
        if not all(c.isalnum() or c in ['-', ' '] for c in numero_cuenta):
            raise forms.ValidationError("El número de cuenta solo puede contener letras, números, guiones y espacios.")
        return numero_cuenta

    def clean(self):
        """
        Valida la coherencia entre tipo de cuenta y tipo de producto:
        - Productos de activo (cuentas corrientes, ahorros) deben ser tipo activo
        - Productos de pasivo (préstamos) deben ser tipo pasivo
        """
        cleaned_data = super().clean()
        tipo_cuenta = cleaned_data.get('tipoCuenta')
        tipo_producto = cleaned_data.get('tipoProducto')

        producto_a_tipo = {
            'corriente': 'activo',
            'ahorro': 'activo',
            'plazo_fijo': 'activo',
            'prestamo': 'pasivo',
            'credito': 'pasivo',
            'inversion': 'patrimonio'
        }

        if tipo_producto and tipo_cuenta:
            tipo_esperado = producto_a_tipo.get(tipo_producto)
            if tipo_esperado and tipo_cuenta != tipo_esperado:
                raise forms.ValidationError(
                    f"El tipo de producto {self.instance.get_tipoProducto_display()} debe ser de tipo contable {tipo_esperado}."
                )

        return cleaned_data