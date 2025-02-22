from django.contrib import admin
from .models import Personas

# Personalización de la vista de Personas en el admin
class PersonaAdmin(admin.ModelAdmin):
    list_display = ('idTP', 'cedula', 'nombres', 'apellidos', 'telefono', 'correo', 'fecha')  # Muestra estos campos en la lista
    search_fields = ('cedula', 'nombres', 'apellidos')  # Permite buscar por estos campos

# Registra el modelo con las personalizaciones
admin.site.register(Personas, PersonaAdmin)
