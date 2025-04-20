from django.http import JsonResponse, HttpResponse, HttpResponseRedirect
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.template import loader
from django.db.models import OuterRef, Subquery, Max
from django.urls import reverse
from django.contrib import messages

from django.template.loader import render_to_string
from .forms import TipoFormacionForm, FormacionForm, MateriaForm, CohorteForm, CargoForm, RequisitoForm, ServicioForm, TramiteForm, DenominacionForm, BancoForm, MonedaForm, TasaForm, TipoMovimientoForm, MovimientoForm
from .models import  TipoFormacion, Formacion, Materia, Cohorte, Cargo, Requisito, Servicio, Tramite, Denominacion, Banco, Moneda, Tasa,Movimiento, TipoMovimiento
from apps.persona.models import Personas, PersonaTP, TipoPersona
from apps.persona.forms import TipoPersonaForm, PersonaForm
from apps.honorario.models import Honorario

@csrf_exempt
def formacion_modal(request):
    if request.method == 'POST':
        form = FormacionForm(request.POST)
        if form.is_valid():
            form.save()
            return JsonResponse({'success': True, 'message': 'Registro exitoso.'})
        else:
            errors = {field: error for field, error in form.errors.items()}
            return JsonResponse({'success': False, 'errors': errors})
    else:
        form = FormacionForm()
        tipos_formacion = TipoFormacion.objects.all()  # Obtener los tipos de formación
    return render(request, 'home/formaciones.html', {'form': form, 'tipos_formacion': tipos_formacion})

@csrf_exempt
def edit_formacion(request, pk):
    formacion = get_object_or_404(Formacion, pk=pk)
    if request.method == 'POST':
        form = FormacionForm(request.POST, instance=formacion)
        if form.is_valid():
            form.save()
            return JsonResponse({'success': True, 'message': 'Formación actualizada exitosamente.'})
        else:
            errors = {field: error for field, error in form.errors.items()}
            return JsonResponse({'success': False, 'errors': errors})
    else:
        form = FormacionForm(instance=formacion)
        tipos_formacion = TipoFormacion.objects.all()
        return render(request, 'home/modales/editFormaciones.html', {
            'form': form,
            'formacion': formacion,
            'tipos_formacion': tipos_formacion
        })

@csrf_exempt
def delete_formacion(request, pk):
    instance = get_object_or_404(Formacion, pk=pk)
    instance.estadoFormacion = 'INACTIVO'
    instance.save()
    return JsonResponse({'success': True, 'message': 'Eliminación lógica exitosa.'})

@csrf_exempt
def reactivate_formacion(request, pk):
    instance = get_object_or_404(Formacion, pk=pk)
    instance.estadoFormacion = 'ACTIVO'
    instance.save()
    return JsonResponse({'success': True, 'message': 'Reactivación exitosa.'})

def tabla_formaciones(request):
    if request.user.is_superuser:
        formaciones = Formacion.objects.select_related('idTF').all().distinct  # Usar select_related para optimizar la consulta
    else:
        formaciones = Formacion.objects.select_related('idTF').filter(estadoFormacion='ACTIVO').distinct  # Filtrar solo las activas
    return render(request, 'home/tablaFormaciones.html', {'formaciones': formaciones})

# Tipo de formación
@csrf_exempt
def tipo_formacion_modal(request):
    if request.method == 'POST':
        form = TipoFormacionForm(request.POST)
        if form.is_valid():
            form.save()
            return JsonResponse({'success': True, 'message': 'Registro exitoso.'})
        else:
            errors = {field: error for field, error in form.errors.items()}
            return JsonResponse({'success': False, 'errors': errors})
    else:
        form = TipoFormacionForm()
    return render(request, 'home/tipoFormacion.html', {'form': form})

@csrf_exempt
def edit_tipo_formacion(request, pk):
    instance = get_object_or_404(TipoFormacion, pk=pk)
    if request.method == 'POST':
        form = TipoFormacionForm(request.POST, instance=instance)
        if form.is_valid():
            form.save()
            return JsonResponse({'success': True, 'message': 'Edición exitosa.'})  # Respuesta JSON
        else:
            errors = {field: error for field, error in form.errors.items()}
            return JsonResponse({'success': False, 'errors': errors})  # Respuesta JSON con errores
    else:
        form = TipoFormacionForm(instance=instance)
    return render(request, 'home/modales/editTipoFormacion.html', {'form': form, 'tipoFormacion': instance})


@csrf_exempt
def delete_tipo_formacion(request, pk):
    instance = get_object_or_404(TipoFormacion, pk=pk)
    instance.estadoTipoFormacion = 'INACTIVO'
    instance.save()
    return JsonResponse({'success': True, 'message': 'Eliminación lógica exitosa.'})

@csrf_exempt
def reactivate_tipo_formacion(request, pk):
    instance = get_object_or_404(TipoFormacion, pk=pk)
    instance.estadoTipoFormacion = 'ACTIVO'
    instance.save()
    return JsonResponse({'success': True, 'message': 'Reactivación exitosa.'})

def tabla_tipo_formaciones(request):
    tipo_formaciones = TipoFormacion.objects.all()

    return render(request, 'home/tablaTipoFormaciones.html', {'tipo_formaciones': tipo_formaciones})


#Materia
@csrf_exempt
def materia_modal(request):
    if request.method == 'POST':
        form = MateriaForm(request.POST)
        if form.is_valid():
            form.save()
            return JsonResponse({'success': True, 'message': 'Registro exitoso.'})
        else:
            errors = {field: error for field, error in form.errors.items()}
            return JsonResponse({'success': False, 'errors': errors})
    else:
        form = MateriaForm()
    return render(request, 'home/materia_modal.html', {'form': form})

@csrf_exempt
def edit_materias(request, pk):
    instance = get_object_or_404(Materia, pk=pk)
    if request.method == 'POST':
        form = MateriaForm(request.POST, instance=instance)
        if form.is_valid():
            form.save()
            return JsonResponse({'success': True, 'message': 'Edición exitosa.'})
        else:
            errors = {field: error for field, error in form.errors.items()}
            return JsonResponse({'success': False, 'errors': errors})
    else:
        form = MateriaForm(instance=instance)
        formaciones = Formacion.objects.all()  # Corregir nombre de variable

    return render(request, 'home/modales/editMaterias.html', {   
        'form': form,
        'formaciones': formaciones, 
        'materia': instance  
    })

@csrf_exempt
def delete_materias(request, pk):
    instance = get_object_or_404(Materia, pk=pk)
    instance.estadoMateria = 'INACTIVO'
    instance.save()
    return JsonResponse({'success': True, 'message': 'Eliminación lógica exitosa.'})

@csrf_exempt
def reactivate_materias(request, pk):
    instance = get_object_or_404(Materia, pk=pk)
    instance.estadoMateria = 'ACTIVO'
    instance.save()
    return JsonResponse({'success': True, 'message': 'Reactivación exitosa.'})

def tabla_materias(request):
    materias = Materia.objects.all()

    return render(request, 'home/tablaMaterias.html', {'materias': materias})

#Cohorte
@csrf_exempt
def cohorte_modal(request):
    if request.method == 'POST':
        form = CohorteForm(request.POST)
        if form.is_valid():
            form.save()
            return JsonResponse({'success': True, 'message': 'Registro exitoso.'})
        else:
            errors = {field: error for field, error in form.errors.items()}
            return JsonResponse({'success': False, 'errors': errors})
    else:
        form = CohorteForm()
    return render(request, 'home/cohorte_modal.html', {'form': form})


@csrf_exempt
def edit_cohorte(request, pk):
    cohorte = get_object_or_404(Cohorte, pk=pk)
    if request.method == 'POST':
        form = CohorteForm(request.POST, instance=cohorte)
        if form.is_valid():
            form.save()
            return JsonResponse({'success': True, 'message': 'Cohorte actualizada.'})
        else:
            return JsonResponse({'success': False, 'errors': form.errors})
    else:
        form = CohorteForm(instance=cohorte)
    return render(request, 'home/modales/editCohorte.html', {'form': form, 'cohorte':cohorte})

@csrf_exempt
def delete_cohorte(request, pk):
    instance = get_object_or_404(Cohorte, pk=pk)
    instance.estadoCohorte = 'INACTIVO'
    instance.save()
    return JsonResponse({'success': True, 'message': 'Eliminación lógica exitosa.'})

@csrf_exempt
def reactivate_cohorte(request, pk):
    instance = get_object_or_404(Cohorte, pk=pk)
    instance.estadoCohorte = 'ACTIVO'
    instance.save()
    return JsonResponse({'success': True, 'message': 'Reactivación exitosa.'})

@csrf_exempt
def tabla_cohortes(request):
    cohortes = Cohorte.objects.all()
    return render(request, 'home/tablaCohortes.html', {'cohortes': cohortes})

#Cargo
@csrf_exempt
def cargo_modal(request):
    if request.method == 'POST':
        form = CargoForm(request.POST)
        if form.is_valid():
            form.save()
            return JsonResponse({'success': True, 'message': 'Registro exitoso.'})
        else:
            errors = {field: error for field, error in form.errors.items()}
            return JsonResponse({'success': False, 'errors': errors})
    else:
        form = CargoForm()
    return render(request, 'home/cargo_modal.html', {'form': form})

@csrf_exempt
def edit_cargo(request, pk):
    cargo = get_object_or_404(Cargo, pk=pk)
    if request.method == 'POST':
        form = CargoForm(request.POST, instance=cargo)
        if form.is_valid():
            form.save()
            return JsonResponse({'success': True, 'message': 'Cargo actualizado.'})
        else:
            return JsonResponse({'success': False, 'errors': form.errors})
    else:
        form = CargoForm(instance=cargo)
    return render(request, 'home/modales/editCargo.html', {'form': form, 'cargo':cargo})

@csrf_exempt
def delete_cargo(request, pk):
    instance = get_object_or_404(Cargo, pk=pk)
    instance.estadoCargo = 'INACTIVO'
    instance.save()
    return JsonResponse({'success': True, 'message': 'Eliminación lógica exitosa.'})


@csrf_exempt
def reactivate_cargo(request, pk):
    instance = get_object_or_404(Cargo, pk=pk)
    instance.estadoCargo = 'ACTIVO'
    instance.save()
    return JsonResponse({'success': True, 'message': 'Reactivación exitosa.'})

@csrf_exempt
def tabla_cargos(request):
    cargos = Cargo.objects.all()
    return render(request, 'home/tablaCargos.html', {'cargos': cargos})

#Requisito
@csrf_exempt
def requisito_modal(request):
    if request.method == 'POST':
        form = RequisitoForm(request.POST)
        if form.is_valid():
            form.save()
            return JsonResponse({'success': True, 'message': 'Registro exitoso.'})
        else:
            print(form.errors)  # esto para depurar errores
            errors = {field: error for field, error in form.errors.items()}
            return JsonResponse({'success': False, 'errors': errors})
    else:
        form = RequisitoForm()
    return render(request, 'home/requisito_modal.html', {'form': form})

@csrf_exempt
def edit_requisito(request, pk):
    requisito = get_object_or_404(Requisito, pk=pk)
    if request.method == 'POST':
        form = RequisitoForm(request.POST, instance=requisito)
        if form.is_valid():
            form.save()
            return JsonResponse({'success': True, 'message': 'requisito actualizado.'})
        else:
            return JsonResponse({'success': False, 'errors': form.errors})
    else:
        form = RequisitoForm(instance=requisito)
    return render(request, 'home/modales/editRequisito.html', {'form': form, 'requisito':requisito})

@csrf_exempt
def delete_requisito(request, pk):
    instance = get_object_or_404(Requisito, pk=pk)
    instance.estadoRequisito = 'INACTIVO'
    instance.save()
    return JsonResponse({'success': True, 'message': 'Eliminación lógica exitosa.'})


@csrf_exempt
def reactivate_requisito(request, pk):
    instance = get_object_or_404(Requisito, pk=pk)
    instance.estadoRequisito = 'ACTIVO'
    instance.save()
    return JsonResponse({'success': True, 'message': 'Reactivación exitosa.'})

@csrf_exempt
def tabla_requisitos(request):
    requisitos = Requisito.objects.all()
    return render(request, 'home/tablaRequisitos.html', {'requisitos': requisitos})


#Servicio
@csrf_exempt
def servicio_modal(request):
    if request.method == 'POST':
        form = ServicioForm(request.POST)
        if form.is_valid():
            form.save()
            return JsonResponse({'success': True, 'message': 'Registro exitoso.'})
        else:
            print(form.errors)  # esto para depurar errores
            errors = {field: error for field, error in form.errors.items()}
            return JsonResponse({'success': False, 'errors': errors})
    else:
        form = ServicioForm()
    return render(request, 'home/servicio_modal.html', {'form': form})

@csrf_exempt
def edit_servicio(request, pk):
    servicio = get_object_or_404(Servicio, pk=pk)
    if request.method == 'POST':
        form = ServicioForm(request.POST, instance=servicio)
        if form.is_valid():
            form.save()
            return JsonResponse({'success': True, 'message': 'servicio actualizado.'})
        else:
            return JsonResponse({'success': False, 'errors': form.errors})
    else:
        form = ServicioForm(instance=servicio)
    return render(request, 'home/modales/editServicio.html', {'form': form, 'servicio':servicio})


@csrf_exempt
def delete_servicio(request, pk):
    instance = get_object_or_404(Servicio, pk=pk)
    instance.estadoServicio = 'INACTIVO'
    instance.save()
    return JsonResponse({'success': True, 'message': 'Eliminación lógica exitosa.'})

@csrf_exempt
def reactivate_servicio(request, pk):
    instance = get_object_or_404(Servicio, pk=pk)
    instance.estadoServicio = 'ACTIVO'
    instance.save()
    return JsonResponse({'success': True, 'message': 'Reactivación exitosa.'})

@csrf_exempt
def tabla_servicios(request):
    servicios = Servicio.objects.all()
    return render(request, 'home/tablaServicios.html', {'servicios': servicios})

#Tramite
@csrf_exempt
def tramite_modal(request):
    if request.method == 'POST':
        form = TramiteForm(request.POST)
        if form.is_valid():
            form.save()
            return JsonResponse({'success': True, 'message': 'Registro exitoso.'})
        else:
            print(form.errors)  # esto para depurar errores
            errors = {field: error for field, error in form.errors.items()}
            return JsonResponse({'success': False, 'errors': errors})
    else:
        form = TramiteForm()
    return render(request, 'home/tramite_modal.html', {'form': form})

def edit_tramite(request, pk):
    tramite = get_object_or_404(Tramite, pk=pk)
    if request.method == 'POST':
        form = TramiteForm(request.POST, instance=tramite)
        if form.is_valid():
            form.save()
            return JsonResponse({'success': True, 'message': 'tramite actualizado.'})
        else:
            return JsonResponse({'success': False, 'errors': form.errors})
    else:
        form = TramiteForm(instance=tramite)
    return render(request, 'home/modales/editTramite.html', {'form': form, 'tramite':tramite})

@csrf_exempt
def delete_tramite(request, pk):
    instance = get_object_or_404(Tramite, pk=pk)
    instance.estadoTramite = 'INACTIVO'
    instance.save()
    return JsonResponse({'success': True, 'message': 'Eliminación lógica exitosa.'})

@csrf_exempt
def reactivate_tramite(request, pk):
    instance = get_object_or_404(Tramite, pk=pk)
    instance.estadoTramite = 'ACTIVO'
    instance.save()
    return JsonResponse({'success': True, 'message': 'Reactivación exitosa.'})

@csrf_exempt
def tabla_tramites(request):
    servicios = Servicio.objects.all()
    return render(request, 'home/tablaTramites.html', {'servicios': servicios})

#Denominacion
@csrf_exempt
def denominacion_modal(request):
    if request.method == 'POST':
        form = DenominacionForm(request.POST)
        if form.is_valid():
            form.save()
            return JsonResponse({'success': True, 'message': 'Registro exitoso.'})
        else:
            print(form.errors)  # esto para depurar errores
            errors = {field: error for field, error in form.errors.items()}
            return JsonResponse({'success': False, 'errors': errors})
    else:
        form = DenominacionForm()
    return render(request, 'home/denominacion_modal.html', {'form': form})

@csrf_exempt
def edit_denominacion(request, pk):
    instance = get_object_or_404(Denominacion, pk=pk)
    if request.method == 'POST':
        form = DenominacionForm(request.POST, instance=instance)
        if form.is_valid():
            form.save()
            return JsonResponse({'success': True, 'message': 'Edición exitosa.'})  # Respuesta JSON
        else:
            errors = {field: error for field, error in form.errors.items()}
            return JsonResponse({'success': False, 'errors': errors})  # Respuesta JSON con errores
    else:
        form = DenominacionForm(instance=instance)
    return render(request, 'home/modales/editDenominacion.html', {'form': form, 'denominacion': instance})

@csrf_exempt
def delete_denominacion(request, pk):
    instance = get_object_or_404(Denominacion, pk=pk)
    instance.estadoDenominacion = 'INACTIVO'
    instance.save()
    return JsonResponse({'success': True, 'message': 'Eliminación lógica exitosa.'})

@csrf_exempt
def reactivate_denominacion(request, pk):
    instance = get_object_or_404(Denominacion, pk=pk)
    instance.estadoDenominacion = 'ACTIVO'
    instance.save()
    return JsonResponse({'success': True, 'message': 'Reactivación exitosa.'})

def tabla_denominaciones(request):
    denominaciones = Banco.objects.all()

    return render(request, 'home/tablaDenominaciones.html', {'denominaciones': denominaciones})

#Banco
@csrf_exempt
def banco_modal(request):
    if request.method == 'POST':
        form = BancoForm(request.POST)
        if form.is_valid():
            form.save()
            return JsonResponse({'success': True, 'message': 'Registro exitoso.'})
        else:
           # print(form.errors)  # esto para depurar errores
            errors = {field: error for field, error in form.errors.items()}
            return JsonResponse({'success': False, 'errors': errors})
    else:
        form = BancoForm()
    return render(request, 'home/banco_modal.html', {'form': form})

@csrf_exempt
def edit_banco(request, pk):
    instance = get_object_or_404(Banco, pk=pk)
    if request.method == 'POST':
        form = BancoForm(request.POST, instance=instance)
        if form.is_valid():
            form.save()
            return JsonResponse({'success': True, 'message': 'Edición exitosa.'})  # Respuesta JSON
        else:
            errors = {field: error for field, error in form.errors.items()}
            return JsonResponse({'success': False, 'errors': errors})  # Respuesta JSON con errores
    else:
        form = BancoForm(instance=instance)
    return render(request, 'home/modales/editBanco.html', {'form': form, 'banco': instance})

@csrf_exempt
def delete_banco(request, pk):
    instance = get_object_or_404(Banco, pk=pk)
    instance.estadoBanco = 'INACTIVO'
    instance.save()
    return JsonResponse({'success': True, 'message': 'Eliminación lógica exitosa.'})

@csrf_exempt
def reactivate_banco(request, pk):
    instance = get_object_or_404(Banco, pk=pk)
    instance.estadoBanco = 'ACTIVO'
    instance.save()
    return JsonResponse({'success': True, 'message': 'Reactivación exitosa.'})

def tabla_bancos(request):
    bancos = Banco.objects.all()

    return render(request, 'home/tablaBancos.html', {'bancos': bancos})

#Moneda
@csrf_exempt
def moneda_modal(request):
    if request.method == 'POST':
        form = MonedaForm(request.POST)
        if form.is_valid():
            form.save()
            return JsonResponse({'success': True, 'message': 'Registro exitoso.'})
        else:
           # print(form.errors)  # esto para depurar errores
            errors = {field: error for field, error in form.errors.items()}
            return JsonResponse({'success': False, 'errors': errors})
    else:
        form = MonedaForm()
    return render(request, 'home/moneda_modal.html', {'form': form})

@csrf_exempt
def edit_moneda(request, pk):
    instance = get_object_or_404(Moneda, pk=pk)
    if request.method == 'POST':
        form = MonedaForm(request.POST, instance=instance)
        if form.is_valid():
            form.save()
            return JsonResponse({'success': True, 'message': 'Edición exitosa.'})  # Respuesta JSON
        else:
            errors = {field: error for field, error in form.errors.items()}
            return JsonResponse({'success': False, 'errors': errors})  # Respuesta JSON con errores
    else:
        form = MonedaForm(instance=instance)
    return render(request, 'home/modales/editMoneda.html', {'form': form, 'moneda': instance})

@csrf_exempt
def delete_moneda(request, pk):
    instance = get_object_or_404(Moneda, pk=pk)
    instance.estadoMoneda = 'INACTIVO'
    instance.save()
    return JsonResponse({'success': True, 'message': 'Eliminación lógica exitosa.'})

@csrf_exempt
def reactivate_moneda(request, pk):
    instance = get_object_or_404(Moneda, pk=pk)
    instance.estadoMoneda = 'ACTIVO'
    instance.save()
    return JsonResponse({'success': True, 'message': 'Reactivación exitosa.'})

def tabla_monedas(request):
    monedas = Moneda.objects.all()

    return render(request, 'home/tablaMonedas.html', {'monedas': monedas})

#Tasa
@csrf_exempt
def tasa_modal(request):
    if request.method == 'POST':
        form = TasaForm(request.POST)
        if form.is_valid():
            form.save()
            return JsonResponse({'success': True, 'message': 'Registro exitoso.'})
        else:
           # print(form.errors)  # esto para depurar errores
            errors = {field: error for field, error in form.errors.items()}
            return JsonResponse({'success': False, 'errors': errors})
    else:
        form = TasaForm()
    return render(request, 'home/tasa_modal.html', {'form': form})

@csrf_exempt
def edit_tasa(request, pk):
    instance = get_object_or_404(Tasa, pk=pk)
    if request.method == 'POST':
        form = TasaForm(request.POST, instance=instance)
        if form.is_valid():
            form.save()
            return JsonResponse({'success': True, 'message': 'Edición exitosa.'})  # Respuesta JSON
        else:
            errors = {field: error for field, error in form.errors.items()}
            return JsonResponse({'success': False, 'errors': errors})  # Respuesta JSON con errores
    else:
        form = TasaForm(instance=instance)
        monedas = Moneda.objects.all()
    return render(request, 'home/modales/editTasa.html', {'form': form, 'tasa': instance,'monedas':monedas})

@csrf_exempt
def delete_tasa(request, pk):
    instance = get_object_or_404(Tasa, pk=pk)
    instance.estadoTasa = 'INACTIVO'
    instance.save()
    return JsonResponse({'success': True, 'message': 'Eliminación lógica exitosa.'})

@csrf_exempt
def reactivate_tasa(request, pk):
    instance = get_object_or_404(Tasa, pk=pk)
    instance.estadoTasa = 'ACTIVO'
    instance.save()
    return JsonResponse({'success': True, 'message': 'Reactivación exitosa.'})

def tabla_tasas(request):
    tasas = Tasa.objects.all()

    return render(request, 'home/tablaTasas.html', {'tasas': tasas})
#Tipo Movimiento
@csrf_exempt
def tipoMovimiento_modal(request):
    if request.method == 'POST':
        form = TipoMovimientoForm(request.POST)
        if form.is_valid():
            form.save()
            return JsonResponse({'success': True, 'message': 'Registro exitoso.'})
        else:
           # print(form.errors)  # esto para depurar errores
            errors = {field: error for field, error in form.errors.items()}
            return JsonResponse({'success': False, 'errors': errors})
    else:
        form = TipoMovimientoForm()
    return render(request, 'home/tipoMovimiento_modal.html', {'form': form})

@csrf_exempt
def edit_tipoMovimiento(request, pk):
    instance = get_object_or_404(TipoMovimiento, pk=pk)
    if request.method == 'POST':
        form = TipoMovimientoForm(request.POST, instance=instance)
        if form.is_valid():
            form.save()
            return JsonResponse({'success': True, 'message': 'Edición exitosa.'})  # Respuesta JSON
        else:
            errors = {field: error for field, error in form.errors.items()}
            return JsonResponse({'success': False, 'errors': errors})  # Respuesta JSON con errores
    else:
        form = TipoMovimientoForm(instance=instance)
    return render(request, 'home/modales/editTipoMovimiento.html', {'form': form, 'TipoMovimiento': instance})

@csrf_exempt
def delete_tipoMovimiento(request, pk):
    instance = get_object_or_404(TipoMovimiento, pk=pk)
    instance.estadoTipoMovimiento = 'INACTIVO'
    instance.save()
    return JsonResponse({'success': True, 'message': 'Eliminación lógica exitosa.'})

@csrf_exempt
def reactivate_tipoMovimiento(request, pk):
    instance = get_object_or_404(TipoMovimiento, pk=pk)
    instance.estadoTipoMovimiento = 'ACTIVO'
    instance.save()
    return JsonResponse({'success': True, 'message': 'Reactivación exitosa.'})

def tabla_tipoMovimientos(request):
    TipoMovimiento = TipoMovimiento.objects.all()

    return render(request, 'home/tablaTipoMovimiento.html', {'TipoMovimiento': TipoMovimiento})

#Movimientos
@csrf_exempt
def movimiento_modal(request):
    if request.method == 'POST':
        form = MovimientoForm(request.POST)
        if form.is_valid():
            form.save()
            return JsonResponse({'success': True, 'message': 'Registro exitoso.'})
        else:
            # Agrega esta línea para depurar errores
            print(form.errors)  # Esto imprimirá los errores en la consola
            errors = {field: error for field, error in form.errors.items()}
            return JsonResponse({'success': False, 'errors': errors})
    else:
        form = MovimientoForm()
      
    return render(request, 'home/movimiento_modal.html')

@csrf_exempt
def edit_movimiento(request, pk):
    movimiento = get_object_or_404(Movimiento, pk=pk)
    if request.method == 'POST':
        form = MovimientoForm(request.POST, instance=movimiento)
        if form.is_valid():
            form.save()
            return JsonResponse({'success': True})
        return JsonResponse({'errors': form.errors}, status=400)
    else:
        form = MovimientoForm(instance=movimiento)
        tipoMovimientos = TipoMovimiento.objects.all()
        denominaciones = Denominacion.objects.all()
        bancos = Banco.objects.all()
        # Agregar 'ultima_tasa' a la subconsulta
        monedas = Moneda.objects.annotate(
            ultima_idTasa=Subquery(
                Tasa.objects.filter(idMoneda=OuterRef('idMoneda'))
                .order_by('-fechaTasa')
                .values('idTasa')[:1]
            ),
            ultima_tasa=Subquery(
                Tasa.objects.filter(idMoneda=OuterRef('idMoneda'))
                .order_by('-fechaTasa')
                .values('montoTasa')[:1]
            )
        )
        return render(request, 'home/modales/editMovimiento.html', {
            'form': form,
            'movimiento': movimiento,
            'tipoMovimientos': tipoMovimientos,
            'denominaciones': denominaciones,
            'bancos': bancos,
            'monedas': monedas,
            'naturaleza': movimiento.naturaleza
        })
@csrf_exempt
def delete_movimiento(request, pk):
    movimiento = get_object_or_404(Movimiento, pk=pk)
    movimiento.estadoMovimiento = 'INACTIVO'
    movimiento.save()
    return JsonResponse({'success': True, 'message': 'Movimiento desactivado'})

@csrf_exempt
def reactivate_movimiento(request, pk):
    movimiento = get_object_or_404(Movimiento, pk=pk)
    movimiento.estadoMovimiento = 'ACTIVO'
    movimiento.save()
    return JsonResponse({'success': True, 'message': 'Movimiento reactivado'})


#Fin 


@login_required(login_url="/login/")
def index(request):
    context = {"segment": "index"}

    html_template = loader.get_template("home/index.html")
    return HttpResponse(html_template.render(context, request))

@login_required(login_url="/login/")
def pages(request):
    context = {}
    try:
        load_template = request.path.split("/")[-1]

        if load_template == "admin":
            return HttpResponseRedirect(reverse("admin:index"))
##################################################################################################
      
 

        if load_template == "tablaTipoFormaciones.html":
            tipoFormaciones = TipoFormacion.objects.all()
            context['tipoFormaciones'] = tipoFormaciones

        context["segment"] = load_template

        if load_template == "formacion.html":
            formaciones = TipoFormacion.objects.all()
            context['formaciones'] = formaciones
        context["segment"] = load_template


        if load_template == "tablaMaterias.html":
            materias = Materia.objects.all()
            context['materias'] = materias

        context["segment"] = load_template
        
        if load_template in ["materia.html", "tablaFormaciones.html"]:
            formaciones = Formacion.objects.all()
            context['formaciones'] = formaciones
        else:
            context['formaciones'] = None  # O alguna lógica alternativa

        context["segment"] = load_template

        context["segment"] = load_template
        if load_template == "tablaCohortes.html":
            cohortes = Cohorte.objects.all()
            context['cohortes'] = cohortes

        context["segment"] = load_template

        if load_template == "tablaCargos.html":
            cargos = Cargo.objects.all()
            context['cargos'] = cargos

        context["segment"] = load_template

        if load_template in [ "honorario.html", "honorario2.html", "tablaContratos.html", "tablaHonorarios.html"]:
            personas = Personas.objects.all()
            context['personas'] = personas
            cargos = Cargo.objects.all()
            context['cargos'] = cargos
            materias = Materia.objects.all()
            context['materias'] = materias
            cohortes = Cohorte.objects.all()
            context['cohortes'] = cohortes
            honorarios = Honorario.objects.all()
            context['honorarios'] = honorarios
        context["segment"] = load_template



        if load_template == "tablaRequisitos.html":
            requisitos = Requisito.objects.all()
            context['requisitos'] = requisitos

        context["segment"] = load_template


        if load_template == "tablaServicios.html":
            servicios = Servicio.objects.all()
            context['servicios'] = servicios

        context["segment"] = load_template


        if load_template == "tablaTramites.html":
            tramites = Tramite.objects.all()
            context['tramites'] = tramites

        context["segment"] = load_template


        if load_template == "tablaDenominaciones.html":
            denominaciones = Denominacion.objects.all()
            context['denominaciones'] = denominaciones

        context["segment"] = load_template

        if load_template == "tablaBancos.html":
            bancos = Banco.objects.all()
            context['bancos'] = bancos

        context["segment"] = load_template

        if load_template == "tablaMonedas.html":
            monedas = Moneda.objects.all()
            context['monedas'] = monedas

        context["segment"] = load_template

        if load_template in [ "tablaTasas.html", "tasa.html"]:
            tasas = Tasa.objects.all()
            context['tasas'] = tasas
            monedas = Moneda.objects.all()
            context['monedas'] = monedas
        context["segment"] = load_template
        if load_template == "tablaTipoIngresos.html":
            tipoMovimientos = TipoMovimiento.objects.filter(naturaleza="ingreso")
            context['tipoMovimientos'] = tipoMovimientos

        context["segment"] = load_template
        if load_template == "tablaTipoEgresos.html":
            tipoMovimientos = TipoMovimiento.objects.filter(naturaleza="egreso")
            context['tipoMovimientos'] = tipoMovimientos

        context["segment"] = load_template


        if load_template in [ "tablaIngresos.html", "movimiento.html"]:   
            tipoMovimientos = TipoMovimiento.objects.all()
            context['tipoMovimientos'] = tipoMovimientos
            movimientos = Movimiento.objects.filter(naturaleza="ingreso")
            context['movimientos'] = movimientos
            denominaciones = Denominacion.objects.all()
            context['denominaciones'] = denominaciones   
            bancos = Banco.objects.all()
            context['bancos'] = bancos
           
            # Subconsulta para encontrar la última tasa por moneda
            subconsulta = Tasa.objects.filter(idMoneda=OuterRef('idMoneda')).order_by('-fechaTasa')

            # Obtener todas las monedas con su última tasa
            monedas_con_ultimas_tasas = Moneda.objects.annotate(
                ultima_idTasa=Subquery(subconsulta.values('idTasa')[:1]),  # Último monto de tasa
                ultima_tasa=Subquery(subconsulta.values('montoTasa')[:1]),  # Último monto de tasa
                ultima_fecha=Subquery(subconsulta.values('fechaTasa')[:1])  # Última fecha de tasa
            )

                # Imprimir las monedas y sus últimas tasas en la consola
            for moneda in monedas_con_ultimas_tasas:
                print(f"Moneda: {moneda.nombreMoneda}, Última Tasa: {moneda.ultima_tasa}, Fecha: {moneda.ultima_fecha},  Fecha: {moneda.ultima_idTasa}")

            # Agregar las monedas con sus últimas tasas al contexto
            context['monedas'] = monedas_con_ultimas_tasas

           
        context["segment"] = load_template



        if load_template in [ "tablaEgresos.html", "movimiento.html"]:   
            tipoMovimientos = TipoMovimiento.objects.all()
            context['tipoMovimientos'] = tipoMovimientos
            movimientos = Movimiento.objects.filter(naturaleza="egreso")
            context['movimientos'] = movimientos
            denominaciones = Denominacion.objects.all()
            context['denominaciones'] = denominaciones   
            bancos = Banco.objects.all()
            context['bancos'] = bancos
           
            # Subconsulta para encontrar la última tasa por moneda
            subconsulta = Tasa.objects.filter(idMoneda=OuterRef('idMoneda')).order_by('-fechaTasa')

            # Obtener todas las monedas con su última tasa
            monedas_con_ultimas_tasas = Moneda.objects.annotate(
                ultima_idTasa=Subquery(subconsulta.values('idTasa')[:1]),  # Último monto de tasa
                ultima_tasa=Subquery(subconsulta.values('montoTasa')[:1]),  # Último monto de tasa
                ultima_fecha=Subquery(subconsulta.values('fechaTasa')[:1])  # Última fecha de tasa
            )

                # Imprimir las monedas y sus últimas tasas en la consola
            for moneda in monedas_con_ultimas_tasas:
                print(f"Moneda: {moneda.nombreMoneda}, Última Tasa: {moneda.ultima_tasa}, Fecha: {moneda.ultima_fecha},  Fecha: {moneda.ultima_idTasa}")

            # Agregar las monedas con sus últimas tasas al contexto
            context['monedas'] = monedas_con_ultimas_tasas

           
        context["segment"] = load_template
        html_template = loader.get_template("home/" + load_template)
        return HttpResponse(html_template.render(context, request))

    except loader.TemplateDoesNotExist:
        html_template = loader.get_template("home/page-404.html")
        return HttpResponse(html_template.render(context, request))

    except Exception as e:
        messages.error(request, f'Error inesperado: {e}')
        html_template = loader.get_template("home/page-500.html")
        return HttpResponse(html_template.render(context, request))