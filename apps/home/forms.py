from django import forms  
from .models import TipoPersona, Personas,  PersonaTipoPersona, Ofertas, Cuota, TipoOferta, Materia, Cohorte, Cargo, Honorario, Requisito, Servicio, Tramite, Solicitud, Denominacion, Banco, Moneda, Tasa, TipoMovimiento, Movimiento

class TipoPersonaForm(forms.ModelForm):  
    estadoTP = forms.CharField(widget=forms.HiddenInput(), initial='ACTIVO')  

    class Meta:  
        model = TipoPersona  
        fields = ['nombreTP', 'estadoTP']  


class PersonaForm(forms.ModelForm):  
    estadoPersona = forms.CharField(widget=forms.HiddenInput(), initial='ACTIVO')  

    class Meta:  
        model = Personas  
        fields = ['cedula', 'nombres', 'apellidos', 'telefono', 'correo', 'estadoPersona']  

class PersonaTipoPersonaForm(forms.ModelForm):
    class Meta:
        model = PersonaTipoPersona
        fields = ['idPersona', 'idTP']

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


class HonorarioForm(forms.ModelForm):  
    estadoHonorario = forms.CharField(widget=forms.HiddenInput(), initial='ACTIVO')  
            
    class Meta:  
        model = Honorario  
        fields = ['idHonorario', 'idPersona', 'idCargo', 'idCohorte', 'idMateria', 'horas', 'estadoHonorario']  



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


class BancoForm(forms.ModelForm):  
    estadoBanco = forms.CharField(widget=forms.HiddenInput(), initial='ACTIVO')  

    class Meta:  
        model = Banco
        fields = ['idBanco', 'codBanco', 'codContable', 'nombreBanco', 'estadoBanco']  


class MonedaForm(forms.ModelForm):  
    estadoMoneda = forms.CharField(widget=forms.HiddenInput(), initial='ACTIVO')  

    class Meta:  
        model = Moneda
        fields = ['idMoneda', 'nombreMoneda','simboloMoneda', 'estadoMoneda']  



class TasaForm(forms.ModelForm):  
    estadoTasa = forms.CharField(widget=forms.HiddenInput(), initial='ACTIVO')  

    class Meta:  
        model = Tasa
        fields = ['idTasa', 'idMoneda', 'montoTasa','estadoTasa']  



class TipoMovimientoForm(forms.ModelForm):  
    estadoTipoMovimiento = forms.CharField(widget=forms.HiddenInput(), initial='ACTIVO')  

    class Meta:  
        model = TipoMovimiento  
        fields = ['idTipoMovimiento', 'naturaleza', 'nombreTipoMovimiento', 'estadoTipoMovimiento']  
  

class MovimientoForm(forms.ModelForm):  
    estadoMovimiento = forms.CharField(widget=forms.HiddenInput(), initial='ACTIVO')  

    class Meta:  
        model = Movimiento  
        fields = [
            'idTipoMovimiento', 
            'idDenominacion', 
            'idBanco', 
            'idTasa', 
            'naturaleza',   
            'tipoPago', 
            'referencia', 
            'monto', 
            'descripcion', 
            'estadoMovimiento'
        ]
