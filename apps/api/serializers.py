from rest_framework import serializers
from apps.home.models import Personas, TipoPersona, Cuota, Ofertas, TipoOferta  # Importa el modelo desde home

class PersonaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Personas  # Usa el modelo de home
        fields = ['idPersona', 'idTP', 'cedula', 'nombres', 'apellidos', 'telefono', 'correo', 'estadoPersona', 'fechaPersona']

class TipoPersonaSerializer(serializers.ModelSerializer):
    class Meta:
        model = TipoPersona  # Usa el modelo de home
        fields = ['idTP', 'nombreTP', 'estadoTP', 'fechaTP']

class CuotaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Cuota  # Usa el modelo de home
        fields = ['idCuota', 'nombreCuota', 'estadoCuota', 'fechaCuota']

class OfertasSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ofertas  # Usa el modelo de home
        fields = ['idOferta', 'idTipoOferta', 'nombreOferta', 'duracion', 'estadoOferta', 'fechaOferta']

class TipoOfertaSerializer(serializers.ModelSerializer):
    class Meta:
        model = TipoOferta  # Usa el modelo de home
        fields = ['idTipoOferta', 'idCuota', 'nombreTipoOferta', 'estadoTipoOferta', 'fechaTipoOferta'] 