from django.core.management.base import BaseCommand
from django.conf import settings
from ...models import Bitacora
from django.utils import timezone
from datetime import timedelta

class Command(BaseCommand):
    help = 'Elimina registros antiguos de la bitácora según configuración'
    
    def handle(self, *args, **options):
        # Obtener días de retención de los settings
        dias_retencion = getattr(settings, 'BITACORA_RETENCION_DIAS', 365)
        
        if dias_retencion <= 0:
            self.stdout.write("Retención desactivada, no se eliminarán registros")
            return
        
        fecha_limite = timezone.now() - timedelta(days=dias_retencion)
        
        # Eliminar registros más antiguos
        registros, _ = Bitacora.objects.filter(
            fecha_hora__lt=fecha_limite
        ).delete()
        
        self.stdout.write(self.style.SUCCESS(
            f"Eliminados {registros} registros anteriores a {fecha_limite}"
        ))