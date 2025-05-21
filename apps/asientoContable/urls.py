from django.urls import path
from . import views

urlpatterns = [
    path('', views.asiento_contable_list, name='asiento_contable_list'),
    path('nuevo/', views.asiento_contable_create, name='asiento_contable_create'),
    path('<int:pk>/', views.asiento_contable_detail, name='asiento_contable_detail'),
    path('<int:pk>/editar/', views.asiento_contable_update, name='asiento_contable_update'),
    path('<int:pk>/detalle/nuevo/', views.detalle_asiento_create, name='detalle_asiento_create'),
    path('asiento-contable/<int:pk>/detalles/', views.asiento_contable_detalles, name='asiento_contable_detalles'),

    # path('detalle/<int:pk>/eliminar/', views.detalle_asiento_delete, name='detalle_asiento_delete'),
]