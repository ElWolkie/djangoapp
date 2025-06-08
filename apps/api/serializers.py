from rest_framework import serializers
from apps.home.models import Personas, Materia, Cohorte, Cargo, Requisito, Servicio, Tramite, Denominacion, Banco, Moneda, Tasa, TipoIngreso
from apps.persona.models import PersonaTP, TipoPersona
from apps.honorario.models import Honorario
from apps.solicitud.models import Solicitud

class PersonaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Personas  # Usa el modelo de home
        fields = ['idPersona', 'cedula', 'nombres', 'apellidos', 'telefono', 'correo', 'estadoPersona', 'fechaPersona']

class TipoPersonaSerializer(serializers.ModelSerializer):
    class Meta:
        model = TipoPersona  # Usa el modelo de home
        fields = ['idTP', 'nombreTP', 'estadoTP', 'fechaTP']

class PersonaTPSerializer(serializers.ModelSerializer):
    class Meta:
        model = PersonaTP  # Usa el modelo de home
        fields = ['idPersona', 'idTP', 'fechaAsignacion']

# class CuotaSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = Cuota  # Usa el modelo de home
#         fields = ['idCuota', 'nombreCuota', 'estadoCuota', 'fechaCuota']

# class OfertasSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = Ofertas  # Usa el modelo de home
#         fields = ['idOferta', 'idTipoOferta', 'nombreOferta', 'duracion', 'estadoOferta', 'fechaOferta']

# class TipoOfertaSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = TipoOferta  # Usa el modelo de home
#         fields = ['idTipoOferta', 'idCuota', 'nombreTipoOferta', 'estadoTipoOferta', 'fechaTipoOferta']

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

# class ContratoSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = Contrato  # Usa el modelo de home
#         fields = ['idContrato', 'idPersona', 'idCargo', 'idCohorte', 'idMateria', 'estadoContrato', 'fechaContrato']

class HonorarioSerializer(serializers.ModelSerializer):
    class Meta:
        model = Honorario  # Usa el modelo de home
        fields = ['idHonorario', 'idContrato', 'horas', 'estadoHonorario', 'fechaHonorario']

class RequisitoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Requisito  # Usa el modelo de home
        fields = ['idRequisito', 'nombreRequisito', 'estadoRequisito', 'fechaRequisito']

class ServicioSerializer(serializers.ModelSerializer):
    class Meta:
        model = Servicio  # Usa el modelo de home
        fields = ['idServicio', 'nombreServicio', 'tiempoServicio', 'precioServicio', 'estadoServicio', 'fechaServicio']

class TramiteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tramite  # Usa el modelo de home
        fields = ['idTramite', 'nombreTramite', 'diasTramite', 'precioTramite', 'estadoTramite', 'fechaTramite']

class SolicitudSerializer(serializers.ModelSerializer):
    class Meta:
        model = Solicitud  # Usa el modelo de home
        fields = ['idSoli', 'idPersona', 'idTramite', 'idServicio', 'montoTotal', 'estadoSolicitud', 'fechaEntrega', 'fechaSolicitud']

class DenominacionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Denominacion  # Usa el modelo de home
        fields = ['idDenominacion', 'nombreDenominacion', 'estadoDenominacion', 'fechaDenominacion']

class BancoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Banco  # Usa el modelo de home
        fields = ['idBanco', 'nombreBanco', 'codBanco', 'codContable', 'estadoBanco', 'fechaBanco']

class MonedaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Moneda  # Usa el modelo de home
        fields = ['idMoneda', 'nombreMoneda', 'simboloMoneda', 'estadoMoneda', 'fechaMoneda']

class TasaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tasa  # Usa el modelo de home
        fields = ['idTasa', 'idMoneda', 'montoTasa', 'estadoTasa', 'fechaTasa']

class TipoIngresoSerializer(serializers.ModelSerializer):
    class Meta:
        model = TipoIngreso  # Usa el modelo de home
        fields = ['idTipoIngreso', 'nombreTipoIngreso', 'estadoTipoIngreso', 'fechaTipoIngreso']

# class TipoEgresoSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = TipoEgreso  # Usa el modelo de home
#         fields = ['idTipoEgreso', 'nombreTipoEgreso', 'estadoTipoEgreso', 'fechaTipoEgreso']