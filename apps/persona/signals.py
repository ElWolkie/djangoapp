from django.db.models.signals import post_migrate
from django.dispatch import receiver
from django.apps import apps
from .models import TipoPersona, Personas, PersonaTP

@receiver(post_migrate)
def create_default_tipo_persona(sender, **kwargs):
    if sender.name == "apps.persona":  # Asegúrate de que coincida con el nombre de la app
        default_tipos = ["Usuario", "Cliente", "Proveedor", "Administrador"]
        for tipo in default_tipos:
            TipoPersona.objects.get_or_create(nombreTP=tipo, defaults={"estadoTP": "ACTIVO"})

        # Crear superusuario administrador
        admin_tipo = TipoPersona.objects.get(nombreTP="Administrador")
        admin_persona, created = Personas.objects.get_or_create(
            cedula="V-0000",
            defaults={
                "nombres": "Super",
                "apellidos": "Administrador",
                "telefono": "0000000000",
                "correo": "admin@example.com",
                "estadoPersona": "ACTIVO",
            }
        )

        if created:
            # Relacionar la persona con el tipo "Administrador"
            PersonaTP.objects.get_or_create(idPersona=admin_persona, idTP=admin_tipo)

            # Obtener el modelo personalizado de usuario
            CustomUser = apps.get_model("home", "Usuarios")

            # Crear usuario de Django vinculado a la persona
            CustomUser.objects.create_superuser(
                idPersona=admin_persona.idPersona,
                password="admin123",
                is_staff=True,
                is_superuser=True
            )


