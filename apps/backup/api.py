from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from django.db.models import Q

from .models import Backup, BackupTask, BackupAudit
from .serializers import BackupSerializer, BackupTaskSerializer

import threading
from django.core import management


class IsBackupAdmin(IsAuthenticated):
    def has_permission(self, request, view):
        return super().has_permission(request, view) and (request.user.is_superuser or request.user.is_staff)


class BackupViewSet(viewsets.ModelViewSet):
    queryset = Backup.objects.all().order_by('-fecha_creacion')
    serializer_class = BackupSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = super().get_queryset()
        desde = self.request.query_params.get('desde')
        hasta = self.request.query_params.get('hasta')
        tipo = self.request.query_params.get('type')
        if desde:
            qs = qs.filter(fecha_creacion__gte=desde)
        if hasta:
            qs = qs.filter(fecha_creacion__lte=hasta)
        if tipo:
            qs = qs.filter(tipo=tipo)
        return qs

    def list(self, request, *args, **kwargs):
        # Default dashboard: return first 5
        page_size = int(request.query_params.get('page_size', 5))
        qs = self.get_queryset()
        serializer = self.get_serializer(qs[:page_size], many=True)
        return Response({'results': serializer.data, 'count': qs.count()})

    def create(self, request, *args, **kwargs):
        # Expect metadata and ruta_storage; compute checksum server-side if file uploaded
        data = request.data.copy()
        data['usuario'] = getattr(request.user, 'username', str(request.user))
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        backup = serializer.save()
        # create audit
        BackupAudit.objects.create(backup=backup, usuario=data['usuario'], action='create')
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'], url_path='restore', permission_classes=[IsBackupAdmin])
    def restore(self, request, pk=None):
        backup = self.get_object()
        # validate checksum (basic presence check here)
        if not backup.checksum:
            return Response({'detail': 'Checksum missing; cannot restore.'}, status=status.HTTP_400_BAD_REQUEST)

        task = BackupTask.objects.create(backup=backup, usuario=getattr(request.user, 'username', str(request.user)))

        def _run_restore(task_id, backup_path):
            task = BackupTask.objects.get(id=task_id)
            task.status = 'running'
            task.started_at = timezone.now()
            task.save()
            try:
                # call management command to restore
                management.call_command('dbrestore', input=backup_path)
                task.status = 'success'
                task.result = 'Restore completed'
            except Exception as e:
                task.status = 'error'
                task.result = str(e)
            task.finished_at = timezone.now()
            task.save()
            # record audit
            BackupAudit.objects.create(backup=task.backup, usuario=task.usuario, action='restore', notes=task.result)

        thread = threading.Thread(target=_run_restore, args=(task.id, backup.ruta_storage), daemon=True)
        thread.start()
        return Response({'task_id': task.id, 'status': task.status})


class BackupTaskViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = BackupTask.objects.all().order_by('-created_at')
    serializer_class = BackupTaskSerializer
    permission_classes = [IsAuthenticated]
