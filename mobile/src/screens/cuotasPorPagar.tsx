// src/screens/cuotasPorPagar.tsx
import React, { useCallback, useContext, useEffect, useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ActivityIndicator,
  FlatList,
  TouchableOpacity,
  Alert,
  Modal,
  TextInput,
  ScrollView,
  Platform,
  KeyboardAvoidingView,
} from 'react-native';
import Icon from 'react-native-vector-icons/MaterialCommunityIcons';
import { AuthContext } from '../contexts/AuthContext';
import api from '../api/api';
import { useNavigation } from '@react-navigation/native';

type InscripcionLite = any;
type CuotaLite = { nombreCuota: string; valorCuota: number; [k: string]: any };
type ModalPayload = { inscripcion?: InscripcionLite; cuota?: CuotaLite; cuotaIndex?: number } | null;

const fmtMoney = (v: any) => {
  const n = Number(v) || 0;
  return `$${n.toFixed(2)}`;
};

const safeParseJson = (val: any) => {
  if (!val && val !== 0) return null;
  if (Array.isArray(val)) return val;
  if (typeof val === 'object') return val;
  if (typeof val === 'string') {
    try {
      return JSON.parse(val);
    } catch {
      try {
        return JSON.parse(val.replace(/'/g, '"'));
      } catch {
        return null;
      }
    }
  }
  return null;
};

const normalizeCuotas = (raw: any): CuotaLite[] => {
  if (!raw) return [];
  const parsed = safeParseJson(raw) ?? raw;
  if (!parsed) return [];
  if (Array.isArray(parsed)) {
    return parsed.map((c: any) => ({
      nombreCuota: c.nombreCuota ?? c.nombre ?? c.label ?? 'Cuota',
      valorCuota: Number(c.valorCuota ?? c.valor ?? c.monto ?? c.amount ?? 0) || 0,
      ...c,
    }));
  }
  return Object.keys(parsed).map(k => ({
    nombreCuota: k,
    valorCuota: Number(parsed[k]) || 0,
  }));
};

const fetchCuotasForFormacion = async (idFormacion: number) => {
  if (!idFormacion) return [];
  try {
    const res = await api.get(`/api/formaciones/${idFormacion}/cuotas/`);
    const data = Array.isArray(res.data) ? res.data : res.data?.results ?? [];
    return data.map((c: any) => ({
      nombreCuota: c.nombreCuota ?? c.nombre ?? `Cuota ${c.id ?? ''}`,
      valorCuota: Number(c.valorCuota ?? c.valor ?? c.monto ?? 0) || 0,
      ...c,
    }));
  } catch (e) {
    console.warn('No se pudo obtener cuotas por endpoint para formacion', idFormacion, e);
    return [];
  }
};

// FIX: normalizeCedula ahora quita TODO lo que no sean dígitos
const normalizeCedula = (ced: any) => String(ced ?? '').replace(/\D/g, '');

const CuotasPorPagarScreen = () => {
  const navigation = useNavigation<any>();
  const { user } = useContext(AuthContext);

  const [loading, setLoading] = useState<boolean>(true);
  const [inscripciones, setInscripciones] = useState<InscripcionLite[]>([]);
  const [expandedId, setExpandedId] = useState<number | null>(null);
  const [refreshing, setRefreshing] = useState(false);

  // Modal de pago
  const [modalVisible, setModalVisible] = useState(false);
  const [modalPayload, setModalPayload] = useState<ModalPayload>(null);
  const [referencia, setReferencia] = useState('');
  const [capturaText, setCapturaText] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const loadInscripciones = useCallback(async () => {
    setLoading(true);
    try {
      if (!user) {
        console.log('[Cuotas] user no disponible todavía');
        setInscripciones([]);
        return;
      }

      const userCedRaw = user.cedula ?? user.username ?? '';
      const userCed = normalizeCedula(userCedRaw);

      let endpoint = '/api/inscripcion/';
      if (userCed) {
        endpoint = `/api/inscripcion/usuario/?cedula=${encodeURIComponent(user.cedula ?? userCedRaw)}`;
      } else {
        console.warn('[Cuotas] user sin cédula: consultando /api/inscripcion/ y filtrando localmente');
      }

      console.log('[Cuotas] GET', endpoint);
      const res = await api.get(endpoint);
      console.log('[Cuotas] respuesta cruda:', res.data);

      const todas = Array.isArray(res.data) ? res.data : res.data?.results ?? [];

      const filtered = todas
        .filter((ins: any) => {
          const ced = ins.idPersona_detail?.cedula ?? ins.idPersona?.cedula;
          if (!ced) return false;
          const cedNorm = normalizeCedula(ced);
          return userCed ? (userCed === cedNorm) : true;
        })
        .map((ins: any) => {
          const rawForm = ins.idFormacion_detail ?? ins.idFormacion ?? ins.formacion ?? null;
          const idFormacion = rawForm ? Number(rawForm.idFormacion ?? rawForm.id ?? rawForm.pk ?? 0) : null;
          return {
            ...ins,
            idFormacionResolved: idFormacion,
            idCohorte_detail: ins.idCohorte_detail ?? ins.idCohorte ?? null,
            idFormacion_detail: rawForm ?? null,
            montoPagado: Number(ins.montoPagado ?? ins.pagado ?? 0),
            montoTotal: Number(ins.montoTotal ?? ins.total ?? ins.monto ?? 0),
          };
        });

      const enriched = await Promise.all(
        filtered.map(async (ins: any) => {
          let cuotas: CuotaLite[] = [];
          if (ins.idFormacion_detail) {
            if (Array.isArray(ins.idFormacion_detail.cuotas) && ins.idFormacion_detail.cuotas.length) {
              cuotas = ins.idFormacion_detail.cuotas.map((c: any) => ({
                nombreCuota: c.nombreCuota ?? c.nombre ?? 'Cuota',
                valorCuota: Number(c.valorCuota ?? c.valor ?? c.monto ?? 0) || 0,
                ...c,
              }));
            } else {
              const candidate =
                ins.idFormacion_detail.cuotas_json ??
                ins.idFormacion_detail.cuotasData ??
                ins.idFormacion_detail.inscripcioncuota_set ??
                ins.idFormacion_detail.cuotas;
              if (candidate) cuotas = normalizeCuotas(candidate);
            }
          }

          if ((!cuotas || cuotas.length === 0) && ins.idFormacionResolved) {
            const remote = await fetchCuotasForFormacion(Number(ins.idFormacionResolved));
            cuotas = remote;
          }

          return { ...ins, cuotas: cuotas || [] };
        }),
      );

      console.log('[Cuotas] inscripciones enriquecidas:', enriched);
      setInscripciones(enriched);
    } catch (e: any) {
      console.error('Error cargando inscripciones en CuotasPorPagar', e, e?.response?.data ?? null);
      Alert.alert('Error', e?.response?.data?.detail ?? 'No se pudieron cargar las inscripciones');
      setInscripciones([]);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [user]);

  useEffect(() => {
    loadInscripciones();
  }, [loadInscripciones]);

  const computeCuotasWithStatus = (ins: InscripcionLite) => {
    const cuotas: CuotaLite[] = ins.cuotas ?? [];
    const paidTotal = Number(ins.montoPagado ?? 0);
    let remainingPaid = paidTotal;
    const result = cuotas.map((c: any, idx: number) => {
      const valor = Number(c.valorCuota ?? c.valor ?? c.monto ?? 0) || 0;
      let paid = false;
      if (remainingPaid >= valor && valor > 0) {
        paid = true;
        remainingPaid -= valor;
      }
      if ((c.pagado === true || c.estado === 'PAGADA' || c.estado === 'PAGADO') && !paid) paid = true;
      return { ...c, valorCuota: valor, index: idx, paid };
    });

    const firstUnpaid = result.findIndex((r: any) => !r.paid);
    const final = result.map((r: any) => ({
      ...r,
      disabled: r.paid ? true : (firstUnpaid === -1 ? true : r.index !== firstUnpaid),
    }));

    return { cuotas: final, firstUnpaidIndex: firstUnpaid };
  };

  const handleToggleAccordion = (insId: number) => {
    setExpandedId(prev => (prev === insId ? null : insId));
  };

  const onRefresh = async () => {
    setRefreshing(true);
    await loadInscripciones();
    setRefreshing(false);
  };

  const openPagoModal = (inscripcion: InscripcionLite, cuota: any) => {
    setModalPayload({ inscripcion, cuota, cuotaIndex: cuota.index });
    setReferencia('');
    setCapturaText('');
    setModalVisible(true);
  };

  const closeModal = () => {
    setModalVisible(false);
    setModalPayload(null);
    setReferencia('');
    setCapturaText('');
  };

  const handleSolicitarPago = async () => {
    if (!modalPayload || !modalPayload.inscripcion || !modalPayload.cuota) {
      Alert.alert('Error', 'Datos de pago incompletos');
      return;
    }
    if (!referencia.trim()) {
      Alert.alert('Error', 'Ingrese número de referencia');
      return;
    }
    setSubmitting(true);
    try {
      const payload = {
        idInscripcion:
          modalPayload.inscripcion.idInscripcion ??
          modalPayload.inscripcion.id ??
          modalPayload.inscripcion.pk,
        cuotaIndex: modalPayload.cuotaIndex,
        nombreCuota: modalPayload.cuota.nombreCuota,
        monto: modalPayload.cuota.valorCuota,
        referencia: referencia.trim(),
        captura: capturaText.trim(),
        estado: 'PENDIENTE',
        fechaSolicitud: new Date().toISOString(),
      };

      const res = await api.post('/api/cuota-pagos/solicitar/', payload);

      if (res.status === 200 || res.status === 201) {
        Alert.alert('Solicitud enviada', 'Su pago ha sido enviado y queda pendiente de validación administrativa.');
        closeModal();
        await loadInscripciones();
      } else {
        Alert.alert('Error', 'No se pudo registrar la solicitud de pago. Intenta más tarde.');
      }
    } catch (e: any) {
      console.error('Error al solicitar pago de cuota', e);
      const msg = e?.response?.data?.detail ?? e?.response?.data?.message ?? e?.message ?? 'Error desconocido';
      Alert.alert('Error', msg);
    } finally {
      setSubmitting(false);
    }
  };

  const renderInscripcionItem = ({ item }: { item: InscripcionLite }) => {
    const idKey = item.idInscripcion ?? item.id ?? null;
    const tituloForm = item.idFormacion_detail?.nombreFormacion ?? item.idFormacion_detail?.nombre ?? 'Sin nombre';
    const cohName = item.idCohorte_detail?.nombreCohorte ?? item.idCohorte?.nombreCohorte ?? '—';
    const fecha = item.fechaInscripcion ? new Date(item.fechaInscripcion).toLocaleDateString() : '—';
    const { cuotas: cuotasWithStatus } = computeCuotasWithStatus(item);

    return (
      <View style={styles.card}>
        <TouchableOpacity onPress={() => idKey && handleToggleAccordion(Number(idKey))} style={styles.cardHeader}>
          <View style={{ flex: 1 }}>
            <Text style={styles.cardTitle}>{tituloForm}</Text>
            <Text style={styles.cardSubtitle}>{cohName} · Inscripción: {fecha}</Text>
          </View>
          <View style={styles.chevContainer}>
            <Icon name={expandedId === idKey ? 'chevron-up' : 'chevron-down'} size={22} color="#4f8cff" />
          </View>
        </TouchableOpacity>

        {expandedId === idKey && (
          <View style={styles.cardBody}>
            {cuotasWithStatus.length === 0 ? (
              <View style={styles.emptyRow}>
                <Icon name="calendar-remove" size={28} color="#dee2e6" />
                <Text style={styles.emptyText}>No hay cuotas configuradas para esta inscripción</Text>
              </View>
            ) : (
              <>
                {cuotasWithStatus.map((c: any) => (
                  <View key={String(c.index)} style={styles.cuotaRow}>
                    <View style={{ flex: 1 }}>
                      <Text style={[styles.cuotaNombre, c.paid ? styles.cuotaPaidText : undefined]}>
                        {c.nombreCuota}
                      </Text>
                      <Text style={styles.cuotaSub}>{fmtMoney(c.valorCuota)}</Text>
                    </View>

                    <View style={styles.cuotaActions}>
                      {c.paid ? (
                        <View style={styles.paidBadge}>
                          <Text style={styles.paidBadgeText}>PAGADA</Text>
                        </View>
                      ) : (
                        <TouchableOpacity
                          style={[styles.payButton, c.disabled ? styles.payButtonDisabled : {}]}
                          disabled={c.disabled}
                          onPress={() => openPagoModal(item, c)}
                        >
                          <Text style={[styles.payButtonText, c.disabled ? styles.payButtonTextDisabled : {}]}>Pagar</Text>
                        </TouchableOpacity>
                      )}
                    </View>
                  </View>
                ))}
                <View style={styles.infoRow}>
                  <Text style={styles.smallNote}>
                    Solo puede pagar la primera cuota pendiente. Las demás se habilitan tras la confirmación administrativa.
                  </Text>
                </View>
              </>
            )}
          </View>
        )}
      </View>
    );
  };

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.title}>Cuotas por pagar</Text>
        <Text style={styles.subtitle}>Paga tus cuotas en orden — la administración confirmará los pagos</Text>
      </View>

      {loading ? (
        <View style={styles.center}><ActivityIndicator size="large" color="#4f8cff" /></View>
      ) : inscripciones.length === 0 ? (
        <View style={styles.emptyContainer}>
          {/* ICON FIX: use 'file-multiple' which exists in material-community */}
          <Icon name="file-multiple" size={80} color="#e9ecef" />
          <Text style={styles.emptyTitle}>No tienes inscripciones</Text>
          <Text style={styles.emptySubtitle}>Realiza una inscripción para que se generen las cuotas</Text>
        </View>
      ) : (
        <FlatList
          data={inscripciones}
          keyExtractor={(i) => String(i.idInscripcion ?? i.id ?? Math.random())}
          renderItem={renderInscripcionItem}
          contentContainerStyle={{ padding: 12, paddingBottom: 120 }}
          refreshing={refreshing}
          onRefresh={onRefresh}
        />
      )}

      {/* Modal de Pago */}
      <Modal visible={modalVisible} animationType="slide" transparent>
        <KeyboardAvoidingView behavior={Platform.OS === 'ios' ? 'padding' : undefined} style={styles.modalOverlay}>
          <View style={styles.modalCard}>
            <View style={styles.modalHeader}>
              <Text style={styles.modalTitle}>Pagar cuota</Text>
              <TouchableOpacity onPress={closeModal}>
                <Icon name="close" size={22} color="#6c757d" />
              </TouchableOpacity>
            </View>

            <ScrollView contentContainerStyle={{ padding: 12 }}>
              {modalPayload?.inscripcion && modalPayload?.cuota ? (
                <>
                  <View style={styles.infoBlock}>
                    <Text style={styles.infoLabel}>Formación</Text>
                    <Text style={styles.infoValue}>
                      {modalPayload.inscripcion.idFormacion_detail?.nombreFormacion ?? '—'}
                    </Text>
                  </View>

                  <View style={styles.infoBlock}>
                    <Text style={styles.infoLabel}>Cohorte</Text>
                    <Text style={styles.infoValue}>
                      {modalPayload.inscripcion.idCohorte_detail?.nombreCohorte ?? '—'}
                    </Text>
                  </View>

                  <View style={styles.infoBlock}>
                    <Text style={styles.infoLabel}>Cuota</Text>
                    <Text style={styles.infoValue}>
                      {modalPayload.cuota.nombreCuota} — {fmtMoney(modalPayload.cuota.valorCuota)}
                    </Text>
                  </View>

                  <View style={styles.field}>
                    <Text style={styles.fieldLabel}>Número de referencia *</Text>
                    <TextInput value={referencia} onChangeText={setReferencia} placeholder="Ej: 123456789" style={styles.input} />
                  </View>

                  <View style={styles.field}>
                    <Text style={styles.fieldLabel}>Captura (temporal)</Text>
                    <TextInput value={capturaText} onChangeText={setCapturaText} placeholder="Texto para identificar captura / url" style={styles.input} />
                    <Text style={styles.helper}>Por ahora guardamos texto; en el futuro acepta imagenes</Text>
                  </View>

                  <View style={{ height: 12 }} />

                  <TouchableOpacity style={[styles.submit, submitting ? styles.submitDisabled : {}]} disabled={submitting} onPress={handleSolicitarPago}>
                    <View style={{ flexDirection: 'row', justifyContent: 'center', alignItems: 'center' }}>
                      <Icon name="credit-card-check-outline" size={18} color="#fff" />
                      <Text style={styles.submitText}>{submitting ? 'Enviando...' : 'Solicitar pago (quedará pendiente)'}</Text>
                    </View>
                  </TouchableOpacity>
                </>
              ) : (
                <Text>Datos incompletos</Text>
              )}
            </ScrollView>
          </View>
        </KeyboardAvoidingView>
      </Modal>
    </View>
  );
};

export default CuotasPorPagarScreen;

// styles (igual que antes)
const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#f8f9fa' },
  header: { padding: 16, borderBottomWidth: 1, borderBottomColor: '#e9ecef' },
  title: { fontSize: 20, fontWeight: '700', color: '#343a40' },
  subtitle: { fontSize: 13, color: '#6c757d', marginTop: 6 },

  center: { flex: 1, justifyContent: 'center', alignItems: 'center', padding: 16 },
  card: { backgroundColor: '#fff', borderRadius: 12, marginBottom: 12, overflow: 'hidden', borderWidth: 1, borderColor: '#eef2f6' },
  cardHeader: { flexDirection: 'row', padding: 12, alignItems: 'center' },
  cardTitle: { fontSize: 16, fontWeight: '700', color: '#1a365d' },
  cardSubtitle: { fontSize: 13, color: '#6c757d', marginTop: 4 },
  chevContainer: { paddingLeft: 8, paddingRight: 8 },

  cardBody: { padding: 12, borderTopWidth: 1, borderTopColor: '#f1f3f4' },

  emptyRow: { alignItems: 'center', padding: 18 },
  emptyText: { marginTop: 8, color: '#9aa4b2' },

  cuotaRow: { flexDirection: 'row', alignItems: 'center', paddingVertical: 10, borderBottomWidth: 1, borderBottomColor: '#f4f6f8' },
  cuotaNombre: { fontWeight: '600', color: '#2d3748' },
  cuotaPaidText: { color: '#6c757d', textDecorationLine: 'line-through' },
  cuotaSub: { fontSize: 13, color: '#6c757d', marginTop: 4 },

  cuotaActions: { minWidth: 110, alignItems: 'flex-end' },

  payButton: {
    backgroundColor: '#2b6cb0',
    paddingHorizontal: 14,
    paddingVertical: 8,
    borderRadius: 8,
  },
  payButtonText: { color: '#fff', fontWeight: '700' },
  payButtonDisabled: { backgroundColor: '#cbd5e1' },
  payButtonTextDisabled: { color: '#7b8794' },

  paidBadge: { backgroundColor: '#d4edda', paddingHorizontal: 12, paddingVertical: 6, borderRadius: 12 },
  paidBadgeText: { color: '#155724', fontWeight: '700' },

  infoRow: { marginTop: 10 },
  smallNote: { fontSize: 12, color: '#6c757d', fontStyle: 'italic' },

  emptyContainer: { flex: 1, alignItems: 'center', justifyContent: 'center', padding: 20 },
  emptyTitle: { fontSize: 18, fontWeight: '700', color: '#495057', marginTop: 12 },
  emptySubtitle: { fontSize: 14, color: '#6c757d', marginTop: 6, textAlign: 'center' },

  modalOverlay: { flex: 1, justifyContent: 'center', alignItems: 'center', backgroundColor: 'rgba(0,0,0,0.45)' },
  modalCard: { width: '92%', maxHeight: '85%', backgroundColor: '#fff', borderRadius: 12, overflow: 'hidden' },
  modalHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', padding: 12, borderBottomWidth: 1, borderBottomColor: '#eef2f6' },
  modalTitle: { fontSize: 18, fontWeight: '700', color: '#1a365d' },

  infoBlock: { paddingHorizontal: 4, paddingVertical: 8 },
  infoLabel: { fontSize: 12, color: '#6c757d' },
  infoValue: { fontSize: 15, color: '#2d3748', fontWeight: '600', marginTop: 4 },

  field: { paddingHorizontal: 4, paddingVertical: 8 },
  fieldLabel: { fontSize: 13, color: '#495057', marginBottom: 6, fontWeight: '600' },
  input: { borderWidth: 1, borderColor: '#e6edf3', borderRadius: 8, paddingHorizontal: 12, paddingVertical: Platform.OS === 'ios' ? 12 : 8, backgroundColor: '#fff' },
  helper: { fontSize: 12, color: '#6c757d', marginTop: 6 },

  submit: { backgroundColor: '#2b6cb0', margin: 12, paddingVertical: 12, borderRadius: 10, alignItems: 'center' },
  submitText: { color: '#fff', fontWeight: '700', marginLeft: 8 },
  submitDisabled: { backgroundColor: '#6c757d' },
});
