from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.urls import reverse
from django.contrib import messages
from django.db import transaction, IntegrityError
from django.http import JsonResponse
from .models import SaldoContable
from .forms import SaldoContableForm
from apps.planCuenta.models import PlanCuenta
from apps.periodoContable.models import periodoContable

def saldos_existentes_api(request):
    periodo_id = request.GET.get('periodo')
    if not periodo_id:
        return JsonResponse({}, status=400)
    saldos = SaldoContable.objects.filter(
        id_periodo_id=periodo_id
    ).values_list('id_plan_cuenta_id', flat=True)
    return JsonResponse({str(cuenta_id): True for cuenta_id in saldos})


@login_required(login_url='login')
def saldo_contable_create(request):
    if request.method == 'POST':
        form = SaldoContableForm(request.POST)
        is_ajax = request.headers.get('x-requested-with') == 'XMLHttpRequest'

        if form.is_valid():
            try:
                with transaction.atomic():
                    saldo = form.save()  # Ahora guarda correctamente id_plan_cuenta e id_periodo
                    if is_ajax:
                        return JsonResponse({
                            'success': True,
                            'message': 'Saldo Contable creado exitosamente.',
                            'redirect_url': reverse('saldo_contable_list')
                        })
                    messages.success(request, 'Saldo Contable creado exitosamente.')
                    return redirect('saldo_contable_list')
            except IntegrityError as e:
                texto_error = str(e).lower()
                if 'unique' in texto_error or 'violates unique' in texto_error:
                    friendly = "Ya existe un Saldo Contable para ese Plan de Cuenta y Periodo."
                else:
                    friendly = "Ocurrió un error inesperado al guardar. Intente nuevamente."
                if is_ajax:
                    return JsonResponse({'success': False, 'message': friendly})
                messages.error(request, friendly)
        else:
            errores = form.errors.as_data()
            if is_ajax:
                errores_friendly = {
                    campo: [str(e.message) for e in lista]
                    for campo, lista in errores.items()
                }
                return JsonResponse({'success': False, 'errors': errores_friendly})
            for campo, lista in errores.items():
                for e in lista:
                    # e.message viene del clean() o de los error_messages que definimos
                    messages.error(request, e.message)
    else:
        form = SaldoContableForm()

    planes_cuenta = PlanCuenta.objects.filter(estadoPlanCuenta=True).order_by('codigoPlanCuenta')
    periodos = periodoContable.objects.filter(estadoPeriodo=True).order_by('-fechaInicioPeriodo')
    saldos_existentes = SaldoContable.objects.values_list('id_plan_cuenta', 'id_periodo')

    return render(request, 'saldoContable/saldoContable.html', {
        'form': form,
        'planes_cuenta': planes_cuenta,
        'periodos': periodos,
        'titulo': 'Nuevo Saldo Contable',
        'saldos_existentes': saldos_existentes
    })


@login_required(login_url='login')
def saldo_contable_list(request):
    saldos = SaldoContable.objects.all().order_by('saldo_inicial', 'saldo_final')
    return render(request, 'saldoContable/tablaSaldoContable.html', {'saldos': saldos})
