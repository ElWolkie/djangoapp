from django.db import models
from django.db.models import Max

class PlanCuenta(models.Model):
    """
    Modelo que representa el plan de cuentas contables de la organización.
    Incluye jerarquía automática de códigos contables y clasificación por tipos.
    """
    
    TIPO_CUENTA_CHOICES = [
        ('activo', 'Activo'),
        ('pasivo', 'Pasivo'),
        ('patrimonio', 'Patrimonio'),
        ('ingreso', 'Ingreso'),
        ('gasto', 'Gasto'),
    ]
    
    idPlanCuenta = models.AutoField(primary_key=True, verbose_name="ID Plan de Cuenta")
    codigoPlanCuenta = models.CharField(
        max_length=50, 
        unique=True,
        verbose_name="Código de Cuenta",
        help_text="Código jerárquico generado automáticamente"
    )
    nombrePlanCuenta = models.CharField(
        max_length=255,
        verbose_name="Nombre de Cuenta"
    )
    tipoPlanCuenta = models.CharField(
        max_length=50,
        choices=TIPO_CUENTA_CHOICES,
        verbose_name="Tipo de Cuenta"
    )
    nivelPlanCuenta = models.PositiveIntegerField(
        verbose_name="Nivel Jerárquico",
        help_text="1 para cuentas principales, aumenta según profundidad"
    )
    cuentaPadre = models.ForeignKey(
        'self',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='subcuentas',
        verbose_name="Cuenta Padre"
    )
    estadoPlanCuenta = models.BooleanField(
        default=True,
        verbose_name="Estado Activo"
    )
    fechaPlanCuenta = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Fecha de Creación"
    )

    class Meta:
        verbose_name = "Plan de Cuenta"
        verbose_name_plural = "Planes de Cuenta"
        ordering = ['codigoPlanCuenta']

    def __str__(self):
        return f"{self.codigoPlanCuenta} - {self.nombrePlanCuenta}"

    def save(self, *args, **kwargs):
        """
        Sobrescribe el método save para generar automáticamente códigos contables
        basados en la jerarquía y tipo de cuenta.
        """
        if not self.codigoPlanCuenta:
            if self.cuentaPadre:
                # Generar código para subcuenta
                last_child = PlanCuenta.objects.filter(
                    cuentaPadre=self.cuentaPadre
                ).aggregate(Max('codigoPlanCuenta'))
                
                if last_child['codigoPlanCuenta__max']:
                    last_code = last_child['codigoPlanCuenta__max']
                    prefix = last_code[:-2]
                    last_num = int(last_code[-2:])
                    self.codigoPlanCuenta = f"{prefix}{last_num + 1:02d}"
                else:
                    self.codigoPlanCuenta = f"{self.cuentaPadre.codigoPlanCuenta}01"
                
                self.nivelPlanCuenta = self.cuentaPadre.nivelPlanCuenta + 1
            else:
                # Generar código para cuenta principal
                prefix = self._get_prefix_for_type()
                last_main = PlanCuenta.objects.filter(
                    cuentaPadre__isnull=True,
                    tipoPlanCuenta=self.tipoPlanCuenta
                ).aggregate(Max('codigoPlanCuenta'))
                
                if last_main['codigoPlanCuenta__max']:
                    last_num = int(last_main['codigoPlanCuenta__max'][1:])
                    self.codigoPlanCuenta = f"{prefix}{last_num + 1:02d}"
                else:
                    self.codigoPlanCuenta = f"{prefix}101"
                
                self.nivelPlanCuenta = 1
        
        super().save(*args, **kwargs)

    def _get_prefix_for_type(self):
        """Devuelve el prefijo numérico según el tipo de cuenta"""
        type_prefix_map = {
            'activo': '1',
            'pasivo': '2',
            'patrimonio': '3',
            'ingreso': '4',
            'gasto': '5'
        }
        return type_prefix_map.get(self.tipoPlanCuenta, '0')