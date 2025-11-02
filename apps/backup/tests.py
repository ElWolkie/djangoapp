from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from .models import Backup
from django.utils import timezone


class BackupAPITest(TestCase):
    def setUp(self):
        User = get_user_model()
        self.admin = User.objects.create_superuser(username='admin', password='pass')
        # create some backups
        for i in range(7):
            Backup.objects.create(name=f'b{i}', fecha_creacion=timezone.now(), tipo='full', ruta_storage=f'/tmp/b{i}.dump')

    def test_dashboard_limits_to_5(self):
        self.client.login(username='admin', password='pass')
        resp = self.client.get('/api/backups/?page_size=5')
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn('results', data)
        self.assertLessEqual(len(data['results']), 5)
