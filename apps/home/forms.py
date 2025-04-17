from django import forms  
from .models import TipoPersona, Personas, PersonaTP, Formacion,TipoFormacion, Materia, Cohorte, Cargo, Requisito, Servicio, Tramite, Denominacion, Banco, Moneda, Tasa, TipoMovimiento, Movimiento

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

class PersonaTPForm(forms.ModelForm):
    class Meta:
        model = PersonaTP
        fields = ['idPersona', 'idTP']


class TipoFormacionForm(forms.ModelForm):  
    estadoTipoFormacion = forms.CharField(widget=forms.HiddenInput(), initial='ACTIVO')  

    class Meta:  
        model = TipoFormacion  
        fields = ['nombreTipoFormacion','cuotas', 'estadoTipoFormacion']  


class FormacionForm(forms.ModelForm):  
    estadoFormacion = forms.CharField(widget=forms.HiddenInput(), initial='ACTIVO')  

    class Meta:  
        model = Formacion  
        fields = ['idTF', 'nombreFormacion', 'duracion', 'estadoFormacion']


class MateriaForm(forms.ModelForm):  
    estadoMateria = forms.CharField(widget=forms.HiddenInput(), initial='ACTIVO')  

    class Meta:  
        model = Materia  
        fields = ['idFormacion', 'nombreMateria', 'estadoMateria']  # Nota: No se incluye idMateria, ya que es auto generado.


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
