from django.contrib import admin
from .models import Personas, TipoPersona, Cuota, Ofertas, TipoOferta, Materia, Cohorte, Cargo, Contrato, Honorario

# Personalización de la vista de Personas en el admin
class PersonaAdmin(admin.ModelAdmin):
    list_display = ('idTP', 'cedula', 'nombres', 'apellidos', 'telefono', 'correo',  'estadoPersona', 'fechaPersona')  # Muestra estos campos en la lista
    search_fields = ('cedula', 'nombres', 'apellidos')  # Permite buscar por estos campos

# Registra el modelo con las personalizaciones
admin.site.register(Personas, PersonaAdmin)

# Personalización de la vista de TipoPersona en el admin
class TipoPersonaAdmin(admin.ModelAdmin):
    list_display = ('idTP', 'nombreTP', 'estadoTP', 'fechaTP')  # Muestra estos campos en la lista
    search_fields = ('nombreTP','estadoTP','fechaTP')  # Permite buscar por estos campos, corregido a tupla

# Registra el modelo con las personalizaciones
admin.site.register(TipoPersona, TipoPersonaAdmin)

# Personalización de la vista de Cuota en el admin
class CuotaAdmin(admin.ModelAdmin):
    list_display = ('idCuota', 'nombreCuota', 'estadoCuota', 'fechaCuota')  # Muestra estos campos en la lista
    search_fields = ('nombreCuota','estadoCuota','fechaCuota')  # Permite buscar por estos campos, corregido a tupla

# Registra el modelo con las personalizaciones
admin.site.register(Cuota, CuotaAdmin)

# Personalización de la vista de Ofertas en el admin
class OfertasAdmin(admin.ModelAdmin):
    list_display = ('idOferta', 'idTipoOferta', 'nombreOferta', 'duracion', 'estadoOferta', 'fechaOferta')  # Muestra estos campos en la lista
    search_fields = ('nombreOferta','estadoOferta','fechaOferta')  # Permite buscar por estos campos, corregido a tupla

# Registra el modelo con las personalizaciones
admin.site.register(Ofertas, OfertasAdmin)

# Personalización de la vista de TipoOferta en el admin
class TipoOfertaAdmin(admin.ModelAdmin):
    list_display = ('idTipoOferta', 'idCuota', 'nombreTipoOferta', 'estadoTipoOferta', 'fechaTipoOferta')  # Muestra estos campos en la lista
    search_fields = ('nombreTipoOferta','estadoTipoOferta','fechaTipoOferta')  # Permite buscar por estos campos, corregido a tupla

# Registra el modelo con las personalizaciones
admin.site.register(TipoOferta, TipoOfertaAdmin)

# Personalización de la vista de Materia en el admin
class MateriaAdmin(admin.ModelAdmin):
    list_display = ('idMateria', 'idOferta', 'nombreMateria', 'estadoMateria', 'fechaMateria')  # Muestra estos campos en la lista
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

# Personalización de la vista de Cargo en el admin
class ContratoAdmin(admin.ModelAdmin):
    list_display = ('idContrato', 'idPersona', 'idCargo', 'idCohorte', 'idMateria', 'estadoContrato', 'fechaContrato')  # Muestra estos campos en la lista
    search_fields = ('idContrato','estadoContrato','fechaContrato')  # Permite buscar por estos campos, corregido a tupla

# Registra el modelo con las personalizaciones
admin.site.register(Contrato, ContratoAdmin)

# Personalización de la vista de Cargo en el admin
class HonorarioAdmin(admin.ModelAdmin):
    list_display = ('idHonorario', 'idContrato', 'horas', 'estadoHonorario', 'fechaHonorario')  # Muestra estos campos en la lista
    search_fields = ('idHonorario','estadoHonorario','fechaHonorario')  # Permite buscar por estos campos, corregido a tupla

# Registra el modelo con las personalizaciones
admin.site.register(Honorario, HonorarioAdmin)