from django.apps import AppConfig


class AsientocontableConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.asientoContable'

    def ready(self):
        import apps.asientoContable.signals  # Importa las señales