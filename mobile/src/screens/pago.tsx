// src/screens/pago.tsx - VERSIÓN CORREGIDA (resolución robusta de formación)
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

  // Helpers ----------------------------------------------------------------
  const placeholderNames = new Set(['Formación no especificada', 'Información no disponible', '—', null, undefined, '']);

  const isValidFormacionName = (name?: string | null) => {
    if (!name) return false;
    const s = String(name).trim();
    if (!s) return false;
    if (placeholderNames.has(s)) return false;
    return true;
  };

  const getFormacionNameFromNota = (nota: NotaItem) => {
    if (!nota) return 'Formación no especificada';
    if (nota._resolvedFormacionName && isValidFormacionName(nota._resolvedFormacionName)) return nota._resolvedFormacionName;
    if (nota.formacion && (nota.formacion.nombreFormacion || nota.formacion.nombre)) {
      const nm = nota.formacion.nombreFormacion ?? nota.formacion.nombre;
      if (isValidFormacionName(nm)) return nm;
    }
    if (nota.idFormacion_detail && (nota.idFormacion_detail.nombreFormacion || nota.idFormacion_detail.nombre)) {
      const nm = nota.idFormacion_detail.nombreFormacion ?? nota.idFormacion_detail.nombre;
      if (isValidFormacionName(nm)) return nm;
    }
    if (nota.formacionNombre) return nota.formacionNombre;
    if (nota.nombreFormacion) return nota.nombreFormacion;
    // fallback
    return 'Formación no especificada';
  };

  // Resuelve formacion a partir de una inscripcion obtenida por API
  const extractFormacionFromInscripcion = (ins: any): { idFormacion?: number; nombreFormacion?: string } | null => {
    if (!ins) return null;
    // campo idFormacion_detail directo
    const f = ins.idFormacion_detail ?? ins.idFormacion ?? null;
    if (f) {
      const name = f.nombreFormacion ?? f.nombre ?? (f.title ?? null);
      const id = Number(f.idFormacion ?? f.id ?? f.pk ?? 0) || undefined;
      return { idFormacion: id, nombreFormacion: name ?? undefined };
    }
    // intentar vía cohorte
    const coh = ins.idCohorte_detail ?? ins.idCohorte ?? ins.cohorte ?? null;
    if (coh) {
      const ff = coh.idFormacion ?? coh.idFormacion_detail ?? coh.formacion ?? null;
      if (ff) {
        const name = ff.nombreFormacion ?? ff.nombre ?? (ff.title ?? null);
        const id = Number(ff.idFormacion ?? ff.id ?? ff.pk ?? 0) || undefined;
        return { idFormacion: id, nombreFormacion: name ?? undefined };
      }
      // a veces coh contiene solo idFormacion numérico
      const idf = Number(coh.idFormacion ?? coh.id_formacion ?? 0) || undefined;
      if (idf) return { idFormacion: idf, nombreFormacion: undefined };
    }
    return null;
  };

  // Llama la API para obtener una inscripcion por id (si existe)
  const fetchInscripcionById = async (idInscripcion?: number | null) => {
    if (!idInscripcion) return null;
    try {
      const res = await api.get(`/api/inscripcion/${idInscripcion}/`);
      // si el endpoint no existe, intenta fallback a /api/inscripcion/ y filtrar
      if (res?.data) return res.data;
    } catch (e: any) {
      // fallback: traer lista y buscar
      try {
        const list = await api.get('/api/inscripcion/');
        const arr = Array.isArray(list.data) ? list.data : list.data?.results ?? [];
        const found = arr.find((it: any) => (Number(it.idInscripcion ?? it.id ?? it.pk ?? -1) === Number(idInscripcion)));
        return found ?? null;
      } catch (err) {
        return null;
      }
    }
    return null;
  };

  // Enriquecer una nota consultando su inscripcion si hace falta
  const enrichNotaWithFormacion = useCallback(async (nota: NotaItem): Promise<NotaItem> => {
    try {
      // si ya tiene nombre de formación válido devolvemos tal cual
      const existing = getFormacionNameFromNota(nota);
      if (isValidFormacionName(existing) && existing !== 'Formación no especificada') {
        return { ...nota, _resolvedFormacionName: existing };
      }

      // 1) si nota trae idInscripcion (campo agregado por serializer), pedir inscripcion
      const idIns = nota.idInscripcion ?? nota.idInscripcion_detail?.idInscripcion ?? nota.inscripcion_id ?? null;
      if (idIns) {
        const ins = await fetchInscripcionById(Number(idIns));
        if (ins) {
          const ff = extractFormacionFromInscripcion(ins);
          if (ff?.nombreFormacion && isValidFormacionName(ff.nombreFormacion)) {
            return { ...nota, _resolvedFormacionName: ff.nombreFormacion };
          }
          // si solo encontramos idFormacion, intentar obtener detalle formacion
          if (ff?.idFormacion) {
            try {
              const fdet = await api.get(`/api/formaciones/${ff.idFormacion}/`);
              const fdata = fdet?.data;
              if (fdata && (fdata.nombreFormacion || fdata.nombre)) {
                return { ...nota, _resolvedFormacionName: fdata.nombreFormacion ?? fdata.nombre };
              }
            } catch (err) {
              // ignore
            }
          }
        }
      }

      // 2) si nota tiene idInscripcion_detail embebido, usarlo
      if (nota.idInscripcion_detail) {
        const ff = extractFormacionFromInscripcion(nota.idInscripcion_detail);
        if (ff?.nombreFormacion && isValidFormacionName(ff.nombreFormacion)) {
          return { ...nota, _resolvedFormacionName: ff.nombreFormacion };
        }
      }

      // 3) si en params nos pasaron inscripcionId (creada justo ahora), intentar resolver con ese id
      if (inscripcionId) {
        const ins = await fetchInscripcionById(Number(inscripcionId));
        if (ins) {
          const ff = extractFormacionFromInscripcion(ins);
          if (ff?.nombreFormacion && isValidFormacionName(ff.nombreFormacion)) {
            return { ...nota, _resolvedFormacionName: ff.nombreFormacion };
          }
        }
      }

      // no se pudo resolver -> marcar como no especificada
      return { ...nota, _resolvedFormacionName: 'Formación no especificada' };
    } catch (e) {
      // en error, devolver nota original para no romper la lista
      return { ...nota, _resolvedFormacionName: nota._resolvedFormacionName ?? nota.formacion?.nombreFormacion ?? 'Formación no especificada' };
    }
  }, [inscripcionId]);

  // Cargar notas del usuario y enriquecer las que lo necesiten
  const cargarNotasUsuario = useCallback(async () => {
    setCargandoNotas(true);
    try {
      const response = await api.get('/api/notas/usuario/autenticado/');
      const payload = response.data ?? {};
      let items: any[] = [];

      if (payload && typeof payload === 'object' && Array.isArray(payload.data)) {
        items = payload.data;
      } else if (Array.isArray(response.data)) {
        items = response.data;
      } else {
        if (payload.success === false) {
          throw new Error(payload.message || 'No se pudieron cargar las notas');
        }
        // si el shape es otro (ej: { success: true, data: {...}}), intentar forzar
        if (payload && payload.data && !Array.isArray(payload.data)) {
          // si devolvió un objeto con lista en payload.data.items
          const maybe = payload.data.items ?? payload.data.results ?? [];
          if (Array.isArray(maybe)) items = maybe;
        }
      }

      // enriquecer solo las notas que no tienen formacion válida
      const enrichedPromises = items.map(async (n: NotaItem) => {
        try {
          // normalizar campos comunes: idInscripcion puede venir en form diferente
          const normalized: NotaItem = {
            ...n,
            idInscripcion: n.idInscripcion ?? n.idInscripcion_detail?.idInscripcion ?? n.inscripcion_id ?? n.idInscripcionId ?? n.idInscripcionPk ?? n.inscripcion ?? n.idInscripcion,
          };
          // if already has a valid formacion string, just set helper
          const maybeName = getFormacionNameFromNota(normalized);
          if (isValidFormacionName(maybeName)) {
            return { ...normalized, _resolvedFormacionName: maybeName };
          }
          // otherwise try to enrich
          const enriched = await enrichNotaWithFormacion(normalized);
          return enriched;
        } catch (err) {
          return n;
        }
      });

      const enrichedItems = await Promise.all(enrichedPromises);
      setNotasUsuario(enrichedItems);
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
  }, [enrichNotaWithFormacion]);

  useEffect(() => {
    if (modoDirecto && user) {
      cargarNotasUsuario();
    }
    // sincronizar notaData si viene por params
    if (notaData) {
      (async () => {
        const resolved = await enrichNotaWithFormacion(notaData);
        setNotaSeleccionada(resolved);
        setFormData(prev => ({ ...prev, idNota: String(resolved.idNota ?? ''), monto: String(resolved.totalNota ?? '') }));
      })();
    }
  }, [modoDirecto, user, notaData, cargarNotasUsuario, enrichNotaWithFormacion]);

  const onRefresh = async () => {
    setRefreshing(true);
    await cargarNotasUsuario();
    setRefreshing(false);
  };

  // Selección de nota por el usuario
  const seleccionarNota = async (nota: NotaItem) => {
    // si la nota no tiene nombre resuelto intentar enriquecer justo ahora (mejor UX)
    if (!nota._resolvedFormacionName || !isValidFormacionName(nota._resolvedFormacionName)) {
      const enriched = await enrichNotaWithFormacion(nota);
      // actualizar lista por si queremos usarla luego
      setNotasUsuario(prev => prev.map(p => (p.idNota === enriched.idNota ? enriched : p)));
      setNotaSeleccionada(enriched);
      setFormData(prev => ({ ...prev, idNota: String(enriched.idNota ?? ''), monto: String(enriched.totalNota ?? '') }));
      setErrors({});
      return;
    }
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

  const handleProcesarPago = () => {
    if (!validateForm()) {
      Alert.alert('Error', 'Por favor complete todos los campos requeridos');
      return;
    }
    const pagoParams = {
      monto: parseFloat(String(formData.monto)),
      referencia: formData.referencia,
      formaPago: formData.formaPago,
      notaData: notaSeleccionada ?? notaData,
      userData: user
        ? {
            nombre: user.nombre ?? user.nombres ?? '',
            cedula: user.cedula ?? '',
            telefono: user.telefono ?? '',
          }
        : undefined,
    };
    navigation.navigate('PagoMovilFicticio', pagoParams);
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
          {cargandoNotas ? (
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
                  <Text style={styles.label}>Monto a Pagar *</Text>
                  <View style={styles.inputContainer}>
                    <Text style={styles.currencySymbol}>$</Text>
                    <TextInput style={[styles.input, errors.monto && styles.inputError]} value={formData.monto} onChangeText={(v) => handleInputChange('monto', v)} placeholder="0.00" keyboardType="numeric" placeholderTextColor="#6c757d" />
                  </View>
                  <Text style={styles.helperText}>Máximo permitido: <Text style={styles.helperTextBold}>${formatCurrency(Number(notaSeleccionada.totalNota ?? 0))}</Text></Text>
                  {errors.monto && <View style={styles.errorContainer}><Icon name="alert-circle" size={16} color="#dc3545" /><Text style={styles.errorText}>{errors.monto}</Text></View>}
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

                <TouchableOpacity style={styles.submitButton} onPress={handleProcesarPago}>
                  <View style={styles.submitButtonContent}><Icon name="arrow-right" size={20} color="#fff" /><Text style={styles.submitButtonText}>Continuar al Pago</Text></View>
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
          {/* ... mismo formulario que en modo directo (omito por brevedad, ya está arriba) */}
          <View style={styles.formTitleContainer}><Icon name="credit-card-outline" size={24} color="#495057" /><Text style={styles.formTitle}>Datos del Pago</Text></View>

          {/* Forma de pago */}
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

          {/* monto, referencia, fecha, observaciones... (igual que arriba) */}
          <View style={styles.inputGroup}>
            <Text style={styles.label}>Monto a Pagar *</Text>
            <View style={styles.inputContainer}><Text style={styles.currencySymbol}>$</Text><TextInput style={[styles.input, errors.monto && styles.inputError]} value={formData.monto} onChangeText={(v) => handleInputChange('monto', v)} placeholder="0.00" keyboardType="numeric" placeholderTextColor="#6c757d" /></View>
            <Text style={styles.helperText}>Máximo permitido: <Text style={styles.helperTextBold}>${formatCurrency(Number(notaData?.totalNota ?? 0))}</Text></Text>
            {errors.monto && <View style={styles.errorContainer}><Icon name="alert-circle" size={16} color="#dc3545" /><Text style={styles.errorText}>{errors.monto}</Text></View>}
          </View>

          <View style={styles.inputGroup}>
            <Text style={styles.label}>Número de Referencia *</Text>
            <TextInput style={[styles.input, errors.referencia && styles.inputError]} value={formData.referencia} onChangeText={(v) => handleInputChange('referencia', v)} placeholder="Ej: 123456789" maxLength={40} placeholderTextColor="#6c757d" />
            {errors.referencia && <View style={styles.errorContainer}><Icon name="alert-circle" size={16} color="#dc3545" /><Text style={styles.errorText}>{errors.referencia}</Text></View>}
          </View>

          <View style={styles.inputGroup}>
            <Text style={styles.label}>Fecha de Pago *</Text>
            <View style={styles.inputContainer}><Icon name="calendar" size={20} color="#6c757d" style={styles.inputIcon} /><TextInput style={[styles.input, errors.fechaPago && styles.inputError]} value={formData.fechaPago} onChangeText={(v) => handleInputChange('fechaPago', v)} placeholder="AAAA-MM-DD" placeholderTextColor="#6c757d" /></View>
            {errors.fechaPago && <View style={styles.errorContainer}><Icon name="alert-circle" size={16} color="#dc3545" /><Text style={styles.errorText}>{errors.fechaPago}</Text></View>}
          </View>

          <View style={styles.inputGroup}>
            <Text style={styles.label}>Observaciones</Text>
            <TextInput style={[styles.input, styles.textArea]} value={formData.observaciones} onChangeText={(v) => handleInputChange('observaciones', v)} placeholder="Observaciones adicionales..." multiline numberOfLines={3} textAlignVertical="top" placeholderTextColor="#6c757d" />
          </View>

          <TouchableOpacity style={styles.submitButton} onPress={handleProcesarPago}>
            <View style={styles.submitButtonContent}><Icon name="arrow-right" size={20} color="#fff" /><Text style={styles.submitButtonText}>Continuar al Pago</Text></View>
          </TouchableOpacity>
        </View>
      </ScrollView>
    </KeyboardAvoidingView>
  );
};

// --- estilos (copié los tuyos anteriores; ajústalos si quieres) ---
const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#f8f9fa' },
  scrollView: { flex: 1 },
  scrollContent: { flexGrow: 1, paddingBottom: 40 },
  header: { backgroundColor: '#fff', padding: 20, borderBottomWidth: 1, borderBottomColor: '#e9ecef', flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  headerContent: { flex: 1 },
  headerIcon: { padding: 8, backgroundColor: '#f8f9fa', borderRadius: 12 },
  title: { fontSize: 26, fontWeight: 'bold', color: '#343a40', marginBottom: 4 },
  subtitle: { fontSize: 16, color: '#6c757d', fontWeight: '500' },

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
