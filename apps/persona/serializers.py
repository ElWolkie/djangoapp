# apps/persona/serializers.py

from rest_framework import serializers
from .models import Personas, TipoPersona, PersonaTP
import logging

logger = logging.getLogger(__name__)

class PersonaCreateSerializer(serializers.Serializer):
    # Se usarán para la validación y creación, pero no se incluirán en la respuesta.
    tipo_cedula = serializers.ChoiceField(choices=['V', 'E', 'P'], required=True, write_only=True)
    numero_cedula = serializers.CharField(max_length=20, required=True, write_only=True)
    
    # Estos campos se aceptan en la entrada y se devuelven en la salida
    nombres = serializers.CharField(max_length=100, required=True)
    apellidos = serializers.CharField(max_length=100, required=True)
    telefono = serializers.CharField(max_length=20, required=True)
    direccion = serializers.CharField(required=True)
    email = serializers.EmailField(required=False, allow_blank=True, source='correo')
    rif = serializers.CharField(max_length=20, required=False, allow_blank=True)

    # Estos campos son de solo lectura, solo aparecerán en la respuesta
    id = serializers.IntegerField(read_only=True, source='idPersona')
    cedula = serializers.CharField(read_only=True) # Este campo sí existe en el modelo y lo mostraremos
    estadoPersona = serializers.CharField(read_only=True)

    def validate_numero_cedula(self, value):
        # ... (sin cambios aquí)
        if not value.isdigit():
            raise serializers.ValidationError("El número de cédula solo debe contener dígitos.")
        return value

    def validate(self, data):
        # ... (sin cambios aquí)
        cedula_completa = f"{data['tipo_cedula']}{data['numero_cedula']}"
        if Personas.objects.filter(cedula=cedula_completa).exists():
            raise serializers.ValidationError({
                "error": f"La cédula {cedula_completa} ya está registrada.",
                "codigo": "CEDULA_DUPLICADA"
            })
        return data

    def create(self, validated_data):
        # ... (sin cambios aquí)
        cedula_completa = f"{validated_data['tipo_cedula']}{validated_data['numero_cedula']}"
        persona = Personas.objects.create(
            cedula=cedula_completa,
            nombres=validated_data['nombres'],
            apellidos=validated_data['apellidos'],
            telefono=validated_data['telefono'],
            correo=validated_data.get('correo', ''),
            rif=validated_data.get('rif', ''),
            direccion=validated_data['direccion'],
            estadoPersona='ACTIVO'
        )
        logger.info(f"✅ Persona creada en BD - ID: {persona.idPersona}")
        # ... (resto de la lógica para asignar tipos de persona)
        try:
            tipo_cliente = TipoPersona.objects.get(nombreTP='Cliente')
            tipo_usuarios = TipoPersona.objects.get(nombreTP='Usuarios')
            PersonaTP.objects.create(idPersona=persona, idTP=tipo_cliente)
            PersonaTP.objects.create(idPersona=persona, idTP=tipo_usuarios)
            logger.info(f"✅ Tipos de persona asignados a {persona.cedula}: Cliente y Usuarios")
        except TipoPersona.DoesNotExist as e:
            logger.error(f"❌ Error crítico: Tipos de persona 'Cliente' o 'Usuarios' no encontrados en la BD: {e}")
        
        return persona