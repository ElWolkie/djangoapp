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

  // Form fields - CAMBIO: usar undefined en lugar de null para los Pickers
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
            // CORRECCIÓN: Asegurar que idTF sea NUMBER
            const rawIdTF = item.idTF || item.tipo_formacion || item.tipoFormacion || item.tipo_formacion_id || item.idTF_id || 0;
            const idTF = Number(rawIdTF); // FORZAR conversión a número

            console.log(`🎓 Formación: ${item.nombreFormacion || item.nombre}, idTF extraído: ${rawIdTF} -> ${idTF} (${typeof idTF})`);
            
            return {
              idFormacion: Number(item.idFormacion || item.id || 0),
              nombreFormacion: item.nombreFormacion || item.nombre || 'Sin nombre',
              idTF: idTF, // Ahora siempre será número
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

  // DEBUG: Función para ver cuotas específicas
  const debugCuotas = async (formacionId: number) => {
    try {
      console.log('🔍 DEBUG: Obteniendo datos completos de formación...');
      const response = await api.get(`/api/formaciones/${formacionId}/`);
      console.log('📦 Datos COMPLETOS de la formación:', response.data);
      console.log('📋 cuotas_json específico:', response.data.cuotas_json);
      
      if (response.data.cuotas_json) {
        try {
          const parsed = JSON.parse(response.data.cuotas_json);
          console.log('✅ cuotas_json parseado:', parsed);
        } catch (e) {
          console.error('❌ Error parseando cuotas_json:', e);
        }
      }
    } catch (error) {
      console.error('❌ Error en debugCuotas:', error);
    }
  };

  // Función para debuggear errores de validación 400
  const debugError400 = async (errorData: any) => {
    console.log('🔍 DEBUG ERROR 400 - Detalles completos:');
    console.log('Status:', errorData.status);
    console.log('Data:', errorData.data);
    console.log('Errors:', errorData.data);
    
    if (errorData.data) {
      // Si es un objeto con errores específicos
      if (typeof errorData.data === 'object') {
        Object.keys(errorData.data).forEach(key => {
          console.log(`❌ ${key}:`, errorData.data[key]);
        });
      }
    }
  };

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

  // Filtrar formaciones cuando cambia el tipo de formación - VERSIÓN CORREGIDA
  useEffect(() => {
    console.log('🔄 FILTRANDO FORMACIONES - INICIO');
    console.log('Tipo seleccionado:', selectedTipoFormacion, 'Tipo:', typeof selectedTipoFormacion);
    console.log('Total formaciones disponibles:', formaciones.length);
    console.log('Formaciones disponibles:', formaciones.map(f => ({
      id: f.idFormacion, 
      nombre: f.nombreFormacion, 
      idTF: f.idTF,
      tipoIdTF: typeof f.idTF
    })));

    // CAMBIO: Usar undefined en lugar de null
    if (selectedTipoFormacion !== undefined && formaciones.length > 0) {
      // CONVERTIR AMBOS A NUMBER para comparación correcta
      const selectedTipoNum = Number(selectedTipoFormacion);
      
      const filtradas = formaciones.filter(f => {
        const formacionTipoNum = Number(f.idTF);
        const match = formacionTipoNum === selectedTipoNum;
        console.log(`🔍 Formación "${f.nombreFormacion}": idTF=${f.idTF} (${typeof f.idTF}), selectedTipo=${selectedTipoFormacion} (${typeof selectedTipoFormacion}), match=${match}`);
        return match;
      });
      
      console.log('✅ FORMACIONES FILTRADAS:', filtradas.length);
      console.log('📋 Lista filtrada:', filtradas.map(f => ({id: f.idFormacion, nombre: f.nombreFormacion})));
      
      setFormacionesFiltradas(filtradas);
      setSelectedFormacion(undefined);
      
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

  // Función mejorada para obtener cuotas reales con manejo de tipos
  const fetchCuotasReales = async (formacionId: number): Promise<Cuota[]> => {
    try {
      console.log('💰 SOLICITANDO CUOTAS REALES para formación:', formacionId);
      const response = await api.get(`/api/formaciones/${formacionId}/cuotas/`);
      
      // VERIFICAR SI LA RESPUESTA ES HTML (ERROR)
      if (typeof response.data === 'string' && response.data.includes('<!DOCTYPE html>')) {
        console.error('❌ El servidor devolvió HTML en lugar de JSON');
        throw new Error('Error del servidor: respuesta en formato incorrecto');
      }
      
      console.log('💰 RESPUESTA CUOTAS REALES:', response.data);
      
      // Manejar diferentes estructuras de respuesta
      if (response.data.cuotas && Array.isArray(response.data.cuotas)) {
        return response.data.cuotas.map((cuota: any) => ({
          nombreCuota: cuota.nombreCuota,
          valorCuota: Number(cuota.valorCuota) || 0
        }));
      } else if (Array.isArray(response.data)) {
        // Si la respuesta es directamente un array
        return response.data.map((cuota: any) => ({
          nombreCuota: cuota.nombreCuota,
          valorCuota: Number(cuota.valorCuota) || 0
        }));
      }
      
      console.warn('⚠️ Estructura de cuotas no reconocida:', response.data);
      return [];
    } catch (error: any) { // Usar ': any' temporalmente para evitar problemas de tipo
      console.error('❌ Error obteniendo cuotas reales:', error);
      
      // Manejo específico de errores con verificación de tipo
      if (error && typeof error === 'object' && 'response' in error) {
        const axiosError = error as any;
        if (axiosError.response?.status === 500) {
          console.error('🚨 Error 500 del servidor - Verificar el endpoint backend');
        }
      }
      
      return [];
    }
  };

  // CALCULAR COSTOS CON CUOTAS REALES - VERSIÓN CORREGIDA
  // En tu useEffect de cálculo de costos, agrega esto temporalmente:
useEffect(() => {
  if (selectedFormacion !== undefined) {
    const formacion = formaciones.find(f => f.idFormacion === selectedFormacion);
    
    if (formacion) {
      const valorMatricula = Number(formacion.valorInscripcion) || 0;
      setValorInscripcion(valorMatricula);
      
      // ✅ SOLUCIÓN TEMPORAL: Datos hardcodeados por formación
      let cuotasData: Cuota[] = [];
      
      if (formacion.idFormacion === 3 && formacion.nombreFormacion.includes('BIOTECNOLOGIA')) {
        // Datos específicos para BIOTECNOLOGIA
        cuotasData = [
          { nombreCuota: 'CUOTA I', valorCuota: 15 },
          { nombreCuota: 'CUOTA II', valorCuota: 10 },
          { nombreCuota: 'CUOTA III', valorCuota: 20 }
        ];
        console.log('✅ Usando datos hardcodeados para BIOTECNOLOGIA');
      }
      // Agregar más formaciones según necesites
      
      const totalCtas = cuotasData.reduce((sum, cuota) => sum + cuota.valorCuota, 0);
      const totalFinal = valorMatricula + totalCtas;
      
      setCuotas(cuotasData);
      setTotalCuotas(totalCtas);
      setMontoTotal(totalFinal);
      
      console.log('💰 COSTOS CALCULADOS (con datos temporales):');
      console.log('Matrícula:', valorMatricula);
      console.log('Total cuotas:', totalCtas);
      console.log('Total general:', totalFinal);
    }
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

  const openDetail = (item: any) => {
  setSelected(item); // Esto debería ser el objeto completo de la inscripción
  setDetailModalVisible(true);
};

  // Función para verificar que los IDs existen - VERSIÓN MEJORADA
  const verificarIDs = (): boolean => {
    // CAMBIO: Usar undefined en lugar de null
    if (selectedTipoFormacion === undefined || selectedFormacion === undefined || selectedCohorte === undefined) {
      Alert.alert(
        'Error en selección',
        'Por favor, seleccione tipo de formación, formación y cohorte.'
      );
      return false;
    }

    const tipoId = Number(selectedTipoFormacion);
    const formacionId = Number(selectedFormacion);
    const cohorteId = Number(selectedCohorte);
    
    console.log('🔍 VERIFICACIÓN DE IDs (convertidos a número):');
    console.log('Tipo ID seleccionado:', tipoId);
    console.log('Formación ID seleccionado:', formacionId);
    console.log('Cohorte ID seleccionado:', cohorteId);

    const tipoExists = tiposFormacion.some(t => Number(t.idTF) === tipoId);
    const formacionExists = formaciones.some(f => Number(f.idFormacion) === formacionId);
    const cohorteExists = cohortes.some(c => Number(c.idCohorte) === cohorteId);
    
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
    // CAMBIO: Usar undefined en lugar de null
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

  // DEBUG MEJORADO: Función para ver cuotas específicas
  const debugCuotasCompleto = async (formacionId: number) => {
    try {
      console.log('🔍 DEBUG COMPLETO: Obteniendo datos de formación y cuotas...');
      
      // 1. Obtener datos de la formación
      const responseFormacion = await api.get(`/api/formaciones/${formacionId}/`);
      const formacionData = responseFormacion.data;
      
      console.log('📦 DATOS COMPLETOS DE LA FORMACIÓN:', formacionData);
      console.log('💰 Valor inscripción:', formacionData.valorInscripcion);
      console.log('📋 tieneCuotas:', formacionData.tieneCuotas);
      
      // 2. Probar endpoint de cuotas directamente
      console.log('🔍 Probando endpoint de cuotas directamente...');
      try {
        const responseCuotas = await api.get(`/api/formaciones/${formacionId}/cuotas/`);
        console.log('✅ Respuesta cuotas:', responseCuotas.data);
      } catch (error) {
        // CORRECCIÓN: Verificar el tipo del error
        console.error('❌ Error en endpoint de cuotas:', error);
        
        if (error && typeof error === 'object' && 'response' in error) {
          const axiosError = error as any;
          console.error('❌ Status:', axiosError.response?.status);
          console.error('❌ Data:', axiosError.response?.data);
        } else {
          console.error('❌ Error desconocido:', error);
        }
      }
      
    } catch (error) {
      console.error('❌ Error en debugCuotasCompleto:', error);
    }
  };


  // FUNCIÓN MEJORADA: Crear inscripción con payload corregido
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

    // CAMBIO: Usar valores por defecto ya que sabemos que no son undefined por la validación
    const idTF = Number(selectedTipoFormacion);
    const idFormacion = Number(selectedFormacion);
    const idCohorte = Number(selectedCohorte);

    if (isNaN(idTF) || isNaN(idFormacion) || isNaN(idCohorte)) {
      Alert.alert('Error', 'Hay datos inválidos en el formulario.');
      return;
    }

    setCreating(true);

    try {
      const ahora = new Date();
      const fechaFormateada = ahora.toISOString().replace('T', ' ').substring(0, 19);
      
      // PAYLOAD CORREGIDO según el error del backend
        const payload = {
        "idPersona": userInfo?.idPersona,  // Cambiado de idPersona_id a idPersona
        "idTF": selectedTipoFormacion,
        "idFormacion": selectedFormacion,
        "idCohorte": selectedCohorte,
        "montoTotal": montoTotal,
        "montoPagado": 0,
        "estadoPago": "PENDIENTE",
        "fechaInscripcion": new Date().toISOString().slice(0, 19).replace('T', ' ')
      };

        console.log("📤 Enviando payload CORREGIDO:", payload);

      console.log('📤 Enviando payload SIMPLIFICADO:', JSON.stringify(payload, null, 2));

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
      
      // Manejo específico de errores 400
      if (err.response?.status === 400) {
        await debugError400(err.response);
        
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
      
      // Manejo de error 500
      if (err.response?.status === 500) {
        Alert.alert(
          'Error del Servidor', 
          'Error interno del servidor. Por favor, contacte al administrador del sistema.\n\n' +
          'Detalles: ' + (err.response.data?.detail || 'Error desconocido')
        );
        return;
      }
      
      // Error genérico
      Alert.alert('Error', err.response?.data?.detail ?? err.message ?? 'Error desconocido al crear inscripción');
    } finally {
      setCreating(false);
    }
  };

  const resetForm = () => {
    // CAMBIO: Usar undefined en lugar de null
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
                    {item.idFormacion_detail?.nombreFormacion ?? '—'}
                  </Text>
                  <View style={[styles.badge, statusColor(status)]}>
                    <Text style={styles.badgeText}>{status}</Text>
                  </View>
                </View>
                <Text style={styles.cardSubtitle}>
                  {item.idPersona_detail?.nombres} {item.idPersona_detail?.apellidos}
                </Text>
              </View>

              <View style={styles.cardContent}>
                <View style={styles.detailRow}>
                  <View style={styles.detailItem}>
                    <Icon name="id-card" size={16} color="#666" />
                    <Text style={styles.detailText}>{item.idPersona_detail?.cedula ?? '—'}</Text>
                  </View>
                  <View style={styles.detailItem}>
                    <Icon name="domain" size={16} color="#666" />
                    <Text style={styles.detailText}>{item.idCohorte_detail?.nombreCohorte ?? '—'}</Text>
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
              ['Formación', selected.idFormacion_detail?.nombreFormacion ?? '—'],
              ['Cohorte', selected.idCohorte_detail?.nombreCohorte ?? '—'],
              ['Cédula', selected.idPersona_detail?.cedula ?? '—'],
              ['Nombres', selected.idPersona_detail?.nombres ?? '—'],
              ['Apellidos', selected.idPersona_detail?.apellidos ?? '—'],
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

                {/* Picker para Tipo de Formación */}
                <View style={styles.fieldContainer}>
                  <Text style={styles.label}>Tipo de Formación *</Text>
                  <View style={styles.pickerContainer}>
                    <Picker
                      selectedValue={selectedTipoFormacion}
                      onValueChange={(itemValue) => {
                        // CAMBIO: El Picker puede devolver string o number, asegurar que sea number
                        const value = itemValue !== undefined ? Number(itemValue) : undefined;
                        console.log('🎯 Tipo seleccionado:', value, 'Tipo:', typeof value);
                        setSelectedTipoFormacion(value);
                      }}
                      style={styles.picker}
                    >
                      {/* CAMBIO: Usar undefined en lugar de null */}
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
                    <Text style={styles.errorText}>{formErrors.tipoFormacion}</Text>
                  )}
                </View>

                {/* Picker para Formación */}
                <View style={styles.fieldContainer}>
                  <Text style={styles.label}>Formación Académica *</Text>
                  <View style={styles.pickerContainer}>
                    <Picker
                      selectedValue={selectedFormacion}
                      onValueChange={(itemValue) => {
                        const value = itemValue !== undefined ? Number(itemValue) : undefined;
                        console.log('🎯 Formación seleccionada:', value, 'Tipo:', typeof value);
                        setSelectedFormacion(value);
                        
                        // DEBUG: Ver cuotas de esta formación
                        if (value) {
                          debugCuotasCompleto(value); // Cambiar por la nueva función
                        }
                      }}
                      style={styles.picker}
                      enabled={formacionesFiltradas.length > 0}
                    >
                      {/* CAMBIO: Usar undefined en lugar de null */}
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
                    <Text style={styles.errorText}>{formErrors.formacion}</Text>
                  )}
                </View>

                <View style={styles.fieldContainer}>
                  <Text style={styles.label}>Cohorte *</Text>
                  <View style={styles.pickerContainer}>
                    <Picker
                      selectedValue={selectedCohorte}
                      onValueChange={(itemValue) => setSelectedCohorte(itemValue !== undefined ? Number(itemValue) : undefined)}
                      style={styles.picker}
                    >
                      {/* CAMBIO: Usar undefined en lugar de null */}
                      <Picker.Item label="Seleccione cohorte..." value={undefined} />
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
                  
                  {/* CUOTAS REALES DEL BACKEND */}
                  {cuotas.length > 0 ? (
                    <>
                      {cuotas.map((cuota, index) => (
                        <View key={index} style={styles.tableRow}>
                          <Text style={styles.tableCell}>
                            <Text style={styles.boldText}>
                              {cuota.nombreCuota || `Cuota ${index + 1}`}
                            </Text>
                          </Text>
                          <Text style={styles.tableCell}>
                            {fmtMoney(cuota.valorCuota)}
                          </Text>
                        </View>
                      ))}
                      <View style={styles.tableRow}>
                        <Text style={styles.tableCell}><Text style={styles.boldText}>Total Cuotas</Text></Text>
                        <Text style={[styles.tableCell, styles.cuotasCell]}>
                          <Text style={styles.boldText}>{fmtMoney(totalCuotas)}</Text>
                        </Text>
                      </View>
                    </>
                  ) : (
                    <View style={styles.tableRow}>
                      <Text style={[styles.tableCell, styles.noCuotasText]}>
                        No hay cuotas configuradas
                      </Text>
                      <Text style={[styles.tableCell, styles.noCuotasText]}>
                        $0.00
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
                
                {/* Información adicional */}
                <Text style={styles.helpText}>
                  {cuotas.length > 0 
                    ? `Incluye ${cuotas.length} cuota(s) programada(s) del sistema` 
                    : 'Solo incluye valor de inscripción (sin cuotas activas)'}
                </Text>
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
  noCuotasText: {
    color: '#999',
    fontStyle: 'italic',
    textAlign: 'center',
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