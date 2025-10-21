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
  idFormacion?: Formacion; // anidado
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
    // 1) idFormacion_detail (directo)
    if (inscripcion.idFormacion_detail?.nombreFormacion) {
      return inscripcion.idFormacion_detail.nombreFormacion;
    }
    // 2) cohorte.idFormacion (nested)
    if (inscripcion.idCohorte?.idFormacion?.nombreFormacion) {
      return inscripcion.idCohorte.idFormacion.nombreFormacion!;
    }
    // 3) extraer del nombre de la cohorte (fallback)
    const nombreCohorte = inscripcion.idCohorte?.nombreCohorte;
    if (nombreCohorte) {
      if (nombreCohorte.includes('Biotecnología')) return 'Biotecnología';
      if (nombreCohorte.includes('Ingeniería')) return 'Ingeniería';
      if (nombreCohorte.includes('Medicina')) return 'Medicina';
      if (nombreCohorte.includes('Derecho')) return 'Derecho';
      if (nombreCohorte.includes('Administración')) return 'Administración';
      // si no coincide, devolver el nombre de la cohorte
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

  // Cargar TODOS los datos en una sola función
  const loadAllData = async () => {
    setLoading(true);
    setError(null);

    try {
      console.log('🔍 Iniciando carga de datos del dashboard...');
      if (!user) {
        console.warn('⚠️ No hay usuario en el contexto de autenticación');
        setLoading(false);
        return;
      }

      const personaCedula = user.cedula;
      if (!personaCedula) {
        console.warn('⚠️ No se encontró cédula en user data');
        setLoading(false);
        return;
      }
      const cedulaUsuarioNormalizada = normalizarCedula(personaCedula);

      const inscripcionesResult = await safeApiCall('/api/inscripcion/');

      const extractData = (responseData: any) => {
        if (Array.isArray(responseData)) return responseData;
        if (responseData && Array.isArray(responseData.results)) return responseData.results;
        if (responseData && responseData.data && Array.isArray(responseData.data)) return responseData.data;
        if (responseData && typeof responseData === 'object') return [responseData];
        return [];
      };

      const todasInscripciones = extractData(inscripcionesResult.data);
      console.log('📊 Todas las inscripciones obtenidas:', todasInscripciones.length);

      let misInscripcionesFiltradas: Inscripcion[] = [];

      if (todasInscripciones.length > 0) {
        misInscripcionesFiltradas = todasInscripciones.filter((insc: any) => {
          const cedulaInscripcion = insc.idPersona_detail?.cedula || insc.idPersona?.cedula;
          if (!cedulaInscripcion) return false;
          const cedulaInscNormalizada = normalizarCedula(cedulaInscripcion);
          return cedulaInscNormalizada === cedulaUsuarioNormalizada;
        }).map((insc: any) => {
          // Normalizar estructura mínima que usamos en UI
          return {
            ...insc,
            // asegurar fechas y valores en tipos esperados
            fechaInscripcion: insc.fechaInscripcion || insc.fechaInscripcionString || null,
          } as Inscripcion;
        });
      }

      // Debug
      misInscripcionesFiltradas.forEach((insc) => {
        console.log('🔍 Insc debug:', {
          id: insc.idInscripcion,
          cohorte: insc.idCohorte,
          formacion_detail: insc.idFormacion_detail,
        });
      });

      setMisInscripciones(misInscripcionesFiltradas);

      // Simular notas por pagar (temporal)
      const notasSimuladas = misInscripcionesFiltradas.map(insc => ({
        idNota: insc.idInscripcion + 1000,
        totalNota: insc.montoTotal ?? getValorInscripcion(insc) ?? 0,
        descripcion: `Inscripción - ${getNombreFormacion(insc)}`,
        estado: insc.estadoPago === 'PAGADO' ? 'PAGADA' : insc.estadoPago ?? 'PENDIENTE',
        fechaEmision: insc.fechaInscripcion,
        tipoOperacion: 'COBRO',
        tipoArticulo: 'INSCRIPCION',
        relaciones: [{
          idInscripcion: {
            idInscripcion: insc.idInscripcion,
            idCohorte: {
              idCohorte: insc.idCohorte?.idCohorte,
              nombreCohorte: getNombreCohorte(insc)
            }
          }
        }]
      }));

      const notasPendientes = notasSimuladas.filter(n => n.estado === 'PENDIENTE' || n.estado === 'PARCIAL');
      setNotasPorPagar(notasPendientes);

      setMisPagos([]); // temporal

      const inscripcionesPagadas = misInscripcionesFiltradas.filter(i => i.estadoPago === 'PAGADO').length;
      const inscripcionesPendientes = misInscripcionesFiltradas.filter(i => i.estadoPago === 'PENDIENTE' || i.estadoPago === 'PARCIAL').length;

      setEstadoPago({ pagado: inscripcionesPagadas, pendiente: inscripcionesPendientes });

      if (misInscripcionesFiltradas.length === 0) {
        setError('No se encontraron inscripciones para este usuario');
      }
    } catch (err: any) {
      console.error('❌ Error crítico en loadAllData:', err);
      setError('Error inesperado al cargar los datos');
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

  const stats = [
    {
      title: 'Mis Inscripciones',
      value: misInscripciones.length.toString(),
      icon: 'book-account',
      color: '#fb6340',
      subtitle: ultimaInscripcion ? `${getNombreCohorte(ultimaInscripcion)} - ${ultimaInscripcion.estadoPago ?? 'Activa'}` : 'No tienes inscripciones',
    },
    {
      title: 'Mis Pagos',
      value: misPagos.length.toString(),
      icon: 'currency-usd',
      color: '#2dce89',
      subtitle: misPagos.length ? `Último: ${formatDate(misPagos[0].fechaPago)} - $${misPagos[0].monto}` : 'No hay pagos registrados',
    },
    {
      title: 'Estado de Pagos',
      value: estadoPago.pendiente === 0 ? 'Al día' : 'Pendiente',
      icon: 'clock-check',
      color: estadoPago.pendiente === 0 ? '#11cdef' : '#f7b731',
      subtitle: estadoPago.pendiente === 0 ? 'Todas las inscripciones pagadas' : `${estadoPago.pendiente} inscripción(es) pendiente(s)`,
    },
    {
      title: 'Notas por Pagar',
      value: notasPorPagar.length.toString(),
      icon: 'note-alert',
      color: '#f5365c',
      subtitle: montoTotalPorPagar > 0 ? `Total: ${fmtMoney(montoTotalPorPagar)}` : 'No hay notas pendientes',
    },
  ];

  const handleRetry = () => loadAllData();

  // Renders (loading / error handled)
  if (!user && loading) {
    return (
      <View style={styles.container}>
        <StatusBar barStyle="light-content" backgroundColor="#4f8cff" />
        <View style={styles.header}>
          <Text style={styles.headerTitle}>{greeting.emoji} {greeting.title}</Text>
          <Text style={styles.headerSubtitle}>Mi panel personal • {formatDate(new Date().toISOString())}</Text>
        </View>
        <View style={{ flex: 1, justifyContent: 'center', alignItems: 'center' }}>
          <ActivityIndicator size="large" color="#4f8cff" />
          <Text style={{ marginTop: 12, color: '#666' }}>Cargando información del usuario...</Text>
        </View>
      </View>
    );
  }

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

  if (error) {
    return (
      <View style={styles.container}>
        <StatusBar barStyle="light-content" backgroundColor="#4f8cff" />
        <View style={styles.header}>
          <Text style={styles.headerTitle}>{greeting.emoji} {greeting.title}</Text>
          <Text style={styles.headerSubtitle}>Mi panel personal • {formatDate(new Date().toISOString())}</Text>
        </View>
        <View style={{ flex: 1, justifyContent: 'center', alignItems: 'center', paddingHorizontal: 20 }}>
          <Icon name="alert-circle" size={48} color="#f5365c" />
          <Text style={{ color: '#f5365c', fontWeight: '700', marginBottom: 8, marginTop: 12, textAlign: 'center' }}>
            Error al cargar datos
          </Text>
          <Text style={{ color: '#666', textAlign: 'center', marginBottom: 20 }}>{error}</Text>
          <TouchableOpacity style={styles.retryButton} onPress={handleRetry}>
            <Icon name="reload" size={20} color="#fff" />
            <Text style={styles.retryButtonText}>Reintentar</Text>
          </TouchableOpacity>
        </View>
      </View>
    );
  }

  function getCohorteDeNota(nota: NotaCobro): React.ReactNode {
    throw new Error('Function not implemented.');
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

      <ScrollView contentContainerStyle={styles.scrollContent} showsVerticalScrollIndicator={false}>
        <View style={styles.cardsRow}>
          {stats.map((item, idx) => (
            <Animated.View
              key={item.title}
              style={[
                styles.card,
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
              <Text style={styles.cardSubtitle}>{item.subtitle}</Text>
            </Animated.View>
          ))}
        </View>

        <View style={styles.sectionContainer}>
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
          <View style={styles.detailContainer}>
            <Text style={styles.detailTitle}>Notas por Pagar</Text>
            {notasPorPagar.map((nota) => (
              <View key={nota.idNota} style={styles.notaItem}>
                <View style={styles.notaHeader}>
                  <Text style={styles.notaDescripcion}>{nota.descripcion || `Nota ${nota.idNota}`}</Text>
                  <Text style={styles.notaMonto}>{fmtMoney(nota.totalNota)}</Text>
                </View>
                <Text style={styles.notaDetalle}>
                  {getCohorteDeNota(nota)} • Emitida: {formatDate(nota.fechaEmision)} • Tipo: {nota.tipoArticulo || 'Cobro'}
                </Text>
              </View>
            ))}
          </View>
        )}

        {misInscripciones.length > 0 && (
          <View style={styles.detailContainer}>
            <Text style={styles.detailTitle}>Mis Inscripciones Activas</Text>
            {misInscripciones.map((inscripcion) => (
              <View key={inscripcion.idInscripcion} style={styles.inscripcionItem}>
                <View style={styles.inscripcionHeader}>
                  <Text style={styles.inscripcionNombre}>{getNombreCohorte(inscripcion)}</Text>
                  <Text style={[
                      styles.inscripcionEstado,
                      { color: inscripcion.estadoPago === 'PAGADO' ? '#2dce89' : inscripcion.estadoPago === 'PARCIAL' ? '#f7b731' : '#fb6340' }
                    ]}>
                    {inscripcion.estadoPago ?? 'PENDIENTE'}
                  </Text>
                </View>

                <Text style={styles.inscripcionFormacion}>{getNombreFormacion(inscripcion)}</Text>

                <Text style={styles.inscripcionDetalle}>
                  Valor: {fmtMoney(getValorInscripcion(inscripcion))} • Fecha: {formatDate(inscripcion.fechaInscripcion)}
                </Text>
              </View>
            ))}
          </View>
        )}

        {(misInscripciones.length === 0 && misPagos.length === 0 && notasPorPagar.length === 0) && (
          <View style={styles.infoContainer}>
            <Icon name="information" size={32} color="#4f8cff" />
            <Text style={styles.infoTitle}>Bienvenido al sistema</Text>
            <Text style={styles.infoText}>
              {user?.displayName ? `${user.displayName}, ` : ''} aún no tienes inscripciones, pagos ni notas registradas. Puedes comenzar realizando una nueva inscripción.
            </Text>
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
  // ---------------------------
  // HEADER reducido
  // ---------------------------
  header: {
    backgroundColor: '#4f8cff',
    paddingTop: 28,        // antes 48 -> reducido
    paddingBottom: 12,     // antes 20 -> reducido
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
    fontSize: 22,          // antes 26 -> ligeramente más pequeño
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
  },
  cardsRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    justifyContent: 'center',
    gap: 12,
    width: '94%',
  },
  card: {
    width: CARD_WIDTH,
    backgroundColor: '#fff',
    borderRadius: 16,
    padding: 18,
    margin: 6,
    alignItems: 'center',
    shadowColor: 'rgba(79,140,255,0.18)',
    shadowOffset: { width: 0, height: 6 },
    shadowOpacity: 0.14,
    shadowRadius: 12,
    elevation: 6,
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
    width: '94%',
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
  },
  actionButton: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#f8f9fe',
    paddingVertical: 12,
    paddingHorizontal: 16,
    borderRadius: 12,
    flex: 1,
    marginHorizontal: 4,
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
    width: '94%',
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
  },
  detailContainer: {
    marginTop: 20,
    width: '94%',
    backgroundColor: '#fff',
    borderRadius: 14,
    padding: 16,
    shadowColor: 'rgba(79,140,255,0.08)',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.10,
    shadowRadius: 8,
    elevation: 4,
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
  inscripcionDetalle: {
    fontSize: 12,
    color: '#666',
  },
  inscripcionFormacion: {
    fontSize: 12,
    color: '#4f8cff',
    fontWeight: '600',
    marginBottom: 4,
  },
});
