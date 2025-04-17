from django.db.models.signals import post_migrate
from django.dispatch import receiver
from .models import TipoPersona

@receiver(post_migrate)
def create_default_tipo_persona(sender, **kwargs):
    if sender.name == "apps.persona":  # Asegúrate de que coincida con el nombre de la app
        default_tipos = ["Usuario", "Cliente", "Proveedor"]
        for tipo in default_tipos:
            TipoPersona.objects.get_or_create(nombreTP=tipo, defaults={"estadoTP": "Activo"})