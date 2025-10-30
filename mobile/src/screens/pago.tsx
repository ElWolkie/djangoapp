// src/screens/pago.tsx - VERSIÓN AJUSTADA (montos read-only, sin bancos/teléfono/foto)
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
} from 'react-native';
import { useNavigation, useRoute } from '@react-navigation/native';
import Icon from 'react-native-vector-icons/MaterialCommunityIcons';
import api from '../api/api';
import { AuthContext } from '../contexts/AuthContext';
import { ActivityIndicator } from 'react-native';

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
  // campo de ayuda local
  _resolvedFormacionName?: string | null;
  [k: string]: any;
}

interface Inscripcion {
  idInscripcion: number;
  estadoPago?: string;
  fechaInscripcion?: string;
  idPersona?: number;
  idPersona_detail?: {
    cedula?: string;
  };
  idCohorte?: any;  // Cohorte
  idFormacion_detail?: {
    idFormacion?: number;
    nombreFormacion?: string;
    valorInscripcion?: number | string;
  };
  montoPagado?: number;
  montoTotal?: number;
  saldoPendiente?: number;
}

const PagoScreen = () => {
  const navigation = useNavigation<any>();
  const route = useRoute<any>();
  const { user } = useContext(AuthContext);
  const { width } = useWindowDimensions();

  const { notaData, inscripcionId } = route.params || {};

  const [refreshing, setRefreshing] = useState(false);
  const [formData, setFormData] = useState({
    idNota: notaData?.idNota?.toString?.() ?? '',
    formaPago: 'TRANSFERENCIA',
    monto: notaData?.totalNota?.toString?.() ?? '',
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

  // Estados para inscripciones
  const [inscripcionesUsuario, setInscripcionesUsuario] = useState<Inscripcion[]>([]);
  const [cargandoInscripciones, setCargandoInscripciones] = useState(false);

  // Helpers ----------------------------------------------------------------
  const placeholderNames = new Set(['Formación no especificada', 'Información no disponible', '—', null, undefined, '']);

  const isValidFormacionName = (name?: string | null) => {
    if (!name) return false;
    const s = String(name).trim();
    if (!s) return false;
    if (placeholderNames.has(s)) return false;
    return true;
  };

  // Lógica limpia para extraer nombre de formación (solo de datos reales, sin manual)
  const getNombreFormacion = (inscripcion: Inscripcion): string => {
    // 1) idFormacion_detail (directo)
    const name1 = inscripcion.idFormacion_detail?.nombreFormacion;
    if (name1 && isValidFormacionName(name1)) return name1;

    // 2) cohorte.idFormacion (nested)
    const name2 = inscripcion.idCohorte?.idFormacion?.nombreFormacion || inscripcion.idCohorte?.idFormacion?.nombre;
    if (name2 && isValidFormacionName(name2)) return name2;

    // 3) Otros fields si existen (e.g., inscripcion.nombreFormacion si agregas)
    const name3 = (inscripcion as any).nombreFormacion;
    if (name3 && isValidFormacionName(name3)) return name3;

    return 'Formación no especificada';
  };

  // Función para mapear nota a su inscripción (mejorada)
  const findInscripcionForNota = (nota: NotaItem): Inscripcion | null => {
    console.log(`🔍 Buscando inscripción para nota ${nota.idNota}: fecha=${nota.fechaEmision}, monto=${nota.totalNota}, idIns=${nota.idInscripcion}`);

    // Prioridad 1: Por ID de inscripción
    const idIns = nota.idInscripcion ?? nota.idInscripcion_detail?.idInscripcion ?? nota.inscripcion_id ?? null;
    if (idIns) {
      const match = inscripcionesUsuario.find((ins) => ins.idInscripcion === Number(idIns));
      if (match) {
        console.log(`✅ Match por ID: ${match.idInscripcion}`);
        return match;
      }
    }

    // Prioridad 2: Por fecha cercana (+/- 1 día)
    if (nota.fechaEmision) {
      const notaDate = new Date(nota.fechaEmision).getTime();
      const match = inscripcionesUsuario.find((ins) => {
        if (ins.fechaInscripcion) {
          const insDate = new Date(ins.fechaInscripcion).getTime();
          const diff = Math.abs(notaDate - insDate);
          return diff < 86400000;  // 1 día
        }
        return false;
      });
      if (match) {
        console.log(`✅ Match por fecha: nota ${nota.fechaEmision} ~ ins ${match.fechaInscripcion}`);
        return match;
      }
    }

    // Prioridad 3: Por monto exacto (si unique)
    if (nota.totalNota) {
      const matches = inscripcionesUsuario.filter((ins) => Number(ins.montoTotal) === Number(nota.totalNota));
      if (matches.length === 1) {
        console.log(`✅ Match por monto unique: ${nota.totalNota}`);
        return matches[0];
      } else if (matches.length > 1) {
        console.warn(`⚠️ Múltiples matches por monto ${nota.totalNota}, usando primero`);
        return matches[0];
      }
    }

    // Fallback: Primera inscripción con estado pendiente o parcial
    const fallback = inscripcionesUsuario.find((ins) => ins.estadoPago !== 'PAGADO');
    if (fallback) {
      console.log(`📌 Fallback a primera pendiente: ${fallback.idInscripcion}`);
      return fallback;
    }

    console.warn(`⚠️ No match para nota ${nota.idNota}`);
    return null;
  };

  // getFormacionNameFromNota: Usa el mapper
  const getFormacionNameFromNota = (nota: NotaItem) => {
    if (!nota) return 'Formación no especificada';
    if (nota._resolvedFormacionName && isValidFormacionName(nota._resolvedFormacionName)) return nota._resolvedFormacionName;

    // Buscar inscripción matching y extraer nombre
    const ins = findInscripcionForNota(nota);
    if (ins) {
      const name = getNombreFormacion(ins);
      if (isValidFormacionName(name)) {
        nota._resolvedFormacionName = name;  // Cache
        return name;
      }
    }

    // Fallback si backend envió algo usable
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

      if (Array.isArray(data)) {
        items = data;
      } else if (data.results && Array.isArray(data.results)) {
        items = data.results;
      } else if (data.data && Array.isArray(data.data)) {
        items = data.data;
      }

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

  // Cargar notas del usuario
  const cargarNotasUsuario = useCallback(async () => {
    setCargandoNotas(true);
    try {
      const response = await api.get('/api/notas/usuario/autenticado/');
      console.log('📡 Raw notas response:', response.data);
      const payload = response.data ?? {};
      let items: NotaItem[] = [];

      if (payload && typeof payload === 'object' && Array.isArray(payload.data)) {
        items = payload.data;
      } else if (Array.isArray(response.data)) {
        items = response.data;
      } else {
        if (payload.success === false) {
          throw new Error(payload.message || 'No se pudieron cargar las notas');
        }
        if (payload && payload.data && !Array.isArray(payload.data)) {
          const maybe = payload.data.items ?? payload.data.results ?? [];
          if (Array.isArray(maybe)) items = maybe;
        }
      }

      console.log('🗂️ Items extraídos:', items.map(n => ({ id: n.idNota, fecha: n.fechaEmision, monto: n.totalNota })));

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
      setFormData(prev => ({ ...prev, idNota: String(notaData.idNota ?? ''), monto: String(notaData.totalNota ?? '') }));
    }
  }, [modoDirecto, user, notaData, cargarNotasUsuario, cargarInscripcionesUsuario]);

  const onRefresh = async () => {
    setRefreshing(true);
    await Promise.all([cargarInscripcionesUsuario(), cargarNotasUsuario()]);
    setRefreshing(false);
  };

  // Selección de nota por el usuario
  const seleccionarNota = async (nota: NotaItem) => {
    setNotaSeleccionada(nota);
    setFormData(prev => ({ ...prev, idNota: String(nota.idNota ?? ''), monto: String(nota.totalNota ?? '') }));
    setErrors({});
  };

  // Validaciones / submit
  const validateForm = (): boolean => {
    const newErrors: { [key: string]: string } = {};
    if (!formData.idNota) newErrors.idNota = 'Debe seleccionar una nota';
    if (!formData.formaPago) newErrors.formaPago = 'Seleccione forma de pago';
    if (!formData.monto || parseFloat(String(formData.monto)) <= 0) newErrors.monto = 'Monto debe ser mayor a 0';
    else if (notaSeleccionada && parseFloat(String(formData.monto)) > Number(notaSeleccionada.totalNota ?? 0))
      newErrors.monto = `El monto no puede ser mayor a $${formatCurrency(Number(notaSeleccionada.totalNota ?? 0))}`;
    if (!formData.referencia.trim()) newErrors.referencia = 'Número de referencia es requerido';
    if (!formData.fechaPago) newErrors.fechaPago = 'Fecha de pago es requerida';
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleInputChange = (field: string, value: string) => {
    setFormData(prev => ({ ...prev, [field]: value }));
    if (errors[field]) setErrors(prev => ({ ...prev, [field]: '' }));
  };

  const handleProcesarPago = async () => {
    if (!validateForm()) {
      Alert.alert('Error', 'Por favor complete todos los campos requeridos');
      return;
    }

    setSubmitting(true);
    try {
      const response = await api.post('/api/pagos/create/', formData);
      if (response.data.success) {
        Alert.alert('Éxito', response.data.message || 'Pago registrado correctamente.');
        setNotaSeleccionada(null);  // Cierra modal
        onRefresh();  // Recarga lista
      } else {
        Alert.alert('Error', response.data.message || 'Error al procesar pago');
      }
    } catch (error: any) {
      Alert.alert('Error', error.response?.data?.message || 'Error en la conexión');
    } finally {
      setSubmitting(false);
    }
  };

  const formatCurrency = (amount: number): string => {
    try {
      return new Intl.NumberFormat('es-VE', { minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(amount);
    } catch {
      return Number(amount || 0).toFixed(2);
    }
  };

  const formatDate = (dateString?: string): string => {
    if (!dateString) return '—';
    const d = new Date(dateString);
    if (isNaN(d.getTime())) return dateString;
    return d.toLocaleDateString('es-VE');
  };

  // Render --------------------------------------------------------------------------------
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

  // UI: modoDirecto (lista + modal)
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
              keyExtractor={(item) => String(item.idNota ?? Math.random())}
              refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} colors={['#4f8cff']} tintColor="#4f8cff" />}
              contentContainerStyle={styles.listaContent}
              showsVerticalScrollIndicator={false}
            />
          )}
        </View>

        {notaSeleccionada && (
          <View style={styles.formularioOverlay}>
            <ScrollView contentContainerStyle={[styles.formScrollContent, { padding: 20 }]}>
              <View style={[styles.formCard, { width: modalMaxWidth, alignSelf: 'center' }]}>
                <View style={styles.formHeader}>
                  <View style={styles.formTitleContainer}>
                    <Icon name="credit-card-check" size={24} color="#28a745" />
                    <Text style={styles.formTitle}>Procesar Pago</Text>
                  </View>
                  <TouchableOpacity onPress={() => setNotaSeleccionada(null)} style={styles.cancelarBtn}>
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

                {/* Forma, monto, referencia, etc. (idéntico a tu UI anterior) */}
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
                    <TextInput
                      style={[styles.input, { color: '#495057' }]}
                      value={formatCurrency(Number(notaSeleccionada.totalNota ?? 0))}
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

                <TouchableOpacity style={styles.submitButton} onPress={handleProcesarPago} disabled={submitting}>
                  <View style={styles.submitButtonContent}>
                    {submitting ? <ActivityIndicator color="#fff" /> : <Icon name="arrow-right" size={20} color="#fff" />}
                    <Text style={styles.submitButtonText}>{submitting ? 'Procesando...' : 'Continuar al Pago'}</Text>
                  </View>
                </TouchableOpacity>
              </View>
            </ScrollView>
          </View>
        )}
      </KeyboardAvoidingView>
    );
  }

  // modo automático (notaData proporcionada por params)
  return (
    <KeyboardAvoidingView style={styles.container} behavior={Platform.OS === 'ios' ? 'padding' : 'height'}>
      <ScrollView style={styles.scrollView} contentContainerStyle={styles.scrollContent}>
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
                value={formatCurrency(Number(notaSeleccionada?.totalNota ?? 0))}
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

          <TouchableOpacity style={styles.submitButton} onPress={handleProcesarPago} disabled={submitting}>
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

// Estilos aquí al final
const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#f8f9fa' },
  scrollView: { flex: 1 },
  scrollContent: { flexGrow: 1, paddingBottom: 40 },
  header: { backgroundColor: '#fff', padding: 20, borderBottomWidth: 1, borderBottomColor: '#e9ecef', flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  headerContent: { flex: 1 },
  headerIcon: { padding: 8, backgroundColor: '#f8f9fa', borderRadius: 12 },
  title: { fontSize: 26, fontWeight: 'bold', color: '#343a40', marginBottom: 4 },
  subtitle: { fontSize: 16, color: '#6c757d', fontWeight: '500' },
  readOnlyInput: { color: '#495057', backgroundColor: '#f8f9fa' },
  
  listaContainer: { flex: 1, padding: 16 },
  listaContent: { paddingBottom: 20 },

  loadingContainer: { flex: 1, justifyContent: 'center', alignItems: 'center', paddingVertical: 60 },
  loadingText: { marginTop: 12, color: '#6c757d', fontSize: 16, fontWeight: '500' },

  emptyContainer: { flex: 1, justifyContent: 'center', alignItems: 'center', paddingVertical: 80 },
  emptyText: { fontSize: 18, color: '#6c757d', fontWeight: '600', marginTop: 16, textAlign: 'center' },
  emptySubtext: { fontSize: 14, color: '#6c757d', textAlign: 'center', marginTop: 8, paddingHorizontal: 40, lineHeight: 20 },

  notaItem: { backgroundColor: '#fff', padding: 16, borderRadius: 12, marginBottom: 12, borderWidth: 2, borderColor: 'transparent' },
  notaItemSeleccionada: { borderColor: '#28a745', backgroundColor: '#f8fff9' },
  notaHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 },
  notaNumero: { fontSize: 16, fontWeight: '700', color: '#343a40' },
  estadoBadge: { paddingHorizontal: 12, paddingVertical: 6, borderRadius: 20 },
  estadoPendiente: { backgroundColor: '#fff3cd' },
  estadoParcial: { backgroundColor: '#d1ecf1' },
  estadoPagada: { backgroundColor: '#d4edda' },
  estadoText: { fontSize: 12, fontWeight: '700', color: '#000' },
  notaFormacion: { fontSize: 14, color: '#495057', marginBottom: 12, lineHeight: 20 },
  notaFooter: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  notaFecha: { fontSize: 13, color: '#6c757d', fontWeight: '500' },
  notaMonto: { fontSize: 16, fontWeight: 'bold', color: '#28a745' },

  seleccionadoIndicator: { flexDirection: 'row', alignItems: 'center', marginTop: 12, paddingTop: 12, borderTopWidth: 1, borderTopColor: '#e9ecef' },
  seleccionadoText: { marginLeft: 8, color: '#28a745', fontWeight: '600', fontSize: 14 },

  formularioOverlay: { position: 'absolute', top: 0, left: 0, right: 0, bottom: 0, backgroundColor: 'rgba(0,0,0,0.55)' },
  formScrollContent: { flexGrow: 1, justifyContent: 'center' },

  formCard: { backgroundColor: '#fff', borderRadius: 12, padding: 20, marginHorizontal: 12, shadowColor: '#000', shadowOffset: { width: 0, height: 4 }, shadowOpacity: 0.12, shadowRadius: 12, elevation: 6 },
  formHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 },
  formTitleContainer: { flexDirection: 'row', alignItems: 'center' },
  formTitle: { fontSize: 20, fontWeight: 'bold', marginLeft: 8 },
  cancelarBtn: { padding: 8, borderRadius: 8, backgroundColor: '#f8f9fa' },

  infoCard: { backgroundColor: '#fff', marginBottom: 16, padding: 12, borderRadius: 12, borderLeftWidth: 4, borderLeftColor: '#4f8cff' },
  infoHeader: { flexDirection: 'row', alignItems: 'center', marginBottom: 8 },
  infoTitle: { fontSize: 16, fontWeight: '700', marginLeft: 8 },
  infoGrid: { gap: 8 },
  infoItem: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'flex-start' },
  totalItem: { borderTopWidth: 1, borderTopColor: '#e9ecef', paddingTop: 12, marginTop: 6 },
  infoLabel: { fontSize: 14, color: '#6c757d', fontWeight: '500', flex: 1 },
  infoValue: { fontSize: 14, color: '#495057', fontWeight: '600', flex: 1, textAlign: 'right' },
  totalLabel: { fontSize: 16, fontWeight: '700', color: '#495057', flex: 1 },
  totalValue: { fontSize: 16, fontWeight: '700', color: '#28a745', flex: 1, textAlign: 'right' },

  inputGroup: { marginBottom: 16 },
  label: { fontSize: 15, fontWeight: '600', color: '#495057', marginBottom: 8 },
  inputContainer: { flexDirection: 'row', alignItems: 'center', borderWidth: 1, borderColor: '#ced4da', borderRadius: 8, backgroundColor: '#fff' },
  currencySymbol: { fontSize: 16, fontWeight: '600', color: '#495057', paddingHorizontal: 12, backgroundColor: '#f8f9fa', borderRightWidth: 1, borderRightColor: '#ced4da', height: 44, textAlignVertical: 'center' },
  inputIcon: { paddingHorizontal: 12 },
  input: { flex: 1, padding: 12, fontSize: 15, color: '#495057', minHeight: 44 },
  inputError: { borderColor: '#dc3545' },
  textArea: { height: 100 },
  helperText: { fontSize: 13, color: '#6c757d', marginTop: 6 },
  helperTextBold: { fontWeight: '700', color: '#495057' },

  radioGroup: { gap: 8 },
  radioOption: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', padding: 12, borderWidth: 1, borderColor: '#e9ecef', borderRadius: 8, backgroundColor: '#fff', marginBottom: 8 },
  radioOptionSelected: { borderColor: '#4f8cff', backgroundColor: '#f0f7ff' },
  radioContent: { flexDirection: 'row', alignItems: 'center', flex: 1 },
  radioCircle: { height: 20, width: 20, borderRadius: 10, borderWidth: 2, borderColor: '#ced4da', alignItems: 'center', justifyContent: 'center', marginRight: 12 },
  radioSelected: { height: 10, width: 10, borderRadius: 5, backgroundColor: '#4f8cff' },
  radioLabel: { fontSize: 15, color: '#495057', fontWeight: '500' },
  radioLabelSelected: { color: '#4f8cff', fontWeight: '700' },

  errorContainer: { flexDirection: 'row', alignItems: 'center', marginTop: 6 },
  errorText: { fontSize: 13, color: '#dc3545', marginLeft: 6, fontWeight: '600' },

  submitButton: { backgroundColor: '#28a745', padding: 12, borderRadius: 10, alignItems: 'center', marginTop: 8 },
  submitButtonContent: { flexDirection: 'row', alignItems: 'center' },
  submitButtonText: { color: '#fff', fontSize: 16, fontWeight: 'bold', marginLeft: 8 },
});

export default PagoScreen;