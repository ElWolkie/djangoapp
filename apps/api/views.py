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
            print("📥 Datos recibidos:", request.data)
            
            data = request.data.copy()
            
            # Asegurarnos de que los IDs sean enteros
            for field in ['idPersona', 'idTF', 'idFormacion', 'idCohorte']:
                if field in data:
                    try:
                        data[field] = int(data[field])
                    except (ValueError, TypeError):
                        return Response(
                            {"error": f"El campo {field} debe ser un número entero válido"},
                            status=status.HTTP_400_BAD_REQUEST
                        )
            
            # Si idPersona no viene, usar el del usuario autenticado
            if 'idPersona' not in data and hasattr(request.user, 'idPersona'):
                data['idPersona'] = request.user.idPersona.idPersona
            
            # Validar que existan las referencias
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
                return Response(
                    {"error": f"Referencia no encontrada: {str(e)}"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            serializer = self.get_serializer(data=data)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            
            print("✅ Inscripción creada exitosamente:", serializer.data)
            headers = self.get_success_headers(serializer.data)
            return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
            
        except serializers.ValidationError as e:
            print("❌ Error de validación:", e.detail)
            return Response(
                {"error": "Error de validación", "details": e.detail},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            print("❌ Error al crear inscripción:", str(e))
            print("📋 Datos que causaron el error:", request.data)
            return Response(
                {"error": str(e), "details": "Error interno del servidor"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

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
