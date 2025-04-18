from django import forms  
from .models import  Formacion,TipoFormacion, Materia, Cohorte, Cargo, Requisito, Servicio, Tramite, Denominacion, Banco, Moneda, Tasa, TipoMovimiento, Movimiento, Configuracion

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

class ConfiguracionForm(forms.ModelForm):
    # Opcional: Personalizar widgets para añadir clases de Bootstrap, etc.
    nombreInstitucion = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control text-dark', 'placeholder': 'Ingrese el nombre de la institución', 'maxlength': 150}))
    rif = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control text-dark', 'placeholder': 'Ej: J-12345678-9', 'maxlength': 15}))
    correoInstitucion = forms.EmailField(widget=forms.EmailInput(attrs={'class': 'form-control text-dark', 'placeholder': 'contacto@institucion.com', 'maxlength': 254}))
    # El widget para Moneda se renderizará como un select por defecto
    moneda = forms.ModelChoiceField(
        queryset=Moneda.objects.filter(estadoMoneda='ACTIVO'), # Asegura que solo monedas activas aparezcan aquí también
        widget=forms.Select(attrs={'class': 'form-control text-dark'}),
        empty_label="Seleccione una moneda..."
    )
    logo = forms.ImageField(widget=forms.FileInput(attrs={'class': 'form-control-file text-dark', 'accept': 'image/*'}), required=False) # Hacemos 'required=False' por defecto
    firma = forms.ImageField(widget=forms.FileInput(attrs={'class': 'form-control-file text-dark', 'accept': 'image/*'}), required=False) # Hacemos 'required=False' por defecto

    class Meta:
        model = Configuracion
        # Excluimos fechaConfiguracion que es auto_now_add
        fields = ['nombreInstitucion', 'rif', 'correoInstitucion', 'moneda', 'logo', 'firma']

    def __init__(self, *args, **kwargs):
        super(ConfiguracionForm, self).__init__(*args, **kwargs)

        if not self.instance or not self.instance.pk:
            self.fields['logo'].required = True
            self.fields['firma'].required = True
        self.fields['moneda'].queryset = Moneda.objects.filter(estadoMoneda='ACTIVO')