from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.db import transaction
from apps.periodoContable.models import periodoContable
from apps.saldoContable.models import SaldoContable
from apps.planCuenta.models import PlanCuenta

@receiver(post_save, sender=periodoContable)
def manejar_nuevo_periodo(sender, instance, created, **kwargs):
    """
    Automáticamente maneja la creación de saldos cuando se crea un nuevo período contable
    """
    if created and instance.estadoPeriodo:
        with transaction.atomic():
            # 1. Inactivar todos los demás períodos
            periodoContable.objects.exclude(idPeriodo=instance.idPeriodo).update(estadoPeriodo=False)
            
            # 2. Obtener el período anterior inactivado
            periodo_anterior = periodoContable.objects.filter(estadoPeriodo=False).exclude(
                idPeriodo=instance.idPeriodo
            ).order_by('-fechaFinPeriodo').first()
            
            # 3. Si hay un período anterior, actualizar sus saldos finales
            #    y crear nuevos saldos para el nuevo período
            if periodo_anterior:
                # Para cada plan de cuenta...
                for cuenta in PlanCuenta.objects.all():
                    # Obtener el saldo del período anterior para esta cuenta
                    try:
                        saldo_anterior = SaldoContable.objects.get(
                            id_periodo=periodo_anterior,
                            id_plan_cuenta=cuenta
                        )
                        saldo_final_anterior = saldo_anterior.saldo_final
                    except SaldoContable.DoesNotExist:
                        saldo_final_anterior = 0
                    
                    # 4. Crear nuevo saldo para el nuevo período
                    SaldoContable.objects.create(
                        id_periodo=instance,
                        id_plan_cuenta=cuenta,
                        saldo_inicial=saldo_final_anterior,
                        saldo_final=0  # Inicialmente en 0
                    )
            else:
                # Primer período - crear saldos iniciales en 0
                for cuenta in PlanCuenta.objects.all():
                    SaldoContable.objects.create(
                        id_periodo=instance,
                        id_plan_cuenta=cuenta,
                        saldo_inicial=0,
                        saldo_final=0
                    )

@receiver(pre_save, sender=periodoContable)
def actualizar_saldos_al_inactivar(sender, instance, **kwargs):
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