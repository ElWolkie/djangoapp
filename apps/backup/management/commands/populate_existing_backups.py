import os
import hashlib
from django.core.management.base import BaseCommand
from django.conf import settings
from django.utils import timezone
from apps.backup.models import Backup

def compute_checksum(file_path):
    """Calcula el checksum SHA256 de un archivo"""
    h = hashlib.sha256()
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            h.update(chunk)
    return h.hexdigest()

class Command(BaseCommand):
    help = 'Registra backups existentes en el directorio en la base de datos'

    def handle(self, *args, **options):
        backup_dir = getattr(settings, 'BACKUP_DIR', None) or os.path.join(settings.BASE_DIR, 'backups')
        
        if not os.path.exists(backup_dir):
            self.stdout.write(self.style.ERROR(f'Directorio de backups no existe: {backup_dir}'))
            return

        count = 0
        for filename in os.listdir(backup_dir):
            if filename.endswith('.dump'):
                file_path = os.path.join(backup_dir, filename)
                
                # Verificar si ya existe en la base de datos
                if not Backup.objects.filter(name=filename).exists():
                    try:
                        file_size = os.path.getsize(file_path)
                        checksum = compute_checksum(file_path)
                        
                        # Usar la hora actual como fecha de creación
                        Backup.objects.create(
                            name=filename,
                            usuario='system',
                            tipo='full',
                            ruta_storage=file_path,
                            tamaño=file_size,
                            checksum=checksum
                        )
                        count += 1
                        self.stdout.write(f'Registrado: {filename}')
                    except Exception as e:
                        self.stdout.write(self.style.ERROR(f'Error con {filename}: {str(e)}'))
                else:
                    self.stdout.write(f'Ya existe: {filename}')

        self.stdout.write(self.style.SUCCESS(f'Se registraron {count} nuevos backups'))