from django.views.generic import ListView
from .models import Bitacora
from django.db.models import Q
import csv
from django.http import HttpResponse, JsonResponse
from django.utils import timezone
from django.db.models import Value
from django.db.models.functions import Concat

class BitacoraListView(ListView):
    model = Bitacora
    template_name = 'bitacora_list.html'
    paginate_by = 25
    context_object_name = 'registros'

    def get_queryset(self):
        qs = Bitacora.objects.select_related('usuario', 'usuario__idPersona')\
            .annotate(
                nombre_completo=Concat(
                    'usuario__idPersona__nombres',
                    Value(' '),
                    'usuario__idPersona__apellidos'
                )
            )\
            .order_by('-fecha_hora')

        filtro_usuario = self.request.GET.get('usuario', '').strip()

        filtro_usuario = self.request.GET.get('usuario', '').strip()
        filtro_accion  = self.request.GET.get('accion', '').strip()
        filtro_fecha   = self.request.GET.get('fecha', '').strip()
        filtro_q       = self.request.GET.get('q', '').strip()

        if filtro_usuario:
            qs = qs.filter(
                Q(usuario__idPersona__nombres__icontains=filtro_usuario) |
                Q(usuario__idPersona__apellidos__icontains=filtro_usuario) |
                Q(nombre_completo__icontains=filtro_usuario) |
                Q(usuario__idUsuario__icontains=filtro_usuario)
            )

        if filtro_accion:
            qs = qs.filter(accion=filtro_accion)

        if filtro_fecha:
            qs = qs.filter(fecha_hora__date=filtro_fecha)

        if filtro_q:
            qs = qs.filter(
                Q(descripcion__icontains=filtro_q) |
                Q(modelo_afectado__icontains=filtro_q) |
                Q(ip__icontains=filtro_q) |
                Q(usuario__idPersona__nombres__icontains=filtro_q) |
                Q(usuario__idPersona__apellidos__icontains=filtro_q) |
                Q(usuario__idUsuario__icontains=filtro_q)
            )

        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.update({
            'filtro_usuario': self.request.GET.get('usuario', ''),
            'filtro_accion':  self.request.GET.get('accion', ''),
            'filtro_fecha':   self.request.GET.get('fecha', ''),
            'filtro_q':       self.request.GET.get('q', ''),
        })
        return ctx
    
def exportar_bitacora(request):
    # Crear una instancia de la vista de lista para reutilizar su lógica
    view = BitacoraListView()
    view.request = request
    
    # Obtener los registros filtrados
    registros = view.get_queryset()
    
    formato = request.GET.get('formato', 'csv')
    
    if formato == 'csv':
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="bitacora_{timezone.now().strftime("%Y%m%d_%H%M%S")}.csv"'
        
        writer = csv.writer(response)
        writer.writerow([
            'Fecha', 'Usuario', 'Acción', 'Modelo', 'ID Objeto', 
            'Descripción', 'IP', 'Severidad'
        ])
        
        for reg in registros:
            usuario = ""
            if reg.usuario and reg.usuario.idPersona:
                usuario = f"{reg.usuario.idPersona.nombres} {reg.usuario.idPersona.apellidos}"
            
            writer.writerow([
                reg.fecha_hora.strftime("%Y-%m-%d %H:%M"),
                usuario,
                reg.get_accion_display(),
                reg.modelo_afectado,
                reg.objeto_id,
                reg.descripcion,
                reg.ip,
                reg.get_severidad_display()
            ])
        
        return response
    
    elif formato == 'json':
        data = []
        for reg in registros:
            usuario = ""
            if reg.usuario and reg.usuario.idPersona:
                usuario = f"{reg.usuario.idPersona.nombres} {reg.usuario.idPersona.apellidos}"
            
            data.append({
                'fecha': reg.fecha_hora.isoformat(),
                'usuario': usuario,
                'accion': reg.get_accion_display(),
                'modelo': reg.modelo_afectado,
                'objeto_id': reg.objeto_id,
                'descripcion': reg.descripcion,
                'ip': reg.ip,
                'severidad': reg.get_severidad_display(),
                'cambios': reg.cambios
            })
        
        return JsonResponse(data, safe=False)
    
    elif formato == 'excel':
        try:
            from openpyxl import Workbook
        except ImportError:
            return HttpResponse("La librería openpyxl no está instalada", status=500)
        
        response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = f'attachment; filename="bitacora_{timezone.now().strftime("%Y%m%d_%H%M%S")}.xlsx"'
        
        wb = Workbook()
        ws = wb.active
        ws.title = "Bitácora"
        
        # Encabezados
        headers = [
            'Fecha', 'Usuario', 'Acción', 'Modelo', 'ID Objeto', 
            'Descripción', 'IP', 'Severidad'
        ]
        ws.append(headers)
        
        # Datos
        for reg in registros:
            usuario = ""
            if reg.usuario and reg.usuario.idPersona:
                usuario = f"{reg.usuario.idPersona.nombres} {reg.usuario.idPersona.apellidos}"
            
            row = [
                reg.fecha_hora.strftime("%Y-%m-%d %H:%M"),
                usuario,
                reg.get_accion_display(),
                reg.modelo_afectado,
                reg.objeto_id,
                reg.descripcion,
                reg.ip,
                reg.get_severidad_display()
            ]
            ws.append(row)
        
        wb.save(response)
        return response
    
    return HttpResponse("Formato no soportado", status=400)