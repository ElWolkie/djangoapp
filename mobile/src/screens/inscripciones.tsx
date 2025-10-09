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
import { useNavigation } from '@react-navigation/native';
import { StackNavigationProp } from '@react-navigation/stack';
import { RootStackParamList } from '../../App';
import { 
  TipoFormacion, 
  Formacion, 
  Cohorte, 
  Inscripcion,
  Cuota 
} from '../types/inscripciones';

const { width, height } = Dimensions.get('window');
const isSmallScreen = width < 375;
const isMediumScreen = width >= 375 && width < 768;

const fmtMoney = (v: any) => {
  const n = Number(v);
  if (!isFinite(n)) return '—';
  return `$${n.toFixed(2)}`;
};

const InscripcionesScreen = () => {
  const navigation = useNavigation<any>();
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

  // Estados para la información del usuario
  const [userInfo, setUserInfo] = useState<{cedula?: string; idPersona?: number | null; nombres?: string; apellidos?: string} | null>(null);
  const [loadingUser, setLoadingUser] = useState(false);

  // 🔄 FUNCIÓN MEJORADA: Obtener información del usuario
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

  // 🔄 FUNCIÓN MEJORADA: Cargar inscripciones SOLO del usuario actual
  const fetchInscripciones = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      // Obtener información del usuario primero
      await obtenerInformacionUsuario();
      
      if (!userInfo?.idPersona) {
        console.log('❌ No hay idPersona para filtrar inscripciones');
        setItems([]);
        setMostradas([]);
        return;
      }

      console.log('🔍 Cargando inscripciones para idPersona:', userInfo.idPersona);
      
      // MODIFICADO: Filtrar por el usuario actual
      const res = await api.get('/api/inscripcion/');
      let data = Array.isArray(res.data) ? res.data : (res.data.results ?? []);
      
      // 🔥 FILTRAR SOLO LAS INSCRIPCIONES DEL USUARIO ACTUAL
      data = data.filter((inscripcion: Inscripcion) => {
        const inscripcionPersonaId = inscripcion.idPersona?.idPersona || inscripcion.idPersona;
        return inscripcionPersonaId === userInfo.idPersona;
      });

      console.log(`✅ Encontradas ${data.length} inscripciones para el usuario`);
      
      setItems(data);
      setMostradas(data);
    } catch (e: any) {
      console.error('fetchInscripciones error', e);
      setError(e?.response?.data?.detail ?? e?.message ?? 'Error al cargar inscripciones');
    } finally {
      setLoading(false);
    }
  }, [userInfo?.idPersona]);

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

      const extractData = (responseData: any, tipo: string) => {
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

        const mappedData = dataArray.map((item: any) => {
          if (tipo === 'tipos') {
            return {
              idTF: Number(item.idTF || item.id || item.tipo_id || 0),
              nombreTipoFormacion: item.nombreTipoFormacion || item.nombre || item.descripcion || 'Sin nombre'
            };
          }
          
          if (tipo === 'formaciones') {
            const rawIdTF = item.idTF || item.tipo_formacion || item.tipoFormacion || item.tipo_formacion_id || item.idTF_id || 0;
            const idTF = Number(rawIdTF);

            return {
              idFormacion: Number(item.idFormacion || item.id || 0),
              nombreFormacion: item.nombreFormacion || item.nombre || 'Sin nombre',
              idTF: idTF,
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
          if (tipo === 'tipos') return item.idTF > 0;
          if (tipo === 'formaciones') return item.idFormacion > 0;
          if (tipo === 'cohortes') return item.idCohorte > 0;
          return true;
        });

        return mappedData;
      };

      const tiposData = extractData(r1.data, 'tipos');
      const formacionesData = extractData(r2.data, 'formaciones');
      const cohortesData = extractData(r3.data, 'cohortes');

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
      obtenerInformacionUsuario();
    }
  }, [formModalVisible]);

  // Efecto principal para cargar datos
  useEffect(() => {
    fetchInscripciones();
    fetchDatosFormulario();
  }, [fetchInscripciones, fetchDatosFormulario]);

  // Filtrar formaciones cuando cambia el tipo de formación
  useEffect(() => {
    if (selectedTipoFormacion !== undefined && formaciones.length > 0) {
      const selectedTipoNum = Number(selectedTipoFormacion);
      const filtradas = formaciones.filter(f => Number(f.idTF) === selectedTipoNum);
      
      setFormacionesFiltradas(filtradas);
      setSelectedFormacion(undefined);
      
      if (filtradas.length === 1) {
        setSelectedFormacion(filtradas[0].idFormacion);
      }
    } else {
      setFormacionesFiltradas(formaciones);
    }
  }, [selectedTipoFormacion, formaciones]);

  // CALCULAR COSTOS
  useEffect(() => {
    if (selectedFormacion !== undefined) {
      const formacion = formaciones.find(f => f.idFormacion === selectedFormacion);
      
      if (formacion) {
        const valorMatricula = Number(formacion.valorInscripcion) || 0;
        setValorInscripcion(valorMatricula);
        
        // Datos hardcodeados por formación (temporal)
        let cuotasData: Cuota[] = [];
        
        if (formacion.idFormacion === 3 && formacion.nombreFormacion.includes('BIOTECNOLOGIA')) {
          cuotasData = [
            { nombreCuota: 'CUOTA I', valorCuota: 15 },
            { nombreCuota: 'CUOTA II', valorCuota: 10 },
            { nombreCuota: 'CUOTA III', valorCuota: 20 }
          ];
        }
        
        const totalCtas = cuotasData.reduce((sum, cuota) => sum + cuota.valorCuota, 0);
        const totalFinal = valorMatricula + totalCtas;
        
        setCuotas(cuotasData);
        setTotalCuotas(totalCtas);
        setMontoTotal(totalFinal);
      }
    }
  }, [selectedFormacion, formaciones]);

  // Filtrar inscripciones por búsqueda
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

  const openDetail = (item: any) => {
    setSelected(item);
    setDetailModalVisible(true);
  };

  const validateCreateForm = () => {
    const errs: Record<string,string> = {};
    if (selectedTipoFormacion === undefined) 
      errs.tipoFormacion = 'Seleccione un tipo de formación';
    if (selectedFormacion === undefined) 
      errs.formacion = 'Seleccione una formación';
    if (selectedCohorte === undefined) 
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

    if (!userInfo?.idPersona) {
      Alert.alert('Error', 'No se pudo identificar su usuario. Por favor, cierre sesión y vuelva a ingresar.');
      return;
    }

    setCreating(true);

    try {
      const payload = {
        "idPersona": userInfo.idPersona,
        "idTF": selectedTipoFormacion,
        "idFormacion": selectedFormacion,
        "idCohorte": selectedCohorte,
        "montoTotal": montoTotal,
        "montoPagado": 0,
        "estadoPago": "PENDIENTE",
        "fechaInscripcion": new Date().toISOString().slice(0, 19).replace('T', ' ')
      };

      console.log("📤 Enviando payload:", payload);

      const res = await api.post('/api/inscripcion/', payload);
      
      if (res.status === 201 || res.status === 200) {
        console.log('✅ Inscripción creada, ID:', res.data.idInscripcion);
        
        // Crear nota de cobro automáticamente
        try {
          const notaResponse = await api.post('/api/nota-cobro/create/', {
            idInscripcion: res.data.idInscripcion
          });
          
          if (notaResponse.data.success) {
            console.log('✅ Nota de cobro creada:', notaResponse.data.data);
            
            navigation.navigate('pago', {
              notaData: notaResponse.data.data,
              inscripcionId: res.data.idInscripcion
            });
            
            Alert.alert('Éxito', 'Inscripción y nota de cobro creadas correctamente. Proceda al pago.');
          } else {
            throw new Error(notaResponse.data.message);
          }
        } catch (notaError) {
          console.error('❌ Error creando nota de cobro:', notaError);
          Alert.alert(
            'Atención', 
            'Inscripción creada pero hubo un error al generar la nota de cobro. Contacte al administrador.'
          );
        }
        
        setFormModalVisible(false);
        resetForm();
        await fetchInscripciones();
      }
    } catch (err: any) {
      console.error('❌ ERROR EN handleCreateInscripcion:', err.response?.data);
      
      if (err.response?.status === 400) {
        let errorMessage = 'Errores de validación:\n';
        
        if (err.response.data && typeof err.response.data === 'object') {
          Object.keys(err.response.data).forEach(key => {
            if (Array.isArray(err.response.data[key])) {
              errorMessage += `• ${key}: ${err.response.data[key].join(', ')}\n`;
            } else {
              errorMessage += `• ${key}: ${err.response.data[key]}\n`;
            }
          });
        } else {
          errorMessage = err.response.data?.detail || JSON.stringify(err.response.data);
        }
        
        Alert.alert('Error de Validación', errorMessage);
        return;
      }
      
      Alert.alert('Error', err.response?.data?.detail ?? err.message ?? 'Error desconocido al crear inscripción');
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
      {/* HEADER MEJORADO PARA MÓVIL */}
      <View style={[styles.header, isSmallScreen && styles.headerSmall]}>
        <Text style={[styles.title, isSmallScreen && styles.titleSmall]}>Mis Inscripciones</Text>
        <TouchableOpacity 
          style={[styles.addButton, isSmallScreen && styles.addButtonSmall]} 
          onPress={() => setFormModalVisible(true)}
        >
          <Icon name="plus" size={isSmallScreen ? 20 : 24} color="#fff" />
          <Text style={[styles.addButtonText, isSmallScreen && styles.addButtonTextSmall]}>Nueva</Text>
        </TouchableOpacity>
      </View>

      {/* SEARCH BAR MEJORADO */}
      <View style={[styles.searchContainer, isSmallScreen && styles.searchContainerSmall]}>
        <View style={[styles.searchWrapper, isSmallScreen && styles.searchWrapperSmall]}>
          <Icon name="magnify" size={isSmallScreen ? 18 : 20} color="#666" />
          <TextInput
            placeholder="Buscar por formación, cohorte o estado..."
            value={searchText}
            onChangeText={setSearchText}
            style={[styles.searchInput, isSmallScreen && styles.searchInputSmall]}
            placeholderTextColor="#999"
          />
        </View>
      </View>

      {/* LISTA DE INSCRIPCIONES */}
      <FlatList
        data={mostradas}
        keyExtractor={(i) => String(i.idInscripcion ?? i.id ?? Math.random())}
        renderItem={({item}) => {
          const status = deriveStatus(item);
          return (
            <View style={[styles.card, isSmallScreen && styles.cardSmall]}>
              <View style={styles.cardHeader}>
                <View style={[styles.cardTitleContainer, isSmallScreen && styles.cardTitleContainerSmall]}>
                  <Text style={[styles.cardTitle, isSmallScreen && styles.cardTitleSmall]} numberOfLines={2}>
                    {item.idFormacion_detail?.nombreFormacion ?? '—'}
                  </Text>
                  <View style={[styles.badge, statusColor(status), isSmallScreen && styles.badgeSmall]}>
                    <Text style={[styles.badgeText, isSmallScreen && styles.badgeTextSmall]}>{status}</Text>
                  </View>
                </View>
                <Text style={[styles.cardSubtitle, isSmallScreen && styles.cardSubtitleSmall]}>
                  {item.idPersona_detail?.nombres} {item.idPersona_detail?.apellidos}
                </Text>
              </View>

              <View style={[styles.cardContent, isSmallScreen && styles.cardContentSmall]}>
                <View style={[styles.detailRow, isSmallScreen && styles.detailRowSmall]}>
                  <View style={styles.detailItem}>
                    <Icon name="domain" size={isSmallScreen ? 14 : 16} color="#666" />
                    <Text style={[styles.detailText, isSmallScreen && styles.detailTextSmall]}>
                      {item.idCohorte_detail?.nombreCohorte ?? '—'}
                    </Text>
                  </View>
                  <View style={styles.detailItem}>
                    <Icon name="cash" size={isSmallScreen ? 14 : 16} color="#666" />
                    <Text style={[styles.detailText, isSmallScreen && styles.detailTextSmall]}>
                      {fmtMoney(item.montoTotal)}
                    </Text>
                  </View>
                </View>
                
                <View style={[styles.detailRow, isSmallScreen && styles.detailRowSmall]}>
                  <View style={styles.detailItem}>
                    <Icon name="calendar" size={isSmallScreen ? 14 : 16} color="#666" />
                    <Text style={[styles.detailText, isSmallScreen && styles.detailTextSmall]}>
                      {item.fechaInscripcion ? new Date(item.fechaInscripcion).toLocaleDateString() : '—'}
                    </Text>
                  </View>
                </View>
              </View>

              <TouchableOpacity 
                style={[styles.cardButton, isSmallScreen && styles.cardButtonSmall]} 
                onPress={() => openDetail(item)}
              >
                <Text style={[styles.cardButtonText, isSmallScreen && styles.cardButtonTextSmall]}>
                  Ver detalles
                </Text>
                <Icon name="chevron-right" size={isSmallScreen ? 18 : 20} color="#4f8cff" />
              </TouchableOpacity>
            </View>
          );
        }}
        contentContainerStyle={[styles.listContent, isSmallScreen && styles.listContentSmall]}
        ListEmptyComponent={
          <View style={styles.emptyState}>
            <Icon name="clipboard-text-outline" size={isSmallScreen ? 48 : 64} color="#ccc" />
            <Text style={[styles.emptyText, isSmallScreen && styles.emptyTextSmall]}>
              {loading ? 'Cargando...' : 'No tienes inscripciones registradas'}
            </Text>
            <TouchableOpacity 
              style={[styles.addButton, isSmallScreen && styles.addButtonSmall, {marginTop: 16}]}
              onPress={() => setFormModalVisible(true)}
            >
              <Icon name="plus" size={isSmallScreen ? 18 : 20} color="#fff" />
              <Text style={[styles.addButtonText, isSmallScreen && styles.addButtonTextSmall]}>
                Crear primera inscripción
              </Text>
            </TouchableOpacity>
          </View>
        }
      />

      {/* MODAL DE DETALLE - MEJORADO PARA MÓVIL */}
      <Modal 
        isVisible={detailModalVisible} 
        onBackdropPress={() => setDetailModalVisible(false)}
        style={[styles.modal, isSmallScreen && styles.modalSmall]}
      >
        <View style={[styles.modalContent, isSmallScreen && styles.modalContentSmall]}>
          <View style={[styles.modalHeader, isSmallScreen && styles.modalHeaderSmall]}>
            <Text style={[styles.modalTitle, isSmallScreen && styles.modalTitleSmall]}>
              Detalles de Inscripción
            </Text>
            <TouchableOpacity 
              style={styles.closeButton}
              onPress={() => setDetailModalVisible(false)}
            >
              <Icon name="close" size={isSmallScreen ? 20 : 24} color="#666" />
            </TouchableOpacity>
          </View>
          
          <ScrollView style={styles.modalBody}>
            {selected && [
              ['Formación', selected.idFormacion_detail?.nombreFormacion ?? '—'],
              ['Cohorte', selected.idCohorte_detail?.nombreCohorte ?? '—'],
              ['Cédula', selected.idPersona_detail?.cedula ?? '—'],
              ['Nombres', selected.idPersona_detail?.nombres ?? '—'],
              ['Apellidos', selected.idPersona_detail?.apellidos ?? '—'],
              ['Fecha inscripción', selected.fechaInscripcion ? new Date(selected.fechaInscripcion).toLocaleString() : '—'],
              ['Estado pago', deriveStatus(selected)],
              ['Monto total', fmtMoney(selected.montoTotal)],
              ['Monto pagado', fmtMoney(selected.montoPagado)],
              ['Saldo pendiente', fmtMoney(selected.saldoPendiente)],
            ].map(([lbl,val]) => (
              <View key={String(lbl)} style={[styles.detailRowModal, isSmallScreen && styles.detailRowModalSmall]}>
                <Text style={[styles.detailLabel, isSmallScreen && styles.detailLabelSmall]}>{lbl}:</Text>
                <Text style={[styles.detailValue, isSmallScreen && styles.detailValueSmall]}>{val}</Text>
              </View>
            ))}
          </ScrollView>

          <View style={[styles.modalFooter, isSmallScreen && styles.modalFooterSmall]}>
            <TouchableOpacity 
              style={[styles.modalButton, isSmallScreen && styles.modalButtonSmall]}
              onPress={() => setDetailModalVisible(false)}
            >
              <Text style={[styles.modalButtonText, isSmallScreen && styles.modalButtonTextSmall]}>Cerrar</Text>
            </TouchableOpacity>
          </View>
        </View>
      </Modal>

      {/* MODAL DE FORMULARIO - COMPLETAMENTE RESPONSIVE */}
      <Modal
        isVisible={formModalVisible}
        onBackdropPress={() => setFormModalVisible(false)}
        style={[styles.modal, isSmallScreen && styles.modalSmall]}
      >
        <KeyboardAvoidingView 
          behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
          style={styles.keyboardAvoid}
        >
          <View style={[styles.formModal, isSmallScreen && styles.formModalSmall]}>
            <View style={[styles.modalHeader, isSmallScreen && styles.modalHeaderSmall]}>
              <Text style={[styles.modalTitle, isSmallScreen && styles.modalTitleSmall]}>
                Nueva Inscripción
              </Text>
              <TouchableOpacity 
                style={styles.closeButton}
                onPress={() => setFormModalVisible(false)}
              >
                <Icon name="close" size={isSmallScreen ? 20 : 24} color="#666" />
              </TouchableOpacity>
            </View>

            <ScrollView 
              style={styles.formBody}
              showsVerticalScrollIndicator={false}
              contentContainerStyle={[styles.formContent, isSmallScreen && styles.formContentSmall]}
            >
              {/* Sección Información Personal */}
              <View style={styles.formSection}>
                <Text style={[styles.sectionTitle, isSmallScreen && styles.sectionTitleSmall]}>
                  Información Personal
                </Text>
                
                <View style={styles.fieldContainer}>
                  <Text style={[styles.label, isSmallScreen && styles.labelSmall]}>Cédula del Cliente</Text>
                  <View style={[styles.cedulaFijaContainer, isSmallScreen && styles.cedulaFijaContainerSmall]}>
                    <Icon name="account" size={isSmallScreen ? 16 : 20} color="#4f8cff" />
                    {loadingUser ? (
                      <ActivityIndicator size="small" color="#4f8cff" />
                    ) : (
                      <Text style={[styles.cedulaFijaText, isSmallScreen && styles.cedulaFijaTextSmall]}>
                        {userInfo?.cedula || user?.cedula || 'No se pudo cargar la cédula'}
                      </Text>
                    )}
                  </View>
                  <Text style={[styles.helpText, isSmallScreen && styles.helpTextSmall]}>
                    {userInfo?.nombres && userInfo?.apellidos 
                      ? `Usuario: ${userInfo.nombres} ${userInfo.apellidos}`
                      : 'Información del usuario actual'}
                  </Text>
                </View>
              </View>

              {/* Sección Información Académica */}
              <View style={styles.formSection}>
                <Text style={[styles.sectionTitle, isSmallScreen && styles.sectionTitleSmall]}>
                  Información Académica
                </Text>

                {/* Picker para Tipo de Formación */}
                <View style={styles.fieldContainer}>
                  <Text style={[styles.label, isSmallScreen && styles.labelSmall]}>Tipo de Formación *</Text>
                  <View style={[styles.pickerContainer, isSmallScreen && styles.pickerContainerSmall]}>
                    <Picker
                      selectedValue={selectedTipoFormacion}
                      onValueChange={(itemValue) => setSelectedTipoFormacion(itemValue !== undefined ? Number(itemValue) : undefined)}
                      style={[styles.picker, isSmallScreen && styles.pickerSmall]}
                    >
                      <Picker.Item label="Seleccione tipo de formación..." value={undefined} />
                      {tiposFormacion.map(tf => (
                        <Picker.Item 
                          key={tf.idTF} 
                          label={`${tf.nombreTipoFormacion}`} 
                          value={tf.idTF} 
                        />
                      ))}
                    </Picker>
                  </View>
                  {formErrors.tipoFormacion && (
                    <Text style={[styles.errorText, isSmallScreen && styles.errorTextSmall]}>{formErrors.tipoFormacion}</Text>
                  )}
                </View>

                {/* Picker para Formación */}
                <View style={styles.fieldContainer}>
                  <Text style={[styles.label, isSmallScreen && styles.labelSmall]}>Formación Académica *</Text>
                  <View style={[styles.pickerContainer, isSmallScreen && styles.pickerContainerSmall]}>
                    <Picker
                      selectedValue={selectedFormacion}
                      onValueChange={(itemValue) => setSelectedFormacion(itemValue !== undefined ? Number(itemValue) : undefined)}
                      style={[styles.picker, isSmallScreen && styles.pickerSmall]}
                      enabled={formacionesFiltradas.length > 0}
                    >
                      <Picker.Item 
                        label={
                          formacionesFiltradas.length === 0 ? 
                          "Seleccione tipo primero" : 
                          "Seleccione formación..."
                        } 
                        value={undefined} 
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
                  {formErrors.formacion && (
                    <Text style={[styles.errorText, isSmallScreen && styles.errorTextSmall]}>{formErrors.formacion}</Text>
                  )}
                </View>

                <View style={styles.fieldContainer}>
                  <Text style={[styles.label, isSmallScreen && styles.labelSmall]}>Cohorte *</Text>
                  <View style={[styles.pickerContainer, isSmallScreen && styles.pickerContainerSmall]}>
                    <Picker
                      selectedValue={selectedCohorte}
                      onValueChange={(itemValue) => setSelectedCohorte(itemValue !== undefined ? Number(itemValue) : undefined)}
                      style={[styles.picker, isSmallScreen && styles.pickerSmall]}
                    >
                      <Picker.Item label="Seleccione cohorte..." value={undefined} />
                      {cohortes.map(c => (
                        <Picker.Item 
                          key={c.idCohorte} 
                          label={`${c.nombreCohorte}`} 
                          value={c.idCohorte} 
                        />
                      ))}
                    </Picker>
                  </View>
                  {formErrors.cohorte && (
                    <Text style={[styles.errorText, isSmallScreen && styles.errorTextSmall]}>{formErrors.cohorte}</Text>
                  )}
                </View>
              </View>

              {/* Sección Resumen de Costos */}
              <View style={styles.formSection}>
                <Text style={[styles.sectionTitle, isSmallScreen && styles.sectionTitleSmall]}>
                  Resumen de Costos
                </Text>
                
                <View style={[styles.costosTable, isSmallScreen && styles.costosTableSmall]}>
                  <View style={[styles.tableHeader, isSmallScreen && styles.tableHeaderSmall]}>
                    <Text style={[styles.tableHeaderText, isSmallScreen && styles.tableHeaderTextSmall]}>Concepto</Text>
                    <Text style={[styles.tableHeaderText, isSmallScreen && styles.tableHeaderTextSmall]}>Monto</Text>
                  </View>
                  
                  <View style={[styles.tableRow, isSmallScreen && styles.tableRowSmall]}>
                    <Text style={[styles.tableCell, isSmallScreen && styles.tableCellSmall]}>
                      <Text style={styles.boldText}>Valor de Inscripción</Text>
                    </Text>
                    <Text style={[styles.tableCell, styles.inscripcionCell, isSmallScreen && styles.tableCellSmall]}>
                      <Text style={styles.boldText}>{fmtMoney(valorInscripcion)}</Text>
                    </Text>
                  </View>
                  
                  {cuotas.length > 0 ? (
                    <>
                      {cuotas.map((cuota, index) => (
                        <View key={index} style={[styles.tableRow, isSmallScreen && styles.tableRowSmall]}>
                          <Text style={[styles.tableCell, isSmallScreen && styles.tableCellSmall]}>
                            <Text style={styles.boldText}>
                              {cuota.nombreCuota || `Cuota ${index + 1}`}
                            </Text>
                          </Text>
                          <Text style={[styles.tableCell, isSmallScreen && styles.tableCellSmall]}>
                            {fmtMoney(cuota.valorCuota)}
                          </Text>
                        </View>
                      ))}
                      <View style={[styles.tableRow, isSmallScreen && styles.tableRowSmall]}>
                        <Text style={[styles.tableCell, isSmallScreen && styles.tableCellSmall]}>
                          <Text style={styles.boldText}>Total Cuotas</Text>
                        </Text>
                        <Text style={[styles.tableCell, styles.cuotasCell, isSmallScreen && styles.tableCellSmall]}>
                          <Text style={styles.boldText}>{fmtMoney(totalCuotas)}</Text>
                        </Text>
                      </View>
                    </>
                  ) : (
                    <View style={[styles.tableRow, isSmallScreen && styles.tableRowSmall]}>
                      <Text style={[styles.tableCell, styles.noCuotasText, isSmallScreen && styles.tableCellSmall]}>
                        No hay cuotas configuradas
                      </Text>
                      <Text style={[styles.tableCell, styles.noCuotasText, isSmallScreen && styles.tableCellSmall]}>
                        $0.00
                      </Text>
                    </View>
                  )}
                  
                  <View style={[styles.tableRow, styles.totalRow, isSmallScreen && styles.tableRowSmall]}>
                    <Text style={[styles.tableCell, isSmallScreen && styles.tableCellSmall]}>
                      <Text style={styles.boldText}>Total a Pagar</Text>
                    </Text>
                    <Text style={[styles.tableCell, styles.totalCell, isSmallScreen && styles.tableCellSmall]}>
                      <Text style={styles.boldText}>{fmtMoney(montoTotal)}</Text>
                    </Text>
                  </View>
                </View>
              </View>

              {/* Sección Fecha Automática */}
              <View style={styles.formSection}>
                <Text style={[styles.sectionTitle, isSmallScreen && styles.sectionTitleSmall]}>
                  Información de Registro
                </Text>
                
                <View style={styles.fieldContainer}>
                  <Text style={[styles.label, isSmallScreen && styles.labelSmall]}>Fecha y Hora de Inscripción</Text>
                  <View style={[styles.fechaContainer, isSmallScreen && styles.fechaContainerSmall]}>
                    <Icon name="calendar-clock" size={isSmallScreen ? 16 : 20} color="#4f8cff" />
                    <Text style={[styles.fechaText, isSmallScreen && styles.fechaTextSmall]}>{fechaInscripcion}</Text>
                  </View>
                </View>
              </View>
            </ScrollView>

            <View style={[styles.formFooter, isSmallScreen && styles.formFooterSmall]}>
              <TouchableOpacity 
                style={[styles.formButton, styles.cancelButton, isSmallScreen && styles.formButtonSmall]}
                onPress={() => setFormModalVisible(false)}
              >
                <Text style={[styles.cancelButtonText, isSmallScreen && styles.cancelButtonTextSmall]}>Cancelar</Text>
              </TouchableOpacity>

              <TouchableOpacity 
                style={[styles.formButton, styles.submitButton, isSmallScreen && styles.formButtonSmall]}
                onPress={handleCreateInscripcion}
                disabled={creating || loadingUser}
              >
                {creating ? (
                  <ActivityIndicator color="#fff" size="small" />
                ) : (
                  <>
                    <Icon name="check" size={isSmallScreen ? 16 : 20} color="#fff" />
                    <Text style={[styles.submitButtonText, isSmallScreen && styles.submitButtonTextSmall]}>
                      Crear Inscripción
                    </Text>
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

// ESTILOS COMPLETAMENTE RESPONSIVE
const styles = StyleSheet.create({
  // Estilos base
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
  
  // Header responsive
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
  headerSmall: {
    paddingHorizontal: 16,
    paddingTop: 16,
    paddingBottom: 8,
  },
  title: { 
    fontSize: 28, 
    fontWeight: '700', 
    color: '#1a365d',
  },
  titleSmall: {
    fontSize: 22,
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
  addButtonSmall: {
    paddingHorizontal: 12,
    paddingVertical: 8,
    gap: 6,
  },
  addButtonText: {
    color: '#fff',
    fontWeight: '600',
    fontSize: 16,
  },
  addButtonTextSmall: {
    fontSize: 14,
  },
  
  // Search responsive
  searchContainer: {
    padding: 20,
    backgroundColor: '#fff',
    borderBottomWidth: 1,
    borderBottomColor: '#e1e5e9',
  },
  searchContainerSmall: {
    padding: 16,
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
  searchWrapperSmall: {
    paddingHorizontal: 12,
    height: 44,
    borderRadius: 10,
  },
  searchInput: {
    flex: 1,
    fontSize: 16,
    marginLeft: 12,
    color: '#333',
  },
  searchInputSmall: {
    fontSize: 14,
    marginLeft: 8,
  },
  
  // List responsive
  listContent: {
    padding: 20,
    paddingTop: 10,
  },
  listContentSmall: {
    padding: 16,
    paddingTop: 8,
  },
  
  // Card responsive
  card: {
    backgroundColor: '#fff',
    borderRadius: 16,
    padding: 20,
    marginBottom: 16,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 3.84,
    elevation: 5,
    borderWidth: 1,
    borderColor: '#f1f3f4',
  },
  cardSmall: {
    padding: 16,
    borderRadius: 12,
    marginBottom: 12,
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
  cardTitleContainerSmall: {
    marginBottom: 6,
    flexDirection: 'column',
    alignItems: 'flex-start',
    gap: 8,
  },
  cardTitle: {
    fontSize: 18,
    fontWeight: '600',
    color: '#1a365d',
    flex: 1,
    marginRight: 12,
  },
  cardTitleSmall: {
    fontSize: 16,
    marginRight: 0,
  },
  cardSubtitle: {
    fontSize: 14,
    color: '#666',
    fontWeight: '500',
  },
  cardSubtitleSmall: {
    fontSize: 13,
  },
  cardContent: {
    marginBottom: 16,
  },
  cardContentSmall: {
    marginBottom: 12,
  },
  detailRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginBottom: 12,
  },
  detailRowSmall: {
    marginBottom: 8,
    flexDirection: 'column',
    gap: 8,
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
  detailTextSmall: {
    fontSize: 13,
    marginLeft: 6,
  },
  cardButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: 12,
    borderTopWidth: 1,
    borderTopColor: '#f1f3f4',
  },
  cardButtonSmall: {
    paddingVertical: 10,
  },
  cardButtonText: {
    color: '#4f8cff',
    fontWeight: '600',
    fontSize: 16,
    marginRight: 8,
  },
  cardButtonTextSmall: {
    fontSize: 14,
    marginRight: 6,
  },
  
  // Badge responsive
  badge: {
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 20,
    minWidth: 80,
    alignItems: 'center',
  },
  badgeSmall: {
    paddingHorizontal: 10,
    paddingVertical: 4,
    minWidth: 70,
    borderRadius: 16,
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
  badgeTextSmall: {
    fontSize: 11,
  },
  
  // Empty state
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
  emptyTextSmall: {
    fontSize: 14,
    marginTop: 12,
  },
  errorText: {
    color: '#e53e3e',
    fontSize: 14,
    marginTop: 4,
    fontWeight: '500',
  },
  errorTextSmall: {
    fontSize: 12,
  },
  
  // Modal responsive
  modal: {
    margin: 0,
    justifyContent: 'center',
    alignItems: 'center',
  },
  modalSmall: {
    paddingHorizontal: 10,
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
  modalContentSmall: {
    width: '100%',
    maxHeight: height * 0.85,
    borderRadius: 16,
  },
  formModal: {
    backgroundColor: '#fff',
    borderRadius: 20,
    width: width * 0.9,
    maxWidth: 500,
    maxHeight: height * 0.9,
    overflow: 'hidden',
  },
  formModalSmall: {
    width: '100%',
    maxHeight: height * 0.95,
    borderRadius: 16,
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
  modalHeaderSmall: {
    padding: 20,
    paddingBottom: 12,
  },
  modalTitle: {
    fontSize: 24,
    fontWeight: '700',
    color: '#1a365d',
    flex: 1,
  },
  modalTitleSmall: {
    fontSize: 20,
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
  formContentSmall: {
    paddingBottom: 16,
  },
  modalFooter: {
    padding: 24,
    paddingTop: 16,
    borderTopWidth: 1,
    borderTopColor: '#e1e5e9',
  },
  modalFooterSmall: {
    padding: 20,
    paddingTop: 12,
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
  detailRowModalSmall: {
    paddingVertical: 10,
    paddingHorizontal: 20,
    flexDirection: 'column',
    gap: 4,
  },
  detailLabel: {
    fontWeight: '600',
    fontSize: 16,
    color: '#4a5568',
    flex: 1,
  },
  detailLabelSmall: {
    fontSize: 14,
  },
  detailValue: {
    flex: 1,
    fontSize: 16,
    color: '#2d3748',
    textAlign: 'right',
    fontWeight: '500',
  },
  detailValueSmall: {
    fontSize: 14,
    textAlign: 'left',
  },
  modalButton: {
    backgroundColor: '#4f8cff',
    paddingVertical: 14,
    borderRadius: 12,
    alignItems: 'center',
  },
  modalButtonSmall: {
    paddingVertical: 12,
    borderRadius: 10,
  },
  modalButtonText: {
    color: '#fff',
    fontWeight: '600',
    fontSize: 16,
  },
  modalButtonTextSmall: {
    fontSize: 14,
  },
  
  // Form styles responsive
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
  sectionTitleSmall: {
    fontSize: 16,
    marginBottom: 12,
    paddingHorizontal: 20,
    paddingTop: 12,
  },
  fieldContainer: {
    marginBottom: 16,
    paddingHorizontal: 24,
  },
  fieldContainerSmall: {
    marginBottom: 12,
    paddingHorizontal: 20,
  },
  label: {
    fontWeight: '600',
    color: '#4a5568',
    marginBottom: 8,
    fontSize: 15,
  },
  labelSmall: {
    fontSize: 14,
    marginBottom: 6,
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
  cedulaFijaContainerSmall: {
    paddingHorizontal: 12,
    paddingVertical: 12,
    gap: 8,
    borderRadius: 10,
  },
  cedulaFijaText: {
    fontSize: 16,
    fontWeight: '600',
    color: '#4a5568',
  },
  cedulaFijaTextSmall: {
    fontSize: 14,
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
  fechaContainerSmall: {
    paddingHorizontal: 12,
    paddingVertical: 12,
    gap: 8,
    borderRadius: 10,
  },
  fechaText: {
    fontSize: 16,
    fontWeight: '600',
    color: '#22543d',
  },
  fechaTextSmall: {
    fontSize: 14,
  },
  helpText: {
    fontSize: 12,
    color: '#6c757d',
    marginTop: 4,
    fontStyle: 'italic',
  },
  helpTextSmall: {
    fontSize: 11,
  },
  pickerContainer: {
    borderWidth: 1,
    borderColor: '#e1e5e9',
    borderRadius: 12,
    backgroundColor: '#fff',
    overflow: 'hidden',
  },
  pickerContainerSmall: {
    borderRadius: 10,
  },
  picker: {
    height: 52,
  },
  pickerSmall: {
    height: 44,
  },
  
  // Costos table responsive
  costosTable: {
    borderWidth: 1,
    borderColor: '#e1e5e9',
    borderRadius: 12,
    overflow: 'hidden',
    marginHorizontal: 24,
  },
  costosTableSmall: {
    marginHorizontal: 20,
    borderRadius: 10,
  },
  tableHeader: {
    flexDirection: 'row',
    backgroundColor: '#f8f9fa',
    paddingVertical: 12,
    paddingHorizontal: 16,
    borderBottomWidth: 1,
    borderBottomColor: '#e1e5e9',
  },
  tableHeaderSmall: {
    paddingVertical: 10,
    paddingHorizontal: 12,
  },
  tableHeaderText: {
    flex: 1,
    fontWeight: '700',
    color: '#4a5568',
    fontSize: 16,
  },
  tableHeaderTextSmall: {
    fontSize: 14,
  },
  tableRow: {
    flexDirection: 'row',
    paddingVertical: 12,
    paddingHorizontal: 16,
    borderBottomWidth: 1,
    borderBottomColor: '#f8f9fa',
  },
  tableRowSmall: {
    paddingVertical: 10,
    paddingHorizontal: 12,
  },
  tableCell: {
    flex: 1,
    fontSize: 15,
    color: '#4a5568',
  },
  tableCellSmall: {
    fontSize: 13,
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
  noCuotasText: {
    color: '#999',
    fontStyle: 'italic',
    textAlign: 'center',
  },
  
  // Form footer responsive
  formFooter: {
    flexDirection: 'row',
    padding: 24,
    paddingTop: 16,
    borderTopWidth: 1,
    borderTopColor: '#e1e5e9',
    gap: 12,
  },
  formFooterSmall: {
    padding: 20,
    paddingTop: 12,
    gap: 8,
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
  formButtonSmall: {
    paddingVertical: 14,
    borderRadius: 10,
    gap: 6,
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
  cancelButtonTextSmall: {
    fontSize: 14,
  },
  submitButton: {
    backgroundColor: '#4f8cff',
  },
  submitButtonText: {
    color: '#fff',
    fontWeight: '600',
    fontSize: 16,
  },
  submitButtonTextSmall: {
    fontSize: 14,
  },
});

export default InscripcionesScreen;