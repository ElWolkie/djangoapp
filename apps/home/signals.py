from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import Group
from apps.home.models import Usuarios

@receiver(post_save, sender=Usuarios)
def assign_admin_group(sender, instance, created, **kwargs):
    # Solo actuamos en la creación del usuario
    if not created:
        return
    
    # Obtenemos (o creamos) el grupo Administrador
    admin_group, _ = Group.objects.get_or_create(name="Administrador")
    
    # Solo asignamos el grupo si es staff PERO NO es superuser
    if instance.is_staff and not instance.is_superuser:
        instance.groups.add(admin_group)