from django.db import models  
from django.contrib.auth.models import User  

class TipoPersona(models.Model):  
    idTP = models.AutoField(primary_key=True)  # Definimos la clave primaria con el nombre idTP  
    nombreTP = models.CharField(max_length=100)  
    estadoTP = models.CharField(max_length=10)  
    fechaTP = models.DateField(auto_now_add=True)  

    class Meta:  
        verbose_name = "Tipo de Persona"  
        verbose_name_plural = "Tipos de Personas"  


class Personas(models.Model):  
    idPersona = models.AutoField(primary_key=True)  # Definimos la clave primaria con el nombre id
    idTP = models.ForeignKey(TipoPersona, on_delete=models.CASCADE)  # Llave foránea hacia TipoPersona  
    cedula = models.CharField(max_length=10)  
    nombres = models.CharField(max_length=100)  
    apellidos = models.CharField(max_length=100)  
    telefono = models.CharField(max_length=15)  
    correo = models.EmailField()  
    estadoPersona = models.CharField(max_length=10)  
    fechaPersona = models.DateField(auto_now_add=True)  

    class Meta:  
        verbose_name = "Persona"  
        verbose_name_plural = "Personas"  
        ordering = ['idTP']  


class Cuota(models.Model):  
    idCuota = models.AutoField(primary_key=True)  # Clave primaria para el modelo  
    nombreCuota = models.CharField(max_length=100)  # Nombre de la cuota  
    estadoCuota = models.CharField(max_length=10)  # Estado de la cuota  
    fechaCuota = models.DateField(auto_now_add=True)  # Fecha de creación de la cuota  

    class Meta:  
        verbose_name = "Cuota"  
        verbose_name_plural = "Cuotas"  


class TipoOferta(models.Model):  
    idTipoOferta = models.AutoField(primary_key=True)  # Clave primaria para el modelo  
    idCuota = models.ForeignKey('Cuota', on_delete=models.CASCADE)  # Asumiendo que 'Cuota' es otro modelo  
    nombreTipoOferta = models.CharField(max_length=100)  
    estadoTipoOferta = models.CharField(max_length=10)  
    fechaTipoOferta = models.DateField(auto_now_add=True)  

    class Meta:  
        verbose_name = "Tipo de Oferta"  
        verbose_name_plural = "Tipos de Ofertas"  


class Ofertas(models.Model):  
    idOferta = models.AutoField(primary_key=True)  # Definimos la clave primaria con el nombre idOferta  
    idTipoOferta = models.ForeignKey('TipoOferta', on_delete=models.CASCADE)  
    nombreOferta = models.CharField(max_length=100)  
    duracion = models.CharField(max_length=100)  # Para representar una duración, puede ser en días, horas, etc.  
    estadoOferta = models.CharField(max_length=10)  
    fechaOferta = models.DateField(auto_now_add=True)  

    class Meta:  
        verbose_name = "Oferta"  
        verbose_name_plural = "Ofertas"  


class Materia(models.Model):  
    idMateria = models.AutoField(primary_key=True)  # Clave primaria para el modelo Materia  
    idOferta = models.ForeignKey(Ofertas, on_delete=models.CASCADE)  # Llave foránea hacia Ofertas  
    nombreMateria = models.CharField(max_length=100)  
    estadoMateria = models.CharField(max_length=10)  
    fechaMateria = models.DateField(auto_now_add=True)  # Fecha de creación de la materia  

    class Meta:  
        verbose_name = "Materia"  
        verbose_name_plural = "Materias"

class Cohorte(models.Model):  
    idCohorte = models.AutoField(primary_key=True)  # Clave primaria para el modelo  
    nombreCohorte = models.CharField(max_length=100)  # Nombre de la cuota  
    estadoCohorte = models.CharField(max_length=10)  # Estado de la cuota  
    fechaCohorte = models.DateField(auto_now_add=True)  # Fecha de creación de la cuota  

    class Meta:  
        verbose_name = "Cohorte"  
        verbose_name_plural = "Cohortes"  


class Cargo(models.Model):  
    idCargo = models.AutoField(primary_key=True)  # Clave primaria para el modelo  
    nombreCargo = models.CharField(max_length=100)  # Nombre de la cuota  
    estadoCargo = models.CharField(max_length=10)  # Estado de la cuota  
    fechaCargo = models.DateField(auto_now_add=True)  # Fecha de creación de la cuota  

    class Meta:  
        verbose_name = "Cargo"  
        verbose_name_plural = "Cargos"  

class Contrato(models.Model):  
    idContrato = models.AutoField(primary_key=True)  # Clave primaria para el modelo  
    idPersona = models.ForeignKey(Personas, on_delete=models.CASCADE)  # Llave foránea hacia Persona
    idCargo = models.ForeignKey(Cargo, on_delete=models.CASCADE)  # Llave foránea hacia Cargo  
    idCohorte = models.ForeignKey(Cohorte, on_delete=models.CASCADE)  # Llave foránea hacia Cohorte  
    idMateria = models.ForeignKey(Materia, on_delete=models.CASCADE)  # Llave foránea hacia Materia  
    estadoContrato = models.CharField(max_length=10)  # Estado del contrato  
    fechaContrato = models.DateField(auto_now_add=True)  # Fecha de creación del contrato  

    class Meta:  
        verbose_name = "Contrato"  
        verbose_name_plural = "Contratos"  

class Honorario(models.Model):  
    idHonorario = models.AutoField(primary_key=True)  # Clave primaria para el modelo  
    idContrato = models.ForeignKey(Contrato, on_delete=models.CASCADE)  # Llave foránea hacia Contrato
    horas = models.FloatField()  # Cantidad de horas trabajadas  
    estadoContrato = models.CharField(max_length=10)  # Estado del honorario  
    fechaContrato = models.DateField(auto_now_add=True)  # Fecha de creación del honorario  

    class Meta:  
        verbose_name = "Honorario"  
        verbose_name_plural = "Honorarios"  