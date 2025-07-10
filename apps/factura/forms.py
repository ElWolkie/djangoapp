from django import forms
from .models import Nota, Factura, FacturaDetalle, Pago, ParametroTributario

class NotaForm(forms.ModelForm):
    """
    Formulario para la creación y edición de Notas (Cobro/Pago).
    Incluye validaciones específicas para los campos relacionados.
    """
    class Meta:
        model = Nota
        fields = '__all__'
        widgets = {
            'idPersona': forms.Select(attrs={'class': 'form-control'}),
            'idEmpresa': forms.Select(attrs={'class': 'form-control'}),
            'tipoArticulo': forms.Select(attrs={'class': 'form-control'}),
            'numeroNota': forms.TextInput(attrs={'class': 'form-control'}),
            'fechaEmision': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'fechaVencimiento': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'formaPago': forms.TextInput(attrs={'class': 'form-control'}),
            'subtotalExento': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'subtotalGravado': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'iva': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'ivaRetenido': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'islrRetenido': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'descuento': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'totalNota': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'estado': forms.Select(attrs={'class': 'form-control'}),
            'observaciones': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

    def clean(self):
        """
        Validaciones personalizadas para el formulario de Nota.
        """
        cleaned_data = super().clean()
        subtotal_exento = cleaned_data.get('subtotalExento')
        subtotal_gravado = cleaned_data.get('subtotalGravado')
        iva = cleaned_data.get('iva')
        total_nota = cleaned_data.get('totalNota')

        # Validar que el total de la nota sea consistente con los subtotales y el IVA
        if total_nota is not None and subtotal_exento is not None and subtotal_gravado is not None and iva is not None:
            calculado = subtotal_exento + subtotal_gravado + iva
            if total_nota != calculado:
                self.add_error('totalNota', "El total de la nota no coincide con la suma de los subtotales y el IVA.")

        return cleaned_data


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
            'numeroFactura': forms.TextInput(attrs={'class': 'form-control'}),
            'tipoFactura': forms.Select(attrs={'class': 'form-control'}),
            'subtotalExento': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'subtotalGravado': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'iva': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'ivaRetenido': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'islrRetenido': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'descuento': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'totalVenta': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'estado': forms.Select(attrs={'class': 'form-control'}),
            'observaciones': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

    def clean(self):
        """
        Validaciones personalizadas para el formulario de Factura.
        """
        cleaned_data = super().clean()
        subtotal_exento = cleaned_data.get('subtotalExento')
        subtotal_gravado = cleaned_data.get('subtotalGravado')
        iva = cleaned_data.get('iva')
        total_venta = cleaned_data.get('totalVenta')

        # Validar que el total de la factura sea consistente con los subtotales y el IVA
        if total_venta is not None and subtotal_exento is not None and subtotal_gravado is not None and iva is not None:
            calculado = subtotal_exento + subtotal_gravado + iva
            if total_venta != calculado:
                self.add_error('totalVenta', "El total de la factura no coincide con la suma de los subtotales y el IVA.")

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
            'cantidad': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'precioUnitario': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'subtotal': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'ivaItem': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'totalItem': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
        }

    def clean(self):
        """
        Validaciones personalizadas para el formulario de FacturaDetalle.
        """
        cleaned_data = super().clean()
        cantidad = cleaned_data.get('cantidad')
        precio_unitario = cleaned_data.get('precioUnitario')
        subtotal = cleaned_data.get('subtotal')

        # Validar que el subtotal sea igual a cantidad * precio_unitario
        if cantidad and precio_unitario and subtotal is not None:
            if subtotal != cantidad * precio_unitario:
                self.add_error('subtotal', "El subtotal debe ser igual a la cantidad multiplicada por el precio unitario.")

        return cleaned_data


class PagoForm(forms.ModelForm):
    """
    Formulario para la creación y edición de Pagos.
    Incluye validaciones específicas para los campos relacionados.
    """
    class Meta:
        model = Pago
        exclude = ['idAsiento']  # Excluir el campo idAsiento
        widgets = {
            'idFactura': forms.Select(attrs={'class': 'form-control'}),
            'idCuentaBanco': forms.Select(attrs={'class': 'form-control'}),
            'formaPago': forms.TextInput(attrs={'class': 'form-control'}),
            'referencia': forms.TextInput(attrs={'class': 'form-control'}),
            'monto': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
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
            self.add_error('monto', "El monto del pago debe ser mayor a 0.")

        return cleaned_data


class ParametroTributarioForm(forms.ModelForm):
    """
    Formulario para la creación y edición de Parámetros Tributarios.
    """
    class Meta:
        model = ParametroTributario
        fields = [
            'tipo', 'aplica_a', 'porcentaje', 'valor_fijo', 
            'fecha_inicio', 'fecha_fin', 'activo', 'descripcion'
        ]
        widgets = {
            'fecha_inicio': forms.DateInput(attrs={'type': 'date'}),
            'fecha_fin': forms.DateInput(attrs={'type': 'date'}),
            'descripcion': forms.Textarea(attrs={'rows': 3}),
        }
        help_texts = {
            'porcentaje': 'Ingrese el porcentaje a aplicar (0 para exenciones).',
            'valor_fijo': 'Ingrese un valor fijo si aplica, en lugar de porcentaje.',
        }

    def clean(self):
        """
        Validaciones personalizadas para el formulario de Parámetro Tributario.
        """
        cleaned_data = super().clean()
        fecha_inicio = cleaned_data.get('fecha_inicio')
        fecha_fin = cleaned_data.get('fecha_fin')

        # Validar que la fecha de fin no sea anterior a la fecha de inicio
        if fecha_fin and fecha_inicio and fecha_fin < fecha_inicio:
            self.add_error('fecha_fin', "La fecha de fin no puede ser anterior a la fecha de inicio.")

        return cleaned_data