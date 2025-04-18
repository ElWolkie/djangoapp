from django.db import models
from django.utils import timezone # Para la fecha
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin

class TipoPersona(models.Model):  
    idTP = models.AutoField(primary_key=True)  # Clave primaria para TipoPersona  
    nombreTP = models.CharField(max_length=100)  # Nombre del TipoPersona  
    estadoTP = models.CharField(max_length=10)  # Estado del TipoPersona  
    fechaTP = models.DateField(auto_now_add=True)  # Fecha de creación del TipoPersona  

    class Meta:  
        verbose_name = "Tipo de Persona"  
        verbose_name_plural = "Tipos de Personas"

    def __str__(self):
        return self.nombreTP  # Representación legible en el admin de Django


class Personas(models.Model):  
    idPersona = models.AutoField(primary_key=True)  # Clave primaria para Personas  
    cedula = models.CharField(max_length=10)  # Número de cedula  
    nombres = models.CharField(max_length=100)  # Nombres  
    apellidos = models.CharField(max_length=100)  # Apellidos
    telefono = models.CharField(max_length=15)  # Número de teléfono  
    correo = models.EmailField()  # Dirección de correo electrónicos 
    estadoPersona = models.CharField(max_length=10)  # Estado de la Persona  
    fechaPersona = models.DateField(auto_now_add=True)  # Fecha de creación de la Persona  

    class Meta:  
        verbose_name = "Persona"  
        verbose_name_plural = "Personas"  
        ordering = ['idPersona']  # Orden predeterminado por idPersona
        
    def __str__(self):
        return f"{self.nombres} {self.apellidos}"  # Representación legible en el admin de Django


class UsuarioManager(BaseUserManager):
    def create_user(self, idPersona, password=None, **extra_fields):
        """
        Crea y guarda un usuario con el idPersona y contraseña dados.
        """
        if not idPersona:
            raise ValueError('El idPersona es obligatorio')
        
        # Obtener la instancia de Personas
        try:
            persona = Personas.objects.get(pk=idPersona)
        except Personas.DoesNotExist:
            raise ValueError(f'No existe una Persona con idPersona={idPersona}')
        
        # Campos obligatorios para usuarios normales
        extra_fields.setdefault('preguntaSeguridad', 'pregunta_default')
        extra_fields.setdefault('respuestaSeguridad', 'respuesta_default')
        
        user = self.model(idPersona=persona, **extra_fields)
        
        # Establecer la contraseña usando el sistema de Django
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, idPersona, password=None, **extra_fields):
        """
        Crea y guarda un superusuario con el idPersona y contraseña dados.
        """
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('preguntaSeguridad', 'admin_seguridad') # Modificable
        extra_fields.setdefault('respuestaSeguridad', 'admin_respuesta') # Modificable

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self.create_user(idPersona, password, **extra_fields)

class Usuarios(AbstractBaseUser, PermissionsMixin):
    idUsuario = models.AutoField(primary_key=True)
    idPersona = models.OneToOneField('Personas', on_delete=models.CASCADE)
    preguntaSeguridad = models.CharField(max_length=255)
    respuestaSeguridad = models.CharField(max_length=255)
    coloresUsuario = models.CharField(max_length=50, blank=True, null=True)
    fechaUsuario = models.DateTimeField(auto_now_add=True)

    is_active = models.BooleanField(default=True) #Necesario para activo o inactivo
    is_staff = models.BooleanField(default=False)  # Necesario para admin
    is_superuser = models.BooleanField(default=False)  # Necesario para permisos de superusuario

    # class Meta:
    #     db_table = 'usuarios'  # Esto forzará el nombre de tabla exacto

    objects = UsuarioManager()

    USERNAME_FIELD = 'idPersona'
    REQUIRED_FIELDS = []

    def __str__(self):
        return f"{self.idPersona}"
    
    class Meta:
        verbose_name = 'Usuario'
        verbose_name_plural = 'Usuarios'
    
# Tabla intermedia para la relación muchos a muchos entre Personas y TipoPersona
class PersonaTP(models.Model):
    idPersona = models.ForeignKey(Personas, on_delete=models.CASCADE)  # Clave foránea a Personas
    idTP = models.ForeignKey(TipoPersona, on_delete=models.CASCADE)  # Clave foránea a TipoPersona
    fechaAsignacion = models.DateField(auto_now_add=True)  # Fecha de asignación del tipo a la persona

    class Meta:
        verbose_name = "Asignación de Tipo a Persona"
        verbose_name_plural = "Asignaciones de Tipos a Personas"
        unique_together = ('idPersona', 'idTP')  # Evita duplicados

    def __str__(self):
        return f"{self.idPersona} - {self.idTP}"  # Representación legible en el admin de Django


class TipoFormacion(models.Model):  
    idTF = models.AutoField(primary_key=True)  # Clave primaria para TipoFormacion  
    nombreTipoFormacion = models.CharField(max_length=100)  # Nombre del TipoFormacion  
    estadoTipoFormacion = models.CharField(max_length=10)  # Estado del TipoFormacion  
    cuotas= models.CharField(max_length=5) #Cantidad de Cuotas
    fechaTipoFormacion = models.DateField(auto_now_add=True)  # Fecha de creación del TipoFormacion  
    

    class Meta:  
        verbose_name = "TipoFormación"  
        verbose_name_plural = "TiposFormacion"  


class Formacion(models.Model):  
    idFormacion = models.AutoField(primary_key=True)  # Clave primaria para Formacion  
    idTF = models.ForeignKey(TipoFormacion, on_delete=models.CASCADE, related_name='formaciones')  # Clave foránea a TipoFormacion  
    nombreFormacion = models.CharField(max_length=100)  # Nombre de la Formación  
    duracion = models.CharField(max_length=100)  # Duración de la Formación  
    estadoFormacion = models.CharField(max_length=10)  # Estado de la Formación  
    fechaFormacion = models.DateField(auto_now_add=True)  # Fecha de creación de la Formación  

    class Meta:  
        verbose_name = "Formacion"  
        verbose_name_plural = "Formaciones"


class Materia(models.Model):  
    idMateria = models.AutoField(primary_key=True)  # Clave primaria para Materia  
    idFormacion = models.ForeignKey(Formacion, on_delete=models.CASCADE)  # Clave foránea a Ofertas  
    nombreMateria = models.CharField(max_length=100)  # Nombre de la Materia  
    estadoMateria = models.CharField(max_length=10)  # Estado de la Materia  
    fechaMateria = models.DateField(auto_now_add=True)  # Fecha de creación de la Materia  

    class Meta:  
        verbose_name = "Materia"  
        verbose_name_plural = "Materias"


class Cohorte(models.Model):  
    idCohorte = models.AutoField(primary_key=True)  # Clave primaria para Cohorte  
    nombreCohorte = models.CharField(max_length=100)  # Nombre de la Cohorte  
    estadoCohorte = models.CharField(max_length=10)  # Estado de la Cohorte  
    fechaCohorte = models.DateField(auto_now_add=True)  # Fecha de creación de la Cohorte  

    class Meta:  
        verbose_name = "Cohorte"  
        verbose_name_plural = "Cohortes"


class Cargo(models.Model):  
    idCargo = models.AutoField(primary_key=True)  # Clave primaria para Cargo  
    nombreCargo = models.CharField(max_length=100)  # Nombre del Cargo  
    estadoCargo = models.CharField(max_length=10)  # Estado del Cargo  
    fechaCargo = models.DateField(auto_now_add=True)  # Fecha de creación del Cargo  

    class Meta:  
        verbose_name = "Cargo"  
        verbose_name_plural = "Cargos"  


class Honorario(models.Model):  
    idHonorario = models.AutoField(primary_key=True)  # Clave primaria para Honorario  
    idPersona = models.ForeignKey(Personas, on_delete=models.CASCADE)  # Clave foránea a Personas  
    idCargo = models.ForeignKey(Cargo, on_delete=models.CASCADE)  # Clave foránea a Cargo  
    idCohorte = models.ForeignKey(Cohorte, on_delete=models.CASCADE)  # Clave foránea a Cohorte  
    idMateria = models.ForeignKey(Materia, on_delete=models.CASCADE)  # Clave foránea a Materia  
    horas = models.FloatField()  # Número de horas trabajadas  
    estadoHonorario = models.CharField(max_length=10)  # Estado del Honorario  
    fechaHonorario = models.DateField(auto_now_add=True)  # Fecha de creación del Honorario  

    class Meta:  
        verbose_name = "Honorario"  
        verbose_name_plural = "Honorarios"  


class Requisito(models.Model):  
    idRequisito = models.AutoField(primary_key=True)  # Clave primaria para Requisito  
    nombreRequisito = models.CharField(max_length=100)  # Nombre del Requisito  
    estadoRequisito = models.CharField(max_length=10)  # Estado del Requisito  
    fechaRequisito = models.DateField(auto_now_add=True)  # Fecha de creación del Requisito  

    class Meta:  
        verbose_name = "Requisito"  
        verbose_name_plural = "Requisitos"  


class Servicio(models.Model):  
    idServicio = models.AutoField(primary_key=True)  # Clave primaria para Servicios  
    nombreServicio = models.CharField(max_length=100)  # Nombre del Servicio  
    tiempoServicio = models.CharField(max_length=100)  # Duración del Servicio  
    precioServicio = models.CharField(max_length=100)  # Precio del Servicio  
    estadoServicio = models.CharField(max_length=10)  # Estado del Servicio  
    fechaServicio = models.DateField(auto_now_add=True)  # Fecha de creación del Servicio  
        
    class Meta:  
        verbose_name = "Servicio"  
        verbose_name_plural = "Servicios"  


class Tramite(models.Model):  
    idTramite = models.AutoField(primary_key=True)  # Clave primaria para Tramites  
    nombreTramite = models.CharField(max_length=100)  # Nombre del Tramite  
    diasTramite = models.CharField(max_length=100)  # Duración del Tramite  
    precioTramite = models.CharField(max_length=100)  # Precio del Tramite  
    estadoTramite = models.CharField(max_length=10)  # Estado del Tramite  
    fechaTramite = models.DateField(auto_now_add=True)  # Fecha de creación del Tramite  
        
    class Meta:  
        verbose_name = "Tramite"  
        verbose_name_plural = "Tramites"  

class Solicitud(models.Model):
    idSoli = models.AutoField(primary_key=True)  # Clave primaria para Solicitud
    idPersona = models.ForeignKey(Personas, on_delete=models.CASCADE)  # Clave foránea a Personas  
    idTramite = models.ForeignKey(Tramite, on_delete=models.CASCADE)  # Clave foránea a Tramite
    idServicio = models.ForeignKey(Servicio, on_delete=models.CASCADE)  # Clave foránea a Servicio
    montoTotal = models.DecimalField(max_digits=10, decimal_places=2)  # Monto total de la Solicitud
    estadoSolicitud = models.CharField(max_length=10)  # Estado de la Solicitud
    fechaEntrega = models.DateField()  # Fecha de entrega de la Solicitud
    fechaSolicitud = models.DateField(auto_now_add=True)  # Fecha de creación de la Solicitud

    class Meta:
        verbose_name = "Solicitud"
        verbose_name_plural = "Solicitudes"

class Denominacion(models.Model):  
    idDenominacion = models.AutoField(primary_key=True)  # Clave primaria para Denominacion  
    nombreDenominacion = models.CharField(max_length=100)  # Nombre del Denominacion  
    estadoDenominacion = models.CharField(max_length=10)  # Estado del Denominacion  
    fechaDenominacion = models.DateField(auto_now_add=True)  # Fecha de creación del Denominacion  

    class Meta:  
        verbose_name = "Denominacion"  
        verbose_name_plural = "Denominaciones"  


class Banco(models.Model):
    idBanco = models.AutoField(primary_key=True) # ID autoincremental
    nombreBanco = models.CharField(max_length=150, verbose_name="Nombre del Banco")
    codBanco = models.CharField(max_length=4, unique=True, db_index=True, verbose_name="Código SUDEBAN")
    # Código contable, por defecto '0000'
    codContable = models.CharField(max_length=10, default='0000', verbose_name="Código Contable")
    estadoBanco = models.CharField(max_length=10, default='ACTIVO', verbose_name="Estado")
    fechaBanco = models.DateField(default=timezone.now, verbose_name="Fecha Registro")

    class Meta:
        verbose_name = "Banco"
        verbose_name_plural = "Bancos"
        ordering = ['nombreBanco'] # Ordenar por nombre

    def __str__(self):
        return f"{self.nombreBanco} ({self.codBanco})"


class Moneda(models.Model):
    idMoneda = models.AutoField(primary_key=True)
    nombreMoneda = models.CharField(max_length=100)
    simboloMoneda = models.CharField(max_length=5, unique=True, db_index=True)
    estadoMoneda = models.CharField(max_length=10)
    fechaMoneda = models.DateField(auto_now_add=True)

    class Meta:
        verbose_name = "Moneda"
        verbose_name_plural = "Monedas"
        ordering = ['nombreMoneda']

    def __str__(self):
        return f"{self.nombreMoneda} ({self.simboloMoneda})"


class Tasa(models.Model):  
    idTasa = models.AutoField(primary_key=True)  # Clave primaria para Banco  
    idMoneda = models.ForeignKey(Moneda, on_delete=models.CASCADE)  # Clave foránea a Moneda  
    montoTasa = models.CharField(max_length=100)  # Codigo del Banco  
    estadoTasa = models.CharField(max_length=10)  # Estado del Banco  
    fechaTasa = models.DateTimeField(auto_now_add=True)  # Fecha y hora de creación del Banco  

    class Meta:  
        verbose_name = "Tasa"  
        verbose_name_plural = "Tasas"  


class TipoIngreso(models.Model):  
    idTipoIngreso = models.AutoField(primary_key=True)  # Clave primaria para TipoIngreso  
    nombreTipoIngreso = models.CharField(max_length=100)  # Nombre de la TipoIngreso  
    estadoTipoIngreso = models.CharField(max_length=10)  # Estado de la TipoIngreso  
    fechaTipoIngreso = models.DateField(auto_now_add=True)  # Fecha de creación de la TipoIngreso  

    class Meta:  
        verbose_name = "TipoIngreso"  
        verbose_name_plural = "TipoIngresos"  


class TipoMovimiento(models.Model):  
    idTipoMovimiento = models.AutoField(primary_key=True)  # Clave primaria para TipoIngreso  
    naturaleza = models.CharField(max_length=10)  # Nombre de la TipoIngreso  
    nombreTipoMovimiento = models.CharField(max_length=100)  # Nombre de la TipoIngreso  
    estadoTipoMovimiento = models.CharField(max_length=10)  # Estado de la TipoIngreso  
    fechaTipoMovimiento = models.DateField(auto_now_add=True)  # Fecha de creación de la TipoIngreso  

    class Meta:  
        verbose_name = "TipoMovimiento"  
        verbose_name_plural = "TipoMovimientos"  


class Movimiento(models.Model):  
    idMovimiento = models.AutoField(primary_key=True)  # Clave primaria para Ingreso  
    idTipoMovimiento = models.ForeignKey(TipoMovimiento, on_delete=models.CASCADE)  # Relación con TipoIngreso  
    idDenominacion = models.ForeignKey(Denominacion, on_delete=models.CASCADE)  # Relación con Denominacion  
    idBanco = models.ForeignKey(Banco, on_delete=models.CASCADE, null=True, blank=True)  # Banco opcional
    idTasa = models.ForeignKey(Tasa, on_delete=models.CASCADE)  # Relación con Tasa  
    naturaleza = models.CharField(max_length=10)  # NATURALEZA detallada del Ingreso  
    tipoPago = models.CharField(max_length=100)  # Tipo de pago del Ingreso  
    referencia = models.CharField(max_length=100, null=True, blank=True)  # Referencia opcional    idTasa = models.ForeignKey(Tasa, on_delete=models.CASCADE)  # Relación con Tasa  
    monto = models.DecimalField(max_digits=10, decimal_places=2)  # Monto del Ingreso  
    descripcion = models.TextField()  # Descripción detallada del Ingreso  
    estadoMovimiento = models.CharField(max_length=10)  # Estado del Ingreso (activo/inactivo)  
    fechaMovimiento = models.DateTimeField(auto_now_add=True)  # Fecha de registro del Ingreso  

    class Meta:  
        verbose_name = "Ingreso"  
        verbose_name_plural = "Ingresos"


class Configuracion(models.Model):
    idConfig = models.AutoField(primary_key=True, verbose_name="ID Configuración")
    nombreInstitucion = models.CharField(max_length=150, verbose_name="Nombre de la Institución")
    rif = models.CharField(max_length=15, verbose_name="RIF")
    correoInstitucion = models.EmailField(max_length=254, verbose_name="Correo Institucional")
    logo = models.ImageField(upload_to='configuracion/logos/', verbose_name="Logo Institucional")
    firma = models.ImageField(upload_to='configuracion/firmas/', verbose_name="Firma Autorizada")
    moneda = models.ForeignKey(Moneda, on_delete=models.PROTECT, verbose_name="Moneda Principal")
    fechaConfiguracion = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de Configuración")

    class Meta:
        verbose_name = "Configuración Institucional"
        verbose_name_plural = "Configuraciones Institucionales"
        ordering = ['-fechaConfiguracion']  # Ordenar por la más reciente primero

    def __str__(self):
        return f"{self.nombreInstitucion} (Últ. actualización: {self.fechaConfiguracion.strftime('%d/%m/%Y')})"
