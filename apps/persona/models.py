from django.db import models  

class TipoPersona(models.Model):  
    idTP = models.AutoField(primary_key=True)  # Clave primaria para TipoPersona  
    nombreTP = models.CharField(max_length=100, unique=True)  # Nombre del TipoPersona (único y sensible a mayúsculas)  
    estadoTP = models.CharField(max_length=10)  # Estado del TipoPersona  
    fechaTP = models.DateField(auto_now_add=True)  # Fecha de creación del TipoPersona  

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['nombreTP'],
                name='unique_nombreTP_case_sensitive'
            )
        ]

    class Meta:  
        verbose_name = "Tipo de Persona"  
        verbose_name_plural = "Tipos de Personas"  

    def __str__(self):
        return self.nombreTP  # Representación legible en el admin de Django


class Personas(models.Model):  
    idPersona = models.AutoField(primary_key=True)  # Clave primaria para Personas  
    cedula = models.CharField(max_length=10, unique=True)  # Número de cedula (único)  
    nombres = models.CharField(max_length=100)  # Nombres  
    apellidos = models.CharField(max_length=100)  # Apellidos  
    telefono = models.CharField(max_length=15)  # Número de teléfono  
    correo = models.EmailField()  # Dirección de correo electrónico  
    estadoPersona = models.CharField(max_length=10)  # Estado de la Persona  
    fechaPersona = models.DateField(auto_now_add=True)  # Fecha de creación de la Persona  

    class Meta:  
        verbose_name = "Persona"  
        verbose_name_plural = "Personas"  
        ordering = ['idPersona']  # Orden predeterminado por idPersona

    def __str__(self):
        return f"{self.nombres} {self.apellidos}"  # Representación legible en el admin de Django


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
    
