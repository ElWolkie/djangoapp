from django import forms  
from .models import  Honorario


class HonorarioForm(forms.ModelForm):  
    estadoHonorario = forms.CharField(widget=forms.HiddenInput(), initial='ACTIVO')  
            
    class Meta:  
        model = Honorario  
        fields = ['idHonorario', 'idPersona', 'idCargo', 'idCohorte', 'idMateria', 'horas', 'monto', 'estadoHonorario']  

