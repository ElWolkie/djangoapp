from django.db.models.signals import post_save, post_migrate
from django.dispatch import receiver
from django.contrib.auth.models import Group
from apps.home.models import Usuarios, Servicio

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

@receiver(post_migrate)
def create_default_service(sender, **kwargs):
    # Verificamos si ya existe un servicio con id=0
    if not Servicio.objects.filter(idServicio=0).exists():
        Servicio.objects.create(
            idServicio=0,
            nombreServicio="GENERAL",
            tiempoServicio="0",
            precioServicio="0",
            estadoServicio="ACTIVO"
        )