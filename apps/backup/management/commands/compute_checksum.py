import hashlib
from django.core.management.base import BaseCommand

class Command(BaseCommand):
    help = 'Compute sha256 checksum of a file and print it'

    def add_arguments(self, parser):
        parser.add_argument('path', help='File path to compute checksum')

    def handle(self, *args, **options):
        path = options['path']
        h = hashlib.sha256()
        with open(path, 'rb') as f:
            for chunk in iter(lambda: f.read(8192), b''):
                h.update(chunk)
        self.stdout.write(h.hexdigest())
