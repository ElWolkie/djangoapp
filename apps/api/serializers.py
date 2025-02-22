from rest_framework import serializers
from apps.home.models import Personas  # Importa el modelo desde home

class PersonaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Personas  # Usa el modelo de home
        fields = '__all__'