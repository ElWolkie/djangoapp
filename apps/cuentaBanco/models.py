from django.db import models, IntegrityError
from django.db.models import Max
from apps.home.models import Moneda
from apps.planCuenta.models import PlanCuenta
from django.core.exceptions import ValidationError
import re

class Banco(models.Model):
    """
    Modelo que representa las instituciones bancarias con sus cuentas contables asociadas.
    """
    idBanco = models.AutoField(primary_key=True, verbose_name="ID Banco")
    nombreBanco = models.CharField(
        max_length=100,
        verbose_name="Nombre del Banco"
    )
    codLocalBanco = models.CharField(
        max_length=10,
        unique=True,
        verbose_name="Código Local"
    )
    codSwiftBanco = models.CharField(
        max_length=11,
        unique=True,
        verbose_name="Código SWIFT/BIC"
    )
    cuentaPadre = models.ForeignKey(
        PlanCuenta,
        on_delete=models.CASCADE,
        related_name="bancos_hijos",
        verbose_name="Cuenta Contable Padre"
    )
    codigoPlanCuenta = models.ForeignKey(
        PlanCuenta,
        on_delete=models.CASCADE,
        related_name="bancos",
        null=True,
        blank=True,
        verbose_name="Cuenta Contable Asociada"
    )
    estadoBanco = models.BooleanField(
        default=True,
        verbose_name="Activo"
    )
    fechaBanco = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Fecha de Registro"
    )

    class Meta:
        verbose_name = "Banco"
        verbose_name_plural = "Bancos"
        ordering = ['nombreBanco']

    def __str__(self):
        return self.nombreBanco

    def clean(self):
        """
        Validaciones en español para los campos del modelo Banco.
        Se lanzan ValidationError con mensajes en español.
        """
        errores = {}

        # nombreBanco: no vacío
        if not self.nombreBanco or not self.nombreBanco.strip():
            errores['nombreBanco'] = 'El nombre del banco no puede estar vacío.'

        # codSwiftBanco: obligatorio y formato SWIFT (8 u 11 caracteres alfanuméricos)
        if not self.codSwiftBanco or not self.codSwiftBanco.strip():
            errores['codSwiftBanco'] = 'El código SWIFT es obligatorio.'
        else:
            valor_swift = self.codSwiftBanco.strip().upper()
            if not re.fullmatch(r'^[A-Z0-9]{8}([A-Z0-9]{3})?$', valor_swift):
                errores['codSwiftBanco'] = 'El código SWIFT debe tener 8 u 11 caracteres alfanuméricos (A-Z, 0-9).'
            else:
                # Normalizar a mayúsculas
                self.codSwiftBanco = valor_swift

        # cuentaPadre: obligatoria
        if not self.cuentaPadre_id:
            errores['cuentaPadre'] = 'La cuenta contable padre es obligatoria.'
        else:
            # Comprobar que la cuenta padre tenga un nivel válido (ejemplo: no nivel negativo)
            try:
                nivel_padre = self.cuentaPadre.nivelPlanCuenta
                if nivel_padre is None:
                    errores['cuentaPadre'] = 'La cuenta padre debe tener definido el nivel.'
                elif nivel_padre < 0:
                    errores['cuentaPadre'] = 'Nivel de la cuenta padre inválido.'
            except Exception:
                # Si por alguna razón no se puede leer, dejar que sea validado en la base
                pass

        # Si ya hay una cuenta contable asociada, validar que su cuenta padre coincida con cuentaPadre
        if self.codigoPlanCuenta_id and self.cuentaPadre_id:
            try:
                if getattr(self.codigoPlanCuenta, 'cuentaPadre_id', None) != self.cuentaPadre_id:
                    errores['codigoPlanCuenta'] = 'La cuenta contable asociada debe ser hija de la cuenta padre seleccionada.'
            except Exception:
                # Evitar fallos si el objeto relacionado no está cargado; en ese caso, no validar aquí.
                pass

        # Validaciones de unicidad para mensajes en español (evitar errores de BD por duplicados)
        if self.codLocalBanco:
            qs_local = self.__class__.objects.filter(codLocalBanco__iexact=self.codLocalBanco)
            if self.pk:
                qs_local = qs_local.exclude(pk=self.pk)
            if qs_local.exists():
                errores['codLocalBanco'] = 'Ya existe un banco con ese código local.'

        if self.codSwiftBanco:
            qs_swift = self.__class__.objects.filter(codSwiftBanco__iexact=self.codSwiftBanco)
            if self.pk:
                qs_swift = qs_swift.exclude(pk=self.pk)
            if qs_swift.exists():
                errores['codSwiftBanco'] = 'Ya existe un banco con ese código SWIFT/BIC.'

        if errores:
            raise ValidationError(errores)

    def save(self, *args, **kwargs):
        """
        Genera automáticamente la cuenta contable asociada al banco si no existe.
        Ejecuta validaciones (mensajes en español) antes de guardar.
        """
        # Ejecutar validaciones explícitas para asegurar mensajes en español y normalizaciones
        self.full_clean()

        # Asignar automáticamente el tipo de cuenta basado en la cuenta padre
        tipo_cuenta_padre = self.cuentaPadre.tipoPlanCuenta
        naturaleza_cuenta_padre = self.cuentaPadre.naturalezaPlanCuenta

        if not self.codigoPlanCuenta:
            # Crear subcuenta para este banco específico
            new_code = self._generate_bank_account_code(self.cuentaPadre)
            try:
                plan_cuenta = PlanCuenta.objects.create(
                    codigoPlanCuenta=new_code,
                    nombrePlanCuenta=f"{self.nombreBanco} ({tipo_cuenta_padre})",
                    tipoPlanCuenta=tipo_cuenta_padre,
                    naturalezaPlanCuenta=naturaleza_cuenta_padre,
                    nivelPlanCuenta=self.cuentaPadre.nivelPlanCuenta + 1,
                    cuentaPadre=self.cuentaPadre
                )
            except IntegrityError as e:
                # Convertir error de BD por duplicado en ValidationError con mensaje en español
                raise ValidationError({'codigoPlanCuenta': 'No se pudo crear la cuenta contable asociada (código duplicado en la base de datos).'})
            self.codigoPlanCuenta = plan_cuenta

        try:
            super().save(*args, **kwargs)
        except IntegrityError as e:
            # Mensaje genérico en español para duplicados en campos únicos
            raise ValidationError({'__all__': 'Error al guardar Banco: posible duplicado en un campo único.'})

    def _generate_bank_account_code(self, cuenta_padre):
        """Genera el código para la cuenta específica del banco respetando la jerarquía del plan contable"""
        last_account = PlanCuenta.objects.filter(
            cuentaPadre=cuenta_padre
        ).aggregate(Max('codigoPlanCuenta'))

        max_code = last_account.get('codigoPlanCuenta__max')
        if max_code:
            # Extraer la parte correspondiente al nivel actual
            base_code = cuenta_padre.codigoPlanCuenta
            suffix_length = len(max_code) - len(base_code)
            if suffix_length > 0:
                last_suffix = int(max_code[-suffix_length:])
                next_suffix = f"{last_suffix + 1:0{suffix_length}d}"
                new_code = f"{base_code}{next_suffix}"
            else:
                new_code = f"{base_code}01"
        else:
            new_code = f"{cuenta_padre.codigoPlanCuenta}01"

        # Validar unicidad del código generado
        while PlanCuenta.objects.filter(codigoPlanCuenta=new_code).exists():
            match = re.search(r'(\\d+)$', new_code)
            if match:
                num = int(match.group(1)) + 1
                width = len(match.group(1))
                new_code = f"{cuenta_padre.codigoPlanCuenta}{num:0{width}d}"
            else:
                new_code = f"{cuenta_padre.codigoPlanCuenta}01"

        return new_code

class CuentaBanco(models.Model):
    """
    Modelo que representa las cuentas bancarias específicas con sus productos asociados.
    """
    TIPO_PRODUCTO_CHOICES = [
        ('corriente', 'Cuenta Corriente'),
        ('ahorro', 'Cuenta de Ahorro'),
        ('plazo_fijo', 'Depósito a Plazo Fijo'),
        ('prestamo', 'Préstamo'),
        ('credito', 'Línea de Crédito'),
        ('inversion', 'Fondo de Inversión'),
    ]
    
    idCuentaBanco = models.AutoField(primary_key=True, verbose_name="ID Cuenta Bancaria")
    banco = models.ForeignKey(
        Banco,
        on_delete=models.CASCADE,
        verbose_name="Banco"
    )
    planCuenta = models.ForeignKey(
        PlanCuenta,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        verbose_name="Cuenta Contable Asociada"
    )
    numeroCuentaBanco = models.CharField(
        max_length=20,
        unique=True,
        verbose_name="Número de Cuenta"
    )
    moneda = models.ForeignKey(
        Moneda,
        on_delete=models.CASCADE,
        verbose_name="Moneda"
    )
    tipoProducto = models.CharField(
        max_length=20,
        choices=TIPO_PRODUCTO_CHOICES,
        default='corriente',
        verbose_name="Tipo de Producto"
    )
    fechaApertura = models.DateField(verbose_name="Fecha de Apertura")
    saldoDisponible = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0,
        verbose_name="Saldo Disponible"
    )
    fechaRegistro = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Fecha de Registro"
    )
    fechaActualizacion = models.DateTimeField(
        auto_now=True,
        verbose_name="Última Actualización"
    )
    estado = models.BooleanField(
        default=True,
        verbose_name="Activa"
    )

    class Meta:
        verbose_name = "Cuenta Bancaria"
        verbose_name_plural = "Cuentas Bancarias"
        ordering = ['banco__nombreBanco', 'numeroCuentaBanco']

    def __str__(self):
        return f"{self.numeroCuentaBanco} - {self.banco.nombreBanco} ({self.get_tipoProducto_display()})"
    
    def save(self, *args, **kwargs):
        """
        Genera automáticamente la cuenta contable asociada a la cuenta bancaria.
        La cuenta contable será hija directa de la cuenta contable del banco.
        """
        if not self.planCuenta_id:
            # Crear subcuenta para esta cuenta específica, hija directa del banco
            new_code = self._generate_account_code(self.banco.codigoPlanCuenta)
            plan_cuenta = PlanCuenta.objects.create(
                codigoPlanCuenta=new_code,
                nombrePlanCuenta=f"{self.get_tipoProducto_display()} {self.numeroCuentaBanco}",
                tipoPlanCuenta=self.banco.codigoPlanCuenta.tipoPlanCuenta,
                naturalezaPlanCuenta=self.banco.codigoPlanCuenta.naturalezaPlanCuenta,  # La naturaleza se hereda de la cuenta padre
                nivelPlanCuenta=self.banco.codigoPlanCuenta.nivelPlanCuenta + 1,
                cuentaPadre=self.banco.codigoPlanCuenta
            )
            self.planCuenta = plan_cuenta

        super().save(*args, **kwargs)

    def _generate_account_code(self, cuenta_padre):
        """Genera código para la cuenta bancaria específica respetando la jerarquía del plan contable"""
        try:
            last_account = PlanCuenta.objects.filter(
                cuentaPadre=cuenta_padre
            ).aggregate(Max('codigoPlanCuenta'))

            if last_account['codigoPlanCuenta__max']:
                base_code = cuenta_padre.codigoPlanCuenta
                suffix_length = len(last_account['codigoPlanCuenta__max']) - len(base_code)
                if suffix_length > 0:
                    last_suffix = int(last_account['codigoPlanCuenta__max'][-suffix_length:])
                    next_suffix = f"{last_suffix + 1:0{suffix_length}d}"
                    new_code = f"{base_code}{next_suffix}"
                else:
                    new_code = f"{base_code}01"
            else:
                new_code = f"{cuenta_padre.codigoPlanCuenta}01"

            # Validar unicidad del código generado
            while PlanCuenta.objects.filter(codigoPlanCuenta=new_code).exists():
                match = re.search(r'(\\d+)$', new_code)
                if match:
                    num = int(match.group(1)) + 1
                    width = len(match.group(1))
                    new_code = f"{cuenta_padre.codigoPlanCuenta}{num:0{width}d}"
                else:
                    new_code = f"{cuenta_padre.codigoPlanCuenta}01"

            return new_code
        except Exception as e:
            print(f"[ERROR] Error al generar el código de cuenta bancaria: {e}")
            raise
