from django.apps import apps
from datetime import timedelta
from decimal import Decimal
import re
import uuid
import decimal
import traceback
from django.contrib.auth import get_user_model
from django.utils.timezone import now
from django.db import IntegrityError, transaction
from django.db.models import Sum, Q

from requests import Response
from rest_framework import serializers
from apps.home.models import Configuracion, Materia, Cohorte, Cargo, Requisito, Servicio, Tramite, Moneda, Tasa, Formacion, CuotaFormacion, TipoFormacion, Usuarios
from apps.persona.models import Personas, PersonaTP, TipoPersona
from apps.honorario.models import Honorario
from apps.inscripcion.models import Inscripcion, InscripcionCuota
from apps.solicitud.models import Solicitud
from apps.asientoContable.models import AsientoContable, DetalleAsiento
from apps.planCuenta.models import PlanCuenta
from apps.periodoContable.models import periodoContable
from apps.cuentaBanco.models import Banco, CuentaBanco
from rest_framework_simplejwt.tokens import RefreshToken
from apps.factura.models import Nota, NotaRelacionada, Pago, PlanArticulo, PagoTemporal
from apps.factura.utils import create_nota_relacionada_robusta

import logging
logger = logging.getLogger(__name__)

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
            # usar related_name 'cuotas' (según tu model) y fallback a otros nombres
            rel = getattr(obj, 'cuotas', None)
            if rel is None:
                rel = getattr(obj, 'cuotaformacion_set', None)
            if rel is None:
                return 0
            try:
                return rel.filter(is_active=True).count()
            except Exception:
                try:
                    return rel.count()
                except Exception:
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
            if not obj.fechaInicio:
                return False
            lapso = int(obj.lapsoInscripcion or 0)
            inicio_date = obj.fechaInicio
            hoy = now().date()
            fecha_fin_lapso = inicio_date + timedelta(days=lapso)
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
    idPersona_detail = serializers.SerializerMethodField()
    idFormacion_detail = serializers.SerializerMethodField()
    idCohorte_detail = CohorteSerializer(source='idCohorte', read_only=True)
    cuotas = serializers.SerializerMethodField(read_only=True)

    idPersona = serializers.IntegerField(write_only=True, required=False)
    idCohorte = serializers.IntegerField(write_only=True, required=False)

    montoTotal = serializers.SerializerMethodField()
    saldoPendiente = serializers.SerializerMethodField()
    pago_inscripcion_confirmada = serializers.SerializerMethodField()

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
            'pago_inscripcion_confirmada',
        ]

    def get_pago_inscripcion_confirmada(self, inscripcion: Inscripcion):
        """
        True si la nota de tipo 'INSCRIPCION' asociada tiene al menos un PagoTemporal confirmado
        o si la nota ya tiene estado == 'PAGADA'. False por defecto.
        """
        try:
            # Buscar nota relacionada de tipo INSCRIPCION
            nota = Nota.objects.filter(relaciones__idInscripcion=inscripcion, tipoArticulo='INSCRIPCION').first()
            if not nota:
                return False

            # Si existe PagoTemporal confirmado para esa nota -> True
            if PagoTemporal.objects.filter(idNota=nota, confirmado=True).exists():
                return True

            # Fallback: si la nota ya marcó estado PAGADA
            if (nota.estado or '').upper() == 'PAGADA':
                return True

            return False
        except Exception:
            # En caso de error devolvemos False para no habilitar pagos por seguridad
            return False

    def get_idPersona_detail(self, obj):
        try:
            persona = getattr(obj, 'idPersona', None)
            if not persona:
                return None
            # evita importar PersonaSerializer si hay problemas; devuelve campos mínimos
            return {
                'idPersona': getattr(persona, 'idPersona', None),
                'nombre': getattr(persona, 'nombre', None),
                'cedula': getattr(persona, 'cedula', None),
            }
        except Exception:
            return None

    def get_idFormacion_detail(self, obj):
        """
        Devuelve data de la formación asociada de forma defensiva:
        - intenta idCohorte.idFormacion (select_related)
        - si no existe, intenta buscar mediante idCohorte_id -> query (fallback)
        """
        try:
            cohorte = getattr(obj, 'idCohorte', None)
            if cohorte:
                form = getattr(cohorte, 'idFormacion', None)
                if form:
                    return FormacionSerializer(form).data
                # si cohorte existe pero no tiene idFormacion prefetched: intentar resolver por FK id
                form_id = getattr(cohorte, 'idFormacion_id', None) or getattr(cohorte, 'idFormacion', None)
                if form_id:
                    # hacer una consulta ligera
                    form_obj = Formacion.objects.filter(idFormacion=form_id).first()
                    if form_obj:
                        return FormacionSerializer(form_obj).data
            # fallback: intentar si el objeto Inscripcion tiene un campo nombreFormacion simple
            nombre_directo = getattr(obj, 'nombreFormacion', None)
            if nombre_directo:
                return {'nombreFormacion': nombre_directo}
            return None
        except Exception as e:
            logger.exception("get_idFormacion_detail error: %s", e)
            return None

    def get_cuotas(self, obj):
        try:
            coh = getattr(obj, 'idCohorte', None)
            if not coh:
                return []
            form = getattr(coh, 'idFormacion', None)
            form_id = None
            if form:
                # si el prefetch populó attr 'prefetched_cuotas' en la instancia de formación
                pref = getattr(form, 'prefetched_cuotas', None)
                if pref is not None:
                    return CuotaFormacionSerializer(pref, many=True).data
                form_id = getattr(form, 'idFormacion', None) or getattr(form, 'id', None)
            else:
                # fallback: tal vez solo tenemos id
                form_id = getattr(coh, 'idFormacion_id', None)
            if not form_id:
                return []
            qs = CuotaFormacion.objects.filter(idFormacion_id=form_id, is_active=True).order_by('orden')
            return CuotaFormacionSerializer(qs, many=True).data
        except Exception as e:
            logger.exception("get_cuotas error: %s", e)
            return []

    def get_montoTotal(self, obj):
        try:
            return float(getattr(obj, 'montoTotal', getattr(obj, 'monto_total', getattr(obj, 'total', 0)) or 0) )
        except Exception:
            return 0.0

    def get_saldoPendiente(self, obj):
        try:
            return float(getattr(obj, 'saldoPendiente', getattr(obj, 'montoTotal', 0) - getattr(obj, 'montoPagado', 0)))
        except Exception:
            return 0.0

    def validate(self, data):
        """
        Evita crear una nueva inscripción para la misma persona + misma cohorte/formación
        si ya existe una inscripción relacionada con pago confirmado (PagoTemporal.confirmado=True)
        o con nota en estado 'PAGADA'.
        """
        try:
            # obtener los ids (puede venir en validated_data o en initial_data si write_only)
            id_persona = data.get('idPersona') or self.initial_data.get('idPersona')
            id_cohorte = data.get('idCohorte') or self.initial_data.get('idCohorte')

            # si no están ambos, dejamos que la validación normal lo maneje más adelante
            if not id_persona or not id_cohorte:
                return data

            # resolver cohorte y su formacion (defensivo)
            coh = Cohorte.objects.select_related('idFormacion').filter(pk=id_cohorte).first()
            if not coh:
                # si la cohorte no existe no nos metemos; la creación fallará en create()
                return data
            form_id = getattr(getattr(coh, 'idFormacion', None), 'idFormacion', None) or getattr(coh, 'idFormacion_id', None)

            # buscar inscripciones previas de la misma persona y:
            # - que sean de la misma cohorte, o
            # - que pertenezcan a la misma formación (misma idFormacion)
            from apps.inscripcion.models import Inscripcion as InscripcionModel  # ajusta import si hace falta
            q_ins = InscripcionModel.objects.filter(idPersona_id=id_persona).filter(
                Q(idCohorte_id=id_cohorte) | Q(idCohorte__idFormacion_id=form_id)
            )

            if not q_ins.exists():
                return data

            # buscar notas de tipo INSCRIPCION relacionadas con esas inscripciones
            notas_qs = Nota.objects.filter(tipoArticulo='INSCRIPCION', relaciones__idInscripcion__in=q_ins).distinct()

            # 1) ¿alguna nota ya está en estado PAGADA?
            if notas_qs.filter(estado__iexact='PAGADA').exists():
                raise serializers.ValidationError("Ya existe una inscripción para esta formación/cohorte con pago confirmado (nota PAGADA). No se permiten nuevas inscripciones.")

            # 2) ¿alguna nota tiene PagoTemporal confirmado?
            if PagoTemporal.objects.filter(idNota__in=notas_qs, confirmado=True).exists():
                raise serializers.ValidationError("Ya existe una inscripción para esta formación/cohorte con pago confirmado. No se permiten nuevas inscripciones.")

        except serializers.ValidationError:
            raise
        except Exception as e:
            # si hay un problema al validar, lo registramos y permitimos seguir
            # (no lanzamos error duro para no bloquear otras validaciones)
            logger.exception("Error validando duplicidad de inscripción: %s", e)

        return data

    def create(self, validated_data):
        # tu create original (sin cambios)
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
    
class NotaSerializer(serializers.ModelSerializer):
    idInscripcion = serializers.SerializerMethodField(read_only=True)
    formacion = serializers.SerializerMethodField(read_only=True)
    persona = serializers.SerializerMethodField(read_only=True)
    idPersona_detail = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Nota
        fields = [
            'idNota', 'numeroNota', 'fechaEmision', 'totalNota', 'estado',
            'tipoArticulo', 'formaPago', 'idInscripcion', 'formacion', 'persona', 'idPersona_detail'
        ]

    def _get_first_relation(self, obj):
        """
        Obtener rel prefetched o a través de relaciones
        """
        try:
            # Primero intentar con las relaciones prefetched
            prefetched = getattr(obj, 'prefetched_relaciones', None)
            if prefetched and len(prefetched) > 0:
                return prefetched[0]
            
            # Si no hay prefetch, buscar directamente
            rel = obj.relaciones.filter(idInscripcion__isnull=False).select_related(
                'idInscripcion__idCohorte__idFormacion',
                'idInscripcion__idPersona'
            ).first()
            return rel
        except Exception as e:
            logger.exception("Error en _get_first_relation: %s", e)
            return None

    def _resolve_formacion_from_inscripcion(self, ins):
        if not ins:
            return {'nombreFormacion': 'Formación no disponible'}
        try:
            coh = getattr(ins, 'idCohorte', None)
            if coh:
                form = getattr(coh, 'idFormacion', None)
                if form:
                    return {
                        'idFormacion': form.idFormacion, 
                        'nombreFormacion': form.nombreFormacion
                    }
            return {'nombreFormacion': 'Formación no disponible'}
        except Exception as e:
            logger.exception("Error resolviendo formación desde Inscripcion: %s", e)
            return {'nombreFormacion': 'Formación no disponible'}

    def get_idInscripcion(self, obj):
        rel = self._get_first_relation(obj)
        if rel and rel.idInscripcion:
            return rel.idInscripcion.idInscripcion
        return None

    def get_formacion(self, obj):
        rel = self._get_first_relation(obj)
        try:
            if not rel:
                return {'nombreFormacion': 'Formación no disponible'}
            return self._resolve_formacion_from_inscripcion(rel.idInscripcion)
        except Exception as e:
            logger.exception("No se pudo resolver la formación para la nota %s: %s", obj.idNota, e)
            return {'nombreFormacion': 'Formación no disponible'}
        
    def get_persona(self, obj):
        """Devuelve los datos de la persona desde idPersona directo de la nota"""
        try:
            if obj.idPersona:
                return {
                    'cedula': obj.idPersona.cedula,
                    'nombre': f"{obj.idPersona.nombres} {obj.idPersona.apellidos}"
                }
        except Exception as e:
            logger.warning("No se pudo obtener persona directa para nota %s: %s", obj.idNota, e)
        
        # Fallback: intentar a través de la relación NotaRelacionada
        try:
            rel = self._get_first_relation(obj)
            if rel and rel.idInscripcion and rel.idInscripcion.idPersona:
                persona = rel.idInscripcion.idPersona
                return {
                    'cedula': persona.cedula,
                    'nombre': f"{persona.nombres} {persona.apellidos}"
                }
        except Exception as e:
            logger.warning("No se pudo obtener persona por relación para nota %s: %s", obj.idNota, e)
        
        return None

    def get_idPersona_detail(self, obj):
        """Campo adicional para compatibilidad con el frontend"""
        persona_data = self.get_persona(obj)
        if persona_data:
            return {
                'cedula': persona_data['cedula'],
                'nombres': persona_data['nombre'].split(' ')[0] if ' ' in persona_data['nombre'] else persona_data['nombre'],
                'apellidos': ' '.join(persona_data['nombre'].split(' ')[1:]) if ' ' in persona_data['nombre'] else ''
            }
        return None

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
        model = PagoTemporal
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

        # Si la nota ya está pagada, bloquear
        if (nota.estado or '').upper() == 'PAGADA':
            raise serializers.ValidationError("Esta nota ya ha sido pagada completamente.")

        # Evitar pagos duplicados: si ya existe un PagoTemporal no confirmado para la nota
        if PagoTemporal.objects.filter(idNota=nota, confirmado=False).exists():
            raise serializers.ValidationError("Ya existe un pago pendiente para esta nota. Espere confirmación antes de enviar otro pago.")

        # Comprobar que la suma de pagos confirmados + monto propuesto no exceda el total de la nota
        pagos_confirmados = Pago.objects.filter(idNota=nota).aggregate(suma=Sum('monto'))['suma'] or Decimal('0.00')
        # (además podríamos sumar pagos temporales confirmados, pero esos no deberían existir si la lógica es correcta)
        if (pagos_confirmados + Decimal(data['monto'])) > Decimal(nota.totalNota):
            raise serializers.ValidationError({
                "monto": f"El monto total de pagos excede el total de la nota (${nota.totalNota}). Pagos confirmados actuales: ${pagos_confirmados}."
            })

        # Validar que existe configuración con cuenta bancaria
        configuracion = Configuracion.objects.first()
        if not configuracion or not getattr(configuracion, 'idCuentaBanco', None):
            raise serializers.ValidationError("No hay cuenta bancaria configurada en el sistema.")

        # Guardar la nota y configuración en el contexto para usar en create()
        self.context['nota'] = nota
        self.context['configuracion'] = configuracion
        return data

    def create(self, validated_data):
        """
        Crea un PagoTemporal y marca la nota como 'EN_PROCESO' en la misma transacción.
        Evita race conditions con select_for_update().
        """
        nota = self.context.get('nota')
        configuracion = self.context.get('configuracion')

        if nota is None:
            raise serializers.ValidationError("Nota no encontrada en contexto.")
        if configuracion is None or configuracion.idCuentaBanco is None:
            raise serializers.ValidationError("Configuración de cuenta bancaria no encontrada.")

        # Determinar tasa (ejemplo: la más reciente para la moneda del sistema)
        moneda = getattr(configuracion, 'moneda', None) or Moneda.objects.filter(idMoneda=1).first()
        tasa = Tasa.objects.filter(idMoneda=moneda).order_by('-idTasa').first()
        if not tasa:
            raise serializers.ValidationError("No se encontró una tasa válida para la moneda del sistema.")

        with transaction.atomic():
            # Bloquear fila de nota para evitar condiciones de carrera
            nota_locked = Nota.objects.select_for_update().get(pk=nota.pk)

            # Re-checks dentro de la transacción
            if (nota_locked.estado or '').upper() == 'PAGADA':
                raise serializers.ValidationError("La nota ya fue pagada (re-check).")

            if PagoTemporal.objects.filter(idNota=nota_locked, confirmado=False).exists():
                raise serializers.ValidationError("Ya existe un pago pendiente para esta nota (re-check).")

            # Crear pago temporal usando la cuenta configurada
            pago_temporal = PagoTemporal.objects.create(
                idNota=nota_locked,
                idCuentaBanco=configuracion.idCuentaBanco,
                idTasa=tasa,
                monto=validated_data['monto'],
                referencia=validated_data.get('referencia', '') or '',
                observaciones=validated_data.get('observaciones', '') or '',
                fechaPago=validated_data['fechaPago'],
                confirmado=False
            )

            # Marcar la nota como 'EN_PROCESO' para bloquear UI hasta confirmación
            nota_locked.estado = 'EN_PROCESO'   # O 'EN_VALIDACION' si prefieres
            nota_locked.save(update_fields=['estado'])

            return pago_temporal

def generar_numero_nota():
    fecha_actual = now().strftime('%Y%m%d')
    numero_unico = uuid.uuid4().hex[:6].upper()
    return f"NOTA-CUOTA-{fecha_actual}-{numero_unico}"

# --- Serializer corregido ---
class CuotaPagoTemporalSerializer(serializers.Serializer):
    idInscripcion = serializers.IntegerField(write_only=True)
    nombreCuota = serializers.CharField(max_length=200)
    monto = serializers.DecimalField(max_digits=20, decimal_places=4)
    referencia = serializers.CharField(max_length=200, required=False, allow_blank=True, default='')
    observaciones = serializers.CharField(required=False, allow_blank=True, default='')

    def validate_monto(self, value):
        if value <= Decimal('0.00'):
            raise serializers.ValidationError("El monto debe ser mayor a 0.")
        return value

    def validate(self, data):
        # 1) validar existencia de inscripcion
        try:
            inscripcion = Inscripcion.objects.get(idInscripcion=data['idInscripcion'])
        except Inscripcion.DoesNotExist:
            raise serializers.ValidationError({"idInscripcion": "La inscripción especificada no existe."})

        # 2) buscar la nota de inscripción asociada (si existe)
        nota_inscripcion = Nota.objects.filter(relaciones__idInscripcion=inscripcion, tipoArticulo='INSCRIPCION').first()
        if not nota_inscripcion:
            raise serializers.ValidationError("No se encontró la nota de inscripción asociada. No se puede procesar el pago de cuotas.")

        # 3) VALIDACIÓN CLAVE: PagoTemporal confirmado O nota.estado == 'PAGADA'
        pago_confirmado = PagoTemporal.objects.filter(idNota=nota_inscripcion, confirmado=True).exists()
        if not pago_confirmado and (nota_inscripcion.estado or '').upper() != 'PAGADA':
            raise serializers.ValidationError("El pago de inscripción no está confirmado. Solo puede pagar cuotas después de la confirmación.")

        # 4) validar que exista la InscripcionCuota con estado EN ESPERA para ese nombre
        try:
            cuota = inscripcion.inscripcioncuota_set.select_related('idCuota').get(
                idCuota__nombreCuota__iexact=data['nombreCuota'],
                estadoPago__iexact='EN ESPERA'
            )
        except InscripcionCuota.DoesNotExist:
            raise serializers.ValidationError({"cuota": "La cuota seleccionada no está disponible para pago (ya fue pagada, está pendiente o no existe)."})
        except InscripcionCuota.MultipleObjectsReturned:
            raise serializers.ValidationError({"cuota": "Error de duplicidad de cuotas. Contacte a soporte."})

        # 5) validar/ajustar monto
        real_valor = getattr(cuota.idCuota, 'valorCuota', None)
        if real_valor is not None and Decimal(str(data['monto'])) != Decimal(str(real_valor)):
            data['monto'] = Decimal(str(real_valor))

        # 6) validar configuración (con fallback en nombres)
        configuracion = Configuracion.objects.first()
        cuenta_banco = None
        if configuracion:
            cuenta_banco = getattr(configuracion, 'idCuentaBanco', None) or getattr(configuracion, 'id_cuenta_banco', None) or getattr(configuracion, 'cuenta_banco', None)

        if not configuracion or not cuenta_banco:
            raise serializers.ValidationError("No hay cuenta bancaria configurada en el sistema (Configuracion.idCuentaBanco).")

        # Guardar en contexto para create()
        self.context['inscripcion'] = inscripcion
        self.context['cuota'] = cuota
        self.context['configuracion'] = configuracion
        self.context['nota_inscripcion'] = nota_inscripcion
        return data

    @transaction.atomic
    def create(self, validated_data):
        debug_steps = []
        try:
            inscripcion: Inscripcion = self.context.get('inscripcion')
            cuota: InscripcionCuota = self.context.get('cuota')
            configuracion = self.context.get('configuracion')
            nota_inscripcion = self.context.get('nota_inscripcion')

            debug_steps.append({"step": "context_loaded", "inscripcion": getattr(inscripcion, 'idInscripcion', None), "cuota_pk": getattr(cuota, 'pk', None)})

            # tasa
            tasa = None
            moneda = getattr(configuracion, 'moneda', None) or getattr(configuracion, 'idMoneda', None)
            if moneda:
                tasa = Tasa.objects.filter(idMoneda=moneda).order_by('-idTasa').first()
            debug_steps.append({"step": "tasa_busqueda", "tasa_found": bool(tasa), "tasa_id": getattr(tasa, 'idTasa', None)})
            if not tasa:
                raise serializers.ValidationError({"error": "No se encontró tasa para la moneda configurada.", "debug": debug_steps})

            # periodo
            periodo_activo = periodoContable.objects.filter(estadoPeriodo=True).first()
            if not periodo_activo:
                periodo_activo = periodoContable.objects.order_by('-idPeriodo').first()
            debug_steps.append({"step": "periodo", "periodo_activo": getattr(periodo_activo, 'idPeriodo', None)})
            if not periodo_activo:
                raise serializers.ValidationError({"error": "No hay periodo contable activo.", "debug": debug_steps})

            # crear asiento
            numero_asiento = f"CUOTA-{now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
            asiento = AsientoContable.objects.create(
                numeroAsiento=numero_asiento,
                fechaAsiento=now().date(),
                conceptoAsiento=f"Solicitud pago cuota: {getattr(cuota.idCuota, 'nombreCuota', 'Cuota')} - Inscripción: {inscripcion.idInscripcion}",
                idPeriodo=periodo_activo
            )
            debug_steps.append({"step": "crear_asiento", "asiento_id": getattr(asiento, 'pk', None)})

            # crear nota
            numero_nota = generar_numero_nota()
            nota = Nota.objects.create(
                idAsiento=asiento,
                idPersona=inscripcion.idPersona,
                tipoArticulo='CUOTA',
                numeroNota=numero_nota,
                fechaEmision=now().date(),
                fechaVencimiento=now().date() + timedelta(days=7),
                formaPago='TRANSFERENCIA',
                totalNota=validated_data['monto'],
                idTasa=tasa,
                estado='PENDIENTE',
                observaciones=f"Nota para {getattr(cuota.idCuota, 'nombreCuota', 'Cuota')}"
            )
            debug_steps.append({"step": "crear_nota", "nota_id": getattr(nota, 'idNota', None)})

            # === Crear NotaRelacionada: intentar con InscripcionCuota primero, si falla intentar con CuotaFormacion ===
            created_nr = None
            try:
                # intento normal: pasar la instancia InscripcionCuota
                with transaction.atomic():
                    created_nr = NotaRelacionada.objects.create(
                        idNota=nota,
                        idInscripcion=inscripcion,
                        idCuota=cuota  # intenta insertar la FK como InscripcionCuota
                    )
                debug_steps.append({"step": "nota_relacionada", "method": "inscripcioncuota", "idCuota_used": getattr(cuota, 'pk', None)})
            except IntegrityError as ie:
                # Fallback: la BD probablemente tenga la FK apuntando a CuotaFormacion.
                logger.warning("IntegrityError creando NotaRelacionada con InscripcionCuota pk=%s: %s", getattr(cuota,'pk',None), ie)
                # obtener la FK real hacia CuotaFormacion desde la InscripcionCuota
                # obtener la PK de la CuotaFormacion desde la InscripcionCuota
                cf = getattr(cuota, 'idCuota', None)
                cf_pk = getattr(cf, 'idCuota', None) or getattr(cf, 'pk', None) or getattr(cf, 'id', None)
                if not cf_pk:
                    raise serializers.ValidationError({
                        "error": "No se pudo resolver la CuotaFormacion desde la InscripcionCuota."
                    })

                # crear NotaRelacionada apuntando a la CuotaFormacion de forma consistente:
                created_nr = None
                # obtener la PK de la CuotaFormacion desde la InscripcionCuota
                cf = getattr(cuota, 'idCuota', None)
                cf_pk = getattr(cf, 'idCuota', None) or getattr(cf, 'pk', None) or getattr(cf, 'id', None)
                if not cf_pk:
                    logger.exception("No se pudo resolver PK de CuotaFormacion desde InscripcionCuota (inscripcion=%s, cuota_pk=%s)", getattr(inscripcion,'idInscripcion',None), getattr(cuota,'pk',None))
                    raise serializers.ValidationError({
                        "error": "No se pudo resolver la CuotaFormacion desde la InscripcionCuota."
                    })

                # crear NotaRelacionada de forma consistente apuntando a la CuotaFormacion
                try:
                    created_nr = NotaRelacionada.objects.create(
                        idNota=nota,
                        idInscripcion=inscripcion,
                        idCuota_id=cf_pk  # <- referenciamos siempre la CuotaFormacion
                    )
                    debug_steps.append({"step": "nota_relacionada", "method": "cuotaformacion_direct", "idCuota_used": cf_pk})
                except IntegrityError as ie:
                    logger.exception("IntegrityError creando NotaRelacionada apuntando a CuotaFormacion id=%s: %s", cf_pk, ie)
                    raise serializers.ValidationError({
                        "error": "Error creando NotaRelacionada (integridad).",
                        "detail": str(ie),
                        "debug": debug_steps
                    })

            # pago temporal
            cuenta_banco_val = getattr(configuracion, 'idCuentaBanco', getattr(configuracion, 'id_cuenta_banco', getattr(configuracion, 'cuenta_banco', None)))
            pago_temporal = PagoTemporal.objects.create(
                idNota=nota,
                idCuentaBanco=cuenta_banco_val,
                idTasa=tasa,
                monto=validated_data['monto'],
                referencia=validated_data.get('referencia', ''),
                observaciones=validated_data.get('observaciones', ''),
                confirmado=False
            )
            debug_steps.append({"step": "pago_temporal_created", "idPagoTemporal": getattr(pago_temporal, 'idPagoTemporal', None)})

            # actualizar cuota (InscripcionCuota)
            cuota.estadoPago = 'PENDIENTE'
            cuota.save(update_fields=['estadoPago'])
            debug_steps.append({"step": "cuota_actualizada", "estadoPago": cuota.estadoPago})

            # detalles de asiento (PlanArticulo)
                        # detalles de asiento (PlanArticulo) - REVISADO: incluir idMoneda obligatorio
            plan_articulos = PlanArticulo.objects.filter(tipoArticulo='CUOTA').order_by('-fecha')
            plan_debe = plan_articulos.filter(tipo=True).first() or plan_articulos.filter(tipo=1).first()
            plan_haber = plan_articulos.filter(tipo=False).first() or plan_articulos.filter(tipo=0).first()
            debug_steps.append({"step": "plan_articulos", "plan_debe": getattr(plan_debe, 'pk', None), "plan_haber": getattr(plan_haber, 'pk', None)})

            # --- NUEVO: resolver moneda para DetalleAsiento (campo obligatorio en DB) ---
            moneda_obj = None
            # tasa fue resuelta arriba; preferimos la moneda de la tasa
            moneda_obj = getattr(tasa, 'idMoneda', None) or getattr(tasa, 'moneda', None)
            # fallback a la configuración (si contiene objeto o id)
            if not moneda_obj:
                moneda_obj = getattr(configuracion, 'moneda', None) or getattr(configuracion, 'idMoneda', None)

            if not moneda_obj:
                # abortar con mensaje claro en vez de provocar IntegrityError en BD
                debug_steps.append({"step": "detalle_asiento_error", "reason": "no_moneda_disponible"})
                raise serializers.ValidationError({
                    "error": "No se pudo determinar la moneda para los DetalleAsiento (idMoneda). Revise la configuración/tasa.",
                    "debug": debug_steps
                })

            # obtener id numérico de la moneda (soporta tanto instancia como entero)
            moneda_id = None
            try:
                moneda_id = getattr(moneda_obj, 'pk', None) or getattr(moneda_obj, 'id', None) or int(moneda_obj)
            except Exception:
                moneda_id = None

            if not moneda_id:
                debug_steps.append({"step": "detalle_asiento_error", "reason": "moneda_id_no_valida", "moneda_obj": str(moneda_obj)})
                raise serializers.ValidationError({
                    "error": "La moneda determinada no tiene una PK válida (idMoneda).",
                    "debug": debug_steps
                })

            # crear los DetalleAsiento incluyendo idMoneda_id para satisfacer la constraint NOT NULL
            if plan_debe and plan_haber:
                DetalleAsiento.objects.create(
                    idAsiento=asiento,
                    idPlanCuenta=plan_debe.idPlanCuenta,
                    idMoneda_id=moneda_id,
                    debe=Decimal(validated_data['monto']),
                    haber=Decimal('0.00')
                )
                DetalleAsiento.objects.create(
                    idAsiento=asiento,
                    idPlanCuenta=plan_haber.idPlanCuenta,
                    idMoneda_id=moneda_id,
                    debe=Decimal('0.00'),
                    haber=Decimal(validated_data['monto'])
                )
                debug_steps.append({"step": "detalle_asiento_creado", "moneda_id": moneda_id})
            else:
                debug_steps.append({"step": "detalle_asiento_omitido", "reason": "PlanArticulo no encontrado"})

            # Guardar meta para la vista: id de la nota relacionada y el raw idCuota guardado en DB
            if created_nr:
                self.context['created_nr_id'] = getattr(created_nr, 'id', None)
                # _id raw es el entero que está en la columna idCuota_id (puede ser id InscripcionCuota o id CuotaFormacion)
                self.context['created_nr_raw_idCuota'] = getattr(created_nr, 'idCuota_id', None)

            self.context['debug_steps'] = debug_steps
            return pago_temporal

        except serializers.ValidationError:
            raise
        except Exception as exc:
            tb = traceback.format_exc()
            logger.exception("Error en create() CuotaPagoTemporalSerializer: %s", tb)
            raise serializers.ValidationError({
                "error": str(exc),
                "traceback": tb,
                "debug_steps": debug_steps
            })

class RequisitoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Requisito
        fields = ['idRequisito', 'nombreRequisito', 'app', 'estadoRequisito', 'fechaRequisito']

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
        model = Usuarios  # Usa el modelo de home
        fields = ['idUsuario', 'idPersona', 'preguntaSeguridad', 'coloresUsuario', 'fechaUsuario', 'is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions']

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


# Si tienes modelo CuentaBanco, mejor serializarlo anidado:
class CuentaBancoSerializer(serializers.ModelSerializer):
    class Meta:
        model = CuentaBanco  # ajusta si tu clase se llama distinto
        fields = ('idCuentaBanco', 'banco', 'numeroCuentaBanco', 'tipoProducto')

class ConfiguracionSerializer(serializers.ModelSerializer):
    # Exponer idCuentaBanco como objeto anidado
    idCuentaBanco = CuentaBancoSerializer(read_only=True)

    # Campos "derivados" para compatibilidad con frontend
    nombre_banco = serializers.SerializerMethodField(read_only=True)
    numero_cuenta = serializers.SerializerMethodField(read_only=True)
    tipo_cuenta = serializers.SerializerMethodField(read_only=True)

    def get_nombre_banco(self, obj):
        return getattr(obj.idCuentaBanco, 'banco', None) or getattr(obj, 'nombre_banco', None) or ''

    def get_numero_cuenta(self, obj):
        return getattr(obj.idCuentaBanco, 'numeroCuentaBanco', None) or getattr(obj, 'numero_cuenta', None) or ''

    def get_tipo_cuenta(self, obj):
        return getattr(obj.idCuentaBanco, 'tipoProducto', None) or getattr(obj, 'tipo_cuenta', None) or ''

    class Meta:
        model = Configuracion
        fields = [
            'idConfig',
            'nombreInstitucion',
            'rif',
            'correoInstitucion',
            'logo',
            'firma',
            'moneda',
            'descuento',
            'idCuentaBanco',   # ahora será el objeto anidado
            'cedulaCuenta',
            'fechaConfiguracion',
            'nombre_banco',
            'numero_cuenta',
            'tipo_cuenta'
        ]


class SecurityAnswerSerializer(serializers.Serializer):
    cedula = serializers.CharField()
    respuesta = serializers.CharField()

    def validate_cedula(self, value):
        return normalize_cedula(value)

class PasswordResetSerializer(serializers.Serializer):
    cedula = serializers.CharField()
    password = serializers.CharField(min_length=8)

    def validate_cedula(self, value):
        return normalize_cedula(value)

    def validate_password(self, value):
        # Validación simple de complejidad: mínimo 8, letras + números
        if len(value) < 8:
            raise serializers.ValidationError("La contraseña debe tener al menos 8 caracteres.")
        if not re.search(r'[0-9]', value) or not re.search(r'[A-Za-zÁÉÍÓÚáéíóúÑñ]', value):
            raise serializers.ValidationError("La contraseña debe contener letras y números.")
        return value