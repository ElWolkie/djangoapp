from datetime import datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal
import re
import uuid
import decimal
import traceback

import logging
logger = logging.getLogger(__name__)

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
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import get_user_model
from django.utils.timezone import make_aware, now
from django.db import models, transaction

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

        # Validaciones de negocio
        if nota.estado == 'PAGADA':
            raise serializers.ValidationError("Esta nota ya ha sido pagada completamente.")

        if data['monto'] > nota.totalNota:
            raise serializers.ValidationError({
                "monto": f"El monto no puede exceder el total de la nota (${nota.totalNota})."
            })

        # Validar que existe configuración con cuenta bancaria
        configuracion = Configuracion.objects.first()
        if not configuracion or not configuracion.idCuentaBanco:
            raise serializers.ValidationError("No hay cuenta bancaria configurada en el sistema.")

        # Guardar la nota y configuración en el contexto
        self.context['nota'] = nota
        self.context['configuracion'] = configuracion
        return data

    def create(self, validated_data):
        """
        Crea un PagoTemporal usando la cuenta bancaria de la configuración.
        """
        nota = self.context.get('nota')
        configuracion = self.context.get('configuracion')
        
        if nota is None:
            raise serializers.ValidationError("Nota no encontrada en contexto.")
        if configuracion is None or configuracion.idCuentaBanco is None:
            raise serializers.ValidationError("Configuración de cuenta bancaria no encontrada.")

        # Obtener moneda/tasa
        moneda = None
        if configuracion and getattr(configuracion, 'moneda', None):
            moneda = configuracion.moneda
        else:
            moneda = Moneda.objects.filter(idMoneda=1).first()

        if not moneda:
            raise serializers.ValidationError("No se pudo determinar la moneda del sistema.")

        tasa = Tasa.objects.filter(idMoneda=moneda).order_by('-idTasa').first()
        if not tasa:
            raise serializers.ValidationError(f"No se encontró tasa para la moneda {moneda}.")

        # Crear PagoTemporal con la cuenta bancaria de la configuración
        pago_temporal = PagoTemporal.objects.create(
            idNota=nota,
            idCuentaBanco=configuracion.idCuentaBanco,  # Usamos la cuenta de la configuración
            idTasa=tasa,
            monto=validated_data['monto'],
            referencia=validated_data.get('referencia', '') or '',
            observaciones=validated_data.get('observaciones', '') or '',
            fechaPago=validated_data['fechaPago'],
            confirmado=False
        )

        return pago_temporal

class CuotaPagoTemporalSerializer(serializers.Serializer):
    """
    Serializer para registrar un pago temporal de una CUOTA específica
    de una inscripción.
    """
    idInscripcion = serializers.IntegerField(write_only=True)
    nombreCuota = serializers.CharField(max_length=200)
    monto = serializers.DecimalField(max_digits=20, decimal_places=4)
    referencia = serializers.CharField(max_length=200)
    observaciones = serializers.CharField(required=False, allow_blank=True, default='')
    
    # ... (validate_monto y validate se mantienen iguales) ...
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

        # 2) buscar la nota de inscripción asociada
        nota_inscripcion = Nota.objects.filter(relaciones__idInscripcion=inscripcion, tipoArticulo='INSCRIPCION').first()
        if not nota_inscripcion:
            raise serializers.ValidationError("No se encontró la nota de inscripción asociada. No se puede procesar el pago de cuotas.")

        # 3) VALIDACIÓN CLAVE: PagoTemporal confirmado O nota.estado == 'PAGADA'
        pago_confirmado = PagoTemporal.objects.filter(idNota=nota_inscripcion, confirmado=True).exists()
        if not pago_confirmado and (nota_inscripcion.estado or '').upper() != 'PAGADA':
            raise serializers.ValidationError("El pago de inscripción no está confirmado. Solo puede pagar cuotas después de la confirmación.")

        # 4) validar que exista la InscripcionCuota con estado EN ESPERA para ese nombre
        try:
            cuota = inscripcion.inscripcioncuota_set.get(
                idCuota__nombreCuota=data['nombreCuota'],
                estadoPago='EN ESPERA'
            )
        except InscripcionCuota.DoesNotExist:
            raise serializers.ValidationError({"cuota": "La cuota seleccionada no está disponible para pago (ya fue pagada, está pendiente o no existe)."})
        except InscripcionCuota.MultipleObjectsReturned:
            raise serializers.ValidationError({"cuota": "Error de duplicidad de cuotas. Contacte a soporte."})

        # 5) validar/ajustar monto
        real_valor = getattr(cuota.idCuota, 'valorCuota', None)
        if real_valor is not None and Decimal(data['monto']) != Decimal(real_valor):
            data['monto'] = Decimal(real_valor)

        # 6) validar configuración
        configuracion = Configuracion.objects.first()
        if not configuracion or not getattr(configuracion, 'idCuentaBanco', None):
            raise serializers.ValidationError("No hay cuenta bancaria configurada en el sistema.")

        # Guardar en contexto para create()
        self.context['inscripcion'] = inscripcion
        self.context['cuota'] = cuota
        self.context['configuracion'] = configuracion
        return data

    @transaction.atomic
    def create(self, validated_data):
        inscripcion: Inscripcion = self.context.get('inscripcion')
        cuota: InscripcionCuota = self.context.get('cuota')
        configuracion = self.context.get('configuracion')
        monto_pago = validated_data['monto'] # Este tiene 4 decimales

        # 1. Obtener tasa
        tasa = None
        try:
            moneda = getattr(configuracion, 'moneda', None)
            if moneda:
                tasa = Tasa.objects.filter(idMoneda=moneda).order_by('-idTasa').first()
        except Exception:
            tasa = None
        if not tasa:
            raise serializers.ValidationError("No se encontró tasa para la moneda configurada.")

        # 2. Verificar periodo contable
        periodo_activo = periodoContable.objects.filter(estadoPeriodo=True).first()
        if not periodo_activo:
            raise serializers.ValidationError("No hay periodo contable activo. Contacte a administración.")

        # 3. Crear asiento provisorio
        numero_asiento = f"CUOTA-{now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
        asiento = AsientoContable.objects.create(
            numeroAsiento=numero_asiento,
            fechaAsiento=now().date(),
            conceptoAsiento=f"Solicitud pago cuota: {getattr(cuota.idCuota, 'nombreCuota', 'Cuota')} - Inscripción: {inscripcion.idInscripcion}",
            idPeriodo=periodo_activo
        )

        # 4. Crear la Nota de Cobro (tipo CUOTA)
        numero_nota = f"NOTA-CUOTA-{uuid.uuid4().hex[:6].upper()}"
        nota = Nota.objects.create(
            idAsiento=asiento,
            idPersona=inscripcion.idPersona,
            tipoArticulo='CUOTA',
            numeroNota=numero_nota,
            fechaEmision=now().date(),
            fechaVencimiento=now().date() + timedelta(days=7),
            formaPago='TRANSFERENCIA',
            totalNota=monto_pago,
            idTasa=tasa,
            estado='PENDIENTE',
            observaciones=f"Nota para {getattr(cuota.idCuota, 'nombreCuota', 'Cuota')}"
        )

        # 5. Crear detalles de asiento
        try:
            plan_debe = PlanArticulo.objects.filter(tipoArticulo='CUOTA', tipo=1).order_by('-fecha').first()
            plan_haber = PlanArticulo.objects.filter(tipoArticulo='CUOTA', tipo=0).order_by('-fecha').first()
            
            if not plan_debe:
                raise serializers.ValidationError("Error de configuración: No se encontró plan de cuenta (DEBE) para 'CUOTA'.")
            if not plan_haber:
                raise serializers.ValidationError("Error de configuración: No se encontró plan de cuenta (HABER) para 'CUOTA'.")

            DetalleAsiento.objects.create(
                idAsiento=asiento, idPlanCuenta=plan_debe.idPlanCuenta,
                debe=monto_pago, haber=Decimal('0.00')
            )
            DetalleAsiento.objects.create(
                idAsiento=asiento, idPlanCuenta=plan_haber.idPlanCuenta,
                debe=Decimal('0.00'), haber=monto_pago
            )
        except Exception as e:
            raise serializers.ValidationError(f"Error creando detalles contables: {e}")
        
        # 6. Relacionar la nota
        NotaRelacionada.objects.create(
            idNota=nota,
            idInscripcion=inscripcion,
            idCuota=cuota
        )

        # 7. Crear PagoTemporal
        pago_temporal = PagoTemporal.objects.create(
            idNota=nota,
            idCuentaBanco=getattr(configuracion, 'idCuentaBanco'),
            idTasa=tasa,
            monto=monto_pago,
            referencia=validated_data.get('referencia', ''),
            observaciones=validated_data.get('observaciones', ''),
            confirmado=False
        )
        
        # --- ¡MANEJO DE ERROR CRÍTICO Y SOLUCIÓN DE GUARDADO! ---
        # 8. Actualizar la InscripcionCuota
        try:
            cuota.estadoPago = 'PENDIENTE'
            cuota.fechaPago = now().date()
            
            # Redondeo para InscripcionCuota (2 decimales)
            dos_decimales = Decimal('0.01')
            cuota.montoPagado = monto_pago.quantize(dos_decimales, rounding=ROUND_HALF_UP)
            
            # CAMBIO CLAVE: Usamos un save() simple para evitar problemas con update_fields
            cuota.save() 
            logger.info(f"InscripcionCuota {cuota.id if hasattr(cuota, 'id') else cuota.pk} actualizada a PENDIENTE.")

        except Exception as e:
            # Si hay un error aquí, lo capturamos, lo logeamos y lo lanzamos como ValidationError
            # para que la transacción haga ROLLBACK y veamos el mensaje en el log de Django.
            logger.error(f"Error CRÍTICO al actualizar InscripcionCuota {cuota.pk}: {e}")
            raise serializers.ValidationError(f"Error interno al finalizar el pago de cuota: {e}")


        return pago_temporal

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


class ConfiguracionSerializer(serializers.ModelSerializer):
    nombre_banco = serializers.CharField(source='idCuentaBanco.banco', read_only=True)
    numero_cuenta = serializers.CharField(source='idCuentaBanco.numeroCuentaBanco', read_only=True)
    tipo_cuenta = serializers.CharField(source='idCuentaBanco.tipoProducto', read_only=True)
    
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
            'idCuentaBanco',
            'cedulaCuenta',
            'fechaConfiguracion',
            'nombre_banco',
            'numero_cuenta',
            'tipo_cuenta'
        ]