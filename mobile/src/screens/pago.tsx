// src/screens/pago.tsx
import React, { useState, useEffect, useContext, useCallback } from 'react';
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  ScrollView,
  Alert,
  StyleSheet,
  FlatList,
  RefreshControl,
  KeyboardAvoidingView,
  Platform,
  useWindowDimensions,
  ActivityIndicator,
  Modal,
} from 'react-native';
import { useNavigation, useRoute } from '@react-navigation/native';
import Icon from 'react-native-vector-icons/MaterialCommunityIcons';
import api from '../api/api';
import { AuthContext } from '../contexts/AuthContext';

interface NotaItem {
  idNota?: number;
  numeroNota?: string;
  fechaEmision?: string;
  totalNota?: number;
  estado?: string;
  formacion?: any;
  idInscripcion?: number | null;
  idInscripcion_detail?: any;
  persona?: { nombre?: string; cedula?: string } | any;
  _resolvedFormacionName?: string | null;
  [k: string]: any;
}

interface Inscripcion {
  idInscripcion?: number;
  estadoPago?: string;
  fechaInscripcion?: string;
  idPersona?: number | string | null;
  idPersona_detail?: {
    cedula?: string;
    [k: string]: any;
  };
  idCohorte?: any;
  idCohorte_detail?: any;
  idFormacion_detail?: {
    idFormacion?: number;
    nombreFormacion?: string;
    valorInscripcion?: number | string;
    [k: string]: any;
  };
  montoPagado?: number;
  montoTotal?: number;
  saldoPendiente?: number;
  nombreFormacion?: string;
  [k: string]: any;
}

interface Configuracion {
  idConfig?: number;
  nombreInstitucion?: string;
  rif?: string;
  correoInstitucion?: string;
  idCuentaBanco?: number;
  cedulaCuenta?: string;
  nombre_banco?: string;
  numero_cuenta?: string;
  tipo_cuenta?: string;
}

interface Requisito {
  idRequisito: number;
  nombreRequisito: string;
  app: boolean; // Campo clave para el filtro
  estadoRequisito: string;
  fechaRequisito: string;
}

const PagoScreen: React.FC = () => {
  const navigation = useNavigation<any>();
  const route = useRoute<any>();
  const { user } = useContext(AuthContext);
  const { width } = useWindowDimensions();
  const { notaData } = route.params || {};

  const [refreshing, setRefreshing] = useState(false);
  const [configuracion, setConfiguracion] = useState<Configuracion | null>(null);
  const [loadingConfig, setLoadingConfig] = useState(false);

  const [requisitosData, setRequisitosData] = useState<Requisito[]>([]);
  const [loadingRequisitos, setLoadingRequisitos] = useState(false);

  const toBackendDecimal = (v: number | string) => {
    const n = Number(String(v).replace(',', '.')) || 0;
    return n.toFixed(4);
  };

  const [formData, setFormData] = useState({
    idNota: notaData?.idNota?.toString?.() ?? '',
    formaPago: 'TRANSFERENCIA',
    monto: notaData?.totalNota != null ? toBackendDecimal(notaData.totalNota) : '',
    referencia: '',
    observaciones: '',
    fechaPago: new Date().toISOString().split('T')[0],
  });

  const [errors, setErrors] = useState<{ [k: string]: string }>({});
  const [modoDirecto, setModoDirecto] = useState(!notaData);
  const [notasUsuario, setNotasUsuario] = useState<NotaItem[]>([]);
  const [cargandoNotas, setCargandoNotas] = useState(false);
  const [notaSeleccionada, setNotaSeleccionada] = useState<NotaItem | null>(notaData ?? null);
  const [submitting, setSubmitting] = useState(false);

  const [inscripcionesUsuario, setInscripcionesUsuario] = useState<Inscripcion[]>([]);
  const [cargandoInscripciones, setCargandoInscripciones] = useState(false);

  const [showDetailsModal, setShowDetailsModal] = useState(false);
  const [showPaymentModal, setShowPaymentModal] = useState(false);
  const [showRequisitosModal, setShowRequisitosModal] = useState(false);
  const [showProcesoModal, setShowProcesoModal] = useState(false);

  // Cargar configuración
  const cargarConfiguracion = useCallback(async () => {
    setLoadingConfig(true);
    try {
      const response = await api.get('/api/configuracion/');
      if (response.data && (response.data.success === undefined || response.data.success === true)) {
        setConfiguracion(response.data.data ?? response.data);
        console.log('✅ Configuración cargada:', response.data.data ?? response.data);
      } else {
        console.warn('No se pudo cargar la configuración:', response.data?.message);
        Alert.alert('Advertencia', 'No se pudo cargar la configuración del sistema');
      }
    } catch (error: any) {
      console.error('Error cargando configuración:', error);
      Alert.alert('Error', 'No se pudo cargar la configuración del sistema');
    } finally {
      setLoadingConfig(false);
    }
  }, []);

  // NUEVA FUNCIÓN: Cargar y filtrar requisitos
  const cargarRequisitos = useCallback(async () => {
    setLoadingRequisitos(true);
    try {
      const response = await api.get('/api/requisito/');
      const payload = response.data?.data ?? response.data?.results ?? response.data;

      let items: Requisito[] = [];

      if (Array.isArray(payload)) items = payload;
      else if (payload && Array.isArray(payload.results)) items = payload.results;
      else if (payload && Array.isArray(payload.data)) items = payload.data;

      const requisitosFisicos = items.filter(req => req.app === true);
      console.log(`✅ Requisitos cargados y filtrados. Total: ${items.length}, Físicos (app: true): ${requisitosFisicos.length}`);

      setRequisitosData(requisitosFisicos);
    } catch (error: any) {
      console.error('Error cargando requisitos:', error?.response ?? error);
    } finally {
      setLoadingRequisitos(false);
    }
  }, []);

  // helpers
  const placeholderNames = new Set(['Formación no especificada', 'Información no disponible', '—', null, undefined, '']);
  const isValidFormacionName = (name?: string | null) => {
    if (!name) return false;
    const s = String(name).trim();
    if (!s) return false;
    if (placeholderNames.has(s)) return false;
    return true;
  };

  const getNombreFormacion = (inscripcion: Inscripcion): string => {
    const name1 = (inscripcion as any).idFormacion_detail?.nombreFormacion;
    if (name1 && isValidFormacionName(name1)) return name1;

    const name2 = inscripcion.idCohorte?.idFormacion?.nombreFormacion || inscripcion.idCohorte?.idFormacion?.nombre;
    if (name2 && isValidFormacionName(name2)) return name2;

    const name3 = (inscripcion as any).nombreFormacion;
    if (name3 && isValidFormacionName(name3)) return name3;

    return 'Formación no especificada';
  };

  const findInscripcionForNota = (nota: NotaItem): Inscripcion | null => {
    const idIns = nota.idInscripcion ?? nota.idInscripcion_detail?.idInscripcion ?? nota.inscripcion_id ?? null;
    if (idIns) {
      const match = inscripcionesUsuario.find((ins) => Number(ins.idInscripcion) === Number(idIns));
      if (match) return match;
    }

    if (nota.fechaEmision) {
      const notaDate = new Date(nota.fechaEmision).getTime();
      const match = inscripcionesUsuario.find((ins) => {
        if (ins.fechaInscripcion) {
          const insDate = new Date(ins.fechaInscripcion).getTime();
          const diff = Math.abs(notaDate - insDate);
          return diff < 86400000;
        }
        return false;
      });
      if (match) return match;
    }

    if (nota.totalNota) {
      const matches = inscripcionesUsuario.filter((ins) => Number(ins.montoTotal) === Number(nota.totalNota));
      if (matches.length === 1) return matches[0];
      if (matches.length > 1) return matches[0];
    }

    return inscripcionesUsuario.find((ins) => (ins.estadoPago ?? '').toUpperCase() !== 'PAGADO') ?? null;
  };

  const getFormacionNameFromNota = (nota: NotaItem) => {
    if (!nota) return 'Formación no especificada';
    if (nota._resolvedFormacionName && isValidFormacionName(nota._resolvedFormacionName)) return nota._resolvedFormacionName;

    const ins = findInscripcionForNota(nota);
    if (ins) {
      const name = getNombreFormacion(ins);
      if (isValidFormacionName(name)) {
        nota._resolvedFormacionName = name;
        return name;
      }
    }

    if (nota.formacion && (nota.formacion.nombreFormacion || nota.formacion.nombre)) {
      const nm = nota.formacion.nombreFormacion ?? nota.formacion.nombre;
      if (isValidFormacionName(nm)) return nm;
    }

    return 'Formación no especificada';
  };

  // Determinar estado y color de la nota
  const getEstadoNota = (nota: NotaItem) => {
    if (!nota || nota.estado === null || nota.estado === undefined) {
      return { texto: 'Por pagar', color: '#dc3545', esPorPagar: true };
    }

    const estado = String(nota.estado).toUpperCase();

    if (estado === 'PAGADA') {
      return { texto: 'Pagada', color: '#28a745', esPagada: true };
    } else if (estado === 'PARCIAL') {
      return { texto: 'Parcial', color: '#ffc107', esParcial: true };
    } else if (estado === 'PENDIENTE') {
      return { texto: 'Por pagar', color: '#dc3545', esPorPagar: true };
    } else if (estado === 'EN_PROCESO' || estado === 'EN_VALIDACION' || estado === 'EN_PROCESAMIENTO') {
      return { texto: 'En proceso', color: '#ffc107', esParcial: true, esEnProceso: true };
    } else {
      return { texto: 'Por pagar', color: '#dc3545', esPorPagar: true };
    }
  };

  // Cargar inscripciones del usuario
  const cargarInscripcionesUsuario = useCallback(async () => {
    setCargandoInscripciones(true);
    try {
      const response = await api.get('/api/inscripcion/');
      const data = response.data;
      let items: Inscripcion[] = [];

      if (Array.isArray(data)) items = data;
      else if (data && Array.isArray(data.results)) items = data.results;
      else if (data && Array.isArray(data.data)) items = data.data;

      const cedulaUsuario = user?.cedula ? normalizarCedula(user.cedula) : null;
      if (cedulaUsuario) {
        items = items.filter((ins: Inscripcion) => {
          const cedIns = ins.idPersona_detail?.cedula ?? (ins.idPersona != null ? String(ins.idPersona) : '');
          return normalizarCedula(cedIns) === cedulaUsuario;
        });
      }

      setInscripcionesUsuario(items);
    } catch (error: any) {
      console.error('Error cargando inscripciones:', error);
    } finally {
      setCargandoInscripciones(false);
    }
  }, [user]);

  const cargarNotasUsuario = useCallback(async () => {
    setCargandoNotas(true);
    try {
      const response = await api.get('/api/notas/usuario/autenticado/');
      const d = response.data ?? {};
      let items: NotaItem[] = [];
      if (Array.isArray(d)) {
        items = d;
      } else if (Array.isArray(d.data)) {
        items = d.data;
      } else if (Array.isArray(d.results)) {
        items = d.results;
      } else if (d && d.data && typeof d.data === 'object') {
        const maybe = d.data.items ?? d.data.results ?? [];
        if (Array.isArray(maybe)) items = maybe;
      } else if (d && d.results && typeof d.results === 'object') {
        const maybe = d.results.items ?? [];
        if (Array.isArray(maybe)) items = maybe;
      }
      setNotasUsuario(items);
    } catch (error: any) {
      console.error('Error cargando notas:', error?.response ?? error);
    } finally {
      setCargandoNotas(false);
    }
  }, []);

  useEffect(() => {
    cargarConfiguracion();
    cargarRequisitos();
    if (modoDirecto && user) {
      cargarInscripcionesUsuario();
      cargarNotasUsuario();
    }
    if (notaData) {
      setNotaSeleccionada(notaData);
      setFormData(prev => ({ ...prev, idNota: String(notaData.idNota ?? ''), monto: toBackendDecimal(notaData.totalNota ?? 0) }));
      if (!modoDirecto) {
        setShowPaymentModal(true);
      }
    }
  }, [modoDirecto, user, notaData, cargarNotasUsuario, cargarInscripcionesUsuario, cargarConfiguracion, cargarRequisitos]);

  const onRefresh = async () => {
    setRefreshing(true);
    await Promise.all([cargarInscripcionesUsuario(), cargarNotasUsuario(), cargarConfiguracion(), cargarRequisitos()]);
    setRefreshing(false);
  };

  const seleccionarNota = async (nota: NotaItem) => {
    setNotaSeleccionada(nota);
    const estado = getEstadoNota(nota);

    if (estado.esPorPagar) {
      setFormData(prev => ({ ...prev, idNota: String(nota.idNota ?? ''), monto: toBackendDecimal(nota.totalNota ?? 0) }));
      setErrors({});
      setShowDetailsModal(true);
      setShowPaymentModal(false);
    } else if (estado.esParcial) {
      setShowProcesoModal(true);
    } else if (estado.esPagada) {
      setShowRequisitosModal(true);
    }
  };

  const iniciarPago = () => {
    if (!notaSeleccionada) return Alert.alert('Error', 'Seleccione una nota primero');
    setFormData(prev => ({
      ...prev,
      idNota: String(notaSeleccionada.idNota ?? ''),
      monto: toBackendDecimal(notaSeleccionada.totalNota ?? 0),
      referencia: '',
      fechaPago: new Date().toISOString().split('T')[0],
    }));
    setShowDetailsModal(false);
    setShowPaymentModal(true);
    setErrors({});
  };

  const cerrarModales = () => {
    setShowDetailsModal(false);
    setShowPaymentModal(false);
    setShowRequisitosModal(false);
    setShowProcesoModal(false);
    setNotaSeleccionada(null);
    setErrors({});
  };

  const validateForm = (): boolean => {
    const newErrors: { [key: string]: string } = {};
    if (!formData.idNota) newErrors.idNota = 'Debe seleccionar una nota';
    const montoNum = Number(String(formData.monto).replace(',', '.'));
    if (!formData.monto || isNaN(montoNum) || montoNum <= 0) newErrors.monto = 'Monto debe ser mayor a 0';
    else if (notaSeleccionada && montoNum > Number(notaSeleccionada.totalNota ?? 0)) newErrors.monto = `El monto no puede exceder el total de la nota ($${Number(notaSeleccionada.totalNota ?? 0)})`;
    if (!formData.referencia.trim()) newErrors.referencia = 'Número de referencia es requerido';
    if (!formData.fechaPago) newErrors.fechaPago = 'Fecha de pago es requerida';
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleInputChange = (field: string, value: string) => {
    setFormData(prev => ({ ...prev, [field]: value }));
    if (errors[field]) setErrors(prev => ({ ...prev, [field]: '' }));
  };

  // PROCESAR PAGO
  const handleProcesarPago = async () => {
    if (!validateForm()) {
      Alert.alert('Error', 'Por favor complete todos los campos requeridos');
      return;
    }

    if (!configuracion || !configuracion.idCuentaBanco) {
      Alert.alert('Error', 'No hay cuenta bancaria configurada en el sistema. Contacte al administrador.');
      return;
    }

    setSubmitting(true);

    const payload = {
      idNota: Number(formData.idNota),
      monto: Number(String(formData.monto).replace(',', '.')),
      fechaPago: formData.fechaPago,
      formaPago: 'TRANSFERENCIA',
      referencia: String(formData.referencia || ''),
      observaciones: String(formData.observaciones || ''),
    };

    console.log('[Pago] Payload a enviar:', payload);

    try {
      const response = await api.post('/api/pagos/create/', payload, {
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json'
        },
        validateStatus: () => true
      });

      const contentType = response.headers?.['content-type'] ?? response.headers?.['Content-Type'] ?? '';
      const isJson = typeof contentType === 'string' && contentType.toLowerCase().includes('application/json');

      if (isJson) {
        const body = response.data;
        console.log('[Pago] response.data (json):', body);

        if ((response.status === 201 || response.status === 200) && body?.success) {
          // PRIMERO: recargar notas e inscripciones para que la UI refleje el cambio
          try {
            await Promise.all([cargarNotasUsuario(), cargarInscripcionesUsuario()]);
          } catch (e) {
            console.warn('[Pago] error recargando datos después de crear pago:', e);
          }

          // CERRAR modal y limpiar selección / formulario mínimo
          setShowPaymentModal(false);
          setNotaSeleccionada(null);
          setFormData(prev => ({ ...prev, referencia: '', observaciones: '' }));

          // MENSAJE claro al usuario (confirmando que la lista se actualizó)
          Alert.alert(
            'Pago registrado',
            `✅ Su pago fue registrado correctamente y la lista se actualizó.`,
            [{ text: 'OK' }]
          );
        } else {
          const msg = body.message ?? JSON.stringify(body);
          Alert.alert('Error', `Servidor: ${msg}`);
        }
      } else {
        Alert.alert(
          'Error del servidor',
          `El servidor devolvió un error. Por favor contacte al administrador.\nStatus: ${response.status}`
        );
      }
    } catch (err: any) {
      console.error('[Pago] error catched:', err);
      const resp = err?.response;
      if (resp?.status === 400 && resp.data) {
        const body = resp.data;
        let message = body.message ?? 'Error de validación';
        if (body.errors && typeof body.errors === 'object') {
          const parts: string[] = [];
          Object.keys(body.errors).forEach(k => {
            const v = body.errors[k];
            if (Array.isArray(v)) parts.push(`${k}: ${v.join(', ')}`);
            else parts.push(`${k}: ${String(v)}`);
          });
          message += '\n' + parts.join('\n');
        }
        Alert.alert('Error de validación', message);
      } else if (resp?.status === 500) {
        Alert.alert('Error servidor', 'Error interno del servidor. Contacte al administrador.');
      } else {
        Alert.alert('Error', err.message ? String(err.message) : 'Error en la conexión');
      }
    } finally {
      setSubmitting(false);
    }
  };

  const formatCurrency = (amount: number): string => {
    try { return new Intl.NumberFormat('es-VE', { minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(amount); }
    catch { return Number(amount || 0).toFixed(2); }
  };

  const formatDate = (dateString?: string): string => {
    if (!dateString) return '—';
    const d = new Date(dateString);
    if (isNaN(d.getTime())) return dateString;
    return d.toLocaleDateString('es-VE');
  };

  const renderNotaItem = ({ item }: { item: NotaItem }) => {
    const estado = getEstadoNota(item);
    const formacionName = getFormacionNameFromNota(item);

    return (
      <TouchableOpacity
        style={[styles.notaItem, notaSeleccionada?.idNota === item.idNota && styles.notaItemSeleccionada]}
        onPress={() => seleccionarNota(item)}
      >
        <View style={styles.notaHeader}>
          <Text style={styles.notaNumero}>{item.numeroNota ?? '—'}</Text>
          <View style={[styles.estadoBadge, { backgroundColor: estado.color }]}>
            <Text style={styles.estadoText}>{estado.texto}</Text>
          </View>
        </View>

        <Text style={styles.notaFormacion} numberOfLines={2}>
          {formacionName}
        </Text>

        <View style={styles.notaFooter}>
          <Text style={styles.notaFecha}>{formatDate(item.fechaEmision)}</Text>
          <Text style={styles.notaMonto}>${formatCurrency(Number(item.totalNota ?? 0))}</Text>
        </View>

        {notaSeleccionada?.idNota === item.idNota && (
          <View style={styles.seleccionadoIndicator}>
            <Icon name="check-circle" size={20} color="#28a745" />
            <Text style={styles.seleccionadoText}>Seleccionada</Text>
          </View>
        )}
      </TouchableOpacity>
    );
  };

  const modalMaxWidth = Math.min(Math.max(320, width - 48), 900);

  // Componente para mostrar información de la cuenta bancaria
  const InfoCuentaBancaria = () => (
    <View style={styles.cuentaBancariaCard}>
      <View style={styles.cuentaHeader}>
        <Icon name="bank" size={20} color="#2dce89" />
        <Text style={styles.cuentaTitle}>Información para Transferencia</Text>
      </View>

      <View style={styles.cuentaGrid}>
        <View style={styles.cuentaItem}>
          <Text style={styles.cuentaLabel}>Banco:</Text>
          <Text style={styles.cuentaValue}>{configuracion?.nombre_banco || 'No especificado'}</Text>
        </View>

        <View style={styles.cuentaItem}>
          <Text style={styles.cuentaLabel}>Tipo de Cuenta:</Text>
          <Text style={styles.cuentaValue}>{configuracion?.tipo_cuenta || 'No especificado'}</Text>
        </View>

        <View style={styles.cuentaItem}>
          <Text style={styles.cuentaLabel}>Número de Cuenta:</Text>
          <Text style={[styles.cuentaValue, styles.cuentaDestacado]}>
            {configuracion?.numero_cuenta || 'No especificado'}
          </Text>
        </View>

        <View style={styles.cuentaItem}>
          <Text style={styles.cuentaLabel}>Cédula/RIF:</Text>
          <Text style={[styles.cuentaValue, styles.cuentaDestacado]}>
            {configuracion?.cedulaCuenta || 'No especificado'}
          </Text>
        </View>

        <View style={styles.cuentaItem}>
          <Text style={styles.cuentaLabel}>Titular:</Text>
          <Text style={styles.cuentaValue}>{configuracion?.nombreInstitucion || 'Institución'}</Text>
        </View>
      </View>

      <View style={styles.cuentaInstrucciones}>
        <Text style={styles.instruccionesTitle}>📋 Instrucciones:</Text>
        <Text style={styles.instruccionesText}>
          1. Realice la transferencia a la cuenta mostrada arriba{'\n'}
          2. Guarde el número de referencia de la transferencia{'\n'}
          3. Complete el formulario con la referencia y fecha{'\n'}
          4. Envíe el comprobante por correo si es requerido
        </Text>
      </View>
    </View>
  );

  // Modal de Requisitos (ACTUALIZADO para usar requisitosData)
  const ModalRequisitos = () => (
    <Modal
      visible={showRequisitosModal}
      animationType="slide"
      transparent={true}
      onRequestClose={cerrarModales}
    >
      <View style={styles.modalOverlay}>
        <View style={[styles.modalContent, { maxWidth: modalMaxWidth, maxHeight: '90%' }]}>
          <View style={styles.modalHeader}>
            <View style={styles.modalTitleContainer}>
              <Icon name="clipboard-check" size={24} color="#28a745" />
              <Text style={styles.modalTitle}>Requisitos de Entrega</Text>
            </View>
            <TouchableOpacity onPress={cerrarModales} style={styles.closeButton}>
              <Icon name="close" size={22} color="#6c757d" />
            </TouchableOpacity>
          </View>

          <ScrollView style={styles.modalBody} showsVerticalScrollIndicator={false}>
            <View style={styles.successCard}>
              <Icon name="check-circle" size={50} color="#28a745" />
              <Text style={styles.successTitle}>¡Pago Confirmado!</Text>
              <Text style={styles.successSubtitle}>
                Su pago ha sido confirmado exitosamente. Para completar su inscripción,
                por favor acérquese a la institución con los siguientes documentos físicos:
              </Text>
            </View>

            <View style={styles.requisitosList}>
              <Text style={styles.requisitosTitle}>Documentos Requeridos:</Text>

              {loadingRequisitos ? (
                <ActivityIndicator size="large" color="#007bff" style={{ marginVertical: 20 }} />
              ) : requisitosData.length > 0 ? (
                requisitosData.map((req) => (
                  <View key={req.idRequisito} style={styles.requisitoItem}>
                    <Icon name="checkbox-marked-circle" size={20} color="#28a745" />
                    <Text style={styles.requisitoText}>{req.nombreRequisito}</Text>
                  </View>
                ))
              ) : (
                <View style={styles.requisitoItem}>
                  <Icon name="information-outline" size={20} color="#ffc107" />
                  <Text style={[styles.requisitoText, { color: '#ffc107' }]}>
                    No se encontraron requisitos físicos (app: true) para consignar.
                  </Text>
                </View>
              )}
            </View>

            <View style={styles.infoCard}>
              <Text style={styles.infoTitle}>📍 Dirección de la Institución:</Text>
              <Text style={styles.infoText}>
                {configuracion?.nombreInstitucion || 'Institución Educativa'}{'\n'}
                Av. Principal, Edificio Central{'\n'}
                Horario de atención: Martes a Jueves 8:00 AM - 3:00 PM
              </Text>
            </View>
          </ScrollView>

          <View style={styles.modalFooter}>
            <TouchableOpacity style={styles.primaryButton} onPress={cerrarModales}>
              <Text style={styles.primaryButtonText}>Entendido</Text>
            </TouchableOpacity>
          </View>
        </View>
      </View>
    </Modal>
  );

  // Modal de Proceso (para notas pendientes)
  const ModalProceso = () => (
    <Modal
      visible={showProcesoModal}
      animationType="slide"
      transparent={true}
      onRequestClose={cerrarModales}
    >
      <View style={styles.modalOverlay}>
        <View style={[styles.modalContent, { maxWidth: modalMaxWidth, maxHeight: '80%' }]}>
          <View style={styles.modalHeader}>
            <View style={styles.modalTitleContainer}>
              <Icon name="clock-outline" size={24} color="#ffc107" />
              <Text style={styles.modalTitle}>Pago en Proceso</Text>
            </View>
            <TouchableOpacity onPress={cerrarModales} style={styles.closeButton}>
              <Icon name="close" size={22} color="#6c757d" />
            </TouchableOpacity>
          </View>

          <View style={styles.modalBody}>
            <View style={styles.warningCard}>
              <Icon name="clock" size={50} color="#ffc107" />
              <Text style={styles.warningTitle}>Pago Pendiente de Confirmación</Text>
              <Text style={styles.warningSubtitle}>
                Su pago se encuentra en proceso de verificación por nuestra administración.
                Una vez confirmado, recibirá una notificación y podrá proceder con la entrega de documentos.
              </Text>
            </View>

            <View style={styles.infoCard}>
              <Text style={styles.infoTitle}>⏳ Tiempo de espera estimado:</Text>
              <Text style={styles.infoText}>24-48 horas hábiles</Text>
            </View>
          </View>

          <View style={styles.modalFooter}>
            <TouchableOpacity style={styles.primaryButton} onPress={cerrarModales}>
              <Text style={styles.primaryButtonText}>Entendido</Text>
            </TouchableOpacity>
          </View>
        </View>
      </View>
    </Modal>
  );

  if (modoDirecto) {
    return (
      <KeyboardAvoidingView style={styles.container} behavior={Platform.OS === 'ios' ? 'padding' : 'height'}>
        <View style={styles.header}>
          <View style={styles.headerContent}>
            <Text style={styles.title}>Mis Notas de Cobro</Text>
            <Text style={styles.subtitle}>Seleccione una nota para proceder al pago</Text>
          </View>
          <View style={styles.headerIcon}>
            <Icon name="file-multiple" size={28} color="#4f8cff" />
          </View>
        </View>

        <View style={styles.listaContainer}>
          {cargandoNotas || cargandoInscripciones ? (
            <View style={styles.loadingContainer}>
              <ActivityIndicator size="large" color="#4f8cff" />
              <Text style={styles.loadingText}>Cargando notas...</Text>
            </View>
          ) : notasUsuario.length === 0 ? (
            <View style={styles.emptyContainer}>
              <Icon name="file-alert" size={70} color="#dee2e6" />
              <Text style={styles.emptyText}>No tienes notas pendientes</Text>
              <Text style={styles.emptySubtext}>Realiza una inscripción para generar una nota de cobro</Text>
            </View>
          ) : (
            <FlatList
              data={notasUsuario}
              renderItem={renderNotaItem}
              keyExtractor={(item) => String(item.idNota ?? item.numeroNota ?? `nota-${item.numeroNota ?? Math.random().toString(36).slice(2,9)}`)}
              refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} colors={['#4f8cff']} tintColor="#4f8cff" />}
              contentContainerStyle={styles.listaContent}
              showsVerticalScrollIndicator={false}
            />
          )}
        </View>

        {/* MODAL DETALLE (solo para notas por pagar) */}
        {notaSeleccionada && showDetailsModal && (
          <View style={styles.formularioOverlay}>
            <View style={[styles.modalContent, { width: modalMaxWidth, maxHeight: '85%' }]}>
              <View style={styles.modalHeader}>
                <View style={styles.modalTitleContainer}>
                  <Icon name="file-document" size={24} color="#495057" />
                  <Text style={styles.modalTitle}>Detalle de Nota</Text>
                </View>
                <TouchableOpacity onPress={cerrarModales} style={styles.closeButton}>
                  <Icon name="close" size={22} color="#6c757d" />
                </TouchableOpacity>
              </View>

              <ScrollView style={styles.modalBody} showsVerticalScrollIndicator={false}>
                <View style={styles.infoCard}>
                  <View style={styles.infoHeader}>
                    <Icon name="file-document" size={18} color="#495057" />
                    <Text style={styles.infoTitle}>Nota Seleccionada</Text>
                  </View>

                  <View style={styles.infoGrid}>
                    <View style={styles.infoItem}>
                      <Text style={styles.infoLabel}>Número:</Text>
                      <Text style={styles.infoValue}>{notaSeleccionada.numeroNota ?? '—'}</Text>
                    </View>
                    <View style={styles.infoItem}>
                      <Text style={styles.infoLabel}>Formación:</Text>
                      <Text style={styles.infoValue} numberOfLines={2}>
                        {getFormacionNameFromNota(notaSeleccionada)}
                      </Text>
                    </View>
                    <View style={styles.infoItem}>
                      <Text style={styles.infoLabel}>Total:</Text>
                      <Text style={styles.totalValue}>${formatCurrency(Number(notaSeleccionada.totalNota ?? 0))}</Text>
                    </View>
                  </View>
                </View>

                {/* Información de cuenta bancaria en modal de detalles */}
                <InfoCuentaBancaria />

                <View style={styles.infoCard}>
                  <Text style={styles.infoTitle}>💡 Siguiente Paso:</Text>
                  <Text style={styles.infoText}>
                    Al continuar, podrá registrar los datos de su transferencia.
                    Asegúrese de tener a mano el comprobante de pago con el número de referencia.
                  </Text>
                </View>
              </ScrollView>

              <View style={styles.modalFooter}>
                <TouchableOpacity style={[styles.secondaryButton, { marginRight: 8 }]} onPress={cerrarModales}>
                  <Text style={styles.secondaryButtonText}>Cancelar</Text>
                </TouchableOpacity>
                <TouchableOpacity style={styles.primaryButton} onPress={iniciarPago}>
                  <Text style={styles.primaryButtonText}>Continuar al Pago</Text>
                </TouchableOpacity>
              </View>
            </View>
          </View>
        )}

        {/* MODAL PAGO MEJORADO */}
        {notaSeleccionada && showPaymentModal && (
          <View style={styles.formularioOverlay}>
            <View style={[styles.modalContent, { width: modalMaxWidth, maxHeight: '90%' }]}>
              <View style={styles.modalHeader}>
                <View style={styles.modalTitleContainer}>
                  <Icon name="credit-card-check" size={24} color="#28a745" />
                  <Text style={styles.modalTitle}>Registrar Pago</Text>
                </View>
                <TouchableOpacity onPress={cerrarModales} style={styles.closeButton}>
                  <Icon name="close" size={22} color="#6c757d" />
                </TouchableOpacity>
              </View>

              <ScrollView style={styles.modalBody} showsVerticalScrollIndicator={false}>
                <View style={styles.infoCard}>
                  <View style={styles.infoHeader}>
                    <Icon name="file-document" size={18} color="#495057" />
                    <Text style={styles.infoTitle}>Información de la Nota</Text>
                  </View>

                  <View style={styles.infoGrid}>
                    <View style={styles.infoItem}>
                      <Text style={styles.infoLabel}>Número:</Text>
                      <Text style={styles.infoValue}>{notaSeleccionada.numeroNota ?? '—'}</Text>
                    </View>
                    <View style={styles.infoItem}>
                      <Text style={styles.infoLabel}>Formación:</Text>
                      <Text style={styles.infoValue} numberOfLines={2}>
                        {getFormacionNameFromNota(notaSeleccionada)}
                      </Text>
                    </View>
                    <View style={styles.infoItem}>
                      <Text style={styles.infoLabel}>Total a Pagar:</Text>
                      <Text style={styles.totalValue}>${formatCurrency(Number(notaSeleccionada.totalNota ?? 0))}</Text>
                    </View>
                  </View>
                </View>

                {/* Información de cuenta bancaria */}
                <InfoCuentaBancaria />

                <View style={styles.formSection}>
                  <Text style={styles.sectionTitle}>Datos del Pago</Text>

                  <View style={styles.inputGroup}>
                    <Text style={styles.label}>Forma de Pago</Text>
                    <View style={styles.readOnlyField}>
                      <Icon name="bank-transfer" size={20} color="#4f8cff" style={styles.fieldIcon} />
                      <Text style={styles.readOnlyText}>Transferencia Bancaria</Text>
                    </View>
                  </View>

                  <View style={styles.inputGroup}>
                    <Text style={styles.label}>Número de Referencia *</Text>
                    <TextInput
                      style={[styles.input, errors.referencia && styles.inputError]}
                      value={formData.referencia}
                      onChangeText={(v) => handleInputChange('referencia', v)}
                      placeholder="Ingrese el número de referencia de la transferencia"
                      maxLength={40}
                      placeholderTextColor="#6c757d"
                      editable={!submitting}
                    />
                    {errors.referencia && (
                      <View style={styles.errorContainer}>
                        <Icon name="alert-circle" size={16} color="#dc3545" />
                        <Text style={styles.errorText}>{errors.referencia}</Text>
                      </View>
                    )}
                  </View>

                  <View style={styles.inputGroup}>
                    <Text style={styles.label}>Fecha de Pago *</Text>
                    <View style={styles.inputContainer}>
                      <Icon name="calendar" size={20} color="#6c757d" style={styles.inputIcon} />
                      <TextInput
                        style={[styles.input, errors.fechaPago && styles.inputError]}
                        value={formData.fechaPago}
                        onChangeText={(v) => handleInputChange('fechaPago', v)}
                        placeholder="AAAA-MM-DD"
                        placeholderTextColor="#6c757d"
                        editable={!submitting}
                      />
                    </View>
                    {errors.fechaPago && (
                      <View style={styles.errorContainer}>
                        <Icon name="alert-circle" size={16} color="#dc3545" />
                        <Text style={styles.errorText}>{errors.fechaPago}</Text>
                      </View>
                    )}
                  </View>

                  <View style={styles.inputGroup}>
                    <Text style={styles.label}>Observaciones (Opcional)</Text>
                    <TextInput
                      style={[styles.input, styles.textArea]}
                      value={formData.observaciones}
                      onChangeText={(v) => handleInputChange('observaciones', v)}
                      placeholder="Observaciones adicionales sobre el pago..."
                      multiline
                      numberOfLines={3}
                      textAlignVertical="top"
                      placeholderTextColor="#6c757d"
                      editable={!submitting}
                    />
                  </View>

                  <View style={styles.infoCard}>
                    <View style={styles.infoHeader}>
                      <Icon name="information" size={18} color="#495057" />
                      <Text style={styles.infoTitle}>Información Importante</Text>
                    </View>
                    <Text style={styles.infoText}>
                      • Su pago será verificado por la administración{"\n"}
                      • Recibirá una notificación cuando sea confirmado{"\n"}
                      • El proceso puede tomar 24-48 horas hábiles{"\n"}
                      • Guarde el comprobante de transferencia
                    </Text>
                  </View>
                </View>
              </ScrollView>

              <View style={styles.modalFooter}>
                <TouchableOpacity
                  style={[styles.primaryButton, submitting && styles.buttonDisabled]}
                  onPress={handleProcesarPago}
                  disabled={submitting}
                >
                  <View style={styles.buttonContent}>
                    {submitting ? (
                      <ActivityIndicator size="small" color="#fff" />
                    ) : (
                      <Icon name="check-circle" size={20} color="#fff" />
                    )}
                    <Text style={styles.primaryButtonText}>
                      {submitting ? 'Procesando...' : 'Confirmar Pago'}
                    </Text>
                  </View>
                </TouchableOpacity>
              </View>
            </View>
          </View>
        )}

        {/* Modales nuevos */}
        <ModalRequisitos />
        <ModalProceso />
      </KeyboardAvoidingView>
    );
  }

  // [El resto del código para modo automático se mantiene similar...]

  return (
    <KeyboardAvoidingView style={styles.container} behavior={Platform.OS === 'ios' ? 'padding' : 'height'}>
      <ScrollView style={styles.scrollView} contentContainerStyle={styles.formScrollContent}>
        <View style={styles.header}>
          <View style={styles.headerContent}>
            <Text style={styles.title}>Registrar Pago</Text>
            <Text style={styles.subtitle}>Complete los datos para registrar el pago por transferencia</Text>
          </View>
          <View style={styles.headerIcon}><Icon name="credit-card-scan" size={28} color="#4f8cff" /></View>
        </View>

        {notaData && (
          <View style={[styles.infoCard, { maxWidth: Math.min(920, width - 48), alignSelf: 'center' }]}>
            <View style={styles.infoHeader}><Icon name="file-document" size={18} color="#495057" /><Text style={styles.infoTitle}>Información de la Nota</Text></View>
            <View style={styles.infoGrid}>
              <View style={styles.infoItem}><Text style={styles.infoLabel}>Número:</Text><Text style={styles.infoValue}>{notaData.numeroNota ?? '—'}</Text></View>
              <View style={styles.infoItem}><Text style={styles.infoLabel}>Formación:</Text><Text style={styles.infoValue}>{getFormacionNameFromNota(notaSeleccionada ?? notaData)}</Text></View>
              <View style={styles.infoItem}><Text style={styles.infoLabel}>Estudiante:</Text><Text style={styles.infoValue}>{notaData.persona?.nombre ?? notaData.persona ?? '—'}</Text></View>
              <View style={styles.infoItem}><Text style={styles.infoLabel}>Cédula:</Text><Text style={styles.infoValue}>{notaData.persona?.cedula ?? '—'}</Text></View>
              <View style={[styles.infoItem, styles.totalItem]}><Text style={styles.totalLabel}>Total a Pagar:</Text><Text style={styles.totalValue}>${formatCurrency(Number(notaData.totalNota ?? 0))}</Text></View>
            </View>
          </View>
        )}

        {/* Información de cuenta bancaria en el formulario principal */}
        {configuracion && (
          <View style={[styles.cuentaBancariaCard, { maxWidth: Math.min(920, width - 48), alignSelf: 'center' }]}>
            <View style={styles.cuentaHeader}>
              <Icon name="bank" size={20} color="#2dce89" />
              <Text style={styles.cuentaTitle}>Información para Transferencia</Text>
            </View>

            <View style={styles.cuentaGrid}>
              <View style={styles.cuentaItem}>
                <Text style={styles.cuentaLabel}>Banco:</Text>
                <Text style={styles.cuentaValue}>{configuracion.nombre_banco || 'No especificado'}</Text>
              </View>

              <View style={styles.cuentaItem}>
                <Text style={styles.cuentaLabel}>Tipo de Cuenta:</Text>
                <Text style={styles.cuentaValue}>{configuracion.tipo_cuenta || 'No especificado'}</Text>
              </View>

              <View style={styles.cuentaItem}>
                <Text style={styles.cuentaLabel}>Número de Cuenta:</Text>
                <Text style={[styles.cuentaValue, styles.cuentaDestacado]}>
                  {configuracion.numero_cuenta || 'No especificado'}
                </Text>
              </View>

              <View style={styles.cuentaItem}>
                <Text style={styles.cuentaLabel}>Cédula/RIF:</Text>
                <Text style={[styles.cuentaValue, styles.cuentaDestacado]}>
                  {configuracion.cedulaCuenta || 'No especificado'}
                </Text>
              </View>

              <View style={styles.cuentaItem}>
                <Text style={styles.cuentaLabel}>Titular:</Text>
                <Text style={styles.cuentaValue}>{configuracion.nombreInstitucion || 'Institución'}</Text>
              </View>
            </View>
          </View>
        )}

        <View style={[styles.formCard, { maxWidth: Math.min(920, width - 48), alignSelf: 'center' }]}>
          <View style={styles.formSection}>
            <Text style={styles.sectionTitle}>Datos del Pago</Text>

            <View style={styles.inputGroup}>
              <Text style={styles.label}>Forma de Pago</Text>
              <View style={styles.readOnlyField}>
                <Icon name="bank-transfer" size={20} color="#4f8cff" style={styles.fieldIcon} />
                <Text style={styles.readOnlyText}>Transferencia Bancaria</Text>
              </View>
            </View>

            <View style={styles.inputGroup}>
              <Text style={styles.label}>Número de Referencia *</Text>
              <TextInput
                style={[styles.input, errors.referencia && styles.inputError]}
                value={formData.referencia}
                onChangeText={(v) => handleInputChange('referencia', v)}
                placeholder="Ingrese el número de referencia"
                maxLength={40}
                placeholderTextColor="#6c757d"
                editable={!submitting}
              />
              {errors.referencia && <View style={styles.errorContainer}><Icon name="alert-circle" size={16} color="#dc3545" /><Text style={styles.errorText}>{errors.referencia}</Text></View>}
            </View>

            <View style={styles.inputGroup}>
              <Text style={styles.label}>Fecha de Pago *</Text>
              <View style={styles.inputContainer}>
                <Icon name="calendar" size={20} color="#6c757d" style={styles.inputIcon} />
                <TextInput
                  style={[styles.input, errors.fechaPago && styles.inputError]}
                  value={formData.fechaPago}
                  onChangeText={(v) => handleInputChange('fechaPago', v)}
                  placeholder="AAAA-MM-DD"
                  placeholderTextColor="#6c757d"
                  editable={!submitting}
                />
              </View>
              {errors.fechaPago && <View style={styles.errorContainer}><Icon name="alert-circle" size={16} color="#dc3545" /><Text style={styles.errorText}>{errors.fechaPago}</Text></View>}
            </View>

            <View style={styles.inputGroup}>
              <Text style={styles.label}>Observaciones</Text>
              <TextInput
                style={[styles.input, styles.textArea]}
                value={formData.observaciones}
                onChangeText={(v) => handleInputChange('observaciones', v)}
                placeholder="Observaciones adicionales..."
                multiline
                numberOfLines={3}
                textAlignVertical="top"
                placeholderTextColor="#6c757d"
                editable={!submitting}
              />
            </View>
          </View>

          <TouchableOpacity
            style={[styles.primaryButton, submitting && styles.buttonDisabled]}
            onPress={handleProcesarPago}
            disabled={submitting}
          >
            <View style={styles.buttonContent}>
              {submitting ? (
                <ActivityIndicator size="small" color="#fff" />
              ) : (
                <Icon name="check-circle" size={20} color="#fff" />
              )}
              <Text style={styles.primaryButtonText}>
                {submitting ? 'Procesando...' : 'Confirmar Pago'}
              </Text>
            </View>
          </TouchableOpacity>
        </View>
      </ScrollView>

      <ModalRequisitos />
      <ModalProceso />
    </KeyboardAvoidingView>
  );
};

// Estilos (idénticos a los tuyos)
const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#f8f9fa' },
  scrollView: { flex: 1 },
  header: { flexDirection: 'row', padding: 20, alignItems: 'center', justifyContent: 'space-between', backgroundColor: '#fff', borderBottomWidth: 1, borderBottomColor: '#e9ecef' },
  headerContent: { flex: 1 },
  title: { fontSize: 22, fontWeight: '700', color: '#212529' },
  subtitle: { fontSize: 14, color: '#6c757d', marginTop: 4 },
  headerIcon: { marginLeft: 12 },
  listaContainer: { flex: 1, paddingHorizontal: 16, paddingBottom: 20 },
  listaContent: { paddingBottom: 120 },
  notaItem: { backgroundColor: '#fff', borderRadius: 12, padding: 16, marginVertical: 8, shadowColor: '#000', shadowOpacity: 0.05, shadowOffset: { width: 0, height: 2 }, shadowRadius: 4, elevation: 2 },
  notaItemSeleccionada: { borderColor: '#4f8cff', borderWidth: 2 },
  notaHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  notaNumero: { fontWeight: '700', color: '#343a40', fontSize: 16 },
  estadoBadge: { paddingHorizontal: 12, paddingVertical: 6, borderRadius: 20 },
  estadoText: { fontSize: 12, color: '#fff', fontWeight: '600' },
  notaFormacion: { marginTop: 8, color: '#495057', fontSize: 14, lineHeight: 20 },
  notaFooter: { flexDirection: 'row', justifyContent: 'space-between', marginTop: 12, alignItems: 'center' },
  notaFecha: { color: '#6c757d', fontSize: 13 },
  notaMonto: { fontWeight: '700', color: '#212529', fontSize: 16 },
  seleccionadoIndicator: { flexDirection: 'row', alignItems: 'center', marginTop: 8, paddingTop: 8, borderTopWidth: 1, borderTopColor: '#e9ecef' },
  seleccionadoText: { marginLeft: 6, color: '#28a745', fontWeight: '600' },

  formularioOverlay: { position: 'absolute', top: 0, left: 0, right: 0, bottom: 0, backgroundColor: 'rgba(0,0,0,0.5)', justifyContent: 'center', alignItems: 'center', padding: 20 },
  formScrollContent: { paddingBottom: 40 },

  modalOverlay: { flex: 1, backgroundColor: 'rgba(0,0,0,0.5)', justifyContent: 'center', alignItems: 'center', padding: 20 },
  modalContent: { backgroundColor: '#fff', borderRadius: 16, width: '100%', shadowColor: '#000', shadowOffset: { width: 0, height: 4 }, shadowOpacity: 0.3, shadowRadius: 8, elevation: 8 },
  modalHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', padding: 20, borderBottomWidth: 1, borderBottomColor: '#e9ecef' },
  modalTitleContainer: { flexDirection: 'row', alignItems: 'center' },
  modalTitle: { fontSize: 20, fontWeight: '700', marginLeft: 8, color: '#212529' },
  closeButton: { padding: 4 },
  modalBody: { padding: 20 },
  modalFooter: { padding: 20, borderTopWidth: 1, borderTopColor: '#e9ecef', flexDirection: 'row', justifyContent: 'flex-end' },

  infoCard: { backgroundColor: '#f8f9fa', borderRadius: 12, padding: 16, marginBottom: 16, borderLeftWidth: 4, borderLeftColor: '#4f8cff' },
  infoHeader: { flexDirection: 'row', alignItems: 'center', marginBottom: 12 },
  infoTitle: { marginLeft: 8, fontWeight: '700', color: '#343a40', fontSize: 16 },
  infoGrid: {  },
  infoItem: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 },
  infoLabel: { color: '#6c757d', fontSize: 14, fontWeight: '500' },
  infoValue: { color: '#212529', fontWeight: '600', fontSize: 14, flex: 1, textAlign: 'right' },
  totalItem: { marginTop: 8, paddingTop: 8, borderTopWidth: 1, borderTopColor: '#dee2e6' },
  totalLabel: { color: '#495057', fontWeight: '700', fontSize: 15 },
  totalValue: { color: '#212529', fontWeight: '900', fontSize: 18 },

  cuentaBancariaCard: { backgroundColor: '#e8f5e8', borderRadius: 12, padding: 16, marginBottom: 16, borderLeftWidth: 4, borderLeftColor: '#2dce89' },
  cuentaHeader: { flexDirection: 'row', alignItems: 'center', marginBottom: 12 },
  cuentaTitle: { marginLeft: 8, fontWeight: '700', color: '#155724', fontSize: 16 },
  cuentaGrid: {  },
  cuentaItem: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8, paddingVertical: 4 },
  cuentaLabel: { color: '#155724', fontSize: 14, fontWeight: '600' },
  cuentaValue: { color: '#212529', fontWeight: '600', fontSize: 14, flex: 1, textAlign: 'right' },
  cuentaDestacado: { color: '#2dce89', fontWeight: '800', fontSize: 15 },
  cuentaInstrucciones: { marginTop: 12, paddingTop: 12, borderTopWidth: 1, borderTopColor: '#c3e6cb' },
  instruccionesTitle: { color: '#155724', fontWeight: '700', fontSize: 14, marginBottom: 8 },
  instruccionesText: { color: '#155724', fontSize: 13, lineHeight: 18 },

  formSection: {  },
  sectionTitle: { fontSize: 18, fontWeight: '700', color: '#495057', marginBottom: 16, paddingBottom: 8, borderBottomWidth: 1, borderBottomColor: '#e9ecef' },
  inputGroup: { marginBottom: 20 },
  label: { marginBottom: 8, color: '#495057', fontWeight: '600', fontSize: 14 },
  readOnlyField: { flexDirection: 'row', alignItems: 'center', backgroundColor: '#e9ecef', borderRadius: 8, padding: 12 },
  fieldIcon: { marginRight: 8 },
  readOnlyText: { color: '#495057', fontWeight: '600', fontSize: 16 },
  inputContainer: { flexDirection: 'row', alignItems: 'center', backgroundColor: '#fff', borderRadius: 8, paddingHorizontal: 12, borderWidth: 1, borderColor: '#e9ecef' },
  inputIcon: { marginRight: 8 },
  input: { flex: 1, paddingVertical: 12, paddingHorizontal: 8, color: '#212529', fontSize: 16 },
  inputError: { borderColor: '#dc3545' },
  textArea: { minHeight: 100, textAlignVertical: 'top' },

  primaryButton: { backgroundColor: '#4f8cff', paddingVertical: 16, borderRadius: 12, alignItems: 'center', justifyContent: 'center', shadowColor: '#4f8cff', shadowOffset: { width: 0, height: 4 }, shadowOpacity: 0.3, shadowRadius: 8, elevation: 4 },
  secondaryButton: { backgroundColor: '#6c757d', paddingVertical: 16, borderRadius: 12, alignItems: 'center', justifyContent: 'center', paddingHorizontal: 24 },
  buttonDisabled: { opacity: 0.6 },
  buttonContent: { flexDirection: 'row', alignItems: 'center' },
  primaryButtonText: { color: '#fff', marginLeft: 8, fontWeight: '700', fontSize: 16 },
  secondaryButtonText: { color: '#fff', fontWeight: '700', fontSize: 16 },

  errorContainer: { flexDirection: 'row', alignItems: 'center', marginTop: 8 },
  errorText: { color: '#dc3545', marginLeft: 6, fontSize: 14 },

  successCard: { backgroundColor: '#d4edda', padding: 20, borderRadius: 12, alignItems: 'center', marginBottom: 20, borderLeftWidth: 4, borderLeftColor: '#28a745' },
  successTitle: { fontSize: 20, fontWeight: '700', color: '#155724', marginTop: 12, textAlign: 'center' },
  successSubtitle: { color: '#155724', textAlign: 'center', marginTop: 8, lineHeight: 22, fontSize: 15 },
  warningCard: { backgroundColor: '#fff3cd', padding: 20, borderRadius: 12, alignItems: 'center', marginBottom: 20, borderLeftWidth: 4, borderLeftColor: '#ffc107' },
  warningTitle: { fontSize: 20, fontWeight: '700', color: '#856404', marginTop: 12, textAlign: 'center' },
  warningSubtitle: { color: '#856404', textAlign: 'center', marginTop: 8, lineHeight: 22, fontSize: 15 },

  requisitosList: { marginBottom: 20 },
  requisitosTitle: { fontSize: 18, fontWeight: '700', color: '#212529', marginBottom: 16 },
  requisitoItem: { flexDirection: 'row', alignItems: 'flex-start', marginBottom: 12, paddingHorizontal: 8 },
  requisitoText: { marginLeft: 12, color: '#495057', fontSize: 15, flex: 1, lineHeight: 22 },

  loadingContainer: { padding: 40, alignItems: 'center' },
  loadingText: { color: '#6c757d', marginTop: 12, fontSize: 16 },
  emptyContainer: { alignItems: 'center', padding: 40 },
  emptyText: { fontSize: 18, fontWeight: '700', color: '#343a40', marginTop: 16, textAlign: 'center' },
  emptySubtext: { color: '#6c757d', marginTop: 8, textAlign: 'center', fontSize: 14 },

  formCard: { backgroundColor: '#fff', borderRadius: 16, padding: 24, margin: 16, shadowColor: '#000', shadowOffset: { width: 0, height: 2 }, shadowOpacity: 0.1, shadowRadius: 8, elevation: 4 },
  infoText: { color: '#495057', lineHeight: 22, fontSize: 14 },
});

function normalizarCedula(cedula: string): string {
  if (!cedula) return '';
  let normalizada = cedula.toString().toUpperCase().replace(/[\.\-\s]/g, '');
  if (/^[VEJG]/.test(normalizada)) {
    normalizada = normalizada.substring(1);
  }
  return normalizada;
}

export default PagoScreen;
