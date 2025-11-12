# En api/endpoints.py o en tu archivo de vistas
from datetime import timedelta, timezone
import traceback
from rest_framework.decorators import api_view
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny

from apps.persona.models import PersonaTP, Personas
from apps.home.models import CuotaFormacion, Formacion, Moneda, Usuarios
import logging

from rest_framework.permissions import IsAuthenticated
from apps.persona.serializers import PersonaCreateSerializer, UsuarioCreateSerializer

from apps.asientoContable.models import AsientoContable, DetalleAsiento
from apps.periodoContable.models import periodoContable
from django.db import transaction
from apps.inscripcion.models import Inscripcion, InscripcionCuota
from apps.factura.models import Nota, NotaRelacionada, Pago, PagoTemporal, PlanArticulo, ParametroTributario
from apps.home.models import Tasa, Configuracion
from apps.factura.templatetags.decimal_filters import to_decimal
from django.utils.timezone import now
import uuid
from decimal import Decimal, InvalidOperation

logger = logging.getLogger(__name__)

# En tu views.py, modifica la vista para más logging
class PersonaPublicRegisterView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        logger.info(f"📥 Datos recibidos RAW: {request.data}")
        
        try:
            serializer = PersonaCreateSerializer(data=request.data)
            
            if serializer.is_valid():
                logger.info(f"✅ Datos válidos: {serializer.validated_data}")
                persona_creada = serializer.save()
                
                response_data = serializer.data
                response_data['mensaje'] = 'Persona registrada exitosamente'
                
                logger.info(f"✅ Persona creada exitosamente: {persona_creada.idPersona}")
                return Response(response_data, status=status.HTTP_201_CREATED)
                
            else:
                logger.error(f"❌ Errores de validación: {serializer.errors}")
                return Response({
                    'error': 'Datos inválidos',
                    'detalles': serializer.errors,
                }, status=status.HTTP_400_BAD_REQUEST)
                
        except Exception as e:
            logger.error(f"🔥 Error crítico: {str(e)}", exc_info=True)
            return Response({
                'error': f'Error interno: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
def verificar_cedula(request):
    cedula = request.GET.get('cedula', '')
    response_data = {
        'existe': False,
        'usuario_existe': False
    }
    
    if len(cedula) >= 6:  # Longitud mínima para buscar
        try:
            persona = Personas.objects.get(cedula=cedula)
            response_data['existe'] = True
            # Verificar si ya tiene usuario
            if Usuarios.objects.filter(idPersona=persona).exists():
                response_data['usuario_existe'] = True
        except Personas.DoesNotExist:
            pass
    
    return Response(response_data)

class UsuarioPublicRegisterView(APIView):
    """
    Endpoint público para crear una cuenta de Usuario para una Persona
    que ya existe y tiene el tipo 'Usuario'.
    """
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        logger.info(f"📥 Intento de registro de usuario: {request.data.get('cedula')}")
        
        serializer = UsuarioCreateSerializer(data=request.data)
        
        if serializer.is_valid():
            # El método .save() llamará a nuestro método create()
            usuario_creado = serializer.save()
            # El método to_representation() formateará la respuesta
            return Response(serializer.to_representation(usuario_creado), status=status.HTTP_201_CREATED)
        else:
            logger.warning(f"⚠️ Registro de usuario fallido: {serializer.errors}")
            # Devolvemos el primer error encontrado para un mensaje más claro
            error_detail = next(iter(serializer.errors.values()))[0]
            return Response({
                'error': error_detail,
                'codigo': 'VALIDATION_ERROR'
            }, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET'])
def obtener_persona_login(request):
    cedula = request.GET.get('cedula', '').strip()
    print(f"🔍 [DEBUG] Buscando cédula: '{cedula}'")
    
    if len(cedula) < 6:
        return Response({
            'error': 'La cédula debe tener al menos 6 dígitos'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # Intentar diferentes formatos de búsqueda
    formatos_a_probar = [
        cedula,  # Formato original
        f"V-{cedula}",  # Con prefijo V-
        f"E-{cedula}",  # Con prefijo E- (por si acaso)
        f"P-{cedula}",  # Con prefijo P- (por si acaso)
        cedula.zfill(8)  # Con ceros a la izquierda
    ]
    
    for formato in formatos_a_probar:
        try:
            persona = Personas.objects.get(cedula=formato)
            print(f"✅ [DEBUG] Encontrada con formato '{formato}': {persona.cedula} -> {persona.idPersona}")
            
            return Response({
                'idPersona': persona.idPersona,
                'cedula': persona.cedula,
                'nombres': persona.nombres,
                'apellidos': persona.apellidos,
                'tiene_usuario': Usuarios.objects.filter(idPersona=persona).exists()
            })
            
        except Personas.DoesNotExist:
            continue
    
    # Si ningún formato funciona, buscar por contenido
    print(f"❌ [DEBUG] No se encontró con ningún formato para: '{cedula}'")
    
    similares = Personas.objects.filter(cedula__icontains=cedula)[:10]
    print(f"🔍 [DEBUG] Cédulas similares encontradas ({similares.count()}):")
    for p in similares:
        print(f"   - '{p.cedula}' -> ID: {p.idPersona}")
    
    return Response({
        'error': 'No se encontró persona con esta cédula',
        'sugerencia': 'Intente con el formato completo (ej: V-30895206)',
        'debug_similares': [{'cedula': p.cedula, 'id': p.idPersona} for p in similares]
    }, status=status.HTTP_404_NOT_FOUND)


class CuotasFormacionAPIView(APIView):
    def get(self, request, formacion_id):
        try:
            logger.info(f"🔍 [PRODUCTION] Solicitando cuotas para formación: {formacion_id}")
            
            # Verificar que formacion_id sea válido
            if not formacion_id or formacion_id <= 0:
                return Response({'error': 'ID de formación inválido'}, status=400)
            
            # Intentar obtener la formación
            formacion = Formacion.objects.get(idFormacion=formacion_id)
            logger.info(f"✅ [PRODUCTION] Formación encontrada: {formacion.nombreFormacion}")
            
            # Obtener cuotas activas
            cuotas = CuotaFormacion.objects.filter(
                idFormacion=formacion_id, 
                is_active=True
            ).order_by('orden')
            
            logger.info(f"✅ [PRODUCTION] Cuotas encontradas: {cuotas.count()}")
            
            cuotas_data = []
            for cuota in cuotas:
                cuotas_data.append({
                    'idCuota': cuota.idCuota,
                    'nombreCuota': cuota.nombreCuota,
                    'tipoCuota': cuota.tipoCuota,
                    'valorCuota': float(cuota.valorCuota),
                    'orden': cuota.orden
                })
            
            response_data = {
                'formacion_id': formacion.idFormacion,
                'nombre_formacion': formacion.nombreFormacion,
                'cuotas': cuotas_data,
                'total_cuotas': len(cuotas_data),
                'valor_total_cuotas': sum(cuota['valorCuota'] for cuota in cuotas_data),
                'status': 'success'
            }
            
            logger.info(f"✅ [PRODUCTION] Respuesta enviada exitosamente")
            return Response(response_data)
            
        except Formacion.DoesNotExist:
            logger.error(f"❌ [PRODUCTION] Formación no encontrada: {formacion_id}")
            return Response({
                'error': 'Formación no encontrada',
                'formacion_id': formacion_id,
                'status': 'error'
            }, status=404)
            
        except Exception as e:
            logger.error(f"❌ [PRODUCTION] Error inesperado: {str(e)}")
            logger.error(f"❌ [PRODUCTION] Traceback: {traceback.format_exc()}")
            
            return Response({
                'error': 'Error interno del servidor',
                'detalle': str(e) if logging.DEBUG else 'Contacte al administrador',
                'status': 'error'
            }, status=500)

class NotaCobroCreateAPIView(APIView):
    @transaction.atomic
    def post(self, request):
        id_inscripcion = request.data.get('idInscripcion')
        if not id_inscripcion:
            return Response({
                'success': False,
                'message': 'Inscripcion no encontrada. (idInscripcion faltante en request)'
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            # obtener inscripción (ya con select_related si lo necesitas)
            inscripcion = Inscripcion.objects.filter(idInscripcion=id_inscripcion, is_active=True).select_related('idFormacion', 'idPersona').first()
            if not inscripcion:
                return Response({
                    'success': False,
                    'message': 'No se encontró una inscripción activa con el ID proporcionado.'
                }, status=status.HTTP_404_NOT_FOUND)

            # obtener configuración (moneda por defecto)
            configuracion = Configuracion.objects.first()
            if not configuracion or not getattr(configuracion, 'moneda', None):
                return Response({
                    'success': False,
                    'message': 'No se encontró una configuración activa o moneda en la configuración.'
                }, status=status.HTTP_400_BAD_REQUEST)

            moneda_configuracion = configuracion.moneda

            # obtener tasa asociada a la moneda de configuración
            tasa_configuracion = Tasa.objects.filter(idMoneda=moneda_configuracion).order_by('-idTasa').first()
            if not tasa_configuracion:
                return Response({
                    'success': False,
                    'message': f'No se encontró una tasa registrada para la moneda de configuración ({getattr(moneda_configuracion, "nombreMoneda", moneda_configuracion)}).'
                }, status=status.HTTP_400_BAD_REQUEST)

            tasa_configuracion_valor = to_decimal(tasa_configuracion.montoTasa)
            numero_nota = generar_numero_nota()

            # periodo contable
            periodo_activo = periodoContable.objects.filter(estadoPeriodo=True).first()
            if not periodo_activo:
                periodo_activo = periodoContable.objects.order_by('-idPeriodo').first()
            if not periodo_activo:
                return Response({
                    'success': False,
                    'message': 'No hay ningún periodo contable registrado o activo en el sistema.'
                }, status=status.HTTP_400_BAD_REQUEST)

            # valor inscripción desde la formación asociada
            # (asegúrate que select_related('idFormacion') esté presente o usa inscripcion.idFormacion)
            valor_inscripcion = getattr(inscripcion.idFormacion, 'valorInscripcion', None)
            if valor_inscripcion is None:
                # fallback: intenta obtener desde DB
                valor_inscripcion = getattr(Formacion.objects.filter(idFormacion=getattr(inscripcion.idFormacion, 'idFormacion', None)).first(), 'valorInscripcion', Decimal('0.00'))

            # descuento por tipo de persona
            persona = inscripcion.idPersona
            tiene_descuento = PersonaTP.objects.filter(idPersona=persona, idTP=3).exists()

            # cálculos tributos
            subtotal_gravado = Decimal('0.00')
            subtotal_exento = Decimal('0.00')

            parametros_tributarios = ParametroTributario.objects.filter(activo=True)
            def obtener_parametro(tipo, aplica_a):
                return parametros_tributarios.filter(tipo=tipo, aplica_a=aplica_a).first()

            parametro_iva_exento = obtener_parametro('IVA_EXENTO', 'INSCRIPCION')
            if parametro_iva_exento and parametro_iva_exento.porcentaje == Decimal('0.00'):
                subtotal_exento = to_decimal(valor_inscripcion)
                subtotal_gravado = Decimal('0.00')
                iva = Decimal('0.00')
            else:
                subtotal_gravado = to_decimal(valor_inscripcion)
                subtotal_exento = Decimal('0.00')
                parametro_iva = obtener_parametro('IVA_GENERAL', 'INSCRIPCION')
                porcentaje_iva = parametro_iva.porcentaje if parametro_iva else Decimal('16')
                iva = subtotal_gravado * (porcentaje_iva / Decimal('100'))

            iva_retenido = Decimal('0.00')
            islr_retenido = Decimal('0.00')

            descuento = Decimal('0.00')
            if tiene_descuento:
                descuento = (subtotal_gravado + subtotal_exento) * (to_decimal(configuracion.descuento) / Decimal('100'))

            total_nota = subtotal_gravado + subtotal_exento + iva - descuento

            # crear asiento contable (si tu modelo AsientoContable requiere moneda, añádela también aquí)
            asiento = AsientoContable.objects.create(
                numeroAsiento=f"NOTA-{numero_nota}",
                fechaAsiento=now().date(),
                conceptoAsiento=f"Asiento para la nota {numero_nota}",
                idPeriodo=periodo_activo
            )

            # crear nota de cobro
            nota = Nota.objects.create(
                idAsiento=asiento,
                idPersona=persona,
                numeroNota=numero_nota,
                tipoOperacion='COBRO',
                tipoArticulo='INSCRIPCION',
                fechaEmision=now().date(),
                fechaVencimiento=now().date() + timedelta(days=1),
                formaPago='CONTADO',
                plazoCredito=None,
                subtotalExento=subtotal_exento,
                subtotalGravado=subtotal_gravado,
                iva=iva,
                ivaRetenido=iva_retenido,
                islrRetenido=islr_retenido,
                descuento=descuento,
                totalNota=total_nota,
                idTasa=tasa_configuracion,
                estado='PENDIENTE',
                observaciones='NOTA AUTOMATIZADA POR LA APP'
            )

            # crear la relación NotaRelacionada usando el id_inscripcion original (no request.POST)
            # ya tenemos la variable inscripcion actual que es la misma, así que la usamos.
            NotaRelacionada.objects.create(
                idNota=nota,
                idInscripcion=inscripcion
            )
            inscripcion.estadoPago = 'PENDIENTE'
            inscripcion.save()

            # obtener cuentas para asiento
            plan_articulos = PlanArticulo.objects.filter(tipoArticulo='INSCRIPCION').order_by('-fecha')
            plan_articulo_debe = plan_articulos.filter(tipo=1).first()
            plan_articulo_haber = plan_articulos.filter(tipo=0).first()

            if not plan_articulo_debe or not plan_articulo_haber:
                # si falla, forzamos rollback por raise
                raise Exception('No se encontraron cuentas contables válidas para el tipo de artículo seleccionado.')

            # ---- IMPORTANTE: pasar idMoneda = moneda_configuracion aquí ----
            DetalleAsiento.objects.create(
                idAsiento=asiento,
                idPlanCuenta=plan_articulo_debe.idPlanCuenta,
                idMoneda=moneda_configuracion,         # <--- fijar la moneda desde configuracion
                debe=to_decimal(nota.totalNota),
                haber=Decimal('0.00')
            )
            DetalleAsiento.objects.create(
                idAsiento=asiento,
                idPlanCuenta=plan_articulo_haber.idPlanCuenta,
                idMoneda=moneda_configuracion,         # <--- fijar la moneda desde configuracion
                debe=Decimal('0.00'),
                haber=to_decimal(nota.totalNota)
            )

            return Response({
                'success': True,
                'message': 'Nota de cobro creada exitosamente.',
                'data': {
                    'idNota': nota.idNota,
                    'numeroNota': nota.numeroNota,
                    'tipoOperacion': nota.tipoOperacion,
                    'tipoArticulo': nota.tipoArticulo,
                    'totalNota': float(nota.totalNota),
                    'subtotalGravado': float(nota.subtotalGravado),
                    'subtotalExento': float(nota.subtotalExento),
                    'iva': float(nota.iva),
                    'descuento': float(nota.descuento),
                    'estado': nota.estado,
                    'fechaEmision': nota.fechaEmision,
                    'persona': {
                        'idPersona': persona.idPersona,
                        'cedula': persona.cedula,
                        'nombre': f"{persona.nombre} {getattr(persona, 'apellido', '')}"
                    },
                    'formacion': {
                        'idFormacion': getattr(inscripcion.idFormacion, 'idFormacion', None),
                        'nombreFormacion': getattr(inscripcion.idFormacion, 'nombreFormacion', None)
                    }
                }
            }, status=status.HTTP_201_CREATED)

        except Exception as e:
            # transaction.atomic() hará rollback automático si hay excepción
            return Response({
                'success': False,
                'message': f'Ocurrió un error inesperado: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
def generar_numero_nota():
    # Generar un número único basado en la fecha y un UUID
    fecha_actual = now().strftime('%Y%m%d')  # Formato: YYYYMMDD
    numero_unico = uuid.uuid4().hex[:6].upper()  # Tomar los primeros 6 caracteres del UUID
    return f"NOTA-{fecha_actual}-{numero_unico}"

@api_view(['GET'])
def notas_por_usuario_autenticado(request):
    """
    Obtener notas del usuario autenticado (usando el idPersona del usuario logueado)
    """
    try:
        # Obtener el usuario autenticado
        usuario = request.user
        if not usuario.is_authenticated:
            return Response({
                'success': False,
                'message': 'Usuario no autenticado'
            }, status=401)

        # Obtener la persona desde el usuario
        try:
            persona = usuario.idPersona
            print(f"🔍 Buscando notas para persona ID: {persona.idPersona}")
        except Personas.DoesNotExist:
            return Response({
                'success': False,
                'message': 'Perfil de persona no encontrado para este usuario'
            }, status=404)

        # Obtener notas relacionadas con esta persona
        notas = Nota.objects.filter(
            idPersona=persona,
            estado__in=['PENDIENTE', 'PARCIAL']
        ).order_by('-fechaEmision')

        notas_data = []
        for nota in notas:
            # Obtener información de formación - MEJORADO
            formacion_nombre = "Formación no especificada"
            
            try:
                # Buscar en NotaRelacionada para obtener la formación
                relacion = NotaRelacionada.objects.filter(idNota=nota).first()
                if relacion:
                    if relacion.idInscripcion and relacion.idInscripcion.idFormacion:
                        formacion_nombre = relacion.idInscripcion.idFormacion.nombreFormacion
                    elif relacion.idCuota and relacion.idCuota.idFormacion:
                        formacion_nombre = relacion.idCuota.idFormacion.nombreFormacion
                    elif relacion.idSolicitud and relacion.idSolicitud.idFormacion:
                        formacion_nombre = relacion.idSolicitud.idFormacion.nombreFormacion
                    
                    # Si aún no tenemos nombre, buscar en otros campos
                    if formacion_nombre == "Formación no especificada":
                        if relacion.idInscripcion:
                            formacion_nombre = f"Inscripción #{relacion.idInscripcion.idInscripcion}"
                        elif relacion.idCuota:
                            formacion_nombre = f"Cuota #{relacion.idCuota.idCuota}"
                        elif relacion.idSolicitud:
                            formacion_nombre = f"Solicitud #{relacion.idSolicitud.idSolicitud}"
            except Exception as e:
                print(f"⚠️ Error obteniendo formación para nota {nota.idNota}: {str(e)}")
                formacion_nombre = "Información no disponible"

            notas_data.append({
                'idNota': nota.idNota,
                'numeroNota': nota.numeroNota,
                'fechaEmision': nota.fechaEmision,
                'totalNota': float(nota.totalNota),
                'estado': nota.estado,
                'formacion': {
                    'nombreFormacion': formacion_nombre
                },
                'persona': {
                    'nombre': f"{persona.nombres} {persona.apellidos}",
                    'cedula': persona.cedula
                }
            })

        return Response({
            'success': True,
            'data': notas_data,
            'total': len(notas_data),
            'persona_info': {
                'idPersona': persona.idPersona,
                'nombre': f"{persona.nombres} {persona.apellidos}",
                'cedula': persona.cedula
            }
        })

    except Exception as e:
        print(f"❌ Error en notas_por_usuario_autenticado: {str(e)}")
        return Response({
            'success': False,
            'message': f'Error obteniendo notas: {str(e)}'
        }, status=500)

@api_view(['POST'])
def corregir_relaciones_notas(request):
    """
    Script temporal para corregir relaciones de notas existentes
    """
    try:
        # Obtener todas las notas de tipo INSCRIPCION que no tienen relaciones
        notas_sin_relacion = Nota.objects.filter(
            tipoArticulo='INSCRIPCION'
        ).exclude(
            idNota__in=NotaRelacionada.objects.values('idNota')
        )
        
        correcciones = []
        for nota in notas_sin_relacion:
            # Buscar inscripciones relacionadas con esta persona
            inscripciones = Inscripcion.objects.filter(
                idPersona=nota.idPersona,
                is_active=True
            )
            
            for inscripcion in inscripciones:
                # Crear la relación
                relacion = NotaRelacionada.objects.create(
                    idNota=nota,
                    idInscripcion=inscripcion
                )
                correcciones.append({
                    'nota_id': nota.idNota,
                    'nota_numero': nota.numeroNota,
                    'inscripcion_id': inscripcion.idInscripcion,
                    'formacion': inscripcion.idFormacion.nombreFormacion if inscripcion.idFormacion else 'Sin formación'
                })
                print(f"✅ Relación creada: Nota {nota.numeroNota} -> Inscripción {inscripcion.idInscripcion}")
                break  # Solo una relación por nota
        
        return Response({
            'success': True,
            'message': f'Se crearon {len(correcciones)} relaciones',
            'correcciones': correcciones
        })
        
    except Exception as e:
        return Response({
            'success': False,
            'message': f'Error: {str(e)}'
        }, status=500)


@api_view(['GET'])
def notas_por_cedula(request):
    """
    Obtener notas por cédula (para el dashboard)
    """
    try:
        cedula = request.GET.get('cedula', '').strip()
        if not cedula:
            return Response({
                'success': False,
                'message': 'Cédula requerida'
            }, status=400)

        print(f"🔍 [NOTAS] Buscando notas para cédula: {cedula}")

        # Buscar persona por cédula (más flexible)
        personas = Personas.objects.filter(
            cedula__icontains=cedula
        )
        
        if not personas.exists():
            print(f"❌ [NOTAS] No se encontró persona con cédula: {cedula}")
            return Response({
                'success': True,
                'data': [],
                'total': 0,
                'message': 'No se encontraron notas'
            })

        persona = personas.first()
        print(f"✅ [NOTAS] Persona encontrada: {persona.idPersona} - {persona.cedula}")

        # Obtener TODAS las notas de esta persona
        notas = Nota.objects.filter(idPersona=persona.idPersona).order_by('-fechaEmision')
        print(f"📝 [NOTAS] Notas encontradas en BD: {notas.count()}")

        notas_data = []
        for nota in notas:
            print(f"📋 [NOTAS] Procesando nota {nota.idNota} - Estado: {nota.estado}")
            
            # Obtener información de la formación/cohorte desde las relaciones
            formacion_info = "Formación no especificada"
            cohorte_info = "Cohorte no especificada"
            relacion_data = None
            
            try:
                # Buscar en NotaRelacionada
                relacion = NotaRelacionada.objects.filter(idNota=nota).first()
                if relacion:
                    print(f"🔗 [NOTAS] Relación encontrada para nota {nota.idNota}")
                    
                    if relacion.idInscripcion:
                        inscripcion = relacion.idInscripcion
                        print(f"📚 [NOTAS] Inscripción relacionada: {inscripcion.idInscripcion}")
                        
                        if inscripcion.idCohorte:
                            cohorte_info = inscripcion.idCohorte.nombreCohorte or "Cohorte"
                            if inscripcion.idCohorte.idFormacion:
                                formacion_info = inscripcion.idCohorte.idFormacion.nombreFormacion or "Formación"
                        
                        # Construir datos de relación para el frontend
                        relacion_data = {
                            'idInscripcion': {
                                'idInscripcion': inscripcion.idInscripcion,
                                'idCohorte': {
                                    'idCohorte': inscripcion.idCohorte.idCohorte if inscripcion.idCohorte else None,
                                    'nombreCohorte': cohorte_info
                                } if inscripcion.idCohorte else None
                            }
                        }
                    else:
                        print(f"⚠️ [NOTAS] Relación sin inscripción para nota {nota.idNota}")
                else:
                    print(f"⚠️ [NOTAS] No hay relación para nota {nota.idNota}")
                    
            except Exception as e:
                print(f"❌ [NOTAS] Error obteniendo relación para nota {nota.idNota}: {str(e)}")
                import traceback
                print(f"📋 [NOTAS] Traceback: {traceback.format_exc()}")

            # Construir objeto de nota
            nota_obj = {
                'idNota': nota.idNota,
                'numeroNota': nota.numeroNota,
                'fechaEmision': nota.fechaEmision.isoformat() if nota.fechaEmision else None,
                'totalNota': float(nota.totalNota) if nota.totalNota else 0.0,
                'estado': nota.estado or 'PENDIENTE',
                'tipoOperacion': nota.tipoOperacion or 'COBRO',
                'tipoArticulo': nota.tipoArticulo or 'INSCRIPCION',
                'descripcion': f"{nota.tipoArticulo} - {formacion_info}",
                'formacion': {
                    'nombreFormacion': formacion_info
                },
                'cohorte': cohorte_info,
                'persona': {
                    'idPersona': persona.idPersona,
                    'cedula': persona.cedula,
                    'nombre': f"{persona.nombres} {persona.apellidos}"
                }
            }
            
            # Solo agregar relaciones si existen
            if relacion_data:
                nota_obj['relaciones'] = [relacion_data]
            
            notas_data.append(nota_obj)
            print(f"✅ [NOTAS] Nota {nota.idNota} procesada")

        print(f"✅ [NOTAS] Total de notas procesadas: {len(notas_data)}")
        return Response({
            'success': True,
            'data': notas_data,
            'total': len(notas_data),
            'persona_info': {
                'idPersona': persona.idPersona,
                'nombre': f"{persona.nombres} {persona.apellidos}",
                'cedula': persona.cedula
            }
        })

    except Exception as e:
        print(f"❌ [NOTAS] Error crítico en notas_por_cedula: {str(e)}")
        import traceback
        print(f"📋 [NOTAS] Traceback completo: {traceback.format_exc()}")
        return Response({
            'success': False,
            'message': f'Error interno del servidor: {str(e)}'
        }, status=500)

@api_view(['GET'])
def diagnosticar_notas(request):
    """
    Endpoint simple para diagnosticar problemas con notas
    """
    try:
        print("🔍 [DIAGNOSTICO] Iniciando diagnóstico...")
        
        # 1. Verificar si hay personas
        total_personas = Personas.objects.count()
        print(f"✅ [DIAGNOSTICO] Total personas: {total_personas}")
        
        # 2. Verificar si hay notas
        total_notas = Nota.objects.count()
        print(f"✅ [DIAGNOSTICO] Total notas: {total_notas}")
        
        # 3. Verificar si hay relaciones
        total_relaciones = NotaRelacionada.objects.count()
        print(f"✅ [DIAGNOSTICO] Total relaciones: {total_relaciones}")
        
        # 4. Probar con una persona específica
        persona_test = Personas.objects.filter(cedula__icontains="30895206").first()
        if persona_test:
            print(f"✅ [DIAGNOSTICO] Persona test encontrada: {persona_test.idPersona}")
            notas_persona = Nota.objects.filter(idPersona=persona_test.idPersona).count()
            print(f"✅ [DIAGNOSTICO] Notas de persona test: {notas_persona}")
        else:
            print("❌ [DIAGNOSTICO] No se encontró persona test")
        
        return Response({
            'success': True,
            'diagnostico': {
                'total_personas': total_personas,
                'total_notas': total_notas,
                'total_relaciones': total_relaciones,
                'persona_test_encontrada': bool(persona_test),
                'notas_persona_test': notas_persona if persona_test else 0
            }
        })
        
    except Exception as e:
        print(f"❌ [DIAGNOSTICO] Error crítico: {str(e)}")
        import traceback
        print(f"📋 [DIAGNOSTICO] Traceback: {traceback.format_exc()}")
        return Response({
            'success': False,
            'error': str(e)
        }, status=500)