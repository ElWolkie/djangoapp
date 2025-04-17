from django.db import models
from apps.persona.models import Personas
from apps.home.models import Tramite, Servicio

class Solicitud(models.Model):
    idSoli = models.AutoField(primary_key=True)  # Clave primaria para Solicitud
    idPersona = models.ForeignKey(Personas, on_delete=models.CASCADE)  # Clave foránea a Personas  
    idTramite = models.ForeignKey(Tramite, on_delete=models.CASCADE)  # Clave foránea a Tramite
    idServicio = models.ForeignKey(Servicio, on_delete=models.CASCADE)  # Clave foránea a Servicio
    montoTotal = models.DecimalField(max_digits=10, decimal_places=2)  # Monto total de la Solicitud
    estadoSolicitud = models.CharField(max_length=10)  # Estado de la Solicitud
    fechaEntrega = models.DateField()  # Fecha de entrega de la Solicitud
    fechaSolicitud = models.DateField(auto_now_add=True)  # Fecha de creación de la Solicitud

    class Meta:
        verbose_name = "Solicitud"
        verbose_name_plural = "Solicitudes"