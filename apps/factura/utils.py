# apps/notas/utils.py
def obtener_info_formacion_de_inscripcion(inscripcion):
    """
    Intenta extraer idFormacion y nombreFormacion de distintos esquemas de Inscripcion.
    Devuelve (idFormacion_int_or_None, nombreFormacion_or_None)
    """
    if inscripcion is None:
        return (None, None)

    # 1) idFormacion directo
    try:
        if hasattr(inscripcion, 'idFormacion') and inscripcion.idFormacion:
            # si es objeto o número
            val = inscripcion.idFormacion
            if isinstance(val, (int, str)):
                return (int(val), None)
            if isinstance(val, dict):
                return (int(val.get('idFormacion') or val.get('id') or 0), val.get('nombreFormacion') or val.get('nombre'))
            # objeto Django
            if hasattr(val, 'idFormacion') or hasattr(val, 'id'):
                return (int(getattr(val, 'idFormacion', getattr(val, 'id', 0)) or 0),
                        getattr(val, 'nombreFormacion', getattr(val, 'nombre', None)))
    except Exception:
        pass

    # 2) idFormacion_detail (serializers) o formacion
    try:
        detail = getattr(inscripcion, 'idFormacion_detail', None) or getattr(inscripcion, 'formacion', None) or getattr(inscripcion, 'id_formacion', None)
        if detail:
            if isinstance(detail, (int, str)):
                return (int(detail), None)
            if isinstance(detail, dict):
                return (int(detail.get('idFormacion') or detail.get('id') or 0), detail.get('nombreFormacion') or detail.get('nombre'))
            if hasattr(detail, 'idFormacion') or hasattr(detail, 'id'):
                return (int(getattr(detail, 'idFormacion', getattr(detail, 'id', 0)) or 0),
                        getattr(detail, 'nombreFormacion', getattr(detail, 'nombre', None)))
    except Exception:
        pass

    # 3) intentar atributos alternativos
    for candidate in ('id_formacion', 'idFormacion', 'formacion'):
        try:
            v = getattr(inscripcion, candidate, None)
            if v:
                return (int(v), None)
        except Exception:
            continue

    # no encontrado
    return (None, None)
