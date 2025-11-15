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
    Handler robusto: cuando un PagoTemporal llega a confirmado=True:
    - recalcula estado de la nota asociada (PAGADA/PARCIAL/PENDIENTE)
    - busca NotaRelacionada(s) y resuelve la InscripcionCuota correspondiente (soporta idCuota apuntando a InscripcionCuota.pk
      o idCuota representando CuotaFormacion.pk) y marca esa InscripcionCuota como PAGADO
    - si todas las InscripcionCuota de la inscripción están PAGADO, marca la Inscripcion como PAGADA y actualiza montoPagado
    """
    try:
        if not getattr(instance, 'confirmado', False):
            return

        with transaction.atomic():
            nota = getattr(instance, 'idNota', None)
            if nota is None:
                logger.warning("PagoTemporal sin idNota asociado (id=%s)", getattr(instance, 'pk', None))
                return

            # 1) recalcular estado de la nota (suma pagos confirmados)
            pagos_confirmados = PagoTemporal.objects.filter(idNota=nota, confirmado=True)
            total_confirmado = pagos_confirmados.aggregate(total=Sum('monto'))['total'] or Decimal('0.00')
            nota_total = nota.totalNota or Decimal('0.00')

            if nota_total > Decimal('0.00') and total_confirmado >= nota_total:
                nota.estado = 'PAGADA'
            elif total_confirmado > Decimal('0.00'):
                nota.estado = 'PARCIAL'
            else:
                nota.estado = 'PENDIENTE'
            nota.save(update_fields=['estado'])

            # 2) procesar relaciones vinculadas a esa nota
            relaciones = NotaRelacionada.objects.filter(idNota=nota)
            for rel in relaciones:
                try:
                    rel_idcuota_raw = getattr(rel, 'idCuota_id', None)
                    ins_obj = getattr(rel, 'idInscripcion', None)

                    ins_cuota = None
                    # A) Caso: rel.idCuota_id fue guardado como pk de InscripcionCuota
                    if rel_idcuota_raw:
                        ins_cuota = InscripcionCuota.objects.filter(pk=rel_idcuota_raw).first()

                    # B) Caso: rel.idCuota_id es pk de CuotaFormacion -> buscar InscripcionCuota por inscripcion + idCuota_id
                    if not ins_cuota and ins_obj and rel_idcuota_raw:
                        ins_cuota = InscripcionCuota.objects.filter(
                            idInscripcion=ins_obj,
                            idCuota_id=rel_idcuota_raw
                        ).first()

                    # C) Si aún no hay resultado, intentar buscar por idInscripcion y valor aproximado (fallback)
                    if not ins_cuota and ins_obj:
                        ins_cuota = InscripcionCuota.objects.filter(idInscripcion=ins_obj).order_by('pk').first()

                    if ins_cuota:
                        # marcar la InscripcionCuota como PAGADO (y actualizar montoPagado si procede)
                        changed = False
                        if getattr(ins_cuota, 'estadoPago', '').upper() != 'PAGADO':
                            ins_cuota.estadoPago = 'PAGADO'
                            changed = True

                        try:
                            valor = getattr(ins_cuota.idCuota, 'valorCuota', None)
                            if valor is not None:
                                ins_cuota.montoPagado = valor
                                changed = True
                        except Exception:
                            # si falla leer idCuota, no detenemos el proceso
                            logger.debug("No fue posible leer valorCuota desde ins_cuota.idCuota para ins_cuota pk=%s", getattr(ins_cuota,'pk',None))

                        if changed:
                            ins_cuota.save(update_fields=['estadoPago', 'montoPagado'] if hasattr(ins_cuota, 'montoPagado') else ['estadoPago'])

                        # ahora comprobar si todas las cuotas de la inscripción están pagadas
                        try:
                            ins_model = ins_obj if isinstance(ins_obj, Inscripcion) else Inscripcion.objects.filter(pk=getattr(ins_obj, 'pk', ins_obj)).first()
                            if ins_model:
                                faltan = ins_model.inscripcioncuota_set.filter(~Q(estadoPago__iexact='PAGADO')).exists()
                                total_pagado = ins_model.inscripcioncuota_set.aggregate(sum=Sum('montoPagado'))['sum'] or Decimal('0.00')
                                # actualizar campos de la inscripción
                                ins_model.montoPagado = total_pagado
                                ins_model.estadoPago = 'PAGADO' if not faltan else ('PARCIAL' if total_pagado > Decimal('0.00') else 'PENDIENTE')
                                # guardar de forma segura (solo campos existentes)
                                update_fields = []
                                if hasattr(ins_model, 'montoPagado'): update_fields.append('montoPagado')
                                if hasattr(ins_model, 'estadoPago'): update_fields.append('estadoPago')
                                if update_fields:
                                    ins_model.save(update_fields=update_fields)
                        except Exception:
                            logger.exception("Error actualizando Inscripcion tras marcar InscripcionCuota PAGADO (rel id=%s)", getattr(rel,'id',None))
                    else:
                        logger.debug("No se encontró InscripcionCuota para NotaRelacionada id=%s (idCuota_id=%s, idInscripcion=%s)", getattr(rel,'id',None), rel_idcuota_raw, getattr(rel,'idInscripcion',None))
                except Exception:
                    logger.exception("Error procesando NotaRelacionada id=%s para Nota id=%s", getattr(rel,'id',None), getattr(nota,'idNota',None))

    except Exception:
        logger.exception("Error en signal on_pago_temporal_saved")