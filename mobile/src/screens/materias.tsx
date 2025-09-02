// src/screens/materias.tsx
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
  // Picker as RNPicker, // deprecated but kept as fallback comment; we use a simple custom select below
} from 'react-native';
import Icon from 'react-native-vector-icons/MaterialCommunityIcons';
import Modal from 'react-native-modal';
import api from '../api/api';
import { ReloadContext } from '../contexts/ReloadContext';

const { width } = Dimensions.get('window');
const CARD_WIDTH = width - 24;

interface Formacion {
  idFormacion: number;
  nombreFormacion: string;
}

interface Materia {
  idMateria: number;
  idFormacion: number | Formacion | null;
  nombreMateria: string;
  estadoMateria: 'ACTIVO' | 'INACTIVO' | string;
  fechaMateria: string; // ISO date
  // optional friendly name if backend includes it:
  nombreFormacion?: string;
}

/**
 * Notas / supuestos:
 * - Endpoints asumidos: GET/POST /api/materias/  y GET/PUT/DELETE /api/materias/:id/
 * - Para cargar formaciones: GET /api/formaciones/
 * - Si tus URLs o nombres de campo son distintos, ajusta las rutas y mappings dentro de fetchMaterias / handleSave.
 */

export default function PantallaMaterias() {
  const [items, setItems] = useState<Materia[]>([]);
  const [mostradas, setMostradas] = useState<Materia[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchText, setSearchText] = useState('');
  const [detailModalVisible, setDetailModalVisible] = useState(false);
  const [formModalVisible, setFormModalVisible] = useState(false);
  const [selected, setSelected] = useState<Materia | null>(null);
  const [saving, setSaving] = useState(false);

  // Form fields (create / edit)
  const [nombre, setNombre] = useState('');
  const [estado, setEstado] = useState<'ACTIVO' | 'INACTIVO' | string>('ACTIVO');
  const [formaciones, setFormaciones] = useState<Formacion[]>([]);
  const [selectedFormacionId, setSelectedFormacionId] = useState<number | null>(null);

  // Reload context
  const { reloadCount } = useContext(ReloadContext);

  // fetchMaterias
  const fetchMaterias = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.get<Materia[]>('/api/materias/');
      const data = Array.isArray(res.data) ? res.data : [];

      // normalize: ensure nombreFormacion is present if backend returned object in idFormacion
      const normalized = data.map(m => {
        let nombreFormacion = (m as any).nombreFormacion;
        if (!nombreFormacion && m.idFormacion && typeof m.idFormacion === 'object') {
          nombreFormacion = (m.idFormacion as any).nombreFormacion || (m.idFormacion as any).nombre || '';
        }
        return { ...m, nombreFormacion };
      });

      setItems(normalized);
      setMostradas(normalized);
    } catch (err: any) {
      console.error('fetchMaterias error', err);
      setError(err?.message || 'Error al obtener materias');
    } finally {
      setLoading(false);
    }
  }, []);

  const fetchFormaciones = useCallback(async () => {
    try {
      const res = await api.get<Formacion[]>('/api/formaciones/');
      const data = Array.isArray(res.data) ? res.data : [];
      // normalize keys if backend uses different names
      const normalized = data.map(f => ({
        idFormacion: (f as any).idFormacion ?? (f as any).id ?? (f as any).pk ?? (f as any).id_formacion,
        nombreFormacion: (f as any).nombreFormacion ?? (f as any).nombre ?? (f as any).nombre_formacion ?? String((f as any).nombre ?? ''),
      }));
      setFormaciones(normalized);
    } catch (err) {
      console.warn('No se pudieron cargar formaciones (opcional):', err);
      setFormaciones([]);
    }
  }, []);

  // Inicial + cuando se dispare reload desde el header
  useEffect(() => {
    fetchMaterias();
    fetchFormaciones();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [fetchMaterias, fetchFormaciones, reloadCount]);

  useEffect(() => {
    const q = searchText.trim().toLowerCase();
    if (!q) {
      setMostradas(items);
      return;
    }
    setMostradas(
      items.filter(
        m =>
          (m.nombreMateria || '').toLowerCase().includes(q) ||
          (m.estadoMateria || '').toLowerCase().includes(q) ||
          ((m.nombreFormacion || '') as string).toLowerCase().includes(q)
      )
    );
  }, [searchText, items]);

  const openDetail = (t: Materia) => {
    setSelected(t);
    setDetailModalVisible(true);
  };

  const openCreate = () => {
    setSelected(null);
    setNombre('');
    setEstado('ACTIVO');
    setSelectedFormacionId(formaciones.length > 0 ? formaciones[0].idFormacion : null);
    setFormModalVisible(true);
  };

  const openEdit = (t: Materia) => {
    setSelected(t);
    setNombre(t.nombreMateria);
    setEstado(t.estadoMateria || 'ACTIVO');
    // if idFormacion is object or id
    const idF = typeof t.idFormacion === 'object' ? (t.idFormacion as any).idFormacion ?? (t.idFormacion as any).id : (t.idFormacion as number | null);
    setSelectedFormacionId(idF ?? null);
    setFormModalVisible(true);
  };

  const handleSave = async () => {
    if (!nombre.trim()) {
      Alert.alert('Validación', 'El nombre de la materia es requerido');
      return;
    }
    if (!selectedFormacionId) {
      Alert.alert('Validación', 'Selecciona la formación a la que pertenece la materia');
      return;
    }

    setSaving(true);
    try {
      const payload = {
        idFormacion: selectedFormacionId,
        nombreMateria: nombre.trim(),
        estadoMateria: estado,
      };

      if (selected && selected.idMateria) {
        await api.put(`/api/materias/${selected.idMateria}/`, payload);
      } else {
        await api.post('/api/materias/', payload);
      }
      setFormModalVisible(false);
      await fetchMaterias();
    } catch (err: any) {
      console.error('save materia error', err);
      if (err?.response?.status === 403) {
        Alert.alert(
          'Error de permisos',
          'Operación no permitida (403). Verifica que tu sesión sea válida o que el backend acepte tokens (JWT).'
        );
      } else {
        const msg = err?.response?.data?.detail || err?.response?.data || err?.message || 'Error al guardar materia';
        Alert.alert('Error', String(msg));
      }
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = (t: Materia) => {
    Alert.alert(
      'Confirmar eliminación',
      `¿Eliminar materia "${t.nombreMateria}"? Esta acción no puede deshacerse.`,
      [
        { text: 'Cancelar', style: 'cancel' },
        {
          text: 'Eliminar',
          style: 'destructive',
          onPress: async () => {
            try {
              setLoading(true);
              await api.delete(`/api/materias/${t.idMateria}/`);
              await fetchMaterias();
              setDetailModalVisible(false);
            } catch (err: any) {
              console.error('delete materia error', err);
              Alert.alert('Error', err?.message || 'No se pudo eliminar');
            } finally {
              setLoading(false);
            }
          },
        },
      ]
    );
  };

  const renderItem = ({ item }: { item: Materia }) => (
    <TouchableOpacity style={styles.card} onPress={() => openDetail(item)}>
      <View style={{ flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' }}>
        <Text style={styles.name}>{item.nombreMateria}</Text>
        <View style={[styles.badge, item.estadoMateria === 'ACTIVO' ? styles.badgeActive : styles.badgeInactive]}>
          <Text style={styles.badgeText}>{item.estadoMateria === 'ACTIVO' ? 'Activo' : 'Inactivo'}</Text>
        </View>
      </View>

      <Text style={styles.subText}>
        Formación: {item.nombreFormacion ?? (typeof item.idFormacion === 'object' ? (item.idFormacion as any)?.nombreFormacion || (item.idFormacion as any)?.nombre : '—')}
      </Text>

      <Text style={styles.dateText}>
        Creado: {item.fechaMateria ? new Date(item.fechaMateria).toLocaleDateString() : '—'}
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
      <Text style={styles.title}>Materias</Text>

      <View style={styles.searchWrapper}>
        <Icon name="magnify" size={24} />
        <TextInput
          placeholder="Buscar por nombre, formación o estado..."
          value={searchText}
          onChangeText={setSearchText}
          style={styles.searchInput}
          clearButtonMode="while-editing"
        />
        <TouchableOpacity style={{ marginLeft: 8 }} onPress={openCreate}>
          <Icon name="plus-circle" size={28} color="#2dce89" />
        </TouchableOpacity>
      </View>

      <FlatList
        data={mostradas}
        keyExtractor={(t, idx) => String(t?.idMateria ?? idx)}
        renderItem={renderItem}
        contentContainerStyle={{ paddingBottom: 24 }}
        ListEmptyComponent={<Text style={styles.emptyText}>No hay resultados.</Text>}
      />

      {/* Modal detalle */}
      <Modal isVisible={detailModalVisible} onBackdropPress={() => setDetailModalVisible(false)} animationIn="slideInUp" animationOut="slideOutDown" backdropOpacity={0.5} useNativeDriver>
        <View style={styles.modalContent}>
          <ScrollView>
            <Text style={styles.modalTitle}>{selected?.nombreMateria}</Text>
            {selected &&
              ([
                ['ID', String(selected.idMateria ?? '—')],
                ['Nombre', selected.nombreMateria || '—'],
                ['Formación', selected.nombreFormacion ?? (typeof selected.idFormacion === 'object' ? (selected.idFormacion as any)?.nombreFormacion || (selected.idFormacion as any)?.nombre : '—')],
                ['Estado', selected.estadoMateria || '—'],
                ['Fecha', selected.fechaMateria ? new Date(selected.fechaMateria).toLocaleDateString() : '—'],
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
              <Text style={styles.modalTitle}>{selected ? 'Editar Materia' : 'Nueva Materia'}</Text>

              <Text style={styles.label}>Nombre</Text>
              <TextInput value={nombre} onChangeText={setNombre} style={styles.input} placeholder="Nombre de la materia" />

              <Text style={[styles.label, { marginTop: 10 }]}>Formación</Text>
              {/* Simple select: botones list-style to avoid platform Picker issues */}
              <View style={{ backgroundColor: '#fff', borderRadius: 8, borderWidth: 1, borderColor: '#eee', padding: 8 }}>
                {formaciones.length === 0 ? (
                  <Text style={{ fontStyle: 'italic', color: '#666' }}>No hay formaciones cargadas</Text>
                ) : (
                  formaciones.map(f => (
                    <TouchableOpacity
                      key={String(f.idFormacion)}
                      onPress={() => setSelectedFormacionId(f.idFormacion)}
                      style={{
                        paddingVertical: 8,
                        paddingHorizontal: 6,
                        borderRadius: 6,
                        backgroundColor: selectedFormacionId === f.idFormacion ? '#e6f0ff' : 'transparent',
                        marginBottom: 6,
                      }}
                    >
                      <Text style={{ fontWeight: selectedFormacionId === f.idFormacion ? '700' : '600' }}>{f.nombreFormacion}</Text>
                    </TouchableOpacity>
                  ))
                )}
              </View>

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
  name: { fontSize: 18, fontWeight: '600', color: '#222' },
  subText: { fontSize: 14, color: '#525f7f', marginTop: 6 },
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
