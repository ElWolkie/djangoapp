from django.apps import AppConfig


class PersonaConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.persona'

    def ready(self):
        import apps.persona.signals  # Importa las señales 