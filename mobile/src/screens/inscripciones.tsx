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
  const { user, fetchUserProfile } = useContext(AuthContext);
  const [items, setItems] = useState<Inscripcion[]>([]);
  const [mostradas, setMostradas] = useState<Inscripcion[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchText, setSearchText] = useState('');
  const [detailModalVisible, setDetailModalVisible] = useState(false);
  const [selected, setSelected] = useState<Inscripcion | null>(null);

  // Create form modal
  const [formModalVisible, setFormModalVisible] = useState(false);
  const [creating, setCreating] = useState(false);

  // Form fields - USAR UNDEFINED EN LUGAR DE NULL
  const [tiposFormacion, setTiposFormacion] = useState<TipoFormacion[]>([]);
  const [formaciones, setFormaciones] = useState<Formacion[]>([]);
  const [formacionesFiltradas, setFormacionesFiltradas] = useState<Formacion[]>([]);
  const [cohortes, setCohortes] = useState<Cohorte[]>([]);
  
  const [selectedTipoFormacion, setSelectedTipoFormacion] = useState<number | undefined>(undefined);
  const [selectedFormacion, setSelectedFormacion] = useState<number | undefined>(undefined);
  const [selectedCohorte, setSelectedCohorte] = useState<number | undefined>(undefined);
  
  // Resumen de costos
  const [valorInscripcion, setValorInscripcion] = useState(0);
  const [cuotas, setCuotas] = useState<Cuota[]>([]);
  const [totalCuotas, setTotalCuotas] = useState(0);
  const [montoTotal, setMontoTotal] = useState(0);
  
  const [fechaInscripcion, setFechaInscripcion] = useState<string>('');
  const [formErrors, setFormErrors] = useState<Record<string,string>>({});

  // DEBUG: Verificar el usuario
  useEffect(() => {
    console.log('🔐 USUARIO COMPLETO EN INSCRIPCIONES:', JSON.stringify(user, null, 2));
    console.log('🔐 Propiedades del usuario:', user ? Object.keys(user) : 'No hay usuario');
    console.log('🔐 Cedula del usuario:', user?.cedula);
    console.log('🔐 idPersona del usuario:', user?.idPersona);
    
    // Si no tiene idPersona, intentar obtenerlo
    if (user && !user.idPersona) {
      console.log('🔄 Intentando obtener idPersona...');
      fetchUserProfile();
    }
  }, [user, fetchUserProfile]);

  // Load inscripciones
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

  // Load tipos formacion, formaciones & cohortes
  const fetchDatosFormulario = useCallback(async () => {
    try {
      console.log('🔍 Cargando datos del formulario...');
      
      const [r1, r2, r3] = await Promise.all([
        api.get('/api/tipo-formaciones/').catch((error) => {
          console.error('Error cargando tipos formación:', error.response?.data);
          return { data: [] };
        }),
        api.get('/api/formaciones/').catch((error) => {
          console.error('Error cargando formaciones:', error.response?.data);
          return { data: [] };
        }),
        api.get('/api/cohorte/').catch((error) => {
          console.error('Error cargando cohortes:', error.response?.data);
          return { data: [] };
        }),
      ]);

      // Función mejorada para extraer datos con mapeo de campos
      const extractData = (responseData: any, tipo: string) => {
        console.log(`📦 Datos crudos de ${tipo}:`, responseData);
        
        let dataArray = [];
        
        if (Array.isArray(responseData)) {
          dataArray = responseData;
        } else if (responseData && Array.isArray(responseData.results)) {
          dataArray = responseData.results;
        } else if (responseData && responseData.data && Array.isArray(responseData.data)) {
          dataArray = responseData.data;
        } else if (responseData && typeof responseData === 'object') {
          dataArray = [responseData];
        } else {
          dataArray = [];
        }

        // Mapear campos según el tipo - ASEGURANDO QUE idTF SEA NÚMERO
        const mappedData = dataArray.map((item: any) => {
          if (tipo === 'tipos') {
            return {
              idTF: Number(item.idTF || item.id || item.tipo_id),
              nombreTipoFormacion: item.nombreTipoFormacion || item.nombre || item.descripcion || 'Sin nombre'
            };
          }
          
          if (tipo === 'formaciones') {
            return {
              idFormacion: item.idFormacion || item.id,
              nombreFormacion: item.nombreFormacion || item.nombre || 'Sin nombre',
              idTF: Number(item.idTF || item.tipo_formacion_id || item.idTF_id),
              valorInscripcion: Number(item.valorInscripcion || item.precio || item.costo || 0),
              tieneCuotas: Boolean(item.tieneCuotas || item.cuotas || false),
              cuotas_activas: Boolean(item.cuotas_activas || item.cuotas_activas || false),
              cantidad_cuotas: Number(item.cantidad_cuotas || item.cuotas_count || 0),
              cuotas_json: item.cuotas_json || item.cuotas || '[]'
            };
          }
          
          if (tipo === 'cohortes') {
            return {
              idCohorte: item.idCohorte || item.id,
              nombreCohorte: item.nombreCohorte || item.nombre || 'Sin nombre'
            };
          }
          
          return item;
        });

        console.log(`✅ ${tipo} mapeados:`, mappedData.length, mappedData);
        return mappedData;
      };

      const tiposData = extractData(r1.data, 'tipos');
      const formacionesData = extractData(r2.data, 'formaciones');
      const cohortesData = extractData(r3.data, 'cohortes');

      console.log('🎉 Datos finales:');
      console.log('📚 Tipos formación:', tiposData);
      console.log('🎓 Formaciones:', formacionesData);
      console.log('👥 Cohortes:', cohortesData);

      setTiposFormacion(tiposData);
      setFormaciones(formacionesData);
      setCohortes(cohortesData);

    } catch (e) {
      console.error('Error crítico en fetchDatosFormulario:', e);
      Alert.alert('Error', 'No se pudieron cargar los datos del formulario');
    }
  }, []);

  // Establecer fecha actual automáticamente
  const establecerFechaActual = () => {
    const ahora = new Date();
    const fecha = ahora.toISOString().split('T')[0];
    const hora = ahora.toTimeString().split(' ')[0];
    setFechaInscripcion(`${fecha} ${hora}`);
  };

  // Efecto para cargar datos y establecer fecha cuando se abre el modal
  useEffect(() => {
    if (formModalVisible) {
      establecerFechaActual();
      fetchDatosFormulario();
    }
  }, [formModalVisible]);

  useEffect(() => {
    fetchInscripciones();
    fetchDatosFormulario();
  }, [fetchInscripciones, fetchDatosFormulario]);

  // Filtrar formaciones cuando cambia el tipo de formación
  useEffect(() => {
    console.log('🔄 Filtrando formaciones...');
    console.log('Tipo seleccionado:', selectedTipoFormacion, typeof selectedTipoFormacion);
    console.log('Total formaciones:', formaciones.length);
    
    if (selectedTipoFormacion !== undefined && formaciones.length > 0) {
      const filtradas = formaciones.filter(f => {
        const formacionIdTF = Number(f.idTF);
        const selectedIdTF = Number(selectedTipoFormacion);
        const match = formacionIdTF === selectedIdTF;
        console.log(`Formación: ${f.nombreFormacion}, idTF: ${f.idTF} (${typeof f.idTF}), match: ${match}`);
        return match;
      });
      console.log('✅ Formaciones filtradas:', filtradas.length, filtradas);
      setFormacionesFiltradas(filtradas);
      setSelectedFormacion(undefined);
    } else {
      console.log('❌ No hay tipo seleccionado o formaciones');
      setFormacionesFiltradas([]);
      setSelectedFormacion(undefined);
    }
  }, [selectedTipoFormacion, formaciones]);

  // Calcular costos cuando se selecciona formación
  useEffect(() => {
    if (selectedFormacion !== undefined) {
      const formacion = formaciones.find(f => f.idFormacion === selectedFormacion);
      if (formacion) {
        console.log('💰 Calculando costos para:', formacion.nombreFormacion);
        const valorInsc = Number(formacion.valorInscripcion) || 0;
        setValorInscripcion(valorInsc);
        
        // Procesar cuotas
        let cuotasData: Cuota[] = [];
        let totalCtas = 0;
        
        if (formacion.tieneCuotas && formacion.cuotas_activas && formacion.cuotas_json) {
          try {
            cuotasData = JSON.parse(formacion.cuotas_json);
            totalCtas = cuotasData.reduce((sum, cuota) => sum + Number(cuota.valorCuota || 0), 0);
            console.log('📊 Cuotas procesadas:', cuotasData);
          } catch (e) {
            console.error('Error parsing cuotas JSON', e);
          }
        }
        
        setCuotas(cuotasData);
        setTotalCuotas(totalCtas);
        setMontoTotal(valorInsc + totalCtas);
      }
    } else {
      setValorInscripcion(0);
      setCuotas([]);
      setTotalCuotas(0);
      setMontoTotal(0);
    }
  }, [selectedFormacion, formaciones]);

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

  const openDetail = (it: Inscripcion) => {
    setSelected(it);
    setDetailModalVisible(true);
  };

  const validateCreateForm = () => {
    const errs: Record<string,string> = {};
    if (selectedTipoFormacion === undefined) errs.tipoFormacion = 'Seleccione un tipo de formación';
    if (selectedFormacion === undefined) errs.formacion = 'Seleccione una formación';
    if (selectedCohorte === undefined) errs.cohorte = 'Seleccione una cohorte';
    
    // Validación mejorada del usuario
    if (!user) {
      errs.usuario = 'No hay usuario autenticado';
    } else if (!user.idPersona && !user.id) {
      errs.usuario = 'No se pudo obtener la identificación del usuario';
    } else if (!user.cedula && !user.displayName) {
      errs.usuario = 'Información de usuario incompleta';
    }

    setFormErrors(errs);
    return Object.keys(errs).length === 0;
  };

  const handleCreateInscripcion = async () => {
    // DEBUG detallado
    console.log('🔐 VERIFICACIÓN COMPLETA DEL USUARIO:');
    console.log('User object:', user);
    console.log('idPersona:', user?.idPersona);
    console.log('id:', user?.id);
    console.log('cedula:', user?.cedula);

    if (!validateCreateForm()) {
      Alert.alert('Formulario inválido', 'Corrige los errores antes de continuar.');
      return;
    }

    // ESTRATEGIA ROBUSTA PARA OBTENER idPersona
    let idPersona: number;

    // Opción 1: idPersona directo
    if (user?.idPersona) {
      idPersona = Number(user.idPersona);
      console.log('✅ Usando idPersona directo:', idPersona);
    }
    // Opción 2: id como fallback
    else if (user?.id) {
      idPersona = Number(user.id);
      console.log('⚠️ Usando id como fallback para idPersona:', idPersona);
    }
    // Opción 3: Error - no tenemos forma de identificar al usuario
    else {
      console.error('❌ No se pudo obtener idPersona ni id del usuario');
      Alert.alert(
        'Error', 
        'No se pudo identificar su usuario. Por favor, cierre sesión y vuelva a ingresar.'
      );
      return;
    }

    // Validar que tengamos un ID válido
    if (!idPersona || isNaN(idPersona)) {
      console.error('❌ ID de persona inválido:', idPersona);
      Alert.alert('Error', 'No se pudo identificar al usuario correctamente.');
      return;
    }

    const idTF = Number(selectedTipoFormacion);
    const idFormacion = Number(selectedFormacion);
    const idCohorte = Number(selectedCohorte);

    // Validación de IDs
    if (isNaN(idTF) || isNaN(idFormacion) || isNaN(idCohorte)) {
      Alert.alert('Error', 'Hay datos inválidos en el formulario.');
      return;
    }

    setCreating(true);
    try {
      const estadoPago: 'PENDIENTE'|'PARCIAL'|'PAGADO' = 'PENDIENTE';

      const payload: any = {
        idPersona: idPersona,
        idTF: idTF,
        idFormacion: idFormacion,
        idCohorte: idCohorte,
        montoTotal: montoTotal,
        montoPagado: 0,
        estadoPago,
        fechaInscripcion,
      };

      // Incluir cédula si está disponible, si no, incluir displayName
      if (user?.cedula) {
        payload.cedulaPersona = user.cedula;
      } else if (user?.displayName) {
        payload.cedulaPersona = user.displayName;
      }

      console.log('📤 Enviando payload CORREGIDO:', payload);

      const res = await api.post('/api/inscripcion/', payload);
      
      if (res.status === 201 || res.status === 200) {
        Alert.alert('Éxito', 'Inscripción creada correctamente.');
        setFormModalVisible(false);
        resetForm();
        await fetchInscripciones();
      } else {
        const message = res.data?.detail ?? JSON.stringify(res.data);
        Alert.alert('Respuesta del servidor', String(message));
      }
    } catch (err: any) {
      console.error('handleCreateInscripcion error', err);
      const message = err.response?.data?.detail ?? err.message ?? 'Error al crear inscripción';
      
      // Mostrar error más específico
      if (err.response?.status === 500) {
        Alert.alert('Error del servidor', 'Hubo un problema en el servidor. Por favor, contacta al administrador.');
      } else {
        Alert.alert('Error', message);
      }
    } finally {
      setCreating(false);
    }
  };

  const resetForm = () => {
    setSelectedTipoFormacion(undefined);
    setSelectedFormacion(undefined);
    setSelectedCohorte(undefined);
    setFormErrors({});
    setValorInscripcion(0);
    setCuotas([]);
    setTotalCuotas(0);
    setMontoTotal(0);
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

      {/* Detalle modal */}
      <Modal 
        isVisible={detailModalVisible} 
        onBackdropPress={() => setDetailModalVisible(false)}
        style={styles.modal}
      >
        <View style={styles.modalContent}>
          <View style={styles.modalHeader}>
            <Text style={styles.modalTitle}>Detalles de Inscripción</Text>
            <TouchableOpacity 
              style={styles.closeButton}
              onPress={() => setDetailModalVisible(false)}
            >
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
                <Text style={styles.detailValue}>{val}</Text>
              </View>
            ))}
          </ScrollView>

          <View style={styles.modalFooter}>
            <TouchableOpacity 
              style={styles.modalButton}
              onPress={() => setDetailModalVisible(false)}
            >
              <Text style={styles.modalButtonText}>Cerrar</Text>
            </TouchableOpacity>
          </View>
        </View>
      </Modal>

      {/* Form modal: crear inscripción */}
      <Modal
        isVisible={formModalVisible}
        onBackdropPress={() => setFormModalVisible(false)}
        style={styles.modal}
      >
        <KeyboardAvoidingView 
          behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
          style={styles.keyboardAvoid}
        >
          <View style={styles.formModal}>
            <View style={styles.modalHeader}>
              <Text style={styles.modalTitle}>Nueva Inscripción</Text>
              <TouchableOpacity 
                style={styles.closeButton}
                onPress={() => setFormModalVisible(false)}
              >
                <Icon name="close" size={24} color="#666" />
              </TouchableOpacity>
            </View>

            <ScrollView 
              style={styles.formBody}
              showsVerticalScrollIndicator={false}
              contentContainerStyle={styles.formContent}
            >
              {/* Sección Información Personal */}
              <View style={styles.formSection}>
                <Text style={styles.sectionTitle}>Información Personal</Text>
                
                <View style={styles.fieldContainer}>
                  <Text style={styles.label}>Cédula del Cliente</Text>
                  <View style={styles.cedulaFijaContainer}>
                    <Icon name="account" size={20} color="#4f8cff" />
                    <Text style={styles.cedulaFijaText}>
                      {user?.cedula || user?.displayName || 'Usuario no identificado'}
                    </Text>
                  </View>
                  <Text style={styles.helpText}>
                    {user?.nombres && user?.apellidos 
                      ? `Usuario: ${user.nombres} ${user.apellidos}`
                      : user?.displayName 
                        ? `Usuario: ${user.displayName}`
                        : 'Complete su información de perfil'}
                  </Text>
                  {formErrors.usuario && (
                    <Text style={styles.errorText}>{formErrors.usuario}</Text>
                  )}
                </View>
              </View>

              {/* Sección Información Académica */}
              <View style={styles.formSection}>
                <Text style={styles.sectionTitle}>Información Académica</Text>

                <View style={styles.fieldContainer}>
                  <Text style={styles.label}>Tipo de Formación *</Text>
                  <View style={styles.pickerContainer}>
                    <Picker
                      selectedValue={selectedTipoFormacion}
                      onValueChange={(itemValue) => setSelectedTipoFormacion(itemValue)}
                      style={styles.picker}
                    >
                      <Picker.Item label="Seleccione tipo de formación..." value={undefined} />
                      {tiposFormacion.map(tf => (
                        <Picker.Item 
                          key={tf.idTF} 
                          label={tf.nombreTipoFormacion} 
                          value={tf.idTF} 
                        />
                      ))}
                    </Picker>
                  </View>
                  {formErrors.tipoFormacion && (
                    <Text style={styles.errorText}>{formErrors.tipoFormacion}</Text>
                  )}
                </View>

                <View style={styles.fieldContainer}>
                  <Text style={styles.label}>Formación Académica *</Text>
                  <View style={styles.pickerContainer}>
                    <Picker
                      selectedValue={selectedFormacion}
                      onValueChange={setSelectedFormacion}
                      style={styles.picker}
                      enabled={selectedTipoFormacion !== undefined && formacionesFiltradas.length > 0}
                    >
                      <Picker.Item 
                        label={
                          selectedTipoFormacion === undefined ? "Seleccione tipo primero" :
                          formacionesFiltradas.length === 0 ? "No hay formaciones disponibles" : 
                          "Seleccione formación..."
                        } 
                        value={undefined} 
                      />
                      {formacionesFiltradas.map(f => (
                        <Picker.Item 
                          key={f.idFormacion} 
                          label={f.nombreFormacion} 
                          value={f.idFormacion} 
                        />
                      ))}
                    </Picker>
                  </View>
                  {formErrors.formacion && (
                    <Text style={styles.errorText}>{formErrors.formacion}</Text>
                  )}
                </View>

                <View style={styles.fieldContainer}>
                  <Text style={styles.label}>Cohorte *</Text>
                  <View style={styles.pickerContainer}>
                    <Picker
                      selectedValue={selectedCohorte}
                      onValueChange={(itemValue) => setSelectedCohorte(itemValue)}
                      style={styles.picker}
                    >
                      <Picker.Item label="Seleccione cohorte..." value={undefined} />
                      {cohortes.map(c => (
                        <Picker.Item 
                          key={c.idCohorte} 
                          label={c.nombreCohorte} 
                          value={c.idCohorte} 
                        />
                      ))}
                    </Picker>
                  </View>
                  {formErrors.cohorte && (
                    <Text style={styles.errorText}>{formErrors.cohorte}</Text>
                  )}
                </View>
              </View>

              {/* Sección Resumen de Costos */}
              <View style={styles.formSection}>
                <Text style={styles.sectionTitle}>Resumen de Costos</Text>
                
                <View style={styles.costosTable}>
                  <View style={styles.tableHeader}>
                    <Text style={styles.tableHeaderText}>Concepto</Text>
                    <Text style={styles.tableHeaderText}>Monto</Text>
                  </View>
                  
                  <View style={styles.tableRow}>
                    <Text style={styles.tableCell}><Text style={styles.boldText}>Valor de Inscripción</Text></Text>
                    <Text style={[styles.tableCell, styles.inscripcionCell]}>
                      <Text style={styles.boldText}>{fmtMoney(valorInscripcion)}</Text>
                    </Text>
                  </View>
                  
                  {cuotas.map((cuota, index) => (
                    <View key={index} style={styles.tableRow}>
                      <Text style={styles.tableCell}>
                        <Text style={styles.boldText}>{cuota.nombreCuota || `Cuota ${index + 1}`}</Text>
                      </Text>
                      <Text style={styles.tableCell}>{fmtMoney(cuota.valorCuota)}</Text>
                    </View>
                  ))}
                  
                  {cuotas.length > 0 && (
                    <View style={styles.tableRow}>
                      <Text style={styles.tableCell}><Text style={styles.boldText}>Total Cuotas</Text></Text>
                      <Text style={[styles.tableCell, styles.cuotasCell]}>
                        <Text style={styles.boldText}>{fmtMoney(totalCuotas)}</Text>
                      </Text>
                    </View>
                  )}
                  
                  <View style={[styles.tableRow, styles.totalRow]}>
                    <Text style={styles.tableCell}><Text style={styles.boldText}>Total a Pagar</Text></Text>
                    <Text style={[styles.tableCell, styles.totalCell]}>
                      <Text style={styles.boldText}>{fmtMoney(montoTotal)}</Text>
                    </Text>
                  </View>
                </View>
              </View>

              {/* Sección Fecha Automática */}
              <View style={styles.formSection}>
                <Text style={styles.sectionTitle}>Información de Registro</Text>
                
                <View style={styles.fieldContainer}>
                  <Text style={styles.label}>Fecha y Hora de Inscripción</Text>
                  <View style={styles.fechaContainer}>
                    <Icon name="calendar-clock" size={20} color="#4f8cff" />
                    <Text style={styles.fechaText}>{fechaInscripcion}</Text>
                  </View>
                  <Text style={styles.helpText}>Fecha y hora automáticas del sistema</Text>
                </View>
              </View>
            </ScrollView>

            <View style={styles.formFooter}>
              <TouchableOpacity 
                style={[styles.formButton, styles.cancelButton]}
                onPress={() => setFormModalVisible(false)}
              >
                <Text style={styles.cancelButtonText}>Cancelar</Text>
              </TouchableOpacity>

              <TouchableOpacity 
                style={[styles.formButton, styles.submitButton]}
                onPress={handleCreateInscripcion}
                disabled={creating}
              >
                {creating ? (
                  <ActivityIndicator color="#fff" size="small" />
                ) : (
                  <>
                    <Icon name="check" size={20} color="#fff" />
                    <Text style={styles.submitButtonText}>Crear Inscripción</Text>
                  </>
                )}
              </TouchableOpacity>
            </View>
          </View>
        </KeyboardAvoidingView>
      </Modal>
    </View>
  );
}

// Los estilos se mantienen igual...
const styles = StyleSheet.create({
  center: { 
    flex: 1, 
    justifyContent: 'center', 
    alignItems: 'center',
    backgroundColor: '#f5f7fa',
  },
  container: { 
    flex: 1, 
    backgroundColor: '#f5f7fa',
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingHorizontal: 20,
    paddingTop: 20,
    paddingBottom: 10,
    backgroundColor: '#fff',
    borderBottomWidth: 1,
    borderBottomColor: '#e1e5e9',
  },
  title: { 
    fontSize: 28, 
    fontWeight: '700', 
    color: '#1a365d',
  },
  addButton: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#4f8cff',
    paddingHorizontal: 16,
    paddingVertical: 10,
    borderRadius: 8,
    gap: 8,
  },
  addButtonText: {
    color: '#fff',
    fontWeight: '600',
    fontSize: 16,
  },
  searchContainer: {
    padding: 20,
    backgroundColor: '#fff',
    borderBottomWidth: 1,
    borderBottomColor: '#e1e5e9',
  },
  searchWrapper: {
    flexDirection: 'row',
    backgroundColor: '#f8f9fa',
    borderRadius: 12,
    alignItems: 'center',
    paddingHorizontal: 16,
    height: 52,
    borderWidth: 1,
    borderColor: '#e1e5e9',
  },
  searchInput: {
    flex: 1,
    fontSize: 16,
    marginLeft: 12,
    color: '#333',
  },
  listContent: {
    padding: 20,
    paddingTop: 10,
  },
  card: {
    backgroundColor: '#fff',
    borderRadius: 16,
    padding: 20,
    marginBottom: 16,
    shadowColor: '#000',
    shadowOffset: {
      width: 0,
      height: 2,
    },
    shadowOpacity: 0.1,
    shadowRadius: 3.84,
    elevation: 5,
    borderWidth: 1,
    borderColor: '#f1f3f4',
  },
  cardHeader: {
    marginBottom: 16,
  },
  cardTitleContainer: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 8,
  },
  cardTitle: {
    fontSize: 18,
    fontWeight: '600',
    color: '#1a365d',
    flex: 1,
    marginRight: 12,
  },
  cardSubtitle: {
    fontSize: 14,
    color: '#666',
    fontWeight: '500',
  },
  cardContent: {
    marginBottom: 16,
  },
  detailRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginBottom: 12,
  },
  detailItem: {
    flexDirection: 'row',
    alignItems: 'center',
    flex: 1,
  },
  detailText: {
    marginLeft: 8,
    fontSize: 14,
    color: '#555',
    fontWeight: '500',
  },
  cardButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: 12,
    borderTopWidth: 1,
    borderTopColor: '#f1f3f4',
  },
  cardButtonText: {
    color: '#4f8cff',
    fontWeight: '600',
    fontSize: 16,
    marginRight: 8,
  },
  badge: {
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 20,
    minWidth: 80,
    alignItems: 'center',
  },
  badgeActive: { 
    backgroundColor: '#2dce89',
  },
  badgePartial: { 
    backgroundColor: '#f1a43a',
  },
  badgeInactive: { 
    backgroundColor: '#f5365c',
  },
  badgeText: { 
    color: '#fff', 
    fontSize: 12, 
    fontWeight: '700',
    textAlign: 'center',
  },
  emptyState: {
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: 60,
  },
  emptyText: { 
    marginTop: 16,
    textAlign: 'center', 
    color: '#999', 
    fontStyle: 'italic', 
    fontSize: 16,
  },
  errorText: {
    color: '#e53e3e',
    fontSize: 14,
    marginTop: 4,
    fontWeight: '500',
  },
  modal: {
    margin: 0,
    justifyContent: 'center',
    alignItems: 'center',
  },
  keyboardAvoid: {
    width: '100%',
    alignItems: 'center',
  },
  modalContent: {
    backgroundColor: '#fff',
    borderRadius: 20,
    width: width * 0.9,
    maxWidth: 500,
    maxHeight: height * 0.8,
    overflow: 'hidden',
  },
  formModal: {
    backgroundColor: '#fff',
    borderRadius: 20,
    width: width * 0.9,
    maxWidth: 500,
    maxHeight: height * 0.9,
    overflow: 'hidden',
  },
  modalHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: 24,
    paddingBottom: 16,
    borderBottomWidth: 1,
    borderBottomColor: '#e1e5e9',
  },
  modalTitle: {
    fontSize: 24,
    fontWeight: '700',
    color: '#1a365d',
    flex: 1,
  },
  closeButton: {
    padding: 4,
  },
  modalBody: {
    flex: 1,
  },
  formBody: {
    flex: 1,
  },
  formContent: {
    paddingBottom: 20,
  },
  modalFooter: {
    padding: 24,
    paddingTop: 16,
    borderTopWidth: 1,
    borderTopColor: '#e1e5e9',
  },
  detailRowModal: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    paddingVertical: 12,
    paddingHorizontal: 24,
    borderBottomWidth: 1,
    borderBottomColor: '#f8f9fa',
  },
  detailLabel: {
    fontWeight: '600',
    fontSize: 16,
    color: '#4a5568',
    flex: 1,
  },
  detailValue: {
    flex: 1,
    fontSize: 16,
    color: '#2d3748',
    textAlign: 'right',
    fontWeight: '500',
  },
  modalButton: {
    backgroundColor: '#4f8cff',
    paddingVertical: 14,
    borderRadius: 12,
    alignItems: 'center',
  },
  modalButtonText: {
    color: '#fff',
    fontWeight: '600',
    fontSize: 16,
  },
  formSection: {
    marginBottom: 8,
  },
  sectionTitle: {
    fontSize: 18,
    fontWeight: '700',
    color: '#2d3748',
    marginBottom: 16,
    paddingHorizontal: 24,
    paddingTop: 16,
  },
  fieldContainer: {
    marginBottom: 16,
    paddingHorizontal: 24,
  },
  label: {
    fontWeight: '600',
    color: '#4a5568',
    marginBottom: 8,
    fontSize: 15,
  },
  cedulaFijaContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#f8f9fa',
    borderRadius: 12,
    paddingHorizontal: 16,
    paddingVertical: 14,
    borderWidth: 1,
    borderColor: '#e1e5e9',
    gap: 12,
  },
  cedulaFijaText: {
    fontSize: 16,
    fontWeight: '600',
    color: '#4a5568',
  },
  fechaContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#f0fff4',
    borderRadius: 12,
    paddingHorizontal: 16,
    paddingVertical: 14,
    borderWidth: 1,
    borderColor: '#9ae6b4',
    gap: 12,
  },
  fechaText: {
    fontSize: 16,
    fontWeight: '600',
    color: '#22543d',
  },
  helpText: {
    fontSize: 12,
    color: '#6c757d',
    marginTop: 4,
    fontStyle: 'italic',
  },
  pickerContainer: {
    borderWidth: 1,
    borderColor: '#e1e5e9',
    borderRadius: 12,
    backgroundColor: '#fff',
    overflow: 'hidden',
  },
  picker: {
    height: 52,
  },
  costosTable: {
    borderWidth: 1,
    borderColor: '#e1e5e9',
    borderRadius: 12,
    overflow: 'hidden',
    marginHorizontal: 24,
  },
  tableHeader: {
    flexDirection: 'row',
    backgroundColor: '#f8f9fa',
    paddingVertical: 12,
    paddingHorizontal: 16,
    borderBottomWidth: 1,
    borderBottomColor: '#e1e5e9',
  },
  tableHeaderText: {
    flex: 1,
    fontWeight: '700',
    color: '#4a5568',
    fontSize: 16,
  },
  tableRow: {
    flexDirection: 'row',
    paddingVertical: 12,
    paddingHorizontal: 16,
    borderBottomWidth: 1,
    borderBottomColor: '#f8f9fa',
  },
  tableCell: {
    flex: 1,
    fontSize: 15,
    color: '#4a5568',
  },
  boldText: {
    fontWeight: '600',
  },
  inscripcionCell: {
    backgroundColor: '#cce5ff',
  },
  cuotasCell: {
    backgroundColor: '#e2d4f0',
  },
  totalRow: {
    backgroundColor: '#d4edda',
  },
  totalCell: {
    fontWeight: '700',
    color: '#155724',
  },
  formFooter: {
    flexDirection: 'row',
    padding: 24,
    paddingTop: 16,
    borderTopWidth: 1,
    borderTopColor: '#e1e5e9',
    gap: 12,
  },
  formButton: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: 16,
    borderRadius: 12,
    gap: 8,
  },
  cancelButton: {
    backgroundColor: '#fff',
    borderWidth: 1,
    borderColor: '#e1e5e9',
  },
  cancelButtonText: {
    color: '#4a5568',
    fontWeight: '600',
    fontSize: 16,
  },
  submitButton: {
    backgroundColor: '#4f8cff',
  },
  submitButtonText: {
    color: '#fff',
    fontWeight: '600',
    fontSize: 16,
  },
});