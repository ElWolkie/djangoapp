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
    
    def clean_horas(self):
        """
        Acepta:
         - minutos como entero (string o int) -> devuelve int
         - "HH:MM" -> convierte a minutos totales int
         - valida valores y levanta ValidationError si no válido
        """
        raw = self.data.get('horas', '')  # usar self.data porque JS puede enviar string
        if raw is None or raw == '':
            raise forms.ValidationError("Ingrese las horas.")
        s = str(raw).strip()
        # si ya es entero en minutos
        if s.isdigit():
            try:
                val = int(s)
                if val < 0:
                    raise forms.ValidationError("Horas inválidas.")
                return val
            except ValueError:
                raise forms.ValidationError("Horas inválidas.")
        # formato HH:MM
        if ':' in s:
            parts = s.split(':')
            if len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit():
                h = int(parts[0])
                m = int(parts[1])
                if not (0 <= h <= 23 and 0 <= m <= 59):
                    raise forms.ValidationError("Horas fuera de rango.")
                return h * 60 + m
        # intentar parsear como número entero
        try:
            val = int(float(s))
            if val < 0:
                raise forms.ValidationError("Horas inválidas.")
            return val
        except Exception:
            raise forms.ValidationError("Formato de horas inválido. Use HH:MM o minutos enteros.")


    def clean_monto(self):
            raw = self.data.get('monto', '')
            if raw is None or raw == '':
                raise forms.ValidationError("Ingrese un monto.")
            
            # Si ya es un número decimal, retornarlo directamente
            try:
                return Decimal(raw)
            except (InvalidOperation, ValueError):
                pass
            
            # Si no, intentar limpiarlo
            s = str(raw).strip()
            s = s.replace(' ', '')
            s = s.replace(',', '.')
            
            # Eliminar caracteres no numéricos excepto punto
            import re
            s = re.sub(r'[^0-9.]', '', s)
            
            # Manejar múltiples puntos
            parts = s.split('.')
            if len(parts) > 2:
                s = parts[0] + '.' + ''.join(parts[1:])
            
            try:
                d = Decimal(s)
            except (InvalidOperation, ValueError):
                raise forms.ValidationError("Monto inválido. Use un número, por ejemplo 1777 o 1777.00")

            return d.quantize(Decimal('0.01'))

    def safe_decimal(value):
        if value is None:
            return Decimal('0.00')
        s = str(value).strip()
        # quitar separadores de miles y usar punto decimal
        s = s.replace(' ', '').replace('.', '').replace(',', '.')
        try:
            return Decimal(s)
        except InvalidOperation:
            raise ValueError(f"Valor decimal inválido: {value}")
