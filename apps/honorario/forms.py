from django import forms  
from django.utils.html import format_html
from .models import Honorario

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
                
        return cleaned_data