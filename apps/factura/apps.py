from django.apps import AppConfig


class FacturaConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.factura'

    def ready(self):
        # registrar señales
        try:
            import apps.factura.signals  # noqa: F401
        except Exception:
            import logging
            logging.exception("No se pudo cargar apps.factura.signals")