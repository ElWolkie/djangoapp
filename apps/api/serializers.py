from rest_framework import serializers
from apps.home.models import Personas, TipoPersona  # Importa el modelo desde home

class PersonaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Personas  # Usa el modelo de home
        fields = '__all__'

class TipoPersonaSerializer(serializers.ModelSerializer):
    class Meta:
        model = TipoPersona  # Usa el modelo de home
        fields = '__all__'