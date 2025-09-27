// src/screens/inscripciones.tsx
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
type Formacion = { idFormacion: number; nombreFormacion?: string; valorInscripcion?: number; };
type Cohorte = { idCohorte: number; nombreCohorte?: string; };

type InscripcionRaw = {
  idInscripcion: number;
  idPersona: number | Persona | null;
  idCohorte: number | Cohorte | null;
  idTF?: any;
  idFormacion: number | Formacion | null;
  fechaInscripcion?: string;
  estadoPago?: string;
  montoPagado?: number | string;
  montoTotal?: number | null;
  saldoPendiente?: number | null;
  is_active?: boolean;
  [k: string]: any;
};

export default function PantallaInscripciones() {
  const [items, setItems] = useState<InscripcionRaw[]>([]);
  const [mostradas, setMostradas] = useState<InscripcionRaw[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchText, setSearchText] = useState('');
  const [modalVisible, setModalVisible] = useState(false);
  const [selected, setSelected] = useState<InscripcionRaw | null>(null);
  const [animValues, setAnimValues] = useState<Animated.Value[]>([]);

  const firstField = (obj: any, candidates: string[]) => {
    if (!obj || typeof obj !== 'object') return null;
    for (const c of candidates) {
      if (obj[c] !== undefined && obj[c] !== null && String(obj[c]).trim() !== '') return String(obj[c]);
    }
    return null;
  };

  const resolveNumberField = (root: any, candidates: string[]): number | null => {
    if (!root) return null;
    if (typeof root === 'number') return root;
    if (typeof root === 'string' && root.trim() !== '' && !isNaN(Number(root))) return Number(root);
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
        const [resIns, resPersonas, resFormaciones, resCohortes] = await Promise.all([
          api.get<InscripcionRaw[]>('/api/inscripcion/'),
          api.get<Persona[]>('/api/personas/'),
          api.get<Formacion[]>('/api/formaciones/'),
          api.get<Cohorte[]>('/api/cohorte/'),
        ]);

        const raw = resIns.data ?? [];
        const personas = resPersonas.data ?? [];
        const formaciones = resFormaciones.data ?? [];
        const cohortes = resCohortes.data ?? [];

        const personaMap = new Map<number, Persona>(personas.map(p => [p.idPersona, p]));
        const formMap = new Map<number, Formacion>(formaciones.map(f => [f.idFormacion, f]));
        const cohMap = new Map<number, Cohorte>(cohortes.map(c => [c.idCohorte, c]));

        const enriched: InscripcionRaw[] = raw.map(r => {
          const personaVal = (typeof r.idPersona === 'object' || r.idPersona === null) ? r.idPersona : personaMap.get(Number(r.idPersona)) ?? null;
          const formVal = (typeof r.idFormacion === 'object' || r.idFormacion === null) ? r.idFormacion : formMap.get(Number(r.idFormacion)) ?? null;
          const cohVal = (typeof r.idCohorte === 'object' || r.idCohorte === null) ? r.idCohorte : cohMap.get(Number(r.idCohorte)) ?? null;

          // resolver números
          const montoPagado = resolveNumberField(r, ['montoPagado','monto_pagado','pagado']) ?? resolveNumberField(r.idFormacion, ['valorInscripcion','valor']) ?? 0;
          const montoTotal = r.montoTotal ?? ( (r as any).montoTotal ?? null );
          const saldo = r.saldoPendiente ?? ( (r as any).saldoPendiente ?? null );

          return {
            ...r,
            idPersona: personaVal,
            idFormacion: formVal,
            idCohorte: cohVal,
            montoPagado,
            montoTotal,
            saldoPendiente: saldo,
          };
        });

        setItems(enriched);
        setMostradas(enriched);
      } catch (err: any) {
        console.warn('Error inscripciones:', err);
        setError(err?.message ?? 'Error al cargar inscripciones');
      } finally {
        setLoading(false);
      }
    };

    fetchAll();
  }, []);

  useEffect(() => {
    const q = searchText.toLowerCase();
    const filt = items.filter(i => {
      const cedula = firstField(i.idPersona, ['cedula']) ?? '';
      const formName = firstField(i.idFormacion, ['nombreFormacion','nombre']) ?? '';
      const cohName = firstField(i.idCohorte, ['nombreCohorte','nombre']) ?? '';
      const estado = (i.estadoPago ?? '').toString();
      return (
        cedula.toLowerCase().includes(q) ||
        formName.toLowerCase().includes(q) ||
        cohName.toLowerCase().includes(q) ||
        estado.toLowerCase().includes(q)
      );
    });
    setMostradas(filt);
  }, [searchText, items]);

  useEffect(() => {
    setAnimValues(mostradas.map(() => new Animated.Value(0)));
  }, [mostradas]);

  useEffect(() => {
    if (animValues.length > 0) {
      Animated.stagger(80, animValues.map(a => Animated.spring(a, { toValue: 1, useNativeDriver: false }))).start();
    }
  }, [animValues]);

  const openModal = (it: InscripcionRaw) => {
    setSelected(it);
    setModalVisible(true);
  };

  const renderItem = ({ item, index }: { item: InscripcionRaw; index: number }) => {
    const anim = animValues[index] || new Animated.Value(1);
    const cedula = firstField(item.idPersona, ['cedula']) ?? '—';
    const formName = firstField(item.idFormacion, ['nombreFormacion','nombre']) ?? '—';
    const cohName = firstField(item.idCohorte, ['nombreCohorte','nombre']) ?? '—';
    const montoPagado = typeof item.montoPagado === 'number' ? `$${item.montoPagado.toFixed(2)}` : ( item.montoPagado ? `$${Number(item.montoPagado).toFixed(2)}` : '—' );
    const saldo = typeof item.saldoPendiente === 'number' ? `$${item.saldoPendiente.toFixed(2)}` : ( item.saldoPendiente ? `$${Number(item.saldoPendiente).toFixed(2)}` : '—' );
    const fecha = formatDate(item.fechaInscripcion);

    return (
      <Animated.View style={[styles.card, { opacity: anim, transform: [{ translateY: anim.interpolate({ inputRange: [0,1], outputRange: [20,0] }) }] }]}>
        <View style={styles.header}>
          <Text style={styles.name}>{formName}</Text>
          <View style={[ styles.badge, (item.estadoPago === 'PAGADO' ? styles.badgeActive : styles.badgeInactive) ]}>
            <Text style={styles.badgeText}>{item.estadoPago ?? '—'}</Text>
          </View>
        </View>

        <View style={styles.row}>
          <Icon name="id-card" size={16} />
          <Text style={styles.detailText}>Cédula: {cedula}</Text>
        </View>

        <View style={styles.row}>
          <Icon name="domain" size={16} />
          <Text style={styles.detailText}>Cohorte: {cohName}</Text>
        </View>

        <View style={styles.row}>
          <Icon name="cash" size={16} />
          <Text style={styles.detailText}>Pagado: {montoPagado} — Saldo: {saldo}</Text>
        </View>

        <Text style={styles.dateText}>Registrado: {fecha}</Text>

        <TouchableOpacity style={styles.button} onPress={() => openModal(item)}>
          <Icon name="chevron-right" size={24} color="#fff" />
        </TouchableOpacity>
      </Animated.View>
    );
  };

  const modalRows = selected ? [
    ['Cédula', firstField(selected.idPersona, ['cedula']) ?? '—'],
    ['Nombres', firstField(selected.idPersona, ['nombres','nombre']) ?? '—'],
    ['Apellidos', firstField(selected.idPersona, ['apellidos','apellido']) ?? '—'],
    ['Formación', firstField(selected.idFormacion, ['nombreFormacion','nombre']) ?? '—'],
    ['Cohorte', firstField(selected.idCohorte, ['nombreCohorte','nombre']) ?? '—'],
    ['Fecha inscripción', formatDate(selected.fechaInscripcion)],
    ['Estado pago', selected.estadoPago ?? '—'],
    ['Monto pagado', selected.montoPagado !== undefined ? (typeof selected.montoPagado === 'number' ? `$${selected.montoPagado.toFixed(2)}` : `$${Number(selected.montoPagado).toFixed(2)}`) : '—'],
    ['Monto total', selected.montoTotal !== undefined && selected.montoTotal !== null ? `$${Number(selected.montoTotal).toFixed(2)}` : '—'],
    ['Saldo pendiente', selected.saldoPendiente !== undefined && selected.saldoPendiente !== null ? `$${Number(selected.saldoPendiente).toFixed(2)}` : '—'],
    ['Activo', selected.is_active ? 'Sí' : 'No'],
  ] as [string,string][] : [];

  if (loading) return <View style={styles.center}><ActivityIndicator size="large" color="#4f8cff" /></View>;
  if (error) return <View style={styles.center}><Text style={styles.errorText}>{error}</Text></View>;

  return (
    <View style={styles.container}>
      <Text style={styles.title}>Inscripciones</Text>

      <View style={styles.searchWrapper}>
        <Icon name="magnify" size={24} />
        <TextInput placeholder="Buscar por cédula, formación, cohorte o estado..." value={searchText} onChangeText={setSearchText} style={styles.searchInput} clearButtonMode="while-editing" />
      </View>

      <FlatList data={mostradas} keyExtractor={(i) => i.idInscripcion.toString()} renderItem={renderItem} contentContainerStyle={{ paddingBottom: 24 }} showsVerticalScrollIndicator={false} ListEmptyComponent={<Text style={styles.emptyText}>No hay resultados.</Text>} />

      <Modal isVisible={modalVisible} onBackdropPress={() => setModalVisible(false)} animationIn="slideInUp" animationOut="slideOutDown" backdropOpacity={0.5} useNativeDriver>
        <View style={styles.modalContent}>
          <ScrollView>
            <Text style={styles.modalTitle}>{ firstField(selected?.idFormacion, ['nombreFormacion','nombre']) ?? 'Inscripción' }</Text>
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

/* Estilos (puedes reutilizar los mismos que usas en honorarios) */
const styles = StyleSheet.create({
  center: { flex: 1, justifyContent: 'center', alignItems: 'center' },
  errorText: { color: 'red', fontSize: 16 },
  container: { flex: 1, paddingTop: 16, backgroundColor: '#f5f7fa' },
  title: { fontSize: 26, fontWeight: '700', color: '#4f8cff', textAlign: 'center', marginBottom: 12 },
  searchWrapper: { flexDirection: 'row', backgroundColor: '#fff', marginHorizontal: 12, borderRadius: 8, alignItems: 'center', paddingHorizontal: 12, elevation: 2, height: 48, marginBottom: 12 },
  searchInput: { flex: 1, fontSize: 16, marginLeft: 8 },
  card: { width: CARD_WIDTH, backgroundColor: '#fff', borderRadius: 16, padding: 16, marginHorizontal: 12, marginVertical: 8, shadowColor: '#000', shadowOpacity: 0.1, shadowOffset: { width: 0, height: 4 }, shadowRadius: 8, elevation: 4, position: 'relative' },
  header: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 },
  name: { fontSize: 18, fontWeight: '600', color: '#222', flex: 1 },
  badge: { paddingHorizontal: 8, paddingVertical: 4, borderRadius: 12 },
  badgeActive: { backgroundColor: '#2dce89' },
  badgeInactive: { backgroundColor: '#f5365c' },
  badgeText: { color: '#fff', fontSize: 12, fontWeight: '600' },
  row: { flexDirection: 'row', alignItems: 'center', marginBottom: 6 },
  detailText: { marginLeft: 8, fontSize: 16, color: '#525f7f', flex: 1 },
  dateText: { fontSize: 14, color: '#8898aa', marginTop: 8 },
  button: { position: 'absolute', right: 12, bottom: 12, backgroundColor: '#4f8cff', width: 40, height: 40, borderRadius: 20, justifyContent: 'center', alignItems: 'center' },
  emptyText: { marginTop: 20, textAlign: 'center', color: '#666', fontStyle: 'italic', fontSize: 16 },
  modalContent: { backgroundColor: '#fff', borderRadius: 16, padding: 16, maxHeight: '80%' },
  modalTitle: { fontSize: 20, fontWeight: '700', color: '#4f8cff', marginBottom: 12, textAlign: 'center' },
  detailRow: { flexDirection: 'row', marginBottom: 10 },
  detailLabel: { width: 120, fontWeight: '600', fontSize: 16, color: '#525f7f' },
  detailValue: { flex: 1, fontSize: 16, color: '#333' },
  modalClose: { marginTop: 12, alignSelf: 'center', backgroundColor: '#4f8cff', paddingHorizontal: 24, paddingVertical: 10, borderRadius: 24 },
  modalCloseText: { color: '#fff', fontWeight: '600', fontSize: 16 },
});
