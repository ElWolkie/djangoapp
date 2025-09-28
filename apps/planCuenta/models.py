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
    

    NATURALEZA_CHOICES = [
        ('deudora', 'Deudora'),
        ('acreedora', 'Acreedora'),
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

    naturalezaPlanCuenta = models.CharField(
        max_length=10,
        choices=NATURALEZA_CHOICES,
        verbose_name="Naturaleza de la Cuenta",
        help_text="Indica si la cuenta es deudora o acreedora. Puede cambiar en casos excepcionales.",
        default=None,
        null=True,
        blank=True
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
                self._generate_child_code()
            else:
                # Generar código para cuenta principal
                self._generate_main_code()
            
            # Asignar naturaleza automáticamente si no está definida
            if not self.naturalezaPlanCuenta:
                self._assign_nature()
        
        super().save(*args, **kwargs)

    def _generate_child_code(self):
        """Genera código para subcuenta basado en la cuenta padre"""
        # Obtener el último hijo de la misma cuenta padre
        last_child = PlanCuenta.objects.filter(
            cuentaPadre=self.cuentaPadre
        ).order_by('-codigoPlanCuenta').first()
        
        if last_child:
            # Incrementar el último código
            last_code = last_child.codigoPlanCuenta
            # Encontrar la parte numérica final (últimos 2 dígitos)
            base_code = last_code[:-2]
            last_num = int(last_code[-2:])
            new_num = last_num + 1
            self.codigoPlanCuenta = f"{base_code}{new_num:02d}"
        else:
            # Primer hijo de esta cuenta padre
            self.codigoPlanCuenta = f"{self.cuentaPadre.codigoPlanCuenta}01"
        
        self.nivelPlanCuenta = self.cuentaPadre.nivelPlanCuenta + 1

    def _generate_main_code(self):
        """Genera código para cuenta principal"""
        prefix = self._get_prefix_for_type()
        
        # Obtener la última cuenta principal del mismo tipo
        last_main = PlanCuenta.objects.filter(
            cuentaPadre__isnull=True,
            tipoPlanCuenta=self.tipoPlanCuenta
        ).order_by('-codigoPlanCuenta').first()
        
        if last_main:
            # Extraer el número del código (ej: "101" -> 01, "202" -> 02)
            last_code = last_main.codigoPlanCuenta
            last_num = int(last_code[1:])  # Ignora el primer dígito (tipo)
            new_num = last_num + 1
            self.codigoPlanCuenta = f"{prefix}{new_num:02d}"
        else:
            # Primera cuenta de este tipo
            self.codigoPlanCuenta = f"{prefix}01"
        
        self.nivelPlanCuenta = 1

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

    def _assign_nature(self):
        """Asigna naturaleza automáticamente según el tipo"""
        naturaleza_map = {
            'activo': 'deudora',
            'gasto': 'deudora', 
            'pasivo': 'acreedora',
            'patrimonio': 'acreedora',
            'ingreso': 'acreedora',
        }
        self.naturalezaPlanCuenta = naturaleza_map.get(self.tipoPlanCuenta)