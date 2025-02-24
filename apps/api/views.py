from rest_framework import generics
from apps.home.models import Personas, TipoPersona, Cuota, Ofertas, TipoOferta
from .serializers import PersonaSerializer, TipoPersonaSerializer, CuotaSerializer, OfertasSerializer, TipoOfertaSerializer  # Importa ambos serializadores

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
    queryset = Cuota.objects.all()  # Usa el modelo Personas
    serializer_class = CuotaSerializer  # Usa el serializador PersonaSerializer

# Vista para Ofertas
class OfertasListCreate(generics.ListCreateAPIView):
    queryset = Ofertas.objects.all()  # Usa el modelo Personas
    serializer_class = OfertasSerializer  # Usa el serializador PersonaSerializer

# Vista para TipoOferta
class TipoOfertaListCreate(generics.ListCreateAPIView):
    queryset = TipoOferta.objects.all()  # Usa el modelo Personas
    serializer_class = TipoOfertaSerializer  # Usa el serializador PersonaSerializer