from django.urls import path, re_path
from apps.home import views

urlpatterns = [

    # The home page
    path('', views.index, name='home'),

    # Specific route for tipoPersona modal
    path('tipoPersonaModal/', views.tipo_persona_modal, name='tipo_persona_modal'),
    
    # Specific route for tipoFormacion modal
    path('tipoFormacionModal/', views.tipo_formacion_modal, name='tipo_formacion_modal'),
    path('deleteTF/<int:pk>/', views.delete_tipo_formacion, name='delete_tf'),
    path('reactivateTF/<int:pk>/', views.reactivate_tipo_formacion, name='reactivate_tf'),
    path('editTF/<int:pk>/', views.edit_tipo_formacion, name='edit_tf'),    
    path('tablaTipoFormaciones/', views.tabla_tipo_formaciones, name='tabla_tipo_formaciones'),    
    # Specific route for formacion modal
    path('formacionModal/', views.formacion_modal, name='formacion_modal'),
    path('editFormacion/<int:pk>/', views.edit_formacion, name='edit_formacion'),
    path('deleteFormacion/<int:pk>/', views.delete_formacion, name='delete_formacion'),
    path('reactivateFormacion/<int:pk>/', views.reactivate_formacion, name='reactivate_formacion'),
    path('tablaFormaciones/', views.tabla_formaciones, name='tabla_formaciones'),
    # Specific route for cuota 
   
    #path('cuotaModal/', views.cuota_modal, name='cuota_modal'), # URL para la creación
    #path('editCuota/<int:pk>/', views.edit_view, name='edit_cuota'), # URL para la edición	
    #path('deleteCuota/<int:pk>/', views.delete_view, name='delete_cuota'),  # URL para la eliminación lógica
    #path('reactivateCuota/<int:pk>/', views.reactivate_view, name='reactivate_cuota'),  # URL para la reactivación
    #path('tablaCuotas/', views.tabla_cuotas, name='tabla_cuotas'), # URL para la tabla de cuotas

       # Specific route for materia modal

    path('materiaModal/', views.materia_modal, name='materia_modal'),
    # Specific route for cohorte modal
    path('cohorteModal/', views.cohorte_modal, name='cohorte_modal'),
    # Specific route for cohorte modal
    path('cargoModal/', views.cargo_modal, name='cargo_modal'),
    # Specific route for cohorte modal
    path('honorarioModal/', views.honorario_modal, name='honorario_modal'),
     # Specific route for cohorte modal
    path('requisitoModal/', views.requisito_modal, name='requisito_modal'),
    # Specific route for servicio modal
    path('servicioModal/', views.servicio_modal, name='servicio_modal'),
    # Specific route for servicio modal
    path('tramiteModal/', views.tramite_modal, name='tramite_modal'),
    # Specific route for cohorte modal
    path('denominacionModal/', views.denominacion_modal, name='denominacion_modal'),
    # Specific route for banco modal
    path('bancoModal/', views.banco_modal, name='banco_modal'),
    # Specific route for banco modal
    path('monedaModal/', views.moneda_modal, name='moneda_modal'),
     # Specific route for banco modal
    path('tasaModal/', views.tasa_modal, name='tasa_modal'),
    # Specific route for tipoIngreso modal
    path('tipoMovimientoModal/', views.tipoMovimiento_modal, name='tipoMovimiento_modal'),
    # Specific route for tipoIngreso modal
    path('movimientoModal/', views.movimiento_modal, name='movimiento_modal'),


    # Matches any html file no mover de lugar 
    re_path(r'^.*\.*', views.pages, name='pages'),


]