from datetime import timedelta
from decimal import Decimal
import re
import uuid
import decimal
import traceback
from venv import logger
from rest_framework import serializers
from apps.home.models import Configuracion, Materia, Cohorte, Cargo, Requisito, Servicio, Tramite, Moneda, Tasa, Formacion, CuotaFormacion, TipoFormacion, Usuarios
from apps.persona.models import Personas, PersonaTP, TipoPersona
from apps.honorario.models import Honorario
from apps.inscripcion.models import Inscripcion
from apps.solicitud.models import Solicitud
from apps.asientoContable.models import AsientoContable, DetalleAsiento
from apps.planCuenta.models import PlanCuenta
from apps.periodoContable.models import periodoContable
from apps.cuentaBanco.models import Banco
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import get_user_model
from django.utils.timezone import now

import logging
from apps.factura.models import Nota, NotaRelacionada, Pago, PlanArticulo, PagoTemporal

class TipoPersonaSerializer(serializers.ModelSerializer):
    class Meta:
        model = TipoPersona  # Usa el modelo de home
        fields = ['idTP', 'nombreTP', 'estadoTP', 'fechaTP']

class PersonaSerializer(serializers.ModelSerializer):
    tipos = serializers.SerializerMethodField()

    class Meta:
        model = Personas
        fields = [
            'idPersona',
            'cedula',
            'nombres',
            'apellidos',
            'telefono',
            'correo',
            'rif',
            'estadoPersona',
            'fechaPersona',
            'tipos',
        ]

    def get_tipos(self, obj):
        # obj.personatp_set all devuelve los enlaces, de cada uno tomamos idTP
        tipos_qs = [rel.idTP for rel in obj.personatp_set.all()]
        return TipoPersonaSerializer(tipos_qs, many=True).data

class PersonaTPSerializer(serializers.ModelSerializer):
    class Meta:
        model = PersonaTP  # Usa el modelo de home
        fields = ['idPersona', 'idTP', 'fechaAsignacion']

class TPFormacionSerializer(serializers.ModelSerializer):
    class Meta:
        model = TipoFormacion  # Usa el modelo de home
        fields = ['idTF', 'nombreTipoFormacion', 'estadoTipoFormacion', 'fechaTipoFormacion']

class MateriaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Materia  # Usa el modelo de home
        fields = ['idMateria', 'idFormacion', 'nombreMateria', 'estadoMateria', 'fechaMateria']

class FormacionSerializer(serializers.ModelSerializer):
    cuotas_count = serializers.SerializerMethodField()
    valorInscripcion = serializers.SerializerMethodField()

    class Meta:
        model = Formacion
        fields = [
            'idFormacion',
            'idTF',
            'nombreFormacion',
            'valorInscripcion',
            'tieneCuotas',
            'duracion',
            'estadoFormacion',
            'fechaFormacion',
            'cuotas_count',
        ]

    def get_valorInscripcion(self, obj):
        try:
            # convierte Decimal a float de forma segura
            v = getattr(obj, 'valorInscripcion', None)
            if v is None:
                return 0.0
            if isinstance(v, decimal.Decimal):
                return float(v)
            return float(v)
        except Exception:
            return 0.0

    def get_cuotas_count(self, obj):
        try:
            # intentos por nombres habituales de relación inversa
            candidates = ['cuotas', 'cuotaformacion_set', 'inscripcioncuota_set', 'cuotas_set']
            for name in candidates:
                rel = getattr(obj, name, None)
                if rel is None:
                    continue
                try:
                    # si es queryset, filtrar por is_active si aplica
                    return rel.filter(is_active=True).count()
                except Exception:
                    try:
                        return rel.count()
                    except Exception:
                        continue
            # fallback seguro
            return 0
        except Exception:
            return 0

class CohorteSerializer(serializers.ModelSerializer):
    idFormacion = FormacionSerializer(read_only=True)
    inscripcionAbierta = serializers.SerializerMethodField()

    class Meta:
        model = Cohorte
        fields = [
            'idCohorte',
            'nombreCohorte',
            'lapsoInscripcion',
            'fechaInicio',
            'fechaFin',
            'estadoCohorte',
            'fechaCohorte',
            'idFormacion',
            'inscripcionAbierta',
        ]

    def get_inscripcionAbierta(self, obj):
        try:
            # si no hay fechaInicio no está abierta
            if not obj.fechaInicio:
                return False
            lapso = int(obj.lapsoInscripcion or 0)
            inicio_date = obj.fechaInicio if hasattr(obj.fechaInicio, 'date') else obj.fechaInicio
            hoy = now().date()
            fecha_fin_lapso = inicio_date + timedelta(days=lapso)
            # está abierta si hoy está entre inicio_date y fecha_fin_lapso (inclusive)
            return inicio_date <= hoy <= fecha_fin_lapso
        except Exception:
            return False

class CargoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Cargo  # Usa el modelo de home
        fields = ['idCargo', 'nombreCargo', 'estadoCargo', 'fechaCargo']

class HonorarioSerializer(serializers.ModelSerializer):
    idPersona = PersonaSerializer(read_only=True)
    idCargo = CargoSerializer(read_only=True)
    idMateria = MateriaSerializer(read_only=True)
    idCohorte = CohorteSerializer(read_only=True)

    class Meta:
        model = Honorario
        fields = ['idHonorario','idPersona','idCargo','idCohorte','idMateria','horas','estadoHonorario','fechaHonorario','monto']


class CuotaFormacionSerializer(serializers.ModelSerializer):
    valorCuota = serializers.SerializerMethodField()

    class Meta:
        model = CuotaFormacion
        fields = ['idCuota', 'nombreCuota', 'tipoCuota', 'valorCuota', 'orden', 'fechaCuota', 'is_active']

    def get_valorCuota(self, obj):
        try:
            v = getattr(obj, 'valorCuota', None)
            if v is None:
                return 0.0
            if isinstance(v, decimal.Decimal):
                return float(v)
            return float(v)
        except Exception:
            return 0.0

class InscripcionSerializer(serializers.ModelSerializer):
    idPersona_detail = PersonaSerializer(source='idPersona', read_only=True)
    idFormacion_detail = FormacionSerializer(source='idCohorte.idFormacion', read_only=True)
    idCohorte_detail = CohorteSerializer(source='idCohorte', read_only=True)
    cuotas = serializers.SerializerMethodField(read_only=True)

    idPersona = serializers.IntegerField(write_only=True)
    idCohorte = serializers.IntegerField(write_only=True)

    montoTotal = serializers.SerializerMethodField()
    saldoPendiente = serializers.SerializerMethodField()

    class Meta:
        model = Inscripcion
        fields = [
            'idInscripcion',
            'idPersona_detail',
            'idFormacion_detail',
            'idCohorte_detail',
            'idPersona',
            'idCohorte',
            'fechaInscripcion',
            'estadoPago',
            'montoPagado',
            'montoTotal',
            'saldoPendiente',
            'is_active',
            'cuotas',
        ]

    def get_cuotas(self, obj):
        """
        Devuelve cuotas asociadas a la Formacion de la cohorte.
        Primero intenta usar datos prefetchados (formacion.prefetched_cuotas),
        si no, hace una consulta directa a CuotaFormacion.
        """
        try:
            coh = getattr(obj, 'idCohorte', None)
            if not coh:
                return []

            formacion = getattr(coh, 'idFormacion', None)
            if not formacion:
                return []

            # Si prefetch_related llenó 'prefetched_cuotas' en la Formacion:
            pref = getattr(formacion, 'prefetched_cuotas', None)
            if pref is not None:
                return CuotaFormacionSerializer(pref, many=True).data

            # fallback: consulta directa
            formacion_id = getattr(formacion, 'idFormacion', None) or getattr(formacion, 'id', None)
            if not formacion_id:
                return []

            qs = CuotaFormacion.objects.filter(idFormacion_id=formacion_id, is_active=True).order_by('orden')
            return CuotaFormacionSerializer(qs, many=True).data
        except Exception:
            return []



    def get_montoTotal(self, obj):
        """Retorna montoTotal como float seguro."""
        try:
            v = getattr(obj, 'montoTotal', None)
            if v is None:
                # algunos modelos usan total o monto
                v = getattr(obj, 'total', None) or getattr(obj, 'monto', None) or 0.0
            return float(v or 0.0)
        except Exception:
            return 0.0

    def get_saldoPendiente(self, obj):
        """Retorna saldoPendiente como float seguro."""
        try:
            v = getattr(obj, 'saldoPendiente', None)
            if v is None:
                # fallback: calcular como montoTotal - montoPagado si ambos existen
                monto_total = getattr(obj, 'montoTotal', None) or getattr(obj, 'total', None) or 0.0
                monto_pagado = getattr(obj, 'montoPagado', None) or getattr(obj, 'pagado', None) or 0.0
                return float((monto_total or 0.0) - (monto_pagado or 0.0))
            return float(v or 0.0)
        except Exception:
            return 0.0

    def create(self, validated_data):
        id_persona = validated_data.pop('idPersona', None)
        id_cohorte = validated_data.pop('idCohorte', None)

        if not id_persona or not id_cohorte:
            raise serializers.ValidationError("idPersona e idCohorte son obligatorios para crear una inscripción")

        inscripcion = Inscripcion.objects.create(
            idPersona_id=id_persona,
            idCohorte_id=id_cohorte,
            **validated_data
        )
        return inscripcion
    
logger = logging.getLogger(__name__)

class NotaSerializer(serializers.ModelSerializer):
    idInscripcion = serializers.SerializerMethodField(read_only=True)
    formacion = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Nota
        fields = [
            'idNota', 'numeroNota', 'fechaEmision', 'totalNota', 'estado',
            'tipoArticulo', 'formaPago', 'idInscripcion', 'formacion',
        ]

    def _get_first_relation(self, obj):
        """
        Función helper para obtener la primera relación de inscripción
        (que ya fue pre-cargada por la vista).
        """
        try:
            # 1. Intenta usar los datos prefetcheados por la vista (rápido)
            #    Buscamos el atributo 'prefetched_relaciones_con_inscripcion' que definimos en la vista.
            prefetched_list = getattr(obj, 'prefetched_relaciones_con_inscripcion', None)
            if prefetched_list:
                return prefetched_list[0] if prefetched_list else None
            
            # 2. Fallback (Lento: N+1) - Si la prefetch falló o no se usó.
            logger.warning(f"[Consulta N+1] Ejecutando fallback lento para Nota {obj.idNota}")
            return NotaRelacionada.objects.filter(
                idNota=obj, 
                idInscripcion__isnull=False
            ).select_related('idInscripcion__idCohorte__idFormacion').first()
        
        except Exception as e:
            logger.error(f"Error en _get_first_relation para nota {obj.idNota}: {e}")
            return None

    def get_idInscripcion(self, obj):
        rel = self._get_first_relation(obj)
        if rel and rel.idInscripcion:
            return rel.idInscripcion.idInscripcion
        return None

    def get_formacion(self, obj):
        # Obtenemos la relación (debería ser instantáneo gracias al prefetch)
        rel = self._get_first_relation(obj)
        
        try:
            # Simplemente seguimos la cadena de relaciones que ya está en memoria.
            # rel -> idInscripcion -> idCohorte -> idFormacion
            formacion = rel.idInscripcion.idCohorte.idFormacion
            
            # Si llegamos aquí, encontramos la formación.
            return {
                'idFormacion': formacion.idFormacion,
                'nombreFormacion': formacion.nombreFormacion
            }
        except (AttributeError, TypeError, Exception) as e:
            # Si algo en la cadena es Nulo (ej, rel=None, idInscripcion=None, etc.)
            # el código entrará aquí.
            logger.warning(f"No se pudo resolver la formación para la nota {obj.idNota}. Rel: {rel}. Error: {e}")
            return {'nombreFormacion': 'Formación no disponible'}

class PagoSerializer(serializers.ModelSerializer):
    idNota = NotaSerializer(read_only=True)
    
    class Meta:
        model = Pago
        fields = [
            'idPago', 'idNota', 'monto', 'fechaPago', 'formaPago',
            'referencia', 'observaciones', 'fechaRegistro'
        ]

class AsientoContableSimpleSerializer(serializers.ModelSerializer):
    class Meta:
        model = AsientoContable
        fields = ['idAsiento', 'numeroAsiento', 'fechaAsiento', 'conceptoAsiento']

class PagoCreateSerializer(serializers.ModelSerializer):
    idNota = serializers.IntegerField(write_only=True)
    monto = serializers.DecimalField(max_digits=20, decimal_places=4)
    fechaPago = serializers.DateField()
    formaPago = serializers.CharField(max_length=50)
    referencia = serializers.CharField(max_length=100, required=False, allow_blank=True)
    observaciones = serializers.CharField(required=False, allow_blank=True)

    class Meta:
        model = Pago
        fields = [
            'idNota',
            'monto',
            'fechaPago',
            'formaPago',
            'referencia',
            'observaciones',
        ]

    def validate_monto(self, value):
        if value <= Decimal('0.00'):
            raise serializers.ValidationError("El monto debe ser mayor a 0.")
        return value

    def validate(self, data):
        # Validar que la nota exista
        try:
            nota = Nota.objects.get(idNota=data['idNota'])
        except Nota.DoesNotExist:
            raise serializers.ValidationError({"idNota": "La nota especificada no existe."})

        # Validaciones de negocio
        if nota.estado == 'PAGADA':
            raise serializers.ValidationError("Esta nota ya ha sido pagada completamente.")

        if data['monto'] > nota.totalNota:
            raise serializers.ValidationError({
                "monto": f"El monto no puede exceder el total de la nota (${nota.totalNota})."
            })

        # Guardar la nota en el contexto para usarla en create / view
        self.context['nota'] = nota
        return data

    def create(self, validated_data):
        """
        Crea el AsientoContable, Pago y DetalleAsiento. 
        Este método se espera sea llamado dentro de una transacción atómica desde la view.
        """
        nota = self.context.get('nota')
        if nota is None:
            raise serializers.ValidationError("Nota no encontrada en contexto.")

        # Obtener moneda/tasa: preferir configuración si existe, si no fallback a Moneda id=1
        configuracion = Configuracion.objects.first()
        moneda = None
        if configuracion and getattr(configuracion, 'moneda', None):
            moneda = configuracion.moneda
        else:
            moneda = Moneda.objects.filter(idMoneda=1).first()

        if not moneda:
            raise serializers.ValidationError("No se pudo determinar la moneda del sistema (ni configuración ni idMoneda=1).")

        tasa = Tasa.objects.filter(idMoneda=moneda).order_by('-idTasa').first()
        if not tasa:
            raise serializers.ValidationError(f"No se encontró tasa para la moneda {moneda}.")

        # periodo contable activo (la view puede validar también)
        from apps.periodoContable.models import periodoContable
        periodo_activo = periodoContable.objects.filter(estadoPeriodo=True).first()
        if not periodo_activo:
            raise serializers.ValidationError("No hay periodo contable activo.")

        # Crear AsientoContable con número único
        numero_asiento = f"PAGO-{now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
        asiento = AsientoContable.objects.create(
            numeroAsiento=numero_asiento,
            fechaAsiento=now().date(),
            conceptoAsiento=f"Pago de {validated_data['formaPago']} - Nota: {nota.numeroNota}",
            idPeriodo=periodo_activo
        )

        # Crear Pago
        pago = Pago.objects.create(
            idNota=nota,
            idAsiento=asiento,
            idTasa=tasa,
            monto=validated_data['monto'],
            fechaPago=validated_data['fechaPago'],
            formaPago=validated_data['formaPago'],
            referencia=validated_data.get('referencia', '') or '',
            observaciones=validated_data.get('observaciones', '') or ''
        )

        # Actualizar estado de nota
        if validated_data['monto'] >= nota.totalNota:
            nota.estado = 'PAGADA'
        else:
            nota.estado = 'PARCIAL'
        nota.save()

        # Actualizar inscripción relacionada (si aplica)
        try:
            nota_relacionada = NotaRelacionada.objects.filter(idNota=nota).first()
            if nota_relacionada and nota_relacionada.idInscripcion:
                inscripcion = nota_relacionada.idInscripcion
                inscripcion.estadoPago = 'PAGADO' if validated_data['monto'] >= nota.totalNota else 'PARCIAL'
                inscripcion.save()
        except Exception as e:
            # no detiene el proceso si falla esto, solo log
            print(f"⚠️ No se pudo actualizar inscripción: {str(e)}")

        # Crear detalles de asiento (si existen planes)
        try:
            plan_articulo_debe = PlanArticulo.objects.filter(
                tipoArticulo=nota.tipoArticulo,
                tipo=True  # en tu modelo tipo es booleano; en versiones previas lo usabas 1/0
            ).order_by('-fecha').first()

            plan_articulo_haber = PlanArticulo.objects.filter(
                tipoArticulo=nota.tipoArticulo,
                tipo=False
            ).order_by('-fecha').first()

            if plan_articulo_debe and plan_articulo_haber:
                DetalleAsiento.objects.create(
                    idAsiento=asiento,
                    idPlanCuenta=plan_articulo_debe.idPlanCuenta,
                    debe=validated_data['monto'],
                    haber=Decimal('0.00')
                )
                DetalleAsiento.objects.create(
                    idAsiento=asiento,
                    idPlanCuenta=plan_articulo_haber.idPlanCuenta,
                    debe=Decimal('0.00'),
                    haber=validated_data['monto']
                )
        except Exception as e:
            print(f"⚠️ Error creando detalles de asiento: {str(e)}")

        return pago

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
    idPersona = PersonaSerializer(read_only=True)
    idTramite = TramiteSerializer(read_only=True)
    idServicio = ServicioSerializer(read_only=True)

    class Meta:
        model = Solicitud
        fields = ['idSoli', 'idPersona', 'idTramite', 'idServicio', 'montoTotal', 'estadoSolicitud', 'fechaEntrega', 'fechaSolicitud']

class BancoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Banco  # Usa el modelo de home
        fields = ['idBanco', 'nombreBanco', 'codLocalBanco', 'codSwiftBanco', 'cuentaPadre', 'codigoPlanCuenta', 'estadoBanco', 'fechaBanco']

class MonedaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Moneda  # Usa el modelo de home
        fields = ['idMoneda', 'nombreMoneda', 'simboloMoneda', 'estadoMoneda', 'fechaMoneda']

class TasaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tasa  # Usa el modelo de home
        fields = ['idTasa', 'idMoneda', 'montoTasa', 'estadoTasa', 'fechaTasa']

User = get_user_model()

def normalize_cedula(s: str) -> str:
    if not s:
        return ''
    # dejar solo dígitos (quita V- , E- , guiones, espacios, letras)
    return re.sub(r'\D', '', str(s))


class CedulaTokenObtainSerializer(serializers.Serializer):
    cedula = serializers.CharField(write_only=True, required=True)
    password = serializers.CharField(write_only=True, required=True)
    access = serializers.CharField(read_only=True)
    refresh = serializers.CharField(read_only=True)

    def validate(self, attrs):
        cedula_raw = attrs.get('cedula', '')
        password = attrs.get('password', '')

        if not cedula_raw or not password:
            raise serializers.ValidationError('cedula y password son requeridos.')

        ced = normalize_cedula(cedula_raw)
        user = None

        # 1) Intentar resolver en Usuarios relacionado a Personas (tu caso)
        try:
            persona = Personas.objects.filter(cedula__iregex=rf"{ced}$").first()
            if persona:
                usuario_rel = Usuarios.objects.filter(idPersona=persona).first()
                if usuario_rel:
                    # Caso A: tu modelo Usuarios implementa check_password
                    if hasattr(usuario_rel, 'check_password') and usuario_rel.check_password(password):
                        user = usuario_rel
                    # Caso B: Usuarios es "perfil" que tiene .user (Django User)
                    elif hasattr(usuario_rel, 'user') and usuario_rel.user and usuario_rel.user.check_password(password):
                        user = usuario_rel.user
        except Exception:
            user = None

        # 2) Si no encontró, intentar buscar en el User model por username (en caso lo uses)
        if user is None:
            try:
                candidate = User.objects.filter(username__iregex=rf"{ced}$").first()
                if candidate and candidate.check_password(password):
                    user = candidate
            except Exception:
                user = None

        if user is None:
            raise serializers.ValidationError('Credenciales inválidas.')

        # Generar tokens JWT
        refresh = RefreshToken.for_user(user)
        return {
            'refresh': str(refresh),
            'access': str(refresh.access_token),
        }

class UsuarioSerializer(serializers.ModelSerializer):
    class Meta:
        model = Banco  # Usa el modelo de home
        fields = ['idUsuario', 'idPersona', 'preguntaSeguridad', 'respuestaSeguridad', 'coloresUsuario', 'fechaUsuario', 'is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions']


# Serializers para contabilidad
class PeriodoContableSerializer(serializers.ModelSerializer):
    class Meta:
        model = periodoContable
        fields = ['idPeriodo', 'nombrePeriodo', 'fechaInicioPeriodo', 'fechaFinPeriodo', 'estadoPeriodo', 'fechaPeriodoDigital']

class PlanCuentaSerializer(serializers.ModelSerializer):
    class Meta:
        model = PlanCuenta
        fields = ['idPlanCuenta', 'codigoPlanCuenta', 'nombrePlanCuenta', 'tipoPlanCuenta', 'naturalezaPlanCuenta', 'nivelPlanCuenta', 'cuentaPadre', 'estadoPlanCuenta', 'fechaPlanCuenta']

class DetalleAsientoSerializer(serializers.ModelSerializer):
    idPlanCuenta = PlanCuentaSerializer(read_only=True)

    class Meta:
        model = DetalleAsiento
        fields = ['idDetalle', 'idPlanCuenta', 'debe', 'haber', 'estadoDetalle', 'fechaDetalle']

class AsientoContableSerializer(serializers.ModelSerializer):
    detalles = DetalleAsientoSerializer(many=True, read_only=True)
    idPeriodo = PeriodoContableSerializer(read_only=True)

    class Meta:
        model = AsientoContable
        fields = ['idAsiento', 'numeroAsiento', 'fechaAsiento', 'conceptoAsiento', 'idPeriodo', 'fechaAsientoDigital', 'detalles']


######## Nuevo Serializer para PagoTemporal##################### 

class PagoTemporalSerializer(serializers.ModelSerializer):
    class Meta:
        model = PagoTemporal
        fields = [
            'idPagoTemporal',
            'idNota',
            'idCuentaBanco',
            'monto',
            'fechaPago',
            'referencia',
            'idTasa',
            'observaciones',
            'confirmado'
        ]
        read_only_fields = ['idPagoTemporal', 'confirmado']