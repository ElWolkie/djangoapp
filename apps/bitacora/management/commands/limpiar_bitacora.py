from django.core.management.base import BaseCommand
from ...models import Bitacora, ConfiguracionBitacora
from django.utils import timezone
from datetime import timedelta
import os
import csv
import json
from django.core.files.storage import default_storage
from openpyxl import Workbook
import logging
from django.conf import settings

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Elimina registros antiguos de la bitácora según configuración'
    
    def handle(self, *args, **options):
        try:
            # Obtener configuración con más detalles de depuración
            config = ConfiguracionBitacora.objects.first()
            if not config:
                self.stdout.write(self.style.WARNING("No se encontró configuración. Creando configuración por defecto..."))
                config = ConfiguracionBitacora.objects.create(
                    retencion='anual',
                    dias_personalizados=365,
                    exportar_antes_limpieza=True,
                    directorio_exportacion='backups/bitacora/'
                )
                self.stdout.write(self.style.SUCCESS("Configuración creada con valores por defecto"))
            
            # Calcular días de retención
            dias_retencion = config.get_dias_retencion()
            self.stdout.write(f"Días de retención configurados: {dias_retencion}")
            
            if dias_retencion <= 0:
                self.stdout.write(self.style.WARNING("Retención desactivada, no se eliminarán registros"))
                return
            
            # Calcular fecha límite con depuración
            fecha_limite = timezone.now() - timedelta(days=dias_retencion)
            self.stdout.write(f"Fecha límite para eliminación: {fecha_limite}")
            
            # Obtener registros a eliminar con conteo
            registros_a_eliminar = Bitacora.objects.filter(fecha_hora__lt=fecha_limite)
            cantidad_registros = registros_a_eliminar.count()
            self.stdout.write(f"Registros encontrados para eliminar: {cantidad_registros}")
            
            # Exportar antes de eliminar si está configurado
            if config.exportar_antes_limpieza and cantidad_registros > 0:
                self.stdout.write("Iniciando exportación de registros...")
                self.exportar_registros(registros_a_eliminar, config.directorio_exportacion)
            
            # Eliminar registros si existen
            if cantidad_registros > 0:
                registros_a_eliminar.delete()
                self.stdout.write(self.style.SUCCESS(
                    f"Eliminados {cantidad_registros} registros anteriores a {fecha_limite}"
                ))
            else:
                self.stdout.write(self.style.WARNING("No se encontraron registros para eliminar"))
            
            # Actualizar fecha de última limpieza
            config.ultima_limpieza = timezone.now()
            config.save()
            self.stdout.write("Fecha de última limpieza actualizada")
            
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"Error al limpiar bitácora: {str(e)}"))
            logger.exception("Error crítico en limpieza de bitácora")
            
    def exportar_registros(self, registros, directorio):
        """Exporta registros a un archivo CSV, Excel y JSON"""
        fecha_exportacion = timezone.now().strftime('%Y%m%d_%H%M%S')
        
        # Crear directorio si no existe usando ruta física
        full_dir_path = os.path.join(settings.MEDIA_ROOT, directorio)
        if not os.path.exists(full_dir_path):
            os.makedirs(full_dir_path, exist_ok=True)
        
        # Exportar a CSV
        self.exportar_csv(registros, full_dir_path, fecha_exportacion)
        
        # Exportar a Excel
        self.exportar_excel(registros, full_dir_path, fecha_exportacion)
        
        # Exportar a JSON
        self.exportar_json(registros, full_dir_path, fecha_exportacion)
    
    def exportar_csv(self, registros, directorio, fecha_exportacion):
        """Exporta a formato CSV"""
        nombre_archivo = f"bitacora_backup_{fecha_exportacion}.csv"
        ruta_completa = os.path.join(directorio, nombre_archivo)
        
        try:
            with open(ruta_completa, 'w', encoding='utf-8', newline='') as csvfile:
                writer = csv.writer(csvfile)
                # Escribir encabezados
                writer.writerow([
                    'fecha_hora', 'severidad', 'accion', 'usuario', 
                    'modelo_afectado', 'objeto_id', 'descripcion', 'ip'
                ])
                
                # Escribir registros
                for registro in registros:
                    # Obtener nombre de usuario usando idPersona
                    if registro.usuario and registro.usuario.idPersona:
                        username = f"{registro.usuario.idPersona.nombres} {registro.usuario.idPersona.apellidos}"
                    else:
                        username = 'Sistema'
                    
                    writer.writerow([
                        registro.fecha_hora.isoformat(),
                        registro.severidad,
                        registro.accion,
                        username,
                        registro.modelo_afectado,
                        registro.objeto_id,
                        registro.descripcion,
                        registro.ip
                    ])
            
            self.stdout.write(f"Exportados {registros.count()} registros a CSV: {ruta_completa}")
        except Exception as e:
            self.stderr.write(f"Error al exportar CSV: {str(e)}")
    
    def exportar_excel(self, registros, directorio, fecha_exportacion):
        """Exporta a formato Excel"""
        nombre_archivo = f"bitacora_backup_{fecha_exportacion}.xlsx"
        ruta_completa = os.path.join(directorio, nombre_archivo)
        
        try:
            wb = Workbook()
            ws = wb.active
            ws.title = "Bitácora"
            
            # Encabezados
            headers = [
                'Fecha/Hora', 'Severidad', 'Acción', 'Usuario', 
                'Modelo Afectado', 'ID Objeto', 'Descripción', 'IP'
            ]
            ws.append(headers)
            
            # Datos
            for registro in registros:
                # Obtener nombre de usuario usando idPersona
                if registro.usuario and registro.usuario.idPersona:
                    username = f"{registro.usuario.idPersona.nombres} {registro.usuario.idPersona.apellidos}"
                else:
                    username = 'Sistema'
                
                row = [
                    registro.fecha_hora.isoformat(),
                    registro.severidad,
                    registro.accion,
                    username,
                    registro.modelo_afectado,
                    registro.objeto_id,
                    registro.descripcion,
                    registro.ip
                ]
                ws.append(row)
            
            # Guardar el archivo
            wb.save(ruta_completa)
            self.stdout.write(f"Exportados {registros.count()} registros a Excel: {ruta_completa}")
        except Exception as e:
            self.stderr.write(f"Error al exportar Excel: {str(e)}")
    
    def exportar_json(self, registros, directorio, fecha_exportacion):
        """Exporta a formato JSON"""
        nombre_archivo = f"bitacora_backup_{fecha_exportacion}.json"
        ruta_completa = os.path.join(directorio, nombre_archivo)
        
        try:
            data = []
            for registro in registros:
                # Obtener nombre de usuario usando idPersona
                if registro.usuario and registro.usuario.idPersona:
                    username = f"{registro.usuario.idPersona.nombres} {registro.usuario.idPersona.apellidos}"
                else:
                    username = 'Sistema'
                
                data.append({
                    'fecha_hora': registro.fecha_hora.isoformat(),
                    'severidad': registro.severidad,
                    'accion': registro.accion,
                    'usuario': username,
                    'modelo_afectado': registro.modelo_afectado,
                    'objeto_id': registro.objeto_id,
                    'descripcion': registro.descripcion,
                    'ip': registro.ip,
                    'cambios': registro.cambios
                })
            
            # Guardar el archivo
            with open(ruta_completa, 'w', encoding='utf-8') as jsonfile:
                json.dump(data, jsonfile, ensure_ascii=False, indent=2)
            
            self.stdout.write(f"Exportados {registros.count()} registros a JSON: {ruta_completa}")
        except Exception as e:
            self.stderr.write(f"Error al exportar JSON: {str(e)}")