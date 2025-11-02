# cleanup_duplicates.py
import os
import django
from django.core.management.base import BaseCommand
from django.apps import apps
from collections import defaultdict
import json
from datetime import datetime

class Command(BaseCommand):
    help = 'Elimina duplicados de todas las tablas de la aplicación persona de forma segura'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Muestra qué duplicados se eliminarían sin ejecutar la eliminación',
        )
        parser.add_argument(
            '--backup',
            action='store_true',
            help='Crea una copia de seguridad de los registros antes de eliminar',
        )
    
    def handle(self, *args, **options):
        dry_run = options['dry_run']
        backup = options['backup']
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING('=== MODO SIMULACIÓN - No se eliminarán registros ===')
            )
        
        # Crear backup si se solicita
        if backup and not dry_run:
            self.create_backup()
        
        self.clean_all_duplicates(dry_run)
        self.verify_no_duplicates()
    
    def create_backup(self):
        """Crea una copia de seguridad de todos los registros"""
        self.stdout.write("Creando copia de seguridad...")
        
        backup_data = {}
        models_to_backup = ['TipoPersona', 'Personas', 'PersonaTP']
        
        for model_name in models_to_backup:
            Model = self.get_model('persona', model_name)
            if Model:
                records = list(Model.objects.all().values())
                backup_data[model_name] = records
                self.stdout.write(f"  - {model_name}: {len(records)} registros")
        
        # Guardar backup en archivo
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f'backup_duplicates_{timestamp}.json'
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(backup_data, f, indent=2, ensure_ascii=False, default=str)
        
        self.stdout.write(
            self.style.SUCCESS(f"Copia de seguridad guardada en: {filename}")
        )
    
    def get_model(self, app_name, model_name):
        try:
            return apps.get_model(app_name, model_name)
        except LookupError:
            self.stdout.write(
                self.style.ERROR(f"No se pudo encontrar el modelo {model_name} en la app {app_name}")
            )
            return None

    def clean_tipo_persona_duplicates(self, dry_run=False):
        """Eliminar duplicados de TipoPersona - VERSIÓN CORREGIDA"""
        TipoPersona = self.get_model('persona', 'TipoPersona')
        if not TipoPersona:
            return
        
        self.stdout.write(
            self.style.SUCCESS("\n=== Limpiando duplicados de TipoPersona ===")
        )
        
        all_tipos = TipoPersona.objects.all()
        original_count = all_tipos.count()
        self.stdout.write(f"Total de TipoPersona: {original_count}")
        
        if original_count == 0:
            self.stdout.write("No hay registros para limpiar")
            return
        
        # Agrupar por nombre en minúsculas
        duplicates = defaultdict(list)
        
        for tipo in all_tipos:
            key = tipo.nombreTP.lower().strip()
            duplicates[key].append(tipo)
        
        # SOLO considerar grupos con más de 1 elemento como duplicados
        duplicate_groups = {k: v for k, v in duplicates.items() if len(v) > 1}
        
        if not duplicate_groups:
            self.stdout.write("No se encontraron duplicados en TipoPersona")
            return
        
        self.stdout.write(f"Se encontraron {len(duplicate_groups)} grupos de duplicados")
        
        deleted_count = 0
        for nombre_lower, tipos in duplicate_groups.items():
            self.stdout.write(f"\nGrupo: '{nombre_lower}' - {len(tipos)} registros")
            
            # Mantener el más reciente (mayor fechaTP) o el que tenga ID más bajo
            tipos_sorted = sorted(tipos, key=lambda x: (x.fechaTP, x.idTP), reverse=True)
            keeper = tipos_sorted[0]
            
            self.stdout.write(f"  Se mantiene: ID {keeper.idTP} - {keeper.nombreTP} (Fecha: {keeper.fechaTP})")
            
            # Eliminar SOLO los duplicados, no el keeper
            for tipo in tipos_sorted[1:]:
                if dry_run:
                    self.stdout.write(
                        f"  [SIMULACIÓN] Eliminaría: ID {tipo.idTP} - {tipo.nombreTP}"
                    )
                else:
                    self.stdout.write(
                        f"  Eliminando: ID {tipo.idTP} - {tipo.nombreTP}"
                    )
                    tipo.delete()
                deleted_count += 1
        
        final_count = TipoPersona.objects.all().count()
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING(f"\n[SIMULACIÓN] Se eliminarían {deleted_count} registros de TipoPersona")
            )
            self.stdout.write(f"[SIMULACIÓN] Quedarían {final_count} registros")
        else:
            self.stdout.write(
                self.style.SUCCESS(f"\nRegistros eliminados de TipoPersona: {deleted_count}")
            )
            self.stdout.write(f"Registros restantes de TipoPersona: {final_count}")

    def clean_personas_duplicates(self, dry_run=False):
        """Eliminar duplicados de Personas - VERSIÓN CORREGIDA"""
        Personas = self.get_model('persona', 'Personas')
        if not Personas:
            return
        
        self.stdout.write(
            self.style.SUCCESS("\n=== Limpiando duplicados de Personas ===")
        )
        
        all_personas = Personas.objects.all()
        original_count = all_personas.count()
        self.stdout.write(f"Total de Personas: {original_count}")
        
        if original_count == 0:
            self.stdout.write("No hay registros para limpiar")
            return
        
        deleted_count = 0
        
        # 1. Duplicados por cédula (solo si la cédula no está vacía)
        cedula_duplicates = defaultdict(list)
        for persona in all_personas:
            if persona.cedula and persona.cedula.strip():
                key = persona.cedula.lower().strip()
                cedula_duplicates[key].append(persona)
        
        # SOLO grupos con más de 1 elemento
        cedula_duplicate_groups = {k: v for k, v in cedula_duplicates.items() if len(v) > 1}
        
        if cedula_duplicate_groups:
            self.stdout.write(f"\nDuplicados por cédula: {len(cedula_duplicate_groups)} grupos")
            
            for cedula, personas in cedula_duplicate_groups.items():
                self.stdout.write(f"\nCédula: '{cedula}' - {len(personas)} registros")
                
                # Mantener el más reciente (mayor idPersona)
                personas_sorted = sorted(personas, key=lambda x: x.idPersona, reverse=True)
                keeper = personas_sorted[0]
                
                self.stdout.write(f"  Se mantiene: ID {keeper.idPersona} - {keeper.nombres} {keeper.apellidos}")
                
                for persona in personas_sorted[1:]:
                    if dry_run:
                        self.stdout.write(
                            f"  [SIMULACIÓN] Eliminaría: ID {persona.idPersona} - {persona.nombres} {persona.apellidos}"
                        )
                    else:
                        self.stdout.write(
                            f"  Eliminando: ID {persona.idPersona} - {persona.nombres} {persona.apellidos}"
                        )
                        persona.delete()
                    deleted_count += 1
        
        # 2. Duplicados por RIF (solo si el RIF no está vacío)
        rif_duplicates = defaultdict(list)
        for persona in Personas.objects.all():  # Re-query para obtener los restantes
            if persona.rif and persona.rif.strip():
                key = persona.rif.lower().strip()
                rif_duplicates[key].append(persona)
        
        # SOLO grupos con más de 1 elemento
        rif_duplicate_groups = {k: v for k, v in rif_duplicates.items() if len(v) > 1}
        
        if rif_duplicate_groups:
            self.stdout.write(f"\nDuplicados por RIF: {len(rif_duplicate_groups)} grupos")
            
            for rif, personas in rif_duplicate_groups.items():
                self.stdout.write(f"\nRIF: '{rif}' - {len(personas)} registros")
                
                # Mantener el más reciente (mayor idPersona)
                personas_sorted = sorted(personas, key=lambda x: x.idPersona, reverse=True)
                keeper = personas_sorted[0]
                
                self.stdout.write(f"  Se mantiene: ID {keeper.idPersona} - {keeper.nombres} {keeper.apellidos}")
                
                for persona in personas_sorted[1:]:
                    if dry_run:
                        self.stdout.write(
                            f"  [SIMULACIÓN] Eliminaría: ID {persona.idPersona} - {persona.nombres} {persona.apellidos}"
                        )
                    else:
                        self.stdout.write(
                            f"  Eliminando: ID {persona.idPersona} - {persona.nombres} {persona.apellidos}"
                        )
                        persona.delete()
                    deleted_count += 1
        
        final_count = Personas.objects.all().count()
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING(f"\n[SIMULACIÓN] Se eliminarían {deleted_count} registros de Personas")
            )
            self.stdout.write(f"[SIMULACIÓN] Quedarían {final_count} registros")
        else:
            self.stdout.write(
                self.style.SUCCESS(f"\nRegistros eliminados de Personas: {deleted_count}")
            )
            self.stdout.write(f"Registros restantes de Personas: {final_count}")

    def clean_personatp_duplicates(self, dry_run=False):
        """Eliminar duplicados de PersonaTP - VERSIÓN CORREGIDA"""
        PersonaTP = self.get_model('persona', 'PersonaTP')
        if not PersonaTP:
            return
        
        self.stdout.write(
            self.style.SUCCESS("\n=== Limpiando duplicados de PersonaTP ===")
        )
        
        all_personatp = PersonaTP.objects.all()
        original_count = all_personatp.count()
        self.stdout.write(f"Total de PersonaTP: {original_count}")
        
        if original_count == 0:
            self.stdout.write("No hay registros para limpiar")
            return
        
        # Agrupar por la combinación de idPersona e idTP
        duplicates = defaultdict(list)
        
        for personatp in all_personatp:
            key = (personatp.idPersona_id, personatp.idTP_id)
            duplicates[key].append(personatp)
        
        # SOLO grupos con más de 1 elemento
        duplicate_groups = {k: v for k, v in duplicates.items() if len(v) > 1}
        
        if not duplicate_groups:
            self.stdout.write("No se encontraron duplicados en PersonaTP")
            return
        
        self.stdout.write(f"Se encontraron {len(duplicate_groups)} grupos de duplicados")
        
        deleted_count = 0
        for key, personatps in duplicate_groups.items():
            persona_id, tipo_id = key
            self.stdout.write(f"\nPersona {persona_id} - Tipo {tipo_id}: {len(personatps)} registros")
            
            # Mantener el más reciente (mayor fechaAsignacion)
            personatps_sorted = sorted(personatps, key=lambda x: x.fechaAsignacion, reverse=True)
            keeper = personatps_sorted[0]
            
            self.stdout.write(f"  Se mantiene: ID {keeper.id} (Fecha: {keeper.fechaAsignacion})")
            
            for personatp in personatps_sorted[1:]:
                if dry_run:
                    self.stdout.write(
                        f"  [SIMULACIÓN] Eliminaría: ID {personatp.id}"
                    )
                else:
                    self.stdout.write(
                        f"  Eliminando: ID {personatp.id}"
                    )
                    personatp.delete()
                deleted_count += 1
        
        final_count = PersonaTP.objects.all().count()
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING(f"\n[SIMULACIÓN] Se eliminarían {deleted_count} registros de PersonaTP")
            )
            self.stdout.write(f"[SIMULACIÓN] Quedarían {final_count} registros")
        else:
            self.stdout.write(
                self.style.SUCCESS(f"\nRegistros eliminados de PersonaTP: {deleted_count}")
            )
            self.stdout.write(f"Registros restantes de PersonaTP: {final_count}")

    def clean_all_duplicates(self, dry_run=False):
        """Función principal que limpia duplicados de todas las tablas"""
        self.stdout.write("Iniciando limpieza de duplicados en todas las tablas...")
        
        # Limpiar en orden para evitar problemas de integridad referencial
        self.clean_tipo_persona_duplicates(dry_run)
        self.clean_personas_duplicates(dry_run)
        self.clean_personatp_duplicates(dry_run)
        
        self.stdout.write(
            self.style.SUCCESS("\n" + "="*50)
        )
        self.stdout.write(
            self.style.SUCCESS("=== RESUMEN FINAL ===")
        )
        
        # Mostrar conteos finales
        TipoPersona = self.get_model('persona', 'TipoPersona')
        Personas = self.get_model('persona', 'Personas')
        PersonaTP = self.get_model('persona', 'PersonaTP')
        
        if TipoPersona:
            count = TipoPersona.objects.all().count()
            self.stdout.write(f"Total TipoPersona: {count}")
        if Personas:
            count = Personas.objects.all().count()
            self.stdout.write(f"Total Personas: {count}")
        if PersonaTP:
            count = PersonaTP.objects.all().count()
            self.stdout.write(f"Total PersonaTP: {count}")
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING("\n=== SIMULACIÓN COMPLETADA - No se eliminaron registros ===")
            )
            self.stdout.write(
                self.style.WARNING("Ejecute sin --dry-run para aplicar los cambios")
            )
        else:
            self.stdout.write(
                self.style.SUCCESS("\n¡Limpieza completada!")
            )

    def verify_no_duplicates(self):
        """Verificar que no quedan duplicados"""
        self.stdout.write(
            self.style.SUCCESS("\n" + "="*50)
        )
        self.stdout.write(
            self.style.SUCCESS("=== VERIFICACIÓN FINAL ===")
        )
        
        # ... (el código de verificación se mantiene igual que antes)
        # Por brevedad, no lo repito aquí, pero usa el mismo código de verificación

if __name__ == "__main__":
    # Esto es para poder ejecutar el script directamente si es necesario
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
    django.setup()
    
    command = Command()
    command.handle(dry_run=True)  # Por defecto en modo simulación