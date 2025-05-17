from django.apps import AppConfig

class BancosConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.cuentaBanco'
    verbose_name = "Gestión Bancaria"

    def ready(self):
        # Importa las señales para que se registren
        import apps.cuentaBanco.signals