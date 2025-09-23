from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.db import transaction
from apps.periodoContable.models import periodoContable
from apps.saldoContable.models import SaldoContable
from apps.planCuenta.models import PlanCuenta

@receiver(post_save, sender=periodoContable)
def manejar_nuevo_periodo(sender, instance, created, **kwargs):
    print("Signal manejar_nuevo_periodo triggered")
    print(f"Created: {created}, EstadoPeriodo: {instance.estadoPeriodo}")

    if created and instance.estadoPeriodo:
        print("Creating saldos for the new periodoContable...")
        with transaction.atomic():
            # Inactivate other periods
            updated_count = periodoContable.objects.exclude(idPeriodo=instance.idPeriodo).update(estadoPeriodo=False)
            print(f"Inactivated {updated_count} other periods.")

            # Get the previous period
            periodo_anterior = periodoContable.objects.filter(estadoPeriodo=False).exclude(
                idPeriodo=instance.idPeriodo
            ).order_by('-fechaFinPeriodo').first()
            print(f"Previous period: {periodo_anterior}")

            if periodo_anterior:
                for cuenta in PlanCuenta.objects.all():
                    print(f"Processing PlanCuenta: {cuenta}")
                    try:
                        saldo_anterior = SaldoContable.objects.get(
                            id_periodo=periodo_anterior,
                            id_plan_cuenta=cuenta
                        )
                        saldo_final_anterior = saldo_anterior.saldo_final
                        print(f"Found previous saldo: {saldo_anterior}")
                    except SaldoContable.DoesNotExist:
                        saldo_final_anterior = 0
                        print("No previous saldo found, defaulting to 0.")

                    # Create new saldo
                    SaldoContable.objects.create(
                        id_periodo=instance,
                        id_plan_cuenta=cuenta,
                        saldo_inicial=saldo_final_anterior,
                        saldo_final=0
                    )
                    print(f"Created new saldo for PlanCuenta {cuenta}.")
            else:
                print("No previous period found, creating initial saldos with 0.")
                for cuenta in PlanCuenta.objects.all():
                    print(f"Processing PlanCuenta: {cuenta}")
                    SaldoContable.objects.create(
                        id_periodo=instance,
                        id_plan_cuenta=cuenta,
                        saldo_inicial=0,
                        saldo_final=0
                    )
                    print(f"Created initial saldo for PlanCuenta {cuenta}.")

@receiver(pre_save, sender=periodoContable)
def actualizar_saldos_al_inactivar(sender, instance, **kwargs):
    print("Signal actualizar_saldos_al_inactivar triggered")
    if instance.pk:
        print(f"Instance PK: {instance.pk}")
        
    """
    Actualiza los saldos cuando un período se inactiva manualmente
    """
    if instance.pk:  # Solo para instancias existentes, no nuevas
        try:
            original = periodoContable.objects.get(pk=instance.pk)
        except periodoContable.DoesNotExist:
            return
        
        # Si el período estaba activo y ahora se está inactivando
        if original.estadoPeriodo and not instance.estadoPeriodo:
            # Obtener el próximo período activo (si existe)
            proximo_periodo = periodoContable.objects.filter(
                estadoPeriodo=True
            ).exclude(idPeriodo=instance.idPeriodo).first()
            
            if proximo_periodo:
                # Actualizar los saldos del período que se está inactivando
                for saldo in SaldoContable.objects.filter(id_periodo=instance):
                    # Transferir el saldo final al próximo período
                    try:
                        saldo_proximo = SaldoContable.objects.get(
                            id_periodo=proximo_periodo,
                            id_plan_cuenta=saldo.id_plan_cuenta
                        )
                        saldo_proximo.saldo_inicial = saldo.saldo_final
                        saldo_proximo.save()
                    except SaldoContable.DoesNotExist:
                        # Crear nuevo saldo si no existe
                        SaldoContable.objects.create(
                            id_periodo=proximo_periodo,
                            id_plan_cuenta=saldo.id_plan_cuenta,
                            saldo_inicial=saldo.saldo_final,
                            saldo_final=0
                        )
@receiver(pre_save, sender=periodoContable)
def manejar_cambio_estado_periodo(sender, instance, **kwargs):
    if instance.pk:  # Solo para instancias existentes
        try:
            original = periodoContable.objects.get(pk=instance.pk)
        except periodoContable.DoesNotExist:
            return

        # Detectar cambio de estadoPeriodo de False a True
        if not original.estadoPeriodo and instance.estadoPeriodo:
            print("Signal manejar_cambio_estado_periodo triggered")
            print(f"Activating periodoContable: {instance.nombrePeriodo}")

            # Ejecutar la lógica de creación de saldos
            with transaction.atomic():
                # Inactivar otros períodos
                periodoContable.objects.exclude(idPeriodo=instance.idPeriodo).update(estadoPeriodo=False)

                # Obtener el período anterior
                periodo_anterior = periodoContable.objects.filter(estadoPeriodo=False).exclude(
                    idPeriodo=instance.idPeriodo
                ).order_by('-fechaFinPeriodo').first()

                print(f"Previous period: {periodo_anterior}")

                if periodo_anterior:
                    # Listar todos los saldos del período anterior
                    saldos_anteriores = SaldoContable.objects.filter(id_periodo=periodo_anterior)
                    print(f"Saldos del período anterior ({periodo_anterior}): {list(saldos_anteriores)}")

                    for cuenta in PlanCuenta.objects.all():
                        print(f"Processing PlanCuenta: {cuenta}")
                        try:
                            saldo_anterior = saldos_anteriores.get(id_plan_cuenta=cuenta)
                            saldo_final_anterior = saldo_anterior.saldo_final
                            print(f"Found previous saldo: {saldo_anterior}, saldo_final: {saldo_final_anterior}")
                        except SaldoContable.DoesNotExist:
                            saldo_final_anterior = 0
                            print("No previous saldo found, defaulting to 0.")

                        SaldoContable.objects.create(
                            id_periodo=instance,
                            id_plan_cuenta=cuenta,
                            saldo_inicial=saldo_final_anterior,
                            saldo_final=0
                        )
                        print(f"Created new saldo for PlanCuenta {cuenta} with saldo_inicial: {saldo_final_anterior}")
                else:
                    print("No previous period found, creating initial saldos with 0.")
                    for cuenta in PlanCuenta.objects.all():
                        print(f"Processing PlanCuenta: {cuenta}")
                        SaldoContable.objects.create(
                            id_periodo=instance,
                            id_plan_cuenta=cuenta,
                            saldo_inicial=0,
                            saldo_final=0
                        )
                        print(f"Created initial saldo for PlanCuenta {cuenta} with saldo_inicial: 0")