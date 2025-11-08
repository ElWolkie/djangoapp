# apps/factura/utils.py
import logging
from apps.home.models import Formacion
from django.db import IntegrityError, transaction
from apps.factura.models import NotaRelacionada
from apps.home.models import CuotaFormacion

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


logger = logging.getLogger(__name__)

def create_nota_relacionada_robusta(nota, inscripcion=None, inscripcion_cuota=None):
    """
    Intenta crear NotaRelacionada apuntando a InscripcionCuota.
    Si falla por FK (DB aún apunta a CuotaFormacion), intenta apuntar a la CuotaFormacion relacionada.
    - nota: instancia Nota
    - inscripcion: instancia Inscripcion (opcional)
    - inscripcion_cuota: instancia InscripcionCuota (opcional)
    Retorna la instancia NotaRelacionada creada.
    Lanza la excepción original si ambos intentos fallan.
    """
    # intento 1: crear usando la InscripcionCuota (forma "nativa")
    try:
        with transaction.atomic():
            nr = NotaRelacionada.objects.create(
                idNota=nota,
                idInscripcion=inscripcion,
                idCuota=inscripcion_cuota
            )
        return nr
    except IntegrityError as err:
        logger.warning("IntegrityError creando NotaRelacionada (intentando fallback): %s", err)
        # intento 2: fallback -> si InscripcionCuota tiene idCuota (FK a CuotaFormacion), usar ese id
        try:
            cf = getattr(inscripcion_cuota, 'idCuota', None)
            cf_pk = getattr(cf, 'idCuota', getattr(cf, 'pk', None))
            if cf_pk and CuotaFormacion.objects.filter(pk=cf_pk).exists():
                with transaction.atomic():
                    # crear pasando la PK entera (ORM guardará en idCuota_id)
                    nr = NotaRelacionada.objects.create(
                        idNota=nota,
                        idInscripcion=inscripcion,
                        idCuota=cf_pk
                    )
                logger.info("NotaRelacionada creada por fallback usando CuotaFormacion id=%s", cf_pk)
                return nr
            else:
                logger.error("Fallback no pudo encontrar CuotaFormacion para InscripcionCuota: %s", inscripcion_cuota)
                raise
        except Exception as exc2:
            logger.exception("Fallback creando NotaRelacionada falló: %s", exc2)
            raise err  # relanzar el error original para que la vista lo maneje/loggee

