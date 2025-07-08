from django.contrib import admin
from .models import ConfiguracionBitacora

@admin.register(ConfiguracionBitacora)
class ConfiguracionBitacoraAdmin(admin.ModelAdmin):
    list_display = ('retencion', 'dias_personalizados', 'exportar_antes_limpieza', 'ultima_limpieza')
    fields = ('retencion', 'dias_personalizados', 'exportar_antes_limpieza', 'directorio_exportacion')
    
    def has_add_permission(self, request):
        # Permitir solo una instancia de configuración
        return not ConfiguracionBitacora.objects.exists()