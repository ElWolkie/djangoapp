# apps/persona/serializers.py
from rest_framework import serializers
from .models import Personas, TipoPersona, PersonaTP
from apps.home.models import Usuarios
from django.contrib.auth.models import Group, Permission
from django.db import transaction

import logging

logger = logging.getLogger(__name__)

class PersonaCreateSerializer(serializers.Serializer):
    tipo_cedula = serializers.ChoiceField(choices=['V', 'E', 'P'], required=True, write_only=True)
    numero_cedula = serializers.CharField(max_length=20, required=True, write_only=True)
    nombres = serializers.CharField(max_length=100, required=True)
    apellidos = serializers.CharField(max_length=100, required=True)
    telefono = serializers.CharField(max_length=20, required=True)
    direccion = serializers.CharField(required=False, allow_blank=True)
    email = serializers.EmailField(required=False, allow_blank=True)  # Cambiado de 'correo' a 'email'
    rif = serializers.CharField(max_length=20, required=False, allow_blank=True)
    id = serializers.IntegerField(read_only=True, source='idPersona')
    cedula = serializers.CharField(read_only=True)
    estadoPersona = serializers.CharField(read_only=True)

    def validate_numero_cedula(self, value):
        if not value.isdigit():
            raise serializers.ValidationError("El número de cédula solo debe contener dígitos.")
        return value

    def validate(self, data):
        cedula_completa = f"{data['tipo_cedula']}-{data['numero_cedula']}"
        if Personas.objects.filter(cedula=cedula_completa).exists():
            raise serializers.ValidationError({
                "error": f"La cédula {cedula_completa} ya está registrada.",
                "codigo": "CEDULA_DUPLICADA"
            })
        return data

    def create(self, validated_data):
        """
        Crea la persona - IMPORTANTE: Ahora usa 'email' en lugar de 'correo'
        """
        cedula_completa = f"{validated_data['tipo_cedula']}-{validated_data['numero_cedula']}"
        
        # Mapeo CORRECTO de campos
        persona_data = {
            'cedula': cedula_completa,
            'nombres': validated_data['nombres'],
            'apellidos': validated_data['apellidos'],
            'telefono': validated_data['telefono'],
            'correo': validated_data.get('email', ''),  # ¡IMPORTANTE! 'email' del frontend -> 'correo' en BD
            'rif': validated_data.get('rif', ''),
            'estadoPersona': 'ACTIVO'
        }
        
        # Solo agregar dirección si existe en el modelo
        if hasattr(Personas, 'direccion') and 'direccion' in validated_data:
            persona_data['direccion'] = validated_data['direccion']
        
        try:
            persona = Personas.objects.create(**persona_data)
            logger.info(f"✅ Persona creada en BD - ID: {persona.idPersona} - Cédula: {persona.cedula}")

            # Asignar tipos automáticamente
            tipo_cliente, _ = TipoPersona.objects.get_or_create(
                nombreTP='Cliente',
                defaults={'estadoTP': 'ACTIVO'}
            )

            tipo_usuario, _ = TipoPersona.objects.get_or_create(
                nombreTP='Usuario',
                defaults={'estadoTP': 'ACTIVO'}
            )

            PersonaTP.objects.create(idPersona=persona, idTP=tipo_cliente)
            PersonaTP.objects.create(idPersona=persona, idTP=tipo_usuario)

            logger.info(f"✅ Tipos asignados a {persona.cedula}")
            return persona
            
        except Exception as e:
            logger.error(f"❌ Error al crear persona: {str(e)}")
            raise


class UsuarioCreateSerializer(serializers.Serializer):
    """
    Serializer para crear una nueva cuenta de Usuario para una Persona existente.
    La cédula debe enviarse en formato: 'V-12345678' (incluye guion).
    """
    cedula = serializers.CharField(max_length=25, write_only=True, help_text="Cédula completa, ej: V-12345678")
    password = serializers.CharField(write_only=True, style={'input_type': 'password'})
    preguntaSeguridad = serializers.CharField(max_length=255)
    respuestaSeguridad = serializers.CharField(max_length=255)

    def _normalize_cedula_input(self, raw: str) -> str:
        """
        Normaliza la entrada:
        - quita espacios
        - convierte a mayúsculas
        - si falta el guion entre tipo y número, lo añade
        - si recibieron sólo dígitos intenta no modificar (se manejará en la búsqueda)
        """
        if not raw:
            return ''

        s = str(raw).upper().strip()
        s = s.replace(' ', '')

        # Si tiene guion, respetarlo (pero normalizar)
        if '-' in s:
            parts = s.split('-', 1)
            return f"{parts[0]}-{parts[1]}"
        # Si empieza con letra seguida de dígitos, añadir guion
        if len(s) >= 2 and s[0].isalpha() and s[1:].isdigit():
            return f"{s[0]}-{s[1:]}"
        # si solo son dígitos, devolverlos (la búsqueda probará prefijos)
        return s

    def validate_cedula(self, value):
        raw_norm = self._normalize_cedula_input(value)
        logger.debug(f"🔎 Validando cédula (raw): '{value}' -> normalizada: '{raw_norm}'")

        persona = None

        # 1) Si la normalizada tiene formato T-NNN..., buscar exacto primero
        if '-' in raw_norm:
            try:
                persona = Personas.objects.get(cedula=raw_norm)
            except Personas.DoesNotExist:
                persona = None
        # 2) Si no la encontramos, si raw_norm son sólo dígitos o no exacto, probar con prefijos comunes
        if persona is None:
            digits = raw_norm.replace('-', '')  # elimina guion por si acaso
            if digits.isdigit():
                for pref in ('V', 'E', 'P'):
                    try:
                        persona = Personas.objects.get(cedula=f"{pref}-{digits}")
                        break
                    except Personas.DoesNotExist:
                        continue
                # si todavía no se encuentra, intentar buscar por sufijo (casos edge)
                if persona is None:
                    posibles = Personas.objects.filter(cedula__endswith=digits)
                    if posibles.exists():
                        persona = posibles.first()
            else:
                # no son sólo dígitos y no tienen guion: buscar por coincidencia (tolerante)
                try:
                    persona = Personas.objects.get(cedula__iexact=raw_norm)
                except Personas.DoesNotExist:
                    persona = None

        if persona is None:
            raise serializers.ValidationError("La cédula indicada no corresponde a ninguna persona registrada.")

        # 2. Comprobar que la persona NO tenga ya un usuario
        if Usuarios.objects.filter(idPersona=persona).exists():
            raise serializers.ValidationError("Esta persona ya tiene una cuenta de usuario asociada.")

        # 3. Comprobar que la persona tenga el tipo 'Usuario' asignado (singular)
        if not persona.personatp_set.filter(idTP__nombreTP='Usuario').exists():
            raise serializers.ValidationError("Esta persona no tiene permisos para crear una cuenta de usuario.")

        # Guardamos el objeto persona en el contexto para create()
        self.context['persona_obj'] = persona
        return value

    def create(self, validated_data):
        persona_obj = self.context.get('persona_obj')
        if persona_obj is None:
            raise serializers.ValidationError("No se encontró la persona asociada para crear el usuario.")

        try:
            with transaction.atomic():
                # Crear usuario (intentamos pasar idPersona como entero)
                try:
                    user = Usuarios.objects.create_user(
                        idPersona=persona_obj.idPersona,
                        password=validated_data['password'],
                        preguntaSeguridad=validated_data['preguntaSeguridad'],
                        respuestaSeguridad=validated_data['respuestaSeguridad']
                    )
                except TypeError:
                    # fallback si la firma usa idPersona_id u otro nombre
                    user = Usuarios.objects.create_user(
                        idPersona_id=persona_obj.idPersona,
                        password=validated_data['password'],
                        preguntaSeguridad=validated_data['preguntaSeguridad'],
                        respuestaSeguridad=validated_data['respuestaSeguridad']
                    )

                logger.info(f"✅ Usuario creado exitosamente para la persona: {persona_obj.cedula} (idUsuario={getattr(user, 'idUsuario', None)})")

                # --- ASIGNAR SOLO GRUPOS EXISTENTES (NO CREAR) ---
                nombres_grupos = ['Clientes-Proveedores', 'Inscripciones']  # ajusta si necesitas otros nombres

                for nombre in nombres_grupos:
                    try:
                        grupo = Group.objects.get(name=nombre)
                    except Group.DoesNotExist:
                        logger.warning(f"⚠️ Grupo '{nombre}' no existe — se omite la asignación a ese grupo.")
                        continue

                    # No modificamos los permisos del grupo aquí — solo añadimos el usuario al grupo existing
                    user.groups.add(grupo)
                    logger.info(f"🔐 Usuario añadido al grupo existente: '{nombre}'")

                user.save()
                return user

        except Exception as e:
            logger.exception("Error creando usuario y asignando grupos existentes.")
            raise serializers.ValidationError(f"No se pudo crear el usuario: {e}")



