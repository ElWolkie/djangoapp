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
}

interface Cohorte {
  idCohorte?: number;
  nombreCohorte?: string;
  idFormacion?: Formacion;
}

interface Inscripcion {
  idInscripcion: number;
  estadoPago: string;
  fechaInscripcion: string;
  idPersona: number;
  idPersona_detail?: {
    cedula?: string;
  };
  idCohorte?: Cohorte;
  idFormacion_detail?: {
    idFormacion?: number;
    nombreFormacion?: string;
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
  fechaEmision: string;
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
  
  // Nuevos datos personalizados
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

  // Helper para formatear fecha
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

  // Función para normalizar cédula (igual que en InscripcionesScreen)
  const normalizarCedula = (cedula: string): string => {
    if (!cedula) return '';
    let normalizada = cedula.toString().toUpperCase().replace(/[\.\-\s]/g, '');
    if (/^[VEJG]/.test(normalizada)) {
      normalizada = normalizada.substring(1);
    }
    return normalizada;
  };

  // Función segura para hacer peticiones
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
        
        return { 
          success: false, 
          error: error?.response?.data || error.message, 
          data: [] 
        };
      }
    };

  // Función MEJORADA para obtener nombre de cohorte
  const getNombreCohorte = (inscripcion: Inscripcion): string => {
    if (!inscripcion.idCohorte) {
      return `Inscripción #${inscripcion.idInscripcion}`;
    }
    
    // Si tenemos nombre de cohorte específico
    if (inscripcion.idCohorte.nombreCohorte) {
      return inscripcion.idCohorte.nombreCohorte;
    }
    
    // Si tenemos ID de cohorte pero no nombre
    if (inscripcion.idCohorte.idCohorte) {
      return `Cohorte #${inscripcion.idCohorte.idCohorte}`;
    }
    
    return `Inscripción #${inscripcion.idInscripcion}`;
  };

  // REEMPLAZA la función getNombreFormacion actual con esta versión MÁS AGRESIVA:
  const getNombreFormacion = (inscripcion: Inscripcion): string => {
  console.log(`🔍 [GET_NOMBRE_FORMACION] Buscando nombre para inscripción ${inscripcion.idInscripcion}`);
  
  // 1. Primero intentar con idFormacion_detail (que es lo que viene del backend)
  if (inscripcion.idFormacion_detail?.nombreFormacion) {
    const nombre = inscripcion.idFormacion_detail.nombreFormacion;
    console.log(`✅ [GET_NOMBRE_FORMACION] Encontrado en idFormacion_detail: ${nombre}`);
    return nombre;
  }
  
  // 2. Luego intentar con la formación dentro de la cohorte (por si acaso)
  if (inscripcion.idCohorte?.idFormacion?.nombreFormacion) {
    const nombre = inscripcion.idCohorte.idFormacion.nombreFormacion;
    console.log(`✅ [GET_NOMBRE_FORMACION] Encontrado en idCohorte.idFormacion: ${nombre}`);
    return nombre;
  }
    
    // 3. Intentar extraer del nombre de la cohorte
    const nombreCohorte = getNombreCohorte(inscripcion);
    if (nombreCohorte && !nombreCohorte.startsWith('Inscripción #') && !nombreCohorte.startsWith('Cohorte #')) {
      console.log(`🟡 [GET_NOMBRE_FORMACION] Usando nombre de cohorte: ${nombreCohorte}`);
      return nombreCohorte;
    }
    
    // 4. Último recurso - buscar en datos de la inscripción
    if (inscripcion.idCohorte?.nombreCohorte) {
      const nombreCohorteCompleto = inscripcion.idCohorte.nombreCohorte;
      
      // Intentar extraer nombre de formación del nombre de cohorte
      if (nombreCohorteCompleto.includes('Biotecnología')) return 'Biotecnología';
      if (nombreCohorteCompleto.includes('Ingeniería')) return 'Ingeniería';
      if (nombreCohorteCompleto.includes('Medicina')) return 'Medicina';
      if (nombreCohorteCompleto.includes('Derecho')) return 'Derecho';
      if (nombreCohorteCompleto.includes('Administración')) return 'Administración';
      
      console.log(`🟡 [GET_NOMBRE_FORMACION] Usando nombre completo de cohorte: ${nombreCohorteCompleto}`);
      return nombreCohorteCompleto;
    }
    
    console.log(`🔴 [GET_NOMBRE_FORMACION] No se pudo determinar, usando valor por defecto`);
    return 'Formación Continua';
  };


    // Función mejorada para obtener información de la cohorte de una nota
  const getCohorteDeNota = (nota: NotaCobro) => {
    if (nota.relaciones && nota.relaciones.length > 0) {
      const primeraRelacion = nota.relaciones[0];
      if (primeraRelacion.idInscripcion?.idCohorte?.nombreCohorte) {
        return primeraRelacion.idInscripcion.idCohorte.nombreCohorte;
      }
      if (primeraRelacion.idInscripcion?.idInscripcion) {
        // Buscar la inscripción correspondiente para obtener más datos
        const inscripcionCorrespondiente = misInscripciones.find(
          insc => insc.idInscripcion === primeraRelacion.idInscripcion?.idInscripcion
        );
        if (inscripcionCorrespondiente) {
          return getNombreCohorte(inscripcionCorrespondiente);
        }
        return `Inscripción #${primeraRelacion.idInscripcion.idInscripcion}`;
      }
    }
    
    // Si no hay relaciones, usar la descripción mejorada
    if (nota.descripcion) {
      const descripcionLimpia = nota.descripcion.replace('Inscripción - ', '');
      if (descripcionLimpia !== 'Formación Continua') {
        return descripcionLimpia;
      }
    }
    
    // Buscar en las inscripciones si esta nota está relacionada
    const inscripcionRelacionada = misInscripciones.find(
      insc => insc.idInscripcion === (nota.idNota - 1000) // Por la simulación temporal
    );
    if (inscripcionRelacionada) {
      return getNombreCohorte(inscripcionRelacionada);
    }
    
    return 'Formación Continua';
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

      console.log('✅ Usuario del contexto:', user);

      const personaCedula = user.cedula;
      if (!personaCedula) {
        console.warn('⚠️ No se encontró cédula en user data');
        setLoading(false);
        return;
      }

      const cedulaUsuarioNormalizada = normalizarCedula(personaCedula);
      console.log('✅ Cédula normalizada a usar:', cedulaUsuarioNormalizada);

      // USAR EL ENDPOINT QUE SÍ FUNCIONA
      console.log('🔍 Cargando datos de APIs...');
      
      const inscripcionesResult = await safeApiCall('/api/inscripcion/');  // ✅ ESTE ENDPOINT SÍ FUNCIONA

      // Extraer datos de forma robusta
      const extractData = (responseData: any, tipo: string) => {
        let dataArray: any[] = [];
        
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
        
        console.log(`📋 ${tipo} - Datos extraídos:`, dataArray.length);
        return dataArray;
      };

      const todasInscripciones = extractData(inscripcionesResult.data, 'Inscripciones');
      
      console.log('📊 Todas las inscripciones obtenidas:', todasInscripciones.length);

      // FILTRAR EN EL FRONTEND (como en el dashboard funcional)
      let misInscripcionesFiltradas: Inscripcion[] = [];
      
      if (todasInscripciones.length > 0) {
        console.log('🔍 Buscando inscripciones del usuario por cédula...');
        
        misInscripcionesFiltradas = todasInscripciones.filter((insc: any) => {
          const cedulaInscripcion = insc.idPersona_detail?.cedula || insc.idPersona?.cedula;
          if (!cedulaInscripcion) {
            console.log('❌ Inscripción sin cédula:', insc.idInscripcion);
            return false;
          }
          
          const cedulaInscNormalizada = normalizarCedula(cedulaInscripcion);
          const match = cedulaInscNormalizada === cedulaUsuarioNormalizada;
          
          if (match) {
            console.log('✅ Inscripción encontrada - DETALLES COMPLETOS:', {
              id: insc.idInscripcion,
              cedulaInsc: cedulaInscripcion,
              cedulaUser: personaCedula,
              estado: insc.estadoPago,
              tieneCohorte: !!insc.idCohorte,
              cohorteCompleta: insc.idCohorte,
              nombreCohorte: getNombreCohorte(insc),
              nombreFormacion: getNombreFormacion(insc)
            });
            
            // Debug detallado de la estructura de cohorte
            if (insc.idCohorte) {
              console.log('🔍 DEBUG Cohorte:', {
                idCohorte: insc.idCohorte.idCohorte,
                nombreCohorte: insc.idCohorte.nombreCohorte,
                tieneFormacion: !!insc.idCohorte.idFormacion,
                formacion: insc.idCohorte.idFormacion
              });
            }
          }
          
          return match;
        });
      }
      
      // SOLUCIÓN MEJORADA: Usar los datos que YA VIENEN en la respuesta
      console.log('🎯 Procesando datos de formaciones con información disponible...');

      // Verificar qué datos de formación tenemos realmente
      misInscripcionesFiltradas.forEach((insc, index) => {
        console.log(`📝 Inscripción ${index + 1} - ANÁLISIS COMPLETO:`, {
          idInscripcion: insc.idInscripcion,
          estadoPago: insc.estadoPago,
          // Análisis de cohorte
          tieneCohorte: !!insc.idCohorte,
          cohorte: insc.idCohorte ? {
            id: insc.idCohorte.idCohorte,
            nombre: insc.idCohorte.nombreCohorte,
            // Análisis profundo de formación
            tieneFormacion: !!insc.idCohorte.idFormacion,
            formacion: insc.idCohorte.idFormacion ? {
              id: insc.idCohorte.idFormacion.idFormacion,
              nombre: insc.idCohorte.idFormacion.nombreFormacion,
              // Verificar todos los campos disponibles en idFormacion
              todosLosCampos: Object.keys(insc.idCohorte.idFormacion)
            } : 'NO HAY DATOS DE FORMACIÓN'
          } : 'NO HAY COHORTE',
          // Llamada a las funciones para ver qué devuelven
          resultadoGetNombreCohorte: getNombreCohorte(insc),
          resultadoGetNombreFormacion: getNombreFormacion(insc)
        });
        
        // Debug adicional: mostrar la estructura completa de la cohorte
        if (insc.idCohorte) {
          console.log(`🔍 ESTRUCTURA COMPLETA de cohorte para inscripción ${insc.idInscripcion}:`, JSON.stringify(insc.idCohorte, null, 2));
        }
      });

      setMisInscripciones(misInscripcionesFiltradas);
      console.log('✅ Mis inscripciones filtradas:', misInscripcionesFiltradas.length);

      // SOLUCIÓN TEMPORAL: Simular notas basadas en inscripciones
      const notasSimuladas = misInscripcionesFiltradas.map(insc => {
        const nombreCohorte = getNombreCohorte(insc);
        const nombreFormacion = getNombreFormacion(insc);
        
        console.log(`📋 Creando nota para inscripción ${insc.idInscripcion}:`, {
          nombreCohorte,
          nombreFormacion,
          estadoPago: insc.estadoPago,
          montoTotal: insc.montoTotal
        });
        
        return {
          idNota: insc.idInscripcion + 1000,
          totalNota: insc.montoTotal || insc.saldoPendiente || 100,
          descripcion: `Inscripción - ${nombreFormacion}`,
          estado: insc.estadoPago === 'PAGADO' ? 'PAGADA' : insc.estadoPago || 'PENDIENTE',
          fechaEmision: insc.fechaInscripcion,
          tipoOperacion: 'COBRO',
          tipoArticulo: 'INSCRIPCION',
          relaciones: [{
            idInscripcion: {
              idInscripcion: insc.idInscripcion,
              idCohorte: {
                idCohorte: insc.idCohorte?.idCohorte,
                nombreCohorte: nombreCohorte
              }
            }
          }]
        };
      });

      // Filtrar notas pendientes
      const notasPendientes = notasSimuladas.filter(nota => 
        nota.estado === 'PENDIENTE' || nota.estado === 'PARCIAL'
      );
      
      setNotasPorPagar(notasPendientes);
      console.log('📝 Notas por pagar (simuladas):', notasPendientes.length);

      // SOLUCIÓN TEMPORAL: Pagos vacíos por ahora
      setMisPagos([]);

      // Calcular estado de pagos basado en inscripciones
      const inscripcionesPagadas = misInscripcionesFiltradas.filter(insc => 
        insc.estadoPago === 'PAGADO'
      ).length;

      const inscripcionesPendientes = misInscripcionesFiltradas.filter(insc => 
        insc.estadoPago === 'PENDIENTE' || insc.estadoPago === 'PARCIAL'
      ).length;

      setEstadoPago({
        pagado: inscripcionesPagadas,
        pendiente: inscripcionesPendientes
      });

      console.log('🎯 Estado final:', {
        inscripciones: misInscripcionesFiltradas.length,
        notasPorPagar: notasPendientes.length,
        pagos: 0,
        inscripcionesPagadas: inscripcionesPagadas,
        inscripcionesPendientes: inscripcionesPendientes
      });

      // Si no hay inscripciones, mostrar mensaje
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
    // entrada animada suave
    Animated.stagger(90, cardsAnim.map(a => Animated.spring(a, { toValue: 1, useNativeDriver: true }))).start();
  }, []);

  // Cargar datos cuando el usuario esté disponible en el contexto
  useEffect(() => {
    if (user) {
      console.log('👤 Usuario disponible en contexto, cargando datos...');
      loadAllData();
    } else {
      console.log('⏳ Esperando usuario en contexto...');
      setLoading(true);
    }
  }, [user]);

  // Obtener la última inscripción
  const getUltimaInscripcion = () => {
    if (misInscripciones.length === 0) return null;
    
    const inscripcionesConFecha = misInscripciones.filter(insc => 
      insc.fechaInscripcion && insc.fechaInscripcion !== 'null'
    );
    
    if (inscripcionesConFecha.length === 0) return misInscripciones[0];
    
    return inscripcionesConFecha.reduce((latest, current) => {
      try {
        const latestDate = new Date(latest.fechaInscripcion);
        const currentDate = new Date(current.fechaInscripcion);
        return currentDate > latestDate ? current : latest;
      } catch {
        return latest;
      }
    });
  };

  // Obtener el último pago
  const getUltimoPago = () => {
    if (misPagos.length === 0) return null;
    
    const pagosConFecha = misPagos.filter(pago => 
      pago.fechaPago && pago.fechaPago !== 'null'
    );
    
    if (pagosConFecha.length === 0) return misPagos[0];
    
    return pagosConFecha.reduce((latest, current) => {
      try {
        const latestDate = new Date(latest.fechaPago);
        const currentDate = new Date(current.fechaPago);
        return currentDate > latestDate ? current : latest;
      } catch {
        return latest;
      }
    });
  };

  // Calcular monto total de notas por pagar
  const getMontoTotalPorPagar = () => {
    return notasPorPagar.reduce((total, nota) => total + (nota.totalNota || 0), 0);
  };

  const ultimaInscripcion = getUltimaInscripcion();
  const ultimoPago = getUltimoPago();
  const montoTotalPorPagar = getMontoTotalPorPagar();

  // Definir stats después de calcular todas las variables necesarias
  const stats = [
    {
      title: 'Mis Inscripciones',
      value: misInscripciones.length.toString(),
      icon: 'book-account',
      color: '#fb6340',
      subtitle: ultimaInscripcion 
        ? `${getNombreCohorte(ultimaInscripcion)} - ${ultimaInscripcion.estadoPago || 'Activa'}`
        : 'No tienes inscripciones',
    },
    {
      title: 'Mis Pagos',
      value: misPagos.length.toString(),
      icon: 'currency-usd',
      color: '#2dce89',
      subtitle: ultimoPago 
        ? `Último: ${formatDate(ultimoPago.fechaPago)} - $${ultimoPago.monto || 0}`
        : 'No hay pagos registrados',
    },
    {
      title: 'Estado de Pagos',
      value: estadoPago.pendiente === 0 ? 'Al día' : 'Pendiente',
      icon: 'clock-check',
      color: estadoPago.pendiente === 0 ? '#11cdef' : '#f7b731',
      subtitle: estadoPago.pendiente === 0 
        ? 'Todas las inscripciones pagadas' 
        : `${estadoPago.pendiente} inscripción(es) pendiente(s)`,
    },
    {
      title: 'Notas por Pagar',
      value: notasPorPagar.length.toString(),
      icon: 'note-alert',
      color: '#f5365c',
      subtitle: montoTotalPorPagar > 0 
        ? `Total: $${montoTotalPorPagar.toFixed(2)}` 
        : 'No hay notas pendientes',
    },
  ];

  // Función para recargar datos
  const handleRetry = () => {
    loadAllData();
  };

  // Mostrar loading mientras no hay usuario
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
          <TouchableOpacity 
              style={styles.retryButton}
              onPress={handleRetry}
            >
              <Icon name="reload" size={20} color="#fff" />
              <Text style={styles.retryButtonText}>Reintentar</Text>
            </TouchableOpacity>
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

        {/* Sección de acciones rápidas - CON CONTENEDOR */}
        <View style={styles.sectionContainer}>
          <Text style={styles.sectionTitle}>Acciones rápidas</Text>
          <View style={styles.actionsRow}>
            <TouchableOpacity 
              style={styles.actionButton} 
              onPress={() => navigation.navigate('Inscripciones')}
            >
              <Icon name="book-plus" size={22} color="#4f8cff" />
              <Text style={styles.actionButtonText}>Nueva Inscripción</Text>
            </TouchableOpacity>
            <TouchableOpacity 
              style={styles.actionButton} 
              onPress={() => navigation.navigate('Pagos')}
            >
              <Icon name="credit-card-check" size={22} color="#2dce89" />
              <Text style={styles.actionButtonText}>Realizar Pago</Text>
            </TouchableOpacity>
          </View>
        </View>

        {/* Detalle de notas por pagar */}
        {notasPorPagar.length > 0 && (
          <View style={styles.detailContainer}>
            <Text style={styles.detailTitle}>Notas por Pagar</Text>
            {notasPorPagar.map((nota, index) => (
              <View key={nota.idNota} style={styles.notaItem}>
                <View style={styles.notaHeader}>
                  <Text style={styles.notaDescripcion}>
                    {nota.descripcion || `Nota ${nota.idNota}`}
                  </Text>
                  <Text style={styles.notaMonto}>${nota.totalNota?.toFixed(2) || '0.00'}</Text>
                </View>
                <Text style={styles.notaDetalle}>
                  {getCohorteDeNota(nota)} • 
                  Emitida: {formatDate(nota.fechaEmision)} • 
                  Tipo: {nota.tipoArticulo || 'Cobro'}
                </Text>
              </View>
            ))}
          </View>
        )}

        {/* Detalle de inscripciones activas */}
        {misInscripciones.length > 0 && (
          <View style={styles.detailContainer}>
            <Text style={styles.detailTitle}>Mis Inscripciones Activas</Text>
            {misInscripciones.map((inscripcion, index) => (
              <View key={inscripcion.idInscripcion} style={styles.inscripcionItem}>
                <View style={styles.inscripcionHeader}>
                  <Text style={styles.inscripcionNombre}>
                    {getNombreCohorte(inscripcion)}
                  </Text>
                  <Text style={[
                    styles.inscripcionEstado,
                    { 
                      color: inscripcion.estadoPago === 'PAGADO' ? '#2dce89' : 
                            inscripcion.estadoPago === 'PARCIAL' ? '#f7b731' : '#fb6340'
                    }
                  ]}>
                    {inscripcion.estadoPago || 'PENDIENTE'}
                  </Text>
                </View>
                <Text style={styles.inscripcionFormacion}>
                  {getNombreFormacion(inscripcion)}
                </Text>
                <Text style={styles.inscripcionDetalle}>
                  Fecha: {formatDate(inscripcion.fechaInscripcion)} • 
                  {inscripcion.montoPagado ? ` Pagado: $${inscripcion.montoPagado}` : ''} • 
                  Saldo: ${inscripcion.saldoPendiente || inscripcion.montoTotal || '0.00'}
                </Text>
              </View>
            ))}
          </View>
        )}

        {/* Información adicional si no hay datos */}
        {(misInscripciones.length === 0 && misPagos.length === 0 && notasPorPagar.length === 0) && (
          <View style={styles.infoContainer}>
            <Icon name="information" size={32} color="#4f8cff" />
            <Text style={styles.infoTitle}>Bienvenido al sistema</Text>
            <Text style={styles.infoText}>
              {user?.displayName ? `${user.displayName}, ` : ''} 
              aún no tienes inscripciones, pagos ni notas registradas. 
              Puedes comenzar realizando una nueva inscripción.
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
  header: {
    backgroundColor: '#4f8cff',
    paddingTop: 48,
    paddingBottom: 20,
    paddingHorizontal: 24,
    borderBottomLeftRadius: 24,
    borderBottomRightRadius: 24,
    alignItems: 'flex-start',
    elevation: 8,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 8 },
    shadowOpacity: 0.18,
    shadowRadius: 12,
  },
  headerTitle: {
    color: '#fff',
    fontSize: 26,
    fontWeight: '800',
    letterSpacing: 0.3,
  },
  headerSubtitle: {
    color: '#e7f0ff',
    fontSize: 13,
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
    cursor: 'pointer',
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
    cursor: 'pointer',
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