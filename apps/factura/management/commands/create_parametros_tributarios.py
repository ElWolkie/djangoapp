from django.core.management.base import BaseCommand
from django.utils import timezone
from apps.factura.models import ParametroTributario

class Command(BaseCommand):
    help = 'Crea parámetros tributarios predeterminados si no existen'

    def handle(self, *args, **kwargs):
        # Verificar si ya existen parámetros para evitar duplicados
        if ParametroTributario.objects.exists():
            self.stdout.write(self.style.WARNING('Los parámetros tributarios ya existen. No se realizaron cambios.'))
            return

        # Fecha de inicio (hoy)
        fecha_inicio = timezone.now().date()

        # Parámetros para IVA
        parametros = [
            # IVA General
            {
                'tipo': 'IVA_GENERAL',
                'aplica_a': 'HONORARIO_PROFESOR',
                'porcentaje': 16.00,
                'fecha_inicio': fecha_inicio,
                'descripcion': 'IVA general aplicable a honorarios profesionales'
            },
            {
                'tipo': 'IVA_GENERAL',
                'aplica_a': 'SERVICIO_GENERAL',
                'porcentaje': 16.00,
                'fecha_inicio': fecha_inicio,
                'descripcion': 'IVA general aplicable a servicios generales'
            },
            {
                'tipo': 'IVA_GENERAL',
                'aplica_a': 'COMPRA_BIENES',
                'porcentaje': 16.00,
                'fecha_inicio': fecha_inicio,
                'descripcion': 'IVA general aplicable a compra de bienes'
            },
            # Exenciones de IVA
            {
                'tipo': 'IVA_EXENTO',
                'aplica_a': 'INSCRIPCION',
                'porcentaje': 0.00,
                'fecha_inicio': fecha_inicio,
                'descripcion': 'Exención de IVA para inscripciones'
            },
            {
                'tipo': 'IVA_EXENTO',
                'aplica_a': 'SOLICITUD',
                'porcentaje': 0.00,
                'fecha_inicio': fecha_inicio,
                'descripcion': 'Exención de IVA para solicitudes de trámites'
            },
            # Retenciones de IVA
            {
                'tipo': 'IVA_RETENIDO_SERVICIOS',
                'aplica_a': 'HONORARIO_PROFESOR',
                'porcentaje': 75.00,
                'fecha_inicio': fecha_inicio,
                'descripcion': 'Porcentaje de retención de IVA para honorarios profesionales'
            },
            {
                'tipo': 'IVA_RETENIDO_SERVICIOS',
                'aplica_a': 'SERVICIO_GENERAL',
                'porcentaje': 75.00,
                'fecha_inicio': fecha_inicio,
                'descripcion': 'Porcentaje de retención de IVA para servicios generales'
            },
            # Retenciones de ISLR
            {
                'tipo': 'ISLR_HONORARIOS',
                'aplica_a': 'HONORARIO_PROFESOR',
                'porcentaje': 10.00,
                'fecha_inicio': fecha_inicio,
                'descripcion': 'Retención de ISLR para honorarios profesionales'
            },
            {
                'tipo': 'ISLR_SERVICIOS',
                'aplica_a': 'SERVICIO_GENERAL',
                'porcentaje': 3.00,
                'fecha_inicio': fecha_inicio,
                'descripcion': 'Retención de ISLR para servicios generales'
            },
            {
                'tipo': 'ISLR_COMPRAS',
                'aplica_a': 'COMPRA_BIENES',
                'porcentaje': 1.00,
                'fecha_inicio': fecha_inicio,
                'descripcion': 'Retención de ISLR para compras de bienes'
            },
            # Montos mínimos para exenciones
            {
                'tipo': 'MONTO_EXENCION_ISLR',
                'aplica_a': 'HONORARIO_PROFESOR',
                'valor_fijo': 1000.00,
                'porcentaje': 0.00,
                'fecha_inicio': fecha_inicio,
                'descripcion': 'Monto mínimo para aplicar retención de ISLR en honorarios'
            },
            {
                'tipo': 'MONTO_EXENCION_IVA',
                'aplica_a': 'COMPRA_BIENES',
                'valor_fijo': 200.00,
                'porcentaje': 0.00,
                'fecha_inicio': fecha_inicio,
                'descripcion': 'Monto mínimo para aplicar IVA en compras'
            }
        ]

        # Crear los parámetros en la base de datos
        for param in parametros:
            ParametroTributario.objects.create(**param)

        self.stdout.write(self.style.SUCCESS('Parámetros tributarios creados exitosamente.'))