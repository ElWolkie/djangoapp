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

interface Formacion {
  idFormacion: number;
  nombreFormacion: string;
}

interface Materia {
  idMateria: number;
  idFormacion: number; // Solo el ID, no el objeto completo
  nombreMateria: string;
  estadoMateria: 'ACTIVO' | 'INACTIVO';
  fechaMateria: string;
  nombreFormacion?: string; // Lo agregaremos después
}

export default function PantallaMaterias() {
  const [materias, setMaterias] = useState<Materia[]>([]);
  const [formaciones, setFormaciones] = useState<Formacion[]>([]);
  const [mostradas, setMostradas] = useState<Materia[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchText, setSearchText] = useState('');
  const [modalVisible, setModalVisible] = useState(false);
  const [selectedMateria, setSelectedMateria] = useState<Materia | null>(null);
  const [animValues, setAnimValues] = useState<Animated.Value[]>([]);

  useEffect(() => {
    const fetchData = async () => {
      try {
        // Cargar formaciones primero
        const resFormaciones = await api.get<Formacion[]>('/api/formaciones/');
        setFormaciones(resFormaciones.data);

        // Luego cargar materias
        const resMaterias = await api.get<Materia[]>('/api/materias/');
        
        // Enriquecer las materias con el nombre de la formación
        const materiasConFormacion = resMaterias.data.map(materia => {
          const formacion = resFormaciones.data.find(f => f.idFormacion === materia.idFormacion);
          return {
            ...materia,
            nombreFormacion: formacion ? formacion.nombreFormacion : 'N/A'
          };
        });

        setMaterias(materiasConFormacion);
        setMostradas(materiasConFormacion);
      } catch (err: any) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, []);

  useEffect(() => {
    const filtradas = materias.filter(m =>
      m.nombreMateria.toLowerCase().includes(searchText.toLowerCase()) ||
      (m.nombreFormacion || '').toLowerCase().includes(searchText.toLowerCase()) ||
      m.estadoMateria.toLowerCase().includes(searchText.toLowerCase())
    );
    setMostradas(filtradas);
  }, [searchText, materias]);

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

  const formatDate = (dateString: string) => {
    if (!dateString) return 'N/A';
    const date = new Date(dateString);
    return date.toLocaleDateString('es-ES', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric'
    });
  };

  const openModal = (m: Materia) => {
    setSelectedMateria(m);
    setModalVisible(true);
  };

  const renderItem = ({ item, index }: { item: Materia; index: number }) => {
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
          <Text style={styles.name}>{item.nombreMateria}</Text>
          <View style={[
            styles.badge,
            item.estadoMateria === 'ACTIVO' ? styles.badgeActive : styles.badgeInactive
          ]}>
            <Text style={styles.badgeText}>
              {item.estadoMateria === 'ACTIVO' ? 'Activo' : 'Inactivo'}
            </Text>
          </View>
        </View>

        <View style={styles.row}>
          <Icon name="book-education" size={16} color="#666" />
          <Text style={styles.detailText}>
            <Text style={styles.label}>Formación: </Text>
            {item.nombreFormacion || 'N/A'}
          </Text>
        </View>

        <Text style={styles.dateText}>Registrado: {formatDate(item.fechaMateria)}</Text>

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
      <Text style={styles.title}>Materias Registradas</Text>

      <View style={styles.searchWrapper}>
        <Icon name="magnify" size={24} color="#666" />
        <TextInput
          placeholder="Buscar por materia, formación..."
          value={searchText}
          onChangeText={setSearchText}
          style={styles.searchInput}
          clearButtonMode="while-editing"
        />
      </View>

      <FlatList
        data={mostradas}
        keyExtractor={m => m.idMateria.toString()}
        renderItem={renderItem}
        contentContainerStyle={{ paddingBottom: 24 }}
        showsVerticalScrollIndicator={false}
        ListEmptyComponent={<Text style={styles.emptyText}>No hay materias registradas.</Text>}
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
            <Text style={styles.modalTitle}>{selectedMateria?.nombreMateria}</Text>
            {selectedMateria && ([
              ['ID', selectedMateria.idMateria.toString()],
              ['Nombre', selectedMateria.nombreMateria],
              ['Formación', selectedMateria.nombreFormacion || 'N/A'],
              ['Estado', selectedMateria.estadoMateria],
              ['Fecha de Registro', formatDate(selectedMateria.fechaMateria)]
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
  searchInput: { flex: 1, fontSize: 18, marginLeft: 8, color: '#333' },
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
  header: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 },
  name: { fontSize: 20, fontWeight: '600', color: '#222', flex: 1 },
  badge: { paddingHorizontal: 8, paddingVertical: 4, borderRadius: 12 },
  badgeActive: { backgroundColor: '#2dce89' },
  badgeInactive: { backgroundColor: '#f5365c' },
  badgeText: { color: '#fff', fontSize: 12, fontWeight: '600' },
  row: { flexDirection: 'row', alignItems: 'center', marginBottom: 8 },
  label: { fontWeight: '600', color: '#333' },
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
  detailLabel: { width: 140, fontWeight: '600', fontSize: 16, color: '#525f7f' },
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