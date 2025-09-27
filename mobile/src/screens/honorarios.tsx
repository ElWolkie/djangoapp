// src/screens/honorarios.tsx
import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  Animated,
  FlatList,
  ActivityIndicator,
  StyleSheet,
  Dimensions,
  TouchableOpacity,
  TextInput,
  ScrollView,
} from 'react-native';
import Icon from 'react-native-vector-icons/MaterialCommunityIcons';
import Modal from 'react-native-modal';
import api from '../api/api';

const { width } = Dimensions.get('window');
const CARD_WIDTH = width - 24;

/* TIPOS (simplificados) */
type Persona = { idPersona: number; cedula?: string; nombres?: string; apellidos?: string; };
type Cargo = { idCargo: number; nombreCargo?: string; nombre?: string; };
type Materia = { idMateria: number; nombreMateria?: string; nombre?: string; };
type Cohorte = { idCohorte: number; nombreCohorte?: string; };

type HonorarioRaw = {
  idHonorario: number;
  idPersona: number | Persona | null;
  idCargo: number | Cargo | null;
  idCohorte: number | Cohorte | null;
  idMateria: number | Materia | null;
  horas?: number;
  estadoHonorario?: string;
  fechaHonorario?: string;
  monto?: number | string; // puede venir como string también
  // a veces la API puede devolver nombres alternativos (montoHonorario, valor, total, etc.)
  [k: string]: any;
};

export default function PantallaHonorarios() {
  const [honorarios, setHonorarios] = useState<HonorarioRaw[]>([]);
  const [mostradas, setMostradas] = useState<HonorarioRaw[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchText, setSearchText] = useState('');
  const [modalVisible, setModalVisible] = useState(false);
  const [selected, setSelected] = useState<HonorarioRaw | null>(null);
  const [animValues, setAnimValues] = useState<Animated.Value[]>([]);

  // Helper: safe extractor para nombres/campos con variantes
  const firstField = (obj: any, candidates: string[]) => {
    if (!obj || typeof obj !== 'object') return null;
    for (const c of candidates) {
      if (obj[c] !== undefined && obj[c] !== null && String(obj[c]).trim() !== '') return String(obj[c]);
    }
    return null;
  };

  // Busca un campo numérico entre candidatos (top-level y dentro de objetos)
  const resolveNumberField = (root: any, candidates: string[]) : number | null => {
    if (!root) return null;
    // 1) si root es un número directo (p.ej. honorario.monto)
    if (typeof root === 'number') return root;
    // 2) si root es string numérico
    if (typeof root === 'string' && root.trim() !== '' && !isNaN(Number(root))) {
      return Number(root);
    }
    // 3) si root es objeto, buscar candidatos dentro
    if (typeof root === 'object') {
      for (const c of candidates) {
        const val = (root as any)[c];
        if (val === undefined || val === null) continue;
        if (typeof val === 'number') return val;
        if (typeof val === 'string' && val.trim() !== '' && !isNaN(Number(val))) return Number(val);
      }
    }
    // 4) también revisar top-level (cuando root es el objeto honorario)
    if (typeof root === 'object') {
      for (const c of candidates) {
        const val = (root as any)[c];
        if (val === undefined || val === null) continue;
        if (typeof val === 'number') return val;
        if (typeof val === 'string' && val.trim() !== '' && !isNaN(Number(val))) return Number(val);
      }
    }
    return null;
  };

  const formatDate = (dateStr?: string | null) => {
    if (!dateStr) return '—';
    try {
      const d = new Date(dateStr);
      if (isNaN(d.getTime())) {
        const m = String(dateStr).match(/(\d{4})-(\d{2})-(\d{2})/);
        if (m) return `${m[3]}/${m[2]}/${m[1]}`;
        return String(dateStr);
      }
      const dd = String(d.getDate()).padStart(2, '0');
      const mm = String(d.getMonth() + 1).padStart(2, '0');
      const yyyy = d.getFullYear();
      return `${dd}/${mm}/${yyyy}`;
    } catch {
      return String(dateStr);
    }
  };

  useEffect(() => {
    const fetchAll = async () => {
      setLoading(true);
      try {
        const [hRes, personasRes, cargosRes, materiasRes, cohortesRes] = await Promise.all([
          api.get<HonorarioRaw[]>('/api/honorario/'),
          api.get<Persona[]>('/api/personas/'),
          api.get<Cargo[]>('/api/cargo/'),
          api.get<Materia[]>('/api/materias/'),
          api.get<Cohorte[]>('/api/cohorte/'),
        ]);

        const rawHonorarios = hRes.data ?? [];
        const personas = personasRes.data ?? [];
        const cargos = cargosRes.data ?? [];
        const materias = materiasRes.data ?? [];
        const cohortes = cohortesRes.data ?? [];

        // Mapas por id
        const personaMap = new Map<number, Persona>(personas.map(p => [p.idPersona, p]));
        const cargoMap = new Map<number, Cargo>(cargos.map(c => [(c as any).idCargo, c]));
        const materiaMap = new Map<number, Materia>(materias.map(m => [(m as any).idMateria, m]));
        const cohorteMap = new Map<number, Cohorte>(cohortes.map(co => [(co as any).idCohorte, co]));

        // Reemplazamos ids por objetos cuando sea necesario y resolvemos montos alternativos
        const enriched: HonorarioRaw[] = rawHonorarios.map(h => {
          const personaVal = (typeof h.idPersona === 'object' || h.idPersona === null)
            ? h.idPersona
            : personaMap.get(Number(h.idPersona)) ?? null;
          const cargoVal = (typeof h.idCargo === 'object' || h.idCargo === null)
            ? h.idCargo
            : cargoMap.get(Number(h.idCargo)) ?? null;
          const materiaVal = (typeof h.idMateria === 'object' || h.idMateria === null)
            ? h.idMateria
            : materiaMap.get(Number(h.idMateria)) ?? null;
          const cohorteVal = (typeof h.idCohorte === 'object' || h.idCohorte === null)
            ? h.idCohorte
            : cohorteMap.get(Number(h.idCohorte)) ?? null;

          // Intentar resolver monto: candidatos comunes
          const montoCandidates = ['monto','montoHonorario','valor','total','monto_total','monto_honorario'];
          const montoResolved = resolveNumberField(h, montoCandidates) ?? resolveNumberField(personaVal, montoCandidates) ?? null;

          return {
            ...h,
            idPersona: personaVal,
            idCargo: cargoVal,
            idMateria: materiaVal,
            idCohorte: cohorteVal,
            monto: montoResolved ?? undefined,
          };
        });

        // console.log('enriched honorarios sample', enriched[0]);

        setHonorarios(enriched);
        setMostradas(enriched);
      } catch (err: any) {
        console.warn('Error fetching honorarios/resources', err);
        setError(err?.message ?? 'Error al cargar datos');
      } finally {
        setLoading(false);
      }
    };

    fetchAll();
  }, []);

  // filtrado simple: busca por cédula, cargo, materia o estado
  useEffect(() => {
    const q = searchText.toLowerCase();
    const filtered = honorarios.filter(h => {
      const cedula = firstField(h.idPersona, ['cedula']) ?? '';
      const cargoName = firstField(h.idCargo, ['nombreCargo','nombre']) ?? '';
      const materiaName = firstField(h.idMateria, ['nombreMateria','nombre']) ?? '';
      const cohorteName = firstField(h.idCohorte, ['nombreCohorte','nombre']) ?? '';
      const estado = (h.estadoHonorario ?? '').toString();
      return (
        cedula.toLowerCase().includes(q) ||
        cargoName.toLowerCase().includes(q) ||
        materiaName.toLowerCase().includes(q) ||
        cohorteName.toLowerCase().includes(q) ||
        estado.toLowerCase().includes(q)
      );
    });
    setMostradas(filtered);
  }, [searchText, honorarios]);

  useEffect(() => {
    const values = mostradas.map(() => new Animated.Value(0));
    setAnimValues(values);
  }, [mostradas]);

  useEffect(() => {
    if (animValues.length > 0) {
      Animated.stagger(80, animValues.map(a => Animated.spring(a, { toValue: 1, useNativeDriver: false }))).start();
    }
  }, [animValues]);

  const openModal = (h: HonorarioRaw) => {
    setSelected(h);
    setModalVisible(true);
  };

  const renderItem = ({ item, index }: { item: HonorarioRaw; index: number }) => {
    const anim = animValues[index] || new Animated.Value(1);

    const cedula = firstField(item.idPersona, ['cedula']) ?? '—';
    const cargoName = firstField(item.idCargo, ['nombreCargo','nombre']) ?? 'DOCENTE';
    const materiaName = firstField(item.idMateria, ['nombreMateria','nombre']) ?? '—';
    const cohorteName = firstField(item.idCohorte, ['nombreCohorte','nombre']) ?? '—';
    const montoVal = resolveNumberField(item, ['monto','montoHonorario','valor','total','monto_total','monto_honorario']);
    const montoStr = typeof montoVal === 'number' ? `$${montoVal.toFixed(2)}` : '—';
    const fechaStr = formatDate(item.fechaHonorario);

    return (
      <Animated.View
        style={[
          styles.card,
          {
            opacity: anim,
            transform: [{ translateY: anim.interpolate({ inputRange: [0,1], outputRange: [20,0] }) }],
          }
        ]}
      >
        <View style={styles.header}>
          <Text style={styles.name}>{cargoName}</Text>
          <View style={[ styles.badge, (item.estadoHonorario === 'ACTIVO' ? styles.badgeActive : styles.badgeInactive) ]}>
            <Text style={styles.badgeText}>{item.estadoHonorario === 'ACTIVO' ? 'Activo' : (item.estadoHonorario ?? '—')}</Text>
          </View>
        </View>

        <View style={styles.row}>
          <Icon name="id-card" size={16} />
          <Text style={styles.detailText}>Cédula: {cedula}</Text>
        </View>

        <View style={styles.row}>
          <Icon name="book-open" size={16} />
          <Text style={styles.detailText}>Materia: {materiaName}</Text>
        </View>

        <View style={styles.row}>
          <Icon name="cash" size={16} />
          <Text style={styles.detailText}>Monto: {montoStr}</Text>
        </View>

        <View style={styles.row}>
          <Icon name="domain" size={16} />
          <Text style={styles.detailText}>Cohorte: {cohorteName}</Text>
        </View>

        <Text style={styles.dateText}>Registrado: {fechaStr}</Text>

        <TouchableOpacity style={styles.button} onPress={() => openModal(item)}>
          <Icon name="chevron-right" size={24} color="#fff" />
        </TouchableOpacity>
      </Animated.View>
    );
  };

  // filas modal (preparadas fuera del JSX)
  const modalRows = selected ? [
    ['Cédula', firstField(selected.idPersona, ['cedula']) ?? '—'],
    ['Nombres', firstField(selected.idPersona, ['nombres','nombre']) ?? '—'],
    ['Apellidos', firstField(selected.idPersona, ['apellidos','apellido']) ?? '—'],
    ['Materia', firstField(selected.idMateria, ['nombreMateria','nombre']) ?? '—'],
    ['Horas', selected.horas !== undefined ? String(selected.horas) : '—'],
    ['Monto', (() => {
      const m = resolveNumberField(selected, ['monto','montoHonorario','valor','total','monto_total','monto_honorario']);
      return m !== null ? `$${m.toFixed(2)}` : '—';
    })()],
    ['Cohorte', firstField(selected.idCohorte, ['nombreCohorte','nombre']) ?? '—'],
    ['Estado', selected.estadoHonorario ?? '—'],
    ['Fecha', formatDate(selected.fechaHonorario)],
  ] as [string,string][] : [];

  if (loading) {
    return <View style={styles.center}><ActivityIndicator size="large" color="#4f8cff" /></View>;
  }

  if (error) {
    return <View style={styles.center}><Text style={styles.errorText}>{error}</Text></View>;
  }

  return (
    <View style={styles.container}>
      <Text style={styles.title}>Honorarios</Text>

      <View style={styles.searchWrapper}>
        <Icon name="magnify" size={24} />
        <TextInput
          placeholder="Buscar por cédula, cargo, materia, cohorte o estado..."
          value={searchText}
          onChangeText={setSearchText}
          style={styles.searchInput}
          clearButtonMode="while-editing"
        />
      </View>

      <FlatList
        data={mostradas}
        keyExtractor={(h) => h.idHonorario.toString()}
        renderItem={renderItem}
        contentContainerStyle={{ paddingBottom: 24 }}
        showsVerticalScrollIndicator={false}
        ListEmptyComponent={<Text style={styles.emptyText}>No hay resultados.</Text>}
      />

      <Modal
        isVisible={modalVisible}
        onBackdropPress={() => setModalVisible(false)}
        animationIn="slideInUp"
        animationOut="slideOutDown"
        backdropOpacity={0.5}
        useNativeDriver
      >
        <View style={styles.modalContent}>
          <ScrollView>
            <Text style={styles.modalTitle}>{ firstField(selected?.idCargo, ['nombreCargo','nombre']) ?? 'DOCENTE' }</Text>

            {modalRows.map(([lbl, val]) => (
              <View key={lbl} style={styles.detailRow}>
                <Text style={styles.detailLabel}>{lbl}:</Text>
                <Text style={styles.detailValue}>{val}</Text>
              </View>
            ))}
          </ScrollView>

          <TouchableOpacity style={styles.modalClose} onPress={() => setModalVisible(false)}>
            <Text style={styles.modalCloseText}>Cerrar</Text>
          </TouchableOpacity>
        </View>
      </Modal>
    </View>
  );
}

const styles = StyleSheet.create({
  center: { flex: 1, justifyContent: 'center', alignItems: 'center' },
  errorText: { color: 'red', fontSize: 16 },
  container: { flex: 1, paddingTop: 16, backgroundColor: '#f5f7fa' },
  title: { fontSize: 26, fontWeight: '700', color: '#4f8cff', textAlign: 'center', marginBottom: 12 },
  searchWrapper: {
    flexDirection: 'row',
    backgroundColor: '#fff',
    marginHorizontal: 12,
    borderRadius: 8,
    alignItems: 'center',
    paddingHorizontal: 12,
    elevation: 2,
    height: 48,
    marginBottom: 12,
  },
  searchInput: { flex: 1, fontSize: 16, marginLeft: 8 },
  card: {
    width: CARD_WIDTH,
    backgroundColor: '#fff',
    borderRadius: 16,
    padding: 16,
    marginHorizontal: 12,
    marginVertical: 8,
    shadowColor: '#000',
    shadowOpacity: 0.1,
    shadowOffset: { width: 0, height: 4 },
    shadowRadius: 8,
    elevation: 4,
    position: 'relative',
  },
  header: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 },
  name: { fontSize: 18, fontWeight: '600', color: '#222', flex: 1 },
  badge: { paddingHorizontal: 8, paddingVertical: 4, borderRadius: 12 },
  badgeActive: { backgroundColor: '#2dce89' },
  badgeInactive: { backgroundColor: '#f5365c' },
  badgeText: { color: '#fff', fontSize: 12, fontWeight: '600' },
  row: { flexDirection: 'row', alignItems: 'center', marginBottom: 6 },
  detailText: { marginLeft: 8, fontSize: 16, color: '#525f7f', flex: 1 },
  dateText: { fontSize: 14, color: '#8898aa', marginTop: 8 },
  button: {
    position: 'absolute',
    right: 12,
    bottom: 12,
    backgroundColor: '#4f8cff',
    width: 40,
    height: 40,
    borderRadius: 20,
    justifyContent: 'center',
    alignItems: 'center',
  },
  emptyText: { marginTop: 20, textAlign: 'center', color: '#666', fontStyle: 'italic', fontSize: 16 },
  modalContent: { backgroundColor: '#fff', borderRadius: 16, padding: 16, maxHeight: '80%' },
  modalTitle: { fontSize: 20, fontWeight: '700', color: '#4f8cff', marginBottom: 12, textAlign: 'center' },
  detailRow: { flexDirection: 'row', marginBottom: 10 },
  detailLabel: { width: 100, fontWeight: '600', fontSize: 16, color: '#525f7f' },
  detailValue: { flex: 1, fontSize: 16, color: '#333' },
  modalClose: {
    marginTop: 12,
    alignSelf: 'center',
    backgroundColor: '#4f8cff',
    paddingHorizontal: 24,
    paddingVertical: 10,
    borderRadius: 24,
  },
  modalCloseText: { color: '#fff', fontWeight: '600', fontSize: 16 },
});
