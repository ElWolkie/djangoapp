# management/commands/cleanup_expired_backups.py
from django.core.management.base import BaseCommand
from django.utils import timezone
from backup.models import Backup
import os

class Command(BaseCommand):
    help = 'Elimina backups expirados'

    def handle(self, *args, **options):
        expired_backups = Backup.objects.filter(expiracion__lt=timezone.now())
        count = expired_backups.count()
        
        for backup in expired_backups:
            # Eliminar archivo físico
            if os.path.exists(backup.ruta_storage):
                os.remove(backup.ruta_storage)
            # Eliminar registro de la base de datos
            backup.delete()
        
        self.stdout.write(
            self.style.SUCCESS(f'Se eliminaron {count} backups expirados')
        )