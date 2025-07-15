from django.db import models
from django.utils import timezone
from apps.persona.models import Personas
from apps.home.models import Cohorte, CuotaFormacion, TipoFormacion, Formacion
# from apps.factura.models import Nota


class Inscripcion(models.Model):
    ESTADOS_PAGO = [
        ('SIN CONFIRMAR', 'Sin Confirmar '), #estado que define una cuota depeniente de una inscripcion sin confirmar
        ('PENDIENTE', 'Pendiente'),
        ('PARCIAL', 'Pago Parcial'),
        ('PAGADO', 'Pago Completo'),
        ('FACTURADO', 'Factura creada'),
    ]
    
    idInscripcion = models.AutoField(primary_key=True)
    idPersona = models.ForeignKey(Personas, on_delete=models.CASCADE)
    idCohorte = models.ForeignKey(Cohorte, on_delete=models.CASCADE)
    idTF = models.ForeignKey(TipoFormacion, on_delete=models.CASCADE)
    idFormacion = models.ForeignKey(Formacion, on_delete=models.CASCADE)
    cuotas = models.ManyToManyField(CuotaFormacion, through='InscripcionCuota', related_name='inscripciones')
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

class InscripcionCuota(models.Model):
    idInscripcion = models.ForeignKey(Inscripcion, on_delete=models.CASCADE)
    idCuota = models.ForeignKey(CuotaFormacion, on_delete=models.CASCADE)
    estadoPago = models.CharField(max_length=20, choices=[
        ('SIN CONFIRMAR', 'Sin Confirmar '), #estado que define una cuota depeniente de una inscripcion sin confirmar
        ('EN ESPERA', 'En Espera'), #estado que define una cuota depeniente de una inscripcion confirmada, sin nota de cobro
        ('PENDIENTE', 'Pendiente'), #estado que define una cuota dependiente de una inscripcion confirmada, con nota de cobro
        ('PARCIAL', 'Pago Parcial'), #estado que define una cuota con un pago parcial de su valor
        ('PAGADO', 'Pagado'), # estado que define una cuota pagada en su totalidad
        ('FACTURADO', 'Factura Creada'), #estado  que define una cuota pagada y facturada

    ], default='PENDIENTE')
    montoPagado = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    fechaPago = models.DateField(null=True, blank=True)

    class Meta:
        verbose_name = "Cuota de Inscripción"
        verbose_name_plural = "Cuotas de Inscripción"