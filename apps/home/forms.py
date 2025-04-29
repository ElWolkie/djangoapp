from django import forms  
from .models import  Usuarios, Formacion, TipoFormacion, Materia, Cohorte, Cargo, Requisito, Servicio, Tramite, Denominacion, Banco, Moneda, Tasa, TipoMovimiento, Movimiento, Configuracion
from django.contrib.auth.models import Group

class AsignarGrupoForm(forms.Form):
    grupos = forms.ModelMultipleChoiceField(
        queryset=Group.objects.all(),
        widget=forms.CheckboxSelectMultiple,
        required=False,
    )

class UsuarioForm(forms.ModelForm):
    NUEVAS_PREGUNTAS = (
        ('', 'Seleccione una nueva pregunta (opcional)'),
        ('¿Cuál es el nombre de tu primera mascota?', '¿Cuál es el nombre de tu primera mascota?'),
        ('¿En qué ciudad naciste?', '¿En qué ciudad naciste?'),
        ('¿Cuál es el nombre de tu madre soltera?', '¿Cuál es el nombre de tu madre soltera?'),
        ('¿Cuál era el nombre de tu escuela primaria?', '¿Cuál era el nombre de tu escuela primaria?'),
        ('¿Cuál es tu película favorita?', '¿Cuál es tu película favorita?'),
        ('¿Cuál es tu color favorito?', '¿Cuál es tu color favorito?'),
    )

    nueva_pregunta = forms.ChoiceField(
        choices=NUEVAS_PREGUNTAS,
        required=False,
        label="Cambiar pregunta de seguridad",
        widget=forms.Select(attrs={'class': 'form-control'}))
    
    nueva_respuesta = forms.CharField(
        required=False,
        label="Nueva respuesta",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ingrese nueva respuesta',
            'maxlength': '255'
        }))

    class Meta:
        model = Usuarios
        fields = ['is_active', 'is_staff', 'is_superuser', 'preguntaSeguridad', 'respuestaSeguridad']
        widgets = {
            'preguntaSeguridad': forms.TextInput(attrs={'readonly': True, 'class': 'form-control'}),
            'respuestaSeguridad': forms.TextInput(attrs={'readonly': True, 'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['preguntaSeguridad'].label = "Pregunta actual"
        self.fields['respuestaSeguridad'].label = "Respuesta actual"
        self.fields['is_active'].label = "¿Usuario Activo?"
        self.fields['is_staff'].label = "¿Es Administrador?"
        self.fields['is_superuser'].label = "¿Es Superusuario?"
        
        # Personalizar opciones de los selects (opcional)
        self.fields['is_active'].choices = [
            (True, 'Sí - Usuario habilitado'),
            (False, 'No - Usuario desactivado')
        ]
        self.fields['is_staff'].choices = [
            (True, 'Sí - Acceso al panel administrativo'),
            (False, 'No - Usuario estándar')
        ]
        self.fields['is_superuser'].choices = [
            (True, 'Sí - Permisos totales'),
            (False, 'No - Permisos limitados')
        ]
    
    # Opcional: Validación extra si se da pregunta pero no respuesta
    def clean(self):
        cleaned_data = super().clean()
        nueva_pregunta = cleaned_data.get("nueva_pregunta")
        nueva_respuesta = cleaned_data.get("nueva_respuesta")

        if nueva_pregunta and not nueva_respuesta:
            self.add_error('nueva_respuesta', "Debe proporcionar una respuesta si ingresa una nueva pregunta.")

        return cleaned_data

class TipoFormacionForm(forms.ModelForm):  
    estadoTipoFormacion = forms.CharField(widget=forms.HiddenInput(), initial='ACTIVO')  

    class Meta:  
        model = TipoFormacion  
        fields = ['nombreTipoFormacion','estadoTipoFormacion']  


class FormacionForm(forms.ModelForm):  
    estadoFormacion = forms.CharField(widget=forms.HiddenInput(), initial='ACTIVO')  

    class Meta:  
        model = Formacion  
        fields = ['idTF', 'nombreFormacion','valorFormacion', 'duracion', 'estadoFormacion']


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