from django.db import models
from django.utils import timezone # Para la fecha
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin, Group
from django.core.exceptions import ValidationError
from apps.persona.models import Personas

class UsuarioManager(BaseUserManager):
    def create_user(self, idPersona, password=None, **extra_fields):
        if not idPersona:
            raise ValueError('El idPersona es obligatorio')
        
        try:
            persona = Personas.objects.get(pk=idPersona)
        except Personas.DoesNotExist:
            raise ValueError(f'No existe una Persona con idPersona={idPersona}')
        
        extra_fields.setdefault('preguntaSeguridad', 'pregunta_default')
        extra_fields.setdefault('respuestaSeguridad', 'respuesta_default')
        
        user = self.model(idPersona=persona, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, idPersona, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('preguntaSeguridad', 'admin_seguridad')
        extra_fields.setdefault('respuestaSeguridad', 'admin_respuesta')

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self.create_user(idPersona, password, **extra_fields)

class Usuarios(AbstractBaseUser, PermissionsMixin):
    idUsuario = models.AutoField(primary_key=True)
    idPersona = models.OneToOneField(Personas, on_delete=models.CASCADE, related_name='usuario')
    preguntaSeguridad = models.CharField(max_length=255)
    respuestaSeguridad = models.CharField(max_length=255)
    coloresUsuario = models.CharField(max_length=50, blank=True, null=True)
    fechaUsuario = models.DateTimeField(auto_now_add=True)

    is_active = models.BooleanField(default=True) #Necesario para activo o inactivo
    is_staff = models.BooleanField(default=False)  # Necesario para admin
    is_superuser = models.BooleanField(default=False)  # Necesario para permisos de superusuario

    groups = models.ManyToManyField(
        Group,
        verbose_name="Grupos",
        blank=True,
        related_name="usuarios_grupos",
        help_text="Grupos a los que pertenece el usuario.",
    )
    user_permissions = models.ManyToManyField(
        "auth.Permission",
        verbose_name="Permisos de usuario",
        blank=True,
        related_name="usuarios_set",
        related_query_name="usuario",
    )

    @property
    def eliminado(self):
        return not self.is_active

    objects = UsuarioManager()

    USERNAME_FIELD = 'idPersona'
    REQUIRED_FIELDS = []

    def __str__(self):
        return f"{self.idPersona}"
    
    class Meta:
        verbose_name = 'Usuario'
        verbose_name_plural = 'Usuarios'

class TipoFormacion(models.Model):  
    idTF = models.AutoField(primary_key=True)
    nombreTipoFormacion = models.CharField(max_length=100, unique=True)
    estadoTipoFormacion = models.CharField(max_length=10)
    fechaTipoFormacion = models.DateField(auto_now_add=True)

    def clean(self):
        qs = TipoFormacion.objects.filter(nombreTipoFormacion__iexact=self.nombreTipoFormacion)
        if self.pk:
            qs = qs.exclude(pk=self.pk)
        if qs.exists():
            raise ValidationError("El nombre del Tipo Formación ya existe.")

    class Meta:  
        verbose_name = "TipoFormación"  
        verbose_name_plural = "TiposFormacion"

class Formacion(models.Model):  
    idFormacion = models.AutoField(primary_key=True)
    idTF = models.ForeignKey(TipoFormacion, on_delete=models.CASCADE, related_name='formaciones')
    nombreFormacion = models.CharField(max_length=100, unique=True)
    valorInscripcion = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Valor de Inscripción", default=0)
    tieneCuotas = models.BooleanField(default=False, verbose_name="Tiene sistema de cuotas?")
    duracion = models.CharField(max_length=100)
    estadoFormacion = models.CharField(max_length=10)
    fechaFormacion = models.DateField(auto_now_add=True)

    class Meta:  
        verbose_name = "Formacion"  
        verbose_name_plural = "Formaciones"


class CuotaFormacion(models.Model):
    TIPOS_CUOTA = [
        ('MENSUAL', 'Mensual'),
        ('BIMESTRAL', 'Bimestral'),
        ('TRIMESTRAL', 'Trimestral'),
        ('SEMESTRAL', 'Semestral'),
        ('ANUAL', 'Anual'),
        ('UNICA', 'Única'),
    ]
    
    idCuota = models.AutoField(primary_key=True)
    idFormacion = models.ForeignKey(Formacion, on_delete=models.CASCADE, related_name='cuotas')
    nombreCuota = models.CharField(max_length=100)
    tipoCuota = models.CharField(max_length=20, choices=TIPOS_CUOTA)
    valorCuota = models.DecimalField(max_digits=10, decimal_places=2)
    orden = models.PositiveIntegerField(help_text="Orden en que se deben pagar las cuotas")
    fechaCuota = models.DateField(null=True, blank=True, auto_now_add=True)
    is_active = models.BooleanField(default=True)

    def clean(self):
        # La lógica de validación está bien, no se necesita cambiar.
        qs = CuotaFormacion.objects.filter(
            idFormacion=self.idFormacion,
            nombreCuota__iexact=self.nombreCuota,
            tipoCuota=self.tipoCuota,
            orden=self.orden
        )
        if self.pk:
            qs = qs.exclude(pk=self.pk)
        if qs.exists():
            raise ValidationError("Ya existe una cuota con el mismo idFormacion, nombreCuota, tipoCuota y orden.")
    
    class Meta:
        verbose_name = "Cuota de Formación"
        verbose_name_plural = "Cuotas de Formación"
        ordering = ['idFormacion', 'orden']
    
    def __str__(self):
        return f"{self.nombreCuota} - {self.get_tipoCuota_display()} - ${self.valorCuota}"


class Materia(models.Model):  
    idMateria = models.AutoField(primary_key=True)
    idFormacion = models.ForeignKey(Formacion, on_delete=models.CASCADE)
    nombreMateria = models.CharField(max_length=100, unique=True)
    estadoMateria = models.CharField(max_length=10)
    fechaMateria = models.DateField(auto_now_add=True)

    class Meta:  
        verbose_name = "Materia"  
        verbose_name_plural = "Materias"

class Cohorte(models.Model):  
    idCohorte = models.AutoField(primary_key=True)
    idFormacion = models.ForeignKey(Formacion, on_delete=models.PROTECT, related_name='cohortes')
    nombreCohorte = models.CharField(max_length=100)
    lapsoInscripcion = models.PositiveSmallIntegerField(verbose_name="Lapso de inscripción")
    fechaInicio = models.DateField()
    fechaFin = models.DateField()
    estadoCohorte = models.CharField(max_length=10, db_index=True)
    fechaCohorte = models.DateField(auto_now_add=True, db_index=True)

    def clean(self):
        # Nombre único sólo dentro de la misma formación
        qs = Cohorte.objects.filter(idFormacion=self.idFormacion, nombreCohorte__iexact=self.nombreCohorte)
        if self.pk:
            qs = qs.exclude(pk=self.pk)
        if qs.exists():
            raise ValidationError("El nombre de la Cohorte ya existe para esta formación.")

        # Fecha inicio debe ser <= fecha fin
        if self.fechaInicio and self.fechaFin and self.fechaInicio > self.fechaFin:
            raise ValidationError("La fecha de inicio debe ser anterior o igual a la fecha de fin.")

        # No permitir cohortes con fechas solapadas o iguales dentro de la misma formación
        if self.fechaInicio and self.fechaFin:
            overlapping = Cohorte.objects.filter(
                idFormacion=self.idFormacion,
                fechaInicio__lte=self.fechaFin,
                fechaFin__gte=self.fechaInicio
            )
            if self.pk:
                overlapping = overlapping.exclude(pk=self.pk)
            if overlapping.exists():
                raise ValidationError("Ya existe una cohorte para esta formación con fechas solapadas o iguales.")

    @classmethod
    def deactivate_expired_cohortes(cls):
        """
        Actualiza el estado de cohortes según fechas:

        - Marca como 'INACTIVO' todas las cohortes con estado 'ACTIVO' cuya fechaFin
        sea anterior a la fecha de hoy.
        - Marca como 'INACTIVO' también las cohortes con estado 'ACTIVO' cuya fechaInicio
        sea después de la fecha de hoy (cohortes que aún no deben iniciarse).
        - Marca como 'ACTIVO' todas las cohortes con estado 'INACTIVO' cuya fechaInicio
        sea igual o anterior a la fecha de hoy y cuya fechaFin no haya pasado.

        Devuelve un dict con los conteos de registros actualizados para cada caso.
        """
        today = timezone.localdate()

        # Cohortes activas que ya terminaron -> inactivar
        expired_by_end_qs = cls.objects.filter(estadoCohorte__iexact='ACTIVO', fechaFin__lt=today)
        expired_by_end_count = expired_by_end_qs.update(estadoCohorte='INACTIVO')

        # Cohortes activas cuya fechaInicio es en el futuro -> inactivar (aún no comienzan)
        future_start_active_qs = cls.objects.filter(estadoCohorte__iexact='ACTIVO', fechaInicio__gt=today)
        future_start_active_count = future_start_active_qs.update(estadoCohorte='INACTIVO')

        # Cohortes inactivas cuya fechaInicio es hoy o anterior y fechaFin no ha pasado -> activar
        activate_by_start_qs = cls.objects.filter(
            estadoCohorte__iexact='INACTIVO',
            fechaInicio__lte=today,
            fechaFin__gte=today  # Asegurarse de que la cohorte no haya terminado
        )
        activated_count = activate_by_start_qs.update(estadoCohorte='ACTIVO')
        print(f"Inactivated by end: {expired_by_end_count}")
        print(f"Inactivated by future start: {future_start_active_count}")
        print(f"Activated by start: {activated_count}")
        total = expired_by_end_count + future_start_active_count + activated_count
        print(f"Total updated: {total}")
        return {
            'inactivated_by_end': expired_by_end_count,
            'inactivated_by_future_start': future_start_active_count,
            'activated_by_start': activated_count,
            'total_updated': expired_by_end_count + future_start_active_count + activated_count
        }
    class Meta:  
        verbose_name = "Cohorte"  
        verbose_name_plural = "Cohortes"

class Cargo(models.Model):  
    idCargo = models.AutoField(primary_key=True)
    nombreCargo = models.CharField(max_length=100, unique=True)
    estadoCargo = models.CharField(max_length=10)
    fechaCargo = models.DateField(auto_now_add=True)

    class Meta:  
        verbose_name = "Cargo"  
        verbose_name_plural = "Cargos"

class Requisito(models.Model):  
    idRequisito = models.AutoField(primary_key=True)
    nombreRequisito = models.CharField(max_length=100, unique=True)
    app = models.BooleanField(default=False)
    estadoRequisito = models.CharField(max_length=10)
    fechaRequisito = models.DateField(auto_now_add=True)

    def clean(self):
        qs = Requisito.objects.filter(nombreRequisito__iexact=self.nombreRequisito)
        if self.pk:
            qs = qs.exclude(pk=self.pk)
        if qs.exists():
            raise ValidationError("El nombre del Requisito ya existe.")

    class Meta:  
        verbose_name = "Requisito"  
        verbose_name_plural = "Requisitos"

class Servicio(models.Model):  
    idServicio = models.AutoField(primary_key=True)
    nombreServicio = models.CharField(max_length=100, unique=True)
    tiempoServicio = models.CharField(max_length=100)
    precioServicio = models.CharField(max_length=100)
    estadoServicio = models.CharField(max_length=10, db_index=True)
    fechaServicio = models.DateField(auto_now_add=True, db_index=True)

    class Meta:  
        verbose_name = "Servicio"
        verbose_name_plural = "Servicios"
    
    class Meta:
        indexes = [
            models.Index(fields=['estadoServicio', 'nombreServicio']),
        ]

    @property
    def solicitudes(self):
        return self.solicitud_set.count()

class Tramite(models.Model):  
    idTramite = models.AutoField(primary_key=True)
    nombreTramite = models.CharField(max_length=100, unique=True)
    diasTramite = models.CharField(max_length=100)
    precioTramite = models.CharField(max_length=100)
    estadoTramite = models.CharField(max_length=10)
    fechaTramite = models.DateField(auto_now_add=True)

    class Meta:  
        verbose_name = "Tramite"  
        verbose_name_plural = "Tramites"

class Moneda(models.Model):
    idMoneda = models.AutoField(primary_key=True)
    nombreMoneda = models.CharField(max_length=100, unique=True)
    simboloMoneda = models.CharField(max_length=5, unique=True, db_index=True)
    estadoMoneda = models.CharField(max_length=10)
    fechaMoneda = models.DateField(auto_now_add=True)

    def clean(self):
        qs = Moneda.objects.filter(nombreMoneda__iexact=self.nombreMoneda)
        if self.pk:
            qs = qs.exclude(pk=self.pk)
        if qs.exists():
            raise ValidationError("El nombre de la Moneda ya existe.")

    class Meta:
        verbose_name = "Moneda"
        verbose_name_plural = "Monedas"
        ordering = ['nombreMoneda']

    def __str__(self):
        return f"{self.nombreMoneda} ({self.simboloMoneda})"

class Tasa(models.Model):  
    idTasa = models.AutoField(primary_key=True)
    idMoneda = models.ForeignKey(Moneda, on_delete=models.CASCADE, related_name='tasas')  # ← Nombre personalizado)
    montoTasa = models.CharField(max_length=100)
    estadoTasa = models.CharField(max_length=10)
    fechaTasa = models.DateTimeField(auto_now_add=True)

    class Meta:  
        verbose_name = "Tasa"  
        verbose_name_plural = "Tasas"

    def clean(self):
        qs = Tasa.objects.filter(idMoneda=self.idMoneda, montoTasa=self.montoTasa, fechaTasa=self.fechaTasa)
        if self.pk:
            qs = qs.exclude(pk=self.pk)
        if qs.exists():
            raise ValidationError("Ya existe una tasa con la misma moneda, monto y fecha/hora.")

class Configuracion(models.Model):
    idConfig = models.AutoField(primary_key=True, verbose_name="ID Configuración")
    nombreInstitucion = models.CharField(max_length=150, unique=True, verbose_name="Nombre de la Institución")
    rif = models.CharField(max_length=15, verbose_name="RIF")
    correoInstitucion = models.EmailField(max_length=254, verbose_name="Correo Institucional")
    logo = models.ImageField(upload_to='configuracion/logos/', verbose_name="Logo Institucional")
    firma = models.ImageField(upload_to='configuracion/firmas/', verbose_name="Firma Autorizada")
    moneda = models.ForeignKey(Moneda, on_delete=models.PROTECT, verbose_name="Moneda Principal")
    descuento = models.DecimalField(max_digits=5, decimal_places=2, default=0, verbose_name="Descuento (%)")
    idCuentaBanco = models.ForeignKey(
        'cuentaBanco.CuentaBanco',  # Usar cadena para evitar el ciclo de importación
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        verbose_name="Cuenta Bancaria Asociada"
    )
    cedulaCuenta = models.CharField(max_length=20, verbose_name="Cédula de la Cuenta")
    fechaConfiguracion = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de Configuración")

    class Meta:
        verbose_name = "Configuración Institucional"
        verbose_name_plural = "Configuraciones Institucionales"
        ordering = ['-fechaConfiguracion']

    def __str__(self):
        return f"{self.nombreInstitucion} (Últ. actualización: {self.fechaConfiguracion.strftime('%d/%m/%Y')})"
