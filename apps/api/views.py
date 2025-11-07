from datetime import timedelta
import re
import traceback
from django.db.models import Prefetch, Q
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated

from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework.permissions import AllowAny
from django.db.models import Sum
from apps.home.models import Personas, Materia, Cohorte, Cargo, Requisito, Servicio, Tramite, Moneda, Tasa, Formacion, TipoFormacion, Usuarios, CuotaFormacion
from .serializers import PagoSerializer, PersonaSerializer, CedulaTokenObtainSerializer, TipoPersonaSerializer, PersonaTPSerializer, FormacionSerializer, TPFormacionSerializer, MateriaSerializer, CohorteSerializer, CargoSerializer, HonorarioSerializer, InscripcionSerializer, RequisitoSerializer, ServicioSerializer, TramiteSerializer, SolicitudSerializer, BancoSerializer, MonedaSerializer, TasaSerializer, UsuarioSerializer, AsientoContableSerializer, PlanCuentaSerializer, PeriodoContableSerializer, CuotaFormacionSerializer, NotaSerializer, ConfiguracionSerializer, CuotaPagoTemporalSerializer  # Importa ambos serializadores
from apps.persona.models import PersonaTP, TipoPersona
from apps.honorario.models import Honorario
from apps.inscripcion.models import Inscripcion, InscripcionCuota
from apps.solicitud.models import Solicitud
from apps.cuentaBanco.models import Banco
from apps.asientoContable.models import AsientoContable, DetalleAsiento
from apps.planCuenta.models import PlanCuenta
from apps.periodoContable.models import periodoContable
from django.db import transaction
from django.utils.timezone import now
from decimal import Decimal, InvalidOperation
import uuid

from apps.factura.models import Nota, Pago, NotaRelacionada, PlanArticulo
from apps.home.models import Moneda, Tasa, Configuracion
from .serializers import PagoCreateSerializer

from apps.api import serializers

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
        # 1) Guardar inscripción (ya activa)
        inscripcion = serializer.save()
        try:
            # Marcar activa si tu modelo la requiere
            try:
                inscripcion.is_active = True
                inscripcion.save(update_fields=['is_active'])
            except Exception:
                # No todos los modelos tienen is_active; ignorar si falla
                pass

            # 2) Determinar la formación y valor de inscripción (defensivo)
            formacion = None
            valor_inscripcion = None
            cohorte = getattr(inscripcion, 'idCohorte', None)
            if cohorte:
                formacion = getattr(cohorte, 'idFormacion', None)

            if formacion:
                valor_inscripcion = getattr(formacion, 'valorInscripcion', None)

            if valor_inscripcion is None:
                raise ValueError('No se pudo determinar valor_inscripcion desde la cohorte/formación.')

            # 3) Crear inscripcion-cuotas: usar prefetched_cuotas si existe (mejor rendimiento)
            cuotas_para_crear = []
            prefetched = getattr(formacion, 'prefetched_cuotas', None)
            if prefetched and isinstance(prefetched, (list, tuple)):
                cuotas_qs = prefetched
            else:
                cuotas_qs = CuotaFormacion.objects.filter(idFormacion=formacion, is_active=True).order_by('orden')

            for cuota in cuotas_qs:
                # Crea la instancia (puedes ajustar campos iniciales según tu modelo)
                cuotas_para_crear.append(
                    InscripcionCuota(
                        idInscripcion=inscripcion,
                        idCuota=cuota,
                        estadoPago='EN ESPERA',
                        montoPagado=Decimal('0.00')
                    )
                )

            if cuotas_para_crear:
                # Bulk create para eficiencia
                InscripcionCuota.objects.bulk_create(cuotas_para_crear)
                logger.debug(f"Se crearon {len(cuotas_para_crear)} InscripcionCuota(s) para Inscripcion {inscripcion.idInscripcion}")
            else:
                logger.debug(f"No se encontraron cuotas activas para la formación asociada a Inscripcion {inscripcion.idInscripcion}")

            # 4) Obtener periodo contable y tasa (como antes)
            periodo_activo = periodoContable.objects.filter(estadoPeriodo=True).first()
            if not periodo_activo:
                periodo_activo = periodoContable.objects.order_by('-idPeriodo').first()
            if not periodo_activo:
                raise ValueError('No hay periodo contable activo')

            configuracion = Configuracion.objects.first()
            if not configuracion:
                raise ValueError('Configuración del sistema no encontrada')

            moneda_configuracion = configuracion.moneda
            tasa = Tasa.objects.filter(idMoneda=moneda_configuracion).order_by('-idTasa').first()
            if not tasa:
                raise ValueError(f'No se encontró tasa para la moneda {moneda_configuracion}')

            # 5) Crear asiento contable
            numero_asiento = f"ASIENTO-{now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
            asiento = AsientoContable.objects.create(
                numeroAsiento=numero_asiento,
                fechaAsiento=now().date(),
                conceptoAsiento=f"Asiento para inscripción {inscripcion.idInscripcion}",
                idPeriodo=periodo_activo
            )

            # 6) Crear Nota de Cobro
            numero_nota = f"NOTA-{now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
            nota = Nota.objects.create(
                idAsiento=asiento,
                idPersona=inscripcion.idPersona,
                numeroNota=numero_nota,
                tipoOperacion='COBRO',
                tipoArticulo='INSCRIPCION',
                fechaEmision=now().date(),
                fechaVencimiento=now().date() + timedelta(days=1),
                formaPago='CONTADO',
                subtotalExento=Decimal('0.00'),
                subtotalGravado=Decimal(str(valor_inscripcion)),
                iva=Decimal('0.00'),
                descuento=Decimal('0.00'),
                totalNota=Decimal(str(valor_inscripcion)),
                idTasa=tasa,
                estado='PENDIENTE',
                observaciones='NOTA AUTOMÁTICA POR INSCRIPCIÓN'
            )

            # 7) Relacionar nota <-> inscripción
            NotaRelacionada.objects.create(
                idNota=nota,
                idInscripcion=inscripcion
            )

            # 8) Crear detalles de asiento
            plan_debe = PlanArticulo.objects.filter(tipoArticulo='INSCRIPCION', tipo=1).order_by('-fecha').first()
            plan_haber = PlanArticulo.objects.filter(tipoArticulo='INSCRIPCION', tipo=0).order_by('-fecha').first()
            if plan_debe and plan_haber:
                DetalleAsiento.objects.create(idAsiento=asiento, idPlanCuenta=plan_debe.idPlanCuenta, debe=nota.totalNota, haber=Decimal('0.00'))
                DetalleAsiento.objects.create(idAsiento=asiento, idPlanCuenta=plan_haber.idPlanCuenta, debe=Decimal('0.00'), haber=nota.totalNota)
            else:
                raise ValueError('No cuentas contables para INSCRIPCION')

            # 9) Actualizar estado de inscripción y guardar
            inscripcion.estadoPago = 'PENDIENTE'
            inscripcion.save()

            # 10) Guardar nota creada para devolverla en la respuesta POST
            self.nota_creada = nota

        except Exception as e:
            logger.exception(f"Error creando nota/cuotas para inscripción {getattr(inscripcion, 'idInscripcion', 'unknown')}: {e}")
            # Propagar excepción para que transaction.atomic haga rollback
            raise

    def post(self, request, *args, **kwargs):
        try:
            response = super().post(request, *args, **kwargs)
            if hasattr(self, 'nota_creada'):
                response.data['nota'] = NotaSerializer(self.nota_creada).data
            return response
        except Exception as e:
            logger.exception("Error en InscripcionListCreate.post: %s", e)
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)


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

class CuotaPagoTemporalCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        logger.info("Petición de pago de CUOTA recibida: %s", request.data)
        serializer = CuotaPagoTemporalSerializer(data=request.data, context={'request': request})
        try:
            serializer.is_valid(raise_exception=True)
            pago_temporal = serializer.save()
            # intentar leer debug_steps si el serializer los dejó
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
        except serializers.ValidationError as e:
            logger.warning("Error de validacion: %s", e.detail)
            return Response({"success": False, "message": "Datos inválidos.", "errors": e.detail}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            # si el serializer lanzó el Exception con dict (ver create), lo desenpaquetamos
            payload = {}
            try:
                # si e.args[0] es un dict con info debug
                first = e.args[0] if len(e.args) else None
                if isinstance(first, dict):
                    payload = first
                else:
                    payload = {"error": str(e)}
            except Exception:
                payload = {"error": str(e)}
            tb = payload.get('traceback') or traceback.format_exc()
            debug_steps = payload.get('debug_steps') or []
            logger.exception("Error creando pago de cuota: %s", tb)
            return Response({
                'success': False,
                'message': 'Ocurrió un error procesando el pago.',
                'error': payload.get('error', str(e)),
                'traceback': tb,
                'debug_steps': debug_steps
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)



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