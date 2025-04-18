from django.urls import path, re_path
from . import views

urlpatterns = [

    path('tablaHonorarios/', views.tabla_honorarios, name='tabla_honorarios'),

    # Specific route for honorario modal
    path('honorarioModal/', views.honorario_modal, name='honorario_modal'),
    path('editHonorario/<int:pk>/', views.edit_honorario, name='edit_honorario'),
    path('deleteHonorario/<int:pk>/', views.delete_honorario, name='delete_honorario'),
    path('reactivateHonorario/<int:pk>/', views.reactivate_honorario, name='reactivate_honorario'),

    # Coincide con cualquier archivo HTML (no mover de lugar)
    re_path(r'^.*\.*', views.pages, name='pages'),

]