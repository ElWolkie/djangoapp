from rest_framework import serializers
from apps.home.models import Personas, TipoPersona, Cuota, Ofertas, TipoOferta, Materia, Cohorte, Cargo, Contrato, Honorario  # Importa el modelo desde home

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

class MateriaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Materia  # Usa el modelo de home
        fields = ['idMateria', 'idOferta', 'nombreMateria', 'estadoMateria', 'fechaMateria']

class CohorteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Cohorte  # Usa el modelo de home
        fields = ['idCohorte', 'nombreCohorte', 'estadoCohorte', 'fechaCohorte']

class CargoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Cargo  # Usa el modelo de home
        fields = ['idCargo', 'nombreCargo', 'estadoCargo', 'fechaCargo']

class ContratoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Contrato  # Usa el modelo de home
        fields = ['idContrato', 'idPersona', 'idCargo', 'idCohorte', 'idMateria', 'estadoContrato', 'fechaContrato']

class HonorarioSerializer(serializers.ModelSerializer):
    class Meta:
        model = Honorario  # Usa el modelo de home
        fields = ['idHonorario', 'idContrato', 'horas', 'estadoHonorario', 'fechaHonorario']