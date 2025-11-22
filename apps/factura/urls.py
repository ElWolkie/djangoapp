from django.urls import path
from . import views

urlpatterns = [
    # Notas
    path('notas/', views.nota_list, name='nota_list'),
    path('notas/nueva/', views.nota_create, name='nota_create'),
    path('nota/administrativa/create/', views.nota_administrativa_create, name='nota_administrativa_create'),
    path('nota/administrativa/list/', views.nota_administrativa_list, name='nota_administrativa_list'),
    # path('notas/editar/<int:pk>/', views.nota_edit, name='nota_edit'),
    # path('notas/eliminar/<int:pk>/', views.nota_delete, name='nota_delete'),
    path('notas/reporteNotaPago/<int:pk>/', views.nota_pago_pdf, name='nota_pago_pdf'),    
    # Facturas
    path('facturas/', views.factura_list, name='factura_list'),
    path('facturas/<int:pk>/', views.factura_detail, name='factura_detail'),
    path('facturas/nueva/<int:nota_id>/', views.factura_create_notas, name='factura_create'),
    path('facturas/editar/<int:pk>/', views.factura_edit, name='factura_edit'),
    path('facturas/eliminar/<int:pk>/', views.factura_delete, name='factura_delete'),
    path('facturas/cargando/<int:pk>', views.factura_cargando, name='factura_cargando'),
    path('obtener-cuotas/', views.obtener_cuotas, name='obtener_cuotas'),
    
     # PlanArticulo
    path('plan-articulo/', views.plan_articulo_list, name='plan_articulo_list'),
    path('plan-articulo/nuevo/', views.create_plan_articulo, name='plan_articulo_create'),
    path('plan-articulo/editar/<int:pk>/', views.edit_plan_articulo, name='plan_articulo_edit'),

    # Reportes
    path('facturas/reporteFacturas/', views.reporte_facturas_pdf, name='reporte_factura_pdf'),
    path('pagos/reportePagos/', views.reporte_pagos_pdf, name='reporte_pagos_pdf'),
    path('pagos/pdf/<int:pk>/', views.pago_pdf, name='pago_pdf'),
    path('facturas/generar/<int:pk>/', views.factura_generar_pdf, name='factura_generar_pdf'),
    path('facturas/cargando/<int:pk>/', views.factura_cargando, name='factura_cargando'),
    
    # Detalles de Factura
    path('factura/<int:factura_id>/detalles/', views.factura_detalle_list, name='factura_detalle_list'),
    path('facturas/<int:factura_id>/detalles/nuevo/', views.factura_detalle_create, name='factura_detalle_create'),
    path('facturas/detalles/editar/<int:pk>/', views.factura_detalle_edit, name='factura_detalle_edit'),
    path('facturas/detalles/eliminar/<int:pk>/', views.factura_detalle_delete, name='factura_detalle_delete'),

    # Pagos
    path('pagos/', views.pago_list, name='pago_list'),
    path('pagos/<int:pk>/', views.pago_detail, name='pago_detail'),
    path('pagos/nuevo/', views.pago_create, name='pago_create'),
    path('pagos/nuevo/<int:pk>/', views.pago_create, name='pago_create'),
    path('pagos/nuevoigtf/<int:pk>/', views.pago_createigtf, name='pago_createigtf'),
    path('pagos/nuevoigtf/', views.pago_createigtf, name='pago_createigtf'),
    path('pagos/editar/<int:pk>/', views.pago_edit, name='pago_edit'),
    path('pagos/eliminar/<int:pk>/', views.pago_delete, name='pago_delete'),
    path('pagos/confirmar/<int:pk>/', views.pago_confirmar, name='pago_confirmar'),
    path('pagos/cancelar/<int:pk>/', views.pago_cancelar, name='pago_cancelar'),
    path('pagosApp/', views.pagoApp_list, name='pago_App_list'),
    path('pagos/obtener-tipo-igtf/', views.obtener_tipo_igtf, name='obtener_tipo_igtf'),


    # Parámetros Tributarios
    path('parametros/', views.parametro_tributario_list, name='parametro_tributario_list'),
    path('parametros/<int:pk>/', views.parametro_tributario_detail, name='parametro_tributario_detail'),
    path('parametros/nuevo/', views.parametro_tributario_create, name='parametro_tributario_create'),
    path('parametros/editar/<int:pk>/', views.parametro_tributario_edit, name='parametro_tributario_edit'),
    path('parametros/eliminar/<int:pk>/', views.parametro_tributario_eliminar, name='parametro_tributario_eliminar'),
    path('parametros/reactivar/<int:pk>/', views.parametro_tributario_reactivar, name='parametro_tributario_reactivar'),
    path('obtener-parametros-tributarios/', views.obtener_parametros_tributarios, name='obtener_parametros_tributarios'),

]