// src/screens/inscripciones.tsx
import React, { useState, useEffect } from 'react';
import {
  View, Text, FlatList, ActivityIndicator, StyleSheet, Dimensions,
  TouchableOpacity, TextInput, ScrollView
} from 'react-native';
import Icon from 'react-native-vector-icons/MaterialCommunityIcons';
import Modal from 'react-native-modal';
import api from '../api/api';

const { width } = Dimensions.get('window');
const CARD_WIDTH = width - 24;

const fmtMoney = (v: any) => {
  const n = Number(v);
  if (!isFinite(n)) return '—';
  return `$${n.toFixed(2)}`;
};

export default function PantallaInscripciones() {
  const [items, setItems] = useState<any[]>([]);
  const [mostradas, setMostradas] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchText, setSearchText] = useState('');
  const [modalVisible, setModalVisible] = useState(false);
  const [selected, setSelected] = useState<any | null>(null);

  useEffect(() => {
    (async () => {
      setLoading(true);
      try {
        const res = await api.get('/api/inscripcion/'); // endpoint simple
        const data = res.data ?? [];
        setItems(data);
        setMostradas(data);
      } catch (e: any) {
        setError(e?.message ?? 'Error al cargar inscripciones');
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  useEffect(() => {
    const q = searchText.toLowerCase();
    setMostradas(items.filter(i => {
      const ced = i.idPersona?.cedula ?? '';
      const form = i.idFormacion?.nombreFormacion ?? '';
      const coh = i.idCohorte?.nombreCohorte ?? '';
      const estado = (i.estadoPago ?? '') as string;
      return ced.toLowerCase().includes(q) || form.toLowerCase().includes(q) || coh.toLowerCase().includes(q) || estado.toLowerCase().includes(q);
    }));
  }, [searchText, items]);

  const openModal = (it: any) => { setSelected(it); setModalVisible(true); };

  // Estado: prioriza el estado que viene del backend si indica PAGADO;
  // si no hay estado explícito, intenta derivar por montos (si existen)
  const deriveStatus = (item: any) => {
    if (String(item.estadoPago ?? '').toUpperCase() === 'PAGADO') return 'PAGADO';
    const paid = Number(item.montoPagado ?? 0) || 0;
    const total = Number(item.montoTotal ?? 0) || 0;
    if (total > 0 && paid >= total) return 'PAGADO';
    if (paid > 0 && paid < total) return 'PARCIAL';
    return item.estadoPago ?? 'PENDIENTE';
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
      <Text style={styles.title}>Inscripciones</Text>

      <View style={styles.searchWrapper}>
        <Icon name="magnify" size={24} />
        <TextInput placeholder="Buscar por cédula, formación, cohorte o estado..." value={searchText} onChangeText={setSearchText} style={styles.searchInput} />
      </View>

      <FlatList
        data={mostradas}
        keyExtractor={(i) => String(i.idInscripcion)}
        renderItem={({item}) => {
          const status = deriveStatus(item);
          return (
            <View style={styles.card}>
              <View style={styles.header}>
                <Text style={styles.name}>{item.idFormacion?.nombreFormacion ?? '—'}</Text>
                <View style={[ styles.badge, statusColor(status) ]}>
                  <Text style={styles.badgeText}>{status}</Text>
                </View>
              </View>

              <View style={styles.row}>
                <Icon name="id-card" size={16} />
                <Text style={styles.detailText}>Cédula: {item.idPersona?.cedula ?? '—'}</Text>
              </View>

              <View style={styles.row}>
                <Icon name="domain" size={16} />
                <Text style={styles.detailText}>Cohorte: {item.idCohorte?.nombreCohorte ?? '—'}</Text>
              </View>

              {/* Mostrar sólo monto total para evitar inconsistencias */}
              <View style={styles.row}>
                <Icon name="cash" size={16} />
                <Text style={styles.detailText}>
                  Total: { fmtMoney(item.montoTotal) }
                </Text>
              </View>

              <Text style={styles.dateText}>Registrado: { item.fechaInscripcion ?? '—' }</Text>

              <TouchableOpacity style={styles.button} onPress={() => openModal(item)}>
                <Icon name="chevron-right" size={24} color="#fff" />
              </TouchableOpacity>
            </View>
          );
        }}
        contentContainerStyle={{ paddingBottom: 24 }}
        ListEmptyComponent={<Text style={styles.emptyText}>No hay resultados.</Text>}
      />

      <Modal isVisible={modalVisible} onBackdropPress={() => setModalVisible(false)}>
        <View style={styles.modalContent}>
          <ScrollView>
            <Text style={styles.modalTitle}>{selected?.idFormacion?.nombreFormacion ?? 'Inscripción'}</Text>
            {selected && [
              ['Cédula', selected.idPersona?.cedula ?? '—'],
              ['Nombres', selected.idPersona?.nombres ?? '—'],
              ['Apellidos', selected.idPersona?.apellidos ?? '—'],
              ['Formación', selected.idFormacion?.nombreFormacion ?? '—'],
              ['Cohorte', selected.idCohorte?.nombreCohorte ?? '—'],
              ['Fecha inscripción', selected.fechaInscripcion ?? '—'],
              ['Estado pago', deriveStatus(selected)],
              // ocultamos monto pagado y saldo para evitar incongruencias; dejamos total
              ['Monto total', fmtMoney(selected.montoTotal)],
              ['Nota', 'Monto pagado oculto en la app para evitar inconsistencias con el backend'],
              ['Activo', selected.is_active ? 'Sí' : 'No'],
            ].map(([lbl,val]) => (
              <View key={String(lbl)} style={styles.detailRow}>
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
  center: { flex:1, justifyContent:'center', alignItems:'center' },
  errorText: { color: 'red' },
  container: { flex: 1, paddingTop: 16, backgroundColor: '#f5f7fa' },
  title: { fontSize: 26, fontWeight: '700', color: '#4f8cff', textAlign: 'center', marginBottom: 12 },
  searchWrapper: { flexDirection:'row', backgroundColor:'#fff', marginHorizontal:12, borderRadius:8, alignItems:'center', paddingHorizontal:12, elevation:2, height:48, marginBottom:12 },
  searchInput: { flex:1, fontSize:16, marginLeft:8 },
  card: { width: CARD_WIDTH, backgroundColor:'#fff', borderRadius:16, padding:16, marginHorizontal:12, marginVertical:8, shadowColor:'#000', shadowOpacity:0.1, shadowOffset:{ width:0, height:4 }, shadowRadius:8, elevation:4, position:'relative' },
  header: { flexDirection:'row', justifyContent:'space-between', alignItems:'center', marginBottom:8 },
  name: { fontSize:18, fontWeight:'600', color:'#222' },
  badge: { paddingHorizontal:8, paddingVertical:4, borderRadius:12 },
  badgeActive: { backgroundColor:'#2dce89' },
  badgePartial: { backgroundColor:'#f1a43a' },
  badgeInactive: { backgroundColor:'#f5365c' },
  badgeText: { color:'#fff', fontSize:12, fontWeight:'600' },
  row: { flexDirection:'row', alignItems:'center', marginBottom:6 },
  detailText: { marginLeft:8, fontSize:16, color:'#525f7f', flex:1 },
  dateText: { fontSize:14, color:'#8898aa', marginTop:8 },
  button: { position:'absolute', right:12, bottom:12, backgroundColor:'#4f8cff', width:40, height:40, borderRadius:20, justifyContent:'center', alignItems:'center' },
  emptyText: { marginTop: 20, textAlign: 'center', color: '#666', fontStyle: 'italic', fontSize: 16 },
  modalContent: { backgroundColor:'#fff', borderRadius:16, padding:16, maxHeight:'80%' },
  modalTitle: { fontSize:20, fontWeight:'700', color:'#4f8cff', marginBottom:12, textAlign:'center' },
  detailRow: { flexDirection:'row', marginBottom:10 },
  detailLabel: { width:120, fontWeight:'600', fontSize:16, color:'#525f7f' },
  detailValue: { flex:1, fontSize:16, color:'#333' },
  modalClose: { marginTop:12, alignSelf:'center', backgroundColor:'#4f8cff', paddingHorizontal:24, paddingVertical:10, borderRadius:24 },
  modalCloseText: { color:'#fff', fontWeight:'600', fontSize:16 },
});
