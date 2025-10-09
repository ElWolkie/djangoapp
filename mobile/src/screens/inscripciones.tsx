// src/screens/inscripciones.tsx
import React, { useCallback, useEffect, useState, useContext } from 'react';
import {
  View,
  Text,
  FlatList,
  ActivityIndicator,
  StyleSheet,
  useWindowDimensions,
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
import { useNavigation } from '@react-navigation/native';
import api from '../api/api';
import { AuthContext } from '../contexts/AuthContext';
import {
  TipoFormacion,
  Formacion,
  Cohorte,
  Inscripcion,
  Cuota
} from '../types/inscripciones';

const fmtMoney = (v: any) => {
  const n = Number(v);
  if (!isFinite(n)) return '—';
  return `$${n.toFixed(2)}`;
};

// Normalizar cédula
const normalizarCedula = (cedula: string): string => {
  if (!cedula) return '';
  let normalizada = cedula.toString().toUpperCase().replace(/[\.\-\s]/g, '');
  if (/^[VEJG]/.test(normalizada)) {
    normalizada = normalizada.substring(1);
  }
  return normalizada;
};

const InscripcionesScreen = () => {
  const navigation = useNavigation<any>();
  const { user } = useContext(AuthContext);

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
  const [formErrors, setFormErrors] = useState<Record<string, string>>({});

  // Responsive helpers
  const { width, height } = useWindowDimensions();
  const isSmallScreen = width <= 620;
  const isTablet = width > 420 && width < 1024;
  const isLargeScreen = width >= 900;

  // FETCH INSCRIPCIONES (filtrando por cédula del user)
  const fetchInscripciones = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      if (!user?.cedula) {
        setItems([]);
        setMostradas([]);
        return;
      }
      const cedulaUsuarioNormalizada = normalizarCedula(user.cedula);
      const res = await api.get('/api/inscripcion/');
      let todasLasInscripciones = Array.isArray(res.data) ? res.data : (res.data.results ?? []);
      const inscripcionesUsuario = todasLasInscripciones.filter((inscripcion: Inscripcion) => {
        const cedulaInscripcion =
          inscripcion.idPersona_detail?.cedula ||
          inscripcion.idPersona?.cedula;
        if (!cedulaInscripcion) return false;
        const cedulaInscNormalizada = normalizarCedula(cedulaInscripcion);
        return cedulaInscNormalizada === cedulaUsuarioNormalizada;
      });
      setItems(inscripcionesUsuario);
      setMostradas(inscripcionesUsuario);
    } catch (e: any) {
      setError(e?.response?.data?.detail ?? e?.message ?? 'Error al cargar inscripciones');
    } finally {
      setLoading(false);
    }
  }, [user?.cedula]);

  // Load tipos formacion, formaciones & cohortes
  const fetchDatosFormulario = useCallback(async () => {
    try {
      const [r1, r2, r3] = await Promise.all([
        api.get('/api/tipo-formaciones/').catch(() => ({ data: [] })),
        api.get('/api/formaciones/').catch(() => ({ data: [] })),
        api.get('/api/cohorte/').catch(() => ({ data: [] })),
      ]);

      const extractData = (responseData: any, tipo: string) => {
        let dataArray: any[] = [];
        if (Array.isArray(responseData)) dataArray = responseData;
        else if (responseData && Array.isArray(responseData.results)) dataArray = responseData.results;
        else if (responseData && responseData.data && Array.isArray(responseData.data)) dataArray = responseData.data;
        else if (responseData && typeof responseData === 'object') dataArray = [responseData];
        else dataArray = [];

        const mapped = dataArray.map((item: any) => {
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
              idTF,
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
        }).filter((it: any) => {
          if (tipo === 'tipos') return it.idTF > 0;
          if (tipo === 'formaciones') return it.idFormacion > 0;
          if (tipo === 'cohortes') return it.idCohorte > 0;
          return true;
        });

        return mapped;
      };

      setTiposFormacion(extractData(r1.data, 'tipos'));
      setFormaciones(extractData(r2.data, 'formaciones'));
      setCohortes(extractData(r3.data, 'cohortes'));
    } catch (e) {
      Alert.alert('Error', 'No se pudieron cargar los datos del formulario');
    }
  }, []);

  // Fecha
  const establecerFechaActual = () => {
    const ahora = new Date();
    const fecha = ahora.toISOString().split('T')[0];
    const hora = ahora.toTimeString().split(' ')[0];
    setFechaInscripcion(`${fecha} ${hora}`);
  };

  useEffect(() => {
    if (formModalVisible) {
      establecerFechaActual();
      fetchDatosFormulario();
    }
  }, [formModalVisible, fetchDatosFormulario]);

  useEffect(() => {
    fetchInscripciones();
  }, [fetchInscripciones]);

  // Filtrar formaciones al seleccionar tipo
  useEffect(() => {
    if (selectedTipoFormacion !== undefined && formaciones.length > 0) {
      const selectedTipoNum = Number(selectedTipoFormacion);
      const filtradas = formaciones.filter(f => Number(f.idTF) === selectedTipoNum);
      setFormacionesFiltradas(filtradas);
      setSelectedFormacion(undefined);
      if (filtradas.length === 1) setSelectedFormacion(filtradas[0].idFormacion);
    } else {
      setFormacionesFiltradas(formaciones);
    }
  }, [selectedTipoFormacion, formaciones]);

  // calcular costos
  useEffect(() => {
    if (selectedFormacion !== undefined) {
      const formacion = formaciones.find(f => f.idFormacion === selectedFormacion);
      if (formacion) {
        const valorMatricula = Number(formacion.valorInscripcion) || 0;
        setValorInscripcion(valorMatricula);
        let cuotasData: Cuota[] = [];
        if (formacion.idFormacion === 3 && formacion.nombreFormacion.includes('BIOTECNOLOGIA')) {
          cuotasData = [
            { nombreCuota: 'CUOTA I', valorCuota: 15 },
            { nombreCuota: 'CUOTA II', valorCuota: 10 },
            { nombreCuota: 'CUOTA III', valorCuota: 20 }
          ];
        }
        const totalCtas = cuotasData.reduce((sum, c) => sum + c.valorCuota, 0);
        const totalFinal = valorMatricula + totalCtas;
        setCuotas(cuotasData);
        setTotalCuotas(totalCtas);
        setMontoTotal(totalFinal);
      }
    }
  }, [selectedFormacion, formaciones]);

  // buscar
  useEffect(() => {
    const q = searchText.trim().toLowerCase();
    if (!q) {
      setMostradas(items);
      return;
    }
    setMostradas(items.filter(i => {
      const ced = (i.idPersona_detail?.cedula ?? '').toString().toLowerCase();
      const form = (i.idFormacion_detail?.nombreFormacion ?? '').toString().toLowerCase();
      const coh = (i.idCohorte_detail?.nombreCohorte ?? '').toString().toLowerCase();
      const estado = (i.estadoPago ?? '').toString().toLowerCase();
      return ced.includes(q) || form.includes(q) || coh.includes(q) || estado.includes(q);
    }));
  }, [searchText, items]);

  const openDetail = (item: any) => {
    setSelected(item);
    setDetailModalVisible(true);
  };

  const validateCreateForm = () => {
    const errs: Record<string, string> = {};
    if (selectedTipoFormacion === undefined) errs.tipoFormacion = 'Seleccione un tipo de formación';
    if (selectedFormacion === undefined) errs.formacion = 'Seleccione una formación';
    if (selectedCohorte === undefined) errs.cohorte = 'Seleccione una cohorte';
    if (!user) errs.usuario = 'No se pudo obtener la información del usuario. Por favor, cierre sesión y vuelva a ingresar.';
    setFormErrors(errs);
    return Object.keys(errs).length === 0;
  };

  const handleCreateInscripcion = async () => {
    if (!validateCreateForm()) {
      Alert.alert('Formulario inválido', 'Corrige los errores antes de continuar.');
      return;
    }
    if (!user?.idPersona) {
      Alert.alert('Error', 'No se pudo identificar su usuario. Por favor, cierre sesión y vuelva a ingresar.');
      return;
    }
    setCreating(true);
    try {
      const payload = {
        idPersona: user.idPersona,
        idTF: selectedTipoFormacion,
        idFormacion: selectedFormacion,
        idCohorte: selectedCohorte,
        montoTotal,
        montoPagado: 0,
        estadoPago: 'PENDIENTE',
        fechaInscripcion: new Date().toISOString().slice(0, 19).replace('T', ' ')
      };
      const res = await api.post('/api/inscripcion/', payload);
      if (res.status === 201 || res.status === 200) {
        try {
          const notaResponse = await api.post('/api/nota-cobro/create/', {
            idInscripcion: res.data.idInscripcion
          });
          if (notaResponse.data.success) {
            navigation.navigate('pago', {
              notaData: notaResponse.data.data,
              inscripcionId: res.data.idInscripcion
            });
            Alert.alert('Éxito', 'Inscripción y nota de cobro creadas correctamente. Proceda al pago.');
          } else {
            throw new Error(notaResponse.data.message);
          }
        } catch (notaError) {
          Alert.alert('Atención', 'Inscripción creada pero hubo un error al generar la nota de cobro. Contacte al administrador.');
        }
        setFormModalVisible(false);
        resetForm();
        await fetchInscripciones();
      }
    } catch (err: any) {
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
        setCreating(false);
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
      {/* HEADER */}
      <View style={[styles.header, isSmallScreen && styles.headerSmall]}>
        <View style={styles.headerTitleContainer}>
          <Text style={[styles.title, isSmallScreen && styles.titleSmall]}>Mis Inscripciones</Text>
          {user?.cedula && (
            <Text style={[styles.userCedula, isSmallScreen && styles.userCedulaSmall]}>
              Cédula: {user.cedula}
            </Text>
          )}
        </View>
        <TouchableOpacity
          style={[styles.addButton, isSmallScreen && styles.addButtonSmall]}
          onPress={() => setFormModalVisible(true)}
        >
          <Icon name="plus" size={isSmallScreen ? 18 : 22} color="#fff" />
          <Text style={[styles.addButtonText, isSmallScreen && styles.addButtonTextSmall]}>Nueva</Text>
        </TouchableOpacity>
      </View>

      {/* SEARCH */}
      <View style={[styles.searchContainer, isSmallScreen && styles.searchContainerSmall]}>
        <View style={[styles.searchWrapper, isSmallScreen && styles.searchWrapperSmall]}>
          <Icon name="magnify" size={isSmallScreen ? 16 : 18} color="#666" />
          <TextInput
            placeholder="Buscar formación, cohorte..."
            value={searchText}
            onChangeText={setSearchText}
            style={[styles.searchInput, isSmallScreen && styles.searchInputSmall]}
            placeholderTextColor="#999"
            returnKeyType="search"
          />
          {searchText.length > 0 && (
            <TouchableOpacity onPress={() => setSearchText('')}>
              <Icon name="close-circle" size={isSmallScreen ? 16 : 18} color="#999" />
            </TouchableOpacity>
          )}
        </View>
      </View>

      {/* COUNT */}
      <View style={[styles.counterContainer, isSmallScreen && styles.counterContainerSmall]}>
        <Text style={[styles.counterText, isSmallScreen && styles.counterTextSmall]}>
          {mostradas.length} de {items.length} inscripciones
        </Text>
      </View>

      {/* LIST */}
      <FlatList
        data={mostradas}
        keyExtractor={(i) => String(i.idInscripcion ?? i.id ?? Math.random())}
        renderItem={({ item }) => {
          const status = deriveStatus(item);
          return (
            <TouchableOpacity
              style={[styles.card, isSmallScreen && styles.cardSmall]}
              onPress={() => openDetail(item)}
            >
              <View style={styles.cardHeader}>
                <View style={[styles.cardTitleContainer, isSmallScreen && styles.cardTitleContainerSmall]}>
                  <Text style={[styles.cardTitle, isSmallScreen && styles.cardTitleSmall]} numberOfLines={2}>
                    {item.idFormacion_detail?.nombreFormacion ?? '—'}
                  </Text>
                  <View style={[styles.badge, statusColor(status), isSmallScreen && styles.badgeSmall]}>
                    <Text style={[styles.badgeText, isSmallScreen && styles.badgeTextSmall]}>{status}</Text>
                  </View>
                </View>
              </View>

              <View style={[styles.cardContent, isSmallScreen && styles.cardContentSmall]}>
                <View style={[styles.detailRow, isSmallScreen && styles.detailRowSmall]}>
                  <View style={styles.detailItem}>
                    <Icon name="domain" size={isSmallScreen ? 12 : 14} color="#666" />
                    <Text style={[styles.detailText, isSmallScreen && styles.detailTextSmall]}>
                      {item.idCohorte_detail?.nombreCohorte ?? '—'}
                    </Text>
                  </View>
                  <View style={styles.detailItem}>
                    <Icon name="calendar" size={isSmallScreen ? 12 : 14} color="#666" />
                    <Text style={[styles.detailText, isSmallScreen && styles.detailTextSmall]}>
                      {item.fechaInscripcion ? new Date(item.fechaInscripcion).toLocaleDateString() : '—'}
                    </Text>
                  </View>
                </View>

                <View style={[styles.detailRow, isSmallScreen && styles.detailRowSmall]}>
                  <View style={styles.detailItem}>
                    <Icon name="cash" size={isSmallScreen ? 12 : 14} color="#666" />
                    <Text style={[styles.detailText, isSmallScreen && styles.detailTextSmall]}>
                      Total: {fmtMoney(item.montoTotal)}
                    </Text>
                  </View>
                  <View style={styles.detailItem}>
                    <Icon name="cash-check" size={isSmallScreen ? 12 : 14} color="#666" />
                    <Text style={[styles.detailText, isSmallScreen && styles.detailTextSmall]}>
                      Pagado: {fmtMoney(item.montoPagado)}
                    </Text>
                  </View>
                </View>
              </View>

              <View style={[styles.cardFooter, isSmallScreen && styles.cardFooterSmall]}>
                <Text style={[styles.cardButtonText, isSmallScreen && styles.cardButtonTextSmall]}>
                  Tocar para ver detalles
                </Text>
                <Icon name="chevron-right" size={isSmallScreen ? 16 : 18} color="#4f8cff" />
              </View>
            </TouchableOpacity>
          );
        }}
        contentContainerStyle={[styles.listContent, isSmallScreen && styles.listContentSmall]}
        ListEmptyComponent={
          <View style={styles.emptyState}>
            <Icon name="clipboard-text-outline" size={isSmallScreen ? 40 : 50} color="#ccc" />
            <Text style={[styles.emptyText, isSmallScreen && styles.emptyTextSmall]}>
              {loading ? 'Cargando...' : 'No tienes inscripciones registradas'}
            </Text>
            <TouchableOpacity
              style={[styles.addButton, isSmallScreen && styles.addButtonSmall, styles.emptyButton]}
              onPress={() => setFormModalVisible(true)}
            >
              <Icon name="plus" size={isSmallScreen ? 16 : 18} color="#fff" />
              <Text style={[styles.addButtonText, isSmallScreen && styles.addButtonTextSmall]}>
                Crear primera inscripción
              </Text>
            </TouchableOpacity>
          </View>
        }
      />

      {/* DETAIL MODAL */}
      <Modal
        isVisible={detailModalVisible}
        onBackdropPress={() => setDetailModalVisible(false)}
        style={[styles.modal, isSmallScreen && styles.modalSmall]}
        avoidKeyboard
      >
        <View style={[
          styles.modalContent,
          isSmallScreen && styles.modalContentSmall,
          { maxHeight: Math.min(height * 0.85, 720), width: isLargeScreen ? '150%' : undefined }
        ]}>
          <View style={[styles.modalHeader, isSmallScreen && styles.modalHeaderSmall]}>
            <Text style={[styles.modalTitle, isSmallScreen && styles.modalTitleSmall]}>
              Detalles de Inscripción
            </Text>
            <TouchableOpacity
              style={[styles.closeButton, isSmallScreen && styles.closeButtonSmall]}
              onPress={() => setDetailModalVisible(false)}
            >
              <Icon name="close" size={isSmallScreen ? 20 : 22} color="#666" />
            </TouchableOpacity>
          </View>

          <ScrollView
            style={styles.modalBody}
            contentContainerStyle={{ paddingBottom: 12 }}
            showsVerticalScrollIndicator
          >
            {selected && [
              ['Formación', selected.idFormacion_detail?.nombreFormacion ?? '—'],
              ['Cohorte', selected.idCohorte_detail?.nombreCohorte ?? '—'],
              ['Cédula', selected.idPersona_detail?.cedula ?? '—'],
              ['Estado pago', deriveStatus(selected)],
              ['Monto total', fmtMoney(selected.montoTotal)],
              ['Monto pagado', fmtMoney(selected.montoPagado)],
              ['Saldo pendiente', fmtMoney(selected.saldoPendiente)],
              ['Fecha inscripción', selected.fechaInscripcion ? new Date(selected.fechaInscripcion).toLocaleString() : '—'],
            ].map(([lbl, val]) => (
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

      {/* FORM MODAL */}
      <Modal
        isVisible={formModalVisible}
        onBackdropPress={() => !creating && setFormModalVisible(false)}
        style={[styles.modal, styles.formModal, isSmallScreen && styles.modalSmall]}
        avoidKeyboard
      >
        <KeyboardAvoidingView
          behavior={Platform.OS === 'ios' ? 'padding' : undefined}
          style={[styles.keyboardAvoid, { minHeight: Math.min(height * 0.9, 900) }]}
        >
          <View style={[
            styles.formModalContent,
            isSmallScreen ? styles.formModalContentSmall : {},
            {
              maxHeight: Math.min(height * 0.95, 1000),
              width: isLargeScreen ? Math.min(720, width * 0.8) : undefined,
            }
          ]}>
            <View style={[styles.modalHeader, isSmallScreen && styles.modalHeaderSmall]}>
              <Text style={[styles.modalTitle, isSmallScreen && styles.modalTitleSmall]}>
                Nueva Inscripción
              </Text>
              <TouchableOpacity
                style={[styles.closeButton, isSmallScreen && styles.closeButtonSmall]}
                onPress={() => !creating && setFormModalVisible(false)}
                disabled={creating}
              >
                <Icon name="close" size={isSmallScreen ? 20 : 22} color="#666" />
              </TouchableOpacity>
            </View>

            <ScrollView
              style={styles.formBody}
              showsVerticalScrollIndicator
              keyboardShouldPersistTaps="handled"
              contentContainerStyle={[styles.formContent, isSmallScreen && styles.formContentSmall, { paddingBottom: 24 }]}
            >
              {/* Información Personal */}
              <View style={styles.formSection}>
                <View style={styles.sectionHeader}>
                  <Icon name="account" size={isSmallScreen ? 18 : 20} color="#4f8cff" />
                  <Text style={[styles.sectionTitle, isSmallScreen && styles.sectionTitleSmall]}>Información Personal</Text>
                </View>

                <View style={[styles.fieldContainer, isSmallScreen && styles.fieldContainerSmall]}>
                  <Text style={[styles.label, isSmallScreen && styles.labelSmall]}>Cédula</Text>
                  <View style={[styles.cedulaFijaContainer, isSmallScreen && styles.cedulaFijaContainerSmall]}>
                    <Text style={[styles.cedulaFijaText, isSmallScreen && styles.cedulaFijaTextSmall]}>
                      {user?.cedula || 'No disponible'}
                    </Text>
                  </View>
                  <Text style={[styles.helpText, isSmallScreen && styles.helpTextSmall]}>
                    {user?.nombres && user?.apellidos ? `${user.nombres} ${user.apellidos}` : 'Usuario actual'}
                  </Text>
                </View>
              </View>

              {/* Información Académica */}
              <View style={styles.formSection}>
                <View style={styles.sectionHeader}>
                  <Icon name="school" size={isSmallScreen ? 18 : 20} color="#4f8cff" />
                  <Text style={[styles.sectionTitle, isSmallScreen && styles.sectionTitleSmall]}>Información Académica</Text>
                </View>

                <View style={[styles.fieldContainer, isSmallScreen && styles.fieldContainerSmall]}>
                  <Text style={[styles.label, isSmallScreen && styles.labelSmall]}>Tipo de Formación *</Text>
                  <View style={[styles.pickerContainer, isSmallScreen && styles.pickerContainerSmall]}>
                    <Picker
                      selectedValue={selectedTipoFormacion}
                      onValueChange={(itemValue) => setSelectedTipoFormacion(itemValue)}
                      style={[styles.picker, isSmallScreen && styles.pickerSmall, { width: '100%' }]}
                      dropdownIconColor="#666"
                      mode="dropdown"
                    >
                      <Picker.Item label="Seleccione tipo..." value={undefined} />
                      {tiposFormacion.map(tf => (
                        <Picker.Item key={tf.idTF} label={tf.nombreTipoFormacion} value={tf.idTF} />
                      ))}
                    </Picker>
                  </View>
                  {formErrors.tipoFormacion && <Text style={[styles.errorText, isSmallScreen && styles.errorTextSmall]}>{formErrors.tipoFormacion}</Text>}
                </View>

                <View style={[styles.fieldContainer, isSmallScreen && styles.fieldContainerSmall]}>
                  <Text style={[styles.label, isSmallScreen && styles.labelSmall]}>Formación *</Text>
                  <View style={[styles.pickerContainer, isSmallScreen && styles.pickerContainerSmall]}>
                    <Picker
                      selectedValue={selectedFormacion}
                      onValueChange={(itemValue) => setSelectedFormacion(itemValue)}
                      style={[styles.picker, isSmallScreen && styles.pickerSmall, { width: '100%' }]}
                      enabled={formacionesFiltradas.length > 0}
                      dropdownIconColor="#666"
                      mode="dropdown"
                    >
                      <Picker.Item label={formacionesFiltradas.length === 0 ? "Seleccione tipo primero" : "Seleccione formación..."} value={undefined} />
                      {formacionesFiltradas.map(f => (
                        <Picker.Item key={f.idFormacion} label={`${f.nombreFormacion} - $${f.valorInscripcion}`} value={f.idFormacion} />
                      ))}
                    </Picker>
                  </View>
                  {formErrors.formacion && <Text style={[styles.errorText, isSmallScreen && styles.errorTextSmall]}>{formErrors.formacion}</Text>}
                </View>

                <View style={[styles.fieldContainer, isSmallScreen && styles.fieldContainerSmall]}>
                  <Text style={[styles.label, isSmallScreen && styles.labelSmall]}>Cohorte *</Text>
                  <View style={[styles.pickerContainer, isSmallScreen && styles.pickerContainerSmall]}>
                    <Picker
                      selectedValue={selectedCohorte}
                      onValueChange={(itemValue) => setSelectedCohorte(itemValue)}
                      style={[styles.picker, isSmallScreen && styles.pickerSmall, { width: '100%' }]}
                      dropdownIconColor="#666"
                      mode="dropdown"
                    >
                      <Picker.Item label="Seleccione cohorte..." value={undefined} />
                      {cohortes.map(c => (
                        <Picker.Item key={c.idCohorte} label={c.nombreCohorte} value={c.idCohorte} />
                      ))}
                    </Picker>
                  </View>
                  {formErrors.cohorte && <Text style={[styles.errorText, isSmallScreen && styles.errorTextSmall]}>{formErrors.cohorte}</Text>}
                </View>
              </View>

              {/* Resumen de costos */}
              <View style={styles.formSection}>
                <View style={styles.sectionHeader}>
                  <Icon name="cash" size={isSmallScreen ? 18 : 20} color="#4f8cff" />
                  <Text style={[styles.sectionTitle, isSmallScreen && styles.sectionTitleSmall]}>Resumen de Costos</Text>
                </View>

                <View style={[styles.costosContainer, isSmallScreen && styles.costosContainerSmall]}>
                  <View style={[styles.costoItem, isSmallScreen && styles.costoItemSmall]}>
                    <Text style={[styles.costoLabel, isSmallScreen && styles.costoLabelSmall]}>Inscripción:</Text>
                    <Text style={[styles.costoValue, isSmallScreen && styles.costoValueSmall]}>{fmtMoney(valorInscripcion)}</Text>
                  </View>

                  {cuotas.length > 0 ? (
                    <>
                      {cuotas.map((cuota, index) => (
                        <View key={index} style={[styles.costoItem, isSmallScreen && styles.costoItemSmall]}>
                          <Text style={[styles.costoLabel, isSmallScreen && styles.costoLabelSmall]}>{cuota.nombreCuota}:</Text>
                          <Text style={[styles.costoValue, isSmallScreen && styles.costoValueSmall]}>{fmtMoney(cuota.valorCuota)}</Text>
                        </View>
                      ))}
                      <View style={[styles.costoItem, styles.costoTotal, isSmallScreen && styles.costoItemSmall]}>
                        <Text style={[styles.costoLabel, isSmallScreen && styles.costoLabelSmall]}>Total Cuotas:</Text>
                        <Text style={[styles.costoValue, isSmallScreen && styles.costoValueSmall]}>{fmtMoney(totalCuotas)}</Text>
                      </View>
                    </>
                  ) : (
                    <View style={[styles.costoItem, isSmallScreen && styles.costoItemSmall]}>
                      <Text style={[styles.costoLabel, styles.noCuotas, isSmallScreen && styles.costoLabelSmall]}>No hay cuotas configuradas</Text>
                    </View>
                  )}

                  <View style={[styles.costoItem, styles.costoGrandTotal, isSmallScreen && styles.costoItemSmall]}>
                    <Text style={[styles.costoLabel, styles.costoGrandTotalLabel, isSmallScreen && styles.costoLabelSmall]}>TOTAL A PAGAR:</Text>
                    <Text style={[styles.costoValue, styles.costoGrandTotalValue, isSmallScreen && styles.costoValueSmall]}>{fmtMoney(montoTotal)}</Text>
                  </View>
                </View>
              </View>

              {/* Fecha */}
              <View style={styles.formSection}>
                <View style={styles.sectionHeader}>
                  <Icon name="calendar-clock" size={isSmallScreen ? 18 : 20} color="#4f8cff" />
                  <Text style={[styles.sectionTitle, isSmallScreen && styles.sectionTitleSmall]}>Información de Registro</Text>
                </View>

                <View style={[styles.fieldContainer, isSmallScreen && styles.fieldContainerSmall]}>
                  <View style={[styles.fechaContainer, isSmallScreen && styles.fechaContainerSmall]}>
                    <Text style={[styles.fechaText, isSmallScreen && styles.fechaTextSmall]}>{fechaInscripcion}</Text>
                  </View>
                  <Text style={[styles.helpText, isSmallScreen && styles.helpTextSmall]}>Fecha y hora automáticas</Text>
                </View>
              </View>
            </ScrollView>

            <View style={[styles.formFooter, isSmallScreen && styles.formFooterSmall]}>
              <TouchableOpacity
                style={[styles.formButton, styles.cancelButton, isSmallScreen && styles.formButtonSmall]}
                onPress={() => setFormModalVisible(false)}
                disabled={creating}
              >
                <Text style={[styles.cancelButtonText, isSmallScreen && styles.cancelButtonTextSmall]}>Cancelar</Text>
              </TouchableOpacity>

              <TouchableOpacity
                style={[styles.formButton, styles.submitButton, isSmallScreen && styles.formButtonSmall]}
                onPress={handleCreateInscripcion}
                disabled={creating}
              >
                {creating ? (
                  <ActivityIndicator color="#fff" size="small" />
                ) : (
                  <>
                    <Icon name="check" size={isSmallScreen ? 16 : 18} color="#fff" />
                    <Text style={[styles.submitButtonText, isSmallScreen && styles.submitButtonTextSmall]}>Crear Inscripción</Text>
                  </>
                )}
              </TouchableOpacity>
            </View>
          </View>
        </KeyboardAvoidingView>
      </Modal>
    </View>
  );
};

// ESTILOS COMPLETOS
const styles = StyleSheet.create({
  center: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: '#f5f7fa',
    padding: 20,
  },
  container: {
    flex: 1,
    backgroundColor: '#f5f7fa',
  },

  // Header
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    paddingHorizontal: 16,
    paddingTop: 12,
    paddingBottom: 8,
    backgroundColor: '#fff',
    borderBottomWidth: 1,
    borderBottomColor: '#e1e5e9',
  },
  headerSmall: {
    paddingHorizontal: 12,
    paddingTop: 10,
    paddingBottom: 6,
  },
  headerTitleContainer: {
    flex: 1,
  },
  title: {
    fontSize: 20,
    fontWeight: '700',
    color: '#1a365d',
    marginBottom: 2,
  },
  titleSmall: {
    fontSize: 18,
  },
  userCedula: {
    fontSize: 12,
    color: '#666',
    fontWeight: '500',
  },
  userCedulaSmall: {
    fontSize: 11,
  },
  addButton: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#4f8cff',
    paddingHorizontal: 12,
    paddingVertical: 8,
    borderRadius: 8,
    gap: 6,
    marginLeft: 8,
  },
  addButtonSmall: {
    paddingHorizontal: 10,
    paddingVertical: 6,
    gap: 4,
    borderRadius: 6,
  },
  addButtonText: {
    color: '#fff',
    fontWeight: '600',
    fontSize: 14,
  },
  addButtonTextSmall: {
    fontSize: 12,
  },

  // Search
  searchContainer: {
    padding: 12,
    backgroundColor: '#fff',
    borderBottomWidth: 1,
    borderBottomColor: '#e1e5e9',
  },
  searchContainerSmall: {
    padding: 10,
  },
  searchWrapper: {
    flexDirection: 'row',
    backgroundColor: '#f8f9fa',
    borderRadius: 10,
    alignItems: 'center',
    paddingHorizontal: 12,
    height: 40,
    borderWidth: 1,
    borderColor: '#e1e5e9',
  },
  searchWrapperSmall: {
    paddingHorizontal: 10,
    height: 38,
    borderRadius: 8,
  },
  searchInput: {
    flex: 1,
    fontSize: 14,
    marginLeft: 8,
    color: '#333',
    paddingVertical: 0,
  },
  searchInputSmall: {
    fontSize: 13,
    marginLeft: 6,
  },

  // Counter
  counterContainer: {
    paddingHorizontal: 16,
    paddingVertical: 8,
    backgroundColor: '#f8f9fa',
  },
  counterContainerSmall: {
    paddingHorizontal: 12,
    paddingVertical: 6,
  },
  counterText: {
    fontSize: 12,
    color: '#666',
    fontWeight: '500',
  },
  counterTextSmall: {
    fontSize: 11,
  },

  // List
  listContent: {
    padding: 12,
    paddingTop: 8,
    paddingBottom: 24,
  },
  listContentSmall: {
    padding: 10,
    paddingTop: 6,
  },

  // Cards
  card: {
    backgroundColor: '#fff',
    borderRadius: 12,
    padding: 14,
    marginBottom: 10,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.1,
    shadowRadius: 2,
    elevation: 2,
    borderWidth: 1,
    borderColor: '#f1f3f4',
  },
  cardSmall: {
    padding: 12,
    borderRadius: 10,
    marginBottom: 8,
  },
  cardHeader: {
    marginBottom: 10,
  },
  cardTitleContainer: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    marginBottom: 6,
  },
  cardTitleContainerSmall: {
    marginBottom: 4,
    flexDirection: 'column',
    gap: 6,
  },
  cardTitle: {
    fontSize: 16,
    fontWeight: '600',
    color: '#1a365d',
    flex: 1,
    marginRight: 8,
  },
  cardTitleSmall: {
    fontSize: 15,
    marginRight: 0,
  },
  cardContent: {
    marginBottom: 10,
  },
  cardContentSmall: {
    marginBottom: 8,
  },
  cardFooter: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingTop: 10,
    borderTopWidth: 1,
    borderTopColor: '#f1f3f4',
  },
  cardFooterSmall: {
    paddingTop: 8,
  },
  detailRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginBottom: 8,
  },
  detailRowSmall: {
    marginBottom: 6,
    flexDirection: 'column',
    gap: 6,
  },
  detailItem: {
    flexDirection: 'row',
    alignItems: 'center',
    flex: 1,
  },
  detailText: {
    marginLeft: 6,
    fontSize: 13,
    color: '#555',
    fontWeight: '500',
  },
  detailTextSmall: {
    fontSize: 12,
    marginLeft: 4,
  },
  cardButtonText: {
    color: '#4f8cff',
    fontWeight: '500',
    fontSize: 12,
  },
  cardButtonTextSmall: {
    fontSize: 11,
  },

  // Badge
  badge: {
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 12,
    minWidth: 60,
    alignItems: 'center',
  },
  badgeSmall: {
    paddingHorizontal: 6,
    paddingVertical: 3,
    minWidth: 50,
    borderRadius: 10,
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
    fontSize: 10,
    fontWeight: '700',
    textAlign: 'center',
  },
  badgeTextSmall: {
    fontSize: 9,
  },

  // Empty
  emptyState: {
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: 40,
    paddingHorizontal: 20,
  },
  emptyText: {
    marginTop: 12,
    textAlign: 'center',
    color: '#999',
    fontStyle: 'italic',
    fontSize: 14,
    marginBottom: 16,
  },
  emptyTextSmall: {
    fontSize: 13,
    marginTop: 10,
  },
  emptyButton: {
    alignSelf: 'center',
  },

  // Error
  errorText: {
    color: '#e53e3e',
    fontSize: 14,
    marginTop: 4,
    fontWeight: '500',
  },
  errorTextSmall: {
    fontSize: 12,
  },

  // Modal
  modal: {
    margin: 0,
    justifyContent: 'center',
    alignItems: 'center',
  },
  modalSmall: {
    paddingHorizontal: 8,
  },
  formModal: {
    margin: 0,
  },
  keyboardAvoid: {
    width: '100%',
    alignItems: 'center',
    flex: 1,
  },
  modalContent: {
    backgroundColor: '#fff',
    borderRadius: 16,
    width: '90%',
    maxWidth: 500,
    maxHeight: '80%',
    overflow: 'hidden',
  },
  modalContentSmall: {
    width: '95%',
    maxHeight: '85%',
    borderRadius: 14,
  },
  formModalContent: {
    backgroundColor: '#fff',
    borderRadius: 16,
    width: '90%',
    maxWidth: 500,
    maxHeight: '90%',
    overflow: 'hidden',
  },
  formModalContentSmall: {
    width: '95%',
    maxHeight: '95%',
    borderRadius: 14,
  },
  modalHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: 16,
    paddingBottom: 12,
    borderBottomWidth: 1,
    borderBottomColor: '#e1e5e9',
  },
  modalHeaderSmall: {
    padding: 14,
    paddingBottom: 10,
  },
  modalTitle: {
    fontSize: 18,
    fontWeight: '700',
    color: '#1a365d',
    flex: 1,
  },
  modalTitleSmall: {
    fontSize: 16,
  },
  closeButton: {
    padding: 4,
  },
  closeButtonSmall: {
    padding: 2,
  },
  modalBody: {
    flex: 1,
  },
  formBody: {
    flex: 1,
  },
  formContent: {
    paddingBottom: 16,
  },
  formContentSmall: {
    paddingBottom: 14,
  },
  modalFooter: {
    padding: 16,
    paddingTop: 12,
    borderTopWidth: 1,
    borderTopColor: '#e1e5e9',
  },
  modalFooterSmall: {
    padding: 14,
    paddingTop: 10,
  },
  detailRowModal: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    paddingVertical: 10,
    paddingHorizontal: 16,
    borderBottomWidth: 1,
    borderBottomColor: '#f8f9fa',
  },
  detailRowModalSmall: {
    paddingVertical: 8,
    paddingHorizontal: 14,
    flexDirection: 'column',
    gap: 2,
  },
  detailLabel: {
    fontWeight: '600',
    fontSize: 14,
    color: '#4a5568',
    flex: 1,
  },
  detailLabelSmall: {
    fontSize: 13,
  },
  detailValue: {
    flex: 1,
    fontSize: 14,
    color: '#2d3748',
    textAlign: 'right',
    fontWeight: '500',
  },
  detailValueSmall: {
    fontSize: 13,
    textAlign: 'left',
  },
  modalButton: {
    backgroundColor: '#4f8cff',
    paddingVertical: 12,
    borderRadius: 10,
    alignItems: 'center',
  },
  modalButtonSmall: {
    paddingVertical: 10,
    borderRadius: 8,
  },
  modalButtonText: {
    color: '#fff',
    fontWeight: '600',
    fontSize: 14,
  },
  modalButtonTextSmall: {
    fontSize: 13,
  },

  // Form
  formSection: {
    marginBottom: 8,
  },
  sectionHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    marginBottom: 12,
    paddingHorizontal: 16,
  },
  sectionTitle: {
    fontSize: 16,
    fontWeight: '700',
    color: '#2d3748',
  },
  sectionTitleSmall: {
    fontSize: 15,
  },
  fieldContainer: {
    marginBottom: 14,
    paddingHorizontal: 16,
  },
  fieldContainerSmall: {
    marginBottom: 12,
    paddingHorizontal: 14,
  },
  label: {
    fontWeight: '600',
    color: '#4a5568',
    marginBottom: 6,
    fontSize: 14,
  },
  labelSmall: {
    fontSize: 13,
    marginBottom: 4,
  },
  cedulaFijaContainer: {
    backgroundColor: '#f8f9fa',
    borderRadius: 10,
    paddingHorizontal: 12,
    paddingVertical: 10,
    borderWidth: 1,
    borderColor: '#e1e5e9',
  },
  cedulaFijaContainerSmall: {
    paddingHorizontal: 10,
    paddingVertical: 8,
    borderRadius: 8,
  },
  cedulaFijaText: {
    fontSize: 14,
    fontWeight: '600',
    color: '#4a5568',
  },
  cedulaFijaTextSmall: {
    fontSize: 13,
  },
  fechaContainer: {
    backgroundColor: '#f0fff4',
    borderRadius: 10,
    paddingHorizontal: 12,
    paddingVertical: 10,
    borderWidth: 1,
    borderColor: '#9ae6b4',
  },
  fechaContainerSmall: {
    paddingHorizontal: 10,
    paddingVertical: 8,
    borderRadius: 8,
  },
  fechaText: {
    fontSize: 14,
    fontWeight: '600',
    color: '#22543d',
  },
  fechaTextSmall: {
    fontSize: 13,
  },
  helpText: {
    fontSize: 11,
    color: '#6c757d',
    marginTop: 4,
    fontStyle: 'italic',
  },
  helpTextSmall: {
    fontSize: 10,
  },
  pickerContainer: {
    borderWidth: 1,
    borderColor: '#e1e5e9',
    borderRadius: 10,
    backgroundColor: '#fff',
    overflow: 'hidden',
  },
  pickerContainerSmall: {
    borderRadius: 8,
  },
  picker: {
    height: 46,
    width: '100%',
  },
  pickerSmall: {
    height: 42,
  },

  // Costos
  costosContainer: {
    backgroundColor: '#f8f9fa',
    borderRadius: 10,
    padding: 12,
    marginHorizontal: 16,
    borderWidth: 1,
    borderColor: '#e1e5e9',
  },
  costosContainerSmall: {
    padding: 10,
    marginHorizontal: 14,
    borderRadius: 8,
  },
  costoItem: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: 6,
    borderBottomWidth: 1,
    borderBottomColor: '#e9ecef',
  },
  costoItemSmall: {
    paddingVertical: 5,
  },
  costoTotal: {
    borderBottomWidth: 2,
    borderBottomColor: '#dee2e6',
    paddingTop: 8,
    marginTop: 4,
  },
  costoGrandTotal: {
    backgroundColor: '#d4edda',
    borderRadius: 6,
    paddingHorizontal: 8,
    paddingVertical: 8,
    marginTop: 8,
    borderBottomWidth: 0,
  },
  costoLabel: {
    fontSize: 14,
    color: '#4a5568',
    fontWeight: '500',
  },
  costoLabelSmall: {
    fontSize: 13,
  },
  costoGrandTotalLabel: {
    fontWeight: '700',
    color: '#155724',
  },
  costoValue: {
    fontSize: 14,
    color: '#4a5568',
    fontWeight: '600',
  },
  costoValueSmall: {
    fontSize: 13,
  },
  costoGrandTotalValue: {
    fontWeight: '700',
    color: '#155724',
    fontSize: 16,
  },
  noCuotas: {
    color: '#999',
    fontStyle: 'italic',
    textAlign: 'center',
    flex: 1,
  },

  // Form footer
  formFooter: {
    flexDirection: 'row',
    padding: 16,
    paddingTop: 12,
    borderTopWidth: 1,
    borderTopColor: '#e1e5e9',
    gap: 10,
  },
  formFooterSmall: {
    padding: 14,
    paddingTop: 10,
    gap: 8,
  },
  formButton: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: 12,
    borderRadius: 10,
    gap: 6,
  },
  formButtonSmall: {
    paddingVertical: 10,
    borderRadius: 8,
    gap: 4,
  },
  cancelButton: {
    backgroundColor: '#fff',
    borderWidth: 1,
    borderColor: '#e1e5e9',
  },
  cancelButtonText: {
    color: '#4a5568',
    fontWeight: '600',
    fontSize: 14,
  },
  cancelButtonTextSmall: {
    fontSize: 13,
  },
  submitButton: {
    backgroundColor: '#4f8cff',
  },
  submitButtonText: {
    color: '#fff',
    fontWeight: '600',
    fontSize: 14,
  },
  submitButtonTextSmall: {
    fontSize: 13,
  },
});

export default InscripcionesScreen;
