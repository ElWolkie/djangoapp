from django.db import models
from apps.inscripcion.models import Inscripcion
from apps.home.models import Requisito
from apps.solicitud.models import Solicitud  # Si tienes esta app/modelo

class RequisitoCliente(models.Model):
    idRC = models.AutoField(primary_key=True)
    idInscripcion = models.ForeignKey(Inscripcion, on_delete=models.CASCADE, null=True, blank=True)
    idSolicitud = models.ForeignKey(Solicitud, on_delete=models.CASCADE, null=True, blank=True)
    idRequisito = models.ForeignKey(Requisito, on_delete=models.CASCADE)
    entregado = models.BooleanField(default=False)
    fechaCreacion = models.DateTimeField(auto_now_add=True)
    fechaModificado = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Requisito de Cliente"
        verbose_name_plural = "Requisitos de Cliente"

    def __str__(self):
        return f"{self.idRequisito} - {'Entregado' if self.entregado else 'Pendiente'}"