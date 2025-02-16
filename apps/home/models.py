from django.db import models
from django.contrib.auth.models import User

class TipoPersona(models.Model):
    idTP = models.AutoField(primary_key=True)  # Definimos la clave primaria con el nombre idTP
    nombre = models.CharField(max_length=100)

    class Meta:
        verbose_name = "Tipo de Persona"
        verbose_name_plural = "Tipos de Personas"

class Personas(models.Model): 
    idTP = models.ForeignKey(TipoPersona, on_delete=models.CASCADE)  # Llave foránea hacia TipoPersona
    cedula = models.CharField(max_length=10)
    nombres = models.CharField(max_length=100)
    apellidos = models.CharField(max_length=100)
    telefono = models.CharField(max_length=15)
    correo = models.EmailField()
    estadoPersona = models.CharField(max_length=10)
    fecha = models.DateField(auto_now_add=True)

    class Meta:
        verbose_name = "Persona"
        verbose_name_plural = "Personas"
        ordering = ['nombres']