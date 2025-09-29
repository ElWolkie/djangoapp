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
} from 'react-native';
import { useNavigation, NavigationProp } from '@react-navigation/native';
import Icon from 'react-native-vector-icons/MaterialCommunityIcons';
import AsyncStorage from '@react-native-async-storage/async-storage';
import api from '../api/api'; // asegúrate que esta ruta coincide con la tuya

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
};

export default function DashboardScreen() {
  const navigation = useNavigation<NavigationProp<RootStackParamList>>();

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

  // Datos en tiempo real
  const [solicitudesCount, setSolicitudesCount] = useState<number | null>(null);
  const [solicitudesLastDate, setSolicitudesLastDate] = useState<string | null>(null);

  const [serviciosCount, setServiciosCount] = useState<number | null>(null);
  const [serviciosTop, setServiciosTop] = useState<string | null>(null);

  const [honorariosCount, setHonorariosCount] = useState<number | null>(null);
  const [honorariosHoras, setHonorariosHoras] = useState<number | null>(null);

  const [cohortesCount, setCohortesCount] = useState<number | null>(null);
  const [cohortesRecent, setCohortesRecent] = useState<string | null>(null);

  // Saludo dinámico
  const [greeting, setGreeting] = useState<{ title: string; emoji: string }>(() => ({ title: '¡Bienvenido!', emoji: '👋' }));

  useEffect(() => {
    const h = new Date().getHours();
    if (h >= 5 && h < 12) setGreeting({ title: '¡Buenos días!', emoji: '🌞' });
    else if (h >= 12 && h < 19) setGreeting({ title: '¡Buenas tardes!', emoji: '🌤️' });
    else setGreeting({ title: '¡Buenas noches!', emoji: '🌙' });
  }, []);

  // Helpers para fechas y extracción
  const tryParseDate = (v: any): Date | null => {
    if (!v && v !== 0) return null;
    try {
      if (v instanceof Date) return v;
      const s = String(v);
      const d = new Date(s);
      if (!isNaN(d.getTime())) return d;
      const m = s.match(/(\d{4})-(\d{2})-(\d{2})/);
      if (m) return new Date(`${m[1]}-${m[2]}-${m[3]}T00:00:00`);
      return null;
    } catch {
      return null;
    }
  };

  const formatDate = (d?: string | Date | null) => {
    const dt = typeof d === 'string' ? tryParseDate(d) : (d instanceof Date ? d : tryParseDate(d));
    if (!dt) return '—';
    const dd = String(dt.getDate()).padStart(2, '0');
    const mm = String(dt.getMonth() + 1).padStart(2, '0');
    const yyyy = dt.getFullYear();
    return `${dd}/${mm}/${yyyy}`;
  };

  const mostFrequent = (arr: string[]) => {
    if (!arr || arr.length === 0) return null;
    const freq: Record<string, number> = {};
    for (const v of arr) {
      const k = (v ?? '—').toString();
      freq[k] = (freq[k] || 0) + 1;
    }
    let best = arr[0];
    let bestCount = 0;
    for (const [k, c] of Object.entries(freq)) {
      if (c > bestCount) { best = k; bestCount = c; }
    }
    return best;
  };

  useEffect(() => {
    // entrada animada suave
    Animated.stagger(90, cardsAnim.map(a => Animated.spring(a, { toValue: 1, useNativeDriver: true }))).start();
  }, []);

  useEffect(() => {
    const fetchData = async () => {
      setLoading(true);
      setError(null);
      try {
        const [solRes, servRes, honRes, cohRes] = await Promise.all([
          api.get('/api/solicitud/').catch(() => ({ data: [] })),
          api.get('/api/servicio/').catch(() => ({ data: [] })),
          api.get('/api/honorario/').catch(() => ({ data: [] })),
          api.get('/api/cohorte/').catch(() => ({ data: [] })),
        ]);

        const solicitudes = Array.isArray(solRes.data) ? solRes.data : [];
        const servicios = Array.isArray(servRes.data) ? servRes.data : [];
        const honorarios = Array.isArray(honRes.data) ? honRes.data : [];
        const cohortes = Array.isArray(cohRes.data) ? cohRes.data : [];

        // SOLICITUDES: contar activas (fallback)
        const solicitudesActivas = solicitudes.filter((s: any) => {
          if (typeof s.is_active === 'boolean') return s.is_active === true;
          const estado = (s.estadoSolicitud ?? s.estado ?? '').toString().toUpperCase();
          if (estado) return estado !== 'INACTIVO' && estado !== 'CANCELADO';
          return true;
        });
        setSolicitudesCount(solicitudesActivas.length);

        // fecha más reciente
        const solicitudDates: Date[] = [];
        const candidateKeys = ['fechaSolicitud','fecha','fechaRegistro','created','created_at','fecha_solicitud'];
        for (const s of solicitudes) {
          for (const k of candidateKeys) {
            const d = tryParseDate((s as any)[k]);
            if (d) solicitudDates.push(d);
          }
        }
        const latestSolicitud = solicitudDates.length ? new Date(Math.max(...solicitudDates.map(d => d.getTime()))) : null;
        setSolicitudesLastDate(latestSolicitud ? formatDate(latestSolicitud) : null);

        // SERVICIOS: activos + top
        const serviciosActivos = servicios.filter((s: any) => {
          if (typeof s.is_active === 'boolean') return s.is_active === true;
          const estado = (s.estadoServicio ?? s.estado ?? '').toString().toUpperCase();
          if (estado) return estado !== 'INACTIVO' && estado !== 'CANCELADO';
          return true;
        });
        setServiciosCount(serviciosActivos.length);
        const servicioNames = servicios.map((s: any) => (s.nombreServicio ?? s.nombre ?? s.title ?? '—').toString());
        setServiciosTop(mostFrequent(servicioNames) ?? null);

        // HONORARIOS: cantidad y horas
        setHonorariosCount(honorarios.length);
        const totalHoras = honorarios.reduce((acc: number, h: any) => {
          const cand = h.horas ?? h.horasHonorario ?? h.horas_totales ?? h.hours ?? 0;
          const num = (typeof cand === 'number') ? cand : (cand ? Number(cand) : 0);
          return acc + (isNaN(num) ? 0 : num);
        }, 0);
        setHonorariosHoras(totalHoras);

        // COHORTES: cantidad y reciente
        setCohortesCount(cohortes.length);
        let bestCoh: { date?: Date | null, name?: string } | null = null;
        for (const c of cohortes) {
          const date = tryParseDate(c.fechaCohorte ?? c.fecha ?? c.fecha_creacion ?? c.created_at);
          const name = (c.nombreCohorte ?? c.nombre ?? c.title ?? '—').toString();
          if (!bestCoh || (date && bestCoh.date && date.getTime() > bestCoh.date.getTime()) || (date && !bestCoh.date)) {
            bestCoh = { date, name };
          }
        }
        setCohortesRecent(bestCoh?.name ?? null);
      } catch (err: any) {
        console.warn('Dashboard fetch error', err);
        setError(err?.message ?? 'Error al cargar datos del dashboard');
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, []);

  const stats = [
    {
      title: 'Solicitudes activas',
      value: solicitudesCount ?? '—',
      icon: 'file-document-multiple',
      color: '#fb6340',
      subtitle: solicitudesLastDate ? `Último registro: ${solicitudesLastDate}` : 'Último registro: —',
    },
    {
      title: 'Servicios activos',
      value: serviciosCount ?? '—',
      icon: 'truck-fast',
      color: '#2dce89',
      subtitle: serviciosTop ? `Más pedido: ${serviciosTop}` : 'Más pedido: —',
    },
    {
      title: 'Honorarios',
      value: honorariosCount ?? '—',
      icon: 'currency-usd',
      color: '#f7b731',
      subtitle: honorariosHoras !== null ? `${honorariosHoras}h Horas totales` : 'Horas totales: —',
    },
    {
      title: 'Cohortes',
      value: cohortesCount ?? '—',
      icon: 'calendar-multiple',
      color: '#4f8cff',
      subtitle: cohortesRecent ? `${cohortesRecent} — Más reciente` : 'Más reciente: —',
    },
  ];
    // Nombre del usuario para mostrar en el header
  const [userNameDisplay, setUserNameDisplay] = useState<string | null>(null);

  useEffect(() => {
    const loadUserName = async () => {
      try {
        const raw = await AsyncStorage.getItem('myapp-user');
        if (!raw) return;
        const parsed = JSON.parse(raw);
        if (parsed?.displayName) setUserNameDisplay(parsed.displayName);
      } catch (e) {
        // noop
      }
    };
    loadUserName();
  }, []);


  if (loading) {
    return (
      <View style={styles.container}>
        <StatusBar barStyle="light-content" backgroundColor="#4f8cff" />
        <View style={styles.header}>
          <Text style={styles.headerTitle}>{greeting.emoji} {greeting.title}{userNameDisplay ? ` — ${userNameDisplay}` : ''}</Text>
          <Text style={styles.headerSubtitle}>Resumen administrativo • {formatDate(new Date())}</Text>
        </View>
        <View style={{ flex: 1, justifyContent: 'center', alignItems: 'center' }}>
          <ActivityIndicator size="large" color="#4f8cff" />
          <Text style={{ marginTop: 12, color: '#666' }}>Cargando datos...</Text>
        </View>
      </View>
    );
  }

  if (error) {
    return (
      <View style={styles.container}>
        <StatusBar barStyle="light-content" backgroundColor="#4f8cff" />
        <View style={styles.header}>
          <Text style={styles.headerTitle}>{greeting.emoji} {greeting.title}{userNameDisplay ? ` — ${userNameDisplay}` : ''}</Text>
          <Text style={styles.headerSubtitle}>Resumen administrativo • {formatDate(new Date())}</Text>
        </View>
        <View style={{ flex: 1, justifyContent: 'center', alignItems: 'center', paddingHorizontal: 20 }}>
          <Text style={{ color: 'red', fontWeight: '700', marginBottom: 8 }}>Error al cargar datos</Text>
          <Text style={{ color: '#666', textAlign: 'center' }}>{error}</Text>
        </View>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <StatusBar barStyle="light-content" backgroundColor="#4f8cff" />
      <View style={styles.header}>
        <Text style={styles.headerTitle}>{greeting.emoji} {greeting.title}{userNameDisplay ? ` — ${userNameDisplay}` : ''}</Text>
        <Text style={styles.headerSubtitle}>Resumen administrativo • {formatDate(new Date())}</Text>
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
          <Text style={styles.sectionTitle}>Atajos rápidos</Text>
          <View style={{ flexDirection: 'row', gap: 10 }}>
            <View style={[styles.sectionButton, { marginRight: 10 }]}>
              <Icon name="account-group" size={18} color="#fff" />
              <Text style={[styles.sectionButtonText, { marginLeft: 8 }]}>Personas</Text>
            </View>
            <View style={styles.sectionButton}>
              <Icon name="school" size={18} color="#fff" />
              <Text style={[styles.sectionButtonText, { marginLeft: 8 }]}>Formaciones</Text>
            </View>
          </View>
        </View>
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
    marginBottom: 8,
  },
  sectionButton: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#4f8cff',
    paddingVertical: 8,
    paddingHorizontal: 12,
    borderRadius: 20,
    marginTop: 6,
  },
  sectionButtonText: {
    color: '#fff',
    fontWeight: '700',
    fontSize: 14,
  },
});
