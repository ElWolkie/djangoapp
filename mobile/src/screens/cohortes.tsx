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

interface Cohorte {
  idCohorte: number;
  nombreCohorte: string;
  estadoCohorte: 'ACTIVO' | 'INACTIVO' | string;
  fechaCohorte: string;
}

export default function PantallaCohortes() {
  const [cohortes, setCohortes] = useState<Cohorte[]>([]);
  const [mostradas, setMostradas] = useState<Cohorte[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchText, setSearchText] = useState('');
  const [modalVisible, setModalVisible] = useState(false);
  const [selected, setSelected] = useState<Cohorte | null>(null);
  const [animValues, setAnimValues] = useState<Animated.Value[]>([]);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const res = await api.get<Cohorte[]>('/api/cohorte/');
        const data = res.data ?? [];
        setCohortes(data);
        setMostradas(data);
      } catch (err: any) {
        setError(err.message || 'Error al cargar cohortes');
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, []);

  useEffect(() => {
    const fil = cohortes.filter(c =>
      c.nombreCohorte?.toLowerCase().includes(searchText.toLowerCase()) ||
      (c.estadoCohorte ?? '').toLowerCase().includes(searchText.toLowerCase())
    );
    setMostradas(fil);
  }, [searchText, cohortes]);

  useEffect(() => {
    const values = mostradas.map(() => new Animated.Value(0));
    setAnimValues(values);
  }, [mostradas]);

  useEffect(() => {
    if (animValues.length > 0) {
      Animated.stagger(100, animValues.map(a =>
        Animated.spring(a, { toValue: 1, useNativeDriver: false })
      )).start();
    }
  }, [animValues]);

  const openModal = (c: Cohorte) => {
    setSelected(c);
    setModalVisible(true);
  };

  const renderItem = ({ item, index }: { item: Cohorte; index: number }) => {
    const anim = animValues[index] || new Animated.Value(1);

    return (
      <Animated.View style={[
        styles.card,
        {
          opacity: anim,
          transform: [{ translateY: anim.interpolate({ inputRange: [0, 1], outputRange: [20, 0] }) }],
        }
      ]}>
        <View style={styles.header}>
          <Text style={styles.name}>{item.nombreCohorte}</Text>
          <View style={[
            styles.badge,
            item.estadoCohorte === 'ACTIVO' ? styles.badgeActive : styles.badgeInactive
          ]}>
            <Text style={styles.badgeText}>
              {item.estadoCohorte === 'ACTIVO' ? 'Activo' : 'Inactivo'}
            </Text>
          </View>
        </View>

        <View style={styles.row}>
          <Icon name="calendar" size={16} />
          <Text style={styles.detailText}>Registrada: {item.fechaCohorte}</Text>
        </View>

        <TouchableOpacity style={styles.button} onPress={() => openModal(item)}>
          <Icon name="chevron-right" size={24} color="#fff" />
        </TouchableOpacity>
      </Animated.View>
    );
  };

  if (loading) {
    return <View style={styles.center}><ActivityIndicator size="large" color="#4f8cff" /></View>;
  }

  if (error) {
    return <View style={styles.center}><Text style={styles.errorText}>{error}</Text></View>;
  }

  return (
    <View style={styles.container}>
      <Text style={styles.title}>Cohortes</Text>

      <View style={styles.searchWrapper}>
        <Icon name="magnify" size={24} />
        <TextInput
          placeholder="Buscar por nombre o estado..."
          value={searchText}
          onChangeText={setSearchText}
          style={styles.searchInput}
          clearButtonMode="while-editing"
        />
      </View>

      <FlatList
        data={mostradas}
        keyExtractor={c => c.idCohorte.toString()}
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
            <Text style={styles.modalTitle}>{selected?.nombreCohorte}</Text>
            {selected && ([
              ['ID', String(selected.idCohorte)],
              ['Nombre', selected.nombreCohorte],
              ['Estado', selected.estadoCohorte],
              ['Fecha', selected.fechaCohorte]
            ] as [string, string][]).map(([lbl, val]) => (
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
  searchInput: { flex: 1, fontSize: 18, marginLeft: 8 },
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
  name: { fontSize: 20, fontWeight: '600', color: '#222', flex: 1 },
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
  modalContent: { backgroundColor: '#fff', borderRadius: 16, padding: 16, maxHeight: '70%' },
  modalTitle: { fontSize: 24, fontWeight: '700', color: '#4f8cff', marginBottom: 12 },
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
