import re
from django import template

register = template.Library()

@register.filter(name='solo_digitos')
def solo_digitos(value):
    """
    Extrae solo caracteres numéricos de `value` y toma los primeros 4.
    Ejemplos:
      "15 días"   → "15"
      "12345abc"  → "1234"
      "cero"      → ""
    """
    raw = str(value or '')
    # Encuentra todos los dígitos y concatena
    digits = ''.join(re.findall(r'\d', raw))
    # Limita a 4 caracteres
    return digits[:4]
