from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import Group
from apps.home.models import Usuarios  # Asegúrate de importar tu modelo personalizado

@receiver(post_save, sender=Usuarios)
def assign_admin_group(sender, instance, **kwargs):
    admin_group, _ = Group.objects.get_or_create(name="Administrador")
    
    # Si el usuario es staff y NO es superusuario, asigna el grupo Administrador.
    if instance.is_staff and not instance.is_superuser:
        instance.groups.add(admin_group)
    else:
        # Si no se cumple la condición, remueve el grupo Administrador si está asignado.
        if admin_group in instance.groups.all():
            instance.groups.remove(admin_group)
