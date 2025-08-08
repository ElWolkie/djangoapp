import React, { useState, useEffect, useRef, useCallback } from 'react';
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
import api from '../api';

const { width } = Dimensions.get('window');
const CARD_WIDTH = width - 24;

interface Persona {
  idPersona: number;
  nombres: string;
  apellidos: string;
  cedula: string;
  telefono: string;
  correo: string;
  rif?: string;
  tipos: { idTP: number; nombreTP: string }[];
  estadoPersona: 'ACTIVO' | 'INACTIVO';
  fechaPersona: string;
}

export default function PantallaPersonas() {
  const [personas, setPersonas] = useState<Persona[]>([]);
  const [mostradas, setMostradas] = useState<Persona[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchText, setSearchText] = useState('');
  const [modalVisible, setModalVisible] = useState(false);
  const [selectedPersona, setSelectedPersona] = useState<Persona | null>(null);
  const [animValues, setAnimValues] = useState<Animated.Value[]>([]);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const res = await api.get<Persona[]>('/api/personas/');
        const data = res.data.map(p => ({ ...p, tipos: p.tipos ?? [] }));
        setPersonas(data);
        setMostradas(data);
      } catch (err: any) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, []);

  useEffect(() => {
    const filtradas = personas.filter(p =>
      ['nombres', 'apellidos', 'cedula', 'telefono', 'correo', 'rif']
        .some(k => (p as any)[k]?.toLowerCase().includes(searchText.toLowerCase())) ||
      p.tipos.some(tp => tp.nombreTP.toLowerCase().includes(searchText.toLowerCase()))
    );
    setMostradas(filtradas);
  }, [searchText, personas]);

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

  const openModal = (p: Persona) => {
    setSelectedPersona(p);
    setModalVisible(true);
  };

  const renderItem = ({ item, index }: { item: Persona; index: number }) => {
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
          <Text style={styles.name}>{item.nombres} {item.apellidos}</Text>
          <View style={[
            styles.badge,
            item.estadoPersona === 'ACTIVO' ? styles.badgeActive : styles.badgeInactive
          ]}>
            <Text style={styles.badgeText}>
              {item.estadoPersona === 'ACTIVO' ? 'Activo' : 'Inactivo'}
            </Text>
          </View>
        </View>

        <Text style={styles.tipoText}>
          {item.tipos.map(tp => tp.nombreTP).join(', ') || '—'}
        </Text>

        {['cedula', 'telefono', 'correo'].map((f, i) => (
          <View style={styles.row} key={i}>
            <Icon name={f === 'cedula' ? 'id-card' : f === 'telefono' ? 'phone' : 'email'} size={16} />
            <Text style={styles.detailText}>{(item as any)[f]}</Text>
          </View>
        ))}

        {item.rif && (
          <View style={styles.row}>
            <Icon name="file-document" size={16} />
            <Text style={styles.detailText}>{item.rif}</Text>
          </View>
        )}

        <Text style={styles.dateText}>Registrado: {item.fechaPersona}</Text>

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
      <Text style={styles.title}>Personas Registradas</Text>

      <View style={styles.searchWrapper}>
        <Icon name="magnify" size={24} />
        <TextInput
          placeholder="Buscar..."
          value={searchText}
          onChangeText={setSearchText}
          style={styles.searchInput}
          clearButtonMode="while-editing"
        />
      </View>

      <FlatList
        data={mostradas}
        keyExtractor={p => p.idPersona.toString()}
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
            <Text style={styles.modalTitle}>{selectedPersona?.nombres} {selectedPersona?.apellidos}</Text>
            {selectedPersona && ([
              ['Cédula', selectedPersona.cedula],
              ['Teléfono', selectedPersona.telefono],
              ['Correo', selectedPersona.correo],
              ['RIF', selectedPersona.rif || '—'],
              ['Tipos', selectedPersona.tipos.map(tp => tp.nombreTP).join(', ') || '—'],
              ['Estado', selectedPersona.estadoPersona],
              ['Fecha', selectedPersona.fechaPersona]
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
  tipoText: { fontSize: 14, color: '#7b7b93', marginBottom: 8, fontWeight: 'bold', textTransform: 'uppercase' },
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
