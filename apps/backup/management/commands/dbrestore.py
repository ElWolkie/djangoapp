import subprocess
import os
from django.conf import settings
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Restore a Postgres dump created by pg_dump -Fc via pg_restore'

    def add_arguments(self, parser):
        parser.add_argument('--input', '-i', dest='input', help='Input dump file path')

    def handle(self, *args, **options):
        input_file = options.get('input')
        if not input_file:
            self.stderr.write('Please provide --input /path/to/dump')
            return

        db = settings.DATABASES.get('default', {})
        engine = db.get('ENGINE', '')
        if 'postgresql' not in engine:
            self.stderr.write('dbrestore only supports Postgres via pg_restore')
            return

        user = db.get('USER', '')
        name = db.get('NAME', '')
        host = db.get('HOST', '')
        port = db.get('PORT', '')
        password = db.get('PASSWORD')

        cmd = ['pg_restore', '-c', '-d', name, '-U', user, '-h', host, '-p', str(port), input_file]
        env = os.environ.copy()
        if password:
            env['PGPASSWORD'] = str(password)

        self.stdout.write('Running: ' + ' '.join(cmd))
        subprocess.check_call(cmd, env=env)
        self.stdout.write('Restore completed')
