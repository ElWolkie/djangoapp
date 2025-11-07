import logging
import traceback
from decimal import Decimal, InvalidOperation

from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import DetalleAsiento
from apps.saldoContable.models import SaldoContable

logger = logging.getLogger(__name__)

@receiver(post_save, sender=DetalleAsiento)
def actualizar_saldo_contable(sender, instance, **kwargs):
    """
    Señal que actualiza el SaldoContable cuando se crea/actualiza un DetalleAsiento.
    """
    try:
        logger.info("Iniciando señal para actualizar saldo contable... (DetalleAsiento id=%s)", getattr(instance, 'pk', None))

        cuenta = getattr(instance, 'idPlanCuenta', None)
        if not cuenta:
            logger.warning("DetalleAsiento sin idPlanCuenta: instance=%s", instance)
            return

        # Asegurar que idAsiento e idPeriodo existan
        asiento = getattr(instance, 'idAsiento', None)
        periodo = getattr(asiento, 'idPeriodo', None) if asiento else None
        if not periodo:
            logger.warning("No se pudo obtener periodo desde idAsiento (DetalleAsiento id=%s).", getattr(instance, 'pk', None))
            return

        logger.info("Cuenta: %s, Periodo: %s", getattr(cuenta, 'pk', None), getattr(periodo, 'pk', None))

        # Convertir debe/haber a Decimal de forma defensiva
        def to_decimal_safe(v):
            try:
                if v is None:
                    return Decimal('0')
                # si ya es Decimal, devolverlo; si es float/int/str -> convertir desde str
                if isinstance(v, Decimal):
                    return v
                return Decimal(str(v))
            except (InvalidOperation, ValueError) as ex:
                logger.exception("No se pudo convertir a Decimal: %s (valor=%r)", ex, v)
                return Decimal('0')

        debe_dec = to_decimal_safe(getattr(instance, 'debe', 0))
        haber_dec = to_decimal_safe(getattr(instance, 'haber', 0))

        logger.debug("Debe: %s, Haber: %s", debe_dec, haber_dec)

        # Usar transacción y lock para evitar race conditions
        with transaction.atomic():
            # buscar saldo con bloqueo row-level
            saldo = SaldoContable.objects.select_for_update().filter(
                id_plan_cuenta=cuenta, id_periodo=periodo
            ).first()

            if not saldo:
                logger.warning("No se encontró SaldoContable para cuenta=%s periodo=%s", getattr(cuenta,'pk',None), getattr(periodo,'pk',None))
                return

            logger.info("Saldo inicial: %s", saldo.saldo_final)

            naturaleza = getattr(cuenta, 'naturalezaPlanCuenta', None)
            if not naturaleza:
                logger.warning("La cuenta %s no tiene naturalezaPlanCuenta definida.", getattr(cuenta,'pk',None))
                return

            # determinar delta según naturaleza
            delta = Decimal('0')
            if naturaleza == 'deudora':
                if debe_dec > 0:
                    delta = debe_dec
                    logger.info("Actualizando saldo (deudora, debe): +%s", debe_dec)
                elif haber_dec > 0:
                    delta = -haber_dec
                    logger.info("Actualizando saldo (deudora, haber): -%s", haber_dec)
            elif naturaleza == 'acreedora':
                if debe_dec > 0:
                    delta = -debe_dec
                    logger.info("Actualizando saldo (acreedora, debe): -%s", debe_dec)
                elif haber_dec > 0:
                    delta = haber_dec
                    logger.info("Actualizando saldo (acreedora, haber): +%s", haber_dec)
            else:
                logger.warning("Naturaleza desconocida para la cuenta %s: %s", getattr(cuenta,'pk',None), naturaleza)
                return

            # aplicar cambio
            saldo.saldo_final = (saldo.saldo_final or Decimal('0')) + delta
            logger.info("Saldo antes de guardar: %s", saldo.saldo_final)

            # Guardar saldo
            saldo.save()
            # recargar y loggear
            saldo.refresh_from_db()
            logger.info("Saldo guardado y recargado: %s", saldo.saldo_final)

    except Exception as exc:
        # Loguear traza completa para debugging (no relanzamos para no romper la vista)
        tb = traceback.format_exc()
        logger.exception("Error en la señal actualizar_saldo_contable: %s\n%s", exc, tb)
        # opcional: si quieres que la vista reciba la excepción durante debugging,
        # puedes re-raise aquí, pero en producción recomendamos NO relanzar.
        # raise
        return
