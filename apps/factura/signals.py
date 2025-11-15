from django.db.models.signals import post_save
from django.dispatch import receiver
from django.db import transaction
from django.db.models import Sum, Q
from decimal import Decimal
import logging

from apps.factura.models import PagoTemporal, Nota, NotaRelacionada
from apps.inscripcion.models import Inscripcion, InscripcionCuota

logger = logging.getLogger(__name__)

@receiver(post_save, sender=PagoTemporal)
def on_pago_temporal_saved(sender, instance: PagoTemporal, created, **kwargs):
    """
    Si un PagoTemporal se marca confirmado, recalcular estado de la nota, las cuotas relacionadas
    y la inscripción asociada.
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

            # 1) recalcular estado de la nota (suma de pagos confirmados sobre esa nota)
            pagos_confirmados = PagoTemporal.objects.filter(idNota=nota, confirmado=True)
            total_confirmado = pagos_confirmados.aggregate(total=Sum('monto'))['total'] or Decimal('0.00')

            nota_total = nota.totalNota or Decimal('0.00')
            if total_confirmado >= nota_total and nota_total > Decimal('0.00'):
                nota.estado = 'PAGADA'
            elif total_confirmado > Decimal('0.00'):
                nota.estado = 'PARCIAL'
            else:
                nota.estado = 'PENDIENTE'
            nota.save(update_fields=['estado'])

            # 2) actualizar InscripcionCuota(s) relacionadas con esta nota (si las hay)
            relaciones = NotaRelacionada.objects.filter(idNota=nota)
            for rel in relaciones:
                # si rel.idCuota apunta a InscripcionCuota (tu modelo), marcarla PAGADA
                try:
                    if getattr(rel, 'idCuota', None):
                        # rel.idCuota es InscripcionCuota instance
                        ic = rel.idCuota
                        # marcar pagada si la nota ya está PAGADA o si hay monto confirmado suficiente
                        ic.estadoPago = 'PAGADO' if nota.estado == 'PAGADA' else ic.estadoPago
                        ic.save(update_fields=['estadoPago'])
                except Exception:
                    logger.exception("No se pudo actualizar InscripcionCuota desde NotaRelacionada id=%s", getattr(rel, 'id', None))

            # 3) si la nota tiene relación con una inscripcion, recalcular estado y monto de la inscripción
            relacion = relaciones.filter(idInscripcion__isnull=False).first()
            if relacion and relacion.idInscripcion:
                ins = relacion.idInscripcion
                try:
                    # montoPagado: sumar todos los pagos confirmados de todas las notas que referencian a esta inscripcion
                    notas_ins = Nota.objects.filter(relaciones__idInscripcion=ins).distinct()
                    pagos_confirmados_ins = PagoTemporal.objects.filter(idNota__in=notas_ins, confirmado=True)
                    total_confirmado_ins = pagos_confirmados_ins.aggregate(total=Sum('monto'))['total'] or Decimal('0.00')

                    # actualizar montoPagado si existe el campo
                    if hasattr(ins, 'montoPagado'):
                        ins.montoPagado = total_confirmado_ins

                    # determinar si todas las InscripcionCuota están pagadas
                    cuotas = InscripcionCuota.objects.filter(idInscripcion=ins)
                    total_cuotas = cuotas.count()
                    pagadas_count = cuotas.filter(estadoPago__iexact='PAGADO').count()

                    if total_cuotas > 0 and pagadas_count == total_cuotas:
                        ins.estadoPago = 'PAGADO'
                    else:
                        # si hay algún pago confirmado a la inscripción considerarlo PARCIAL
                        if total_confirmado_ins > Decimal('0.00'):
                            ins.estadoPago = 'PARCIAL'
                        else:
                            ins.estadoPago = 'PENDIENTE'

                    # guardar cambios
                    fields = []
                    if hasattr(ins, 'montoPagado'):
                        fields.append('montoPagado')
                    fields.append('estadoPago')
                    ins.save(update_fields=fields)
                except Exception:
                    logger.exception("Error actualizando Inscripcion tras confirmacion de pago (nota id=%s)", getattr(nota, 'idNota', None))

    except Exception:
        logger.exception("Error en signal on_pago_temporal_saved")
