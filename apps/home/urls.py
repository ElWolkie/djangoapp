from django.urls import path, re_path
from . import views
from .views import login_view, index_view, logout_view, registrar_usuario

urlpatterns = [
    # Ruta principal (Home)
    path('', index_view, name='home'),  # Página principal
    path('login/', login_view, name='login'),
    path('logout/', logout_view, name='logout'),
    path('dashboard/', index_view, name='dashboard'),  # Opcional

    path('registrar-usuario/', registrar_usuario, name='registrar_usuario'),

    # Rutas específicas para modales
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

       # Specific route for materia modal
    path('materiaModal/', views.materia_modal, name='materia_modal'),
    path('editMateria/<int:pk>/', views.edit_materias, name='edit_materias'),
    path('deleteMateria/<int:pk>/', views.delete_materias, name='delete_materias'),
    path('reactivateMateria/<int:pk>/', views.reactivate_materias, name='reactivate_materias'),
    path('tablaMaterias/', views.tabla_materias, name='tabla_materias'),

    # Specific route for cohorte modal
    path('cohorteModal/', views.cohorte_modal, name='cohorte_modal'),
    path('editCohorte/<int:pk>/', views.edit_cohorte, name='edit_cohorte'),
    path('deleteCohorte/<int:pk>/', views.delete_cohorte, name='delete_cohorte'),
    path('reactivateCohorte/<int:pk>/', views.reactivate_cohorte, name='reactivate_cohorte'),

    # Specific route for cohorte modal
    path('cargoModal/', views.cargo_modal, name='cargo_modal'),
    path('editCargo/<int:pk>/', views.edit_cargo, name='edit_cargo'),
    path('deleteCargo/<int:pk>/', views.delete_cargo, name='delete_cargo'),
    path('reactivateCargo/<int:pk>/', views.reactivate_cargo, name='reactivate_cargo'),

    # Specific route for cohorte modal
    path('honorarioModal/', views.honorario_modal, name='honorario_modal'),
    path('editHonorario/<int:pk>/', views.edit_honorario, name='edit_honorario'),
    path('deleteHonorario/<int:pk>/', views.delete_honorario, name='delete_honorario'),
    path('reactivateHonorario/<int:pk>/', views.reactivate_honorario, name='reactivate_honorario'),

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