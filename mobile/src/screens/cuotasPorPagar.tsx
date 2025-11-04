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

type InscripcionLite = any; // Tipo base para la inscripción
type CuotaLite = { 
  idCuota?: number;
  nombreCuota: string; 
  valorCuota: number; 
  estadoPago?: string; // Estado de InscripcionCuota ('EN ESPERA', 'PENDIENTE', 'PAGADO')
  orden?: number;
  [k: string]: any 
};
type ModalPayload = { inscripcion?: InscripcionLite; cuota?: CuotaLite; } | null;

const fmtMoney = (v: any) => {
  const n = Number(v) || 0;
  return `$${n.toFixed(2)}`;
};

const normalizeCedula = (ced: any) => String(ced ?? '').replace(/\D/g, '');

// Normaliza las cuotas desde inscripcion.inscripcioncuota_set
const normalizeInscripcionCuotas = (ins: any): CuotaLite[] => {
  const cuotasRelacionadas = ins?.inscripcioncuota_set ?? ins?.inscripcion_cuotas ?? ins?.inscripcionCuotas;
  if (Array.isArray(cuotasRelacionadas) && cuotasRelacionadas.length > 0) {
    return cuotasRelacionadas
      .map((ic: any) => {
        // ic puede venir con idCuota como FK object o como id
        const master = ic.idCuota ?? ic.cuota ?? ic.cuota_detail ?? {};
        const idCuota = typeof master === 'object' ? master.idCuota ?? master.id ?? undefined : master;
        const nombreCuota =
          (master && (master.nombreCuota ?? master.nombre)) ||
          ic.nombreCuota ||
          ic.nombre ||
          `Cuota ${idCuota ?? ''}`;
        const valorCuota =
          Number((master && (master.valorCuota ?? master.valor)) ?? ic.valor ?? ic.monto ?? ic.amount ?? 0) || 0;
        const orden = Number((master && master.orden) ?? ic.orden ?? 0) || 0;
        const estadoPago = ic.estadoPago ?? ic.estado ?? ic.pagado ? 'PAGADO' : 'EN ESPERA';
        return {
          ...ic,
          idCuota,
          nombreCuota,
          valorCuota,
          orden,
          estadoPago,
        } as CuotaLite;
      })
      .sort((a: CuotaLite, b: CuotaLite) => (a.orden ?? 0) - (b.orden ?? 0));
  }
  return [];
};

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
  const [fechaPago, setFechaPago] = useState(new Date().toISOString().split('T')[0]);
  const [observaciones, setObservaciones] = useState('');
  const [submitting, setSubmitting] = useState(false);

    const loadInscripciones = useCallback(async () => {
    setLoading(true);
    try {
      console.log('[Cuotas] loadInscripciones start - user:', user);
      if (!user) {
        console.log('[Cuotas] User no disponible todavía');
        setInscripciones([]);
        return;
      }

      const userCedRaw = (user.cedula ?? user.username ?? '').toString();
      const userCed = normalizeCedula(userCedRaw);
      console.log('[Cuotas] cedula detectada:', userCedRaw, '=>', userCed);

      // endpoints a probar (de más específico a más general)
      const candidateEndpoints = [
        // 1) endpoint usuario que a veces requiere cedula query
        userCed ? `/api/inscripcion/usuario/?cedula=${encodeURIComponent(userCedRaw)}` : '/api/inscripcion/usuario/',
        // 2) endpoint general de inscripciones (con query si hay cédula)
        userCed ? `/api/inscripcion/?cedula=${encodeURIComponent(userCedRaw)}` : '/api/inscripcion/',
        // 3) fallback a /api/inscripcion/usuario/ sin query
        '/api/inscripcion/usuario/',
      ];

      let res: any = null;
      let todas: any[] = [];

      // probar secuencialmente hasta obtener data útil
      for (const ep of candidateEndpoints) {
        try {
          console.log('[Cuotas] probando endpoint:', ep);
          res = await api.get(ep);
          console.log('[Cuotas] respuesta recibida (status):', res.status);
          // imprimir shape para debug rápido (solo primeros campos)
          console.log('[Cuotas] response.data (preview):', Array.isArray(res.data) ? `array(${res.data.length})` : JSON.stringify(Object.keys(res.data || {}).slice(0,6)));
          // extraer array robusto
          todas = Array.isArray(res.data) ? res.data : (Array.isArray(res.data?.results) ? res.data.results : []);
          if (todas && todas.length > 0) {
            console.log('[Cuotas] endpoint útil encontrado:', ep, 'items:', todas.length);
            break;
          } else {
            console.log('[Cuotas] endpoint no devolvió items, continuar a siguiente');
          }
        } catch (err) {
          console.warn('[Cuotas] error llamando', ep, (err as any)?.message ?? err);
          // seguir probando next
        }
      }

      // Si no encontramos nada, devolver vacío con log
      if (!todas || todas.length === 0) {
        console.warn('[Cuotas] No se obtuvieron inscripciones de ningún endpoint. Respuesta final:', res?.data ?? null);
        setInscripciones([]);
        return;
      }

      // --- ahora enriquecemos inscripciones con cuotas (versión híbrida) ---
      const enriched = await Promise.all(
        todas.map(async (ins: any) => {
          // 1) si ya trae inscripcioncuota_set usarlo
          let cuotas = normalizeInscripcionCuotas(ins);
          // 2) si no tiene inscripcioncuota_set, intentar extraer desde idFormacion_detail (como antes)
          if ((!cuotas || cuotas.length === 0)) {
            // buscar en distintos lugares donde el backend podría ponerlas
            const possible =
              ins.idFormacion_detail?.cuotas ??
              ins.idFormacion_detail?.prefetched_cuotas ??
              ins.idFormacion_detail?.cuotas_json ??
              ins.idFormacion_detail?.cuotasData ??
              ins.idFormacion_detail?.inscripcioncuota_set ??
              ins.cuotas ??
              null;

            if (possible && (Array.isArray(possible) ? possible.length > 0 : true)) {
              // si es string/json
              if (typeof possible === 'string' || !Array.isArray(possible)) {
                // intentar parseo defensivo (como en tu versión anterior)
                try {
                  const parsed = JSON.parse(possible);
                  cuotas = Array.isArray(parsed) ? parsed.map((c:any)=>({ nombreCuota: c.nombreCuota ?? c.nombre, valorCuota: Number(c.valorCuota ?? c.valor ?? c.monto ?? 0) })) : [];
                } catch {
                  cuotas = [];
                }
              } else {
                cuotas = (possible as any[]).map((c: any) => ({
                  nombreCuota: c.nombreCuota ?? c.nombre ?? c.label ?? 'Cuota',
                  valorCuota: Number(c.valorCuota ?? c.valor ?? c.monto ?? c.amount ?? 0) || 0,
                  ...c,
                }));
              }
            }
          }

          // 3) fallback: si aún no hay cuotas y existe idFormacion, llamar al endpoint de formaciones
          if ((!cuotas || cuotas.length === 0)) {
            const rawForm = ins.idFormacion_detail ?? ins.idFormacion ?? ins.formacion ?? null;
            const idFormacion = rawForm ? Number(rawForm.idFormacion ?? rawForm.id ?? rawForm.pk ?? 0) : null;
            if (idFormacion) {
              try {
                const remote = await api.get(`/api/formaciones/${idFormacion}/cuotas/`);
                const data = Array.isArray(remote.data) ? remote.data : remote.data?.results ?? [];
                cuotas = data.map((c: any) => ({
                  nombreCuota: c.nombreCuota ?? c.nombre ?? `Cuota ${c.id ?? ''}`,
                  valorCuota: Number(c.valorCuota ?? c.valor ?? c.monto ?? 0) || 0,
                  ...c,
                }));
              } catch (err) {
                  console.warn('[Cuotas] no se pudo obtener cuotas por formacion', idFormacion, (err as any)?.message ?? err);
                }
            }
          }

          return { ...ins, cuotas: cuotas || [] };
        })
      );

      console.log('[Cuotas] inscripciones enriquecidas count:', enriched.length);
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

  // --- LÓGICA DE ESTADO DE CUOTAS (MEJORADA) ---
  const computeCuotasWithStatus = (ins: InscripcionLite) => {
    const cuotas: CuotaLite[] = ins.cuotas ?? [];

    // REGLA: Solo mostrar cuotas si la inscripción está 'PAGADO'
    if ((ins.estadoPago ?? '').toUpperCase() !== 'PAGADO') {
      return { cuotas: [], firstUnpaidIndex: -1, isPagada: false };
    }

    // Buscar la primera cuota en estado 'EN ESPERA' (o similar)
    const firstUnpaidIndex = cuotas.findIndex(c => (c.estadoPago ?? '').toUpperCase() === 'EN ESPERA');

    const final = cuotas.map((r: any, idx: number) => {
      const estado = (r.estadoPago ?? '').toUpperCase();
      const disabled = estado === 'PAGADO' || estado === 'PENDIENTE' || (firstUnpaidIndex !== -1 && idx !== firstUnpaidIndex);
      return {
        ...r,
        estadoPago: estado,
        disabled,
      };
    });

    return { cuotas: final, firstUnpaidIndex, isPagada: true };
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
    setModalPayload({ inscripcion, cuota });
    setReferencia('');
    setFechaPago(new Date().toISOString().split('T')[0]);
    setObservaciones('');
    setModalVisible(true);
  };

  const closeModal = () => {
    setModalVisible(false);
    setModalPayload(null);
    setReferencia('');
    setObservaciones('');
  };

  // --- LÓGICA DE PAGO (ACTUALIZADA) ---
  const handleSolicitarPago = async () => {
    if (!modalPayload || !modalPayload.inscripcion || !modalPayload.cuota) {
      Alert.alert('Error', 'Datos de pago incompletos');
      return;
    }
    if (!referencia.trim()) {
      Alert.alert('Error', 'Ingrese número de referencia');
      return;
    }
    if (!fechaPago.trim()) {
      Alert.alert('Error', 'Ingrese la fecha del pago');
      return;
    }

    setSubmitting(true);
    try {
      const payload = {
        idInscripcion: modalPayload.inscripcion.idInscripcion ?? modalPayload.inscripcion.id ?? modalPayload.inscripcion.pk,
        idCuota: modalPayload.cuota.idCuota ?? modalPayload.cuota.id ?? null,
        nombreCuota: modalPayload.cuota.nombreCuota,
        monto: Number(modalPayload.cuota.valorCuota) || 0,
        referencia: referencia.trim(),
        fechaPago: fechaPago,
        observaciones: observaciones.trim(),
        formaPago: 'TRANSFERENCIA', // Ajusta si usas otro string (PAGO_MOVIL, etc.)
      };

      // Endpoint corregido para crear pagos de cuota (ajusta si tu backend usa otro path)
      const res = await api.post('/api/pagos/cuota/create/', payload);

      if (res.status === 200 || res.status === 201) {
        Alert.alert('Solicitud enviada', 'Su pago ha sido enviado y queda pendiente de validación administrativa.');
        closeModal();
        await loadInscripciones(); // Recarga los datos
      } else {
        const msg = res.data?.message || res.data?.error || 'No se pudo registrar la solicitud de pago.';
        Alert.alert('Error', msg);
      }
    } catch (e: any) {
      console.error('Error al solicitar pago de cuota', e.response?.data || e);
      // Formatear errores de validación si vienen en e.response.data.errors
      const errors = e?.response?.data?.errors;
      let msg = 'Error desconocido';
      if (errors && typeof errors === 'object') {
        msg = Object.keys(errors)
          .map(key => `${key}: ${Array.isArray(errors[key]) ? errors[key].join(', ') : errors[key]}`)
          .join('\n');
      } else {
        msg = e?.response?.data?.message || e?.message || 'Error desconocido';
      }
      Alert.alert('Error al enviar el pago', msg);
    } finally {
      setSubmitting(false);
    }
  };

  const renderInscripcionItem = ({ item }: { item: InscripcionLite }) => {
    const idKey = item.idInscripcion ?? item.id ?? null;
    const tituloForm = item.idFormacion_detail?.nombreFormacion ?? item.idFormacion_detail?.nombre ?? 'Sin nombre';
    const cohName = item.idCohorte_detail?.nombreCohorte ?? item.idCohorte?.nombreCohorte ?? '—';
    const fecha = item.fechaInscripcion ? new Date(item.fechaInscripcion).toLocaleDateString() : '—';

    const { cuotas: cuotasWithStatus, isPagada } = computeCuotasWithStatus(item);

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
            {!isPagada ? (
              <View style={styles.emptyRow}>
                <Icon name="alert-circle-outline" size={28} color="#856404" />
                <Text style={styles.emptyText}>Las cuotas estarán disponibles una vez se confirme el pago de su inscripción.</Text>
              </View>
            ) : cuotasWithStatus.length === 0 ? (
              <View style={styles.emptyRow}>
                <Icon name="calendar-remove" size={28} color="#dee2e6" />
                <Text style={styles.emptyText}>No hay cuotas configuradas para esta inscripción.</Text>
              </View>
            ) : (
              <>
                {cuotasWithStatus.map((c: CuotaLite, index: number) => (
                  <View key={String(c.idCuota ?? index)} style={styles.cuotaRow}>
                    <View style={{ flex: 1 }}>
                      <Text style={[styles.cuotaNombre, c.estadoPago === 'PAGADO' ? styles.cuotaPaidText : {}]}>
                        {c.nombreCuota}
                      </Text>
                      <Text style={styles.cuotaSub}>{fmtMoney(c.valorCuota)}</Text>
                    </View>

                    <View style={styles.cuotaActions}>
                      {c.estadoPago === 'PAGADO' ? (
                        <View style={styles.paidBadge}>
                          <Text style={styles.paidBadgeText}>PAGADA</Text>
                        </View>
                      ) : c.estadoPago === 'PENDIENTE' ? (
                        <View style={styles.pendingBadge}>
                          <Text style={styles.paidBadgeText}>PENDIENTE</Text>
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
                    Solo puede pagar la primera cuota pendiente ('EN ESPERA'). Las demás se habilitan tras la confirmación.
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
                    <Text style={styles.fieldLabel}>Fecha de Pago *</Text>
                    <TextInput value={fechaPago} onChangeText={setFechaPago} placeholder="AAAA-MM-DD" style={styles.input} />
                    <Text style={styles.helper}>Formato: AAAA-MM-DD</Text>
                  </View>

                  <View style={styles.field}>
                    <Text style={styles.fieldLabel}>Observaciones (Opcional)</Text>
                    <TextInput value={observaciones} onChangeText={setObservaciones} placeholder="Ej: Pago cuota 1" style={styles.input} />
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

// styles
const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#f8f9fa' },
  header: { padding: 16, borderBottomWidth: 1, borderBottomColor: '#e9ecef', backgroundColor: '#fff' },
  title: { fontSize: 20, fontWeight: '700', color: '#343a40' },
  subtitle: { fontSize: 13, color: '#6c757d', marginTop: 6 },

  center: { flex: 1, justifyContent: 'center', alignItems: 'center', padding: 16 },
  card: { backgroundColor: '#fff', borderRadius: 12, marginBottom: 12, overflow: 'hidden', borderWidth: 1, borderColor: '#eef2f6' },
  cardHeader: { flexDirection: 'row', padding: 12, alignItems: 'center' },
  cardTitle: { fontSize: 16, fontWeight: '700', color: '#1a365d' },
  cardSubtitle: { fontSize: 13, color: '#6c757d', marginTop: 4 },
  chevContainer: { paddingLeft: 8, paddingRight: 8 },

  cardBody: { padding: 12, borderTopWidth: 1, borderTopColor: '#f1f3f4' },

  emptyRow: { alignItems: 'center', padding: 18, flexDirection: 'row', backgroundColor: '#fff8e1', borderRadius: 8 },
  emptyText: { flex: 1, marginLeft: 10, color: '#856404' },

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
  pendingBadge: { backgroundColor: '#ffeeba', paddingHorizontal: 12, paddingVertical: 6, borderRadius: 12 },
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
