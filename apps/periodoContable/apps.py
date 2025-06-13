from django.apps import AppConfig

class PeriodocontableConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.periodoContable'  # Asegúrate que sea este nombre completo

    def ready(self):
        # Importa las señales para que se registren
        from . import signals