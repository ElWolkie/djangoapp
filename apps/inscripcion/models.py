from django.db import models
from django.utils import timezone
from apps.persona.models import Personas
from apps.home.models import Cohorte, CuotaFormacion, TipoFormacion, Formacion
# from apps.factura.models import Nota


class Inscripcion(models.Model):
    ESTADOS_PAGO = [
        ('PENDIENTE', 'Pendiente'),
        ('PARCIAL', 'Pago Parcial'),
        ('COMPLETO', 'Pago Completo'),
    ]
    
    idInscripcion = models.AutoField(primary_key=True)
    idPersona = models.ForeignKey(Personas, on_delete=models.CASCADE)
    idCohorte = models.ForeignKey(Cohorte, on_delete=models.CASCADE)
    idTF = models.ForeignKey(TipoFormacion, on_delete=models.CASCADE)
    idFormacion = models.ForeignKey(Formacion, on_delete=models.CASCADE)
    is_active = models.BooleanField(default=True)
    fechaInscripcion = models.DateField(auto_now_add=True)
    estadoPago = models.CharField(max_length=20, choices=ESTADOS_PAGO, default='PENDIENTE')
    montoPagado = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    class Meta:
        verbose_name = "Inscripción"
        verbose_name_plural = "Inscripciones"      

    def __str__(self):
        return f"Inscripción {self.idInscripcion} - {self.idPersona}"
    
    @property
    def montoTotal(self):
        """Calcula el monto total a pagar (inscripción + todas las cuotas)"""
        total = self.idFormacion.valorInscripcion
        if self.idFormacion.tieneCuotas:
            total += sum(cuota.valorCuota for cuota in self.idFormacion.cuotas.filter(is_active=True))
        return total
    
    @property
    def saldoPendiente(self):
        return self.montoTotal - self.montoPagado

# class PagoCuota(models.Model):
#     ESTADOS_PAGO = [
#         ('PENDIENTE', 'Pendiente'),
#         ('PAGADO', 'Pagado'),
#         ('VENCIDO', 'Vencido'),
#         ('CANCELADO', 'Cancelado'),
#     ]
    
#     idPagoCuota = models.AutoField(primary_key=True)
#     idInscripcion = models.ForeignKey(Inscripcion, on_delete=models.CASCADE, related_name='pagos_cuota')
#     idCuota = models.ForeignKey(CuotaFormacion, on_delete=models.CASCADE)
#     monto = models.DecimalField(max_digits=10, decimal_places=2)
#     fecha = models.DateField(null=False, auto_now=True )
#     estado = models.CharField(max_length=20, choices=ESTADOS_PAGO, default='PENDIENTE')
#     idNota = models.ForeignKey(Nota, on_delete=models.SET_NULL, null=True, blank=True, related_name='pagos_cuota')
    
#     class Meta:
#         verbose_name = "Pago de Cuota"
#         verbose_name_plural = "Pagos de Cuotas"
    
#     def __str__(self):
#         return f"Pago de {self.idCuota.nombreCuota} - {self.idInscripcion.idPersona}"
    
