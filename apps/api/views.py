from rest_framework import generics
from apps.home.models import Personas, TipoPersona, Cuota, Ofertas, TipoOferta, Materia, Cohorte, Cargo, Contrato, Honorario
from .serializers import PersonaSerializer, TipoPersonaSerializer, CuotaSerializer, OfertasSerializer, TipoOfertaSerializer, MateriaSerializer, CohorteSerializer, CargoSerializer, ContratoSerializer, HonorarioSerializer  # Importa ambos serializadores

# Vista para Personas
class PersonaListCreate(generics.ListCreateAPIView):
    queryset = Personas.objects.all()  # Usa el modelo Personas
    serializer_class = PersonaSerializer  # Usa el serializador PersonaSerializer

# Vista para TipoPersona
class TipoPersonaListCreate(generics.ListCreateAPIView):
    queryset = TipoPersona.objects.all()  # Usa el modelo TipoPersona
    serializer_class = TipoPersonaSerializer  # Usa el serializador TipoPersonaSerializer

# Vista para operaciones de detalle, actualización y eliminación de Personas
class PersonaRetrieveUpdateDestroy(generics.RetrieveUpdateDestroyAPIView):
    queryset = Personas.objects.all()  # Usa el modelo Personas
    serializer_class = PersonaSerializer  # Usa el serializador PersonaSerializer

# Vista para Cuotas
class CuotaListCreate(generics.ListCreateAPIView):
    queryset = Cuota.objects.all()  # Usa el modelo Cuota
    serializer_class = CuotaSerializer  # Usa el serializador CuotaSerializer

# Vista para Ofertas
class OfertasListCreate(generics.ListCreateAPIView):
    queryset = Ofertas.objects.all()  # Usa el modelo Ofertas
    serializer_class = OfertasSerializer  # Usa el serializador OfertasSerializer

# Vista para TipoOferta
class TipoOfertaListCreate(generics.ListCreateAPIView):
    queryset = TipoOferta.objects.all()  # Usa el modelo TipoOferta
    serializer_class = TipoOfertaSerializer  # Usa el serializador TipoOfertaSerializer

class MateriaListCreate(generics.ListCreateAPIView):
    queryset = Materia.objects.all()  # Usa el modelo Materia
    serializer_class = MateriaSerializer  # Usa el serializador MateriaSerializer

class CohorteListCreate(generics.ListCreateAPIView):
    queryset = Cohorte.objects.all()  # Usa el modelo Cohorte
    serializer_class = CohorteSerializer  # Usa el serializador CohorteSerializer

class CargoListCreate(generics.ListCreateAPIView):
    queryset = Cargo.objects.all()  # Usa el modelo Cargo
    serializer_class = CargoSerializer  # Usa el serializador CargoSerializer

class ContratoListCreate(generics.ListCreateAPIView):
    queryset = Contrato.objects.all()  # Usa el modelo Contrato
    serializer_class = ContratoSerializer  # Usa el serializador ContratoSerializer

class HonorarioListCreate(generics.ListCreateAPIView):
    queryset = Honorario.objects.all()  # Usa el modelo Honorario
    serializer_class = HonorarioSerializer  # Usa el serializador HonorarioSerializer