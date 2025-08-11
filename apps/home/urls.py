from django.urls import path, re_path
from django.contrib import admin
from . import views
from .views import registrar_usuario

urlpatterns = [
    # Ruta principal (Home)
    path('', views.home, name='home'),
    path('contabilidad/', views.contabilidad, name='contabilidad'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),

    # Rutas específicas para usuarios
    path('usuarios/', views.lista_usuarios, name='lista_usuarios'),
    path('verificar-cedula/', views.verificar_cedula, name='verificar_cedula'),
    path('recover-password/', views.recover_password, name='recover_password'),
    path('registrar-usuario/', registrar_usuario, name='registrar_usuario'),
    path('asignar_grupos/<int:idUsuario>/', views.asignar_grupos, name='asignar_grupos'),
    path('editar_usuario/<int:pk>/', views.editar_usuario, name='editar_usuario'),
    path('desactivar_usuario/<int:pk>/', views.desactivar_usuario, name='desactivar_usuario'),
    path('eliminar_usuario/<int:pk>/', views.eliminar_usuario, name='eliminar_usuario'),

    # Rutas específicas para configuracion
    path('configuracion/', views.configuracion, name='configuracion'),
    path('actualizar-monedas/', views.actualizar_monedas_api, name='actualizar_monedas_api'),
    path('monedas/', views.tabla_monedas, name='tabla_monedas'),
    path('actualizar-bancos/', views.actualizar_bancos_api, name='actualizar_bancos_api'),
    path('bancos/', views.tabla_bancos, name='tabla_bancos'),

    # Specific route for tipoFormacion modal
    path('tipoFormacionModal/', views.tipoFormacion_modal, name='tipoFormacion_modal'),
    path('delete_tipoFormacion/<int:pk>/', views.delete_tipoFormacion, name='delete_tipoFormacion'),
    path('desactivar_tipoFormacion/<int:pk>/', views.desactivar_tipoFormacion, name='desactivar_tipoFormacion'),
    path('reactivate_tipoFormacion/<int:pk>/', views.reactivate_tipoFormacion, name='reactivate_tipoFormacion'),
    path('edit_tipoFormacion/<int:pk>/', views.edit_tipoFormacion, name='edit_tipoFormacion'),    
    path('tablaTipoFormacion/', views.tabla_tipoFormacion, name='tabla_tipoFormacion'),
    path('reporte-tipo-formacion/', views.reporte_tipo_formacion_pdf, name='reporte_tipo_formacion_pdf'),

  

    # Specific route for cuotas Formacion ###########################################

   # Specific route for formacion modal
    path('cuotaFormacion/<int:idFormacion>/', views.registrar_cuota_formacion, name='registrar_cuota_formacion'),
    path('cuotaFormacion/', views.registrar_cuota_formacion, name='registrar_cuota_formacion'),
    path('reporte-cuotas-formacion/', views.reporte_cuotas_formacion_pdf, name='reporte_cuotas_formacion_pdf'),
    path('editCuotaFormacion/<int:pk>/', views.edit_cuota_formacion, name='edit_cuota_formacion'),
    path('desactivarCuotaFormacion/<int:pk>/', views.desactivar_cuota_formacion, name='desactivar_cuota_formacion'),
    path('activarCuotaFormacion/<int:pk>/', views.activar_cuota_formacion, name='activar_cuota_formacion'),
    path('tablaCuotaFormacion/', views.consultar_cuota_formacion, name='consultar_cuota_formacion'),

    ##########################################################3333

    # Specific route for formacion modal
    path('formacionModal/', views.formacion_modal, name='formacion_modal'),
    path('editFormacion/<int:pk>/', views.edit_formacion, name='edit_formacion'),
    path('reactivateFormacion/<int:pk>/', views.reactivate_formacion, name='reactivate_formacion'),
    path('desactivar_formacion/<int:pk>/', views.desactivar_formacion, name='desactivar_formacion'),
    path('tablaFormaciones/', views.tabla_formaciones, name='tabla_formaciones'),
    path('reporte-formaciones/', views.reporte_formaciones_pdf, name='reporte_formaciones_pdf'),

       # Specific route for materia modal
    path('materiaModal/', views.materia_modal, name='materia_modal'),
    path('editMateria/<int:pk>/', views.edit_materias, name='edit_materias'),
    path('deleteMateria/<int:pk>/', views.delete_materias, name='delete_materias'),
    path('desactivarMateria/<int:pk>/', views.desactivar_materias, name='desactivar_materias'),
    path('reactivateMateria/<int:pk>/', views.reactivate_materias, name='reactivate_materias'),
    path('tablaMaterias/', views.tabla_materias, name='tabla_materias'),
    path('reporte-materias/', views.reporte_materias_pdf, name='reporte_materias_pdf'),

    # Specific route for cohorte modal
    path('cohorteModal/', views.cohorte_modal, name='cohorte_modal'),
    path('editCohorte/<int:pk>/', views.edit_cohorte, name='edit_cohorte'),
    path('deleteCohorte/<int:pk>/', views.delete_cohorte, name='delete_cohorte'),
    path('desactivarCohorte/<int:pk>/', views.desactivar_cohorte, name='desactivar_cohorte'),
    path('reactivateCohorte/<int:pk>/', views.reactivate_cohorte, name='reactivate_cohorte'),
    path('tablaCohorte/', views.tabla_cohortes, name='tabla_cohortes'),
    path('reporte-cohortes/', views.reporte_cohortes_pdf, name='reporte_cohortes_pdf'),

    # Ruta especificica para cargo modal
    path('cargoModal/', views.cargo_modal, name='cargo_modal'),
    path('editCargo/<int:pk>/', views.edit_cargo, name='edit_cargo'),
    path('deleteCargo/<int:pk>/', views.delete_cargo, name='delete_cargo'),
    path('desactivar_cargo/<int:pk>/', views.desactivar_cargo, name='desactivar_cargo'),
    path('reactivateCargo/<int:pk>/', views.reactivate_cargo, name='reactivate_cargo'),
    path('reporteCargo/', views.reporte_cargos_pdf, name='reporte_cargos_pdf'),
    path('tablaCargo/', views.tabla_cargos, name='tabla_cargos'),


     # Specific route for cohorte modal
    path('requisitoModal/', views.requisito_modal, name='requisito_modal'),
    path('editRequisito/<int:pk>/', views.edit_requisito, name='edit_requisito'),
    path('deleteRequisito/<int:pk>/', views.delete_requisito, name='delete_requisito'),
    path('desactivar_requisito/<int:pk>/', views.desactivar_requisito, name='desactivar_requisito'),
    path('reactivateRequisito/<int:pk>/', views.reactivate_requisito, name='reactivate_requisito'),
    path('tablaRequisitos/', views.tabla_requisitos, name='tabla_requisitos'),
    path('reporte-requisitos/', views.reporte_requisitos_pdf, name='reporte_requisitos_pdf'),

    # Specific route for servicio modal
    path('servicioModal/', views.servicio_modal, name='servicio_modal'),
    path('editServicio/<int:pk>/', views.edit_servicio, name='edit_servicio'),
    path('deleteServicio/<int:pk>/', views.delete_servicio, name='delete_servicio'),
    path('desactivar_servicio/<int:pk>/', views.desactivar_servicio, name='desactivar_servicio'),
    path('reactivateServicio/<int:pk>/', views.reactivate_servicio, name='reactivate_servicio'),
    path('tablaServicios/', views.tabla_servicios, name='tabla_servicios'),
    path('reporte-servicios/', views.reporte_servicios_pdf, name='reporte_servicios_pdf'),

    # Specific route for tramite modal
    path('tramiteModal/', views.tramite_modal, name='tramite_modal'),
    path('editTramite/<int:pk>/', views.edit_tramite, name='edit_tramite'),
    path('deleteTramite/<int:pk>/', views.delete_tramite, name='delete_tramite'),
    path('desactivar_tramite/<int:pk>/', views.desactivar_tramite, name='desactivar_tramite'),
    path('reactivateTramite/<int:pk>/', views.reactivate_tramite, name='reactivate_tramite'),
    path('tablaTramites/', views.tabla_tramites, name='tabla_tramites'),
    path('reporte-tramites/', views.reporte_tramites_pdf, name='reporte_tramites_pdf'),

    # Specific route for denominacion modal
    path('denominacionModal/', views.denominacion_modal, name='denominacion_modal'),
    path('editDenominacion/<int:pk>/', views.edit_denominacion, name='edit_denominacion'),
    path('deleteDenominacion/<int:pk>/', views.delete_denominacion, name='delete_denominacion'),
    path('desactivar_denominacion/<int:pk>/', views.desactivar_denominacion, name='desactivar_denominacion'),
    path('reactivateDenominacion/<int:pk>/', views.reactivate_denominacion, name='reactivate_denominacion'),
    path('tablaDenominaciones/', views.tabla_denominaciones, name='tabla_denominaciones'),
    path('reporte-denominaciones/', views.reporte_denominaciones_pdf, name='reporte_denominaciones_pdf'),


    # Specific route for banco modal
    path('bancoModal/', views.banco_modal, name='banco_modal'),
    path('editBanco/<int:pk>/', views.edit_banco, name='edit_banco'),
    path('deleteBanco/<int:pk>/', views.delete_banco, name='delete_banco'),
    path('desactivar_banco/<int:pk>/', views.desactivar_banco, name='desactivar_banco'),
    path('reactivateBanco/<int:pk>/', views.reactivate_banco, name='reactivate_banco'),
    path('tablaBancos/', views.tabla_bancos, name='tabla_bancos'),
    path('reporte-bancos/', views.reporte_bancos_pdf, name='reporte_bancos_pdf'),


    # Specific route for moneda modal
    path('monedaModal/', views.moneda_modal, name='moneda_modal'),
    path('editMoneda/<int:pk>/', views.edit_moneda, name='edit_moneda'),
    path('deleteMoneda/<int:pk>/', views.delete_moneda, name='delete_moneda'),
    path('desactivar_moneda/<int:pk>/', views.desactivar_moneda, name='desactivar_moneda'),
    path('reactivateMoneda/<int:pk>/', views.reactivate_moneda, name='reactivate_moneda'),
    path('tablaMonedas/', views.tabla_monedas, name='tabla_monedas'),
    path('reporte-monedas/', views.reporte_monedas_pdf, name='reporte_monedas_pdf'),

    # Specific route for tasa modal
    path('tasaModal/', views.tasa_modal, name='tasa_modal'),
    path('editTasa/<int:pk>/', views.edit_tasa, name='edit_tasa'),
    path('deleteTasa/<int:pk>/', views.delete_tasa, name='delete_tasa'),
    path('desactivar_tasa/<int:pk>/', views.desactivar_tasa, name='desactivar_tasa'),
    path('reactivateTasa/<int:pk>/', views.reactivate_tasa, name='reactivate_tasa'),
    path('tablaTasas/', views.tabla_tasas, name='tabla_tasas'),
    path('reporte-tasas/', views.reporte_tasas_pdf, name='reporte_tasas_pdf'),



    # Ruta espicifica para tipoIngreso modal
    path('tipoMovimientoModal/', views.tipoMovimiento_modal, name='tipoMovimiento_modal'),
    path('editTipoMovimiento/<int:pk>/', views.edit_tipoMovimiento, name='edit_tipoMovimiento'),
    path('editTipoMovimiento/delete/<int:pk>/', views.delete_tipoMovimiento, name='delete_tipoMovimiento'),
    path('editTipoMovimiento/reactivate/<int:pk>/', views.reactivate_tipoMovimiento, name='reactivate_tipoMovimiento'),
    path('desactivar_tipoMovimiento/<int:pk>/', views.desactivar_tipoMovimiento, name='desactivar_tipoMovimiento'),
    path('tabla_tipoMovimiento/', views.tabla_tipoMovimiento, name='tabla_tipoMovimiento'),
    
    # Ruta espicifica para tipoEgreso modal
    path('tipo-egresos/', views.tabla_tipoEgresos, name='tabla_tipoEgresos'),
    path('tipoEgresoModal/', views.tipoEgreso_modal, name='tipoEgreso_modal'),
    path('editTipoEgresos/<int:pk>/', views.edit_tipoEgresos, name='edit_tipoEgresos'),
    path('delete_tipoEgreso/<int:pk>/', views.delete_tipoEgreso, name='delete_tipoEgreso'),
    path('reactivate_tipoEgreso/<int:pk>/', views.reactivate_tipoEgreso, name='reactivate_tipoEgreso'),
    path('desactivar_tipoEgreso/<int:pk>/', views.desactivar_tipoEgreso, name='desactivar_tipoEgreso'),

    # Ruta espicifica para Egresos
    path('egresos/', views.tabla_egreso, name='tabla_egresos'),
    path('Egreso_Modal/', views.egreso_modal, name='egreso_modal'),
    path('editEgreso/<str:naturaleza>/<int:idMovimiento>/', views.edit_egreso, name='edit_egreso'),
    path('delete_Egreso/<int:pk>/', views.delete_egreso, name='delete_egreso'),
    path('reactivate_Egreso/<int:pk>/', views.reactivate_egreso, name='reactivate_egreso'),
    path('desactivar_Egreso/<int:pk>/', views.desactivar_egreso, name='desactivar_egreso'),

    # Ruta espicifica para tipoIngreso modal
    path('tipo-ingresos/', views.tabla_tipoIngresos, name='tabla_tipoIngresos'),
    path('tipoIngresoModal/', views.tipoIngreso_modal, name='tipoIngreso_modal'),
    path('editTipoIngresos/<int:pk>/', views.edit_tipoIngresos, name='edit_tipoIngresos'),
    path('delete_tipoIngreso/<int:pk>/', views.delete_tipoIngreso, name='delete_tipoIngreso'),
    path('reactivate_tipoIngreso/<int:pk>/', views.reactivate_tipoIngreso, name='reactivate_tipoIngreso'),
    path('desactivar_tipoIngreso/<int:pk>/', views.desactivar_tipoIngreso, name='desactivar_tipoIngreso'),

    #Ruta espicifica para Ingresos
    path('ingresos/', views.tabla_ingreso, name='tabla_ingresos'),
    path('Ingreso_Modal/', views.ingreso_modal, name='ingreso_modal'),
    path('editIngreso/<str:naturaleza>/<int:idMovimiento>/', views.edit_ingreso, name='edit_ingreso'),
    path('delete_Ingreso/<int:pk>/', views.delete_ingreso, name='delete_ingreso'),
    path('reactivate_Ingreso/<int:pk>/', views.reactivate_ingreso, name='reactivate_ingreso'),
    path('desactivar_Ingreso/<int:pk>/', views.desactivar_ingreso, name='desactivar_ingreso'),

    # Ruta espicifica para Movimimientos
    path('movimientoModal/', views.movimiento_modal, name='movimiento_modal'),
    path('editMovimiento/<int:pk>/', views.edit_movimiento, name='edit_movimiento'),
    path('deleteMovimiento/<int:pk>/', views.delete_movimiento, name='delete_movimiento'),
    path('reactivateMovimiento/<int:pk>/', views.reactivate_movimiento, name='reactivate_movimiento'),

    # Ruta espicifica para Errores
    path('403/', views.page_403, name='page-403'),

    # Matches any html file no mover de lugar 
    re_path(r'^.*\.*', views.pages, name='pages'),
]
