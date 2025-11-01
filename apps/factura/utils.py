# apps/factura/utils.py
import logging
from apps.home.models import Formacion

logger = logging.getLogger(__name__)

def obtener_info_formacion_de_inscripcion(inscripcion):
    """
    Retorna (idFormacion, nombreFormacion) o (None, None).
    Maneja:
      - inscripcion.idCohorte.idFormacion
      - inscripcion.idFormacion (si por alguna razón existe)
      - inscripcion.idFormacion_id
    """
    try:
        if not inscripcion:
            return (None, None)
        # 1) cohorte -> formacion (lo normal)
        coh = getattr(inscripcion, 'idCohorte', None)
        if coh:
            frm = getattr(coh, 'idFormacion', None)
            if frm:
                return (getattr(frm, 'idFormacion', getattr(frm, 'id', None)), getattr(frm, 'nombreFormacion', None))

        # 2) inscripcion.idFormacion directo (por compatibilidad)
        val = getattr(inscripcion, 'idFormacion', None)
        if val:
            # si es instancia de Formacion
            if hasattr(val, 'idFormacion') or hasattr(val, 'id'):
                return (getattr(val, 'idFormacion', getattr(val, 'id', None)), getattr(val, 'nombreFormacion', None))
            # si es id primitivo
            try:
                frm_obj = Formacion.objects.filter(idFormacion=val).first()
                if frm_obj:
                    return (frm_obj.idFormacion, frm_obj.nombreFormacion)
            except Exception:
                pass

        # 3) id de fk directo
        fid = getattr(inscripcion, 'idFormacion_id', None)
        if fid:
            frm_obj = Formacion.objects.filter(idFormacion=fid).first()
            if frm_obj:
                return (frm_obj.idFormacion, frm_obj.nombreFormacion)

        return (None, None)
    except Exception as e:
        logger.exception("Error en obtener_info_formacion_de_inscripcion: %s", e)
        return (None, None)
