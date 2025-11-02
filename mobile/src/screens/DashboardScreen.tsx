// src/screens/DashboardScreen.tsx
import React, { useRef, useEffect, useState } from 'react';
import {
  StyleSheet,
  Text,
  View,
  ScrollView,
  Dimensions,
  Animated,
  StatusBar,
  ActivityIndicator,
  TouchableOpacity,
} from 'react-native';
import { useNavigation, NavigationProp } from '@react-navigation/native';
import Icon from 'react-native-vector-icons/MaterialCommunityIcons';
import { useAuth } from '../contexts/AuthContext';
import api from '../api/api';

const { width } = Dimensions.get('window');
const CARD_WIDTH = (width * 0.9 - 24) / 2;

type RootStackParamList = {
  Personas: undefined;
  Formaciones: undefined;
  TipoFormaciones: undefined;
  Materias: undefined;
  Cohortes: undefined;
  Cargos: undefined;
  Honorarios: undefined;
  Inscripciones: undefined;
  Solicitudes: undefined;
  Tramites: undefined;
  Servicios: undefined;
  Requisitos: undefined;
  Monedas: undefined;
  Tasas: undefined;
  Pagos: undefined;
};

interface Formacion {
  idFormacion?: number;
  nombreFormacion?: string;
  valorInscripcion?: number | string;
}

interface Cohorte {
  idCohorte?: number;
  nombreCohorte?: string;
  lapsoInscripcion?: number;
  fechaInicio?: string;
  fechaFin?: string;
  estadoCohorte?: string;
  idFormacion?: Formacion;
}

interface Inscripcion {
  idInscripcion: number;
  estadoPago?: string;
  fechaInscripcion?: string;
  idPersona?: number;
  idPersona_detail?: {
    cedula?: string;
  };
  idCohorte?: Cohorte;
  idFormacion_detail?: {
    idFormacion?: number;
    nombreFormacion?: string;
    valorInscripcion?: number | string;
  };
  montoPagado?: number;
  montoTotal?: number;
  saldoPendiente?: number;
}

interface NotaCobro {
  idNota: number;
  totalNota: number;
  descripcion?: string;
  estado: string;
  fechaEmision?: string;
  tipoOperacion: string;
  tipoArticulo: string;
  idPersona?: number;
  relaciones?: Array<{
    idInscripcion?: {
      idInscripcion?: number;
      idCohorte?: {
        nombreCohorte?: string;
      };
    };
  }>;
}

interface Pago {
  idPago: number;
  monto: number;
  fechaPago: string;
  idNota: number;
  formaPago: string;
  referencia?: string;
  idNota_detail?: {
    numeroNota?: string;
    descripcion?: string;
  };
}

export default function DashboardScreen() {
  const navigation = useNavigation<NavigationProp<RootStackParamList>>();
  const { user } = useAuth();

  // Anims
  const cardsAnim = useRef([
    new Animated.Value(0),
    new Animated.Value(0),
    new Animated.Value(0),
    new Animated.Value(0),
  ]).current;

  // Loading / error
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  
  // Datos
  const [misInscripciones, setMisInscripciones] = useState<Inscripcion[]>([]);
  const [misPagos, setMisPagos] = useState<Pago[]>([]);
  const [notasPorPagar, setNotasPorPagar] = useState<NotaCobro[]>([]);
  const [estadoPago, setEstadoPago] = useState<{pagado: number, pendiente: number}>({pagado: 0, pendiente: 0});

  // Saludo dinámico
  const [greeting, setGreeting] = useState<{ title: string; emoji: string }>({ title: '¡Bienvenido!', emoji: '👋' });

  useEffect(() => {
    const h = new Date().getHours();
    if (h >= 5 && h < 12) setGreeting({ title: '¡Buenos días!', emoji: '🌞' });
    else if (h >= 12 && h < 19) setGreeting({ title: '¡Buenas tardes!', emoji: '🌤️' });
    else setGreeting({ title: '¡Buenas noches!', emoji: '🌙' });
  }, []);

  // Helpers
  const formatDate = (dateString?: string) => {
    if (!dateString) return '—';
    try {
      const date = new Date(dateString);
      const dd = String(date.getDate()).padStart(2, '0');
      const mm = String(date.getMonth() + 1).padStart(2, '0');
      const yyyy = date.getFullYear();
      return `${dd}/${mm}/${yyyy}`;
    } catch {
      return '—';
    }
  };

  const fmtMoney = (v: any) => {
    const n = Number(v);
    if (!isFinite(n)) return '$0.00';
    return `$${n.toFixed(2)}`;
  };

  const normalizarCedula = (cedula: string): string => {
    if (!cedula) return '';
    let normalizada = cedula.toString().toUpperCase().replace(/[\.\-\s]/g, '');
    if (/^[VEJG]/.test(normalizada)) {
      normalizada = normalizada.substring(1);
    }
    return normalizada;
  };

  const safeApiCall = async (endpoint: string, options = {}) => {
    try {
      console.log(`🔍 Haciendo request a: ${endpoint}`);
      const response = await api.get(endpoint, options);
      console.log(`✅ Respuesta de ${endpoint}:`, typeof response.data, response.data);
      return { success: true, data: response.data };
    } catch (error: any) {
      console.warn(`❌ Error en ${endpoint}:`, error?.response?.status, error?.response?.data);
      if (error?.response?.status === 500) {
        console.error('💥 ERROR 500 - Detalles:', {
          url: error.config?.url,
          method: error.config?.method,
          data: error.response?.data
        });
      }
      return { success: false, error: error?.response?.data || error.message, data: [] };
    }
  };

  // Cohorte -> mostrar nombre + rango si hay fechas
  const getNombreCohorte = (inscripcion: Inscripcion): string => {
    const coh = inscripcion.idCohorte;
    if (!coh) return `Inscripción #${inscripcion.idInscripcion}`;

    if (coh.nombreCohorte) {
      const inicio = formatDate((coh as any).fechaInicio);
      const fin = formatDate((coh as any).fechaFin);
      if (inicio !== '—' && fin !== '—') {
        return `${coh.nombreCohorte} (${inicio} - ${fin})`;
      }
      return coh.nombreCohorte;
    }

    if (coh.idCohorte) return `Cohorte #${coh.idCohorte}`;
    return `Inscripción #${inscripcion.idInscripcion}`;
  };

  // Obtener nombre de la formación (varias fuentes)
  const getNombreFormacion = (inscripcion: Inscripcion): string => {
    if (inscripcion.idFormacion_detail?.nombreFormacion) {
      return inscripcion.idFormacion_detail.nombreFormacion;
    }
    if (inscripcion.idCohorte?.idFormacion?.nombreFormacion) {
      return inscripcion.idCohorte.idFormacion.nombreFormacion!;
    }
    const nombreCohorte = inscripcion.idCohorte?.nombreCohorte;
    if (nombreCohorte) {
      if (nombreCohorte.includes('Biotecnología')) return 'Biotecnología';
      if (nombreCohorte.includes('Ingeniería')) return 'Ingeniería';
      if (nombreCohorte.includes('Medicina')) return 'Medicina';
      if (nombreCohorte.includes('Derecho')) return 'Derecho';
      if (nombreCohorte.includes('Administración')) return 'Administración';
      return nombreCohorte;
    }
    return 'Formación Continua';
  };

  // Obtener valor de inscripción con fallbacks
  const getValorInscripcion = (inscripcion: Inscripcion): number => {
    const v1 = inscripcion.idFormacion_detail?.valorInscripcion;
    if (v1 !== undefined && v1 !== null) {
      const n = Number(v1);
      if (isFinite(n)) return n;
    }
    const v2 = inscripcion.idCohorte?.idFormacion?.valorInscripcion;
    if (v2 !== undefined && v2 !== null) {
      const n = Number(v2);
      if (isFinite(n)) return n;
    }
    if (inscripcion.montoTotal !== undefined && inscripcion.montoTotal !== null) {
      const n = Number(inscripcion.montoTotal);
      if (isFinite(n)) return n;
    }
    return 0;
  };

  // Función mejorada para extraer datos de APIs
  const extractData = (data: any): any[] => {
    try {
      if (data == null) return [];
      if (Array.isArray(data)) return data;
      if (typeof data === 'object') {
        const commonKeys = ['results', 'data', 'rows', 'items', 'list', 'inscripciones', 'results_list'];
        for (const k of commonKeys) {
          if (Array.isArray(data[k])) return data[k];
        }
        if (data.data && Array.isArray(data.data.results)) return data.data.results;
        if (data.pagination && Array.isArray(data.pagination.results)) return data.pagination.results;
        const arrayProps = Object.values(data).filter(v => Array.isArray(v));
        if (arrayProps.length === 1) return arrayProps[0];
        if (data.idInscripcion || data.id || data.id_inscripcion || data.idPersona) return [data];
        const flattened = ([] as any[]).concat(...Object.values(data).filter(Array.isArray));
        if (flattened.length) return flattened;
      }
    } catch (e) {
      console.warn('Error extrayendo datos:', e);
    }
    return [];
  };

  // Cargar datos reales de notas y pagos
  const loadNotasAndPagos = async (cedulaUsuarioNormalizada: string) => {
    try {
      // Cargar notas reales del endpoint específico para usuario autenticado
      const notasResult = await safeApiCall('/api/notas/usuario/autenticado/');
      let todasNotas = extractData(notasResult.data);
      
      console.log('📋 Notas obtenidas del endpoint:', todasNotas.length);
      
      // Filtrar notas del usuario actual (por si el endpoint no filtra completamente)
      const misNotas = todasNotas.filter((nota: any) => {
        const cedulaNota = nota.idPersona_detail?.cedula || nota.idPersona?.cedula;
        if (!cedulaNota) return false;
        return normalizarCedula(cedulaNota) === cedulaUsuarioNormalizada;
      });

      console.log('👤 Notas filtradas para el usuario:', misNotas.length);

      // Filtrar notas por pagar (PENDIENTE o PARCIAL)
      const notasPendientes = misNotas.filter((nota: any) => 
        nota.estado === 'PENDIENTE' || nota.estado === 'PARCIAL'
      );
      setNotasPorPagar(notasPendientes);

      // Cargar pagos reales
      const pagosResult = await safeApiCall('/api/pagos/');
      let todosPagos = extractData(pagosResult.data);
      
      console.log('💰 Todos los pagos obtenidos:', todosPagos.length);
      
      // Filtrar pagos del usuario
      const misPagosFiltrados = todosPagos.filter((pago: any) => {
        const cedulaPago = pago.idNota?.idPersona_detail?.cedula || 
                          pago.idNota?.idPersona?.cedula ||
                          pago.idPersona_detail?.cedula;
        if (!cedulaPago) return false;
        return normalizarCedula(cedulaPago) === cedulaUsuarioNormalizada;
      }).map((pago: any) => ({
        idPago: pago.idPago,
        monto: pago.monto,
        fechaPago: pago.fechaPago,
        idNota: pago.idNota?.idNota || pago.idNota,
        formaPago: pago.formaPago,
        referencia: pago.referencia,
        idNota_detail: pago.idNota_detail || {
          numeroNota: pago.idNota?.numeroNota,
          descripcion: pago.idNota?.descripcion
        }
      }));

      console.log('👤 Pagos filtrados para el usuario:', misPagosFiltrados.length);
      setMisPagos(misPagosFiltrados);

      return { 
        misNotas, 
        misPagos: misPagosFiltrados,
        notasPendientes 
      };
    } catch (error) {
      console.error('Error cargando notas y pagos:', error);
      // En caso de error, establecer arrays vacíos
      setNotasPorPagar([]);
      setMisPagos([]);
      return { misNotas: [], misPagos: [], notasPendientes: [] };
    }
  };

  // Cargar TODOS los datos en una sola función
  const loadAllData = async () => {
    setLoading(true);
    setError(null);

    try {
      console.log('🔍 Iniciando carga de datos del dashboard...');
      if (!user) {
        console.warn('⚠️ No hay usuario en el contexto de autenticación');
        setMisInscripciones([]);
        setNotasPorPagar([]);
        setMisPagos([]);
        setEstadoPago({ pagado: 0, pendiente: 0 });
        setLoading(false);
        return;
      }

      const personaCedula = user.cedula;
      if (!personaCedula) {
        console.warn('⚠️ No se encontró cédula en user data');
        setMisInscripciones([]);
        setNotasPorPagar([]);
        setMisPagos([]);
        setEstadoPago({ pagado: 0, pendiente: 0 });
        setLoading(false);
        return;
      }

      const cedulaUsuarioNormalizada = normalizarCedula(personaCedula);
      console.log('👤 Usuario normalizado:', cedulaUsuarioNormalizada);

      // Cargar inscripciones
      const inscripcionesResult = await safeApiCall('/api/inscripcion/');
      
      let misInscripcionesFiltradas: Inscripcion[] = [];
      
      if (inscripcionesResult.success) {
        const todasInscripciones = extractData(inscripcionesResult.data);
        console.log('📊 Todas las inscripciones obtenidas:', todasInscripciones.length);

        if (todasInscripciones.length > 0) {
          misInscripcionesFiltradas = todasInscripciones.filter((insc: any) => {
            const cedulaInscripcion = insc.idPersona_detail?.cedula || insc.idPersona?.cedula;
            if (!cedulaInscripcion) {
              console.log('❌ Inscripción sin cédula:', insc.idInscripcion);
              return false;
            }
            const cedulaInscNormalizada = normalizarCedula(cedulaInscripcion);
            const coincide = cedulaInscNormalizada === cedulaUsuarioNormalizada;
            if (!coincide) {
              console.log('❌ Cédula no coincide:', cedulaInscNormalizada, 'vs', cedulaUsuarioNormalizada);
            }
            return coincide;
          }).map((insc: any) => ({
            ...insc,
            fechaInscripcion: insc.fechaInscripcion || insc.fechaInscripcionString || null,
          } as Inscripcion));
        }
        console.log('✅ Inscripciones filtradas para el usuario:', misInscripcionesFiltradas.length);
      } else {
        console.warn('❌ No se pudieron cargar las inscripciones');
      }

      setMisInscripciones(misInscripcionesFiltradas);

      // Cargar notas y pagos reales
      const { misNotas, misPagos: misPagosReales, notasPendientes } = await loadNotasAndPagos(cedulaUsuarioNormalizada);

      // Calcular estado de pagos basado en inscripciones Y notas
      const inscripcionesPagadas = misInscripcionesFiltradas.filter(i => 
        i.estadoPago === 'PAGADO'
      ).length;
      
      const inscripcionesPendientes = misInscripcionesFiltradas.filter(i => 
        i.estadoPago === 'PENDIENTE' || i.estadoPago === 'PARCIAL'
      ).length;

      // También considerar las notas para el estado general
      const totalNotasPendientes = notasPendientes.length;
      const totalPagos = misPagosReales.length;

      console.log('📊 Resumen final:', {
        inscripciones: misInscripcionesFiltradas.length,
        inscripcionesPagadas,
        inscripcionesPendientes,
        notasPendientes: totalNotasPendientes,
        pagos: totalPagos
      });

      setEstadoPago({ 
        pagado: inscripcionesPagadas, 
        pendiente: inscripcionesPendientes 
      });

      // Si no hay datos, no es un error - solo mostrar estado vacío
      if (misInscripcionesFiltradas.length === 0 && totalNotasPendientes === 0 && totalPagos === 0) {
        console.log('ℹ️ Usuario sin datos registrados');
      }

    } catch (err: any) {
      console.error('❌ Error crítico en loadAllData:', err);
      // No establecer error para que se muestre el dashboard vacío
      setMisInscripciones([]);
      setNotasPorPagar([]);
      setMisPagos([]);
      setEstadoPago({ pagado: 0, pendiente: 0 });
    } finally {
      setLoading(false);
      console.log('🏁 Carga de datos finalizada');
    }
  };

  useEffect(() => {
    Animated.stagger(90, cardsAnim.map(a => Animated.spring(a, { toValue: 1, useNativeDriver: true }))).start();
  }, []);

  useEffect(() => {
    if (user) {
      console.log('👤 Usuario disponible en contexto, cargando datos...');
      loadAllData();
    } else {
      console.log('⏳ Esperando usuario en contexto...');
      setLoading(true);
    }
  }, [user]);

  // Stats
  const ultimaInscripcion = misInscripciones.length ? misInscripciones[0] : null;
  const montoTotalPorPagar = notasPorPagar.reduce((t, n) => t + (n.totalNota || 0), 0);
  const ultimoPago = misPagos.length ? misPagos[0] : null;

  const stats = [
    {
      title: 'Mis Inscripciones',
      value: misInscripciones.length.toString(),
      icon: 'book-account',
      color: '#fb6340',
      subtitle: ultimaInscripcion ? 
        `${getNombreCohorte(ultimaInscripcion)} - ${ultimaInscripcion.estadoPago ?? 'Activa'}` : 
        'No tienes inscripciones',
    },
    {
      title: 'Mis Pagos',
      value: misPagos.length.toString(),
      icon: 'currency-usd',
      color: '#2dce89',
      subtitle: ultimoPago ? 
        `Último: ${formatDate(ultimoPago.fechaPago)} - ${fmtMoney(ultimoPago.monto)}` : 
        'No hay pagos registrados',
    },
    {
      title: 'Estado de Pagos',
      value: estadoPago.pendiente === 0 ? 'Al día' : 'Pendiente',
      icon: 'clock-check',
      color: estadoPago.pendiente === 0 ? '#11cdef' : '#f7b731',
      subtitle: estadoPago.pendiente === 0 ? 
        'Todas las inscripciones pagadas' : 
        `${estadoPago.pendiente} inscripción(es) pendiente(s)`,
    },
    {
      title: 'Notas por Pagar',
      value: notasPorPagar.length.toString(),
      icon: 'note-alert',
      color: '#f5365c',
      subtitle: montoTotalPorPagar > 0 ? 
        `Total: ${fmtMoney(montoTotalPorPagar)}` : 
        'No hay notas pendientes',
    },
  ];

  const handleRetry = () => loadAllData();

  function getCohorteDeNota(nota: NotaCobro): React.ReactNode {
    try {
      const relaciones = nota?.relaciones;
      if (Array.isArray(relaciones) && relaciones.length > 0) {
        const r0 = relaciones[0];
        const nombre = r0?.idInscripcion?.idCohorte?.nombreCohorte;
        if (nombre) return String(nombre);
      }

      const insc = (nota as any).idInscripcion;
      if (insc) {
        const nn = insc?.idCohorte?.nombreCohorte || insc?.idCohorte?.nombre;
        if (nn) return String(nn);
      }

      if (nota.descripcion) return nota.descripcion;
      return '—';
    } catch (e) {
      console.warn('getCohorteDeNota error:', e);
      return '—';
    }
  }

  // Obtener descripción de la nota para pagos
  const getDescripcionNota = (pago: Pago): string => {
    if (pago.idNota_detail?.descripcion) {
      return pago.idNota_detail.descripcion;
    }
    if (pago.idNota_detail?.numeroNota) {
      return `Nota ${pago.idNota_detail.numeroNota}`;
    }
    return `Pago para nota ${pago.idNota}`;
  };

  // Render principal
  if (loading) {
    return (
      <View style={styles.container}>
        <StatusBar barStyle="light-content" backgroundColor="#4f8cff" />
        <View style={styles.header}>
          <Text style={styles.headerTitle}>{greeting.emoji} {greeting.title}</Text>
          <Text style={styles.headerSubtitle}>Mi panel personal • {formatDate(new Date().toISOString())}</Text>
        </View>
        <View style={{ flex: 1, justifyContent: 'center', alignItems: 'center' }}>
          <ActivityIndicator size="large" color="#4f8cff" />
          <Text style={{ marginTop: 12, color: '#666' }}>Cargando tus datos...</Text>
        </View>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <StatusBar barStyle="light-content" backgroundColor="#4f8cff" />
      <View style={styles.header}>
        <Text style={styles.headerTitle}>
          {greeting.emoji} {greeting.title}
          {user?.displayName ? ` — ${user.displayName}` : ''}
        </Text>
        <Text style={styles.headerSubtitle}>Mi panel personal • {formatDate(new Date().toISOString())}</Text>
      </View>

      <ScrollView 
        contentContainerStyle={styles.scrollContent} 
        showsVerticalScrollIndicator={false}
        style={styles.responsiveScrollView}
      >
        <View style={styles.cardsRow}>
          {stats.map((item, idx) => (
            <Animated.View
              key={item.title}
              style={[
                styles.card,
                styles.responsiveCard,
                {
                  opacity: cardsAnim[idx],
                  transform: [{ translateY: cardsAnim[idx].interpolate({ inputRange: [0, 1], outputRange: [40, 0] }) }],
                },
              ]}
            >
              <View style={[styles.iconCircle, { backgroundColor: item.color }]}>
                <Icon name={item.icon} size={28} color="#fff" />
              </View>
              <Text style={styles.cardTitle}>{item.title}</Text>
              <Text style={styles.cardValue}>{item.value}</Text>
              <Text style={styles.cardSubtitle} numberOfLines={2}>{item.subtitle}</Text>
            </Animated.View>
          ))}
        </View>

        <View style={[styles.sectionContainer, styles.responsiveSection]}>
          <Text style={styles.sectionTitle}>Acciones rápidas</Text>
          <View style={styles.actionsRow}>
            <TouchableOpacity style={styles.actionButton} onPress={() => navigation.navigate('Inscripciones')}>
              <Icon name="book-plus" size={22} color="#4f8cff" />
              <Text style={styles.actionButtonText}>Nueva Inscripción</Text>
            </TouchableOpacity>
            <TouchableOpacity style={styles.actionButton} onPress={() => navigation.navigate('Pagos')}>
              <Icon name="credit-card-check" size={22} color="#2dce89" />
              <Text style={styles.actionButtonText}>Realizar Pago</Text>
            </TouchableOpacity>
          </View>
        </View>

        {notasPorPagar.length > 0 && (
          <View style={[styles.detailContainer, styles.responsiveDetail]}>
            <Text style={styles.detailTitle}>Notas por Pagar</Text>
            {notasPorPagar.map((nota) => (
              <View key={nota.idNota} style={styles.notaItem}>
                <View style={styles.notaHeader}>
                  <Text style={styles.notaDescripcion}>{nota.descripcion || `Nota ${nota.idNota}`}</Text>
                  <Text style={styles.notaMonto}>{fmtMoney(nota.totalNota)}</Text>
                </View>
                <Text style={styles.notaDetalle}>
                  {getCohorteDeNota(nota)} • Emitida: {formatDate(nota.fechaEmision)} • Estado: {nota.estado}
                </Text>
                <Text style={[
                  styles.notaEstado,
                  { color: nota.estado === 'PARCIAL' ? '#f7b731' : '#fb6340' }
                ]}>
                  {nota.estado === 'PARCIAL' ? '✅ Pago parcial realizado' : '⏳ Pendiente de pago'}
                </Text>
              </View>
            ))}
          </View>
        )}

        {misInscripciones.length > 0 && (
          <View style={[styles.detailContainer, styles.responsiveDetail]}>
            <Text style={styles.detailTitle}>Mis Inscripciones Activas</Text>
            {misInscripciones.map((inscripcion) => (
              <View key={inscripcion.idInscripcion} style={styles.inscripcionItem}>
                <View style={styles.inscripcionHeader}>
                  <Text style={styles.inscripcionNombre}>{getNombreCohorte(inscripcion)}</Text>
                  <Text style={[
                      styles.inscripcionEstado,
                      { 
                        color: inscripcion.estadoPago === 'PAGADO' ? '#2dce89' : 
                               inscripcion.estadoPago === 'PARCIAL' ? '#f7b731' : '#fb6340' 
                      }
                    ]}>
                    {inscripcion.estadoPago ?? 'PENDIENTE'}
                  </Text>
                </View>
                <Text style={styles.inscripcionFormacion}>{getNombreFormacion(inscripcion)}</Text>
                <Text style={styles.inscripcionDetalle}>
                  Valor: {fmtMoney(getValorInscripcion(inscripcion))} • Fecha: {formatDate(inscripcion.fechaInscripcion)}
                </Text>
                {inscripcion.montoPagado !== undefined && inscripcion.montoPagado > 0 && (
                  <Text style={styles.inscripcionPago}>
                    Pagado: {fmtMoney(inscripcion.montoPagado)} • 
                    {inscripcion.saldoPendiente !== undefined && ` Saldo: ${fmtMoney(inscripcion.saldoPendiente)}`}
                  </Text>
                )}
              </View>
            ))}
          </View>
        )}

        {misPagos.length > 0 && (
          <View style={[styles.detailContainer, styles.responsiveDetail]}>
            <Text style={styles.detailTitle}>Mis Últimos Pagos</Text>
            {misPagos.slice(0, 5).map((pago) => (
              <View key={pago.idPago} style={styles.pagoItem}>
                <View style={styles.pagoHeader}>
                  <Text style={styles.pagoDescripcion}>{getDescripcionNota(pago)}</Text>
                  <Text style={styles.pagoMonto}>{fmtMoney(pago.monto)}</Text>
                </View>
                <View style={styles.pagoDetalleRow}>
                  <Text style={styles.pagoDetalle}>
                    {formatDate(pago.fechaPago)} • {pago.formaPago}
                  </Text>
                  {pago.referencia && (
                    <Text style={styles.pagoReferencia}>Ref: {pago.referencia}</Text>
                  )}
                </View>
              </View>
            ))}
            {misPagos.length > 5 && (
              <Text style={styles.moreItemsText}>
                Y {misPagos.length - 5} pagos más...
              </Text>
            )}
          </View>
        )}

        {(misInscripciones.length === 0 && misPagos.length === 0 && notasPorPagar.length === 0) && (
          <View style={styles.infoContainer}>
            <Icon name="information" size={32} color="#4f8cff" />
            <Text style={styles.infoTitle}>Bienvenido al sistema</Text>
            <Text style={styles.infoText}>
              {user?.displayName ? `${user.displayName}, ` : ''} aún no tienes inscripciones, pagos ni notas registradas. 
              Puedes comenzar realizando una nueva inscripción.
            </Text>
            <TouchableOpacity 
              style={styles.primaryButton} 
              onPress={() => navigation.navigate('Inscripciones')}
            >
              <Text style={styles.primaryButtonText}>Comenzar Inscripción</Text>
            </TouchableOpacity>
          </View>
        )}
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f5f7fa',
  },
  responsiveScrollView: {
    maxWidth: 1200,
    alignSelf: 'center',
    width: '100%',
  },
  header: {
    backgroundColor: '#4f8cff',
    paddingTop: 28,
    paddingBottom: 12,
    paddingHorizontal: 20,
    borderBottomLeftRadius: 24,
    borderBottomRightRadius: 24,
    alignItems: 'flex-start',
    elevation: 6,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 6 },
    shadowOpacity: 0.14,
    shadowRadius: 10,
  },
  headerTitle: {
    color: '#fff',
    fontSize: 22,
    fontWeight: '800',
    letterSpacing: 0.3,
  },
  headerSubtitle: {
    color: '#e7f0ff',
    fontSize: 12,
    marginTop: 6,
    fontWeight: '600',
  },
  scrollContent: {
    alignItems: 'center',
    paddingVertical: 24,
    paddingHorizontal: 10,
  },
  cardsRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    justifyContent: 'center',
    gap: 12,
    width: '100%',
    maxWidth: 1000,
  },
  card: {
    backgroundColor: '#fff',
    borderRadius: 16,
    padding: 18,
    alignItems: 'center',
    shadowColor: 'rgba(79,140,255,0.18)',
    shadowOffset: { width: 0, height: 6 },
    shadowOpacity: 0.14,
    shadowRadius: 12,
    elevation: 6,
    minWidth: 150,
    flex: 1,
    maxWidth: 240,
    margin: 6,
  },
  responsiveCard: {
    // Se adapta automáticamente con flex: 1
  },
  iconCircle: {
    width: 48,
    height: 48,
    borderRadius: 24,
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: 10,
    shadowColor: '#000',
    shadowOpacity: 0.12,
    shadowOffset: { width: 0, height: 2 },
    shadowRadius: 4,
    elevation: 4,
  },
  cardTitle: {
    fontSize: 12,
    color: '#7b7b93',
    fontWeight: '700',
    textAlign: 'center',
    marginBottom: 4,
    textTransform: 'uppercase',
    letterSpacing: 0.4,
  },
  cardValue: {
    fontSize: 26,
    fontWeight: '800',
    color: '#22223b',
    marginBottom: 4,
    textAlign: 'center',
  },
  cardSubtitle: {
    fontSize: 12,
    color: '#4f8cff',
    textAlign: 'center',
    marginTop: 2,
  },
  sectionContainer: {
    marginTop: 20,
    width: '100%',
    maxWidth: 1000,
    backgroundColor: '#fff',
    borderRadius: 14,
    padding: 16,
    alignItems: 'flex-start',
    shadowColor: 'rgba(79,140,255,0.08)',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.10,
    shadowRadius: 8,
    elevation: 4,
  },
  responsiveSection: {
    paddingHorizontal: 16,
  },
  sectionTitle: {
    fontSize: 15,
    fontWeight: '700',
    color: '#4f8cff',
    marginBottom: 12,
  },
  actionsRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    width: '100%',
    flexWrap: 'wrap',
    gap: 10,
  },
  actionButton: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#f8f9fe',
    paddingVertical: 12,
    paddingHorizontal: 16,
    borderRadius: 12,
    flex: 1,
    minWidth: 150,
    justifyContent: 'center',
  },
  actionButtonText: {
    color: '#4f8cff',
    fontWeight: '600',
    fontSize: 14,
    marginLeft: 8,
  },
  retryButton: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#4f8cff',
    paddingVertical: 12,
    paddingHorizontal: 20,
    borderRadius: 8,
  },
  retryButtonText: {
    color: '#fff',
    fontWeight: '600',
    fontSize: 14,
    marginLeft: 8,
  },
  infoContainer: {
    marginTop: 20,
    width: '100%',
    maxWidth: 1000,
    backgroundColor: '#e7f0ff',
    borderRadius: 14,
    padding: 20,
    alignItems: 'center',
  },
  infoTitle: {
    fontSize: 16,
    fontWeight: '700',
    color: '#4f8cff',
    marginTop: 8,
    marginBottom: 8,
  },
  infoText: {
    fontSize: 14,
    color: '#4f8cff',
    textAlign: 'center',
    lineHeight: 20,
    marginBottom: 16,
  },
  primaryButton: {
    backgroundColor: '#4f8cff',
    paddingVertical: 12,
    paddingHorizontal: 24,
    borderRadius: 8,
    alignItems: 'center',
  },
  primaryButtonText: {
    color: '#fff',
    fontWeight: '600',
    fontSize: 14,
  },
  detailContainer: {
    marginTop: 20,
    width: '100%',
    maxWidth: 1000,
    backgroundColor: '#fff',
    borderRadius: 14,
    padding: 16,
    shadowColor: 'rgba(79,140,255,0.08)',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.10,
    shadowRadius: 8,
    elevation: 4,
  },
  responsiveDetail: {
    paddingHorizontal: 16,
  },
  detailTitle: {
    fontSize: 16,
    fontWeight: '700',
    color: '#4f8cff',
    marginBottom: 12,
  },
  notaItem: {
    backgroundColor: '#f8f9fe',
    padding: 12,
    borderRadius: 8,
    marginBottom: 8,
  },
  notaHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 4,
    flexWrap: 'wrap',
  },
  notaDescripcion: {
    fontSize: 14,
    fontWeight: '600',
    color: '#22223b',
    flex: 1,
  },
  notaMonto: {
    fontSize: 16,
    fontWeight: '700',
    color: '#f5365c',
  },
  notaDetalle: {
    fontSize: 12,
    color: '#666',
    marginBottom: 2,
  },
  notaEstado: {
    fontSize: 11,
    fontWeight: '600',
  },
  inscripcionItem: {
    backgroundColor: '#f8f9fe',
    padding: 12,
    borderRadius: 8,
    marginBottom: 8,
  },
  inscripcionHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 4,
    flexWrap: 'wrap',
  },
  inscripcionNombre: {
    fontSize: 14,
    fontWeight: '600',
    color: '#22223b',
    flex: 1,
  },
  inscripcionEstado: {
    fontSize: 12,
    fontWeight: '700',
  },
  inscripcionFormacion: {
    fontSize: 12,
    color: '#4f8cff',
    fontWeight: '600',
    marginBottom: 4,
  },
  inscripcionDetalle: {
    fontSize: 12,
    color: '#666',
    marginBottom: 2,
  },
  inscripcionPago: {
    fontSize: 11,
    color: '#2dce89',
    fontWeight: '600',
  },
  pagoItem: {
    backgroundColor: '#f0f9f4',
    padding: 12,
    borderRadius: 8,
    marginBottom: 8,
  },
  pagoHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 4,
    flexWrap: 'wrap',
  },
  pagoDescripcion: {
    fontSize: 14,
    fontWeight: '600',
    color: '#22223b',
    flex: 1,
  },
  pagoMonto: {
    fontSize: 16,
    fontWeight: '700',
    color: '#2dce89',
  },
  pagoDetalleRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    flexWrap: 'wrap',
  },
  pagoDetalle: {
    fontSize: 12,
    color: '#666',
  },
  pagoReferencia: {
    fontSize: 11,
    color: '#6c757d',
    fontStyle: 'italic',
  },
  moreItemsText: {
    fontSize: 12,
    color: '#6c757d',
    textAlign: 'center',
    marginTop: 8,
    fontStyle: 'italic',
  },
});