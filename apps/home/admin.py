from django.contrib import admin
from .models import Personas, TipoPersona, Cuota, Ofertas, TipoOferta

# Personalización de la vista de Personas en el admin
class PersonaAdmin(admin.ModelAdmin):
    list_display = ('idTP', 'cedula', 'nombres', 'apellidos', 'telefono', 'correo',  'estadoPersona', 'fechaPersona')  # Muestra estos campos en la lista
    search_fields = ('cedula', 'nombres', 'apellidos')  # Permite buscar por estos campos

# Registra el modelo con las personalizaciones
admin.site.register(Personas, PersonaAdmin)

# Personalización de la vista de TipoPersona en el admin
class TipoPersonaAdmin(admin.ModelAdmin):
    list_display = ('idTP', 'nombreTP', 'estadoTP', 'fechaTP')  # Muestra estos campos en la lista
    search_fields = ('nombreTP',)  # Permite buscar por estos campos, corregido a tupla

# Registra el modelo con las personalizaciones
admin.site.register(TipoPersona, TipoPersonaAdmin)

# Personalización de la vista de Cuota en el admin
class CuotaAdmin(admin.ModelAdmin):
    list_display = ('idCuota', 'nombreCuota', 'estadoCuota', 'fechaCuota')  # Muestra estos campos en la lista
    search_fields = ('nombreCuota',)  # Permite buscar por estos campos, corregido a tupla

# Registra el modelo con las personalizaciones
admin.site.register(Cuota, CuotaAdmin)

# Personalización de la vista de Ofertas en el admin
class OfertasAdmin(admin.ModelAdmin):
    list_display = ('idOferta', 'idTipoOferta', 'nombreOferta', 'duracion', 'estadoOferta', 'fechaOferta')  # Muestra estos campos en la lista
    search_fields = ('nombreOferta','fechaOferta')  # Permite buscar por estos campos, corregido a tupla

# Registra el modelo con las personalizaciones
admin.site.register(Ofertas, OfertasAdmin)

# Personalización de la vista de TipoOferta en el admin
class TipoOfertaAdmin(admin.ModelAdmin):
    list_display = ('idTipoOferta', 'idCuota', 'nombreTipoOferta', 'estadoTipoOferta', 'fechaTipoOferta')  # Muestra estos campos en la lista
    search_fields = ('nombreTipoOferta','fechaTipoOferta')  # Permite buscar por estos campos, corregido a tupla

# Registra el modelo con las personalizaciones
admin.site.register(TipoOferta, TipoOfertaAdmin)
