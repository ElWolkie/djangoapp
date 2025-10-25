from datetime import timedelta
from decimal import Decimal
import re
import uuid
import decimal
import traceback
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

from apps.factura.models import Nota, NotaRelacionada, Pago, PlanArticulo

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

class NotaSerializer(serializers.ModelSerializer):
    idInscripcion = serializers.SerializerMethodField(read_only=True)
    formacion = serializers.SerializerMethodField(read_only=True)
    persona = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Nota
        fields = [
            'idNota',
            'numeroNota',
            'fechaEmision',
            'totalNota',
            'estado',
            'tipoArticulo',
            'formaPago',
            'idInscripcion',
            'formacion',
            'persona',
        ]

    def _get_relacion(self, obj):
        try:
            return NotaRelacionada.objects.filter(idNota=obj).first()
        except Exception:
            return None

    def _resolve_inscripcion_obj(self, rel):
        """
        Devuelve instancia Inscripcion (o None). Maneja:
         - rel.idInscripcion ya siendo instancia
         - rel.idInscripcion siendo int/str pk
         - rel.idInscripcion siendo dict-like con idInscripcion
        """
        try:
            if not rel:
                return None

            ins_ref = getattr(rel, 'idInscripcion', None)
            # debug simple (para logs)
            # print(f"[DEBUG] rel.idInscripcion raw type: {type(ins_ref)} - value: {repr(ins_ref)}")

            # Caso instancia ya resuelta
            if isinstance(ins_ref, Inscripcion):
                return ins_ref

            # Si es entero o string numérico -> buscar por pk
            ins_pk = None
            if isinstance(ins_ref, int):
                ins_pk = ins_ref
            elif isinstance(ins_ref, str) and ins_ref.isdigit():
                ins_pk = int(ins_ref)
            else:
                # si es objeto con atributos comunes
                try:
                    ins_pk = getattr(ins_ref, 'idInscripcion', getattr(ins_ref, 'pk', None))
                    if not ins_pk and hasattr(ins_ref, 'get'):
                        # dict-like
                        ins_pk = ins_ref.get('idInscripcion') or ins_ref.get('pk') or ins_ref.get('id')
                except Exception:
                    ins_pk = None

            if ins_pk:
                # traer con select_related para tener cohorte/formacion/persona si existen
                return Inscripcion.objects.select_related('idCohorte__idFormacion', 'idPersona').filter(idInscripcion=ins_pk).first()

            # última opción: si ins_ref tiene campos mínimos de cohorte/formacion embebidos (rare)
            return None
        except Exception:
            traceback.print_exc()
            return None

    def get_idInscripcion(self, obj):
        try:
            rel = self._get_relacion(obj)
            ins_obj = self._resolve_inscripcion_obj(rel)
            if ins_obj:
                return getattr(ins_obj, 'idInscripcion', getattr(ins_obj, 'pk', None))
            # fallback: devolver el valor crudo si es pk
            if rel:
                raw = getattr(rel, 'idInscripcion', None)
                try:
                    if isinstance(raw, int):
                        return raw
                    if isinstance(raw, str) and raw.isdigit():
                        return int(raw)
                except Exception:
                    pass
            return None
        except Exception:
            return None

    def get_formacion(self, obj):
        """
        Devuelve un dict con { idFormacion, nombreFormacion } intentando varios caminos:
         - Inscripcion.idFormacion_id (campo FK directo)
         - Inscripcion.idCohorte_id -> Cohorte.idFormacion (consulta select_related)
         - Si falla, imprime debug para ver la forma real de la Inscripcion relacionada.
        """
        try:
            rel = self._get_relacion(obj)
            ins_obj = self._resolve_inscripcion_obj(rel)
            if not ins_obj:
                # nada que resolver
                print(f"[DEBUG-Nota] nota={getattr(obj, 'idNota', '?')} -> no hay inscripcion relacionada")
                return None

            # 1) intentar FK directo en Inscripcion: idFormacion_id
            form_pk = getattr(ins_obj, 'idFormacion_id', None)
            if form_pk:
                form = Formacion.objects.filter(idFormacion=form_pk).first()
                if form:
                    return {
                        'idFormacion': getattr(form, 'idFormacion', getattr(form, 'pk', None)),
                        'nombreFormacion': getattr(form, 'nombreFormacion', getattr(form, 'nombre', None))
                    }

            # 2) intentar via cohorte: primero por idCohorte_id
            coh_pk = getattr(ins_obj, 'idCohorte_id', None)
            # si no existe idCohorte_id, tal vez idCohorte es instancia; intentar extraer su pk
            if not coh_pk:
                coh_candidate = getattr(ins_obj, 'idCohorte', None)
                # si coh_candidate es instancia de Cohorte, extraer su pk
                if coh_candidate and hasattr(coh_candidate, 'idCohorte'):
                    coh_pk = getattr(coh_candidate, 'idCohorte', None)

            if coh_pk:
                coh = Cohorte.objects.select_related('idFormacion').filter(idCohorte=coh_pk).first()
                if coh and getattr(coh, 'idFormacion', None):
                    form = coh.idFormacion
                    return {
                        'idFormacion': getattr(form, 'idFormacion', getattr(form, 'pk', None)),
                        'nombreFormacion': getattr(form, 'nombreFormacion', getattr(form, 'nombre', None))
                    }

            # 3) última opción: intentar leer ins_obj.idCohorte (puede ser dict-like)
            try:
                coh_raw = getattr(ins_obj, 'idCohorte', None)
                if coh_raw and not isinstance(coh_raw, (int, str)):
                    # si es objeto/dict que contiene idFormacion embebido:
                    form_embebido = None
                    # si coh_raw tiene atributo idFormacion
                    if hasattr(coh_raw, 'idFormacion'):
                        f = getattr(coh_raw, 'idFormacion')
                        if f and (hasattr(f, 'nombreFormacion') or isinstance(f, dict)):
                            # si es instancia
                            if hasattr(f, 'nombreFormacion'):
                                return {'idFormacion': getattr(f, 'idFormacion', getattr(f, 'pk', None)), 'nombreFormacion': getattr(f, 'nombreFormacion', getattr(f, 'nombre', None))}
                            # si es dict-like
                            if isinstance(f, dict):
                                return {'idFormacion': f.get('idFormacion') or f.get('id'), 'nombreFormacion': f.get('nombreFormacion') or f.get('nombre')}
                    # si coh_raw es dict con idFormacion anidado:
                    if isinstance(coh_raw, dict):
                        form_d = coh_raw.get('idFormacion') or coh_raw.get('idFormacion_detail') or coh_raw.get('formacion')
                        if isinstance(form_d, dict) and (form_d.get('nombreFormacion') or form_d.get('nombre')):
                            return {'idFormacion': form_d.get('idFormacion') or form_d.get('id'), 'nombreFormacion': form_d.get('nombreFormacion') or form_d.get('nombre')}
            except Exception:
                pass

            # Si llegamos aquí no pudimos resolver, dejar trace para debug
            print(f"[DEBUG-Nota] nota={getattr(obj, 'idNota', '?')} - ins_obj repr: {repr(ins_obj)}")
            try:
                # tratar de imprimir campos útiles (si es modelo)
                attrs = {}
                for a in ('idInscripcion','idCohorte','idCohorte_id','idFormacion','idFormacion_id','idPersona','idPersona_id'):
                    try:
                        attrs[a] = getattr(ins_obj, a, None)
                    except Exception as ee:
                        attrs[a] = f"<err {str(ee)}>"
                print(f"[DEBUG-Nota] campos ins_obj: {attrs}")
            except Exception:
                pass

            return None
        except Exception as e:
            import traceback
            traceback.print_exc()
            print(f"⚠️ Error obteniendo formación para nota {getattr(obj, 'idNota', '?')}: {str(e)}")
            return None


    def get_persona(self, obj):
        try:
            rel = self._get_relacion(obj)
            ins_obj = self._resolve_inscripcion_obj(rel)
            if not ins_obj:
                return None

            persona = getattr(ins_obj, 'idPersona', None)
            if not persona:
                # intentar idPersona_id
                pid = getattr(ins_obj, 'idPersona_id', None)
                if pid:
                    persona_obj = Personas.objects.filter(idPersona=pid).first()
                    if persona_obj:
                        nombres = getattr(persona_obj, 'nombres', '') or getattr(persona_obj, 'nombre', '')
                        apellidos = getattr(persona_obj, 'apellidos', '') or ''
                        return {'nombre': (nombres + ' ' + apellidos).strip(), 'cedula': getattr(persona_obj, 'cedula', None)}
                return None

            if hasattr(persona, 'cedula') or hasattr(persona, 'nombres'):
                nombres = getattr(persona, 'nombres', '') or getattr(persona, 'nombre', '')
                apellidos = getattr(persona, 'apellidos', '') or ''
                return {'nombre': (nombres + ' ' + apellidos).strip(), 'cedula': getattr(persona, 'cedula', None)}

            # si persona es pk/dict
            try:
                pid = getattr(persona, 'idPersona', persona) if persona else None
                persona_obj = Personas.objects.filter(idPersona=pid).first()
                if persona_obj:
                    nombres = getattr(persona_obj, 'nombres', '') or getattr(persona_obj, 'nombre', '')
                    apellidos = getattr(persona_obj, 'apellidos', '') or ''
                    return {'nombre': (nombres + ' ' + apellidos).strip(), 'cedula': getattr(persona_obj, 'cedula', None)}
            except Exception:
                pass

            return None
        except Exception:
            traceback.print_exc()
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
