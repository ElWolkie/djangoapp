from django.apps import AppConfig

class BitacoraConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.bitacora'  # Nombre de importación completo
    
    def ready(self):
        # Importar señales solo cuando la app esté lista
        import apps.bitacora.signals