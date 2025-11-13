from django.db.models.signals import post_save
from django.dispatch import receiver
from django.db import transaction
from django.db.models import Sum
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)

from apps.factura.models import PagoTemporal, Nota, NotaRelacionada
from apps.inscripcion.models import Inscripcion

@receiver(post_save, sender=PagoTemporal)
def on_pago_temporal_saved(sender, instance: PagoTemporal, created, **kwargs):
    """
    Si un PagoTemporal se marca confirmado, recalcular estado de la nota e inscripción.
    """
    try:
        # Solo actuamos cuando el pago esté confirmado
        if not getattr(instance, 'confirmado', False):
            return

        with transaction.atomic():
            nota = instance.idNota
            if nota is None:
                logger.warning("PagoTemporal sin idNota asociado (id=%s)", getattr(instance, 'pk', None))
                return

            pagos_confirmados = PagoTemporal.objects.filter(idNota=nota, confirmado=True)
            total_confirmado = pagos_confirmados.aggregate(total=Sum('monto'))['total'] or Decimal('0.00')

            # decidir estado de la nota
            nota_total = nota.totalNota or Decimal('0.00')
            if total_confirmado >= nota_total and nota_total > Decimal('0.00'):
                nota.estado = 'PAGADA'
            elif total_confirmado > Decimal('0.00'):
                nota.estado = 'PARCIAL'
            else:
                nota.estado = 'PENDIENTE'
            nota.save(update_fields=['estado'])

            # actualizar inscripción si existe relación
            relacion = NotaRelacionada.objects.filter(idNota=nota).first()
            if relacion and relacion.idInscripcion:
                ins = relacion.idInscripcion
                try:
                    # Si el modelo Inscripcion tiene campo montoPagado, actualízalo
                    if hasattr(ins, 'montoPagado'):
                        ins.montoPagado = total_confirmado
                        ins.estadoPago = 'PAGADO' if nota.estado == 'PAGADA' else ('PARCIAL' if nota.estado == 'PARCIAL' else 'PENDIENTE')
                        ins.save(update_fields=['montoPagado', 'estadoPago'])
                    else:
                        ins.estadoPago = 'PAGADO' if nota.estado == 'PAGADA' else ('PARCIAL' if nota.estado == 'PARCIAL' else 'PENDIENTE')
                        ins.save(update_fields=['estadoPago'])
                except Exception:
                    logger.exception("Error actualizando Inscripcion tras confirmacion de pago (nota id=%s)", getattr(nota, 'idNota', None))

    except Exception:
        logger.exception("Error en signal on_pago_temporal_saved")
