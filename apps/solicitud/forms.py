from django import forms  
from .models import Solicitud
from apps.persona.models import Personas


class SolicitudForm(forms.ModelForm):
    idPersona = forms.ModelChoiceField(
        queryset=Personas.objects.all(),
        empty_label="(Selecciona una persona)",
        required=True
    )
    estadoSolicitud = forms.CharField(widget=forms.HiddenInput(), initial='ACTIVO')  
  
    class Meta:  
        model = Solicitud  
        fields = ['idSoli', 'idPersona', 'idTramite', 'idServicio', 'montoTotal', 'estadoSolicitud', 'fechaEntrega']  
