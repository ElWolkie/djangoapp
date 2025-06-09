from django.urls import path
from . import views

urlpatterns = [
    path('', views.asiento_contable_list, name='asiento_contable_list'),
    path('nuevo/', views.asiento_contable_create, name='asiento_contable_create'),
    path('<int:pk>/', views.asiento_contable_detail, name='asiento_contable_detail'),
    path('<int:pk>/editar/', views.editar_asiento, name='editar_asiento'),
    path('asiento/eliminar/<int:id>/', views.desactivar_asiento, name='desactivar_asiento'),
    path('asiento/reactivar/<int:id>/', views.reactivar_asiento, name='reactivar_asiento'),
    path('reporteAsiento/',views.reporte_asientos_pdf, name='reporte_asientos_pdf' ),
    path('<int:pk>/detalle/nuevo/', views.detalle_asiento_create, name='detalle_asiento_create'),
    path('detalle/<int:pk>/editar/', views.editar_asiento_detalle, name='editar_asiento_detalle'),
    path('asiento-contable/<int:pk>/detalles/', views.asiento_contable_detalles, name='asiento_contable_detalles'),
    
    # path('detalle/<int:pk>/eliminar/', views.detalle_asiento_delete, name='detalle_asiento_delete'),
]