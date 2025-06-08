from django.db import models
from django.db.models import Max
from apps.home.models import Moneda
from apps.planCuenta.models import PlanCuenta

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

    def save(self, *args, **kwargs):
        """
        Genera automáticamente la cuenta contable asociada al banco si no existe.
        El tipo de cuenta se hereda automáticamente de la cuenta padre.
        """
        # Asignar automáticamente el tipo de cuenta basado en la cuenta padre
        tipo_cuenta_padre = self.cuentaPadre.tipoPlanCuenta

        if not self.codigoPlanCuenta:
            # Crear subcuenta para este banco específico
            new_code = self._generate_bank_account_code(self.cuentaPadre)
            
            plan_cuenta = PlanCuenta.objects.create(
                codigoPlanCuenta=new_code,
                nombrePlanCuenta=f"{self.nombreBanco} ({tipo_cuenta_padre})",
                tipoPlanCuenta=tipo_cuenta_padre,
                nivelPlanCuenta=self.cuentaPadre.nivelPlanCuenta + 1,
                cuentaPadre=self.cuentaPadre
            )
            self.codigoPlanCuenta = plan_cuenta
        
        super().save(*args, **kwargs)

    def _generate_bank_account_code(self, cuenta_padre):
        """Genera el código para la cuenta específica del banco"""
        last_account = PlanCuenta.objects.filter(
            cuentaPadre=cuenta_padre
        ).aggregate(Max('codigoPlanCuenta'))
        
        if last_account['codigoPlanCuenta__max']:
            last_num = int(last_account['codigoPlanCuenta__max'][-2:])
            return f"{cuenta_padre.codigoPlanCuenta}{last_num + 1:02d}"
        return f"{cuenta_padre.codigoPlanCuenta}01"


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
        """
        if not self.planCuenta_id:
            # Obtener nombres específicos según el tipo de producto
            nombre_producto = {
                'corriente': "CUENTAS CORRIENTES",
                'ahorro': "CUENTAS DE AHORRO",
                'plazo_fijo': "DEPÓSITOS A PLAZO",
                'prestamo': "PRÉSTAMOS BANCARIOS",
                'inversion': "FONDOS DE INVERSIÓN"
            }.get(self.tipoProducto, "OTRAS CUENTAS")
            
            # Buscar o crear la cuenta de producto específico
            cuenta_producto, created = PlanCuenta.objects.get_or_create(
                nombrePlanCuenta=nombre_producto,
                tipoPlanCuenta=self.banco.codigoPlanCuenta.tipoPlanCuenta,
                nivelPlanCuenta=self.banco.codigoPlanCuenta.nivelPlanCuenta + 1,
                cuentaPadre=self.banco.codigoPlanCuenta,
                defaults={
                    'codigoPlanCuenta': self._generate_product_code()
                }
            )
            
            # Crear subcuenta para esta cuenta específica
            new_code = self._generate_account_code(cuenta_producto)
            
            plan_cuenta = PlanCuenta.objects.create(
                codigoPlanCuenta=new_code,
                nombrePlanCuenta=f"{self.get_tipoProducto_display()} {self.numeroCuentaBanco}",
                tipoPlanCuenta=self.banco.codigoPlanCuenta.tipoPlanCuenta,
                nivelPlanCuenta=cuenta_producto.nivelPlanCuenta + 1,
                cuentaPadre=cuenta_producto
            )
            self.planCuenta = plan_cuenta
        
        super().save(*args, **kwargs)
    def _generate_product_code(self):
            """Genera código para la categoría de producto bancario"""
            try:
                last_product = PlanCuenta.objects.filter(
                    cuentaPadre=self.banco.codigoPlanCuenta
                ).aggregate(Max('codigoPlanCuenta'))
                
                if last_product['codigoPlanCuenta__max']:
                    last_num = int(last_product['codigoPlanCuenta__max'][-2:])
                    new_code = f"{self.banco.codigoPlanCuenta.codigoPlanCuenta}{last_num + 1:02d}"
                else:
                    new_code = f"{self.banco.codigoPlanCuenta.codigoPlanCuenta}01"
                
                print(f"[DEBUG] Código de producto generado correctamente: {new_code}")
                return new_code
            except Exception as e:
                print(f"[ERROR] Error al generar el código de producto: {e}")
                raise

    def _generate_account_code(self, cuenta_producto):
            """Genera código para la cuenta bancaria específica"""
            try:
                last_account = PlanCuenta.objects.filter(
                    cuentaPadre=cuenta_producto
                ).aggregate(Max('codigoPlanCuenta'))
                
                if last_account['codigoPlanCuenta__max']:
                    last_num = int(last_account['codigoPlanCuenta__max'][-2:])
                    new_code = f"{cuenta_producto.codigoPlanCuenta}{last_num + 1:02d}"
                else:
                    new_code = f"{cuenta_producto.codigoPlanCuenta}01"
                
                print(f"[DEBUG] Código de cuenta bancaria generado correctamente: {new_code}")
                return new_code
            except Exception as e:
                print(f"[ERROR] Error al generar el código de cuenta bancaria: {e}")
                raise