from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import DetalleAsiento
from apps.saldoContable.models import SaldoContable
from decimal import Decimal

@receiver(post_save, sender=DetalleAsiento)
def actualizar_saldo_contable(sender, instance, **kwargs):
    try:
        print("Iniciando señal para actualizar saldo contable...")

        cuenta = instance.idPlanCuenta
        cuenta.refresh_from_db()  # Asegurarse de que el objeto esté completamente cargado
        print(f"Cuenta obtenida: {cuenta}")

        naturaleza_cuenta = cuenta.naturalezaPlanCuenta
        if not naturaleza_cuenta:
            print(f"La cuenta {cuenta} no tiene una naturaleza definida.")
            return
        print(f"Naturaleza de la cuenta: {naturaleza_cuenta}")

        periodo = instance.idAsiento.idPeriodo  # Obtener el periodo contable desde el AsientoContable
        print(f"Periodo contable obtenido: {periodo}")

        saldo = SaldoContable.objects.filter(id_plan_cuenta=cuenta, id_periodo=periodo).first()
        if not saldo:
            print(f"No se encontró un saldo contable para la cuenta {cuenta} en el periodo {periodo}")
            return

        print(f"Saldo inicial encontrado: {saldo.saldo_final}")
        print(f"Debe: {instance.debe}, Haber: {instance.haber}")

        # Actualizar el saldo según la naturaleza de la cuenta
        if naturaleza_cuenta == 'deudora':
            if instance.debe > 0:
                print(f"Actualizando saldo (deudora, debe): +{instance.debe}")
                saldo.saldo_final += Decimal(str(instance.debe))
            elif instance.haber > 0:
                print(f"Actualizando saldo (deudora, haber): -{instance.haber}")
                saldo.saldo_final -= Decimal(str(instance.haber))
        elif naturaleza_cuenta == 'acreedora':
            if instance.debe > 0:
                print(f"Actualizando saldo (acreedora, debe): -{instance.debe}")
                saldo.saldo_final -= Decimal(str(instance.debe))
            elif instance.haber > 0:
                print(f"Actualizando saldo (acreedora, haber): +{instance.haber}")
                saldo.saldo_final += Decimal(str(instance.haber))

        print(f"Saldo antes de guardar: {saldo.saldo_final}")
        saldo.save()
        print(f"Saldo guardado en la base de datos: {saldo.saldo_final}")

        # Recargar el saldo desde la base de datos para confirmar el cambio
        saldo.refresh_from_db()
        print(f"Saldo después de recargar desde la base de datos: {saldo.saldo_final}")
    except Exception as e:
        print(f"Error en la señal actualizar_saldo_contable: {e}")