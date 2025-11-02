import os
import subprocess
from django.conf import settings
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Create a database backup using pg_dump (Postgres).'

    def add_arguments(self, parser):
        parser.add_argument('--output', '-o', dest='output', help='Output file path')

    def handle(self, *args, **options):
        output = options.get('output') or os.path.join(getattr(settings, 'BACKUP_DIR', settings.BASE_DIR), 'db_backup.dump')
        db = settings.DATABASES.get('default', {})
        engine = db.get('ENGINE', '')
        if 'postgresql' not in engine:
            self.stderr.write('dbbackup only supports Postgres via pg_dump')
            return

        user = db.get('USER', '')
        name = db.get('NAME', '')
        host = db.get('HOST', '')
        port = db.get('PORT', '')

        cmd = ['pg_dump', '-Fc', '-f', output, '-U', user, '-h', host, '-p', str(port), name]
        env = os.environ.copy()
        password = db.get('PASSWORD')
        if password:
            env['PGPASSWORD'] = str(password)

        self.stdout.write('Running: ' + ' '.join(cmd))
        subprocess.check_call(cmd, env=env)
        self.stdout.write('Backup created: %s' % output)
