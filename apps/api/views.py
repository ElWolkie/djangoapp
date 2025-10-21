import traceback
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework.permissions import AllowAny
from django.db.models import Sum
from apps.home.models import Personas, Materia, Cohorte, Cargo, Requisito, Servicio, Tramite, Moneda, Tasa, Formacion, TipoFormacion, Usuarios, CuotaFormacion
from .serializers import PagoSerializer, PersonaSerializer, CedulaTokenObtainSerializer, TipoPersonaSerializer, PersonaTPSerializer, FormacionSerializer, TPFormacionSerializer, MateriaSerializer, CohorteSerializer, CargoSerializer, HonorarioSerializer, InscripcionSerializer, RequisitoSerializer, ServicioSerializer, TramiteSerializer, SolicitudSerializer, MonedaSerializer, TasaSerializer, UsuarioSerializer, AsientoContableSerializer, PlanCuentaSerializer, PeriodoContableSerializer, CuotaFormacionSerializer  # Importa ambos serializadores
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
        'idFormacion',
        'idCohorte',
        'idCohorte__idFormacion'   # <- importante para que CohorteSerializer.idFormacion no haga consultas extra
    ).all().prefetch_related('inscripcioncuota_set')
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
