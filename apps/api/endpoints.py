# apps/api/endpoints.py

from datetime import timedelta
import traceback
import uuid
import logging
from decimal import Decimal, InvalidOperation

from django.db import transaction
from django.utils.timezone import now
from django.db.models import Prefetch

from rest_framework.decorators import api_view
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.renderers import JSONRenderer

from apps.persona.models import PersonaTP, Personas
from apps.home.models import CuotaFormacion, Formacion, Moneda, Usuarios
from apps.asientoContable.models import AsientoContable, DetalleAsiento
from apps.periodoContable.models import periodoContable
from apps.inscripcion.models import Inscripcion
from apps.factura.models import Nota, NotaRelacionada, Pago, PlanArticulo, ParametroTributario
from apps.home.models import Tasa, Configuracion
from apps.factura.templatetags.decimal_filters import to_decimal

# Helper import (asegúrate de tener este helper en apps/factura/utils.py)
from apps.factura.utils import obtener_info_formacion_de_inscripcion

logger = logging.getLogger(__name__)


# -----------------------------
# Helpers locales
# -----------------------------

def generar_numero_nota():
    fecha_actual = now().strftime('%Y%m%d')
    numero_unico = uuid.uuid4().hex[:6].upper()
    return f"NOTA-{fecha_actual}-{numero_unico}"


def _obtener_formacion_desde_inscripcion(inscripcion):
    """Devuelve objeto Formacion o None, intentando varias rutas seguras."""
    try:
        if not inscripcion:
            return None
        coh = getattr(inscripcion, 'idCohorte', None)
        if coh:
            frm = getattr(coh, 'idFormacion', None)
            if frm:
                return frm
        # helper que devuelve idFormacion/nombre si existe de forma compatible
        fid, fname = obtener_info_formacion_de_inscripcion(inscripcion)
        if fid:
            return Formacion.objects.filter(idFormacion=fid).first()
        # fallback por atributo directo
        frm_attr = getattr(inscripcion, 'idFormacion', None) or getattr(inscripcion, 'idFormacion_id', None)
        if frm_attr:
            # si es instancia
            if hasattr(frm_attr, 'idFormacion') or hasattr(frm_attr, 'id'):
                return frm_attr
            return Formacion.objects.filter(idFormacion=frm_attr).first()
    except Exception:
        logger.exception("Error obteniendo formacion desde inscripcion")
    return None


# -----------------------------
# Endpoints
# -----------------------------

class PersonaPublicRegisterView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        logger.info(f"📥 Datos recibidos RAW: {request.data}")
        try:
            from apps.persona.serializers import PersonaCreateSerializer
            serializer = PersonaCreateSerializer(data=request.data)
            if serializer.is_valid():
                persona_creada = serializer.save()
                resp = serializer.data
                resp['mensaje'] = 'Persona registrada exitosamente'
                logger.info(f"✅ Persona creada: {persona_creada.idPersona}")
                return Response(resp, status=status.HTTP_201_CREATED)
            else:
                logger.warning(f"❌ Errores de validación: {serializer.errors}")
                return Response({'error': 'Datos inválidos', 'detalles': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.exception("🔥 Error crítico: %s", e)
            return Response({'error': f'Error interno: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
def verificar_cedula(request):
    cedula = request.GET.get('cedula', '').strip()
    response_data = {'existe': False, 'usuario_existe': False}
    if len(cedula) >= 6:
        try:
            persona = Personas.objects.get(cedula=cedula)
            response_data['existe'] = True
            response_data['usuario_existe'] = Usuarios.objects.filter(idPersona=persona).exists()
        except Personas.DoesNotExist:
            pass
    return Response(response_data)


class UsuarioPublicRegisterView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        logger.info(f"📥 Intento de registro de usuario: {request.data.get('cedula')}")
        from apps.persona.serializers import UsuarioCreateSerializer
        serializer = UsuarioCreateSerializer(data=request.data)
        if serializer.is_valid():
            usuario_creado = serializer.save()
            return Response(serializer.to_representation(usuario_creado), status=status.HTTP_201_CREATED)
        else:
            logger.warning(f"⚠️ Registro de usuario fallido: {serializer.errors}")
            error_detail = next(iter(serializer.errors.values()))[0]
            return Response({'error': error_detail, 'codigo': 'VALIDATION_ERROR'}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
def obtener_persona_login(request):
    cedula = request.GET.get('cedula', '').strip()
    logger.debug("🔍 [DEBUG] Buscando cédula: '%s'", cedula)
    if len(cedula) < 6:
        return Response({'error': 'La cédula debe tener al menos 6 dígitos'}, status=status.HTTP_400_BAD_REQUEST)

    formatos_a_probar = [cedula, f"V-{cedula}", f"E-{cedula}", f"P-{cedula}", cedula.zfill(8)]
    for formato in formatos_a_probar:
        try:
            persona = Personas.objects.get(cedula=formato)
            logger.debug("✅ Encontrada con formato '%s': %s -> %s", formato, persona.cedula, persona.idPersona)
            return Response({
                'idPersona': persona.idPersona,
                'cedula': persona.cedula,
                'nombres': getattr(persona, 'nombres', None) or getattr(persona, 'nombre', None),
                'apellidos': getattr(persona, 'apellidos', None) or getattr(persona, 'apellido', None),
                'tiene_usuario': Usuarios.objects.filter(idPersona=persona).exists()
            })
        except Personas.DoesNotExist:
            continue

    similares = Personas.objects.filter(cedula__icontains=cedula)[:10]
    return Response({'error': 'No se encontró persona con esta cédula', 'sugerencia': 'Intente con el formato completo (ej: V-30895206)', 'debug_similares': [{'cedula': p.cedula, 'id': p.idPersona} for p in similares]}, status=status.HTTP_404_NOT_FOUND)


class CuotasFormacionAPIView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, formacion_id):
        try:
            logger.info(f"🔍 Solicitando cuotas para formación: {formacion_id}")
            if not formacion_id or int(formacion_id) <= 0:
                return Response({'error': 'ID de formación inválido'}, status=400)
            formacion = Formacion.objects.filter(idFormacion=formacion_id).first()
            if not formacion:
                return Response({'error': 'Formación no encontrada', 'formacion_id': formacion_id}, status=404)
            cuotas = CuotaFormacion.objects.filter(idFormacion=formacion_id, is_active=True).order_by('orden')
            cuotas_data = [{'idCuota': c.idCuota, 'nombreCuota': c.nombreCuota, 'tipoCuota': c.tipoCuota, 'valorCuota': float(c.valorCuota), 'orden': c.orden} for c in cuotas]
            return Response({'formacion_id': formacion.idFormacion, 'nombre_formacion': formacion.nombreFormacion, 'cuotas': cuotas_data, 'total_cuotas': len(cuotas_data)}, status=200)
        except Exception as e:
            logger.exception("Error en CuotasFormacionAPIView: %s", e)
            return Response({'error': 'Error interno del servidor'}, status=500)


class NotaCobroCreateAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request):
        id_inscripcion = request.data.get('idInscripcion') or request.POST.get('idInscripcion')
        if not id_inscripcion:
            return Response({'success': False, 'message': 'Inscripcion no encontrada.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            inscripcion = Inscripcion.objects.filter(idInscripcion=id_inscripcion, is_active=True).select_related('idCohorte__idFormacion').first()
            if not inscripcion:
                return Response({'success': False, 'message': 'No se encontró una inscripción activa con el ID proporcionado.'}, status=status.HTTP_404_NOT_FOUND)

            configuracion = Configuracion.objects.first()
            if not configuracion:
                return Response({'success': False, 'message': 'No se encontró una configuración activa en el sistema.'}, status=status.HTTP_400_BAD_REQUEST)

            moneda_configuracion = configuracion.moneda
            tasa_configuracion = Tasa.objects.filter(idMoneda=moneda_configuracion).order_by('-idTasa').first()
            if not tasa_configuracion:
                return Response({'success': False, 'message': f'No se encontró tasa para la moneda de configuración ({getattr(moneda_configuracion, "nombreMoneda", moneda_configuracion)})'}, status=status.HTTP_400_BAD_REQUEST)

            periodo_activo = periodoContable.objects.filter(estadoPeriodo=True).first() or periodoContable.objects.order_by('-idPeriodo').first()
            if not periodo_activo:
                return Response({'success': False, 'message': 'No hay periodo contable registrado o activo.'}, status=status.HTTP_400_BAD_REQUEST)

            formacion = _obtener_formacion_desde_inscripcion(inscripcion)
            if not formacion:
                return Response({'success': False, 'message': 'No se pudo determinar la formación asociada a la inscripción.'}, status=status.HTTP_400_BAD_REQUEST)

            valor_inscripcion = getattr(formacion, 'valorInscripcion', Decimal('0.00'))

            # Cálculos de impuestos y descuentos simplificados
            parametros_tributarios = ParametroTributario.objects.filter(activo=True)
            parametro_iva_exento = parametros_tributarios.filter(tipo='IVA_EXENTO', aplica_a='INSCRIPCION').first()
            if parametro_iva_exento and parametro_iva_exento.porcentaje == Decimal('0.00'):
                subtotal_exento = valor_inscripcion
                subtotal_gravado = Decimal('0.00')
                iva = Decimal('0.00')
            else:
                subtotal_gravado = valor_inscripcion
                subtotal_exento = Decimal('0.00')
                parametro_iva = parametros_tributarios.filter(tipo='IVA_GENERAL', aplica_a='INSCRIPCION').first()
                porcentaje_iva = parametro_iva.porcentaje if parametro_iva else Decimal('16')
                iva = (subtotal_gravado * porcentaje_iva) / Decimal('100')

            tiene_descuento = PersonaTP.objects.filter(idPersona=inscripcion.idPersona, idTP=3).exists()
            descuento = Decimal('0.00')
            if tiene_descuento:
                descuento = (subtotal_gravado + subtotal_exento) * (to_decimal(configuracion.descuento) / Decimal('100'))

            total_nota = subtotal_gravado + subtotal_exento + iva - descuento

            asiento = AsientoContable.objects.create(numeroAsiento=f"NOTA-{generar_numero_nota()}", fechaAsiento=now().date(), conceptoAsiento=f"Asiento para la nota {generar_numero_nota()}", idPeriodo=periodo_activo)

            nota = Nota.objects.create(
                idAsiento=asiento,
                idPersona=inscripcion.idPersona,
                numeroNota=generar_numero_nota(),
                tipoOperacion='COBRO',
                tipoArticulo='INSCRIPCION',
                fechaEmision=now().date(),
                fechaVencimiento=now().date() + timedelta(days=1),
                formaPago='CONTADO',
                plazoCredito=None,
                subtotalExento=subtotal_exento,
                subtotalGravado=subtotal_gravado,
                iva=iva,
                ivaRetenido=Decimal('0.00'),
                islrRetenido=Decimal('0.00'),
                descuento=descuento,
                totalNota=total_nota,
                idTasa=tasa_configuracion,
                estado='PENDIENTE',
                observaciones='NOTA AUTOMATIZADA POR LA APP'
            )

            NotaRelacionada.objects.create(idNota=nota, idInscripcion=inscripcion)
            inscripcion.estadoPago = 'PENDIENTE'
            inscripcion.save()

            # crear detalles de asiento con PlanArticulo
            plan_debe = PlanArticulo.objects.filter(tipoArticulo='INSCRIPCION', tipo=True).order_by('-fecha').first()
            plan_haber = PlanArticulo.objects.filter(tipoArticulo='INSCRIPCION', tipo=False).order_by('-fecha').first()
            if not plan_debe or not plan_haber:
                # no hacemos rollback por la creacion de nota, ya que la transacción hará rollback si se lanza la excepción
                logger.warning('No se encontraron cuentas contables completas para INSCRIPCION')
            else:
                DetalleAsiento.objects.create(idAsiento=asiento, idPlanCuenta=plan_debe.idPlanCuenta, debe=to_decimal(nota.totalNota), haber=Decimal('0.00'))
                DetalleAsiento.objects.create(idAsiento=asiento, idPlanCuenta=plan_haber.idPlanCuenta, debe=Decimal('0.00'), haber=to_decimal(nota.totalNota))

            return Response({'success': True, 'message': 'Nota de cobro creada exitosamente.', 'data': {'idNota': nota.idNota, 'numeroNota': nota.numeroNota, 'totalNota': float(nota.totalNota)}}, status=status.HTTP_201_CREATED)

        except Exception as e:
            logger.exception('Error en NotaCobroCreateAPIView: %s', e)
            tb = traceback.format_exc()
            return Response({'success': False, 'message': 'Error interno', 'error': str(e), 'debug_trace': tb}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
def notas_por_usuario_autenticado(request):
    try:
        usuario = request.user
        if not usuario.is_authenticated:
            return Response({'success': False, 'message': 'Usuario no autenticado'}, status=401)
        persona = getattr(usuario, 'idPersona', None)
        if not persona:
            usuario_rel = Usuarios.objects.filter(user_id=getattr(usuario, 'id', None)).first()
            persona = getattr(usuario_rel, 'idPersona', None) if usuario_rel else None
        if not persona:
            return Response({'success': False, 'message': 'Perfil de persona no encontrado para este usuario'}, status=404)

        logger.debug('🔍 Buscando notas para persona ID: %s', getattr(persona, 'idPersona', persona))
        notas = Nota.objects.filter(idPersona=persona, estado__in=['PENDIENTE', 'PARCIAL']).order_by('-fechaEmision')
        notas_data = []
        for nota in notas:
            formacion_nombre = 'Formación no especificada'
            try:
                relacion = NotaRelacionada.objects.filter(idNota=nota).select_related('idInscripcion__idCohorte__idFormacion').first()
                if relacion:
                    ins = getattr(relacion, 'idInscripcion', None)
                    if ins:
                        form_obj = _obtener_formacion_desde_inscripcion(ins)
                        if form_obj:
                            formacion_nombre = getattr(form_obj, 'nombreFormacion', formacion_nombre)
                        else:
                            formacion_nombre = f"Inscripción #{ins.idInscripcion}"
            except Exception:
                logger.exception('Error obteniendo formacion para nota %s', nota.idNota)

            notas_data.append({'idNota': nota.idNota, 'numeroNota': nota.numeroNota, 'fechaEmision': nota.fechaEmision, 'totalNota': float(nota.totalNota), 'estado': nota.estado, 'formacion': {'nombreFormacion': formacion_nombre}})

        return Response({'success': True, 'data': notas_data, 'total': len(notas_data)}, status=200)
    except Exception as e:
        logger.exception('Error en notas_por_usuario_autenticado: %s', e)
        return Response({'success': False, 'message': f'Error obteniendo notas: {str(e)}'}, status=500)


@api_view(['GET'])
def notas_por_cedula(request):
    try:
        cedula = request.GET.get('cedula', '').strip()
        if not cedula:
            return Response({'success': False, 'message': 'Cédula requerida'}, status=400)
        persona = Personas.objects.filter(cedula__icontains=cedula).first()
        if not persona:
            return Response({'success': True, 'data': [], 'total': 0, 'message': 'No se encontraron notas'})
        notas = Nota.objects.filter(idPersona=persona.idPersona).order_by('-fechaEmision')
        notas_data = []
        for nota in notas:
            formacion_info = 'Formación no especificada'
            cohorte_info = 'Cohorte no especificada'
            try:
                relacion = NotaRelacionada.objects.filter(idNota=nota).select_related('idInscripcion__idCohorte__idFormacion').first()
                if relacion and relacion.idInscripcion:
                    inscripcion = relacion.idInscripcion
                    if getattr(inscripcion, 'idCohorte', None):
                        coh = inscripcion.idCohorte
                        cohorte_info = getattr(coh, 'nombreCohorte', cohorte_info)
                        if getattr(coh, 'idFormacion', None):
                            formacion_info = getattr(coh.idFormacion, 'nombreFormacion', formacion_info)
                    else:
                        form_obj = _obtener_formacion_desde_inscripcion(inscripcion)
                        if form_obj:
                            formacion_info = getattr(form_obj, 'nombreFormacion', formacion_info)
            except Exception:
                logger.exception('Error procesando nota %s', nota.idNota)

            nota_obj = {'idNota': nota.idNota, 'numeroNota': nota.numeroNota, 'fechaEmision': nota.fechaEmision.isoformat() if nota.fechaEmision else None, 'totalNota': float(nota.totalNota) if nota.totalNota else 0.0, 'estado': nota.estado or 'PENDIENTE', 'formacion': {'nombreFormacion': formacion_info}, 'cohorte': cohorte_info}
            notas_data.append(nota_obj)

        return Response({'success': True, 'data': notas_data, 'total': len(notas_data)}, status=200)
    except Exception as e:
        logger.exception('Error en notas_por_cedula: %s', e)
        return Response({'success': False, 'message': f'Error interno del servidor: {str(e)}'}, status=500)


@api_view(['POST'])
def corregir_relaciones_notas(request):
    try:
        notas_sin_relacion = Nota.objects.filter(tipoArticulo='INSCRIPCION').exclude(idNota__in=NotaRelacionada.objects.values('idNota'))
        correcciones = []
        for nota in notas_sin_relacion:
            inscripciones = Inscripcion.objects.filter(idPersona=nota.idPersona, is_active=True)
            for inscripcion in inscripciones:
                relacion = NotaRelacionada.objects.create(idNota=nota, idInscripcion=inscripcion)
                correcciones.append({'nota_id': nota.idNota, 'nota_numero': nota.numeroNota, 'inscripcion_id': inscripcion.idInscripcion})
                break
        return Response({'success': True, 'message': f'Se crearon {len(correcciones)} relaciones', 'correcciones': correcciones})
    except Exception as e:
        logger.exception('Error en corregir_relaciones_notas: %s', e)
        return Response({'success': False, 'message': f'Error: {str(e)}'}, status=500)


@api_view(['GET'])
def diagnosticar_notas(request):
    try:
        total_personas = Personas.objects.count()
        total_notas = Nota.objects.count()
        total_relaciones = NotaRelacionada.objects.count()
        persona_test = Personas.objects.filter(cedula__icontains="30895206").first()
        notas_persona = Nota.objects.filter(idPersona=persona_test.idPersona).count() if persona_test else 0
        return Response({'success': True, 'diagnostico': {'total_personas': total_personas, 'total_notas': total_notas, 'total_relaciones': total_relaciones, 'persona_test_encontrada': bool(persona_test), 'notas_persona_test': notas_persona}})
    except Exception as e:
        logger.exception('Error en diagnosticar_notas: %s', e)
        return Response({'success': False, 'error': str(e)}, status=500)
