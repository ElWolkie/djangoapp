from django.db import models

# Create your models here.
from django.db import models  # Importa el módulo models de Django para definir modelos de base de datos.

class PlanCuenta(models.Model):  # Define un modelo llamado PlanCuenta que representa una tabla en la base de datos.
    idPlanCuenta = models.AutoField(primary_key=True)  # Campo autoincremental que actúa como clave primaria.
    codigoPlanCuenta = models.CharField(max_length=50, unique=True)  # Campo de texto único con un máximo de 50 caracteres.
    nombrePlanCuenta = models.CharField(max_length=255)  # Campo de texto con un máximo de 255 caracteres.
    tipoPlanCuenta = models.CharField(  # Campo de texto con opciones predefinidas para el tipo de cuenta.
        max_length=50, 
        choices=[
            ('activo', 'Activo'),  # Opción para cuentas de tipo activo.
            ('pasivo', 'Pasivo'),  # Opción para cuentas de tipo pasivo.
            ('patrimonio', 'Patrimonio'),  # Opción para cuentas de tipo patrimonio.
            ('ingreso', 'Ingreso'),  # Opción para cuentas de tipo ingreso.
            ('gasto', 'Gasto'),  # Opción para cuentas de tipo gasto.
        ]
    )
    nivelPlanCuenta = models.PositiveIntegerField()  # Campo numérico positivo para indicar el nivel jerárquico de la cuenta.
    cuentaPadre = models.ForeignKey(  # Relación de clave foránea hacia sí mismo para definir jerarquías.
        'self',  # Se refiere al mismo modelo.
        null=True,  # Permite valores nulos.
        blank=True,  # Permite que el campo sea opcional en formularios.
        on_delete=models.SET_NULL,  # Si la cuenta padre se elimina, este campo se establece en NULL.
        related_name='subcuentas'  # Nombre para acceder a las subcuentas relacionadas.
    )
    estadoPlanCuenta = models.BooleanField(default=True)  # Campo booleano para indicar si la cuenta está activa o no.
    fechaPlanCuenta = models.DateTimeField(auto_now_add=True)  # Campo de fecha y hora que se establece automáticamente al crear el registro.

    def __str__(self):  # Método que define cómo se representa el objeto como cadena.
        return f"{self.codigoPlanCuenta} - {self.nombrePlanCuenta}"  # Devuelve el código y el nombre de la cuenta como representación.