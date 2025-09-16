import json
from django.db import models

def model_to_dict(instance, fields=None):
    """
    Convierte una instancia de modelo a diccionario, incluyendo campos especificados
    """
    opts = instance._meta
    data = {}
    for f in opts.fields:
        if fields and f.name not in fields:
            continue
        if isinstance(f, models.fields.related.RelatedField):
            # Ignorar campos relacionados
            continue
        value = f.value_from_object(instance)
        data[f.name] = str(value) if value is not None else None
    return data

def get_field_changes(instance, old_instance, fields=None):
    """
    Detecta cambios entre dos instancias del mismo modelo
    """
    changes = {}
    current_data = model_to_dict(instance, fields)
    old_data = model_to_dict(old_instance, fields)
    
    for key, current_value in current_data.items():
        old_value = old_data.get(key, None)
        if current_value != old_value:
            changes[key] = {
                'anterior': old_value,
                'nuevo': current_value,
                'campo': key
            }
    
    return changes