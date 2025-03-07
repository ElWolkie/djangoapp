from django import forms  
from .models import TipoPersona, Personas, Ofertas, Cuota, TipoOferta, Materia, Cohorte, Cargo, Contrato, Honorario, Requisito, Servicio, Tramite, Solicitud, Denominacion

class TipoPersonaForm(forms.ModelForm):  
    estadoTP = forms.CharField(widget=forms.HiddenInput(), initial='ACTIVO')  

    class Meta:  
        model = TipoPersona  
        fields = ['nombreTP', 'estadoTP']  


class PersonaForm(forms.ModelForm):  
    estadoPersona = forms.CharField(widget=forms.HiddenInput(), initial='ACTIVO')  

    class Meta:  
        model = Personas  
        fields = ['idTP', 'cedula', 'nombres', 'apellidos', 'telefono', 'correo', 'estadoPersona']  


class CuotaForm(forms.ModelForm):  
    estadoCuota = forms.CharField(widget=forms.HiddenInput(), initial='ACTIVO')  

    class Meta:  
        model = Cuota  
        fields = ['idCuota', 'nombreCuota', 'estadoCuota']  


class OfertaForm(forms.ModelForm):  
    estadoOferta = forms.CharField(widget=forms.HiddenInput(), initial='ACTIVO')  

    class Meta:  
        model = Ofertas  
        fields = ['idOferta', 'idTipoOferta', 'nombreOferta', 'duracion', 'estadoOferta']  


class TipoOfertaForm(forms.ModelForm):  
    estadoTipoOferta = forms.CharField(widget=forms.HiddenInput(), initial='ACTIVO')  

    class Meta:  
        model = TipoOferta  
        fields = ['idTipoOferta', 'idCuota', 'nombreTipoOferta', 'estadoTipoOferta']  


class MateriaForm(forms.ModelForm):  
    estadoMateria = forms.CharField(widget=forms.HiddenInput(), initial='ACTIVO')  

    class Meta:  
        model = Materia  
        fields = ['idOferta', 'nombreMateria', 'estadoMateria']  # Nota: No se incluye idMateria, ya que es auto generado.


class CohorteForm(forms.ModelForm):  
    estadoCohorte = forms.CharField(widget=forms.HiddenInput(), initial='ACTIVO')  

    class Meta:  
        model = Cohorte  
        fields = ['idCohorte', 'nombreCohorte', 'estadoCohorte']  


class CargoForm(forms.ModelForm):  
    estadoCargo = forms.CharField(widget=forms.HiddenInput(), initial='ACTIVO')  

    class Meta:  
        model = Cargo  
        fields = ['idCargo', 'nombreCargo', 'estadoCargo']  

class ContratoForm(forms.ModelForm):  
    estadoContrato = forms.CharField(widget=forms.HiddenInput(), initial='ACTIVO')  
            
    class Meta:  
        model = Contrato  
        fields = ['idContrato', 'idPersona', 'idCargo', 'idCohorte', 'idMateria', 'estadoContrato']  


class HonorarioForm(forms.ModelForm):  
    estadoHonorario = forms.CharField(widget=forms.HiddenInput(), initial='ACTIVO')  
            
    class Meta:  
        model = Honorario  
        fields = ['idHonorario','idContrato', 'horas', 'estadoHonorario']  



class RequisitoForm(forms.ModelForm):  
    estadoRequisito = forms.CharField(widget=forms.HiddenInput(), initial='ACTIVO')  

    class Meta:  
        model = Requisito  
        fields = ['idRequisito', 'nombreRequisito', 'estadoRequisito']  


class ServicioForm(forms.ModelForm):  
    estadoServicio = forms.CharField(widget=forms.HiddenInput(), initial='ACTIVO')  

    class Meta:  
        model = Servicio  
        fields = ['idServicio', 'nombreServicio', 'tiempoServicio', 'precioServicio', 'estadoServicio']  


class TramiteForm(forms.ModelForm):  
    estadoTramite = forms.CharField(widget=forms.HiddenInput(), initial='ACTIVO')  

    class Meta:  
        model = Tramite  
        fields = ['idTramite', 'nombreTramite', 'diasTramite', 'precioTramite', 'estadoTramite']  

class SolicitudForm(forms.ModelForm):  
    estadoSolicitud = forms.CharField(widget=forms.HiddenInput(), initial='ACTIVO')  
  
    class Meta:  
        model = Solicitud  
        fields = ['idSoli', 'idPersona', 'idTramite', 'idServicio', 'montoTotal', 'estadoSolicitud', 'fechaEntrega']  


class DenominacionForm(forms.ModelForm):  
    estadoDenominacion = forms.CharField(widget=forms.HiddenInput(), initial='ACTIVO')  

    class Meta:  
        model = Denominacion  
        fields = ['idDenominacion', 'nombreDenominacion', 'estadoDenominacion']  
