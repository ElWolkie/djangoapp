from django.db import models  
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager

# from django.contrib.auth.models import User    COMENTADO POR SI SE NECESITA USAR

class UsuarioManager(BaseUserManager):
    def create_user(self, idPersona, contrasenia, **extra_fields):
        if not idPersona:
            raise ValueError('El campo idPersona es obligatorio')
        user = self.model(idPersona=idPersona, **extra_fields)
        user.set_password(contrasenia)
        user.save(using=self._db)
        return user

    def create_superuser(self, idPersona, contrasenia, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('El superusuario debe tener is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('El superusuario debe tener is_superuser=True.')

        return self.create_user(idPersona, contrasenia, **extra_fields)

class Usuario(AbstractBaseUser):
    idUsuario = models.AutoField(primary_key=True)
    idPersona = models.OneToOneField('Personas', on_delete=models.CASCADE, related_name='usuario')
    contrasenia = models.CharField(max_length=128)  # Usaremos AbstractBaseUser para manejo de contraseñas
    preguntaSeguridad = models.CharField(max_length=255)
    respuestaSeguridad = models.CharField(max_length=255)
    coloresUsuario = models.CharField(max_length=50, blank=True, null=True)
    estadoUsuario = models.BooleanField(default=True)
    fechaUsuario = models.DateTimeField(auto_now_add=True)

    # Campos adicionales para roles/administración
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)

    # Administrador de usuarios
    objects = UsuarioManager()

    # Campo que se usará como identificador único
    USERNAME_FIELD = 'idPersona'  # Autenticación con idPersona
    REQUIRED_FIELDS = []  # No requerimos otros campos obligatorios además de USERNAME_FIELD

    def __str__(self):
        return f"Usuario {self.idUsuario} - Persona: {self.idPersona}"

    def has_perm(self, perm, obj=None):
        return True

    def has_module_perms(self, app_label):
        return True


class TipoPersona(models.Model):  
    idTP = models.AutoField(primary_key=True)  # Clave primaria para TipoPersona  
    nombreTP = models.CharField(max_length=100)  # Nombre del TipoPersona  
    estadoTP = models.CharField(max_length=10)  # Estado del TipoPersona  
    fechaTP = models.DateField(auto_now_add=True)  # Fecha de creación del TipoPersona  

    class Meta:  
        verbose_name = "Tipo de Persona"  
        verbose_name_plural = "Tipos de Personas"  


class Personas(models.Model):  
    idPersona = models.AutoField(primary_key=True)  # Clave primaria para Personas  
    idTP = models.ForeignKey(TipoPersona, on_delete=models.CASCADE)  # Clave foránea a TipoPersona  
    cedula = models.CharField(max_length=10)  # Número de identificación  
    nombres = models.CharField(max_length=100)  # Nombres  
    apellidos = models.CharField(max_length=100)  # Apellidos  
    telefono = models.CharField(max_length=15)  # Número de teléfono  
    correo = models.EmailField()  # Dirección de correo electrónico  
    estadoPersona = models.CharField(max_length=10)  # Estado de la Persona  
    fechaPersona = models.DateField(auto_now_add=True)  # Fecha de creación de la Persona  

    class Meta:  
        verbose_name = "Persona"  
        verbose_name_plural = "Personas"  
        ordering = ['idTP']  # Orden predeterminado por TipoPersona  


class Cuota(models.Model):  
    idCuota = models.AutoField(primary_key=True)  # Clave primaria para Cuota  
    nombreCuota = models.CharField(max_length=100)  # Nombre de la Cuota  
    estadoCuota = models.CharField(max_length=10)  # Estado de la Cuota  
    fechaCuota = models.DateField(auto_now_add=True)  # Fecha de creación de la Cuota  

    class Meta:  
        verbose_name = "Cuota"  
        verbose_name_plural = "Cuotas"  


class TipoOferta(models.Model):  
    idTipoOferta = models.AutoField(primary_key=True)  # Clave primaria para TipoOferta  
    idCuota = models.ForeignKey(Cuota, on_delete=models.CASCADE)  # Clave foránea a Cuota  
    nombreTipoOferta = models.CharField(max_length=100)  # Nombre del TipoOferta  
    estadoTipoOferta = models.CharField(max_length=10)  # Estado del TipoOferta  
    fechaTipoOferta = models.DateField(auto_now_add=True)  # Fecha de creación del TipoOferta  

    class Meta:  
        verbose_name = "Tipo de Oferta"  
        verbose_name_plural = "Tipos de Ofertas"  


class Ofertas(models.Model):  
    idOferta = models.AutoField(primary_key=True)  # Clave primaria para Ofertas  
    idTipoOferta = models.ForeignKey(TipoOferta, on_delete=models.CASCADE)  # Clave foránea a TipoOferta  
    nombreOferta = models.CharField(max_length=100)  # Nombre de la Oferta  
    duracion = models.CharField(max_length=100)  # Duración de la Oferta  
    estadoOferta = models.CharField(max_length=10)  # Estado de la Oferta  
    fechaOferta = models.DateField(auto_now_add=True)  # Fecha de creación de la Oferta  

    class Meta:  
        verbose_name = "Oferta"  
        verbose_name_plural = "Ofertas"  


class Materia(models.Model):  
    idMateria = models.AutoField(primary_key=True)  # Clave primaria para Materia  
    idOferta = models.ForeignKey(Ofertas, on_delete=models.CASCADE)  # Clave foránea a Ofertas  
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


class Contrato(models.Model):  
    idContrato = models.AutoField(primary_key=True)  # Clave primaria para Contrato  
    idPersona = models.ForeignKey(Personas, on_delete=models.CASCADE)  # Clave foránea a Personas  
    idCargo = models.ForeignKey(Cargo, on_delete=models.CASCADE)  # Clave foránea a Cargo  
    idCohorte = models.ForeignKey(Cohorte, on_delete=models.CASCADE)  # Clave foránea a Cohorte  
    idMateria = models.ForeignKey(Materia, on_delete=models.CASCADE)  # Clave foránea a Materia  
    estadoContrato = models.CharField(max_length=10)  # Estado del Contrato  
    fechaContrato = models.DateField(auto_now_add=True)  # Fecha de creación del Contrato  

    class Meta:  
        verbose_name = "Contrato"  
        verbose_name_plural = "Contratos"  


class Honorario(models.Model):  
    idHonorario = models.AutoField(primary_key=True)  # Clave primaria para Honorario  
    idContrato = models.ForeignKey(Contrato, on_delete=models.CASCADE)  # Clave foránea a Contrato  
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
    idBanco = models.AutoField(primary_key=True)  # Clave primaria para Banco  
    nombreBanco = models.CharField(max_length=100)  # Nombre del Banco  
    codBanco = models.CharField(max_length=100)  # Codigo del Banco  
    codContable = models.CharField(max_length=100)  # Codigo contable del Banco  
    estadoBanco = models.CharField(max_length=10)  # Estado del Banco  
    fechaBanco = models.DateField(auto_now_add=True)  # Fecha de creación del Banco  

    class Meta:  
        verbose_name = "Banco"  
        verbose_name_plural = "Bancos"  

class Moneda(models.Model):  
    idMoneda = models.AutoField(primary_key=True)  # Clave primaria para Moneda  
    nombreMoneda = models.CharField(max_length=100)  # Nombre del Moneda  
    simboloMoneda = models.CharField(max_length=5)  # Codigo del Moneda  
    estadoMoneda = models.CharField(max_length=10)  # Estado del Moneda  
    fechaMoneda = models.DateField(auto_now_add=True)  # Fecha de creación del Moneda  

    class Meta:  
        verbose_name = "Moneda"  
        verbose_name_plural = "Monedas"  


class Tasa(models.Model):  
    idTasa = models.AutoField(primary_key=True)  # Clave primaria para Banco  
    idMoneda = models.ForeignKey(Moneda, on_delete=models.CASCADE)  # Clave foránea a Moneda  
    montoTasa = models.CharField(max_length=100)  # Codigo del Banco  
    estadoTasa = models.CharField(max_length=10)  # Estado del Banco  
    fechaTasa = models.DateField(auto_now_add=True)  # Fecha de creación del Banco  

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

class TipoEgreso(models.Model):  
    idTipoEgreso = models.AutoField(primary_key=True)  # Clave primaria para TipoIngreso  
    nombreTipoEgreso = models.CharField(max_length=100)  # Nombre de la TipoIngreso  
    estadoTipoEgreso = models.CharField(max_length=10)  # Estado de la TipoIngreso  
    fechaTipoEgreso = models.DateField(auto_now_add=True)  # Fecha de creación de la TipoIngreso  

    class Meta:  
        verbose_name = "TipoEgreso"  
        verbose_name_plural = "TipoEgresos"  