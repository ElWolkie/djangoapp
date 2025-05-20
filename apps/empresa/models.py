from django.db import models

class empresa(models.Model):
    idEmpresa = models.AutoField(primary_key=True)  # Clave primaria autoincremental
    nombreEmpresa = models.CharField(max_length=255)  # Nombre de la empresa
    rifEmpresa = models.CharField(max_length=20, unique=True)  # RIF de la empresa
    direccionEmpresa = models.TextField()  # Dirección de la empresa
    telefonoEmpresa = models.CharField(max_length=15)  # Teléfono de la empresa
    correoEmpresa = models.EmailField()  # Correo electrónico de la empresa
    estadoEmpresa = models.BooleanField(default=True)  # Estado de la empresa (activo/inactivo)
    fechaEmpresa = models.DateTimeField(auto_now_add=True)  # Fecha de creación del registro

    def __str__(self):
        return self.nombreEmpresa