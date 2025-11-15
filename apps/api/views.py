from datetime import timedelta
import re
import traceback
import uuid

from django.db.models import Prefetch, Q
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from django.utils.timezone import now
from decimal import Decimal
from rest_framework import status as drf_status

from apps.api import serializers
from rest_framework import serializers as drf_serializers
from rest_framework.permissions import AllowAny
from django.db.models import Sum
from apps.home.models import Personas, Materia, Cohorte, Cargo, Requisito, Servicio, Tramite, Moneda, Tasa, Formacion, TipoFormacion, Usuarios, CuotaFormacion
from .serializers import PagoSerializer, PersonaSerializer, CedulaTokenObtainSerializer, TipoPersonaSerializer, PersonaTPSerializer, FormacionSerializer, TPFormacionSerializer, MateriaSerializer, CohorteSerializer, CargoSerializer, HonorarioSerializer, InscripcionSerializer, RequisitoSerializer, ServicioSerializer, TramiteSerializer, SolicitudSerializer, BancoSerializer, MonedaSerializer, TasaSerializer, UsuarioSerializer, AsientoContableSerializer, PlanCuentaSerializer, CuotaFormacionSerializer, NotaSerializer, ConfiguracionSerializer, CuotaPagoTemporalSerializer  # Importa ambos serializadores
from apps.persona.models import PersonaTP, TipoPersona
from apps.honorario.models import Honorario
from apps.inscripcion.models import Inscripcion, InscripcionCuota
from apps.solicitud.models import Solicitud
from apps.cuentaBanco.models import Banco
from apps.asientoContable.models import AsientoContable, DetalleAsiento
from apps.planCuenta.models import PlanCuenta
from apps.periodoContable.models import periodoContable
from django.db import transaction, IntegrityError
from apps.factura.models import Nota, Pago, NotaRelacionada, PagoTemporal, PlanArticulo
from apps.home.models import Moneda, Tasa, Configuracion
from .serializers import PagoCreateSerializer

import logging
logger = logging.getLogger(__name__)

# Vista para Personas
class PersonaListCreate(generics.ListCreateAPIView):
    queryset = Personas.objects.all()  # Usa el modelo Personas
    serializer_class = PersonaSerializer  # Usa el serializador PersonaSerializer

# Vista para TipoPersona
class TipoPersonaListCreate(generics.ListCreateAPIView):
    queryset = TipoPersona.objects.all()  # Usa el modelo TipoPersona
    serializer_class = TipoPersonaSerializer  # Usa el serializador TipoPersonaSerializer

# Vista para TipoPersona
class PersonaTPListCreate(generics.ListCreateAPIView):
    queryset = PersonaTP.objects.all()  # Usa el modelo PersonaTP
    serializer_class = PersonaTPSerializer  # Usa el serializador PersonaTPSerializer

# Vista para operaciones de detalle, actualización y eliminación de Personas
class PersonaRetrieveUpdateDestroy(generics.RetrieveUpdateDestroyAPIView):
    queryset = Personas.objects.all()  # Usa el modelo Personas
    serializer_class = PersonaSerializer  # Usa el serializador PersonaSerializer

# Vista para Formacion
class TPFormacionListCreate(generics.ListCreateAPIView):
    queryset = TipoFormacion.objects.all()  # Usa el modelo Formacion
    serializer_class = TPFormacionSerializer  # Usa el serializador Formacion

class MateriaListCreate(generics.ListCreateAPIView):
    queryset = Materia.objects.all()  # Usa el modelo Materia
    serializer_class = MateriaSerializer  # Usa el serializador MateriaSerializer

class CohorteListCreate(generics.ListCreateAPIView):
    queryset = Cohorte.objects.all()  # Usa el modelo Cohorte
    serializer_class = CohorteSerializer  # Usa el serializador CohorteSerializer

class CargoListCreate(generics.ListCreateAPIView):
    queryset = Cargo.objects.all()  # Usa el modelo Cargo
    serializer_class = CargoSerializer  # Usa el serializador CargoSerializer

class HonorarioListCreate(generics.ListCreateAPIView):
    queryset = Honorario.objects.all()  # Usa el modelo Honorario
    serializer_class = HonorarioSerializer  # Usa el serializador HonorarioSerializer

# Vista para Formacion
class FormacionListCreate(generics.ListCreateAPIView):
    queryset = Formacion.objects.all()  # Usa el modelo Formacion
    serializer_class = FormacionSerializer  # Usa el serializador Formacion

# Lista cuotas de una formación concreta
class CuotasPorFormacionList(generics.ListAPIView):
    serializer_class = CuotaFormacionSerializer

    def get_queryset(self):
        pk = self.kwargs.get('pk')
        return CuotaFormacion.objects.filter(idFormacion_id=pk, is_active=True).order_by('orden')

# Si no tienes detalle de Formacion, añade este retrieve
class FormacionRetrieve(generics.RetrieveAPIView):
    queryset = Formacion.objects.all()
    serializer_class = FormacionSerializer
    # El modelo usa idFormacion como PK, DRF lo respeta al usar 'pk' en la URL

class InscripcionListCreate(generics.ListCreateAPIView):
    queryset = Inscripcion.objects.select_related(
        'idPersona',
        'idCohorte',
        'idCohorte__idFormacion'
    ).prefetch_related(
        Prefetch(
            'idCohorte__idFormacion__cuotas',
            queryset=CuotaFormacion.objects.filter(is_active=True).order_by('orden'),
            to_attr='prefetched_cuotas'
        )
    ).all().prefetch_related('inscripcioncuota_set')

    serializer_class = InscripcionSerializer

    @transaction.atomic
    def perform_create(self, serializer):
        """
        Crea solamente la inscripción y (si aplica) sus InscripcionCuota asociadas.
        Ya NO se crea la Nota/Asiento/DetalleAsiento aquí: ese trabajo lo hará exclusivamente
        el endpoint /api/nota-cobro/create/.
        """
        # 1) Guardar inscripción
        inscripcion = serializer.save()

        try:
            # Intentar marcar is_active si el modelo lo soporta
            try:
                inscripcion.is_active = True
                inscripcion.save(update_fields=['is_active'])
            except Exception:
                # Ignorar si no existe el campo
                pass

            # 2) Determinar formación asociada (defensivo)
            formacion = None
            valor_inscripcion = None
            cohorte = getattr(inscripcion, 'idCohorte', None)
            if cohorte:
                formacion = getattr(cohorte, 'idFormacion', None)

            if formacion:
                valor_inscripcion = getattr(formacion, 'valorInscripcion', None)

            if valor_inscripcion is None:
                # No lanzamos error porque la nota la creará el endpoint de notas,
                # y allí se realizará la validación del monto. Aquí sólo avisamos en log.
                logger.debug("perform_create: no se pudo determinar valor_inscripcion para Inscripcion %s", getattr(inscripcion, 'idInscripcion', None))

            # 3) Crear InscripcionCuota(s) si existen cuotas activas (usar prefetched si viene)
            cuotas_para_crear = []
            prefetched = getattr(formacion, 'prefetched_cuotas', None)
            if prefetched and isinstance(prefetched, (list, tuple)):
                cuotas_qs = prefetched
            else:
                if formacion:
                    cuotas_qs = CuotaFormacion.objects.filter(idFormacion=formacion, is_active=True).order_by('orden')
                else:
                    cuotas_qs = CuotaFormacion.objects.none()

            for cuota in cuotas_qs:
                cuotas_para_crear.append(
                    InscripcionCuota(
                        idInscripcion=inscripcion,
                        idCuota=cuota,
                        estadoPago='EN ESPERA',
                        montoPagado=Decimal('0.00')
                    )
                )

            if cuotas_para_crear:
                InscripcionCuota.objects.bulk_create(cuotas_para_crear)
                logger.debug("Se crearon %d InscripcionCuota(s) para Inscripcion %s", len(cuotas_para_crear), inscripcion.idInscripcion)
            else:
                logger.debug("No se encontraron cuotas activas para la Inscripcion %s", inscripcion.idInscripcion)

            # 4) Marcar estadoPago como PENDIENTE por defecto (si aplica)
            try:
                inscripcion.estadoPago = 'PENDIENTE'
                inscripcion.save(update_fields=['estadoPago'])
            except Exception:
                # Si el campo no existe, ignorar
                pass

            # NOTA: ya NO se crea la Nota/Asiento/DetalleAsiento aquí.
            # El endpoint /api/nota-cobro/create/ es el responsable de crear la nota
            # y los registros contables asociados (Asiento/DetalleAsiento).

        except Exception as e:
            logger.exception("Error en perform_create Inscripcion %s: %s", getattr(inscripcion, 'idInscripcion', 'unknown'), e)
            # Propagar para que transaction.atomic haga rollback
            raise

    def post(self, request, *args, **kwargs):
        """
        Usamos el comportamiento por defecto de ListCreateAPIView.
        No intentamos adjuntar una nota a la respuesta (ya que la nota
        debe crearse explícitamente mediante /api/nota-cobro/create/).
        """
        return super().post(request, *args, **kwargs)

class InscripcionUsuarioList(generics.ListAPIView):
    """
    Devuelve las inscripciones del usuario autenticado (o si se pasa ?cedula=) con las cuotas
    incluidas (campo 'cuotas' que devuelve la serializer).
    """
    serializer_class = InscripcionSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        qs = Inscripcion.objects.select_related(
            'idPersona', 'idCohorte', 'idCohorte__idFormacion'
        ).prefetch_related(
            Prefetch(
                'idCohorte__idFormacion__cuotas',
                queryset=CuotaFormacion.objects.filter(is_active=True).order_by('orden'),
                to_attr='prefetched_cuotas'
            ),
            'inscripcioncuota_set'
        ).all()

        cedula_q = self.request.query_params.get('cedula')
        if cedula_q:
            ced = re.sub(r'\D', '', cedula_q)
            persona = Personas.objects.filter(cedula__iregex=rf"{ced}$").first()
            if persona:
                return qs.filter(idPersona_id=persona.idPersona)
            return qs.none()

        user = getattr(self.request, 'user', None)
        if user and not getattr(user, 'is_anonymous', False):
            try:
                usuario_rel = Usuarios.objects.filter(user_id=getattr(user, 'id', None)).first()
                if usuario_rel and getattr(usuario_rel, 'idPersona', None):
                    persona_id = usuario_rel.idPersona.idPersona if hasattr(usuario_rel.idPersona, 'idPersona') else usuario_rel.idPersona
                    return qs.filter(idPersona_id=persona_id)
            except Exception:
                pass
            try:
                ced_user = re.sub(r'\D', '', str(getattr(user, 'username', '') or ''))
                if ced_user:
                    persona = Personas.objects.filter(cedula__iregex=rf"{ced_user}$").first()
                    if persona:
                        return qs.filter(idPersona_id=persona.idPersona)
            except Exception:
                pass
        return qs.none()

class InscripcionDetail(generics.RetrieveAPIView):  # Cambié a Detail para claridad
    queryset = Inscripcion.objects.select_related(
        'idPersona',
        'idCohorte',
        'idCohorte__idFormacion'
    ).prefetch_related(
        Prefetch(
            'idCohorte__idFormacion__cuotas',
            queryset=CuotaFormacion.objects.filter(is_active=True).order_by('orden'),
            to_attr='prefetched_cuotas'
        )
    )
    serializer_class = InscripcionSerializer
    permission_classes = [IsAuthenticated]  # Seguridad

class NotasUsuarioAutenticadoView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        try:
            user = request.user
            
            if not hasattr(user, 'idPersona') or not user.idPersona:
                return Response({
                    'success': False,
                    'message': 'Usuario no tiene persona asociada',
                    'data': []
                }, status=404)
            
            persona = user.idPersona
            logger.info(f"🔍 Buscando notas para: {persona.nombres} {persona.apellidos} (Cédula: {persona.cedula})")

            # BUSCAR NOTAS DIRECTAS por idPersona
            notas_directas = Nota.objects.filter(idPersona=persona)
            logger.info(f"📄 Notas directas encontradas: {notas_directas.count()}")

            # BUSCAR NOTAS a través de inscripciones
            inscripciones_persona = Inscripcion.objects.filter(idPersona=persona)
            logger.info(f"📚 Inscripciones encontradas: {inscripciones_persona.count()}")
            
            # Log de inscripciones para debug
            for ins in inscripciones_persona:
                cohorte_nombre = getattr(ins.idCohorte, 'nombreCohorte', 'Sin cohorte') if ins.idCohorte else 'Sin cohorte'
                logger.info(f"  - Inscripción {ins.idInscripcion}: {cohorte_nombre}")

            # Obtener notas relacionadas con las inscripciones
            notas_relacionadas = NotaRelacionada.objects.filter(
                idInscripcion__in=inscripciones_persona
            ).select_related('idNota')
            
            notas_por_inscripcion = Nota.objects.filter(
                idNota__in=notas_relacionadas.values_list('idNota_id', flat=True)
            )
            
            logger.info(f"🔗 Notas por inscripción: {notas_por_inscripcion.count()}")

            # COMBINAR resultados
            todas_notas = (notas_directas | notas_por_inscripcion).distinct().order_by('-fechaEmision')
            
            logger.info(f"📋 Total de notas únicas: {todas_notas.count()}")

            # PREFETCH para optimizar - usando el nombre correcto del atributo
            prefetch_relacion = Prefetch(
                'relaciones',
                queryset=NotaRelacionada.objects.select_related(
                    'idInscripcion',
                    'idInscripcion__idCohorte',
                    'idInscripcion__idCohorte__idFormacion',
                    'idInscripcion__idPersona'
                ),
                to_attr='prefetched_relaciones'
            )
            
            # Aplicar prefetch y select_related
            notas_final = todas_notas.prefetch_related(prefetch_relacion).select_related('idPersona')
            
            # Log detallado de cada nota encontrada
            logger.info("--- DETALLE DE NOTAS ENCONTRADAS ---")
            for nota in notas_final:
                tiene_persona = "SÍ" if nota.idPersona else "NO"
                relaciones_count = len(getattr(nota, 'prefetched_relaciones', []))
                logger.info(f"  - Nota {nota.idNota}: {nota.numeroNota} | Estado: {nota.estado} | Total: {nota.totalNota} | Persona directa: {tiene_persona} | Relaciones: {relaciones_count}")
            
            # Serializar
            serializer = NotaSerializer(notas_final, many=True)
            
            logger.info(f"✅ Proceso completado. Enviando {notas_final.count()} notas")
            
            return Response({
                'success': True,
                'count': notas_final.count(),
                'data': serializer.data,
                'user_info': {
                    'persona_id': persona.idPersona,
                    'cedula': persona.cedula,
                    'nombre_completo': f"{persona.nombres} {persona.apellidos}"
                },
                'debug_info': {
                    'notas_directas_count': notas_directas.count(),
                    'inscripciones_count': inscripciones_persona.count(),
                    'notas_por_inscripcion_count': notas_por_inscripcion.count(),
                    'notas_final_count': notas_final.count()
                }
            })
            
        except Exception as e:
            logger.exception("Error crítico en NotasUsuarioAutenticadoView:")
            return Response({
                'success': False,
                'message': f'Error interno del servidor: {str(e)}',
                'data': []
            }, status=500)
    
class PagoCreateAPIView(APIView):
    """
    Endpoint para crear un nuevo Pago Temporal.
    """
    permission_classes = [IsAuthenticated] 

    def post(self, request, *args, **kwargs):
        logger.info(f"📥 Petición de pago temporal recibida: {request.data}")
        
        serializer = PagoCreateSerializer(data=request.data)
        
        try:
            serializer.is_valid(raise_exception=True)
            pago_temporal = serializer.save()
            
            # Respuesta adaptada para PagoTemporal
            response_data = {
                'success': True,
                'message': '¡Pago temporal registrado exitosamente! 🎉',
                'data': {
                    'idPagoTemporal': pago_temporal.idPagoTemporal,
                    'monto': float(pago_temporal.monto),
                    'fechaPago': pago_temporal.fechaPago.isoformat(),
                    'confirmado': pago_temporal.confirmado,
                    'nota': {
                        'idNota': pago_temporal.idNota.idNota,
                        'numeroNota': pago_temporal.idNota.numeroNota,
                        'estado': pago_temporal.idNota.estado,  # Estado permanece igual hasta confirmación
                    }
                }
            }
            logger.info(f"🎊 Pago temporal creado exitosamente: {pago_temporal.idPagoTemporal}")
            return Response(response_data, status=status.HTTP_201_CREATED)
            
        except serializers.ValidationError as e:
            logger.warning(f"Error de validación de pago temporal: {e.detail}")
            return Response({
                "success": False,
                "message": "Datos inválidos. Por favor revise los errores.",
                "errors": e.detail
            }, status=status.HTTP_400_BAD_REQUEST)
            
        except Exception as e:
            logger.error(f"Error crítico en la creación del pago temporal: {str(e)}")
            return Response({
                "success": False,
                "message": "Ocurrió un error inesperado al procesar el pago temporal.",
                "error": str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# --- ¡NUEVA VISTA DE PAGOS PARA CONFIRMAR LOS PAGOS! ---
class PagoConfirmAPIView(APIView):
    @transaction.atomic
    def post(self, request, pk):
        try:
            pago = PagoTemporal.objects.select_related('idNota', 'idCuentaBanco').get(pk=pk)
            if pago.confirmado:
                return Response({'success': False, 'message': 'Pago ya confirmado.'}, status=400)

            # Llamar al método que hace toda la lógica contable
            try:
                pago_principal = pago.confirmar_pago()
            except Exception as e:
                # si falla, retornamos la excepción y rollback por transaction.atomic
                return Response({'success': False, 'message': str(e)}, status=400)

            return Response({'success': True, 'message': 'Pago confirmado y registrado.', 'pago_id': getattr(pago_principal,'idPago', None)})
        except PagoTemporal.DoesNotExist:
            return Response({'success': False, 'message': 'Pago no encontrado.'}, status=404)
        except Exception as e:
            return Response({'success': False, 'message': str(e)}, status=500)


# --- ¡NUEVA VISTA DE PAGOS PARA DASHBOARD! ---
class PagoUsuarioListView(generics.ListAPIView):
    serializer_class = PagoSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        try:
            # Obtener el objeto Personas relacionado con el usuario autenticado
            persona = self.request.user.idPersona
        except Exception as e:
            logger.error(f"Error al obtener idPersona del usuario: {e}")
            return Pago.objects.none()
        
        if not persona:
             logger.warning("Usuario autenticado sin persona asociada.")
             return Pago.objects.none()

        # 1. Buscar notas asociadas a la persona
        notas_directas_ids = Nota.objects.filter(idPersona=persona).values_list('idNota', flat=True)
        
        # 2. Buscar pagos asociados a esas notas
        # Usamos Q para filtrar donde el idNota sea una de las IDs que encontramos
        return Pago.objects.filter(
            Q(idNota__in=notas_directas_ids)
        ).select_related(
            'idNota' # Optimizamos la consulta para el PagoListSerializer
        ).order_by('-fechaPago')
        
    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        
        # Estructura de respuesta que usa tu frontend
        return Response({
            'success': True,
            'count': queryset.count(),
            'data': serializer.data
        }, status=status.HTTP_200_OK)
    
def generar_numero_nota():
    fecha_actual = now().strftime('%Y%m%d')
    numero_unico = uuid.uuid4().hex[:6].upper()
    return f"NOTA-CUOTA-{fecha_actual}-{numero_unico}"

class CuotaCobroCreateAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request):
        logger.info("Petición de pago de CUOTA recibida: %s", request.data)
        serializer = CuotaPagoTemporalSerializer(data=request.data, context={'request': request})

        try:
            serializer.is_valid(raise_exception=True)
            pago_temporal = serializer.save()  # todo el flujo está en el serializer

            # intentar resolver información adicional sobre la nota_relacionada creada
            nota = getattr(pago_temporal, 'idNota', None)
            created_nr_id = serializer.context.get('created_nr_id', None)
            created_nr_raw_idCuota = serializer.context.get('created_nr_raw_idCuota', None)

            # traer la nota relacionada si no la teníamos
            nr = None
            if created_nr_id:
                nr = NotaRelacionada.objects.filter(pk=created_nr_id).first()
            else:
                # fallback: buscar por nota
                if nota:
                    nr = NotaRelacionada.objects.filter(idNota=nota).first()

            # determinar ids útiles para frontend (inscripcion_cuota_id, cuotaFormacion_id)
            id_inscripcion_cuota = None
            id_cuota_formacion = None
            if nr:
                # raw id guardado en columna (puede apuntar a InscripcionCuota.id o a CuotaFormacion.idCuota)
                raw = getattr(nr, 'idCuota_id', None)
                if raw:
                    # si existe una InscripcionCuota con pk == raw -> es idInscripcionCuota
                    if InscripcionCuota.objects.filter(pk=raw).exists():
                        id_inscripcion_cuota = raw
                        # obtener su idCuota (CuotaFormacion) si se necesita
                        try:
                            ins_c = InscripcionCuota.objects.get(pk=raw)
                            id_cuota_formacion = getattr(ins_c.idCuota, 'idCuota', getattr(ins_c.idCuota, 'pk', None))
                        except Exception:
                            id_cuota_formacion = None
                    else:
                        # si no existe InscripcionCuota con pk raw, probablemente raw sea idCuota (CuotaFormacion.idCuota)
                        id_cuota_formacion = raw

            result = {
                'idPagoTemporal': getattr(pago_temporal, 'idPagoTemporal', None),
                'idNota': getattr(nota, 'idNota', None) if nota else None,
                'numeroNota': getattr(nota, 'numeroNota', None) if nota else None,
                'monto': float(getattr(pago_temporal, 'monto', 0)),
                'confirmado': bool(getattr(pago_temporal, 'confirmado', False)),
                'idInscripcionCuota': id_inscripcion_cuota,
                'idCuotaFormacion': id_cuota_formacion,
                'debug_steps': serializer.context.get('debug_steps', [])
            }

            return Response({
                'success': True,
                'message': 'Solicitud de pago de cuota registrada correctamente.',
                'data': result
            }, status=drf_status.HTTP_201_CREATED)

        except serializers.ValidationError as ve:
            logger.warning("Validación fallo en pago cuota: %s", ve)
            return Response({'success': False, 'errors': ve.detail}, status=drf_status.HTTP_400_BAD_REQUEST)

        except Exception as exc:
            logger.exception("Error creando nota/pago temporal de cuota")
            return Response({
                'success': False,
                'message': 'Ocurrió un error creando la nota de cuota.',
                'error': str(exc)
            }, status=drf_status.HTTP_500_INTERNAL_SERVER_ERROR)
        
class CuotaPagoTemporalCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        logger.info("Petición de pago de CUOTA recibida: %s", request.data)
        serializer = CuotaPagoTemporalSerializer(data=request.data, context={'request': request})
        try:
            serializer.is_valid(raise_exception=True)
            pago_temporal = serializer.save()
            debug = serializer.context.get('debug_steps', None)
            return Response({
                'success': True,
                'message': 'Solicitud de pago de cuota registrada.',
                'data': {
                    'idPagoTemporal': pago_temporal.idPagoTemporal,
                    'monto': float(pago_temporal.monto),
                    'fechaPago': pago_temporal.fechaPago.isoformat() if pago_temporal.fechaPago else None,
                    'confirmado': pago_temporal.confirmado,
                    'nota': {
                        'idNota': pago_temporal.idNota.idNota,
                        'numeroNota': pago_temporal.idNota.numeroNota,
                        'estado': pago_temporal.idNota.estado,
                    }
                },
                'debug': debug
            }, status=status.HTTP_201_CREATED)
        except drf_serializers.ValidationError as e:
            logger.warning("Error de validación: %s", e.detail)
            return Response({"success": False, "message": "Datos inválidos.", "errors": e.detail}, status=status.HTTP_400_BAD_REQUEST)
        except IntegrityError as ie:
            tb = traceback.format_exc()
            logger.exception("IntegrityError creando pago de cuota: %s\n%s", ie, tb)
            return Response({"success": False, "message": "Error de integridad en la BD.", "error": str(ie), "traceback": tb}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        except Exception as e:
            tb = traceback.format_exc()
            logger.exception("Error inesperado creando pago de cuota: %s\n%s", e, tb)
            return Response({"success": False, "message": "Ocurrió un error procesando el pago.", "error": str(e), "traceback": tb}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class RequisitoListCreate(generics.ListCreateAPIView):
    queryset = Requisito.objects.all()  # Usa el modelo Requisito
    serializer_class = RequisitoSerializer  # Usa el serializador RequisitoSerializer

class ServicioListCreate(generics.ListCreateAPIView):
    queryset = Servicio.objects.all()  # Usa el modelo Servicio
    serializer_class = ServicioSerializer  # Usa el serializador ServicioSerializer

class TramiteListCreate(generics.ListCreateAPIView):
    queryset = Tramite.objects.all()  # Usa el modelo Tramite
    serializer_class = TramiteSerializer  # Usa el serializador TramiteSerializer

class SolicitudListCreate(generics.ListCreateAPIView):
    queryset = Solicitud.objects.all()  # Usa el modelo TramSolicitudite
    serializer_class = SolicitudSerializer  # Usa el serializador SolicitudSerializer

class BancoListCreate(generics.ListCreateAPIView):
    queryset = Banco.objects.all()  # Usa el modelo Banco
    serializer_class = BancoSerializer  # Usa el serializador BancoSerializer

class MonedaListCreate(generics.ListCreateAPIView):
    queryset = Moneda.objects.all()  # Usa el modelo Moneda
    serializer_class = MonedaSerializer  # Usa el serializador MonedaSerializer

class TasaListCreate(generics.ListCreateAPIView):
    queryset = Tasa.objects.all()  # Usa el modelo Tasa
    serializer_class = TasaSerializer  # Usa el serializador TasaSerializer

class CedulaTokenObtainView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request, *args, **kwargs):
        serializer = CedulaTokenObtainSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(serializer.validated_data, status=status.HTTP_200_OK)

class UsuarioListCreate(generics.ListCreateAPIView):
    queryset = Usuarios.objects.all()  # Usa el modelo Tasa
    serializer_class = UsuarioSerializer  # Usa el serializador UsuarioSerializer

# Vistas para contabilidad
class LibroDiarioAPIView(APIView):
    def get(self, request):
        asientos = AsientoContable.objects.prefetch_related('detalles').order_by('fechaAsiento', 'numeroAsiento')
        serializer = AsientoContableSerializer(asientos, many=True)
        return Response(serializer.data)

class LibroMayorAPIView(APIView):
    def get(self, request):
        cuentas = PlanCuenta.objects.annotate(
            total_debe=Sum('detalleasiento__debe'),
            total_haber=Sum('detalleasiento__haber')
        ).order_by('codigoPlanCuenta')
        serializer = PlanCuentaSerializer(cuentas, many=True)
        return Response(serializer.data)

class BalanceCuentasAPIView(APIView):
    def get(self, request):
        tipos_cuentas = PlanCuenta.objects.values('tipoPlanCuenta').annotate(
            total_debe=Sum('detalleasiento__debe'),
            total_haber=Sum('detalleasiento__haber')
        ).order_by('tipoPlanCuenta')

        # Calcular el saldo para cada tipo de cuenta
        for tipo in tipos_cuentas:
            debe = tipo['total_debe'] or 0
            haber = tipo['total_haber'] or 0
            if debe > haber:
                tipo['saldo'] = f"Deudor: {debe - haber:.2f}"
            elif haber > debe:
                tipo['saldo'] = f"Acreedor: {haber - debe:.2f}"
            else:
                tipo['saldo'] = "Saldo Cero"

        return Response(list(tipos_cuentas))

class IngresosAPIView(APIView):
    def get(self, request):
        ingresos = PlanCuenta.objects.filter(tipoPlanCuenta='ingreso').annotate(
            total_ingreso=Sum('detalleasiento__haber') - Sum('detalleasiento__debe')
        ).order_by('codigoPlanCuenta')
        serializer = PlanCuentaSerializer(ingresos, many=True)
        return Response(serializer.data)

class EgresosAPIView(APIView):
    def get(self, request):
        egresos = PlanCuenta.objects.filter(tipoPlanCuenta='gasto').annotate(
            total_egreso=Sum('detalleasiento__debe') - Sum('detalleasiento__haber')
        ).order_by('codigoPlanCuenta')
        serializer = PlanCuentaSerializer(egresos, many=True)
        return Response(serializer.data)

class ConfiguracionAPIView(APIView):
    permission_classes = [AllowAny]
    
    def get(self, request):
        try:
            configuracion = Configuracion.objects.first()
            if configuracion:
                serializer = ConfiguracionSerializer(configuracion)
                return Response({
                    'success': True,
                    'data': serializer.data
                })
            else:
                return Response({
                    'success': False,
                    'message': 'No hay configuración registrada en el sistema'
                }, status=404)
                
        except Exception as e:
            return Response({
                'success': False,
                'message': f'Error al obtener configuración: {str(e)}'
            }, status=500)