from django.urls import path
from . import views

urlpatterns = [
    # Facturas
    path('facturas/', views.factura_list, name='factura_list'),
    path('facturas/<int:pk>/', views.factura_detail, name='factura_detail'),
    path('facturas/nueva/', views.factura_create, name='factura_create'),
    path('facturas/editar/<int:pk>/', views.factura_edit, name='factura_edit'),
    # path('facturas/eliminar/<int:pk>/', views.factura_delete, name='factura_delete'),

    # Detalles de Factura
    path('facturas/<int:factura_id>/detalles/', views.factura_detalle_list, name='factura_detalle_list'),
    path('facturas/<int:factura_id>/detalles/nuevo/', views.factura_detalle_create, name='factura_detalle_create'),
    # path('facturas/detalles/editar/<int:pk>/', views.factura_detalle_edit, name='factura_detalle_edit'),
    # path('facturas/detalles/eliminar/<int:pk>/', views.factura_detalle_delete, name='factura_detalle_delete'),

    # Pagos
    path('pagos/', views.pago_list, name='pago_list'),
    path('pagos/<int:pk>/', views.pago_detail, name='pago_detail'),
    path('pagos/nuevo/', views.pago_create, name='pago_create'),
    path('pagos/editar/<int:pk>/', views.pago_edit, name='pago_edit'),
    path('pagos/eliminar/<int:pk>/', views.pago_delete, name='pago_delete'),

    # Parámetros Tributarios
    path('parametros/', views.parametro_tributario_list, name='parametro_tributario_list'),
    path('parametros/<int:pk>/', views.parametro_tributario_detail, name='parametro_tributario_detail'),
    path('parametros/nuevo/', views.parametro_tributario_create, name='parametro_tributario_create'),
    path('parametros/editar/<int:pk>/', views.parametro_tributario_edit, name='parametro_tributario_edit'),
    path('parametros/eliminar/<int:pk>/', views.parametro_tributario_delete, name='parametro_tributario_delete'),
        path('obtener-parametros-tributarios/', views.obtener_parametros_tributarios, name='obtener_parametros_tributarios'),
]