from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import Personas, Usuarios, Materia, Cohorte, Cargo, Requisito, Servicio, Tramite, Moneda, Tasa
from apps.persona.models import TipoPersona
from apps.honorario.models import Honorario
from apps.solicitud.models import Solicitud

# Personalización de la vista de Personas en el admini
class PersonaAdmin(admin.ModelAdmin):
    list_display = ('idPersona', 'cedula', 'nombres', 'apellidos', 'telefono', 'correo',  'estadoPersona', 'fechaPersona')  # Muestra estos campos en la lista
    search_fields = ('cedula', 'nombres', 'apellidos')  # Permite buscar por estos campos

# Registra el modelo con las personalizaciones
admin.site.register(Personas, PersonaAdmin)

# Personalización de la vista de TipoPersona en el admin
class TipoPersonaAdmin(admin.ModelAdmin):
    list_display = ('idTP', 'nombreTP', 'estadoTP', 'fechaTP')  # Muestra estos campos en la lista
    search_fields = ('nombreTP','estadoTP','fechaTP')  # Permite buscar por estos campos, corregido a tupla

# Registra el modelo con las personalizaciones
admin.site.register(TipoPersona, TipoPersonaAdmin)

@admin.register(Usuarios)
class UsuarioAdmin(UserAdmin):
    list_display = ('get_cedula', 'get_nombre_completo', 'is_staff', 'is_superuser')
    search_fields = ('idPersona__cedula', 'idPersona__nombres', 'idPersona__apellidos', 'idPersona__correo')
    ordering = ('idPersona',)
    readonly_fields = ('fechaUsuario', 'last_login')  # Campos de solo lectura
    
    fieldsets = (
        (None, {'fields': ('idPersona', 'password')}),
        ('Seguridad', {'fields': ('preguntaSeguridad', 'respuestaSeguridad')}),
        ('Preferencias', {'fields': ('coloresUsuario',)}),
        ('Permisos', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Fechas importantes', {'fields': ('last_login', 'fechaUsuario')}),  # Usamos solo los campos que existen
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('idPersona', 'password1', 'password2'),
        }),
    )
    
    raw_id_fields = ('idPersona',)
    list_filter = ('is_staff', 'is_superuser', 'is_active', 'groups')
    
    def get_cedula(self, obj):
        return obj.idPersona.cedula if obj.idPersona else ''
    get_cedula.short_description = 'Cédula'
    
    def get_nombre_completo(self, obj):
        return f"{obj.idPersona.nombres} {obj.idPersona.apellidos}" if obj.idPersona else ''
    get_nombre_completo.short_description = 'Nombre Completo'
    
    def get_correo(self, obj):
        return obj.idPersona.correo if obj.idPersona else ''
    get_correo.short_description = 'Correo'

# Personalización de la vista de Materia en el admin
class MateriaAdmin(admin.ModelAdmin):
    list_display = ('idMateria', 'idFormacion', 'nombreMateria', 'estadoMateria', 'fechaMateria')  # Muestra estos campos en la lista
    search_fields = ('nombreMateria','estadoMateria','fechaMateria')  # Permite buscar por estos campos, corregido a tupla

# Registra el modelo con las personalizaciones
admin.site.register(Materia, MateriaAdmin)

# Personalización de la vista de Cohorte en el admin
class CohorteAdmin(admin.ModelAdmin):
    list_display = ('idCohorte', 'nombreCohorte', 'estadoCohorte', 'fechaCohorte')  # Muestra estos campos en la lista
    search_fields = ('nombreCohorte','estadoCohorte','fechaCohorte')  # Permite buscar por estos campos, corregido a tupla

# Registra el modelo con las personalizaciones
admin.site.register(Cohorte, CohorteAdmin)

# Personalización de la vista de Cargo en el admin
class CargoAdmin(admin.ModelAdmin):
    list_display = ('idCargo', 'nombreCargo', 'estadoCargo', 'fechaCargo')  # Muestra estos campos en la lista
    search_fields = ('nombreCargo','estadoCargo','fechaCargo')  # Permite buscar por estos campos, corregido a tupla

# Registra el modelo con las personalizaciones
admin.site.register(Cargo, CargoAdmin)

# Personalización de la vista de Honorario en el admin
class HonorarioAdmin(admin.ModelAdmin):
    list_display = ('idHonorario', 'idPersona', 'idCargo', 'idCohorte', 'idMateria', 'horas', 'estadoHonorario', 'fechaHonorario')  # Muestra estos campos en la lista
    search_fields = ('idHonorario','estadoHonorario','fechaHonorario')  # Permite buscar por estos campos, corregido a tupla

# Registra el modelo con las personalizaciones
admin.site.register(Honorario, HonorarioAdmin)

# Personalización de la vista de Requisito en el admin
class RequisitoAdmin(admin.ModelAdmin):
    list_display = ('idRequisito', 'nombreRequisito', 'estadoRequisito', 'fechaRequisito')  # Muestra estos campos en la lista
    search_fields = ('idRequisito','nombreRequisito','estadoRequisito', 'fechaRequisito')  # Permite buscar por estos campos, corregido a tupla

# Registra el modelo con las personalizaciones
admin.site.register(Requisito, RequisitoAdmin)

# Personalización de la vista de Requisito en el admin
class ServicioAdmin(admin.ModelAdmin):
    list_display = ('idServicio', 'nombreServicio', 'tiempoServicio', 'precioServicio', 'estadoServicio', 'fechaServicio')  # Muestra estos campos en la lista
    search_fields = ('idServicio','nombreServicio','estadoServicio', 'fechaServicio')  # Permite buscar por estos campos, corregido a tupla

# Registra el modelo con las personalizaciones
admin.site.register(Servicio, ServicioAdmin)

# Personalización de la vista de Requisito en el admin
class TramiteAdmin(admin.ModelAdmin):
    list_display = ('idTramite', 'nombreTramite', 'diasTramite', 'precioTramite', 'estadoTramite', 'fechaTramite')  # Muestra estos campos en la lista
    search_fields = ('idTramite','nombreTramite','estadoTramite', 'fechaTramite')  # Permite buscar por estos campos, corregido a tupla

# Registra el modelo con las personalizaciones
admin.site.register(Tramite, TramiteAdmin)

# Personalización de la vista de Requisito en el admin
class SolicitudAdmin(admin.ModelAdmin):
    list_display = ('idSoli', 'idPersona', 'idTramite', 'idServicio', 'montoTotal', 'estadoSolicitud', 'fechaEntrega', 'fechaSolicitud')  # Muestra estos campos en la lista
    search_fields = ('idSoli','estadoSolicitud','fechaEntrega', 'fechaSolicitud')  # Permite buscar por estos campos, corregido a tupla

# Registra el modelo con las personalizaciones
admin.site.register(Solicitud, SolicitudAdmin)

class MonedaAdmin(admin.ModelAdmin):
    list_display = ('idMoneda', 'nombreMoneda', 'simboloMoneda', 'estadoMoneda', 'fechaMoneda')  # Muestra estos campos en la lista
    search_fields = ('idMoneda','nombreMoneda','estadoMoneda', 'fechaMoneda')  # Permite buscar por estos campos, corregido a tupla

# Registra el modelo con las personalizaciones
admin.site.register(Moneda, MonedaAdmin)

class TasaAdmin(admin.ModelAdmin):
    list_display = ('idTasa', 'idMoneda', 'montoTasa', 'estadoTasa', 'fechaTasa')  # Muestra estos campos en la lista
    search_fields = ('idTasa','idMoneda','estadoTasa', 'fechaTasa')  # Permite buscar por estos campos, corregido a tupla

# Registra el modelo con las personalizaciones
admin.site.register(Tasa, TasaAdmin)