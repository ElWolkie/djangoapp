from django.urls import path
from . import views

app_name = 'backup'

urlpatterns = [
    # Provide a plain 'backup' name for templates that use `{% url 'backup' %}`
    path('', views.backup_list, name='backup'),
    path('', views.backup_list, name='list'),
    path('create/', views.create_backup, name='create'),
    path('restore/<int:backup_id>/', views.restore_backup, name='restore'),
      # Agregar estas nuevas URLs para la API
    path('api/backups/<int:backup_id>/restore/', views.api_restore_backup, name='api_restore_backup'),
    path('api/backups/<int:backup_id>/download/', views.download_backup, name='download_backup'),
    path('api/backups/backup-tasks/<str:task_id>/', views.get_backup_task, name='get_backup_task'),
]
