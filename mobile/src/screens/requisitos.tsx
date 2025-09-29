// src/screens/requisitos.tsx
import React, { useEffect, useState } from 'react';
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

type RequisitoRaw = {
  idRequisito: number;
  nombreRequisito?: string;
  estadoRequisito?: string;
  fechaRequisito?: string;
  [k: string]: any;
};

export default function PantallaRequisitos() {
  const [items, setItems] = useState<RequisitoRaw[]>([]);
  const [mostradas, setMostradas] = useState<RequisitoRaw[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchText, setSearchText] = useState('');
  const [modalVisible, setModalVisible] = useState(false);
  const [selected, setSelected] = useState<RequisitoRaw | null>(null);
  const [animValues, setAnimValues] = useState<Animated.Value[]>([]);

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
        const res = await api.get<RequisitoRaw[]>('/api/requisito/');
        const data = res.data ?? [];
        setItems(data);
        setMostradas(data);
      } catch (err: any) {
        console.warn('Error fetching requisitos', err);
        setError(err?.message ?? 'Error al cargar requisitos');
      } finally {
        setLoading(false);
      }
    };

    fetchAll();
  }, []);

  useEffect(() => {
    const q = searchText.toLowerCase();
    setMostradas(items.filter(i => {
      const nombre = (i.nombreRequisito ?? '').toString();
      const fecha = (i.fechaRequisito ?? '').toString();
      return nombre.toLowerCase().includes(q) || fecha.toLowerCase().includes(q);
    }));
  }, [searchText, items]);

  useEffect(() => {
    const vals = mostradas.map(() => new Animated.Value(0));
    setAnimValues(vals);
  }, [mostradas]);

  useEffect(() => {
    if (animValues.length > 0) {
      Animated.stagger(70, animValues.map(a => Animated.spring(a, { toValue: 1, useNativeDriver: false }))).start();
    }
  }, [animValues]);

  const openModal = (r: RequisitoRaw) => {
    setSelected(r);
    setModalVisible(true);
  };

  const renderItem = ({ item, index }: { item: RequisitoRaw; index: number }) => {
    const anim = animValues[index] || new Animated.Value(1);
    const nombre = item.nombreRequisito ?? '—';
    const fecha = formatDate(item.fechaRequisito);

    return (
      <Animated.View
        style={[
          styles.card,
          {
            opacity: anim,
            transform: [{ translateY: anim.interpolate({ inputRange: [0, 1], outputRange: [20, 0] }) }],
          },
        ]}
      >
        <View style={styles.header}>
          <Text style={styles.name}>{nombre}</Text>
          <View style={[styles.badge, item.estadoRequisito === 'ACTIVO' ? styles.badgeActive : styles.badgeInactive]}>
            <Text style={styles.badgeText}>{item.estadoRequisito ?? '—'}</Text>
          </View>
        </View>

        <View style={styles.row}>
          <Icon name="file-document-outline" size={16} />
          <Text style={styles.detailText}>Nombre: {nombre}</Text>
        </View>

        <View style={styles.row}>
          <Icon name="calendar" size={16} />
          <Text style={styles.detailText}>Fecha: {fecha}</Text>
        </View>

        <TouchableOpacity style={styles.button} onPress={() => openModal(item)}>
          <Icon name="chevron-right" size={24} color="#fff" />
        </TouchableOpacity>
      </Animated.View>
    );
  };

  const modalRows = selected ? [
    ['Nombre', selected.nombreRequisito ?? '—', 'file-document-outline'],
    ['Estado', selected.estadoRequisito ?? '—', 'information-outline'],
    ['Fecha', formatDate(selected.fechaRequisito), 'calendar'],
  ] as [string, string, string][] : [];

  if (loading) {
    return <View style={styles.center}><ActivityIndicator size="large" color="#4f8cff" /></View>;
  }

  if (error) {
    return <View style={styles.center}><Text style={styles.errorText}>{error}</Text></View>;
  }

  return (
    <View style={styles.container}>
      <Text style={styles.title}>Requisitos</Text>

      <View style={styles.searchWrapper}>
        <Icon name="magnify" size={24} />
        <TextInput
          placeholder="Buscar por nombre o fecha..."
          value={searchText}
          onChangeText={setSearchText}
          style={styles.searchInput}
          clearButtonMode="while-editing"
        />
      </View>

      <FlatList
        data={mostradas}
        keyExtractor={(s) => s.idRequisito.toString()}
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
            <Text style={styles.modalTitle}>{selected?.nombreRequisito ?? 'Requisito'}</Text>

            {modalRows.map(([lbl, val, icon]) => (
              <View key={lbl} style={styles.detailRow}>
                <View style={styles.detailLabelRow}>
                  <Icon name={icon} size={16} color="#4f8cff" />
                  <Text style={styles.detailLabel}>{lbl}:</Text>
                </View>
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
    shadowOpacity: 0.08,
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
  detailRow: { marginBottom: 12 },
  detailLabelRow: { flexDirection: 'row', alignItems: 'center', marginBottom: 6 },
  detailLabel: { marginLeft: 8, fontWeight: '700', fontSize: 15, color: '#525f7f' },
  detailValue: { fontSize: 16, color: '#333' },
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
