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
type CuotaLite = {
  idCuota?: number; // cuota formacion id
  inscripcionCuotaId?: number; // PK de InscripcionCuota (si viene)
  nombreCuota: string;
  valorCuota: number;
  estadoPago?: string;
  orden?: number;
  // campos extra que usaremos en UI
  disabled?: boolean;
  pendingPayment?: boolean;      // true si hay un PagoTemporal no confirmado sobre la cuota
  pagoConfirmado?: boolean;      // true si el PagoTemporal resultó confirmado por admin
  pagoTemporalId?: number | null;
  [k: string]: any;
};
type ModalPayload = { inscripcion?: InscripcionLite; cuota?: CuotaLite } | null;

const fmtMoney = (v: any) => {
  const n = Number(v) || 0;
  return `$${n.toFixed(2)}`;
};

const normalizeCedula = (ced: any) => String(ced ?? '').replace(/\D/g, '');

// Mejorada: guardamos inscripcionCuotaId (pk) y cuotaFormacionId (idCuota)
const normalizeInscripcionCuotas = (ins: any): CuotaLite[] => {
  const cuotasRelacionadas = ins?.inscripcioncuota_set ?? ins?.inscripcion_cuotas ?? ins?.inscripcionCuotas;
  if (Array.isArray(cuotasRelacionadas) && cuotasRelacionadas.length > 0) {
    return cuotasRelacionadas
      .map((ic: any) => {
        // 'master' representa la cuotaFormacion si existe
        const master = ic.idCuota ?? ic.cuota ?? ic.cuota_detail ?? {};
        const cuotaFormacionId = typeof master === 'object' ? (master.idCuota ?? master.id ?? undefined) : master;
        const inscripcionCuotaId = ic.id ?? ic.pk ?? ic.idInscripcionCuota ?? undefined;
        const nombreCuota =
          (master && (master.nombreCuota ?? master.nombre)) || ic.nombreCuota || ic.nombre || `Cuota ${cuotaFormacionId ?? ''}`;
        const valorCuota =
          Number((master && (master.valorCuota ?? master.valor)) ?? ic.valor ?? ic.monto ?? ic.amount ?? 0) || 0;
        const orden = Number((master && master.orden) ?? ic.orden ?? 0) || 0;
        const estadoPago = (ic.pagado ? 'PAGADO' : (ic.estadoPago ?? ic.estado ?? 'EN ESPERA'));
        return {
          ...ic,
          idCuota: cuotaFormacionId,
          inscripcionCuotaId,
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

  // Modal
  const [modalVisible, setModalVisible] = useState(false);
  const [modalPayload, setModalPayload] = useState<ModalPayload>(null);
  const [referencia, setReferencia] = useState('');
  const [fechaPago, setFechaPago] = useState(new Date().toISOString().split('T')[0]);
  const [observaciones, setObservaciones] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const detectPagoInscripcionConfirmado = (ins: any) => {
    if (ins?.pagoInscripcionConfirmado === true || ins?.pago_inscripcion_confirmada === true) return true;

    const nota =
      ins?.nota_inscripcion_detail ??
      ins?.nota_inscripcion ??
      ins?.nota ??
      (ins?.notas && Array.isArray(ins.notas) ? ins.notas[0] : null) ??
      null;
    if (nota && typeof nota.estado === 'string' && nota.estado.toUpperCase() === 'PAGADA') return true;

    const pagos =
      ins?.pago_temporal_set ??
      ins?.pagos_temporales ??
      ins?.pagostemporales ??
      ins?.pago_temporales ??
      ins?.pagos ??
      null;
    if (Array.isArray(pagos) && pagos.some((p: any) => p?.confirmado === true || String(p?.confirmado).toLowerCase() === 'true')) {
      return true;
    }

    if (ins?.inscripcionPagoConfirmado === true) return true;

    return false;
  };

  const loadInscripciones = useCallback(async () => {
    setLoading(true);
    try {
      if (!user) {
        setInscripciones([]);
        return;
      }

      const userCedRaw = (user.cedula ?? user.username ?? '').toString();
      const userCed = normalizeCedula(userCedRaw);

      const candidateEndpoints = [
        userCed ? `/api/inscripcion/usuario/?cedula=${encodeURIComponent(userCedRaw)}` : '/api/inscripcion/usuario/',
        userCed ? `/api/inscripcion/?cedula=${encodeURIComponent(userCedRaw)}` : '/api/inscripcion/',
        '/api/inscripcion/usuario/',
      ];

      let res: any = null;
      let todas: any[] = [];

      for (const ep of candidateEndpoints) {
        try {
          res = await api.get(ep);
          todas = Array.isArray(res.data) ? res.data : (Array.isArray(res.data?.results) ? res.data.results : []);
          if (todas && todas.length > 0) break;
        } catch (err) {
          // seguir probando
        }
      }

      if (!todas || todas.length === 0) {
        setInscripciones([]);
        return;
      }

      const enriched = await Promise.all(
        todas.map(async (ins: any) => {
          let cuotas = normalizeInscripcionCuotas(ins);

          // Si no hay cuotas, intentar otros lugares (fallback)
          if ((!cuotas || cuotas.length === 0)) {
            const possible =
              ins.idFormacion_detail?.cuotas ??
              ins.idFormacion_detail?.prefetched_cuotas ??
              ins.idFormacion_detail?.cuotas_json ??
              ins.idFormacion_detail?.cuotasData ??
              ins.idFormacion_detail?.inscripcioncuota_set ??
              ins.cuotas ??
              null;

            if (possible) {
              if (typeof possible === 'string' || !Array.isArray(possible)) {
                try {
                  const parsed = JSON.parse(possible);
                  cuotas = Array.isArray(parsed) ? parsed.map((c: any) => ({ nombreCuota: c.nombreCuota ?? c.nombre, valorCuota: Number(c.valorCuota ?? c.valor ?? c.monto ?? 0) })) : [];
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

          // fallback por idFormacion si todavía no hay cuotas
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
                  idCuota: c.idCuota ?? c.id ?? c.pk ?? undefined,
                  ...c,
                }));
              } catch {
                // ignore
              }
            }
          }

          // --- Detectar pagos temporales y relacionarlos con cuotas ---
          const pagos =
            ins?.pago_temporal_set ??
            ins?.pagos_temporales ??
            ins?.pagostemporales ??
            ins?.pago_temporales ??
            ins?.pagos ??
            ins?.pagostemporales_prefetch ??
            [];

          // Construir copia inmuble de cuotas para no mutar la respuesta original
          const cuotasCopy: CuotaLite[] = (cuotas || []).map((c: any) => ({ ...c }));

          // intenta relacionar pagos con cuotas por: 
          //  A) InscripcionCuota.id (si la nota/pago trae ese id)
          //  B) CuotaFormacion.id (rel.idCuota.idCuota o rel.idCuota)
          //  C) fallback por monto + nombre
          for (const pago of pagos) {
            try {
              const confirmado = pago?.confirmado === true || String(pago?.confirmado).toLowerCase() === 'true';
              const nota = pago?.idNota ?? pago?.nota ?? pago?.idNota_detail ?? pago?.nota_detail;

              let related_inscripcion_cuota_id: number | null = null;
              let related_cf_id: number | null = null;

              // A) revisar relaciones dentro de la nota
              if (nota && Array.isArray(nota?.relaciones) && nota.relaciones.length > 0) {
                // buscar la primera relación que tenga idCuota
                for (const rel of nota.relaciones) {
                  if (!rel) continue;
                  // rel.idCuota puede venir como objeto (inscripcioncuota o cuotaformacion) o como id numérico
                  const relCuota = rel?.idCuota ?? rel?.id_cuota ?? rel?.idCuota_id;
                  if (relCuota) {
                    if (typeof relCuota === 'object') {
                      // si el objeto tiene 'id' -> probablemente InscripcionCuota
                      if (relCuota.id) related_inscripcion_cuota_id = Number(relCuota.id);
                      // si tiene 'idCuota' -> probablemente CuotaFormacion
                      if (relCuota.idCuota) related_cf_id = Number(relCuota.idCuota);
                      // a veces vienen con pk/id diferente
                      if (!related_inscripcion_cuota_id && (relCuota.pk || relCuota.id_inscripcion_cuota)) {
                        related_inscripcion_cuota_id = Number(relCuota.pk ?? relCuota.id_inscripcion_cuota);
                      }
                    } else {
                      // es un id numérico -> intentar tratarlo como cuotaFormacion id (más frecuente)
                      related_cf_id = Number(relCuota);
                    }
                  }
                }
              }

              // B) revisar si el pago trae un campo directo hacia la inscripcion_cuota o cuota
              if (!related_inscripcion_cuota_id) {
                related_inscripcion_cuota_id = Number(pago?.inscripcionCuotaId ?? pago?.idInscripcionCuota ?? pago?.inscripcion_cuota_id ?? NaN) || null;
              }
              if (!related_cf_id) {
                related_cf_id = Number(pago?.idCuota?.idCuota ?? pago?.idCuota ?? pago?.cuota_id ?? NaN) || null;
              }

              // C) fallback por monto y (opcionalmente) nombre
              let matchedIndex = -1;
              if (related_inscripcion_cuota_id) {
                matchedIndex = cuotasCopy.findIndex((c) => Number(c.inscripcionCuotaId || 0) === Number(related_inscripcion_cuota_id));
              }
              if (matchedIndex === -1 && related_cf_id) {
                matchedIndex = cuotasCopy.findIndex((c) => Number(c.idCuota || 0) === Number(related_cf_id));
              }
              if (matchedIndex === -1) {
                // por monto + nombre como último recurso
                matchedIndex = cuotasCopy.findIndex((c) => {
                  const sameAmount = Number(c.valorCuota || 0) === Number(pago?.monto ?? pago?.amount ?? 0);
                  // si hay nombre en la nota/observaciones intentar matchear
                  const obs = String(pago?.observaciones ?? pago?.observacion ?? '');
                  const nameMatch = obs && String(c.nombreCuota ?? '').length > 0 ? obs.toLowerCase().includes(String(c.nombreCuota ?? '').toLowerCase()) : true;
                  return sameAmount && nameMatch;
                });
              }

              if (matchedIndex !== -1) {
                const target = cuotasCopy[matchedIndex];
                target.pendingPayment = !confirmado;
                target.pagoConfirmado = confirmado;
                target.disabled = !confirmado;
                target.estadoPago = confirmado ? 'PAGADO' : 'PENDIENTE';
                target.pagoTemporalId = pago?.idPagoTemporal ?? pago?.id ?? null;
                cuotasCopy[matchedIndex] = target;
              }
            } catch (err) {
              // no bloquear si hay datos raros
              // console.warn('Error al relacionar pago -> cuota', err);
            }
          }

          // Detectar confirmación del pago inicial (inscripción)
          const pagoConfirmado = detectPagoInscripcionConfirmado(ins);

          return { ...ins, cuotas: cuotasCopy || [], pagoInscripcionConfirmado: pagoConfirmado };
        }),
      );

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

    // Requerimos pago de inscripción confirmado para habilitar pagos de cuotas
    const pagoConfirmado = !!ins.pago_inscripcion_confirmada || !!ins.pagoInscripcionConfirmado || !!ins.pagoInscripcionConfirmado;

    // Si la inscripción no está confirmada: bloqueamos todo
    if (!pagoConfirmado) {
      const resultBlocked = (cuotas || []).map((c: any) => ({
        ...c,
        estadoPago: (c.estadoPago ?? '').toUpperCase() || 'BLOQUEADA',
        disabled: true,
      }));
      return { cuotas: resultBlocked, firstUnpaidIndex: -1, isPagada: false, pagoConfirmado: false };
    }

    // Normal: localizar la primera cuota que esté EN ESPERA y que no tenga pago pendiente
    const normalized = (cuotas || []).map((c: any) => ({
      ...c,
      estadoPago: (c.estadoPago ?? '').toUpperCase(),
      valorCuota: Number(c.valorCuota ?? c.valor ?? c.monto ?? 0) || 0,
      pendingPayment: !!c.pendingPayment,
      pagoConfirmado: !!c.pagoConfirmado,
    }));

    // Encontrar el primer índice que realmente se puede pagar (EN ESPERA y no pendingPayment)
    const firstUnpaidIndex = normalized.findIndex((c: any) =>
      (c.estadoPago === 'EN ESPERA' || c.estadoPago === '' || c.estadoPago === 'EN_ESPERA') && !c.pendingPayment
    );

    const final = normalized.map((r: any, idx: number) => {
      const estado = r.estadoPago ?? '';
      // disabled si:
      // - ya está PAGADO
      // - ya tiene un pago pendiente (PENDIENTE)
      // - o no es la primera cuota pendiente (orden)
      const disabled = estado === 'PAGADO' || r.pendingPayment === true || (firstUnpaidIndex !== -1 && idx !== firstUnpaidIndex);
      return { ...r, estadoPago: estado, disabled };
    });

    return { cuotas: final, firstUnpaidIndex, isPagada: true, pagoConfirmado: true };
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
    // Prevención: si esta cuota tiene pendingPayment -> no abrir modal
    if (cuota.pendingPayment) {
      Alert.alert('Pago en revisión', 'Ya existe un pago en revisión para esta cuota. Espere la confirmación administrativa.');
      return;
    }
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
        idInscripcion: modalPayload.inscripcion.idInscripcion,
        nombreCuota: modalPayload.cuota.nombreCuota,
        monto: modalPayload.cuota.valorCuota,
        referencia: referencia.trim(),
        observaciones: observaciones.trim(),
      };

      console.log('[Pago Cuota] Enviando payload:', payload);

      const res = await api.post('/api/pagos/cuota/create/', payload);

      // Backend devuelve { success: True, message: ..., data: { idPagoTemporal, idNota, numeroNota, monto, confirmado } }
      if (res.status === 200 || res.status === 201) {
        const data = res.data?.data ?? res.data;
        const confirmado = !!data?.confirmado;
        // Mensajes UX
        if (confirmado) {
          Alert.alert('Pago confirmado', 'El pago fue confirmado. Ahora puedes pagar la siguiente cuota.');
        } else {
          Alert.alert('Solicitud enviada', 'Su pago ha sido enviado y queda pendiente de validación administrativa.');
        }

        // Actualización local optimista: marcar la cuota como PENDIENTE y deshabilitar / o PAGADO si confirmado
        setInscripciones(prev => {
          return prev.map((ins: any) => {
            const targetInsId = modalPayload?.inscripcion?.idInscripcion ?? modalPayload?.inscripcion?.id ?? null;
            if (targetInsId && ins.idInscripcion !== targetInsId) return ins;

            const targetNombre = String(modalPayload?.cuota?.nombreCuota ?? modalPayload?.cuota?.nombre ?? '').toLowerCase();

            const cuotas = (ins.cuotas || []).map((c: any) => {
              const currentName = String(c.nombreCuota ?? c.nombre ?? '').toLowerCase();
              if (targetNombre !== '' && currentName === targetNombre) {
                return {
                  ...c,
                  estadoPago: confirmado ? 'PAGADO' : 'PENDIENTE',
                  disabled: !confirmado,
                  pendingPayment: !confirmado,
                  pagoConfirmado: confirmado,
                  pagoTemporalId: data?.idPagoTemporal ?? c.pagoTemporalId ?? null,
                };
              }
              return c;
            });
            return { ...ins, cuotas };
          });
        });

        closeModal();
        // refrescar para traer datos "oficiales" del backend
        await loadInscripciones();
      } else {
        const msg = res.data?.message || res.data?.error || 'No se pudo registrar la solicitud de pago.';
        Alert.alert('Error', msg);
      }
    } catch (e: any) {
      console.error('Error al solicitar pago de cuota', e.response?.data || e);

      const errors = e?.response?.data?.errors ?? e?.response?.data?.error ?? null;
      let msg = 'Error desconocido';
      if (errors) {
        if (typeof errors === 'string') msg = errors;
        else if (typeof errors === 'object') {
          msg = Object.keys(errors)
            .map((key) => `${key}: ${Array.isArray(errors[key]) ? errors[key].join(', ') : String(errors[key])}`)
            .join('\n');
        } else msg = String(errors);
      } else {
        msg = e?.response?.data?.message || e?.response?.data?.detail || e?.message || 'Error desconocido';
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

    const { cuotas: cuotasWithStatus, isPagada, pagoConfirmado } = computeCuotasWithStatus(item);

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
            {!pagoConfirmado && (
              <View style={styles.emptyRow}>
                <Icon name="alert-circle-outline" size={22} color="#856404" />
                <Text style={styles.emptyText}>
                  Las cuotas están visibles, pero no se pueden pagar hasta confirmar el pago de la inscripción.
                </Text>
              </View>
            )}

            {cuotasWithStatus.length === 0 ? (
              <View style={[styles.emptyRow, !pagoConfirmado ? {} : {}]}>
                <Icon name="calendar-remove" size={28} color="#dee2e6" />
                <Text style={styles.emptyText}>No hay cuotas configuradas para esta inscripción.</Text>
              </View>
            ) : (
              <>
                {cuotasWithStatus.map((c: CuotaLite, index: number) => (
                  <View key={String(c.idCuota ?? c.inscripcionCuotaId ?? index)} style={styles.cuotaRow}>
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
                      ) : c.estadoPago === 'PENDIENTE' || c.pendingPayment ? (
                        <View style={styles.pendingBadge}>
                          <Text style={styles.paidBadgeText}>{c.pagoConfirmado ? 'CONFIRMADO' : 'EN REVISIÓN'}</Text>
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

/* estilos: pega tus estilos existentes (sin cambios) */
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
  emptyRow: { alignItems: 'center', padding: 12, flexDirection: 'row', backgroundColor: '#fff8e1', borderRadius: 8 },
  emptyText: { flex: 1, marginLeft: 10, color: '#856404' },
  cuotaRow: { flexDirection: 'row', alignItems: 'center', paddingVertical: 10, borderBottomWidth: 1, borderBottomColor: '#f4f6f8' },
  cuotaNombre: { fontWeight: '600', color: '#2d3748' },
  cuotaPaidText: { color: '#6c757d', textDecorationLine: 'line-through' },
  cuotaSub: { fontSize: 13, color: '#6c757d', marginTop: 4 },
  cuotaActions: { minWidth: 110, alignItems: 'flex-end' },
  payButton: { backgroundColor: '#2b6cb0', paddingHorizontal: 14, paddingVertical: 8, borderRadius: 8 },
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
