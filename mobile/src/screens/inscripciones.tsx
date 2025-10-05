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
import AsyncStorage from '@react-native-async-storage/async-storage';
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
  const { user, fetchUserFromCedula } = useContext(AuthContext);
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

  // Form fields
  const [tiposFormacion, setTiposFormacion] = useState<TipoFormacion[]>([]);
  const [formaciones, setFormaciones] = useState<Formacion[]>([]);
  const [formacionesFiltradas, setFormacionesFiltradas] = useState<Formacion[]>([]);
  const [cohortes, setCohortes] = useState<Cohorte[]>([]);
  
  const [selectedTipoFormacion, setSelectedTipoFormacion] = useState<number | null>(null);
  const [selectedFormacion, setSelectedFormacion] = useState<number | null>(null);
  const [selectedCohorte, setSelectedCohorte] = useState<number | null>(null);
  
  // Resumen de costos
  const [valorInscripcion, setValorInscripcion] = useState(0);
  const [cuotas, setCuotas] = useState<Cuota[]>([]);
  const [totalCuotas, setTotalCuotas] = useState(0);
  const [montoTotal, setMontoTotal] = useState(0);
  
  const [fechaInscripcion, setFechaInscripcion] = useState<string>('');
  const [formErrors, setFormErrors] = useState<Record<string,string>>({});

  // Estados para la información del usuario obtenida del backend
  const [userInfo, setUserInfo] = useState<{cedula?: string; idPersona?: number | null; nombres?: string; apellidos?: string} | null>(null);
  const [loadingUser, setLoadingUser] = useState(false);

  // FUNCIÓN CORREGIDA: Obtener información del usuario
  const obtenerInformacionUsuario = async () => {
    setLoadingUser(true);
    try {
      console.log('🔄 Obteniendo información del usuario...');
      
      if (user) {
        console.log('✅ Usuario del AuthContext:', user);
        setUserInfo({
          cedula: user.cedula,
          idPersona: user.idPersona || null,
          nombres: user.nombres || '',
          apellidos: user.apellidos || ''
        });
      } else {
        console.log('❌ No hay usuario en el AuthContext');
        setUserInfo(null);
      }

    } catch (error) {
      console.error('❌ Error obteniendo información del usuario:', error);
      setUserInfo(null);
    } finally {
      setLoadingUser(false);
    }
  };

  // DEBUG: Verificar el usuario
  useEffect(() => {
    console.log('🔐 USUARIO EN INSCRIPCIONES:', user);
    console.log('🔐 Cedula del usuario:', user?.cedula);
    console.log('🔐 idPersona del usuario:', user?.idPersona);
    
    obtenerInformacionUsuario();
  }, [user]);

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

  // Load tipos formacion, formaciones & cohortes - VERSIÓN MEJORADA
  // Load tipos formacion, formaciones & cohortes - VERSIÓN CORREGIDA
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

    console.log('📦 Respuesta tipos formación:', r1.data);
    console.log('📦 Respuesta formaciones:', r2.data);
    console.log('📦 Respuesta cohortes:', r3.data);

    // Función CORREGIDA para extraer datos
    const extractData = (responseData: any, tipo: string) => {
      let dataArray = [];
      
      // Diferentes estructuras posibles de respuesta
      if (Array.isArray(responseData)) {
        dataArray = responseData;
      } else if (responseData && Array.isArray(responseData.results)) {
        dataArray = responseData.results;
      } else if (responseData && responseData.data && Array.isArray(responseData.data)) {
        dataArray = responseData.data;
      } else if (responseData && typeof responseData === 'object') {
        // Si es un objeto único, lo convertimos en array
        dataArray = [responseData];
      } else {
        dataArray = [];
      }

      console.log(`📊 ${tipo} - datos extraídos:`, dataArray);

      // Mapeo CORREGIDO para cada tipo
      const mappedData = dataArray.map((item: any) => {
        if (tipo === 'tipos') {
          return {
            idTF: Number(item.idTF || item.id || item.tipo_id || 0),
            nombreTipoFormacion: item.nombreTipoFormacion || item.nombre || item.descripcion || 'Sin nombre'
          };
        }
        
        if (tipo === 'formaciones') {
          // CORRECCIÓN CRÍTICA: Extraer correctamente idTF
          const idTF = Number(
            item.idTF || 
            item.tipo_formacion || 
            item.tipoFormacion || 
            item.tipo_formacion_id || 
            item.idTF_id || 
            (item.idTF_obj && item.idTF_obj.idTF) || 
            (item.tipo_formacion_obj && item.tipo_formacion_obj.id) ||
            0
          );

          console.log(`🎓 Formación: ${item.nombreFormacion || item.nombre}, idTF extraído: ${idTF}`, item);
          
          return {
            idFormacion: Number(item.idFormacion || item.id || 0),
            nombreFormacion: item.nombreFormacion || item.nombre || 'Sin nombre',
            idTF: idTF, // Este es el campo crítico que estaba mal
            valorInscripcion: Number(item.valorInscripcion || item.precio || item.costo || 0),
            tieneCuotas: Boolean(item.tieneCuotas || item.cuotas || false),
            cuotas_activas: Boolean(item.cuotas_activas || item.cuotas_activas || false),
            cantidad_cuotas: Number(item.cantidad_cuotas || item.cuotas_count || 0),
            cuotas_json: item.cuotas_json || item.cuotas || '[]'
          };
        }
        
        if (tipo === 'cohortes') {
          return {
            idCohorte: Number(item.idCohorte || item.id || 0),
            nombreCohorte: item.nombreCohorte || item.nombre || 'Sin nombre'
          };
        }
        
        return item;
      }).filter((item: any) => {
        // FILTRAR: Solo items con ID válido mayor a 0
        if (tipo === 'tipos') return item.idTF > 0;
        if (tipo === 'formaciones') return item.idFormacion > 0;
        if (tipo === 'cohortes') return item.idCohorte > 0;
        return true;
      });

      console.log(`✅ ${tipo} mapeados:`, mappedData.length);
      return mappedData;
    };

    const tiposData = extractData(r1.data, 'tipos');
    const formacionesData = extractData(r2.data, 'formaciones');
    const cohortesData = extractData(r3.data, 'cohortes');

    console.log('🎉 DATOS FINALES CARGADOS:');
    console.log('📚 Tipos formación:', tiposData);
    console.log('🎓 Formaciones:', formacionesData);
    console.log('👥 Cohortes:', cohortesData);

    setTiposFormacion(tiposData);
    setFormaciones(formacionesData);
    setCohortes(cohortesData);

    // DEBUG: Verificar relaciones entre tipos y formaciones
    console.log('🔗 RELACIONES TIPO-FORMACIÓN:');
    tiposData.forEach((tipo: TipoFormacion) => {
      const formacionesDelTipo = formacionesData.filter((f: Formacion) => f.idTF === tipo.idTF);
      console.log(`Tipo ${tipo.idTF} (${tipo.nombreTipoFormacion}): ${formacionesDelTipo.length} formaciones`);
    });

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
      obtenerInformacionUsuario();
    }
  }, [formModalVisible]);

  useEffect(() => {
    fetchInscripciones();
    fetchDatosFormulario();
  }, [fetchInscripciones, fetchDatosFormulario]);

  // Filtrar formaciones cuando cambia el tipo de formación - VERSIÓN MEJORADA
  // Filtrar formaciones cuando cambia el tipo de formación - VERSIÓN CORREGIDA
useEffect(() => {
  console.log('🔄 FILTRANDO FORMACIONES - INICIO');
  console.log('Tipo seleccionado:', selectedTipoFormacion);
  console.log('Total formaciones disponibles:', formaciones.length);
  console.log('Formaciones disponibles:', formaciones.map(f => ({
    id: f.idFormacion, 
    nombre: f.nombreFormacion, 
    idTF: f.idTF
  })));

  if (selectedTipoFormacion !== null && formaciones.length > 0) {
    const filtradas = formaciones.filter(f => {
      const match = f.idTF === selectedTipoFormacion;
      console.log(`🔍 Formación "${f.nombreFormacion}": idTF=${f.idTF}, selectedTipo=${selectedTipoFormacion}, match=${match}`);
      return match;
    });
    
    console.log('✅ FORMACIONES FILTRADAS:', filtradas.length);
    console.log('📋 Lista filtrada:', filtradas.map(f => ({id: f.idFormacion, nombre: f.nombreFormacion})));
    
    setFormacionesFiltradas(filtradas);
    setSelectedFormacion(null);
    
    // Si solo hay una formación filtrada, seleccionarla automáticamente
    if (filtradas.length === 1) {
      setSelectedFormacion(filtradas[0].idFormacion);
      console.log('✅ Auto-seleccionando única formación disponible');
    }
  } else {
    console.log('❌ Mostrando TODAS las formaciones (sin filtro)');
    setFormacionesFiltradas(formaciones);
  }
  
  console.log('🔄 FILTRANDO FORMACIONES - FIN');
}, [selectedTipoFormacion, formaciones]);

  // Calcular costos cuando se selecciona formación - VERSIÓN MEJORADA
  useEffect(() => {
    if (selectedFormacion !== null) {
      const formacion = formaciones.find(f => f.idFormacion === selectedFormacion);
      console.log('💰 Formación seleccionada para cálculos:', formacion);
      
      if (formacion) {
        console.log('💰 Calculando costos para:', formacion.nombreFormacion);
        const valorInsc = Number(formacion.valorInscripcion) || 0;
        console.log('💰 Valor inscripción:', valorInsc);
        
        setValorInscripcion(valorInsc);
        
        let cuotasData: Cuota[] = [];
        let totalCtas = 0;
        
        if (formacion.tieneCuotas && formacion.cuotas_activas && formacion.cuotas_json) {
          try {
            cuotasData = JSON.parse(formacion.cuotas_json);
            totalCtas = cuotasData.reduce((sum, cuota) => sum + Number(cuota.valorCuota || 0), 0);
            console.log('📊 Cuotas procesadas:', cuotasData, 'Total cuotas:', totalCtas);
          } catch (e) {
            console.error('Error parsing cuotas JSON', e);
          }
        }
        
        setCuotas(cuotasData);
        setTotalCuotas(totalCtas);
        const totalFinal = valorInsc + totalCtas;
        setMontoTotal(totalFinal);
        console.log('💰 Monto total calculado:', totalFinal);
      } else {
        console.error('❌ No se encontró la formación con ID:', selectedFormacion);
        setValorInscripcion(0);
        setCuotas([]);
        setTotalCuotas(0);
        setMontoTotal(0);
      }
    } else {
      console.log('💰 No hay formación seleccionada, reseteando costos');
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

  // DEBUG: Monitor estado del Picker de formaciones
  useEffect(() => {
    console.log('🎯 ESTADO ACTUAL DEL PICKER:');
    console.log('formacionesFiltradas:', formacionesFiltradas.length);
    console.log('selectedFormacion:', selectedFormacion);
    console.log('Opciones disponibles:', formacionesFiltradas.map(f => 
      `${f.nombreFormacion} (ID: ${f.idFormacion})`
    ));
  }, [formacionesFiltradas, selectedFormacion]);

  const openDetail = (it: Inscripcion) => {
    setSelected(it);
    setDetailModalVisible(true);
  };

  // Función para verificar que los IDs existen - VERSIÓN MEJORADA
  const verificarIDs = (): boolean => {
    const tipoId = selectedTipoFormacion;
    const formacionId = selectedFormacion;
    const cohorteId = selectedCohorte;
    
    console.log('🔍 VERIFICACIÓN DE IDs:');
    console.log('Tipo ID seleccionado:', tipoId);
    console.log('Formación ID seleccionado:', formacionId);
    console.log('Cohorte ID seleccionado:', cohorteId);
    
    console.log('📚 Tipos disponibles:', tiposFormacion.map(t => t.idTF));
    console.log('🎓 Formaciones disponibles:', formaciones.map(f => f.idFormacion));
    console.log('👥 Cohortes disponibles:', cohortes.map(c => c.idCohorte));

    const tipoExists = tiposFormacion.some(t => t.idTF === tipoId);
    const formacionExists = formaciones.some(f => f.idFormacion === formacionId);
    const cohorteExists = cohortes.some(c => c.idCohorte === cohorteId);
    
    console.log('Tipo existe:', tipoExists);
    console.log('Formación existe:', formacionExists);
    console.log('Cohorte existe:', cohorteExists);

    if (!tipoExists || !formacionExists || !cohorteExists) {
      Alert.alert(
        'Error en selección',
        `Los elementos seleccionados no son válidos. Por favor, seleccione opciones de la lista.\n\n` +
        `Tipo formación: ${tipoExists ? '✅' : '❌'}\n` +
        `Formación: ${formacionExists ? '✅' : '❌'}\n` +
        `Cohorte: ${cohorteExists ? '✅' : '❌'}`
      );
      return false;
    }
    
    return true;
  };

  const validateCreateForm = () => {
    const errs: Record<string,string> = {};
    if (selectedTipoFormacion === null) 
      errs.tipoFormacion = 'Seleccione un tipo de formación';
    if (selectedFormacion === null) 
      errs.formacion = 'Seleccione una formación';
    if (selectedCohorte === null) 
      errs.cohorte = 'Seleccione una cohorte';
    
    if (!userInfo && !user) {
      errs.usuario = 'No se pudo obtener la información del usuario. Por favor, cierre sesión y vuelva a ingresar.';
    }

    setFormErrors(errs);
    return Object.keys(errs).length === 0;
  };

  // FUNCIÓN MEJORADA: Crear inscripción
  const handleCreateInscripcion = async () => {
    console.log('🔐 VERIFICACIÓN COMPLETA DEL USUARIO:');
    console.log('UserInfo:', userInfo);
    console.log('AuthContext user:', user);

    if (!validateCreateForm()) {
      Alert.alert('Formulario inválido', 'Corrige los errores antes de continuar.');
      return;
    }

    // Verificar IDs ANTES de continuar
    if (!verificarIDs()) {
      return;
    }

    // Verificar montoTotal
    console.log('💰 VERIFICACIÓN FINAL DE MONTOS:');
    console.log('Valor inscripción:', valorInscripcion);
    console.log('Total cuotas:', totalCuotas);
    console.log('Monto total:', montoTotal);

    if (montoTotal <= 0) {
      Alert.alert(
        'Error en costos', 
        'El monto total debe ser mayor a 0. Verifique que la formación seleccionada tenga un costo configurado.'
      );
      return;
    }

    let cedulaUsuario: string | null = null;
    let idPersonaFinal: number | null = null;

    try {
      const tokens = await AsyncStorage.getItem('myapp-tokens');
      if (tokens) {
        const parsedTokens = JSON.parse(tokens);
        const userData = parsedTokens.user;
        cedulaUsuario = userData?.cedula;
        console.log('✅ Cédula obtenida de tokens:', cedulaUsuario);
      }
    } catch (error) {
      console.error('Error obteniendo tokens:', error);
    }

    if (userInfo?.idPersona) {
      idPersonaFinal = Number(userInfo.idPersona);
      console.log('✅ Usando idPersona del userInfo:', idPersonaFinal);
    } else if (cedulaUsuario) {
      console.log('⚠️ No hay idPersona, usando solo cédula:', cedulaUsuario);
    } else {
      console.error('❌ NO SE PUDO OBTENER INFORMACIÓN VÁLIDA DEL USUARIO');
      Alert.alert(
        'Error de Identificación', 
        'No se pudo identificar su usuario. Por favor, cierre sesión y vuelva a ingresar.'
      );
      return;
    }

    const idTF = Number(selectedTipoFormacion);
    const idFormacion = Number(selectedFormacion);
    const idCohorte = Number(selectedCohorte);

    if (isNaN(idTF) || isNaN(idFormacion) || isNaN(idCohorte)) {
      Alert.alert('Error', 'Hay datos inválidos en el formulario.');
      return;
    }

    setCreating(true);
    try {
      const estadoPago: 'PENDIENTE'|'PARCIAL'|'PAGADO' = 'PENDIENTE';

      const ahora = new Date();
      const fechaFormateada = ahora.toISOString().replace('T', ' ').substring(0, 19);
      
      const payload: any = {
        idPersona: idPersonaFinal,
        idTF: idTF,
        idFormacion: idFormacion,
        idCohorte: idCohorte,
        montoTotal: montoTotal,
        montoPagado: 0,
        estadoPago: estadoPago,
        fechaInscripcion: fechaFormateada,
      };

      console.log('📤 Enviando payload CORREGIDO:', JSON.stringify(payload, null, 2));

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
      console.error('❌ ERROR EN handleCreateInscripcion:');
      console.error('Status:', err.response?.status);
      console.error('Data:', err.response?.data);
      console.error('Config:', err.config?.data);
      
      if (err.response?.status === 500) {
        Alert.alert(
          'Error del Servidor (500)', 
          'Error interno del servidor. Contacte al administrador del sistema.'
        );
      } else if (err.response?.status === 400) {
        Alert.alert('Error de Validación (400)', JSON.stringify(err.response.data));
      } else {
        Alert.alert('Error', err.response?.data?.detail ?? err.message ?? 'Error desconocido');
      }
    } finally {
      setCreating(false);
    }
  };

  const resetForm = () => {
    setSelectedTipoFormacion(null);
    setSelectedFormacion(null);
    setSelectedCohorte(null);
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
                    {loadingUser ? (
                      <ActivityIndicator size="small" color="#4f8cff" />
                    ) : (
                      <Text style={styles.cedulaFijaText}>
                        {userInfo?.cedula || user?.cedula || 'No se pudo cargar la cédula'}
                      </Text>
                    )}
                  </View>
                  <Text style={styles.helpText}>
                    {loadingUser 
                      ? 'Cargando información del usuario...' 
                      : userInfo?.nombres && userInfo?.apellidos 
                        ? `Usuario: ${userInfo.nombres} ${userInfo.apellidos}`
                        : userInfo?.cedula 
                          ? `Cédula: ${userInfo.cedula}`
                          : 'Información del usuario no disponible'}
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
                      <Picker.Item label="Seleccione tipo de formación..." value={null} />
                      {tiposFormacion.map(tf => (
                        <Picker.Item 
                          key={tf.idTF} 
                          label={`${tf.nombreTipoFormacion} (ID: ${tf.idTF})`} 
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
                      enabled={formacionesFiltradas.length > 0}
                    >
                      <Picker.Item 
                        label={
                          formacionesFiltradas.length === 0 ? 
                          "Seleccione un tipo de formación primero..." : 
                          "Seleccione formación..."
                        } 
                        value={null} 
                      />
                      {formacionesFiltradas.map(f => (
                        <Picker.Item 
                          key={f.idFormacion} 
                          label={`${f.nombreFormacion} - $${f.valorInscripcion}`} 
                          value={f.idFormacion} 
                        />
                      ))}
                    </Picker>
                  </View>
                  <Text style={styles.helpText}>
                    {formacionesFiltradas.length > 0 
                      ? `${formacionesFiltradas.length} formación(es) disponible(s)` 
                      : 'No hay formaciones disponibles para el tipo seleccionado'}
                  </Text>
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
                      <Picker.Item label="Seleccione cohorte..." value={null} />
                      {cohortes.map(c => (
                        <Picker.Item 
                          key={c.idCohorte} 
                          label={`${c.nombreCohorte} (ID: ${c.idCohorte})`} 
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
                disabled={creating || loadingUser}
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