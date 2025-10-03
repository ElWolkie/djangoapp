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

interface Persona {
  idPersona: number;
  nombres: string;
  apellidos: string;
  cedula: string;
}

interface Tramite {
  idTramite: number;
  nombreTramite: string;
}

interface Servicio {
  idServicio: number;
  nombreServicio: string;
}

interface Solicitud {
  idSoli: number;
  idPersona: Persona;
  idTramite: Tramite;
  idServicio: Servicio;
  montoTotal: string;
  estadoSolicitud: string;
  fechaEntrega: string;
  fechaSolicitud: string;
}

export default function PantallaSolicitudes() {
  const [solicitudes, setSolicitudes] = useState<Solicitud[]>([]);
  const [mostradas, setMostradas] = useState<Solicitud[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchText, setSearchText] = useState('');
  const [modalVisible, setModalVisible] = useState(false);
  const [selectedSolicitud, setSelectedSolicitud] = useState<Solicitud | null>(null);
  const [animValues, setAnimValues] = useState<Animated.Value[]>([]);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const res = await api.get<Solicitud[]>('/api/solicitud/');
        setSolicitudes(res.data);
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
    const filtradas = solicitudes.filter(s =>
      s.idPersona?.nombres?.toLowerCase().includes(searchText.toLowerCase()) ||
      s.idPersona?.apellidos?.toLowerCase().includes(searchText.toLowerCase()) ||
      s.idTramite?.nombreTramite?.toLowerCase().includes(searchText.toLowerCase()) ||
      s.idServicio?.nombreServicio?.toLowerCase().includes(searchText.toLowerCase()) ||
      s.estadoSolicitud?.toLowerCase().includes(searchText.toLowerCase())
    );
    setMostradas(filtradas);
  }, [searchText, solicitudes]);

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

  const formatMonto = (monto: string | number) => {
    if (!monto) return '$0.00';
    
    try {
      if (typeof monto === 'number') {
        return `$${monto.toFixed(2)}`;
      }
      
      const montoLimpio = monto.replace(',', '');
      const montoNumero = parseFloat(montoLimpio);
      
      if (isNaN(montoNumero)) {
        return `$${monto}`;
      }
      
      return `$${montoNumero.toFixed(2)}`;
    } catch (error) {
      return `$${monto}`;
    }
  };

  const openModal = (s: Solicitud) => {
    setSelectedSolicitud(s);
    setModalVisible(true);
  };

  const getEstadoDisplay = (estado: string) => {
    switch (estado) {
      case 'ACTIVO': return 'Activo';
      case 'PENDIENTE': return 'Pendiente';
      case 'INACTIVO': return 'Inactivo';
      default: return estado;
    }
  };

  const getEstadoColor = (estado: string) => {
    switch (estado) {
      case 'ACTIVO': return styles.badgeActive;
      case 'PENDIENTE': return styles.badgePending;
      case 'INACTIVO': return styles.badgeInactive;
      default: return styles.badgeInactive;
    }
  };

  const renderItem = ({ item, index }: { item: Solicitud; index: number }) => {
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
          <Text style={styles.cardTitle}>Solicitud #{item.idSoli}</Text>
          <View style={[styles.badge, getEstadoColor(item.estadoSolicitud)]}>
            <Text style={styles.badgeText}>{getEstadoDisplay(item.estadoSolicitud)}</Text>
          </View>
        </View>

        <View style={styles.row}>
          <Icon name="account" size={16} color="#666" />
          <Text style={styles.detailText}>
            <Text style={styles.label}>Solicitante: </Text>
            {item.idPersona ? `${item.idPersona.nombres} ${item.idPersona.apellidos}` : 'N/A'}
          </Text>
        </View>

        <View style={styles.row}>
          <Icon name="file-document" size={16} color="#666" />
          <Text style={styles.detailText}>
            <Text style={styles.label}>Trámite: </Text>
            {item.idTramite?.nombreTramite || 'N/A'}
          </Text>
        </View>

        <View style={styles.row}>
          <Icon name="cube" size={16} color="#666" />
          <Text style={styles.detailText}>
            <Text style={styles.label}>Servicio: </Text>
            {item.idServicio?.nombreServicio || 'N/A'}
          </Text>
        </View>

        <View style={styles.row}>
          <Icon name="calendar-start" size={16} color="#666" />
          <Text style={styles.detailText}>
            <Text style={styles.label}>Solicitud: </Text>
            {formatDate(item.fechaSolicitud)}
          </Text>
        </View>
        
        <View style={styles.row}>
          <Icon name="calendar-end" size={16} color="#666" />
          <Text style={styles.detailText}>
            <Text style={styles.label}>Entrega: </Text>
            {formatDate(item.fechaEntrega)}
          </Text>
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
      <Text style={styles.title}>Solicitudes Registradas</Text>

      <View style={styles.searchWrapper}>
        <Icon name="magnify" size={24} color="#666" />
        <TextInput
          placeholder="Buscar por solicitante, trámite, servicio..."
          value={searchText}
          onChangeText={setSearchText}
          style={styles.searchInput}
          clearButtonMode="while-editing"
        />
      </View>

      <FlatList
        data={mostradas}
        keyExtractor={s => s.idSoli.toString()}
        renderItem={renderItem}
        contentContainerStyle={{ paddingBottom: 24 }}
        showsVerticalScrollIndicator={false}
        ListEmptyComponent={<Text style={styles.emptyText}>No hay solicitudes registradas.</Text>}
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
            <Text style={styles.modalTitle}>Detalle de Solicitud #{selectedSolicitud?.idSoli}</Text>
            {selectedSolicitud && ([
              ['Solicitante', selectedSolicitud.idPersona ? `${selectedSolicitud.idPersona.nombres} ${selectedSolicitud.idPersona.apellidos}` : 'N/A'],
              ['Cédula', selectedSolicitud.idPersona?.cedula || 'N/A'],
              ['Trámite', selectedSolicitud.idTramite?.nombreTramite || 'N/A'],
              ['Servicio', selectedSolicitud.idServicio?.nombreServicio || 'N/A'],
              ['Monto Total', formatMonto(selectedSolicitud.montoTotal)],
              ['Estado', getEstadoDisplay(selectedSolicitud.estadoSolicitud)],
              ['Fecha Solicitud', formatDate(selectedSolicitud.fechaSolicitud)],
              ['Fecha Entrega', formatDate(selectedSolicitud.fechaEntrega)]
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
  cardTitle: { fontSize: 18, fontWeight: '600', color: '#222' },
  badge: { paddingHorizontal: 8, paddingVertical: 4, borderRadius: 12 },
  badgeActive: { backgroundColor: '#2dce89' },
  badgePending: { backgroundColor: '#fb6340' },
  badgeInactive: { backgroundColor: '#f5365c' },
  badgeText: { color: '#fff', fontSize: 12, fontWeight: '600' },
  row: { flexDirection: 'row', alignItems: 'center', marginBottom: 8 },
  label: { fontWeight: '600', color: '#333' },
  detailText: { marginLeft: 8, fontSize: 16, color: '#525f7f', flex: 1 },
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
  detailLabel: { width: 120, fontWeight: '600', fontSize: 16, color: '#525f7f' },
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