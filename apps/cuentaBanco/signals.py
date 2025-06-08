from django.db.models.signals import pre_save, post_save
from django.db.models import Max
from django.dispatch import receiver
from .models import Banco, CuentaBanco

@receiver(pre_save, sender=Banco)
def generar_codigo_local(sender, instance, **kwargs):
    """
    Genera automáticamente un código local si no se proporciona.
    """
    if not instance.codLocalBanco:
        # Generar código basado en las iniciales del nombre
        initials = ''.join([word[0].upper() for word in instance.nombreBanco.split()[:3]])
        last_banco = Banco.objects.aggregate(Max('idBanco'))['idBanco__max'] or 0
        instance.codLocalBanco = f"{initials}{last_banco + 1:03d}"

# @receiver(post_save, sender=CuentaBanco)
# def actualizar_saldo_inicial(sender, instance, created, **kwargs):
#     """
#     Registra automáticamente el asiento contable inicial cuando se crea una cuenta
#     con saldo disponible distinto de cero.
#     """
#     if created and instance.saldoDisponible != 0:
#         from apps.asientosContables.models import AsientoContable, DetalleAsiento
        
#         # Crear asiento contable
#         asiento = AsientoContable.objects.create(
#             descripcion=f"Apertura de cuenta {instance.numeroCuentaBanco}",
#             fecha=instance.fechaApertura,
#             estado=True
#         )
        
#         # Crear detalle de asiento
#         DetalleAsiento.objects.create(
#             asiento=asiento,
#             planCuenta=instance.planCuenta,
#             debe=instance.saldoDisponible if instance.saldoDisponible > 0 else 0,
#             haber=abs(instance.saldoDisponible) if instance.saldoDisponible < 0 else 0,
#             descripcion=f"Saldo inicial {instance.get_tipoProducto_display()}"
#         )