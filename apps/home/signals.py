from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import Group
from apps.home.models import Usuarios

@receiver(post_save, sender=Usuarios)
def assign_admin_group(sender, instance, created, **kwargs):
    # Sólo actuamos en la creación del usuario
    if not created:
        return
    # Obtenemos (o creamos) el grupo Administrador
    admin_group, _ = Group.objects.get_or_create(name="Administrador")
    
    # Si el usuario es staff (y no importa si es superuser o no), le damos el grupo.
    if instance.is_staff:
        instance.groups.add(admin_group)
    # No hay cláusula de "else": nunca removemos grupos automáticamente.
