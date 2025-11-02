from rest_framework import routers
from django.urls import path, include
from .api import BackupViewSet, BackupTaskViewSet

router = routers.DefaultRouter()
router.register(r'backups', BackupViewSet, basename='backup')
router.register(r'backup-tasks', BackupTaskViewSet, basename='backuptask')

urlpatterns = [
    path('', include(router.urls)),
]
