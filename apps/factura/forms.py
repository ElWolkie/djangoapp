from django import forms
from .models import Factura, FacturaDetalle, Pago

class FacturaForm(forms.ModelForm):
    """
    Formulario para la creación y edición de Facturas.
    Incluye validaciones específicas para los campos relacionados.
    """
    class Meta:
        model = Factura
        fields = '__all__'
        widgets = {
            'idPersona': forms.Select(attrs={'class': 'form-control'}),
            'idEmpresa': forms.Select(attrs={'class': 'form-control'}),
            'idPeriodo': forms.Select(attrs={'class': 'form-control'}),
            'idAsiento': forms.Select(attrs={'class': 'form-control'}),
            'idTasa': forms.Select(attrs={'class': 'form-control'}),
            'estado': forms.Select(attrs={'class': 'form-control'}),
            'observaciones': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

    def clean(self):
        """
        Validaciones personalizadas para el formulario de Factura.
        """
        cleaned_data = super().clean()
        fecha_emision = cleaned_data.get('fechaEmision')
        fecha_vencimiento = cleaned_data.get('fechaVencimiento')

        # Validar que la fecha de vencimiento sea posterior a la fecha de emisión
        if fecha_vencimiento and fecha_emision and fecha_vencimiento < fecha_emision:
            raise forms.ValidationError("La fecha de vencimiento no puede ser anterior a la fecha de emisión.")

        # Validar que el total de la venta sea mayor a 0
        total_venta = cleaned_data.get('totalVenta')
        if total_venta is not None and total_venta <= 0:
            raise forms.ValidationError("El total de la venta debe ser mayor a 0.")

        return cleaned_data


class FacturaDetalleForm(forms.ModelForm):
    """
    Formulario para la creación y edición de Detalles de Factura.
    Incluye validaciones específicas para los campos relacionados.
    """
    class Meta:
        model = FacturaDetalle
        fields = '__all__'
        widgets = {
            'idFactura': forms.Select(attrs={'class': 'form-control'}),
            'tipoItem': forms.TextInput(attrs={'class': 'form-control'}),
            'descripcion': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }

    def clean(self):
        """
        Validaciones personalizadas para el formulario de FacturaDetalle.
        """
        cleaned_data = super().clean()
        cantidad = cleaned_data.get('cantidad')
        precio_unitario = cleaned_data.get('precioUnitario')

        # Validar que la cantidad y el precio unitario sean mayores a 0
        if cantidad is not None and cantidad <= 0:
            raise forms.ValidationError("La cantidad debe ser mayor a 0.")
        if precio_unitario is not None and precio_unitario <= 0:
            raise forms.ValidationError("El precio unitario debe ser mayor a 0.")

        # Validar que el subtotal sea igual a cantidad * precio_unitario
        subtotal = cleaned_data.get('subtotal')
        if cantidad and precio_unitario and subtotal is not None:
            if subtotal != cantidad * precio_unitario:
                raise forms.ValidationError("El subtotal debe ser igual a la cantidad multiplicada por el precio unitario.")

        return cleaned_data


class PagoForm(forms.ModelForm):
    """
    Formulario para la creación y edición de Pagos.
    Incluye validaciones específicas para los campos relacionados.
    """
    class Meta:
        model = Pago
        fields = '__all__'
        widgets = {
            'idFactura': forms.Select(attrs={'class': 'form-control'}),
            'idAsiento': forms.Select(attrs={'class': 'form-control'}),
            'idCuentaBanco': forms.Select(attrs={'class': 'form-control'}),
            'idMoneda': forms.Select(attrs={'class': 'form-control'}),
            'formaPago': forms.TextInput(attrs={'class': 'form-control'}),
            'referencia': forms.TextInput(attrs={'class': 'form-control'}),
            'observaciones': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

    def clean(self):
        """
        Validaciones personalizadas para el formulario de Pago.
        """
        cleaned_data = super().clean()
        monto = cleaned_data.get('monto')

        # Validar que el monto sea mayor a 0
        if monto is not None and monto <= 0:
            raise forms.ValidationError("El monto del pago debe ser mayor a 0.")

        return cleaned_data