from django import forms  
from django.utils.html import format_html
from .models import Honorario
from decimal import Decimal, InvalidOperation

class HonorarioForm(forms.ModelForm):  
    estadoHonorario = forms.CharField(widget=forms.HiddenInput(), initial='ACTIVO')  
            
    class Meta:  
        model = Honorario  
        fields = ['idHonorario', 'idPersona', 'idCargo', 'idCohorte', 'idMateria', 'horas', 'monto', 'estadoHonorario']  

    def clean(self):
        cleaned_data = super().clean()
        idPersona = cleaned_data.get('idPersona')
        idCargo = cleaned_data.get('idCargo')
        idMateria = cleaned_data.get('idMateria')
        idCohorte = cleaned_data.get('idCohorte')
        
        # Verificar si todos los campos necesarios están presentes
        if all([idPersona, idCargo, idMateria, idCohorte]):
            # Verifica si ya existe un registro idéntico
            duplicate = Honorario.objects.filter(
                idPersona=idPersona,
                idCargo=idCargo,
                idMateria=idMateria,
                idCohorte=idCohorte
            )
            
            if duplicate.exists():
                # Construir mensaje detallado
                existing = duplicate.first()
                error_msg = format_html(
                    "Ya existe un honorario idéntico registrado:<br>"
                    "• Proveedor: {} {}<br>"
                    "• Cargo: {}<br>"
                    "• Materia: {}<br>"
                    "• Cohorte: {}",
                    existing.idPersona.nombres,
                    existing.idPersona.apellidos,
                    existing.idCargo.nombreCargo,
                    existing.idMateria.nombreMateria,
                    existing.idCohorte.nombreCohorte
                )
                raise forms.ValidationError({'__all__': [error_msg]})
                
        return 
    
    def clean_monto(self):
        raw = self.data.get('monto', '')
        if raw is None:
            raise forms.ValidationError("Ingrese un monto.")
        # normalizar: quitar espacios, comas de miles, comas decimales -> usar punto
        s = str(raw).strip()
        # si el usuario ingresó separador de miles con puntos (ej: 1.777,00) primero convertir coma->.
        # pero para simplificar: quitar espacios y barras
        s = s.replace(' ', '')
        # Si hay comas y puntos, suponer que la coma es decimal si la coma viene después del último punto
        # Estrategia simple: reemplazar comas por puntos, eliminar duplicados de puntos antes del decimal
        s = s.replace(',', '.')
        # eliminar caracteres que no sean dígitos o punto
        import re
        s = re.sub(r'[^0-9.]', '', s)
        # si hay más de un punto, unir los extras como parte decimal
        parts = s.split('.')
        if len(parts) > 2:
            s = parts[0] + '.' + ''.join(parts[1:])

        try:
            d = Decimal(s)
        except (InvalidOperation, ValueError):
            raise forms.ValidationError("Monto inválido. Use un número, por ejemplo 1777 o 1777.00")

        # redondear/truncar a 2 decimales
        return d.quantize(Decimal('0.01'))