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

const PagoScreen: React.FC = () => {
  const navigation = useNavigation<any>();
  const route = useRoute<any>();
  const { user } = useContext(AuthContext);
  const { width } = useWindowDimensions();
  const { notaData } = route.params || {};

  const [refreshing, setRefreshing] = useState(false);

  // helper para formatear monto para enviar al backend (4 decimales, punto decimal)
  const toBackendDecimal = (v: number | string) => {
    const n = Number(String(v).replace(',', '.')) || 0;
    return n.toFixed(4); // devuelve string con 4 decimales
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

  const pagoMovilInfo = {
    banco: 'BANCO DEMO',
    titular: 'INSTITUCIÓN EJEMPLO C.A.',
    cedulaTitular: 'V-12345678',
    numeroCuenta: '0123-4567-8901-2345',
    tipoCuenta: 'Ahorros',
    telefonoPagoMovil: '+58 424-1234567',
    rif: 'J-12345678-9'
  };

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
    // Prioridad 1: Por idInscripcion
    const idIns = nota.idInscripcion ?? nota.idInscripcion_detail?.idInscripcion ?? nota.inscripcion_id ?? null;
    if (idIns) {
      const match = inscripcionesUsuario.find((ins) => Number(ins.idInscripcion) === Number(idIns));
      if (match) return match;
    }

    // Prioridad 2: Por fecha cercana
    if (nota.fechaEmision) {
      const notaDate = new Date(nota.fechaEmision).getTime();
      const match = inscripcionesUsuario.find((ins) => {
        if (ins.fechaInscripcion) {
          const insDate = new Date(ins.fechaInscripcion).getTime();
          const diff = Math.abs(notaDate - insDate);
          return diff < 86400000; // 1 día
        }
        return false;
      });
      if (match) return match;
    }

    // Prioridad 3: por monto
    if (nota.totalNota) {
      const matches = inscripcionesUsuario.filter((ins) => Number(ins.montoTotal) === Number(nota.totalNota));
      if (matches.length === 1) return matches[0];
      if (matches.length > 1) return matches[0];
    }

    // Fallback: una inscripción no pagada
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

  // Cargar inscripciones del usuario
  const cargarInscripcionesUsuario = useCallback(async () => {
    setCargandoInscripciones(true);
    try {
      const response = await api.get('/api/inscripcion/');
      const data = response.data;
      let items: Inscripcion[] = [];

      if (Array.isArray(data)) items = data;
      else if (data.results && Array.isArray(data.results)) items = data.results;
      else if (data.data && Array.isArray(data.data)) items = data.data;

      const cedulaUsuario = user?.cedula ? normalizarCedula(user.cedula) : null;
      if (cedulaUsuario) {
        items = items.filter((ins: Inscripcion) => {
          const cedIns = ins.idPersona_detail?.cedula ?? (ins.idPersona != null ? String(ins.idPersona) : '');
          return normalizarCedula(cedIns) === cedulaUsuario;
        });
      }

      setInscripcionesUsuario(items);
      console.log('📚 Inscripciones cargadas:', items.map(i => ({ id: i.idInscripcion, fecha: i.fechaInscripcion, monto: i.montoTotal, formacion: getNombreFormacion(i) })));
    } catch (error: any) {
      console.error('Error cargando inscripciones:', error);
      Alert.alert('Error', 'No se pudieron cargar las inscripciones.');
    } finally {
      setCargandoInscripciones(false);
    }
  }, [user]);

  const cargarNotasUsuario = useCallback(async () => {
    setCargandoNotas(true);
    try {
      const response = await api.get('/api/notas/usuario/autenticado/');
      const payload = response.data ?? {};
      let items: NotaItem[] = [];

      if (payload && typeof payload === 'object' && Array.isArray(payload.data)) items = payload.data;
      else if (Array.isArray(response.data)) items = response.data;
      else {
        if (payload.success === false) throw new Error(payload.message || 'No se pudieron cargar las notas');
        if (payload && payload.data && !Array.isArray(payload.data)) {
          const maybe = payload.data.items ?? payload.data.results ?? [];
          if (Array.isArray(maybe)) items = maybe;
        }
      }

      setNotasUsuario(items);
    } catch (error: any) {
      console.error('Error cargando notas:', error?.response ?? error);
      if (error.response?.status === 401) {
        Alert.alert('Error de autenticación', 'Por favor inicie sesión nuevamente');
      } else if (error.response?.status === 404) {
        Alert.alert('Perfil no encontrado', 'No se encontró el perfil de persona asociado a su usuario');
      } else {
        Alert.alert('Error', error.message ? String(error.message) : 'No se pudieron cargar las notas. Verifica tu conexión.');
      }
    } finally {
      setCargandoNotas(false);
    }
  }, []);

  useEffect(() => {
    if (modoDirecto && user) {
      cargarInscripcionesUsuario();
      cargarNotasUsuario();
    }
    if (notaData) {
      setNotaSeleccionada(notaData);
      setFormData(prev => ({ ...prev, idNota: String(notaData.idNota ?? ''), monto: toBackendDecimal(notaData.totalNota ?? 0) }));
      // si viene notaData y estás en modo automático, abre directamente modal pago
      if (!modoDirecto) {
        setShowPaymentModal(true);
      }
    }
  }, [modoDirecto, user, notaData, cargarNotasUsuario, cargarInscripcionesUsuario]);

  const onRefresh = async () => {
    setRefreshing(true);
    await Promise.all([cargarInscripcionesUsuario(), cargarNotasUsuario()]);
    setRefreshing(false);
  };

  const seleccionarNota = async (nota: NotaItem) => {
    setNotaSeleccionada(nota);
    setFormData(prev => ({ ...prev, idNota: String(nota.idNota ?? ''), monto: toBackendDecimal(nota.totalNota ?? 0) }));
    setErrors({});
    setShowDetailsModal(true);
    setShowPaymentModal(false);
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
    setNotaSeleccionada(null);
    setErrors({});
  };

  const validateForm = (): boolean => {
    const newErrors: { [key: string]: string } = {};
    if (!formData.idNota) newErrors.idNota = 'Debe seleccionar una nota';
    if (!formData.formaPago) newErrors.formaPago = 'Seleccione forma de pago';
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

  // ---------- PROCESAR PAGO (adaptado estrictamente al backend)
const handleProcesarPago = async () => {
  if (!validateForm()) {
    Alert.alert('Error', 'Por favor complete todos los campos requeridos');
    return;
  }

  setSubmitting(true);

  // payload compatible con el serializer (monto con 4 decimales aceptados por backend)
  const payload = {
    idNota: Number(formData.idNota),
    monto: Number(String(formData.monto).replace(',', '.')), // si el backend prefiere string con 4 decimales, ajusta abajo
    fechaPago: formData.fechaPago,
    formaPago: String(formData.formaPago),
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
      validateStatus: () => true // manejamos nosotros el status
    });

    console.log('[Pago] response.status:', response.status);

    // Si el servidor devolvió JSON
    const contentType = response.headers?.['content-type'] ?? response.headers?.['Content-Type'] ?? '';
    const isJson = typeof contentType === 'string' && contentType.toLowerCase().includes('application/json');

    if (isJson) {
      const body = response.data;
      console.log('[Pago] response.data (json):', body);

      if ((response.status === 201 || response.status === 200) && body?.success) {
        const d = body.data ?? {};
        Alert.alert('Pago procesado', `Pago registrado correctamente.\nAsiento: ${d.numeroAsiento ?? '—'}\nID Pago: ${d.idPago ?? '—'}\nMonto: ${d.monto ?? payload.monto}`, [{ text: 'OK' }]);
        // sincronizar en memoria y refrescar
        const idNotaNum = Number(payload.idNota);
        if (idNotaNum) setNotasUsuario(prev => prev.map(n => (Number(n.idNota) === idNotaNum ? { ...n, estado: 'PAGADA' } : n)));
        await Promise.all([cargarNotasUsuario(), cargarInscripcionesUsuario()]);
        setShowPaymentModal(false);
        setNotaSeleccionada(null);
      } else {
        // Backend devolvió JSON con success=false o error
        const msg = body.message ?? JSON.stringify(body);
        Alert.alert('Error', `Servidor: ${msg}`);
      }
    } else {
      // servidor devolvió HTML (error 500 renderizado como página) o texto no-JSON
      // mostrar los primeros 600 caracteres y pedir revisar logs del servidor
      const textBody = typeof response.data === 'string' ? response.data : JSON.stringify(response.data);
      console.warn('[Pago] Servidor devolvió texto/HTML en body. Primeros 600 chars:', textBody.slice(0, 600));
      Alert.alert(
        'Error del servidor',
        `El servidor devolvió una página de error (500). Por favor revisa los logs del backend.\nStatus: ${response.status}\nMás info en consola (primeros 600 chars).`
      );
      // opcional: abrir panel de debug (o enviar textBody a un endpoint de logs si existe)
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
      } else if (body.detail) {
        message = body.detail;
      }
      Alert.alert('Error de validación', message);
    } else if (resp?.status === 500) {
      Alert.alert('Error servidor', resp.data?.message ?? 'Error interno del servidor. Revisa logs.');
      console.error('[Pago] respuesta 500 (body):', resp.data);
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
    const estado = (item.estado ?? '').toUpperCase();
    const formacionName = getFormacionNameFromNota(item);
    return (
      <TouchableOpacity
        style={[styles.notaItem, notaSeleccionada?.idNota === item.idNota && styles.notaItemSeleccionada]}
        onPress={() => seleccionarNota(item)}
      >
        <View style={styles.notaHeader}>
          <Text style={styles.notaNumero}>{item.numeroNota ?? '—'}</Text>
          <View style={[
            styles.estadoBadge,
            estado === 'PAGADA' ? styles.estadoPagada : estado === 'PARCIAL' ? styles.estadoParcial : styles.estadoPendiente
          ]}>
            <Text style={styles.estadoText}>
              {estado === 'PAGADA' ? 'Pagada' : estado === 'PARCIAL' ? 'Parcial' : 'Pendiente'}
            </Text>
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
            <Text style={styles.seleccionadoText}>Seleccionada para pago</Text>
          </View>
        )}
      </TouchableOpacity>
    );
  };

  const modalMaxWidth = Math.min(Math.max(320, width - 48), 900);

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
            <View style={styles.loadingContainer}><Text style={styles.loadingText}>Cargando notas...</Text></View>
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
              keyExtractor={(item) => String(item.idNota ?? 'nota-' + Math.random().toString(36).slice(2, 9))}
              refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} colors={['#4f8cff']} tintColor="#4f8cff" />}
              contentContainerStyle={styles.listaContent}
              showsVerticalScrollIndicator={false}
            />
          )}
        </View>

        {/* MODAL DETALLE */}
        {notaSeleccionada && showDetailsModal && (
          <View style={styles.formularioOverlay}>
            <ScrollView contentContainerStyle={[styles.formScrollContent, { padding: 20 }]}>
              <View style={[styles.formCard, { width: modalMaxWidth, alignSelf: 'center' }]}>
                <View style={styles.formHeader}>
                  <View style={styles.formTitleContainer}>
                    <Icon name="file-document" size={24} color="#495057" />
                    <Text style={styles.formTitle}>Detalle de Nota</Text>
                  </View>
                  <TouchableOpacity onPress={cerrarModales} style={styles.cancelarBtn}>
                    <Icon name="close" size={22} color="#6c757d" />
                  </TouchableOpacity>
                </View>

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

                <View style={{ flexDirection: 'row', justifyContent: 'space-between', marginTop: 12 }}>
                  <TouchableOpacity style={[styles.submitButton, { backgroundColor: '#6c757d' }]} onPress={cerrarModales}>
                    <Text style={styles.submitButtonText}>Cerrar</Text>
                  </TouchableOpacity>
                  <TouchableOpacity style={styles.submitButton} onPress={iniciarPago}>
                    <Text style={styles.submitButtonText}>Iniciar Pago</Text>
                  </TouchableOpacity>
                </View>
              </View>
            </ScrollView>
          </View>
        )}

        {/* MODAL PAGO */}
        {notaSeleccionada && showPaymentModal && (
          <View style={styles.formularioOverlay}>
            <ScrollView contentContainerStyle={[styles.formScrollContent, { padding: 20 }]}>
              <View style={[styles.formCard, { width: modalMaxWidth, alignSelf: 'center' }]}>
                <View style={styles.formHeader}>
                  <View style={styles.formTitleContainer}>
                    <Icon name="credit-card-check" size={24} color="#28a745" />
                    <Text style={styles.formTitle}>Procesar Pago</Text>
                  </View>
                  <TouchableOpacity onPress={cerrarModales} style={styles.cancelarBtn}>
                    <Icon name="close" size={22} color="#6c757d" />
                  </TouchableOpacity>
                </View>

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

                <View style={styles.inputGroup}>
                  <Text style={styles.label}>Forma de Pago *</Text>
                  <View style={styles.radioGroup}>
                    {['TRANSFERENCIA', 'PAGO_MOVIL'].map(tipo => (
                      <TouchableOpacity key={tipo} style={[styles.radioOption, formData.formaPago === tipo && styles.radioOptionSelected]} onPress={() => handleInputChange('formaPago', tipo)}>
                        <View style={styles.radioContent}>
                          <View style={styles.radioCircle}>{formData.formaPago === tipo && <View style={styles.radioSelected} />}</View>
                          <Text style={[styles.radioLabel, formData.formaPago === tipo && styles.radioLabelSelected]}>{tipo === 'TRANSFERENCIA' ? 'Transferencia Bancaria' : 'Pago Móvil'}</Text>
                        </View>
                        <Icon name={tipo === 'TRANSFERENCIA' ? 'bank-transfer' : 'cellphone'} size={20} color={formData.formaPago === tipo ? '#4f8cff' : '#6c757d'} />
                      </TouchableOpacity>
                    ))}
                  </View>
                  {errors.formaPago && <View style={styles.errorContainer}><Icon name="alert-circle" size={16} color="#dc3545" /><Text style={styles.errorText}>{errors.formaPago}</Text></View>}
                </View>

                <View style={styles.inputGroup}>
                  <Text style={styles.label}>Monto a Pagar</Text>
                  <View style={styles.inputContainer}>
                    <Text style={styles.currencySymbol}>$</Text>
                    <TextInput style={[styles.input, styles.readOnlyInput]} value={formatCurrency(Number(notaSeleccionada.totalNota ?? 0))} editable={false} />
                  </View>
                </View>

                <View style={styles.inputGroup}>
                  <Text style={styles.label}>Número de Referencia *</Text>
                  <TextInput style={[styles.input, errors.referencia && styles.inputError]} value={formData.referencia} onChangeText={(v) => handleInputChange('referencia', v)} placeholder="Ej: 123456789" maxLength={40} placeholderTextColor="#6c757d" />
                  {errors.referencia && <View style={styles.errorContainer}><Icon name="alert-circle" size={16} color="#dc3545" /><Text style={styles.errorText}>{errors.referencia}</Text></View>}
                </View>

                <View style={styles.inputGroup}>
                  <Text style={styles.label}>Fecha de Pago *</Text>
                  <View style={styles.inputContainer}>
                    <Icon name="calendar" size={20} color="#6c757d" style={styles.inputIcon} />
                    <TextInput style={[styles.input, errors.fechaPago && styles.inputError]} value={formData.fechaPago} onChangeText={(v) => handleInputChange('fechaPago', v)} placeholder="AAAA-MM-DD" placeholderTextColor="#6c757d" />
                  </View>
                  {errors.fechaPago && <View style={styles.errorContainer}><Icon name="alert-circle" size={16} color="#dc3545" /><Text style={styles.errorText}>{errors.fechaPago}</Text></View>}
                </View>

                <View style={styles.inputGroup}>
                  <Text style={styles.label}>Observaciones</Text>
                  <TextInput style={[styles.input, styles.textArea]} value={formData.observaciones} onChangeText={(v) => handleInputChange('observaciones', v)} placeholder="Observaciones adicionales..." multiline numberOfLines={3} textAlignVertical="top" placeholderTextColor="#6c757d" />
                </View>

                {formData.formaPago === 'PAGO_MOVIL' && (
                  <View style={[styles.infoCard, { marginTop: 12 }]}>
                    <View style={styles.infoHeader}><Icon name="cellphone" size={18} color="#495057" /><Text style={styles.infoTitle}>Datos para Pago Móvil (demo)</Text></View>
                    <View style={{ marginTop: 8 }}>
                      <Text style={styles.infoLabel}>Banco: <Text style={styles.infoValueInline}>{pagoMovilInfo.banco}</Text></Text>
                      <Text style={styles.infoLabel}>Titular: <Text style={styles.infoValueInline}>{pagoMovilInfo.titular}</Text></Text>
                      <Text style={styles.infoLabel}>RIF: <Text style={styles.infoValueInline}>{pagoMovilInfo.rif}</Text></Text>
                      <Text style={styles.infoLabel}>Teléfono/Pay: <Text style={styles.infoValueInline}>{pagoMovilInfo.telefonoPagoMovil}</Text></Text>
                      <Text style={styles.infoLabel}>Cuenta: <Text style={styles.infoValueInline}>{pagoMovilInfo.numeroCuenta} ({pagoMovilInfo.tipoCuenta})</Text></Text>
                      <Text style={{ marginTop: 8, color: '#6c757d', fontSize: 12 }}>Nota: estos datos son de ejemplo. En producción se deben obtener desde su API de configuración.</Text>
                    </View>
                  </View>
                )}

                <TouchableOpacity style={[styles.submitButton, submitting && { opacity: 0.7 }]} onPress={handleProcesarPago} disabled={submitting}>
                  <View style={styles.submitButtonContent}>
                    {submitting ? <ActivityIndicator color="#fff" /> : <Icon name="arrow-right" size={20} color="#fff" />}
                    <Text style={styles.submitButtonText}>{submitting ? 'Procesando...' : 'Procesar Pago'}</Text>
                  </View>
                </TouchableOpacity>
              </View>
            </ScrollView>
          </View>
        )}
      </KeyboardAvoidingView>
    );
  }

  // modo automático (notaData)
  return (
    <KeyboardAvoidingView style={styles.container} behavior={Platform.OS === 'ios' ? 'padding' : 'height'}>
      <ScrollView style={styles.scrollView} contentContainerStyle={styles.formScrollContent}>
        <View style={styles.header}>
          <View style={styles.headerContent}>
            <Text style={styles.title}>Procesar Pago</Text>
            <Text style={styles.subtitle}>Complete los datos para registrar el pago</Text>
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

        <View style={[styles.formCard, { maxWidth: Math.min(920, width - 48), alignSelf: 'center' }]}>
          <View style={styles.formTitleContainer}><Icon name="credit-card-outline" size={24} color="#495057" /><Text style={styles.formTitle}>Datos del Pago</Text></View>

          <View style={styles.inputGroup}>
            <Text style={styles.label}>Forma de Pago *</Text>
            <View style={styles.radioGroup}>
              {['TRANSFERENCIA', 'PAGO_MOVIL'].map(tipo => (
                <TouchableOpacity key={tipo} style={[styles.radioOption, formData.formaPago === tipo && styles.radioOptionSelected]} onPress={() => handleInputChange('formaPago', tipo)}>
                  <View style={styles.radioContent}><View style={styles.radioCircle}>{formData.formaPago === tipo && <View style={styles.radioSelected} />}</View><Text style={[styles.radioLabel, formData.formaPago === tipo && styles.radioLabelSelected]}>{tipo === 'TRANSFERENCIA' ? 'Transferencia Bancaria' : 'Pago Móvil'}</Text></View>
                  <Icon name={tipo === 'TRANSFERENCIA' ? 'bank-transfer' : 'cellphone'} size={20} color={formData.formaPago === tipo ? '#4f8cff' : '#6c757d'} />
                </TouchableOpacity>
              ))}
            </View>
            {errors.formaPago && <View style={styles.errorContainer}><Icon name="alert-circle" size={16} color="#dc3545" /><Text style={styles.errorText}>{errors.formaPago}</Text></View>}
          </View>

          <View style={styles.inputGroup}>
            <Text style={styles.label}>Monto a Pagar</Text>
            <View style={styles.inputContainer}>
              <Text style={styles.currencySymbol}>$</Text>
              <TextInput
                style={[styles.input, styles.readOnlyInput]}
                value={formatCurrency(Number(notaSeleccionada?.totalNota ?? notaData?.totalNota ?? 0))}
                editable={false}
              />
            </View>
          </View>

          <View style={styles.inputGroup}>
            <Text style={styles.label}>Número de Referencia *</Text>
            <TextInput style={[styles.input, errors.referencia && styles.inputError]} value={formData.referencia} onChangeText={(v) => handleInputChange('referencia', v)} placeholder="Ej: 123456789" maxLength={40} placeholderTextColor="#6c757d" />
            {errors.referencia && <View style={styles.errorContainer}><Icon name="alert-circle" size={16} color="#dc3545" /><Text style={styles.errorText}>{errors.referencia}</Text></View>}
          </View>

          <View style={styles.inputGroup}>
            <Text style={styles.label}>Fecha de Pago *</Text>
            <View style={styles.inputContainer}>
              <Icon name="calendar" size={20} color="#6c757d" style={styles.inputIcon} />
              <TextInput style={[styles.input, errors.fechaPago && styles.inputError]} value={formData.fechaPago} onChangeText={(v) => handleInputChange('fechaPago', v)} placeholder="AAAA-MM-DD" placeholderTextColor="#6c757d" />
            </View>
            {errors.fechaPago && <View style={styles.errorContainer}><Icon name="alert-circle" size={16} color="#dc3545" /><Text style={styles.errorText}>{errors.fechaPago}</Text></View>}
          </View>

          <View style={styles.inputGroup}>
            <Text style={styles.label}>Observaciones</Text>
            <TextInput style={[styles.input, styles.textArea]} value={formData.observaciones} onChangeText={(v) => handleInputChange('observaciones', v)} placeholder="Observaciones adicionales..." multiline numberOfLines={3} textAlignVertical="top" placeholderTextColor="#6c757d" />
          </View>

          {formData.formaPago === 'PAGO_MOVIL' && (
            <View style={[styles.infoCard, { marginTop: 12 }]}>
              <View style={styles.infoHeader}><Icon name="cellphone" size={18} color="#495057" /><Text style={styles.infoTitle}>Datos para Pago Móvil (demo)</Text></View>
              <View style={{ marginTop: 8 }}>
                <Text style={styles.infoLabel}>Banco: <Text style={styles.infoValueInline}>{pagoMovilInfo.banco}</Text></Text>
                <Text style={styles.infoLabel}>Titular: <Text style={styles.infoValueInline}>{pagoMovilInfo.titular}</Text></Text>
                <Text style={styles.infoLabel}>RIF: <Text style={styles.infoValueInline}>{pagoMovilInfo.rif}</Text></Text>
                <Text style={styles.infoLabel}>Teléfono/Pay: <Text style={styles.infoValueInline}>{pagoMovilInfo.telefonoPagoMovil}</Text></Text>
                <Text style={styles.infoLabel}>Cuenta: <Text style={styles.infoValueInline}>{pagoMovilInfo.numeroCuenta} ({pagoMovilInfo.tipoCuenta})</Text></Text>
                <Text style={{ marginTop: 8, color: '#6c757d', fontSize: 12 }}>Nota: estos datos son de ejemplo. En producción se deben obtener desde su API de configuración.</Text>
              </View>
            </View>
          )}

          <TouchableOpacity style={[styles.submitButton, submitting && { opacity: 0.7 }]} onPress={handleProcesarPago} disabled={submitting}>
            <View style={styles.submitButtonContent}>
              {submitting ? <ActivityIndicator color="#fff" /> : <Icon name="arrow-right" size={20} color="#fff" />}
              <Text style={styles.submitButtonText}>{submitting ? 'Procesando...' : 'Procesar Pago'}</Text>
            </View>
          </TouchableOpacity>
        </View>
      </ScrollView>
    </KeyboardAvoidingView>
  );
};

function normalizarCedula(cedula: string): string {
  if (!cedula) return '';
  let normalizada = cedula.toString().toUpperCase().replace(/[\.\-\s]/g, '');
  if (/^[VEJG]/.test(normalizada)) {
    normalizada = normalizada.substring(1);
  }
  return normalizada;
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#f8f9fa' },
  scrollView: { flex: 1 },
  header: { flexDirection: 'row', padding: 16, alignItems: 'center', justifyContent: 'space-between' },
  headerContent: { flex: 1 },
  title: { fontSize: 20, fontWeight: '700', color: '#212529' },
  subtitle: { fontSize: 13, color: '#6c757d', marginTop: 4 },
  headerIcon: { marginLeft: 12 },
  listaContainer: { flex: 1, paddingHorizontal: 12, paddingBottom: 20 },
  listaContent: { paddingBottom: 120 },
  notaItem: { backgroundColor: '#fff', borderRadius: 8, padding: 12, marginVertical: 8, shadowColor: '#000', shadowOpacity: 0.03, elevation: 1 },
  notaItemSeleccionada: { borderColor: '#4f8cff', borderWidth: 1.5 },
  notaHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  notaNumero: { fontWeight: '700', color: '#343a40' },
  estadoBadge: { paddingHorizontal: 8, paddingVertical: 4, borderRadius: 12 },
  estadoText: { fontSize: 12, color: '#fff' },
  estadoPagada: { backgroundColor: '#28a745' },
  estadoParcial: { backgroundColor: '#ffc107' },
  estadoPendiente: { backgroundColor: '#dc3545' },
  notaFormacion: { marginTop: 8, color: '#495057' },
  notaFooter: { flexDirection: 'row', justifyContent: 'space-between', marginTop: 12 },
  notaFecha: { color: '#6c757d' },
  notaMonto: { fontWeight: '700', color: '#212529' },
  seleccionadoIndicator: { flexDirection: 'row', alignItems: 'center', marginTop: 8 },
  seleccionadoText: { marginLeft: 6, color: '#28a745' },

  formularioOverlay: { position: 'absolute', top: 0, left: 0, right: 0, bottom: 0, backgroundColor: 'rgba(0,0,0,0.35)', justifyContent: 'center', padding: 16 },
  formScrollContent: { paddingBottom: 40 },
  formCard: { backgroundColor: '#fff', borderRadius: 12, padding: 12, shadowColor: '#000', shadowOpacity: 0.05, elevation: 4 },
  formHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  formTitleContainer: { flexDirection: 'row', alignItems: 'center' },
  formTitle: { marginLeft: 8, fontWeight: '700', color: '#212529' },
  cancelarBtn: { padding: 6 },

  infoCard: { marginTop: 12, backgroundColor: '#f1f3f5', borderRadius: 8, padding: 10 },
  infoHeader: { flexDirection: 'row', alignItems: 'center' },
  infoTitle: { marginLeft: 8, fontWeight: '700', color: '#343a40' },
  infoGrid: { marginTop: 8 },
  infoItem: { marginBottom: 8 },
  infoLabel: { color: '#6c757d', fontSize: 13 },
  infoValue: { color: '#212529', fontWeight: '600' },
  infoValueInline: { color: '#212529', fontWeight: '700' },
  totalItem: { marginTop: 6 },
  totalLabel: { color: '#6c757d', fontWeight: '700' },
  totalValue: { color: '#212529', fontWeight: '900', fontSize: 16 },

  inputGroup: { marginTop: 12 },
  label: { marginBottom: 6, color: '#495057', fontWeight: '600' },
  inputContainer: { flexDirection: 'row', alignItems: 'center', backgroundColor: '#fff', borderRadius: 8, paddingHorizontal: 8, borderWidth: 1, borderColor: '#e9ecef' },
  currencySymbol: { marginRight: 6, color: '#495057' },
  input: { flex: 1, paddingVertical: 10, paddingHorizontal: 6, color: '#212529' },
  readOnlyInput: { backgroundColor: '#e9ecef' },
  inputError: { borderColor: '#dc3545', borderWidth: 1 },
  inputIcon: { marginRight: 8 },
  radioGroup: { marginTop: 6 },
  radioOption: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', paddingVertical: 8, paddingHorizontal: 10, borderRadius: 8, borderWidth: 1, borderColor: '#e9ecef', marginBottom: 8 },
  radioOptionSelected: { borderColor: '#4f8cff', backgroundColor: '#eef6ff' },
  radioContent: { flexDirection: 'row', alignItems: 'center' },
  radioCircle: { width: 18, height: 18, borderRadius: 9, borderWidth: 1.5, borderColor: '#6c757d', justifyContent: 'center', alignItems: 'center', marginRight: 10 },
  radioSelected: { width: 10, height: 10, borderRadius: 5, backgroundColor: '#4f8cff' },
  radioLabel: { color: '#495057' },
  radioLabelSelected: { fontWeight: '700' },

  textArea: { minHeight: 80 },
  submitButton: { marginTop: 16, backgroundColor: '#4f8cff', paddingVertical: 12, borderRadius: 8, alignItems: 'center', justifyContent: 'center' },
  submitButtonContent: { flexDirection: 'row', alignItems: 'center' },
  submitButtonText: { color: '#fff', marginLeft: 8, fontWeight: '700' },

  errorContainer: { flexDirection: 'row', alignItems: 'center', marginTop: 6 },
  errorText: { color: '#dc3545', marginLeft: 6 },

  loadingContainer: { padding: 20, alignItems: 'center' },
  loadingText: { color: '#6c757d' },

  emptyContainer: { alignItems: 'center', padding: 24 },
  emptyText: { fontSize: 16, fontWeight: '700', color: '#343a40', marginTop: 8 },
  emptySubtext: { color: '#6c757d', marginTop: 4 },
});

export default PagoScreen;
