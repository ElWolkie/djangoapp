from django import forms

from apps.cuentaBanco.models import CuentaBanco  
from .models import  Usuarios, Formacion, TipoFormacion, Materia, Cohorte, Cargo, Requisito, Servicio, Tramite, Moneda, Tasa, Configuracion, CuotaFormacion
from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError

class AsignarGrupoForm(forms.Form):
    grupos = forms.ModelMultipleChoiceField(
        queryset=Group.objects.none(),  # inicial vacío, se setea dinámicamente
        widget=forms.CheckboxSelectMultiple,
        required=False
    )

    def __init__(self, *args, **kwargs):
        grupos_qs = kwargs.pop('grupos_qs', Group.objects.none())
        super().__init__(*args, **kwargs)
        self.fields['grupos'].queryset = grupos_qs
        self.fields['grupos'].label = "Seleccionar Grupos"
        self.fields['grupos'].widget.attrs.update({'class': 'form-check-input'})


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
        widget=forms.Select(attrs={
            'class': 'form-control input-with-icon',
            'style': 'padding-left: 40px;'  # ESPACIO PARA EL ICONO
        }))
    
    nueva_respuesta = forms.CharField(
        required=False,
        label="Nueva respuesta",
        widget=forms.TextInput(attrs={
            'class': 'form-control input-with-icon',
            'style': 'padding-left: 40px;',  # ESPACIO PARA EL ICONO
            'placeholder': 'Ingrese nueva respuesta',
            'maxlength': '255'
        }))

    class Meta:
        model = Usuarios
        fields = ['is_active', 'is_staff', 'is_superuser', 'preguntaSeguridad', 'respuestaSeguridad']
        widgets = {
            'preguntaSeguridad': forms.TextInput(attrs={
                'readonly': True, 
                'class': 'form-control input-with-icon',
                'style': 'padding-left: 40px;'  # ESPACIO PARA EL ICONO
            }),
            'respuestaSeguridad': forms.TextInput(attrs={
                'readonly': True, 
                'class': 'form-control input-with-icon',
                'style': 'padding-left: 40px;'  # ESPACIO PARA EL ICONO
            }),
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
        fields = ['idTF', 'nombreFormacion', 'valorInscripcion', 'tieneCuotas', 'duracion', 'estadoFormacion']
        widgets = {
            'tieneCuotas': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def clean_nombreFormacion(self):
        nombre = self.cleaned_data['nombreFormacion'].strip()
        # Si es edición y no cambió, lo devolvemos directamente
        if self.instance.pk and nombre.lower() == self.instance.nombreFormacion.lower():
            return nombre
        # Si cambió, comprobamos unicidad
        if Formacion.objects.filter(nombreFormacion__iexact=nombre).exists():
            raise ValidationError("Ya existe una formación con ese nombre.")
        return nombre

    def clean_valorInscripcion(self):
        valor = self.cleaned_data['valorInscripcion']
        if valor < 0:
            raise ValidationError("El valor de inscripción no puede ser negativo.")
        return valor

class CuotaFormacionForm(forms.ModelForm):
    class Meta:
        model = CuotaFormacion
        fields = [
            'idFormacion', 
            'nombreCuota', 
            'tipoCuota', 
            'valorCuota', 
            'orden', 
            'is_active'
        ]
        widgets = {
            'idFormacion': forms.Select(attrs={'class': 'form-control'}),
            'nombreCuota': forms.TextInput(attrs={
                'class': 'form-control', 
                'placeholder': 'Ingrese el nombre de la cuota'
            }),
            'tipoCuota': forms.Select(attrs={'class': 'form-control'}),
            'valorCuota': forms.NumberInput(attrs={
                'class': 'form-control', 
                'placeholder': 'Ingrese el valor de la cuota'
            }),
            'orden': forms.NumberInput(attrs={
                'class': 'form-control', 
                'placeholder': 'Ingrese el orden de la cuota'
            }),
            'fechaCuota': forms.DateInput(attrs={
                'class': 'form-control', 
                'type': 'date'
            }),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def clean_valorCuota(self):
        valor = self.cleaned_data['valorCuota']
        if valor <= 0:
            raise forms.ValidationError("El valor de la cuota debe ser mayor a cero.")
        return valor

    def clean_orden(self):
        orden = self.cleaned_data['orden']
        if orden <= 0:
            raise forms.ValidationError("El orden debe ser un número positivo.")
        return orden
    
class MateriaForm(forms.ModelForm):  
    estadoMateria = forms.CharField(widget=forms.HiddenInput(), initial='ACTIVO')  

    class Meta:  
        model = Materia  
        fields = ['idFormacion', 'nombreMateria', 'estadoMateria']

    def clean_nombreMateria(self):
        nombre = self.cleaned_data['nombreMateria'].strip()
        # Si es edición y no cambió, lo devolvemos directamente
        if self.instance.pk and nombre.lower() == self.instance.nombreMateria.lower():
            return nombre
        # Si cambió, comprobamos unicidad
        if Materia.objects.filter(nombreMateria__iexact=nombre).exists():
            raise ValidationError("Ya existe una materia con ese nombre.")
        return nombre


class CohorteForm(forms.ModelForm):  
    estadoCohorte = forms.CharField(widget=forms.HiddenInput(), initial='ACTIVO')  

    class Meta:  
        model = Cohorte  
        fields = ['idCohorte', 'idFormacion', 'nombreCohorte', 'lapsoInscripcion', 'fechaInicio', 'fechaFin' ,'estadoCohorte']

class CargoForm(forms.ModelForm):  
    estadoCargo = forms.CharField(widget=forms.HiddenInput(), initial='ACTIVO')  

    class Meta:  
        model = Cargo  
        fields = ['nombreCargo', 'estadoCargo']

    def clean_nombreCargo(self):
        nombre = self.cleaned_data['nombreCargo'].strip()
        # Si es edición y no cambió, lo devolvemos directamente
        if self.instance.pk and nombre.lower() == self.instance.nombreCargo.lower():
            return nombre
        # Si cambió, comprobamos unicidad
        if Cargo.objects.filter(nombreCargo__iexact=nombre).exists():
            raise ValidationError("Ya existe un cargo con ese nombre.")
        return nombre


class RequisitoForm(forms.ModelForm):  
    estadoRequisito = forms.CharField(widget=forms.HiddenInput(), initial='ACTIVO')  

    class Meta:  
        model = Requisito  
        fields = ['idRequisito', 'nombreRequisito', 'estadoRequisito']  


class ServicioForm(forms.ModelForm):  
    estadoServicio = forms.CharField(widget=forms.HiddenInput(), initial='ACTIVO')  

    class Meta:  
        model = Servicio  
        fields = ['nombreServicio', 'tiempoServicio', 'precioServicio', 'estadoServicio'] 
    
    def clean_nombreServicio(self):
        nombre = self.cleaned_data['nombreServicio'].strip()
        # Si es edición y no cambió, lo devolvemos directamente
        if self.instance.pk and nombre.lower() == self.instance.nombreServicio.lower():
            return nombre
        # Si cambió, comprobamos unicidad
        if Servicio.objects.filter(nombreServicio__iexact=nombre).exists():
            raise ValidationError("Ya existe un servicio con ese nombre.")
        return nombre


class TramiteForm(forms.ModelForm):  
    estadoTramite = forms.CharField(widget=forms.HiddenInput(), initial='ACTIVO')  

    class Meta:  
        model = Tramite  
        fields = ['nombreTramite', 'diasTramite', 'precioTramite', 'estadoTramite']

    def clean_nombreTramite(self):
        nombre = self.cleaned_data['nombreTramite'].strip()
        # Si es edición y no cambió, lo devolvemos directamente
        if self.instance.pk and nombre.lower() == self.instance.nombreTramite.lower():
            return nombre
        # Si cambió, comprobamos unicidad
        if Tramite.objects.filter(nombreTramite__iexact=nombre).exists():
            raise ValidationError("Ya existe un tramite con ese nombre.")
        return nombre 

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

class ConfiguracionForm(forms.ModelForm):
    nombreInstitucion = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'form-control text-dark', 
            'placeholder': 'Ingrese el nombre de la institución', 
            'maxlength': 150
        })
    )
    rif = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'form-control text-dark', 
            'placeholder': 'Ej: J-12345678-9', 
            'maxlength': 15
        })
    )
    correoInstitucion = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'form-control text-dark', 
            'placeholder': 'contacto@institucion.com', 
            'maxlength': 254
        })
    )
    moneda = forms.ModelChoiceField(
        queryset=Moneda.objects.filter(estadoMoneda='ACTIVO'),
        widget=forms.Select(attrs={'class': 'form-control text-dark'}),
        empty_label="Seleccione una moneda..."
    )    
    idCuentaBanco = forms.ModelChoiceField(
        queryset=CuentaBanco.objects.all(),
        widget=forms.Select(attrs={
            'class': 'form-control text-dark',
            'placeholder': 'Seleccione una cuenta bancaria'
        }),
        empty_label="Seleccione una cuenta bancaria..."
    )

    cedulaCuenta = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'form-control text-dark', 
            'placeholder': 'Ej: V-12345678', 
            'maxlength': 20
        })
    )
    descuento = forms.DecimalField(
        max_digits=5, 
        decimal_places=2,
        widget=forms.NumberInput(attrs={
            'class': 'form-control text-dark', 
            'placeholder': '30', 
            'min': '0', 
            'max': '100', 
            'step': '0.01'
        }),
        label="Descuento (%)",
        required=True
    )
    logo = forms.ImageField(
        widget=forms.FileInput(attrs={
            'class': 'form-control-file text-dark', 
            'accept': 'image/*'
        }), 
        required=False
    )
    firma = forms.ImageField(
        widget=forms.FileInput(attrs={
            'class': 'form-control-file text-dark', 
            'accept': 'image/*'
        }), 
        required=False
    )

    class Meta:
        model = Configuracion
        fields = ['nombreInstitucion', 'rif', 'correoInstitucion', 'moneda', 'idCuentaBanco', 'cedulaCuenta', 'descuento', 'logo', 'firma']

    def __init__(self, *args, **kwargs):
        super(ConfiguracionForm, self).__init__(*args, **kwargs)
        self.fields['moneda'].queryset = Moneda.objects.filter(estadoMoneda='ACTIVO')
        
        # Solo requerir archivos para nuevas configuraciones
        if self.instance and self.instance.pk:
            self.fields['logo'].required = False
            self.fields['firma'].required = False
        else:
            self.fields['logo'].required = True
            self.fields['firma'].required = True

    def clean(self):
        cleaned_data = super().clean()
        instance = getattr(self, 'instance', None)
        
        # Mantener archivos existentes si no se suben nuevos
        if instance and instance.pk:
            if not cleaned_data.get('logo'):
                cleaned_data['logo'] = instance.logo
            if not cleaned_data.get('firma'):
                cleaned_data['firma'] = instance.firma
                
        return cleaned_data