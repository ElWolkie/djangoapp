import traceback
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework.permissions import AllowAny
from django.db.models import Sum
from apps.home.models import Personas, Materia, Cohorte, Cargo, Requisito, Servicio, Tramite, Moneda, Tasa, Formacion, TipoFormacion, Usuarios
from .serializers import PersonaSerializer, CedulaTokenObtainSerializer, TipoPersonaSerializer, PersonaTPSerializer, FormacionSerializer, TPFormacionSerializer, MateriaSerializer, CohorteSerializer, CargoSerializer, HonorarioSerializer, InscripcionSerializer, RequisitoSerializer, ServicioSerializer, TramiteSerializer, SolicitudSerializer, MonedaSerializer, TasaSerializer, UsuarioSerializer, AsientoContableSerializer, PlanCuentaSerializer, PeriodoContableSerializer  # Importa ambos serializadores
from apps.persona.models import PersonaTP, TipoPersona
from apps.honorario.models import Honorario
from apps.inscripcion.models import Inscripcion
from apps.solicitud.models import Solicitud
from apps.asientoContable.models import AsientoContable, DetalleAsiento
from apps.planCuenta.models import PlanCuenta
from apps.periodoContable.models import periodoContable

from rest_framework import status
from django.db import transaction
from django.utils.timezone import now
from decimal import Decimal
import uuid

from apps.factura.models import Nota, Pago, NotaRelacionada, PlanArticulo
from apps.home.models import Moneda, Tasa, Configuracion
from .serializers import PagoCreateSerializer

from apps.api import serializers

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

# Vista para Formacion
class FormacionListCreate(generics.ListCreateAPIView):
    queryset = Formacion.objects.all()  # Usa el modelo Formacion
    serializer_class = FormacionSerializer  # Usa el serializador Formacion

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

class InscripcionListCreate(generics.ListCreateAPIView):
    queryset = Inscripcion.objects.select_related('idPersona','idFormacion','idCohorte').all().prefetch_related('inscripcioncuota_set')
    serializer_class = InscripcionSerializer

    def create(self, request, *args, **kwargs):
        try:
            print("=" * 50)
            print("📥 INICIANDO CREACIÓN DE INSCRIPCIÓN")
            print("📥 Datos recibidos:", request.data)
            
            data = request.data.copy()
            
            # Asegurarnos de que los IDs sean enteros - USAR LOS NOMBRES DIRECTOS
            for field in ['idPersona', 'idTF', 'idFormacion', 'idCohorte']:
                if field in data:
                    try:
                        data[field] = int(data[field])
                        print(f"✅ Campo {field} convertido a entero: {data[field]}")
                    except (ValueError, TypeError) as conv_error:
                        print(f"❌ Error convirtiendo {field}: {conv_error}")
                        return Response(
                            {"error": f"El campo {field} debe ser un número entero válido"},
                            status=status.HTTP_400_BAD_REQUEST
                        )
            
            # Si idPersona no viene, usar el del usuario autenticado
            if 'idPersona' not in data and hasattr(request.user, 'idPersona'):
                data['idPersona'] = request.user.idPersona.idPersona
            
            # Validar que existan las referencias - USAR LOS NOMBRES DIRECTOS
            try:
                if 'idPersona' in data:
                    Personas.objects.get(idPersona=data['idPersona'])
                if 'idTF' in data:
                    TipoFormacion.objects.get(idTF=data['idTF'])
                if 'idFormacion' in data:
                    Formacion.objects.get(idFormacion=data['idFormacion'])
                if 'idCohorte' in data:
                    Cohorte.objects.get(idCohorte=data['idCohorte'])
            except (Personas.DoesNotExist, TipoFormacion.DoesNotExist, 
                    Formacion.DoesNotExist, Cohorte.DoesNotExist) as e:
                print(f"❌ Referencia no encontrada: {str(e)}")
                return Response(
                    {"error": f"Referencia no encontrada: {str(e)}"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            print("🔍 Creando serializer...")
            serializer = self.get_serializer(data=data)
            
            print("🔍 Validando serializer...")
            if not serializer.is_valid():
                print("❌ ERRORES DE VALIDACIÓN DEL SERIALIZER:")
                for field, errors in serializer.errors.items():
                    print(f"   {field}: {errors}")
                return Response(
                    {"error": "Error de validación", "details": serializer.errors},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            print("🔍 Ejecutando perform_create...")
            self.perform_create(serializer)
            
            print("✅ Inscripción creada exitosamente:", serializer.data)
            headers = self.get_success_headers(serializer.data)
            return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
            
        except Exception as e:
            print("❌ ERROR NO CONTROLADO al crear inscripción:")
            print(f"   Tipo: {type(e).__name__}")
            print(f"   Mensaje: {str(e)}")
            import traceback
            print(f"   Traceback: {traceback.format_exc()}")
            print("📋 Datos que causaron el error:", request.data)
            return Response(
                {"error": str(e), "details": "Error interno del servidor"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class PagoCreateAPIView(APIView):
    @transaction.atomic
    def post(self, request):
        print("🚀 [PAGO-VIEW] Iniciando procesamiento...")
        
        try:
            # Usar el serializer para validación
            serializer = PagoCreateSerializer(data=request.data, context={'request': request})
            
            if not serializer.is_valid():
                print(f"❌ Validación falló: {serializer.errors}")
                return Response({
                    'success': False,
                    'message': 'Datos inválidos',
                    'errors': serializer.errors
                }, status=status.HTTP_400_BAD_REQUEST)

            print("✅ Serializer válido")
            
            # Obtener datos validados
            validated_data = serializer.validated_data
            nota = serializer.context['nota']
            monto_pago = validated_data['monto']

            print(f"📥 Procesando nota ID: {nota.idNota}, Monto: {monto_pago}")

            # 🔥 MONEDA FIJA ID=1 - como solicitaste
            moneda_base = Moneda.objects.filter(idMoneda=1).first()
            if not moneda_base:
                return Response({
                    'success': False,
                    'message': 'Moneda base (ID=1) no configurada'
                }, status=status.HTTP_400_BAD_REQUEST)

            print(f"✅ Moneda base: {moneda_base.nombreMoneda}")

            # Obtener tasa más reciente para la moneda base
            tasa = Tasa.objects.filter(idMoneda=moneda_base).order_by('-idTasa').first()
            if not tasa:
                return Response({
                    'success': False,
                    'message': f'No se encontró tasa para la moneda base ({moneda_base.nombreMoneda})'
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

            # Crear asiento contable
            numero_asiento = f"PAGO-{now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
            
            asiento = AsientoContable.objects.create(
                numeroAsiento=numero_asiento,
                fechaAsiento=now().date(),
                conceptoAsiento=f"Pago de {validated_data['formaPago']} - Nota: {nota.numeroNota}",
                idPeriodo=periodo_activo
            )
            print(f"✅ Asiento contable creado: {asiento.idAsiento}")

            # Crear pago
            pago = Pago.objects.create(
                idNota=nota,
                idAsiento=asiento,
                idTasa=tasa,
                monto=monto_pago,
                fechaPago=validated_data['fechaPago'],
                formaPago=validated_data['formaPago'],
                referencia=validated_data.get('referencia', ''),
                observaciones=validated_data.get('observaciones', '')
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

            # Crear detalles del asiento contable (opcional)
            try:
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
            except Exception as e:
                print(f"⚠️ Error creando detalles de asiento: {str(e)}")

            # Respuesta exitosa
            response_data = {
                'success': True,
                'message': '¡Pago procesado exitosamente! 🎉',
                'data': {
                    'idPago': pago.idPago,
                    'numeroAsiento': asiento.numeroAsiento,
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
