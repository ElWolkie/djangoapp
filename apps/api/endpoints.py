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

from apps.persona.serializers import PersonaCreateSerializer
from rest_framework.authentication import SessionAuthentication
from apps.persona.serializers import PersonaCreateSerializer, UsuarioCreateSerializer

from apps.asientoContable.models import AsientoContable, DetalleAsiento
from apps.periodoContable.models import periodoContable
from django.db import transaction
from apps.inscripcion.models import Inscripcion
from apps.factura.models import Nota, NotaRelacionada, Pago, PlanArticulo, ParametroTributario
from apps.home.models import Tasa, Configuracion
from apps.factura.templatetags.decimal_filters import to_decimal
from django.utils.timezone import now
import uuid
from decimal import Decimal, InvalidOperation

from core import settings

logger = logging.getLogger(__name__)


class PersonaPublicRegisterView(APIView):
    authentication_classes = [] # Le dice a DRF: "No intentes autenticar esta petición".
    permission_classes = [AllowAny]   # Le dice a DRF: "Cualquiera tiene permiso para acceder".

    def post(self, request, *args, **kwargs):
        # ... el resto de tu función post se queda exactamente igual
        logger.info(f"📥 Datos recibidos para registro de persona: {request.data}")
        
        serializer = PersonaCreateSerializer(data=request.data)
        
        if serializer.is_valid():
            try:
                # El método .save() llamará internamente a nuestro método create() en el serializer
                persona_creada = serializer.save()
                
                # Preparamos la respuesta usando los datos del serializer post-creación
                # El serializer automáticamente convierte el objeto 'persona_creada' a JSON
                response_data = serializer.data
                response_data['mensaje'] = 'Persona registrada exitosamente'
                
                logger.info(f"📤 Enviando respuesta exitosa: {response_data}")
                return Response(response_data, status=status.HTTP_201_CREATED)
                
            except Exception as e:
                logger.error(f"❌ Error interno durante la creación de la persona: {str(e)}", exc_info=True)
                return Response({
                    'error': 'Ocurrió un error inesperado al guardar los datos.',
                    'codigo': 'ERROR_INTERNO'
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        else:
            # Si los datos no son válidos, el serializer.errors contendrá los detalles
            logger.warning(f"⚠️ Datos de registro inválidos: {serializer.errors}")
            return Response({
                'error': 'Datos inválidos. Por favor, revisa los campos.',
                'detalles': serializer.errors,
                'codigo': 'VALIDATION_ERROR'
            }, status=status.HTTP_400_BAD_REQUEST)


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
                'message': 'Inscripcion no encontrada.'
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            inscripcion = Inscripcion.objects.filter(idInscripcion=id_inscripcion, is_active=True).select_related('idFormacion').first()
            if not inscripcion:
                return Response({
                    'success': False,
                    'message': 'No se encontró una inscripción activa con el ID proporcionado.'
                }, status=status.HTTP_404_NOT_FOUND)

            configuracion = Configuracion.objects.first()
            if not configuracion:
                return Response({
                    'success': False,
                    'message': 'No se encontró una configuración activa en el sistema.'
                }, status=status.HTTP_400_BAD_REQUEST)

            moneda_configuracion = configuracion.moneda
            tasa_configuracion = Tasa.objects.filter(idMoneda=moneda_configuracion).order_by('-idTasa').first()
            if not tasa_configuracion:
                return Response({
                    'success': False,
                    'message': f'No se encontró una tasa registrada para la moneda de configuración ({moneda_configuracion.nombreMoneda}).'
                }, status=status.HTTP_400_BAD_REQUEST)

            tasa_configuracion_valor = to_decimal(tasa_configuracion.montoTasa)
            numero_nota = generar_numero_nota()

            # Verificar si hay un periodo contable activo
            periodo_activo = periodoContable.objects.filter(estadoPeriodo=True).first()
            if not periodo_activo:
                periodo_activo = periodoContable.objects.order_by('-idPeriodo').first()
            if not periodo_activo:
                return Response({
                    'success': False,
                    'message': 'No hay ningún periodo contable registrado o activo en el sistema. Por favor, registre o active un periodo contable antes de continuar.'
                }, status=status.HTTP_400_BAD_REQUEST)

            # Obtener el valor de la inscripción desde la formación asociada
            valor_inscripcion = inscripcion.idFormacion.valorInscripcion

            # Verificar si la persona está relacionada con TipoPersona id=3
            persona = inscripcion.idPersona
            tiene_descuento = PersonaTP.objects.filter(idPersona=persona, idTP=3).exists()

            # Calcular montos
            subtotal_gravado = Decimal('0.00')
            subtotal_exento = Decimal('0')

            # Obtener parámetros tributarios
            parametros_tributarios = ParametroTributario.objects.filter(activo=True)

            def obtener_parametro(tipo, aplica_a):
                return parametros_tributarios.filter(tipo=tipo, aplica_a=aplica_a).first()

            # Calcular IVA respetando exenciones
            parametro_iva_exento = obtener_parametro('IVA_EXENTO', 'INSCRIPCION')
            if parametro_iva_exento and parametro_iva_exento.porcentaje == Decimal('0.00'):
                subtotal_exento = valor_inscripcion
                subtotal_gravado = Decimal('0.00')
                iva = Decimal('0.00')  # No aplica IVA si es exento
            else:
                subtotal_gravado = valor_inscripcion
                subtotal_exento = Decimal('0.00')
                parametro_iva = obtener_parametro('IVA_GENERAL', 'INSCRIPCION')
                porcentaje_iva = parametro_iva.porcentaje if parametro_iva else Decimal('16')
                iva = subtotal_gravado * (porcentaje_iva / Decimal('100'))

            # Calcular retenciones (si aplica)
            iva_retenido = Decimal('0.00')
            islr_retenido = Decimal('0.00')

            # Calcular descuento
            descuento = Decimal('0')
            if tiene_descuento:
                descuento = (subtotal_gravado + subtotal_exento) * (to_decimal(configuracion.descuento) / Decimal('100'))

            # Calcular total
            total_nota = subtotal_gravado + subtotal_exento + iva - descuento

            # El idPersona se obtiene del registro de inscripción
            persona = inscripcion.idPersona

             # Crear el asiento contable
            asiento = AsientoContable.objects.create(
                numeroAsiento=f"NOTA-{numero_nota}",
                fechaAsiento=now().date(),
                conceptoAsiento=f"Asiento para la nota {numero_nota}",
                idPeriodo=periodo_activo
            )
            asiento.save()
            # Crear la nota de cobro
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

            # Crear la relación en NotaRelacionada si se proporciona idInscripcion
            id_inscripcion = request.POST.get('idInscripcion')
            if id_inscripcion:
                inscripcion = Inscripcion.objects.filter(idInscripcion=id_inscripcion).first()
                if inscripcion:
                    NotaRelacionada.objects.create(
                        idNota=nota,
                        idInscripcion=inscripcion
                    )
                    inscripcion.estadoPago = 'PENDIENTE'
                    inscripcion.save()
                else:
                    print("No se encontró una inscripción con el ID proporcionado.")
            else:
                print("ID Inscripcion no proporcionado en el formulario.")

            # Crear los detalles del asiento contable
            plan_articulos = PlanArticulo.objects.filter(tipoArticulo='INSCRIPCION').order_by('-fecha')
            plan_articulo_debe = plan_articulos.filter(tipo=1).first()
            plan_articulo_haber = plan_articulos.filter(tipo=0).first()

            if not plan_articulo_debe or not plan_articulo_haber:
                return Response({
                    'success': False,
                    'message': 'No se encontraron cuentas contables válidas para el tipo de artículo seleccionado.'
                }, status=status.HTTP_400_BAD_REQUEST)

            # Crear los detalles del asiento contable usando los registros encontrados
            DetalleAsiento.objects.create(
                idAsiento=asiento,
                idPlanCuenta=plan_articulo_debe.idPlanCuenta,
                debe=to_decimal(nota.totalNota),
                haber=Decimal('0.00')
            )
            DetalleAsiento.objects.create(
                idAsiento=asiento,
                idPlanCuenta=plan_articulo_haber.idPlanCuenta,
                debe=Decimal('0.00'),
                haber=to_decimal(nota.totalNota)
            )

            inscripcion.estadoPago = 'PENDIENTE'
            inscripcion.save()

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
                        'nombre': f"{persona.nombre} {persona.apellido}"
                    },
                    'formacion': {
                        'idFormacion': inscripcion.idFormacion.idFormacion,
                        'nombreFormacion': inscripcion.idFormacion.nombreFormacion
                    }
                }
            }, status=status.HTTP_201_CREATED)

        except Exception as e:
            return Response({
                'success': False,
                'message': f'Ocurrió un error inesperado: {str(e)}.'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
def generar_numero_nota():
    # Generar un número único basado en la fecha y un UUID
    fecha_actual = now().strftime('%Y%m%d')  # Formato: YYYYMMDD
    numero_unico = uuid.uuid4().hex[:6].upper()  # Tomar los primeros 6 caracteres del UUID
    return f"NOTA-{fecha_actual}-{numero_unico}"

# En tu archivo de vistas (endpoints.py o views.py)
@api_view(['GET'])
def notas_por_usuario_autenticado(request):
    """
    Obtener notas del usuario autenticado - VERSIÓN ROBUSTA
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
            # Obtener información de formación - ENFOQUE DIRECTO Y ROBUSTO
            formacion_nombre = "Formación no especificada"
            
            # Método 1: Buscar directamente en NotaRelacionada
            try:
                relacion = NotaRelacionada.objects.filter(idNota=nota).first()
                if relacion:
                    print(f"🔍 Relación encontrada para nota {nota.idNota}")
                    
                    # Intentar obtener desde inscripción
                    if relacion.idInscripcion:
                        print(f"📚 Tiene inscripción: {relacion.idInscripcion.idInscripcion}")
                        if relacion.idInscripcion.idFormacion:
                            formacion_nombre = relacion.idInscripcion.idFormacion.nombreFormacion
                            print(f"✅ Formación desde inscripción: {formacion_nombre}")
                    
                    # Intentar obtener desde cuota
                    elif relacion.idCuota:
                        print(f"💰 Tiene cuota: {relacion.idCuota.idCuota}")
                        if relacion.idCuota.idFormacion:
                            formacion_nombre = relacion.idCuota.idFormacion.nombreFormacion
                            print(f"✅ Formación desde cuota: {formacion_nombre}")
                    
                    # Intentar obtener desde solicitud
                    elif relacion.idSolicitud:
                        print(f"📋 Tiene solicitud: {relacion.idSolicitud.idSolicitud}")
                        if relacion.idSolicitud.idFormacion:
                            formacion_nombre = relacion.idSolicitud.idFormacion.nombreFormacion
                            print(f"✅ Formación desde solicitud: {formacion_nombre}")
                    
                else:
                    print(f"⚠️ No se encontró relación para nota {nota.idNota}")
                    
            except Exception as e:
                print(f"❌ Error obteniendo formación para nota {nota.idNota}: {str(e)}")
                import traceback
                print(f"📋 Traceback: {traceback.format_exc()}")

            notas_data.append({
                'idNota': nota.idNota,
                'numeroNota': nota.numeroNota,
                'fechaEmision': nota.fechaEmision.strftime('%Y-%m-%d') if nota.fechaEmision else None,
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
            'debug_info': {
                'persona_id': persona.idPersona,
                'total_notas': len(notas_data)
            }
        })

    except Exception as e:
        print(f"❌ Error en notas_por_usuario_autenticado: {str(e)}")
        import traceback
        print(f"📋 Traceback: {traceback.format_exc()}")
        return Response({
            'success': False,
            'message': f'Error obteniendo notas: {str(e)}'
        }, status=500)

class PagoCreateAPIView(APIView):
    @transaction.atomic
    def post(self, request):
        print("🚀 [PAGO-DEFINITIVO] Iniciando procesamiento...")
        
        # Variables para rollback
        asiento = None
        pago = None
        
        try:
            data = request.data
            print(f"📥 [PAGO-DEFINITIVO] Datos: {data}")
            
            # Validaciones básicas
            required_fields = ['idNota', 'formaPago', 'monto', 'fechaPago']
            for field in required_fields:
                if field not in data:
                    return Response({
                        'success': False,
                        'message': f'Campo requerido faltante: {field}'
                    }, status=status.HTTP_400_BAD_REQUEST)

            # ========== OBTENER NOTA ==========
            try:
                nota_id = int(data['idNota'])
                nota = Nota.objects.get(idNota=nota_id)
                print(f"✅ [PAGO-DEFINITIVO] Nota: {nota.numeroNota}")
            except (ValueError, TypeError, Nota.DoesNotExist):
                return Response({
                    'success': False,
                    'message': 'Nota no encontrada o ID inválido'
                }, status=status.HTTP_404_NOT_FOUND)

            if nota.estado == 'PAGADA':
                return Response({
                    'success': False,
                    'message': 'Esta nota ya ha sido pagada completamente'
                }, status=status.HTTP_400_BAD_REQUEST)

            # ========== VALIDAR MONTO ==========
            try:
                monto_pago = Decimal(str(data['monto']))
                if monto_pago <= 0:
                    return Response({
                        'success': False,
                        'message': 'El monto debe ser mayor a 0'
                    }, status=status.HTTP_400_BAD_REQUEST)
                
                if monto_pago > nota.totalNota:
                    return Response({
                        'success': False,
                        'message': f'El monto no puede ser mayor al total de la nota (${nota.totalNota})'
                    }, status=status.HTTP_400_BAD_REQUEST)
            except (ValueError, TypeError, InvalidOperation):
                return Response({
                    'success': False,
                    'message': 'Monto inválido'
                }, status=status.HTTP_400_BAD_REQUEST)

            # ========== CONFIGURACIONES ==========
            periodo_activo = periodoContable.objects.filter(estadoPeriodo=True).first()
            if not periodo_activo:
                periodo_activo = periodoContable.objects.order_by('-idPeriodo').first()
                if not periodo_activo:
                    return Response({
                        'success': False,
                        'message': 'No hay periodos contables configurados'
                    }, status=status.HTTP_400_BAD_REQUEST)

            # Usar tasa específica (ID 4 que se creó)
            tasa = Tasa.objects.filter(idTasa=4).first()
            if not tasa:
                return Response({
                    'success': False,
                    'message': 'No se encontró la tasa configurada'
                }, status=status.HTTP_400_BAD_REQUEST)

            # ========== CREAR ASIENTO CONTABLE ==========
            try:
                numero_asiento = f"PAGO-{now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
                
                asiento = AsientoContable.objects.create(
                    numeroAsiento=numero_asiento,
                    fechaAsiento=now().date(),
                    conceptoAsiento=f"Pago de {data['formaPago']} - Nota: {nota.numeroNota}",
                    idPeriodo=periodo_activo
                )
                print(f"✅ [PAGO-DEFINITIVO] Asiento: {asiento.numeroAsiento}")
            except Exception as e:
                print(f"❌ [PAGO-DEFINITIVO] Error asiento: {str(e)}")
                return Response({
                    'success': False,
                    'message': f'Error creando asiento contable: {str(e)}'
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            # ========== CREAR PAGO - PUNTO CRÍTICO ==========
            print("💰 [PAGO-DEFINITIVO] Creando registro de pago...")
            try:
                # IMPORTAR DIRECTAMENTE el modelo Pago
                from apps.factura.models import Pago
                
                # Preparar datos EXACTAMENTE como espera el modelo
                pago_data = {
                    'idNota_id': nota.idNota,  # Usar _id para ForeignKey
                    'idAsiento_id': asiento.idAsiento,
                    'idTasa_id': tasa.idTasa,
                    'formaPago': data['formaPago'],
                    'monto': monto_pago,
                    'fechaPago': data['fechaPago'],
                    'referencia': data.get('referencia', ''),
                    'observaciones': data.get('observaciones', ''),
                    # idCuentaBanco_id se deja como NULL (no se incluye)
                }
                
                print(f"📝 [PAGO-DEFINITIVO] Datos para pago: {pago_data}")
                
                # CREAR EL PAGO usando create() con los datos preparados
                pago = Pago.objects.create(**pago_data)
                print(f"🎉 [PAGO-DEFINITIVO] PAGO CREADO: ID {pago.idPago}")

            except Exception as e:
                print(f"💥 [PAGO-DEFINITIVO] ERROR creando pago: {str(e)}")
                import traceback
                error_traceback = traceback.format_exc()
                print(f"📋 [PAGO-DEFINITIVO] Traceback:\n{error_traceback}")
                
                # Revertir asiento
                if asiento:
                    asiento.delete()
                    print("✅ [PAGO-DEFINITIVO] Asiento revertido")
                
                return Response({
                    'success': False,
                    'message': f'Error crítico al crear el pago: {str(e)}',
                    'error_type': type(e).__name__,
                    'error_details': str(e),
                    'debug_info': 'Verifique la estructura del modelo Pago en la base de datos'
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            # ========== ACTUALIZAR ESTADOS ==========
            nuevo_estado = 'PENDIENTE'
            try:
                if monto_pago >= nota.totalNota:
                    nota.estado = 'PAGADA'
                    nuevo_estado = 'PAGADA'
                else:
                    nota.estado = 'PARCIAL'
                    nuevo_estado = 'PARCIAL'
                
                nota.save()
                print(f"✅ [PAGO-DEFINITIVO] Nota actualizada: {nuevo_estado}")

                # Actualizar inscripción relacionada
                try:
                    relacion = NotaRelacionada.objects.filter(idNota=nota).first()
                    if relacion and relacion.idInscripcion:
                        inscripcion = relacion.idInscripcion
                        if monto_pago >= nota.totalNota:
                            inscripcion.estadoPago = 'PAGADO'
                        else:
                            inscripcion.estadoPago = 'PARCIAL'
                        inscripcion.save()
                        print(f"✅ [PAGO-DEFINITIVO] Inscripción actualizada")
                except Exception as e:
                    print(f"⚠️ [PAGO-DEFINITIVO] Error inscripción: {str(e)}")

            except Exception as e:
                print(f"⚠️ [PAGO-DEFINITIVO] Error actualizando estados: {str(e)}")

            # ========== RESPUESTA EXITOSA ==========
            response_data = {
                'success': True,
                'message': '¡Pago procesado exitosamente! 🎉',
                'data': {
                    'idPago': pago.idPago,
                    'numeroPago': numero_asiento,
                    'monto': float(pago.monto),
                    'fechaPago': pago.fechaPago.isoformat(),
                    'formaPago': pago.formaPago,
                    'referencia': pago.referencia,
                    'nota': {
                        'idNota': nota.idNota,
                        'numeroNota': nota.numeroNota,
                        'nuevoEstado': nuevo_estado,
                        'totalNota': float(nota.totalNota)
                    }
                }
            }

            print(f"🎊 [PAGO-DEFINITIVO] PROCESO COMPLETADO EXITOSAMENTE")
            return Response(response_data, status=status.HTTP_201_CREATED)

        except Exception as e:
            print(f"💣 [PAGO-DEFINITIVO] ERROR GENERAL: {str(e)}")
            import traceback
            print(f"📋 [PAGO-DEFINITIVO] Traceback:\n{traceback.format_exc()}")
            
            # Limpiar recursos
            if asiento and not pago:
                asiento.delete()
            
            return Response({
                'success': False,
                'message': 'Error interno del servidor',
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# Endpoint de diagnóstico para ver relaciones de notas
@api_view(['GET'])
def debug_nota_relaciones(request, id_nota):
    """
    Endpoint para diagnosticar las relaciones de una nota específica
    """
    try:
        nota = Nota.objects.get(idNota=id_nota)
        
        relaciones = NotaRelacionada.objects.filter(idNota=nota)
        
        debug_info = {
            'nota': {
                'idNota': nota.idNota,
                'numeroNota': nota.numeroNota,
                'tipoArticulo': nota.tipoArticulo,
                'estado': nota.estado,
            },
            'relaciones_count': relaciones.count(),
            'relaciones': []
        }
        
        for rel in relaciones:
            relacion_info = {
                'id_relacion': rel.id,
                'tiene_inscripcion': bool(rel.idInscripcion),
                'tiene_cuota': bool(rel.idCuota),
                'tiene_solicitud': bool(rel.idSolicitud),
            }
            
            if rel.idInscripcion:
                relacion_info['inscripcion'] = {
                    'id': rel.idInscripcion.idInscripcion,
                    'tiene_formacion': bool(rel.idInscripcion.idFormacion),
                    'formacion_nombre': rel.idInscripcion.idFormacion.nombreFormacion if rel.idInscripcion.idFormacion else None,
                    'estado_pago': rel.idInscripcion.estadoPago
                }
            
            if rel.idCuota:
                relacion_info['cuota'] = {
                    'id': rel.idCuota.idCuota,
                    'tiene_formacion': bool(rel.idCuota.idFormacion),
                    'formacion_nombre': rel.idCuota.idFormacion.nombreFormacion if rel.idCuota.idFormacion else None
                }
            
            if rel.idSolicitud:
                relacion_info['solicitud'] = {
                    'id': rel.idSolicitud.idSolicitud,
                    'tiene_formacion': bool(rel.idSolicitud.idFormacion),
                    'formacion_nombre': rel.idSolicitud.idFormacion.nombreFormacion if rel.idSolicitud.idFormacion else None
                }
            
            debug_info['relaciones'].append(relacion_info)
        
        return Response(debug_info)
        
    except Exception as e:
        return Response({'error': str(e)}, status=500)

# Crea un script temporal para corregir las relaciones de notas
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

@api_view(['POST'])
def verificar_estado_sistema(request):
    """
    Verificar el estado de todos los componentes del sistema necesarios para pagos
    """
    try:
        verificaciones = {
            'periodos_contables': periodoContable.objects.count(),
            'tasas_activas': Tasa.objects.filter(estadoTasa=True).count(),
            'monedas_base': Moneda.objects.filter(idMoneda=1).count(),
            'planes_cuenta': PlanArticulo.objects.filter(tipoArticulo='INSCRIPCION').count(),
            'notas_pendientes': Nota.objects.filter(estado__in=['PENDIENTE', 'PARCIAL']).count(),
        }
        
        # Verificar que exista al menos un periodo contable
        if verificaciones['periodos_contables'] == 0:
            # Crear periodo contable por defecto
            periodo = periodoContable.objects.create(
                descripcionPeriodo="Periodo Automático",
                fechaInicio=now().date(),
                fechaFin=now().date() + timedelta(days=365),
                estadoPeriodo=True
            )
            verificaciones['periodo_creado'] = periodo.idPeriodo
        
        # Verificar que exista tasa base
        if verificaciones['tasas_activas'] == 0:
            moneda_base = Moneda.objects.filter(idMoneda=1).first()
            if not moneda_base:
                moneda_base = Moneda.objects.create(
                    nombreMoneda="Bolívar",
                    simboloMoneda="Bs",
                    estadoMoneda=True
                )
            
            tasa = Tasa.objects.create(
                idMoneda=moneda_base,
                montoTasa=1.00,
                fechaTasa=now().date(),
                estadoTasa=True
            )
            verificaciones['tasa_creada'] = tasa.idTasa
        
        return Response({
            'success': True,
            'message': 'Estado del sistema verificado',
            'verificaciones': verificaciones
        })
        
    except Exception as e:
        return Response({
            'success': False,
            'message': f'Error verificando sistema: {str(e)}'
        }, status=500)

@api_view(['POST'])
def test_pago_simple(request):
    """
    Endpoint de prueba MUY simple para pagos
    """
    try:
        print("🧪 [TEST] Endpoint de prueba llamado")
        
        # Solo validar datos básicos
        data = request.data
        required = ['idNota', 'monto']
        
        for field in required:
            if field not in data:
                return Response({
                    'success': False,
                    'message': f'Falta: {field}'
                }, status=400)
        
        # Simular éxito
        return Response({
            'success': True,
            'message': '✅ Prueba exitosa - El endpoint funciona',
            'data_received': data
        })
        
    except Exception as e:
        return Response({
            'success': False,
            'message': f'Error en prueba: {str(e)}'
        }, status=500)

@api_view(['GET'])
def diagnostico_modelo_pago(request):
    """
    Diagnóstico específico del modelo Pago
    """
    try:
        from django.apps import apps
        from django.db import connection
        
        diagnostico = {
            'import_directo': {},
            'via_apps': {},
            'tabla_bd': {},
            'campos_modelo': {}
        }
        
        # 1. Intentar importar directamente
        try:
            from apps.factura.models import Pago
            diagnostico['import_directo'] = {
                'exito': True,
                'modelo': str(Pago),
                'app_label': Pago._meta.app_label,
                'db_table': Pago._meta.db_table
            }
            
            # Verificar campos
            campos = []
            for field in Pago._meta.fields:
                campo_info = {
                    'name': field.name,
                    'type': type(field).__name__,
                    'null': field.null,
                    'blank': field.blank,
                    'default': field.default if field.has_default() else 'NO DEFAULT'
                }
                campos.append(campo_info)
            
            diagnostico['campos_modelo'] = campos
            
            # Intentar contar registros
            try:
                count = Pago.objects.count()
                diagnostico['import_directo']['registros_count'] = count
            except Exception as e:
                diagnostico['import_directo']['error_count'] = str(e)
                
        except Exception as e:
            diagnostico['import_directo'] = {
                'exito': False,
                'error': str(e)
            }
        
        # 2. Verificar via apps
        try:
            modelo = apps.get_model('factura', 'Pago')
            diagnostico['via_apps'] = {
                'exito': True,
                'modelo': str(modelo)
            }
        except Exception as e:
            diagnostico['via_apps'] = {
                'exito': False,
                'error': str(e)
            }
        
        # 3. Verificar tabla en BD
        try:
            with connection.cursor() as cursor:
                # Verificar si la tabla existe
                cursor.execute("""
                    SELECT table_name 
                    FROM information_schema.tables 
                    WHERE table_name = 'factura_pago'
                """)
                tabla_existe = cursor.fetchone() is not None
                
                diagnostico['tabla_bd'] = {
                    'existe': tabla_existe,
                    'nombre_tabla': 'factura_pago'
                }
                
                if tabla_existe:
                    # Obtener estructura de la tabla
                    cursor.execute("""
                        SELECT column_name, data_type, is_nullable, column_default
                        FROM information_schema.columns 
                        WHERE table_name = 'factura_pago'
                        ORDER BY ordinal_position
                    """)
                    columnas = cursor.fetchall()
                    diagnostico['tabla_bd']['columnas'] = [
                        {
                            'name': col[0],
                            'type': col[1],
                            'nullable': col[2] == 'YES',
                            'default': col[3]
                        } for col in columnas
                    ]
                    
        except Exception as e:
            diagnostico['tabla_bd'] = {
                'error': str(e)
            }
        
        return Response({
            'success': True,
            'diagnostico': diagnostico
        })
        
    except Exception as e:
        return Response({
            'success': False,
            'message': f'Error en diagnóstico: {str(e)}'
        }, status=500)