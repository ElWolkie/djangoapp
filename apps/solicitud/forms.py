from django import forms  
from .models import Solicitud


class SolicitudForm(forms.ModelForm):  
    estadoSolicitud = forms.CharField(widget=forms.HiddenInput(), initial='ACTIVO')  
  
    class Meta:  
        model = Solicitud  
        fields = ['idSoli', 'idPersona', 'idTramite', 'idServicio', 'montoTotal', 'estadoSolicitud', 'fechaEntrega']  
