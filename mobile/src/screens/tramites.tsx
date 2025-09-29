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
import api from '../api/api';

const { width } = Dimensions.get('window');
const CARD_WIDTH = width - 24;

interface Tramite {
  idTramite: number;
  nombreTramite: string;
  diasTramite: string;
  precioTramite: string;
  estadoTramite: 'ACTIVO' | 'INACTIVO';
  fechaTramite: string;
}

export default function PantallaTramites() {
  const [tramites, setTramites] = useState<Tramite[]>([]);
  const [mostradas, setMostradas] = useState<Tramite[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchText, setSearchText] = useState('');
  const [modalVisible, setModalVisible] = useState(false);
  const [selectedTramite, setSelectedTramite] = useState<Tramite | null>(null);
  const [animValues, setAnimValues] = useState<Animated.Value[]>([]);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const res = await api.get<Tramite[]>('/api/tramite/');
        setTramites(res.data);
        setMostradas(res.data);
      } catch (err: any) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, []);

  useEffect(() => {
    const filtradas = tramites.filter(t =>
      t.nombreTramite.toLowerCase().includes(searchText.toLowerCase()) ||
      t.diasTramite.toLowerCase().includes(searchText.toLowerCase()) ||
      t.precioTramite.toLowerCase().includes(searchText.toLowerCase()) ||
      t.estadoTramite.toLowerCase().includes(searchText.toLowerCase())
    );
    setMostradas(filtradas);
  }, [searchText, tramites]);

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

  // Función mejorada para formatear el precio
  const formatPrecio = (precio: string) => {
    if (!precio) return '0,00';
    
    try {
      // Si ya tiene el formato correcto (con coma), devolverlo tal cual
      if (precio.includes(',')) {
        return precio;
      }
      
      // Si tiene punto decimal, convertirlo a formato con coma
      if (precio.includes('.')) {
        const partes = precio.split('.');
        // Formatear la parte entera con separadores de miles
        const parteEntera = partes[0].replace(/\B(?=(\d{3})+(?!\d))/g, '.');
        const parteDecimal = partes[1] || '00';
        return `${parteEntera},${parteDecimal.padEnd(2, '0')}`;
      }
      
      // Si es un número entero sin decimales
      const numero = parseFloat(precio);
      if (!isNaN(numero)) {
        const parteEntera = Math.floor(numero).toString().replace(/\B(?=(\d{3})+(?!\d))/g, '.');
        return `${parteEntera},00`;
      }
      
      return precio;
    } catch (error) {
      return precio;
    }
  };

  const formatDate = (dateString: string) => {
    if (!dateString || dateString === 'N/A') return 'N/A';
    try {
      const date = new Date(dateString);
      if (isNaN(date.getTime())) return 'Fecha inválida';
      return date.toLocaleDateString('es-ES', {
        day: '2-digit',
        month: '2-digit',
        year: 'numeric'
      });
    } catch (error) {
      return 'Fecha inválida';
    }
  };

  const openModal = (t: Tramite) => {
    setSelectedTramite(t);
    setModalVisible(true);
  };

  const renderItem = ({ item, index }: { item: Tramite; index: number }) => {
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
          <Text style={styles.name}>{item.nombreTramite}</Text>
          <View style={[
            styles.badge,
            item.estadoTramite === 'ACTIVO' ? styles.badgeActive : styles.badgeInactive
          ]}>
            <Text style={styles.badgeText}>
              {item.estadoTramite === 'ACTIVO' ? 'Activo' : 'Inactivo'}
            </Text>
          </View>
        </View>

        <View style={styles.row}>
          <Icon name="calendar-clock" size={16} color="#666" />
          <Text style={styles.detailText}>
            <Text style={styles.label}>Días de respuesta: </Text>
            {item.diasTramite || 'N/A'}
          </Text>
        </View>

        <View style={styles.row}>
          <Icon name="cash" size={16} color="#666" />
          <Text style={styles.detailText}>
            <Text style={styles.label}>Precio: </Text>
            {formatPrecio(item.precioTramite)}
          </Text>
        </View>

        <Text style={styles.dateText}>Registrado: {formatDate(item.fechaTramite)}</Text>

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
      <Text style={styles.title}>Trámites Registrados</Text>

      <View style={styles.searchWrapper}>
        <Icon name="magnify" size={24} color="#666" />
        <TextInput
          placeholder="Buscar por nombre, días, precio..."
          value={searchText}
          onChangeText={setSearchText}
          style={styles.searchInput}
          clearButtonMode="while-editing"
        />
      </View>

      <FlatList
        data={mostradas}
        keyExtractor={t => t.idTramite.toString()}
        renderItem={renderItem}
        contentContainerStyle={{ paddingBottom: 24 }}
        showsVerticalScrollIndicator={false}
        ListEmptyComponent={<Text style={styles.emptyText}>No hay trámites registrados.</Text>}
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
            <Text style={styles.modalTitle}>{selectedTramite?.nombreTramite}</Text>
            {selectedTramite && ([
              ['Nombre', selectedTramite.nombreTramite],
              ['Días de Respuesta', selectedTramite.diasTramite],
              ['Precio', formatPrecio(selectedTramite.precioTramite)],
              ['Estado', selectedTramite.estadoTramite],
              ['Fecha de Registro', formatDate(selectedTramite.fechaTramite)]
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