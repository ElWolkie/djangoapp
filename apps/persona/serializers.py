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
    correo = serializers.EmailField(required=False, allow_blank=True)
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
        
        # ✅ NUEVA VALIDACIÓN: Para tipo V, RIF es requerido
        if data['tipo_cedula'] == 'V' and (not data.get('rif') or data.get('rif') == ''):
            raise serializers.ValidationError({
                "error": "El RIF es obligatorio para cédula venezolana (V).",
                "codigo": "RIF_REQUERIDO"
            })
        
        return data

    def create(self, validated_data):
        cedula_completa = f"{validated_data['tipo_cedula']}-{validated_data['numero_cedula']}"
        
        # ✅ SOLUCIÓN DEFINITIVA: Manejo inteligente de RIF
        rif = validated_data.get('rif', '')
        
        # Para tipos E y P, RIF debe ser NULL en la base de datos
        if validated_data['tipo_cedula'] in ['E', 'P']:
            rif = None  # Esto evita el problema de unique constraint
        # Para tipo V, usar el RIF proporcionado (ya validado que no está vacío)
        elif validated_data['tipo_cedula'] == 'V' and rif == '':
            # Generar RIF automáticamente si no se proporcionó
            rif = self._generar_rif_automatico(validated_data['tipo_cedula'], validated_data['numero_cedula'])
        
        persona_data = {
            'cedula': cedula_completa,
            'nombres': validated_data['nombres'],
            'apellidos': validated_data['apellidos'],
            'telefono': validated_data['telefono'],
            'correo': validated_data.get('correo', ''),
            'rif': rif,  # ✅ Ahora es None para E/P, evitando duplicados
            'estadoPersona': 'ACTIVO'
        }
        
        if hasattr(Personas, 'direccion') and 'direccion' in validated_data:
            persona_data['direccion'] = validated_data['direccion']
        
        try:
            persona = Personas.objects.create(**persona_data)
            logger.info(f"✅ Persona creada en BD - ID: {persona.idPersona} - Cédula: {persona.cedula} - RIF: {persona.rif}")

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
            # Manejo específico de error de RIF duplicado
            if 'persona_personas_rif_key' in str(e):
                raise serializers.ValidationError({
                    "error": "Ya existe un registro con RIF vacío en el sistema. Contacte al administrador.",
                    "codigo": "RIF_DUPLICADO"
                })
            raise

    def _generar_rif_automatico(self, tipo_cedula, numero_cedula):
        """Genera RIF automático para tipo V si no se proporciona"""
        # Lógica para generar RIF (puedes adaptar tu función existente)
        tipo_mapeo = {'V': 1, 'E': 2, 'J': 3, 'P': 4, 'G': 5}
        letra = tipo_cedula.upper()
        nums = numero_cedula.zfill(8)[-8:]  # Rellena con ceros a la izquierda
        
        # Cálculo del dígito verificador (puedes usar tu función existente)
        base_numerico = f"{tipo_mapeo[letra]}{nums}"
        multiplicadores = [4, 3, 2, 7, 6, 5, 4, 3, 2]
        suma = sum(int(base_numerico[i]) * multiplicadores[i] for i in range(len(multiplicadores)))
        resto = suma % 11
        digito = 11 - resto
        digito = 0 if digito in [10, 11] else digito
        
        return f"{letra}-{nums}-{digito}"


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
        if not raw:
            return ''
        s = str(raw).upper().strip().replace(' ', '')
        if '-' in s:
            parts = s.split('-', 1)
            return f"{parts[0]}-{parts[1]}"
        if len(s) >= 2 and s[0].isalpha() and s[1:].isdigit():
            return f"{s[0]}-{s[1:]}"
        return s

    def validate_cedula(self, value):
        raw_norm = self._normalize_cedula_input(value)
        logger.debug(f"🔎 Validando cédula (raw): '{value}' -> normalizada: '{raw_norm}'")

        persona = None
        if '-' in raw_norm:
            try:
                persona = Personas.objects.get(cedula=raw_norm)
            except Personas.DoesNotExist:
                persona = None

        if persona is None:
            digits = raw_norm.replace('-', '')
            if digits.isdigit():
                for pref in ('V', 'E', 'P'):
                    try:
                        persona = Personas.objects.get(cedula=f"{pref}-{digits}")
                        break
                    except Personas.DoesNotExist:
                        continue
                if persona is None:
                    posibles = Personas.objects.filter(cedula__endswith=digits)
                    if posibles.exists():
                        persona = posibles.first()
            else:
                try:
                    persona = Personas.objects.get(cedula__iexact=raw_norm)
                except Personas.DoesNotExist:
                    persona = None

        if persona is None:
            raise serializers.ValidationError("La cédula indicada no corresponde a ninguna persona registrada.")

        # Verificar que NO exista usuario
        if Usuarios.objects.filter(idPersona=persona).exists():
            raise serializers.ValidationError("Esta persona ya tiene una cuenta de usuario asociada.")

        # Verificar que la persona tenga tipo 'Usuario'
        if not persona.personatp_set.filter(idTP__nombreTP='Usuario').exists():
            raise serializers.ValidationError("Esta persona no tiene permisos para crear una cuenta de usuario.")

        self.context['persona_obj'] = persona
        return value

    def create(self, validated_data):
        persona_obj = self.context.get('persona_obj')
        if persona_obj is None:
            raise serializers.ValidationError("No se encontró la persona asociada para crear el usuario.")

        try:
            with transaction.atomic():
                try:
                    user = Usuarios.objects.create_user(
                        idPersona=persona_obj.idPersona,
                        password=validated_data['password'],
                        preguntaSeguridad=validated_data['preguntaSeguridad'],
                        respuestaSeguridad=validated_data['respuestaSeguridad'],
                        coloresUsuario='UsuariosApp'
                    )
                except TypeError:
                    user = Usuarios.objects.create_user(
                        idPersona_id=persona_obj.idPersona,
                        password=validated_data['password'],
                        preguntaSeguridad=validated_data['preguntaSeguridad'],
                        respuestaSeguridad=validated_data['respuestaSeguridad'],
                        coloresUsuario='UsuariosApp'
                    )

                logger.info(f"✅ Usuario creado exitosamente para la persona: {persona_obj.cedula} "
                            f"(idUsuario={getattr(user, 'idUsuario', None)}, tipo=UsuariosApp)")

                nombres_grupos = ['Clientes-Proveedores', 'Inscripciones']
                for nombre in nombres_grupos:
                    try:
                        grupo = Group.objects.get(name=nombre)
                    except Group.DoesNotExist:
                        logger.warning(f"⚠️ Grupo '{nombre}' no existe — se omite la asignación a ese grupo.")
                        continue
                    user.groups.add(grupo)
                    logger.info(f"🔐 Usuario añadido al grupo existente: '{nombre}'")

                user.save()
                return user

        except Exception as e:
            logger.exception("Error creando usuario y asignando grupos existentes.")
            raise serializers.ValidationError(f"No se pudo crear el usuario: {e}")

    def to_representation(self, instance):
        """
        Representación robusta cuando `instance` es un objeto Usuarios.
        No asumimos atributos que no existen en Usuarios.
        """
        # proteger accesos por si falta idPersona
        persona = getattr(instance, 'idPersona', None)
        cedula = getattr(persona, 'cedula', None) if persona else None
        nombres = getattr(persona, 'nombres', '') if persona else ''
        apellidos = getattr(persona, 'apellidos', '') if persona else ''

        return {
            'idUsuario': getattr(instance, 'idUsuario', None),
            # Para mantener compatibilidad con frontend, devolvemos 'usuario' como la cédula o el idUsuario si no existe cédula
            'usuario': cedula if cedula else getattr(instance, 'idUsuario', None),
            'idPersona': getattr(persona, 'idPersona', None) if persona else None,
            'cedula': cedula,
            'nombres': nombres,
            'apellidos': apellidos,
            'coloresUsuario': getattr(instance, 'coloresUsuario', None),
            'mensaje': 'Usuario creado exitosamente'
        }