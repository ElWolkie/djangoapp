from django.contrib import admin
from .models import Personas, TipoPersona, Cuota, Ofertas, TipoOferta, Materia, Cohorte, Cargo, Contrato, Honorario, Requisito, Servicio, Tramite, Solicitud, Denominacion, Banco, Moneda, Tasa, TipoIngreso, TipoEgreso

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

# Personalización de la vista de Contrato en el admin
class ContratoAdmin(admin.ModelAdmin):
    list_display = ('idContrato', 'idPersona', 'idCargo', 'idCohorte', 'idMateria', 'estadoContrato', 'fechaContrato')  # Muestra estos campos en la lista
    search_fields = ('idContrato','estadoContrato','fechaContrato')  # Permite buscar por estos campos, corregido a tupla

# Registra el modelo con las personalizaciones
admin.site.register(Contrato, ContratoAdmin)

# Personalización de la vista de Honorario en el admin
class HonorarioAdmin(admin.ModelAdmin):
    list_display = ('idHonorario', 'idContrato', 'horas', 'estadoHonorario', 'fechaHonorario')  # Muestra estos campos en la lista
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

class DenominacionAdmin(admin.ModelAdmin):
    list_display = ('idDenominacion', 'nombreDenominacion', 'estadoDenominacion', 'fechaDenominacion')  # Muestra estos campos en la lista
    search_fields = ('idDenominacion','nombreDenominacion','estadoDenominacion', 'fechaDenominacion')  # Permite buscar por estos campos, corregido a tupla

# Registra el modelo con las personalizaciones
admin.site.register(Denominacion, DenominacionAdmin)

class BancoAdmin(admin.ModelAdmin):
    list_display = ('idBanco', 'nombreBanco', 'codBanco', 'codContable', 'estadoBanco', 'fechaBanco')  # Muestra estos campos en la lista
    search_fields = ('idBanco','nombreBanco','codBanco', 'estadoBanco', 'fechaBanco')  # Permite buscar por estos campos, corregido a tupla

# Registra el modelo con las personalizaciones
admin.site.register(Banco, BancoAdmin)

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

class TipoIngresoAdmin(admin.ModelAdmin):
    list_display = ('idTipoIngreso', 'nombreTipoIngreso', 'estadoTipoIngreso', 'fechaTipoIngreso')  # Muestra estos campos en la lista
    search_fields = ('idTipoIngreso','nombreTipoIngreso','estadoTipoIngreso', 'fechaTipoIngreso')  # Permite buscar por estos campos, corregido a tupla

# Registra el modelo con las personalizaciones
admin.site.register(TipoIngreso, TipoIngresoAdmin)

class TipoEgresoAdmin(admin.ModelAdmin):
    list_display = ('idTipoEgreso', 'nombreTipoEgreso', 'estadoTipoEgreso', 'fechaTipoEgreso')  # Muestra estos campos en la lista
    search_fields = ('idTipoEgreso','nombreTipoEgreso','estadoTipoEgreso', 'fechaTipoEgreso')  # Permite buscar por estos campos, corregido a tupla

# Registra el modelo con las personalizaciones
admin.site.register(TipoEgreso, TipoEgresoAdmin)