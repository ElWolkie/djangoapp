from django.apps import AppConfig


class FacturaConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.factura'

    def ready(self):
        import apps.factura.signals  # Registrar los signals para IGTF
