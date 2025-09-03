# factura/templatetags/decimal_filters.py
from django import template
from decimal import Decimal, InvalidOperation
import re

register = template.Library()

@register.filter(name='to_decimal')
def to_decimal(value, default=0):
    """
    Convierte un valor a Decimal de forma segura, manejando diferentes formatos.
    """
    if value is None:
        return Decimal(default)
    
    if isinstance(value, Decimal):
        return value
        
    # Convertir a string y limpiar
    value_str = str(value).strip()
    
    # Remover caracteres no numéricos excepto punto, coma y signo negativo
    cleaned = re.sub(r'[^\d.,-]', '', value_str)
    
    # Determinar el separador decimal (prioriza la coma si hay múltiples separadores)
    if ',' in cleaned and '.' in cleaned:
        # Si hay ambos, asumimos que la coma es el separador decimal
        cleaned = cleaned.replace('.', '').replace(',', '.')
    elif ',' in cleaned:
        # Solo hay coma, reemplazar por punto
        cleaned = cleaned.replace(',', '.')
    
    # Validar que sea un número decimal válido
    try:
        return Decimal(cleaned)
    except (InvalidOperation, ValueError):
        return Decimal(default)