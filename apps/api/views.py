from datetime import timedelta
import re
import traceback
from django.db.models import Prefetch
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated

from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework.permissions import AllowAny
from django.db.models import Sum
from apps.home.models import Personas, Materia, Cohorte, Cargo, Requisito, Servicio, Tramite, Moneda, Tasa, Formacion, TipoFormacion, Usuarios, CuotaFormacion
from .serializers import PagoSerializer, PersonaSerializer, CedulaTokenObtainSerializer, TipoPersonaSerializer, PersonaTPSerializer, FormacionSerializer, TPFormacionSerializer, MateriaSerializer, CohorteSerializer, CargoSerializer, HonorarioSerializer, InscripcionSerializer, RequisitoSerializer, ServicioSerializer, TramiteSerializer, SolicitudSerializer, MonedaSerializer, TasaSerializer, UsuarioSerializer, AsientoContableSerializer, PlanCuentaSerializer, PeriodoContableSerializer, CuotaFormacionSerializer, NotaSerializer  # Importa ambos serializadores
from apps.persona.models import PersonaTP, TipoPersona
from apps.honorario.models import Honorario
from apps.inscripcion.models import Inscripcion
from apps.solicitud.models import Solicitud
from apps.asientoContable.models import AsientoContable, DetalleAsiento
from apps.planCuenta.models import PlanCuenta
from apps.periodoContable.models import periodoContable
from django.db import transaction
from django.utils.timezone import now
from decimal import Decimal
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
        # Crea la inscripción
        inscripcion = serializer.save()
        
        try:
            # 🔥 Crea la nota automáticamente (lógica de tu NotaCobroCreateAPIView)
            configuracion = Configuracion.objects.first()
            if not configuracion:
                raise ValueError('Configuración del sistema no encontrada')

            moneda_configuracion = configuracion.moneda
            tasa = Tasa.objects.filter(idMoneda=moneda_configuracion).order_by('-idTasa').first()
            if not tasa:
                raise ValueError(f'No se encontró tasa para la moneda {moneda_configuracion.nombreMoneda}')

            # Valor de inscripción desde formacion (ajusta si viene en payload)
            valor_inscripcion = inscripcion.idCohorte.idFormacion.valorInscripcion  # O de payload si envías

            # Periodo activo
            periodo_activo = periodoContable.objects.filter(estadoPeriodo=True).first()
            if not periodo_activo:
                periodo_activo = periodoContable.objects.order_by('-idPeriodo').first()
            if not periodo_activo:
                raise ValueError('No hay periodo contable activo')

            # Asiento contable
            numero_asiento = f"ASIENTO-{now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
            asiento = AsientoContable.objects.create(
                numeroAsiento=numero_asiento,
                fechaAsiento=now().date(),
                conceptoAsiento=f"Asiento para inscripción {inscripcion.idInscripcion}",
                idPeriodo=periodo_activo
            )

            # Nota
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
                subtotalExento=Decimal('0.00'),  # Ajusta cálculos
                subtotalGravado=valor_inscripcion,
                iva=Decimal('0.00'),  # Ajusta
                descuento=Decimal('0.00'),  # Ajusta si descuento
                totalNota=valor_inscripcion,  # Ajusta
                idTasa=tasa,
                estado='PENDIENTE',
                observaciones='NOTA AUTOMÁTICA POR INSCRIPCIÓN'
            )

            # Relación
            NotaRelacionada.objects.create(
                idNota=nota,
                idInscripcion=inscripcion
            )

            # Detalles asiento (ajusta planes)
            plan_debe = PlanArticulo.objects.filter(tipoArticulo='INSCRIPCION', tipo=1).order_by('-fecha').first()
            plan_haber = PlanArticulo.objects.filter(tipoArticulo='INSCRIPCION', tipo=0).order_by('-fecha').first()
            if plan_debe and plan_haber:
                DetalleAsiento.objects.create(idAsiento=asiento, idPlanCuenta=plan_debe.idPlanCuenta, debe=nota.totalNota, haber=Decimal('0.00'))
                DetalleAsiento.objects.create(idAsiento=asiento, idPlanCuenta=plan_haber.idPlanCuenta, debe=Decimal('0.00'), haber=nota.totalNota)
            else:
                raise ValueError('No cuentas contables para INSCRIPCION')

            # Actualiza inscripción
            inscripcion.estadoPago = 'PENDIENTE'
            inscripcion.save()

            # Agrega nota a serializer data para response
            self.nota_creada = nota
        except Exception as e:
            logger.error(f"Error creando nota para inscripción {inscripcion.idInscripcion}: {str(e)}")
            raise  # Rollback

    def post(self, request, *args, **kwargs):
        try:
            response = super().post(request, *args, **kwargs)
            if hasattr(self, 'nota_creada'):
                response.data['nota'] = NotaSerializer(self.nota_creada).data
            return response
        except Exception as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)

class InscripcionUsuarioList(generics.ListAPIView):
    """
    Devuelve las inscripciones del usuario autenticado (o si se pasa ?cedula=) con las cuotas
    incluidas (campo 'cuotas' que devuelve la serializer).
    """
    serializer_class = InscripcionSerializer
    permission_classes = [AllowAny]  # si prefieres exigir token usa IsAuthenticated

    def get_queryset(self):
        qs = Inscripcion.objects.select_related(
            'idPersona', 'idCohorte', 'idCohorte__idFormacion'
        ).all()

        # Si pasan ?cedula=V-12345678 filtramos por esa cédula
        cedula_q = self.request.query_params.get('cedula')
        if cedula_q:
            ced = re.sub(r'\D', '', cedula_q)
            persona = Personas.objects.filter(cedula__iregex=rf"{ced}$").first()
            if persona:
                return qs.filter(idPersona_id=persona.idPersona)
            return qs.none()

        # Intenta deducir persona asociado a request.user via modelo Usuarios (ajusta si tu relación es distinta)
        user = getattr(self.request, 'user', None)
        if user and not getattr(user, 'is_anonymous', False):
            # Intenta buscar en tabla Usuarios que referencie persona
            try:
                usuario_rel = Usuarios.objects.filter(user_id=getattr(user, 'id', None)).first()
                if usuario_rel and getattr(usuario_rel, 'idPersona', None):
                    persona_id = usuario_rel.idPersona.idPersona if hasattr(usuario_rel.idPersona, 'idPersona') else usuario_rel.idPersona
                    return qs.filter(idPersona_id=persona_id)
            except Exception:
                pass

            # fallback: buscar persona por username / campo cedula en user
            try:
                ced_user = re.sub(r'\D', '', str(getattr(user, 'username', '') or ''))
                if ced_user:
                    persona = Personas.objects.filter(cedula__iregex=rf"{ced_user}$").first()
                    if persona:
                        return qs.filter(idPersona_id=persona.idPersona)
            except Exception:
                pass

        # por defecto no exponemos todas las inscripciones
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

class NotasUsuarioAutenticadoView(generics.ListAPIView):
    serializer_class = NotaSerializer
    permission_classes = [IsAuthenticated]

    def get_persona_id(self):
        # 1) buscar via tabla Usuarios si existe (ajusta según tu modelo Usuarios)
        user = getattr(self.request, 'user', None)
        try:
            from apps.home.models import Usuarios
            urel = Usuarios.objects.filter(user_id=getattr(user, 'id', None)).first()
            if urel and getattr(urel, 'idPersona', None):
                return getattr(urel.idPersona, 'idPersona', urel.idPersona)
        except Exception:
            pass

        # 2) permitir ?cedula=... como fallback
        cedula_q = self.request.query_params.get('cedula')
        if cedula_q:
            ced = re.sub(r'\D', '', cedula_q)
            p = Personas.objects.filter(cedula__iregex=rf"{ced}$").first()
            if p:
                return p.idPersona

        return None

    def get_queryset(self):
        persona_id = self.get_persona_id()
        if not persona_id:
            return Nota.objects.none()

        prefetch_rel = Prefetch(
            'notarelacionada_set',
            queryset=NotaRelacionada.objects.select_related('idInscripcion__idCohorte__idFormacion'),
            to_attr='prefetched_notarelacionadas'
        )

        qs = Nota.objects.filter(
            notarelacionada__idInscripcion__idPersona_id=persona_id
        ).prefetch_related(prefetch_rel).distinct()

        # Opcional: filtrar solo notas con formacion resuelta (para debug)
        # qs = qs.filter(notarelacionada__idInscripcion__idCohorte__idFormacion__isnull=False)

        return qs

class PagoCreateAPIView(APIView):
    @transaction.atomic
    def post(self, request):
        print("🚀 [PAGO-VIEW] Iniciando procesamiento...")
        serializer = PagoCreateSerializer(data=request.data, context={'request': request})

        if not serializer.is_valid():
            print(f"❌ Validación falló: {serializer.errors}")
            return Response({
                'success': False,
                'message': 'Datos inválidos',
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)

        print("✅ Serializer válido")

        # Antes de llamar a serializer.save() validamos que exista periodo contable y tasa en forma robusta
        # (Nota ya fue comprobada en serializer.validate y está en serializer.context['nota'])
        nota = serializer.context['nota']

        # Intentar obtener moneda por configuración, sino fallback a Moneda id=1
        configuracion = Configuracion.objects.first()
        moneda = None
        if configuracion and getattr(configuracion, 'moneda', None):
            moneda = configuracion.moneda
        else:
            moneda = Moneda.objects.filter(idMoneda=1).first()

        if not moneda:
            return Response({
                'success': False,
                'message': 'Moneda del sistema no configurada (ni configuración ni moneda id=1).'
            }, status=status.HTTP_400_BAD_REQUEST)

        tasa = Tasa.objects.filter(idMoneda=moneda).order_by('-idTasa').first()
        if not tasa:
            return Response({
                'success': False,
                'message': f'No se encontró tasa para la moneda {moneda}.'
            }, status=status.HTTP_400_BAD_REQUEST)

        periodo_activo = periodoContable.objects.filter(estadoPeriodo=True).first()
        if not periodo_activo:
            return Response({
                'success': False,
                'message': 'No hay periodo contable activo'
            }, status=status.HTTP_400_BAD_REQUEST)

        # Todo validado — crear dentro de la misma transacción (serializer.create hace la mayoría del trabajo)
        try:
            pago = serializer.save()
            # serializar la respuesta
            pago_serializado = PagoSerializer(pago).data

            response_data = {
                'success': True,
                'message': '¡Pago procesado exitosamente! 🎉',
                'data': {
                    'idPago': pago.idPago,
                    'numeroAsiento': pago.idAsiento.numeroAsiento,
                    'monto': float(pago.monto),
                    'fechaPago': pago.fechaPago.isoformat(),
                    'formaPago': pago.formaPago,
                    'referencia': pago.referencia or '',
                    'nota': {
                        'idNota': nota.idNota,
                        'numeroNota': nota.numeroNota,
                        'nuevoEstado': nota.estado,
                        'totalNota': float(nota.totalNota)
                    }
                }
            }
            print("🎊 Pago procesado exitosamente!")
            return Response(response_data, status=status.HTTP_201_CREATED)

        except serializers.ValidationError as ve:
            # errores arrojados por serializer.create
            print(f"💥 ValidationError en creación: {ve.detail if hasattr(ve, 'detail') else str(ve)}")
            return Response({
                'success': False,
                'message': 'Error en validación al crear pago',
                'errors': ve.detail if hasattr(ve, 'detail') else str(ve)
            }, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            import traceback
            print(f"💥 Error en PagoCreateAPIView: {str(e)}")
            print(f"📋 Traceback: {traceback.format_exc()}")
            return Response({
                'success': False,
                'message': f'Error procesando pago: {str(e)}'
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



##########################API DE PAGO TEMPORAL APP ############################

from rest_framework import status
from apps.factura.models import PagoTemporal
from .serializers import PagoTemporalSerializer 
class PagoTemporalCreateAPIView(APIView):
    """
    API para registrar un nuevo PagoTemporal.
    """
    def post(self, request, *args, **kwargs):
        serializer = PagoTemporalSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({
                'success': True,
                'message': 'Pago temporal registrado exitosamente.',
                'data': serializer.data
            }, status=status.HTTP_201_CREATED)
        return Response({
            'success': False,
            'message': 'Error al registrar el pago temporal.',
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)