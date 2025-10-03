// src/screens/tipoFormaciones.tsx
import React, { useEffect, useState, useCallback, useContext } from 'react';
import {
  View,
  Text,
  FlatList,
  ActivityIndicator,
  StyleSheet,
  Dimensions,
  TouchableOpacity,
  TextInput,
  Alert,
  ScrollView,
  KeyboardAvoidingView,
  Platform,
} from 'react-native';
import Icon from 'react-native-vector-icons/MaterialCommunityIcons';
import Modal from 'react-native-modal';
import api from '../api/api';
import { ReloadContext } from '../contexts/ReloadContext';

const { width } = Dimensions.get('window');
const CARD_WIDTH = width - 24;

interface TipoFormacion {
  idTF: number;
  nombreTipoFormacion: string;
  estadoTipoFormacion: 'ACTIVO' | 'INACTIVO' | string;
  fechaTipoFormacion: string; // ISO date
}

export default function PantallaTipoFormaciones() {
  const [items, setItems] = useState<TipoFormacion[]>([]);
  const [mostradas, setMostradas] = useState<TipoFormacion[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchText, setSearchText] = useState('');
  const [detailModalVisible, setDetailModalVisible] = useState(false);
  const [formModalVisible, setFormModalVisible] = useState(false);
  const [selected, setSelected] = useState<TipoFormacion | null>(null);
  const [saving, setSaving] = useState(false);

  // Form fields (create / edit)
  const [nombre, setNombre] = useState('');
  const [estado, setEstado] = useState<'ACTIVO' | 'INACTIVO' | string>('ACTIVO');

  // Reload context
  const { reloadCount } = useContext(ReloadContext);

  // fetchTipos - useCallback opcional para estabilidad
  const fetchTipos = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.get<TipoFormacion[]>('/api/tipo-formaciones/');
      const data = Array.isArray(res.data) ? res.data : [];
      setItems(data);
      setMostradas(data);
    } catch (err: any) {
      console.error('fetchTipos error', err);
      setError(err?.message || 'Error al obtener tipos');
    } finally {
      setLoading(false);
    }
  }, []);

  // Inicial + cuando se dispare reload desde el header
  useEffect(() => {
    fetchTipos();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [fetchTipos, reloadCount]);

  useEffect(() => {
    const q = searchText.trim().toLowerCase();
    if (!q) {
      setMostradas(items);
      return;
    }
    setMostradas(
      items.filter(
        t =>
          (t.nombreTipoFormacion || '').toLowerCase().includes(q) ||
          (t.estadoTipoFormacion || '').toLowerCase().includes(q)
      )
    );
  }, [searchText, items]);

  const openDetail = (t: TipoFormacion) => {
    setSelected(t);
    setDetailModalVisible(true);
  };

  const openCreate = () => {
    setSelected(null);
    setNombre('');
    setEstado('ACTIVO');
    setFormModalVisible(true);
  };

  const openEdit = (t: TipoFormacion) => {
    setSelected(t);
    setNombre(t.nombreTipoFormacion);
    setEstado(t.estadoTipoFormacion || 'ACTIVO');
    setFormModalVisible(true);
  };

  const handleSave = async () => {
    if (!nombre.trim()) {
      Alert.alert('Validación', 'El nombre es requerido');
      return;
    }
    setSaving(true);
    try {
      if (selected && selected.idTF) {
        // editar
        await api.put(`/api/tipo-formaciones/${selected.idTF}/`, {
          nombreTipoFormacion: nombre.trim(),
          estadoTipoFormacion: estado,
        });
      } else {
        // crear
        await api.post('/api/tipo-formaciones/', {
          nombreTipoFormacion: nombre.trim(),
          estadoTipoFormacion: estado,
        });
      }
      setFormModalVisible(false);
      // re-fetch para asegurar consistencia
      await fetchTipos();
    } catch (err: any) {
      console.error('save error', err);
      // si es 403 puede ser problema de autenticación/CSRF
      if (err?.response?.status === 403) {
        Alert.alert(
          'Error de permisos',
          'Operación no permitida (403). Verifica que tu sesión sea válida o que el backend acepte tokens (JWT).'
        );
      } else {
        const msg = err?.response?.data?.detail || err?.response?.data || err?.message || 'Error al guardar';
        Alert.alert('Error', String(msg));
      }
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = (t: TipoFormacion) => {
    Alert.alert(
      'Confirmar eliminación',
      `¿Eliminar tipo "${t.nombreTipoFormacion}"? Esta acción no puede deshacerse.`,
      [
        { text: 'Cancelar', style: 'cancel' },
        {
          text: 'Eliminar',
          style: 'destructive',
          onPress: async () => {
            try {
              setLoading(true);
              await api.delete(`/api/tipo-formaciones/${t.idTF}/`);
              await fetchTipos();
              setDetailModalVisible(false);
            } catch (err: any) {
              console.error('delete error', err);
              Alert.alert('Error', err?.message || 'No se pudo eliminar');
            } finally {
              setLoading(false);
            }
          },
        },
      ]
    );
  };

  const renderItem = ({ item }: { item: TipoFormacion }) => (
    <TouchableOpacity style={styles.card} onPress={() => openDetail(item)}>
      <View style={{ flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' }}>
        <Text style={styles.name}>{item.nombreTipoFormacion}</Text>
        <View style={[styles.badge, item.estadoTipoFormacion === 'ACTIVO' ? styles.badgeActive : styles.badgeInactive]}>
          <Text style={styles.badgeText}>{item.estadoTipoFormacion === 'ACTIVO' ? 'Activo' : 'Inactivo'}</Text>
        </View>
      </View>

      <Text style={styles.dateText}>
        Creado: {item.fechaTipoFormacion ? new Date(item.fechaTipoFormacion).toLocaleDateString() : '—'}
      </Text>

      <View style={{ position: 'absolute', right: 12, bottom: 12 }}>
        <TouchableOpacity onPress={() => openEdit(item)} style={styles.smallIconButton}>
          <Icon name="pencil" size={18} color="#fff" />
        </TouchableOpacity>
      </View>
    </TouchableOpacity>
  );

  if (loading) return <View style={styles.center}><ActivityIndicator size="large" color="#4f8cff" /></View>;
  if (error) return <View style={styles.center}><Text style={styles.errorText}>{error}</Text></View>;

  return (
    <View style={styles.container}>
      <Text style={styles.title}>Tipos de Formación</Text>

      <View style={styles.searchWrapper}>
        <Icon name="magnify" size={24} />
        <TextInput placeholder="Buscar..." value={searchText} onChangeText={setSearchText} style={styles.searchInput} clearButtonMode="while-editing" />
        <TouchableOpacity style={{ marginLeft: 8 }} onPress={openCreate}>
          <Icon name="plus-circle" size={28} color="#2dce89" />
        </TouchableOpacity>
      </View>

      <FlatList
        data={mostradas}
        keyExtractor={(t, idx) => String(t?.idTF ?? idx)}
        renderItem={renderItem}
        contentContainerStyle={{ paddingBottom: 24 }}
        ListEmptyComponent={<Text style={styles.emptyText}>No hay resultados.</Text>}
      />

      {/* Modal detalle */}
      <Modal isVisible={detailModalVisible} onBackdropPress={() => setDetailModalVisible(false)} animationIn="slideInUp" animationOut="slideOutDown" backdropOpacity={0.5} useNativeDriver>
        <View style={styles.modalContent}>
          <ScrollView>
            <Text style={styles.modalTitle}>{selected?.nombreTipoFormacion}</Text>
            {selected &&
              ([
                ['ID', selected.idTF?.toString() || '—'],
                ['Nombre', selected.nombreTipoFormacion || '—'],
                ['Estado', selected.estadoTipoFormacion || '—'],
                ['Fecha', selected.fechaTipoFormacion ? new Date(selected.fechaTipoFormacion).toLocaleDateString() : '—'],
              ] as [string, string][]).map(([lbl, val]) => (
                <View key={lbl} style={styles.detailRow}>
                  <Text style={styles.detailLabel}>{lbl}:</Text>
                  <Text style={styles.detailValue}>{val}</Text>
                </View>
              ))}
          </ScrollView>

          <View style={{ flexDirection: 'row', justifyContent: 'space-between', marginTop: 12 }}>
            <TouchableOpacity style={[styles.modalAction, { backgroundColor: '#4f8cff' }]} onPress={() => { setDetailModalVisible(false); openEdit(selected!); }}>
              <Text style={styles.modalActionText}>Editar</Text>
            </TouchableOpacity>
            <TouchableOpacity style={[styles.modalAction, { backgroundColor: '#f5365c' }]} onPress={() => selected && handleDelete(selected)}>
              <Text style={styles.modalActionText}>Eliminar</Text>
            </TouchableOpacity>
          </View>
        </View>
      </Modal>

      {/* Modal formulario (crear / editar) */}
      <Modal isVisible={formModalVisible} onBackdropPress={() => setFormModalVisible(false)} animationIn="slideInUp" animationOut="slideOutDown" backdropOpacity={0.5} useNativeDriver>
        <KeyboardAvoidingView behavior={Platform.OS === 'ios' ? 'padding' : undefined}>
          <View style={styles.modalContent}>
            <ScrollView>
              <Text style={styles.modalTitle}>{selected ? 'Editar Tipo' : 'Nueva Tipo'}</Text>

              <Text style={styles.label}>Nombre</Text>
              <TextInput value={nombre} onChangeText={setNombre} style={styles.input} placeholder="Nombre del tipo" />

              <Text style={[styles.label, { marginTop: 10 }]}>Estado</Text>
              <View style={{ flexDirection: 'row', marginTop: 8 }}>
                <TouchableOpacity onPress={() => setEstado('ACTIVO')} style={[styles.stateBtn, estado === 'ACTIVO' ? styles.stateBtnActive : null]}>
                  <Text style={estado === 'ACTIVO' ? styles.stateBtnTextActive : styles.stateBtnText}>Activo</Text>
                </TouchableOpacity>
                <TouchableOpacity onPress={() => setEstado('INACTIVO')} style={[styles.stateBtn, estado === 'INACTIVO' ? styles.stateBtnActive : null]}>
                  <Text style={estado === 'INACTIVO' ? styles.stateBtnTextActive : styles.stateBtnText}>Inactivo</Text>
                </TouchableOpacity>
              </View>
            </ScrollView>

            <View style={{ flexDirection: 'row', justifyContent: 'space-between', marginTop: 12 }}>
              <TouchableOpacity style={[styles.modalAction, { backgroundColor: '#6c757d' }]} onPress={() => setFormModalVisible(false)}>
                <Text style={styles.modalActionText}>Cancelar</Text>
              </TouchableOpacity>
              <TouchableOpacity style={[styles.modalAction, { backgroundColor: '#2dce89' }]} onPress={handleSave} disabled={saving}>
                {saving ? <ActivityIndicator color="#fff" /> : <Text style={styles.modalActionText}>Guardar</Text>}
              </TouchableOpacity>
            </View>
          </View>
        </KeyboardAvoidingView>
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
  name: { fontSize: 18, fontWeight: '600', color: '#222' },
  badge: { paddingHorizontal: 8, paddingVertical: 4, borderRadius: 12 },
  badgeActive: { backgroundColor: '#2dce89' },
  badgeInactive: { backgroundColor: '#f5365c' },
  badgeText: { color: '#fff', fontSize: 12, fontWeight: '600' },
  dateText: { fontSize: 14, color: '#8898aa', marginTop: 8 },
  emptyText: { marginTop: 20, textAlign: 'center', color: '#666', fontStyle: 'italic', fontSize: 16 },
  modalContent: { backgroundColor: '#fff', borderRadius: 16, padding: 16, maxHeight: '80%' },
  modalTitle: { fontSize: 20, fontWeight: '700', color: '#4f8cff', marginBottom: 12 },
  detailRow: { flexDirection: 'row', marginBottom: 10 },
  detailLabel: { width: 120, fontWeight: '600', fontSize: 16, color: '#525f7f' },
  detailValue: { flex: 1, fontSize: 16, color: '#333' },
  modalAction: { flex: 1, marginHorizontal: 6, paddingVertical: 10, borderRadius: 10, justifyContent: 'center', alignItems: 'center' },
  modalActionText: { color: '#fff', fontWeight: '700' },
  label: { fontWeight: '600', color: '#525f7f', marginBottom: 6 },
  input: { backgroundColor: '#fff', borderRadius: 8, paddingHorizontal: 12, height: 44, borderWidth: 1, borderColor: '#eee' },
  stateBtn: { paddingVertical: 8, paddingHorizontal: 12, borderRadius: 8, marginRight: 8, borderWidth: 1, borderColor: '#ddd' },
  stateBtnActive: { backgroundColor: '#4f8cff', borderColor: '#4f8cff' },
  stateBtnText: { color: '#525f7f', fontWeight: '600' },
  stateBtnTextActive: { color: '#fff', fontWeight: '700' },
  smallIconButton: { width: 36, height: 36, borderRadius: 18, backgroundColor: '#4f8cff', justifyContent: 'center', alignItems: 'center' },
});
