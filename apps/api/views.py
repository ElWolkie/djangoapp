from rest_framework import generics
from apps.home.models import Personas, TipoPersona  # Importa el modelo desde home
from .serializers import PersonaSerializer

class PersonaListCreate(generics.ListCreateAPIView):
    queryset = Personas.objects.all()  # Usa el modelo de home
    serializer_class = PersonaSerializer

class PersonaListCreate(generics.ListCreateAPIView):
    queryset = TipoPersona.objects.all()  # Usa el modelo de home
    serializer_class = PersonaSerializer

class PersonaRetrieveUpdateDestroy(generics.RetrieveUpdateDestroyAPIView):
    queryset = Personas.objects.all()  # Usa el modelo de home
    serializer_class = PersonaSerializer