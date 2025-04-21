from rest_framework import generics
from apps.home.models import Personas, Materia, Cohorte, Cargo, Requisito, Servicio, Tramite, Denominacion, Banco, Moneda, Tasa, TipoIngreso
from .serializers import PersonaSerializer, TipoPersonaSerializer, PersonaTPSerializer, MateriaSerializer, CohorteSerializer, CargoSerializer, HonorarioSerializer, RequisitoSerializer, ServicioSerializer, TramiteSerializer, SolicitudSerializer, DenominacionSerializer, BancoSerializer, MonedaSerializer, TasaSerializer, TipoIngresoSerializer  # Importa ambos serializadores
from apps.persona.models import PersonaTP, TipoPersona
from apps.honorario.models import Honorario
from apps.solicitud.models import Solicitud

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

# # Vista para Cuotas
# class CuotaListCreate(generics.ListCreateAPIView):
#     queryset = Cuota.objects.all()  # Usa el modelo Cuota
#     serializer_class = CuotaSerializer  # Usa el serializador CuotaSerializer

# # Vista para Ofertas
# class OfertasListCreate(generics.ListCreateAPIView):
#     queryset = Ofertas.objects.all()  # Usa el modelo Ofertas
#     serializer_class = OfertasSerializer  # Usa el serializador OfertasSerializer

# # Vista para TipoOferta
# class TipoOfertaListCreate(generics.ListCreateAPIView):
#     queryset = TipoOferta.objects.all()  # Usa el modelo TipoOferta
#     serializer_class = TipoOfertaSerializer  # Usa el serializador TipoOfertaSerializer

class MateriaListCreate(generics.ListCreateAPIView):
    queryset = Materia.objects.all()  # Usa el modelo Materia
    serializer_class = MateriaSerializer  # Usa el serializador MateriaSerializer

class CohorteListCreate(generics.ListCreateAPIView):
    queryset = Cohorte.objects.all()  # Usa el modelo Cohorte
    serializer_class = CohorteSerializer  # Usa el serializador CohorteSerializer

class CargoListCreate(generics.ListCreateAPIView):
    queryset = Cargo.objects.all()  # Usa el modelo Cargo
    serializer_class = CargoSerializer  # Usa el serializador CargoSerializer

# class ContratoListCreate(generics.ListCreateAPIView):
#     queryset = Contrato.objects.all()  # Usa el modelo Contrato
#     serializer_class = ContratoSerializer  # Usa el serializador ContratoSerializer

class HonorarioListCreate(generics.ListCreateAPIView):
    queryset = Honorario.objects.all()  # Usa el modelo Honorario
    serializer_class = HonorarioSerializer  # Usa el serializador HonorarioSerializer

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

class DenominacionListCreate(generics.ListCreateAPIView):
    queryset = Denominacion.objects.all()  # Usa el modelo Denominacion
    serializer_class = DenominacionSerializer  # Usa el serializador DenominacionSerializer

class BancoListCreate(generics.ListCreateAPIView):
    queryset = Banco.objects.all()  # Usa el modelo Banco
    serializer_class = BancoSerializer  # Usa el serializador BancoSerializer

class MonedaListCreate(generics.ListCreateAPIView):
    queryset = Moneda.objects.all()  # Usa el modelo Moneda
    serializer_class = MonedaSerializer  # Usa el serializador MonedaSerializer

class TasaListCreate(generics.ListCreateAPIView):
    queryset = Tasa.objects.all()  # Usa el modelo Tasa
    serializer_class = TasaSerializer  # Usa el serializador TasaSerializer

class TipoIngresoListCreate(generics.ListCreateAPIView):
    queryset = TipoIngreso.objects.all()  # Usa el modelo TipoIngreso
    serializer_class = TipoIngresoSerializer  # Usa el serializador TipoIngresoSerializer

# class TipoEgresoListCreate(generics.ListCreateAPIView):
#     queryset = TipoEgreso.objects.all()  # Usa el modelo TipoEgreso
#     serializer_class = TipoEgresoSerializer  # Usa el serializador TipoEgresoSerializer