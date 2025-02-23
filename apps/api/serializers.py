from rest_framework import serializers
from apps.home.models import Personas, TipoPersona  # Importa el modelo desde home

class PersonaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Personas  # Usa el modelo de home
        fields = ['id', 'idTP', 'cedula', 'nombres', 'apellidos', 'telefono', 'correo', 'estadoPersona', 'fecha']

class TipoPersonaSerializer(serializers.ModelSerializer):
    class Meta:
        model = TipoPersona  # Usa el modelo de home
        fields = ['idTP', 'nombreTP', 'estadoTP', 'fechaTP']