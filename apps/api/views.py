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
from .serializers import PagoSerializer, PersonaSerializer, CedulaTokenObtainSerializer, TipoPersonaSerializer, PersonaTPSerializer, FormacionSerializer, TPFormacionSerializer, MateriaSerializer, CohorteSerializer, CargoSerializer, HonorarioSerializer, InscripcionSerializer, RequisitoSerializer, ServicioSerializer, TramiteSerializer, SolicitudSerializer, BancoSerializer, MonedaSerializer, TasaSerializer, UsuarioSerializer, AsientoContableSerializer, PlanCuentaSerializer, PeriodoContableSerializer, CuotaFormacionSerializer, NotaSerializer  # Importa ambos serializadores
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

            # 8) Crear detalles de asiento (usar booleano True/False)
            plan_debe = PlanArticulo.objects.filter(tipoArticulo='INSCRIPCION', tipo=True).order_by('-fecha').first()
            plan_haber = PlanArticulo.objects.filter(tipoArticulo='INSCRIPCION', tipo=False).order_by('-fecha').first()
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

class NotasUsuarioAutenticadoView(generics.ListAPIView):
    serializer_class = NotaSerializer
    permission_classes = [IsAuthenticated]

    def get_persona(self):
        try:
            # intenta devolver instancia Personas (no id)
            if hasattr(self.request.user, 'idPersona') and self.request.user.idPersona:
                return self.request.user.idPersona
            usuario_rel = Usuarios.objects.filter(user_id=getattr(self.request.user, 'id', None)).first()
            if usuario_rel and getattr(usuario_rel, 'idPersona', None):
                return usuario_rel.idPersona
            return None
        except Exception as e:
            logger.exception("Error obteniendo persona: %s", e)
            return None

    def get_queryset(self):
        persona = self.get_persona()
        if not persona:
            return Nota.objects.none()

        prefetch_relacion = Prefetch(
            'relaciones',
            queryset=NotaRelacionada.objects.select_related('idInscripcion__idCohorte__idFormacion').filter(idInscripcion__isnull=False),
            to_attr='prefetched_relaciones_con_inscripcion'
        )

        qs = Nota.objects.filter(
            relaciones__idInscripcion__idPersona=persona
        ).prefetch_related(prefetch_relacion).distinct()
        return qs
    
class PagoCreateAPIView(APIView):
    @transaction.atomic
    def post(self, request):
        try:
            data = request.data
            print(f"📥 Datos recibidos: {data}")
            
            # Validar datos requeridos
            required_fields = ['idNota', 'formaPago', 'monto', 'fechaPago']
            for field in required_fields:
                if field not in data:
                    return Response({
                        'success': False,
                        'message': f'Campo requerido faltante: {field}'
                    }, status=status.HTTP_400_BAD_REQUEST)

            # Obtener y validar nota
            try:
                nota = Nota.objects.get(idNota=data['idNota'])
                print(f"✅ Nota encontrada: {nota.numeroNota} - Estado: {nota.estado}")
            except Nota.DoesNotExist:
                return Response({
                    'success': False,
                    'message': 'Nota no encontrada'
                }, status=status.HTTP_404_NOT_FOUND)

            if nota.estado == 'PAGADA':
                return Response({
                    'success': False,
                    'message': 'Esta nota ya ha sido pagada completamente'
                }, status=status.HTTP_400_BAD_REQUEST)

            # Validar monto
            try:
                monto_pago = Decimal(str(data['monto']))
                if monto_pago <= 0:
                    return Response({
                        'success': False,
                        'message': 'El monto debe ser mayor a 0'
                    }, status=status.HTTP_400_BAD_REQUEST)

                if monto_pago > nota.totalNota:
                    return Response({
                        'success': False,
                        'message': f'El monto no puede ser mayor al total de la nota (${nota.totalNota})'
                    }, status=status.HTTP_400_BAD_REQUEST)
            except (ValueError, InvalidOperation):
                return Response({
                    'success': False,
                    'message': 'Formato de monto inválido'
                }, status=status.HTTP_400_BAD_REQUEST)

            # 🔥 CORRECCIÓN: Obtener tasa de la configuración, no moneda base
            configuracion = Configuracion.objects.first()
            if not configuracion:
                return Response({
                    'success': False,
                    'message': 'Configuración del sistema no encontrada'
                }, status=status.HTTP_400_BAD_REQUEST)

            moneda_configuracion = configuracion.moneda
            tasa = Tasa.objects.filter(idMoneda=moneda_configuracion).order_by('-idTasa').first()
            
            if not tasa:
                return Response({
                    'success': False,
                    'message': f'No se encontró tasa para la moneda de configuración ({moneda_configuracion.nombreMoneda})'
                }, status=status.HTTP_400_BAD_REQUEST)

            print(f"✅ Tasa encontrada: {tasa.idTasa} - {tasa.montoTasa}")

            # Obtener periodo contable activo
            periodo_activo = periodoContable.objects.filter(estadoPeriodo=True).first()
            if not periodo_activo:
                return Response({
                    'success': False,
                    'message': 'No hay periodo contable activo'
                }, status=status.HTTP_400_BAD_REQUEST)

            print(f"✅ Periodo activo: {periodo_activo.nombrePeriodo}")

            # 🔥 CORRECCIÓN: Crear asiento contable con número único
            numero_asiento = f"PAGO-{now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
            
            asiento = AsientoContable.objects.create(
                numeroAsiento=numero_asiento,
                fechaAsiento=now().date(),
                conceptoAsiento=f"Pago de {data['formaPago']} - Nota: {nota.numeroNota}",
                idPeriodo=periodo_activo
            )
            print(f"✅ Asiento contable creado: {asiento.idAsiento}")

            # 🔥 CORRECCIÓN: Crear pago según el modelo REAL
            pago = Pago.objects.create(
                idNota=nota,
                idAsiento=asiento,
                idTasa=tasa,
                # idCuentaBanco se deja null por ahora (no viene del frontend)
                monto=monto_pago,
                fechaPago=data['fechaPago'],
                formaPago=data['formaPago'],
                referencia=data.get('referencia', ''),
                observaciones=data.get('observaciones', '')
                # fechaRegistro se auto-genera
            )
            print(f"✅ Pago creado: {pago.idPago}")

            # Actualizar estado de la nota
            if monto_pago >= nota.totalNota:
                nota.estado = 'PAGADA'
                print(f"✅ Nota marcada como PAGADA")
            else:
                nota.estado = 'PARCIAL'
                print(f"✅ Nota marcada como PARCIAL")
            
            nota.save()

            # Actualizar estado de la inscripción relacionada si existe
            try:
                nota_relacionada = NotaRelacionada.objects.filter(idNota=nota).first()
                if nota_relacionada and nota_relacionada.idInscripcion:
                    inscripcion = nota_relacionada.idInscripcion
                    if monto_pago >= nota.totalNota:
                        inscripcion.estadoPago = 'PAGADO'
                    else:
                        inscripcion.estadoPago = 'PARCIAL'
                    inscripcion.save()
                    print(f"✅ Inscripción actualizada: {inscripcion.idInscripcion}")
            except Exception as e:
                print(f"⚠️ No se pudo actualizar inscripción: {str(e)}")

            # 🔥 CORRECCIÓN: Crear detalles del asiento contable
            try:
                # Buscar cuentas contables para el tipo de artículo
                plan_articulo_debe = PlanArticulo.objects.filter(
                    tipoArticulo=nota.tipoArticulo,
                    tipo=1  # DEBE
                ).order_by('-fecha').first()
                
                plan_articulo_haber = PlanArticulo.objects.filter(
                    tipoArticulo=nota.tipoArticulo, 
                    tipo=0  # HABER
                ).order_by('-fecha').first()

                if plan_articulo_debe and plan_articulo_haber:
                    DetalleAsiento.objects.create(
                        idAsiento=asiento,
                        idPlanCuenta=plan_articulo_debe.idPlanCuenta,
                        debe=monto_pago,
                        haber=Decimal('0.00')
                    )
                    DetalleAsiento.objects.create(
                        idAsiento=asiento,
                        idPlanCuenta=plan_articulo_haber.idPlanCuenta,
                        debe=Decimal('0.00'),
                        haber=monto_pago
                    )
                    print(f"✅ Detalles de asiento creados")
                else:
                    print(f"⚠️ No se encontraron cuentas contables para {nota.tipoArticulo}")
            except Exception as e:
                print(f"⚠️ Error creando detalles de asiento: {str(e)}")

            # Respuesta exitosa
            response_data = {
                'success': True,
                'message': '¡Pago procesado exitosamente! 🎉',
                'data': {
                    'idPago': pago.idPago,
                    'numeroAsiento': asiento.numeroAsiento,  # Usar número de asiento como referencia
                    'monto': float(pago.monto),
                    'fechaPago': pago.fechaPago.isoformat(),
                    'formaPago': pago.formaPago,
                    'referencia': pago.referencia,
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

        except Exception as e:
            print(f"💥 Error en PagoCreateAPIView: {str(e)}")
            import traceback
            print(f"📋 Traceback: {traceback.format_exc()}")
            
            return Response({
                'success': False,
                'message': f'Error procesando pago: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def generar_numero_pago(self):
        # CORREGIDO: usar now() en lugar de timezone.now()
        fecha_actual = now().strftime('%Y%m%d')
        numero_unico = uuid.uuid4().hex[:6].upper()
        return f"PAGO-{fecha_actual}-{numero_unico}"
        
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



##########################API DE PAGO TEMPORAL APP ############################

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