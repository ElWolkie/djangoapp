// src/screens/inscripciones.tsx
import React, { useCallback, useEffect, useState, useContext } from 'react';
import {
  View,
  Text,
  FlatList,
  ActivityIndicator,
  StyleSheet,
  Dimensions,
  TouchableOpacity,
  TextInput,
  ScrollView,
  KeyboardAvoidingView,
  Platform,
  Alert,
} from 'react-native';
import Icon from 'react-native-vector-icons/MaterialCommunityIcons';
import Modal from 'react-native-modal';
import { Picker } from '@react-native-picker/picker';
import api from '../api/api';
import { AuthContext } from '../contexts/AuthContext';
import {
  TipoFormacion,
  Formacion,
  Cohorte,
  Inscripcion,
  Cuota
} from '../types/inscripciones';

const { width, height } = Dimensions.get('window');

const fmtMoney = (v: any) => {
  const n = Number(v);
  if (!isFinite(n)) return '—';
  return `$${n.toFixed(2)}`;
};

export default function PantallaInscripciones() {
  const { user } = useContext(AuthContext);
  const [items, setItems] = useState<Inscripcion[]>([]);
  const [mostradas, setMostradas] = useState<Inscripcion[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchText, setSearchText] = useState('');
  const [detailModalVisible, setDetailModalVisible] = useState(false);
  const [selected, setSelected] = useState<Inscripcion | null>(null);
  const [formModalVisible, setFormModalVisible] = useState(false);
  const [creating, setCreating] = useState(false);

  const [tiposFormacion, setTiposFormacion] = useState<TipoFormacion[]>([]);
  const [formaciones, setFormaciones] = useState<Formacion[]>([]);
  const [formacionesFiltradas, setFormacionesFiltradas] = useState<Formacion[]>([]);
  const [cohortes, setCohortes] = useState<Cohorte[]>([]);
  
  const [selectedTipoFormacion, setSelectedTipoFormacion] = useState<number | null>(null);
  const [selectedFormacion, setSelectedFormacion] = useState<number | null>(null);
  const [selectedCohorte, setSelectedCohorte] = useState<number | null>(null);
  
  const [valorInscripcion, setValorInscripcion] = useState(0);
  const [cuotas, setCuotas] = useState<Cuota[]>([]);
  const [totalCuotas, setTotalCuotas] = useState(0);
  const [montoTotal, setMontoTotal] = useState(0);
  
  const [formErrors, setFormErrors] = useState<Record<string,string>>({});

  const fetchInscripciones = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.get('/api/inscripcion/');
      const data = Array.isArray(res.data) ? res.data : (res.data.results ?? []);
      setItems(data);
      setMostradas(data);
    } catch (e: any) {
      console.error('fetchInscripciones error', e);
      setError(e?.response?.data?.detail ?? e?.message ?? 'Error al cargar inscripciones');
    } finally {
      setLoading(false);
    }
  }, []);

  const fetchDatosFormulario = useCallback(async () => {
    try {
      const [r1, r2, r3] = await Promise.all([
        api.get('/api/tipo-formaciones/'),
        api.get('/api/formaciones/'),
        api.get('/api/cohorte/'),
      ]);

      const extractData = (responseData: any, tipo: 'tipos' | 'formaciones' | 'cohortes') => {
        let dataArray = responseData.data?.results || responseData.data || responseData;
        if (!Array.isArray(dataArray)) dataArray = [];

        return dataArray.map((item: any) => {
          if (tipo === 'tipos') return {
            idTF: Number(item.idTF),
            nombreTipoFormacion: item.nombreTipoFormacion,
          };
          if (tipo === 'formaciones') return {
            idFormacion: Number(item.idFormacion),
            nombreFormacion: item.nombreFormacion,
            idTF: Number(item.idTF),
            valorInscripcion: Number(item.valorInscripcion),
            tieneCuotas: Boolean(item.tieneCuotas),
            cuotas_activas: Boolean(item.cuotas_activas),
            cantidad_cuotas: Number(item.cantidad_cuotas),
            cuotas_json: item.cuotas_json || '[]',
          };
          if (tipo === 'cohortes') return {
            idCohorte: Number(item.idCohorte),
            nombreCohorte: item.nombreCohorte,
          };
          return item;
        });
      };

      setTiposFormacion(extractData(r1, 'tipos'));
      setFormaciones(extractData(r2, 'formaciones'));
      setCohortes(extractData(r3, 'cohortes'));

    } catch (e) {
      console.error('Error crítico en fetchDatosFormulario:', e);
      Alert.alert('Error', 'No se pudieron cargar los datos del formulario');
    }
  }, []);

  useEffect(() => {
    fetchInscripciones();
    fetchDatosFormulario();
  }, [fetchInscripciones, fetchDatosFormulario]);

  // CORRECCIÓN CLAVE: El origen del problema estaba aquí.
  useEffect(() => {
    console.log('🔄 Filtrando formaciones...');
    console.log(`Tipo seleccionado: ${selectedTipoFormacion} (tipo: ${typeof selectedTipoFormacion})`);
    
    if (selectedTipoFormacion !== null) {
      // Convertimos el tipo seleccionado a Número para una comparación estricta.
      const tipoIdNumero = Number(selectedTipoFormacion);
      
      const filtradas = formaciones.filter(f => {
        const match = f.idTF === tipoIdNumero; // Ahora la comparación es number === number
        console.log(`Formación: ${f.nombreFormacion}, idTF: ${f.idTF}, comparando con ${tipoIdNumero}, match: ${match}`);
        return match;
      });
      console.log('✅ Formaciones filtradas:', filtradas.length);
      setFormacionesFiltradas(filtradas);
      setSelectedFormacion(null); // Resetea la selección de formación
    } else {
      setFormacionesFiltradas(formaciones);
    }
  }, [selectedTipoFormacion, formaciones]);
  
  useEffect(() => {
    if (selectedFormacion !== null) {
      const formacion = formaciones.find(f => f.idFormacion === selectedFormacion);
      if (formacion) {
        const valorInsc = Number(formacion.valorInscripcion) || 0;
        setValorInscripcion(valorInsc);
        
        let cuotasData: Cuota[] = [];
        let totalCtas = 0;
        if (formacion.tieneCuotas && formacion.cuotas_activas) {
          try {
            cuotasData = JSON.parse(formacion.cuotas_json);
            totalCtas = cuotasData.reduce((sum, cuota) => sum + Number(cuota.valorCuota || 0), 0);
          } catch (e) { console.error('Error parsing cuotas JSON', e); }
        }
        setCuotas(cuotasData);
        setTotalCuotas(totalCtas);
        setMontoTotal(valorInsc + totalCtas);
      }
    } else {
      // Resetea costos si no hay formación seleccionada
      setValorInscripcion(0);
      setCuotas([]);
      setTotalCuotas(0);
      setMontoTotal(0);
    }
  }, [selectedFormacion, formaciones]);

  // (El resto de tu código de filtrado de búsqueda, modales, etc., está bien y no necesita cambios)
  // ... (handleCreateInscripcion, resetForm, renderItem, etc.)

  const handleCreateInscripcion = async () => {
    // Validaciones
    const errs: Record<string,string> = {};
    if (selectedTipoFormacion === null) errs.tipo = 'Seleccione un tipo';
    if (selectedFormacion === null) errs.formacion = 'Seleccione una formación';
    if (selectedCohorte === null) errs.cohorte = 'Seleccione una cohorte';
    if (!user?.idPersona) errs.usuario = 'No se pudo identificar al usuario.';
    
    setFormErrors(errs);
    if (Object.keys(errs).length > 0) {
      Alert.alert('Formulario Incompleto', 'Por favor, complete todos los campos requeridos.');
      return;
    }
    
    if (montoTotal <= 0) {
      Alert.alert('Error de Costo', 'La formación seleccionada no tiene un costo válido.');
      return;
    }

    setCreating(true);
    try {
      const payload = {
        idPersona: user!.idPersona,
        idTF: selectedTipoFormacion,
        idFormacion: selectedFormacion,
        idCohorte: selectedCohorte,
        montoTotal: montoTotal,
        montoPagado: 0,
        estadoPago: 'PENDIENTE',
        fechaInscripcion: new Date().toISOString().slice(0, 19).replace('T', ' '),
      };
      
      console.log('📤 Enviando payload:', payload);
      const res = await api.post('/api/inscripcion/', payload);

      Alert.alert('Éxito', 'Inscripción creada correctamente.');
      setFormModalVisible(false);
      resetForm();
      await fetchInscripciones();

    } catch (err: any) {
      console.error('❌ ERROR AL CREAR INSCRIPCIÓN:', err.response?.data || err.message);
      Alert.alert('Error', err.response?.data?.detail || 'No se pudo crear la inscripción.');
    } finally {
      setCreating(false);
    }
  };

  const resetForm = () => {
    setSelectedTipoFormacion(null);
    setSelectedFormacion(null);
    setSelectedCohorte(null);
    setFormErrors({});
  };

  const deriveStatus = (item: any) => {
    if (String(item.estadoPago ?? '').toUpperCase() === 'PAGADO') return 'PAGADO';
    const paid = Number(item.montoPagado ?? 0) || 0;
    const total = Number(item.montoTotal ?? 0) || 0;
    if (total > 0 && paid >= total) return 'PAGADO';
    if (paid > 0 && paid < total) return 'PARCIAL';
    return (item.estadoPago ?? 'PENDIENTE') as string;
  };

  const statusColor = (status: string) => {
    if (status === 'PAGADO') return styles.badgeActive;
    if (status === 'PARCIAL') return styles.badgePartial;
    return styles.badgeInactive;
  };
  
  const openDetail = (it: Inscripcion) => {
    setSelected(it);
    setDetailModalVisible(true);
  };
  
  useEffect(() => {
    const q = searchText.trim().toLowerCase();
    if (!q) {
      setMostradas(items);
      return;
    }
    setMostradas(items.filter(i => {
      const ced = (i.idPersona?.cedula ?? '').toString().toLowerCase();
      const form = (i.idFormacion?.nombreFormacion ?? '').toString().toLowerCase();
      const coh = (i.idCohorte?.nombreCohorte ?? '').toString().toLowerCase();
      const estado = (i.estadoPago ?? '').toString().toLowerCase();
      return ced.includes(q) || form.includes(q) || coh.includes(q) || estado.includes(q);
    }));
  }, [searchText, items]);

  if (loading) return <View style={styles.center}><ActivityIndicator size="large" color="#4f8cff" /></View>;
  if (error) return <View style={styles.center}><Text style={styles.errorText}>{error}</Text></View>;

  return (
    <View style={styles.container}>
        <View style={styles.header}>
            <Text style={styles.title}>Inscripciones</Text>
            <TouchableOpacity style={styles.addButton} onPress={() => setFormModalVisible(true)}>
                <Icon name="plus" size={24} color="#fff" />
                <Text style={styles.addButtonText}>Nueva</Text>
            </TouchableOpacity>
        </View>

        <View style={styles.searchContainer}>
            <View style={styles.searchWrapper}>
                <Icon name="magnify" size={20} color="#666" />
                <TextInput
                    placeholder="Buscar por cédula, formación, cohorte o estado..."
                    value={searchText}
                    onChangeText={setSearchText}
                    style={styles.searchInput}
                    placeholderTextColor="#999"
                />
            </View>
        </View>

        <FlatList
            data={mostradas}
            keyExtractor={(i) => String(i.idInscripcion ?? i.id ?? Math.random())}
            renderItem={({item}) => {
                const status = deriveStatus(item);
                return (
                    <View style={styles.card}>
                        <View style={styles.cardHeader}>
                            <View style={styles.cardTitleContainer}>
                                <Text style={styles.cardTitle} numberOfLines={1}>
                                    {item.idFormacion?.nombreFormacion ?? '—'}
                                </Text>
                                <View style={[styles.badge, statusColor(status)]}>
                                    <Text style={styles.badgeText}>{status}</Text>
                                </View>
                            </View>
                            <Text style={styles.cardSubtitle}>
                                {item.idPersona?.nombres} {item.idPersona?.apellidos}
                            </Text>
                        </View>

                        <View style={styles.cardContent}>
                            <View style={styles.detailRow}>
                                <View style={styles.detailItem}>
                                    <Icon name="id-card" size={16} color="#666" />
                                    <Text style={styles.detailText}>{item.idPersona?.cedula ?? '—'}</Text>
                                </View>
                                <View style={styles.detailItem}>
                                    <Icon name="domain" size={16} color="#666" />
                                    <Text style={styles.detailText}>{item.idCohorte?.nombreCohorte ?? '—'}</Text>
                                </View>
                            </View>
                            <View style={styles.detailRow}>
                                <View style={styles.detailItem}>
                                    <Icon name="cash" size={16} color="#666" />
                                    <Text style={styles.detailText}>{fmtMoney(item.montoTotal)}</Text>
                                </View>
                                <View style={styles.detailItem}>
                                    <Icon name="calendar" size={16} color="#666" />
                                    <Text style={styles.detailText}>{item.fechaInscripcion ?? '—'}</Text>
                                </View>
                            </View>
                        </View>

                        <TouchableOpacity style={styles.cardButton} onPress={() => openDetail(item)}>
                            <Text style={styles.cardButtonText}>Ver detalles</Text>
                            <Icon name="chevron-right" size={20} color="#4f8cff" />
                        </TouchableOpacity>
                    </View>
                );
            }}
            contentContainerStyle={styles.listContent}
            ListEmptyComponent={
                <View style={styles.emptyState}>
                    <Icon name="clipboard-text-outline" size={64} color="#ccc" />
                    <Text style={styles.emptyText}>No hay inscripciones registradas</Text>
                </View>
            }
        />

        <Modal 
            isVisible={detailModalVisible} 
            onBackdropPress={() => setDetailModalVisible(false)}
            style={styles.modal}
        >
            <View style={styles.modalContent}>
                <View style={styles.modalHeader}>
                    <Text style={styles.modalTitle}>Detalles de Inscripción</Text>
                    <TouchableOpacity style={styles.closeButton} onPress={() => setDetailModalVisible(false)}>
                        <Icon name="close" size={24} color="#666" />
                    </TouchableOpacity>
                </View>
                <ScrollView style={styles.modalBody}>
                    {selected && [
                        ['Formación', selected.idFormacion?.nombreFormacion ?? '—'],
                        ['Cohorte', selected.idCohorte?.nombreCohorte ?? '—'],
                        ['Cédula', selected.idPersona?.cedula ?? '—'],
                        ['Nombres', selected.idPersona?.nombres ?? '—'],
                        ['Apellidos', selected.idPersona?.apellidos ?? '—'],
                        ['Fecha inscripción', selected.fechaInscripcion ?? '—'],
                        ['Estado pago', deriveStatus(selected)],
                        ['Monto total', fmtMoney(selected.montoTotal)],
                        ['Monto pagado', fmtMoney(selected.montoPagado)],
                        ['Saldo pendiente', fmtMoney(selected.saldoPendiente)],
                        ['Activo', selected.is_active ? 'Sí' : 'No'],
                    ].map(([lbl,val]) => (
                        <View key={String(lbl)} style={styles.detailRowModal}>
                            <Text style={styles.detailLabel}>{lbl}:</Text>
                            <Text style={styles.detailValue}>{String(val)}</Text>
                        </View>
                    ))}
                </ScrollView>
                <View style={styles.modalFooter}>
                    <TouchableOpacity style={styles.modalButton} onPress={() => setDetailModalVisible(false)}>
                        <Text style={styles.modalButtonText}>Cerrar</Text>
                    </TouchableOpacity>
                </View>
            </View>
        </Modal>

        <Modal isVisible={formModalVisible} onBackdropPress={() => setFormModalVisible(false)} style={styles.modal}>
            <KeyboardAvoidingView behavior={Platform.OS === 'ios' ? 'padding' : 'height'} style={styles.keyboardAvoid}>
                <View style={styles.formModal}>
                    <View style={styles.modalHeader}>
                        <Text style={styles.modalTitle}>Nueva Inscripción</Text>
                        <TouchableOpacity style={styles.closeButton} onPress={() => setFormModalVisible(false)}>
                            <Icon name="close" size={24} color="#666" />
                        </TouchableOpacity>
                    </View>

                    <ScrollView style={styles.formBody} showsVerticalScrollIndicator={false} contentContainerStyle={styles.formContent}>
                        <View style={styles.formSection}>
                            <Text style={styles.sectionTitle}>Información Personal</Text>
                            <View style={styles.fieldContainer}>
                                <Text style={styles.label}>Cédula del Cliente</Text>
                                <View style={styles.cedulaFijaContainer}>
                                    <Icon name="account" size={20} color="#4f8cff" />
                                    <Text style={styles.cedulaFijaText}>
                                        {user?.cedula || 'No se pudo cargar la cédula'}
                                    </Text>
                                </View>
                            </View>
                        </View>

                        <Text style={styles.label}>Tipo de Formación *</Text>
                        <View style={styles.pickerContainer}>
                            <Picker
                                selectedValue={selectedTipoFormacion}
                                onValueChange={(itemValue) => {
                                    setSelectedTipoFormacion(itemValue);
                                    setSelectedFormacion(null);
                                }}
                            >
                                <Picker.Item label="-- Seleccione un tipo --" value={null} />
                                {tiposFormacion.map(tipo => (
                                    <Picker.Item key={tipo.idTF} label={tipo.nombreTipoFormacion} value={tipo.idTF} />
                                ))}
                            </Picker>
                        </View>
                        {formErrors.tipo && <Text style={styles.errorText}>{formErrors.tipo}</Text>}

                        <Text style={styles.label}>Formación *</Text>
                        <View style={styles.pickerContainer}>
                            <Picker
                                selectedValue={selectedFormacion}
                                onValueChange={(itemValue) => setSelectedFormacion(itemValue)}
                                enabled={selectedTipoFormacion !== null && formacionesFiltradas.length > 0}
                            >
                                <Picker.Item label={selectedTipoFormacion === null ? "-- Seleccione un tipo primero --" : (formacionesFiltradas.length > 0 ? "-- Seleccione una formación --" : "-- No hay formaciones --")} value={null} />
                                {formacionesFiltradas.map(formacion => (
                                    <Picker.Item key={formacion.idFormacion} label={formacion.nombreFormacion} value={formacion.idFormacion} />
                                ))}
                            </Picker>
                        </View>
                        {formErrors.formacion && <Text style={styles.errorText}>{formErrors.formacion}</Text>}

                        <Text style={styles.label}>Cohorte *</Text>
                        <View style={styles.pickerContainer}>
                            <Picker selectedValue={selectedCohorte} onValueChange={(itemValue) => setSelectedCohorte(itemValue)}>
                                <Picker.Item label="-- Seleccione una cohorte --" value={null} />
                                {cohortes.map(cohorte => (
                                    <Picker.Item key={cohorte.idCohorte} label={cohorte.nombreCohorte} value={cohorte.idCohorte} />
                                ))}
                            </Picker>
                        </View>
                        {formErrors.cohorte && <Text style={styles.errorText}>{formErrors.cohorte}</Text>}

                        {selectedFormacion !== null && (
                            <View style={styles.costSummary}>
                                <Text style={styles.sectionTitle}>Resumen de Costos</Text>
                                <View style={styles.costRow}>
                                    <Text>Monto Inscripción:</Text>
                                    <Text>{fmtMoney(valorInscripcion)}</Text>
                                </View>
                                <View style={styles.costRow}>
                                    <Text>Total en Cuotas:</Text>
                                    <Text>{fmtMoney(totalCuotas)}</Text>
                                </View>
                                <View style={[styles.costRow, styles.totalRow]}>
                                    <Text style={styles.totalText}>Monto Total:</Text>
                                    <Text style={styles.totalText}>{fmtMoney(montoTotal)}</Text>
                                </View>
                            </View>
                        )}
                    </ScrollView>

                    <View style={styles.modalFooter}>
                        <TouchableOpacity 
                            style={[styles.modalButton, styles.createButton, creating && styles.disabledButton]} 
                            onPress={handleCreateInscripcion}
                            disabled={creating}
                        >
                            {creating ? <ActivityIndicator color="#fff" /> : <Text style={styles.modalButtonText}>Inscribir</Text>}
                        </TouchableOpacity>
                    </View>
                </View>
            </KeyboardAvoidingView>
        </Modal>
    </View>
  );
}

const styles = StyleSheet.create({
    container: { flex: 1, backgroundColor: '#f5f5f5' },
    center: { flex: 1, justifyContent: 'center', alignItems: 'center' },
    errorText: { color: 'red', fontSize: 12, marginTop: 4, marginLeft: 10 },
    header: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', padding: 15, backgroundColor: '#fff' },
    title: { fontSize: 24, fontWeight: 'bold' },
    addButton: { flexDirection: 'row', backgroundColor: '#4f8cff', paddingVertical: 8, paddingHorizontal: 12, borderRadius: 20, alignItems: 'center' },
    addButtonText: { color: '#fff', fontWeight: 'bold', marginLeft: 5 },
    searchContainer: { paddingHorizontal: 15, paddingVertical: 10, backgroundColor: '#fff' },
    searchWrapper: { flexDirection: 'row', backgroundColor: '#f0f0f0', borderRadius: 10, paddingHorizontal: 10, alignItems: 'center' },
    searchInput: { flex: 1, height: 40, marginLeft: 5 },
    listContent: { padding: 15 },
    card: { backgroundColor: '#fff', borderRadius: 8, marginBottom: 15, elevation: 2, shadowColor: '#000', shadowOpacity: 0.1, shadowOffset: {width: 0, height: 1}, shadowRadius: 3 },
    cardHeader: { padding: 15, borderBottomWidth: 1, borderBottomColor: '#eee' },
    cardTitleContainer: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
    cardTitle: { fontSize: 16, fontWeight: 'bold', flex: 1 },
    cardSubtitle: { fontSize: 14, color: '#666', marginTop: 4 },
    cardContent: { padding: 15 },
    detailRow: { flexDirection: 'row', justifyContent: 'space-between', marginBottom: 8 },
    detailItem: { flexDirection: 'row', alignItems: 'center', width: '50%' },
    detailText: { marginLeft: 8, color: '#333' },
    cardButton: { flexDirection: 'row', justifyContent: 'center', alignItems: 'center', paddingVertical: 12, borderTopWidth: 1, borderTopColor: '#eee' },
    cardButtonText: { color: '#4f8cff', fontWeight: 'bold', marginRight: 5 },
    emptyState: { flex: 1, justifyContent: 'center', alignItems: 'center', marginTop: 50 },
    emptyText: { marginTop: 10, color: '#aaa', fontSize: 16 },
    badge: { paddingVertical: 4, paddingHorizontal: 8, borderRadius: 12 },
    badgeText: { color: '#fff', fontWeight: 'bold', fontSize: 12 },
    badgeActive: { backgroundColor: '#28a745' },
    badgeInactive: { backgroundColor: '#dc3545' },
    badgePartial: { backgroundColor: '#ffc107' },
    modal: { justifyContent: 'flex-end', margin: 0 },
    keyboardAvoid: { flex: 1, justifyContent: 'flex-end' },
    modalContent: { backgroundColor: 'white', borderTopLeftRadius: 20, borderTopRightRadius: 20, padding: 20, maxHeight: height * 0.7 },
    formModal: { backgroundColor: 'white', borderTopLeftRadius: 20, borderTopRightRadius: 20, padding: 20, maxHeight: height * 0.85, flex: 1 },
    modalHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', borderBottomWidth: 1, borderBottomColor: '#eee', paddingBottom: 10, marginBottom: 15 },
    modalTitle: { fontSize: 18, fontWeight: 'bold' },
    closeButton: { padding: 5 },
    modalBody: { flex: 1 },
    formBody: { flex: 1 },
    formContent: { paddingBottom: 20 },
    modalFooter: { borderTopWidth: 1, borderTopColor: '#eee', paddingTop: 15, marginTop: 10 },
    modalButton: { backgroundColor: '#6c757d', padding: 12, borderRadius: 8, alignItems: 'center' },
    createButton: { backgroundColor: '#4f8cff' },
    disabledButton: { backgroundColor: '#aaa' },
    modalButtonText: { color: 'white', fontWeight: 'bold' },
    detailRowModal: { flexDirection: 'row', justifyContent: 'space-between', paddingVertical: 8, borderBottomWidth: 1, borderBottomColor: '#f5f5f5' },
    detailLabel: { fontWeight: 'bold', color: '#555' },
    detailValue: { color: '#333', flex: 1, textAlign: 'right' },
    formSection: { marginBottom: 20 },
    sectionTitle: { fontSize: 16, fontWeight: 'bold', marginBottom: 10, color: '#333' },
    fieldContainer: { marginBottom: 15 },
    label: { fontSize: 14, color: '#555', marginBottom: 5 },
    pickerContainer: { borderWidth: 1, borderColor: '#ccc', borderRadius: 8 },
    cedulaFijaContainer: { flexDirection: 'row', alignItems: 'center', backgroundColor: '#f0f0f0', padding: 12, borderRadius: 8 },
    cedulaFijaText: { marginLeft: 10, fontSize: 16, fontWeight: 'bold', color: '#333' },
    costSummary: { marginTop: 20, paddingTop: 15, borderTopWidth: 1, borderTopColor: '#eee' },
    costRow: { flexDirection: 'row', justifyContent: 'space-between', paddingVertical: 5 },
    totalRow: { marginTop: 5, paddingTop: 5, borderTopWidth: 1, borderTopColor: '#ccc' },
    totalText: { fontWeight: 'bold', fontSize: 16 },
});

