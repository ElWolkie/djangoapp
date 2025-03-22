from django.urls import path, re_path
from . import views

urlpatterns = [
    # Ruta principal (Home)
    path('', views.index, name='home'),
    
    # Ruta para el index (sin duplicados)
    path('index/', views.index_view, name='index'),
    
    # Rutas específicas para modales
    path('tipoPersonaModal/', views.tipo_persona_modal, name='tipo_persona_modal'),
    path('tipoOfertaModal/', views.tipo_oferta_modal, name='tipo_oferta_modal'),
    path('ofertaModal/', views.oferta_modal, name='oferta_modal'),
<<<<<<< HEAD
    path('cuotaModal/', views.cuota_modal, name='cuota_modal'),
=======
    # Specific route for cuota 
   
    path('cuotaModal/', views.cuota_modal, name='cuota_modal'), # URL para la creación
    path('editCuota/<int:pk>/', views.edit_view, name='edit_cuota'), # URL para la edición	
    path('deleteCuota/<int:pk>/', views.delete_view, name='delete_cuota'),  # URL para la eliminación lógica
    path('reactivateCuota/<int:pk>/', views.reactivate_view, name='reactivate_cuota'),  # URL para la reactivación
    path('tablaCuotas/', views.tabla_cuotas, name='tabla_cuotas'), # URL para la tabla de cuotas

>>>>>>> feature/respaldo-funcionalidadesJG
       # Specific route for materia modal

    path('materiaModal/', views.materia_modal, name='materia_modal'),
    # Specific route for cohorte modal
    path('cohorteModal/', views.cohorte_modal, name='cohorte_modal'),
    # Specific route for cohorte modal
    path('cargoModal/', views.cargo_modal, name='cargo_modal'),
    # Specific route for cohorte modal
    path('contratoModal/', views.contrato_modal, name='contrato_modal'),    
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
    path('tipoIngresoModal/', views.tipoIngreso_modal, name='tipoIngreso_modal'),
    # Specific route for tipoEgreso modal
    path('tipoEgresoModal/', views.tipoEgreso_modal, name='tipoEgreso_modal'),



    # Matches any html file no mover de lugar 
    re_path(r'^.*\.*', views.pages, name='pages'),
]