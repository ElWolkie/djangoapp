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

class PagoCreateAPIView(APIView):
    @transaction.atomic
    def post(self, request):
        try:
            data = request.data
            print(f"📥 Datos recibidos: {data}")
            
            # Validar datos requeridos
            required_fields = ['idNota', 'formaPago', 'monto', 'fechaPago']
            for field in required_fields:
                if field not in data:
                    return Response({
                        'success': False,
                        'message': f'Campo requerido faltante: {field}'
                    }, status=status.HTTP_400_BAD_REQUEST)

            # Obtener y validar nota
            try:
                nota = Nota.objects.get(idNota=data['idNota'])
                print(f"✅ Nota encontrada: {nota.numeroNota} - Estado: {nota.estado}")
            except Nota.DoesNotExist:
                return Response({
                    'success': False,
                    'message': 'Nota no encontrada'
                }, status=status.HTTP_404_NOT_FOUND)

            if nota.estado == 'PAGADA':
                return Response({
                    'success': False,
                    'message': 'Esta nota ya ha sido pagada completamente'
                }, status=status.HTTP_400_BAD_REQUEST)

            # Validar monto
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
            except (ValueError, InvalidOperation):
                return Response({
                    'success': False,
                    'message': 'Formato de monto inválido'
                }, status=status.HTTP_400_BAD_REQUEST)

            # 🔥 CORRECCIÓN: Obtener tasa de la configuración, no moneda base
            configuracion = Configuracion.objects.first()
            if not configuracion:
                return Response({
                    'success': False,
                    'message': 'Configuración del sistema no encontrada'
                }, status=status.HTTP_400_BAD_REQUEST)

            moneda_configuracion = configuracion.moneda
            tasa = Tasa.objects.filter(idMoneda=moneda_configuracion).order_by('-idTasa').first()
            
            if not tasa:
                return Response({
                    'success': False,
                    'message': f'No se encontró tasa para la moneda de configuración ({moneda_configuracion.nombreMoneda})'
                }, status=status.HTTP_400_BAD_REQUEST)

            print(f"✅ Tasa encontrada: {tasa.idTasa} - {tasa.montoTasa}")

            # Obtener periodo contable activo
            periodo_activo = periodoContable.objects.filter(estadoPeriodo=True).first()
            if not periodo_activo:
                return Response({
                    'success': False,
                    'message': 'No hay periodo contable activo'
                }, status=status.HTTP_400_BAD_REQUEST)

            print(f"✅ Periodo activo: {periodo_activo.nombrePeriodo}")

            # 🔥 CORRECCIÓN: Crear asiento contable con número único
            numero_asiento = f"PAGO-{now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
            
            asiento = AsientoContable.objects.create(
                numeroAsiento=numero_asiento,
                fechaAsiento=now().date(),
                conceptoAsiento=f"Pago de {data['formaPago']} - Nota: {nota.numeroNota}",
                idPeriodo=periodo_activo
            )
            print(f"✅ Asiento contable creado: {asiento.idAsiento}")

            # 🔥 CORRECCIÓN: Crear pago según el modelo REAL
            pago = Pago.objects.create(
                idNota=nota,
                idAsiento=asiento,
                idTasa=tasa,
                # idCuentaBanco se deja null por ahora (no viene del frontend)
                monto=monto_pago,
                fechaPago=data['fechaPago'],
                formaPago=data['formaPago'],
                referencia=data.get('referencia', ''),
                observaciones=data.get('observaciones', '')
                # fechaRegistro se auto-genera
            )
            print(f"✅ Pago creado: {pago.idPago}")

            # Actualizar estado de la nota
            if monto_pago >= nota.totalNota:
                nota.estado = 'PAGADA'
                print(f"✅ Nota marcada como PAGADA")
            else:
                nota.estado = 'PARCIAL'
                print(f"✅ Nota marcada como PARCIAL")
            
            nota.save()

            # Actualizar estado de la inscripción relacionada si existe
            try:
                nota_relacionada = NotaRelacionada.objects.filter(idNota=nota).first()
                if nota_relacionada and nota_relacionada.idInscripcion:
                    inscripcion = nota_relacionada.idInscripcion
                    if monto_pago >= nota.totalNota:
                        inscripcion.estadoPago = 'PAGADO'
                    else:
                        inscripcion.estadoPago = 'PARCIAL'
                    inscripcion.save()
                    print(f"✅ Inscripción actualizada: {inscripcion.idInscripcion}")
            except Exception as e:
                print(f"⚠️ No se pudo actualizar inscripción: {str(e)}")

            # 🔥 CORRECCIÓN: Crear detalles del asiento contable
            try:
                # Buscar cuentas contables para el tipo de artículo
                plan_articulo_debe = PlanArticulo.objects.filter(
                    tipoArticulo=nota.tipoArticulo,
                    tipo=1  # DEBE
                ).order_by('-fecha').first()
                
                plan_articulo_haber = PlanArticulo.objects.filter(
                    tipoArticulo=nota.tipoArticulo, 
                    tipo=0  # HABER
                ).order_by('-fecha').first()

                if plan_articulo_debe and plan_articulo_haber:
                    DetalleAsiento.objects.create(
                        idAsiento=asiento,
                        idPlanCuenta=plan_articulo_debe.idPlanCuenta,
                        debe=monto_pago,
                        haber=Decimal('0.00')
                    )
                    DetalleAsiento.objects.create(
                        idAsiento=asiento,
                        idPlanCuenta=plan_articulo_haber.idPlanCuenta,
                        debe=Decimal('0.00'),
                        haber=monto_pago
                    )
                    print(f"✅ Detalles de asiento creados")
                else:
                    print(f"⚠️ No se encontraron cuentas contables para {nota.tipoArticulo}")
            except Exception as e:
                print(f"⚠️ Error creando detalles de asiento: {str(e)}")

            # Respuesta exitosa
            response_data = {
                'success': True,
                'message': '¡Pago procesado exitosamente! 🎉',
                'data': {
                    'idPago': pago.idPago,
                    'numeroAsiento': asiento.numeroAsiento,  # Usar número de asiento como referencia
                    'monto': float(pago.monto),
                    'fechaPago': pago.fechaPago.isoformat(),
                    'formaPago': pago.formaPago,
                    'referencia': pago.referencia,
                    'nota': {
                        'idNota': nota.idNota,
                        'numeroNota': nota.numeroNota,
                        'nuevoEstado': nota.estado,
                        'totalNota': float(nota.totalNota)
                    }
                }
            }
            
            print("🎊 Pago procesado exitosamente!")
            return Response(response_data, status=status.HTTP_201_CREATED)

        except Exception as e:
            print(f"💥 Error en PagoCreateAPIView: {str(e)}")
            import traceback
            print(f"📋 Traceback: {traceback.format_exc()}")
            
            return Response({
                'success': False,
                'message': f'Error procesando pago: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def generar_numero_pago(self):
        # CORREGIDO: usar now() en lugar de timezone.now()
        fecha_actual = now().strftime('%Y%m%d')
        numero_unico = uuid.uuid4().hex[:6].upper()
        return f"PAGO-{fecha_actual}-{numero_unico}"

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
