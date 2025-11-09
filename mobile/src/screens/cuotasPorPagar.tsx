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

// --- Tipos (relajados) ---
type CuotaLite = any;
type InscripcionLite = any;
type ModalPayload = { inscripcion?: InscripcionLite; cuota?: CuotaLite } | null;

const fmtMoney = (v: any) => {
  const n = Number(v) || 0;
  return `$${n.toFixed(2)}`;
};

const normalizeCedula = (ced: any) => String(ced ?? '').replace(/\D/g, '');

const extractCuotasFromInscripcion = (ins: any): CuotaLite[] => {
  const sources = [
    ins.cuotas,
    ins.inscripcioncuota_set,
    ins.inscripcion_cuotas,
    ins.inscripcionCuotas,
    ins.idFormacion_detail?.cuotas,
    ins.idFormacion_detail?.prefetched_cuotas,
    ins.idFormacion_detail?.cuotas_json,
  ];

  for (const s of sources) {
    if (!s) continue;
    try {
      if (typeof s === 'string') {
        const parsed = JSON.parse(s);
        if (Array.isArray(parsed)) return parsed;
        continue;
      }
      if (Array.isArray(s) && s.length > 0) {
        const mapped = s.map((ic: any) => {
          const idInscripcionCuota = ic.id ?? ic.pk ?? null;
          const idCuotaObj = ic.idCuota ?? ic.cuota ?? ic.cuota_detail ?? ic.idCuota_id ?? null;
          const idCuota =
            typeof idCuotaObj === 'object' ? (idCuotaObj.idCuota ?? idCuotaObj.id ?? idCuotaObj.pk ?? null) : idCuotaObj;
          const nombreCuota = (ic.nombreCuota ?? ic.nombre ?? (idCuotaObj && idCuotaObj.nombreCuota) ?? `Cuota ${idCuota ?? ''}`);
          const valorCuota = Number(ic.valorCuota ?? ic.valor ?? ic.monto ?? (idCuotaObj && (idCuotaObj.valorCuota ?? idCuotaObj.valor)) ?? 0) || 0;
          const orden = Number(ic.orden ?? (idCuotaObj && idCuotaObj.orden) ?? 0) || 0;
          const estadoPago = ic.estadoPago ?? ic.estado ?? (ic.pagado ? 'PAGADO' : 'EN ESPERA');
          return {
            id: idInscripcionCuota,
            idCuota,
            nombreCuota,
            valorCuota,
            orden,
            estadoPago: String(estadoPago).toUpperCase(),
            __raw: ic,
          };
        });
        return mapped.sort((a: any, b: any) => (a.orden ?? 0) - (b.orden ?? 0));
      }
    } catch (err) {
      // seguir
    }
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

  // pagos locales pendientes (optimista) que aún no aparecen confirmados en backend
  const [pendingLocalPayments, setPendingLocalPayments] = useState<any[]>([]);

  const detectPagoInscripcionConfirmado = (ins: any) => {
    if (ins?.pago_inscripcion_confirmada === true || ins?.pagoInscripcionConfirmado === true || ins?.inscripcionPagoConfirmado === true) return true;

    const pagos = ins?.pago_temporal_set ?? ins?.pagos ?? ins?.pagostemporales ?? ins?.pagos_temporales ?? [];
    if (Array.isArray(pagos) && pagos.some((p: any) => p?.confirmado === true || String(p?.confirmado).toLowerCase() === 'true')) return true;

    const notas = ins?.notas ?? ins?.nota_inscripcion_detail ?? [];
    if (Array.isArray(notas) && notas.some((n: any) => (n?.tipoArticulo ?? '').toString().toUpperCase() === 'INSCRIPCION' && (n?.estado ?? '').toString().toUpperCase() === 'PAGADO')) return true;

    return false;
  };

  // Reaplica pagos locales pendientes sobre el estado actual de inscripciones (para mantener "EN REVISIÓN")
  const reapplyLocalPendings = useCallback((pendings: any[]) => {
    if (!pendings || pendings.length === 0) return;
    
    console.log('[Cuotas-debug] Reaplicando', pendings.length, 'pagos locales pendientes');
    
    setInscripciones(current => current.map((ins: any) => {
      const curInsId = ins.idInscripcion ?? ins.id ?? null;
      const relatedPendings = pendings.filter(p => p.insId === curInsId);
      
      if (!relatedPendings.length) return ins;
      
      const cuotas = (ins.cuotas || []).map((c: any) => {
        for (const p of relatedPendings) {
          const sameName = String(c.nombreCuota ?? '').toLowerCase() === String(p.nombreCuota ?? '').toLowerCase();
          const sameMonto = Number(c.valorCuota ?? 0) === Number(p.monto ?? 0);
          const sameId = p.idCuota && (Number(c.idCuota) === Number(p.idCuota) || Number(c.id) === Number(p.idCuota));
          
          if (sameId || sameName) {
            // 🔥 FORZAR ESTADO PENDIENTE SI ES UN PAGO LOCAL NO CONFIRMADO
            if (!p.confirmado) {
              console.log('[Cuotas-debug] Forzando estado PENDIENTE para:', c.nombreCuota);
              return {
                ...c,
                estadoPago: 'PENDIENTE',
                pendingPayment: true,
                pagoConfirmado: false,
                pagoTemporalId: p.pagoTemporalId ?? c.pagoTemporalId ?? null,
                disabled: true,
              };
            }
          }
        }
        return c;
      });
      
      return { ...ins, cuotas };
    }));
  }, []);

  const loadInscripciones = useCallback(async () => {
    setLoading(true);
    try {
      if (!user) {
        setInscripciones([]);
        return;
      }

      // variantes de cédula
      const userCedRaw = (user.cedula ?? user.username ?? '').toString();
      const cedulaDigits = normalizeCedula(userCedRaw) || userCedRaw;
      const candidates = [userCedRaw, cedulaDigits, `V-${cedulaDigits}`, `E-${cedulaDigits}`].filter(Boolean);
      console.log('[Cuotas] probaré estas variantes de cédula:', candidates);

      // normalizador de respuestas (axios/fetch)
      const normalizeResponse = (res: any) => {
        if (!res) return [];
        if (res.data !== undefined) {
          if (Array.isArray(res.data)) return res.data;
          if (Array.isArray(res.data.results)) return res.data.results;
          if (Array.isArray(res.data.data)) return res.data.data;
          return Array.isArray(res.data) ? res.data : [];
        }
        if (Array.isArray(res)) return res;
        if (Array.isArray(res.results)) return res.results;
        return [];
      };

      // fetch inscripciones probando variantes
      const fetchInscripciones = async (ced: string) => {
        try {
          const endpoint = `/api/inscripcion/usuario/?cedula=${encodeURIComponent(ced)}`;
          console.log('[Cuotas] GET', endpoint);
          const res = await api.get(endpoint);
          const d = normalizeResponse(res);
          console.log('[Cuotas-debug] respuesta inscripciones para', ced, '->', d.length);
          return d;
        } catch (err: any) {
          console.warn('[Cuotas] error fetching inscripciones para', ced, err?.response?.data ?? err);
          return [];
        }
      };

      let insData: any[] = [];
      for (const cand of candidates) {
        insData = await fetchInscripciones(cand);
        if (insData && insData.length > 0) { console.log('[Cuotas] encontrada inscripciones con variante:', cand); break; }
      }

      // fallback general
      if (!insData || insData.length === 0) {
        try {
          const resAll = await api.get('/api/inscripcion/');
          insData = normalizeResponse(resAll);
          console.log('[Cuotas-debug] fallback /api/inscripcion/ ->', insData.length);
        } catch (err: any) {
          console.warn('[Cuotas] fallback /api/inscripcion/ falló', err?.response?.data ?? err);
          insData = [];
        }
      }

      // traer notas y pagos separados
      let notasResp: any[] = [];
      let pagosResp: any[] = [];
      try {
        const r = await api.get('/api/notas/usuario/autenticado/');
        notasResp = normalizeResponse(r);
      } catch (err: any) {
        console.warn('[Cuotas] error cargando notas:', err?.response?.data ?? err);
        notasResp = [];
      }
      try {
        const p = await api.get('/api/pagos/');
        pagosResp = normalizeResponse(p);
      } catch (err: any) {
        console.warn('[Cuotas] error cargando pagos:', err?.response?.data ?? err);
        pagosResp = [];
      }

      console.log('[Cuotas-debug] counts -> ins:', insData.length, 'notas:', notasResp.length, 'pagos:', pagosResp.length);

      // helper: detectar confirmación robusta
      const isConfirmed = (obj: any) => {
        if (obj == null) return false;

        // Verificar si es un pago local pendiente
        const objId = obj?.idNota ?? obj?.id ?? null;
        const isPendingLocal = objId && pendingLocalPayments.some(p => 
          p.idNota === objId || p.pagoTemporalId === objId
        );

        if (isPendingLocal) {
          console.log('[Cuotas-debug] Detectado pago local pendiente, forzando no confirmado:', objId);
          return false;
        }

        // Lógica normal de confirmación
        if (obj === true) return true;
        if (obj === 1 || obj === '1') return true;
        const s = String(obj).toLowerCase();
        if (s === 'true' || s === 't' || s === 'yes' || s === 'si') return true;

        if (typeof obj === 'object') {
          const candidates = [
            obj?.confirmado,
            obj?.confirmado_pago,
            obj?.confirmadoPago,
            obj?.estado,
            obj?.estadoPago,
            obj?.estado_nota,
            obj?.status,
            obj?.statusPago,
          ];

          for (const cand of candidates) {
            if (cand === true) return true;
            if (cand === 1 || cand === '1') return true;
            const candS = String(cand ?? '').toUpperCase();
            if (candS === 'PAGADO' || candS === 'PAGADA' || candS === 'CONFIRMADO' || candS === 'APROBADO') return true;
            if (String(cand ?? '').toLowerCase() === 'true') return true;
          }

          const notaObj = obj?.idNota ?? obj?.nota ?? obj?.nota_detail ?? obj?.idNota_detail;
          if (notaObj) {
            const estadoNota = (notaObj?.estado ?? notaObj?.estadoNota ?? notaObj?.status ?? '').toString().toUpperCase();
            if (estadoNota === 'PAGADO' || estadoNota === 'PAGADA') {
              console.log('[Cuotas-debug] isConfirmed detectó estado PAGADO dentro de idNota/nota:', estadoNota, notaObj);
              return true;
            }
            if (notaObj?.confirmado === true || String(notaObj?.confirmado).toLowerCase() === 'true') return true;
          }
        }

        return false;
      };

      const normalizeNumber = (v: any) => {
        if (v == null || v === '') return null;
        const x = typeof v === 'object' ? (v?.id ?? v?.pk ?? v?.idCuota ?? null) : v;
        const n = Number(x);
        return !isNaN(n) && n > 0 ? n : null;
      };
      const getAllIdsFromCuota = (c: any) => {
        const ids = new Set<number>();
        const cand = [
          c.id, c.pk, c.idInscripcionCuota, c.idInscripcionCuota?.id,
          c.idCuota, c.id_cuota, c.cuota,
          c.__raw && (c.__raw.idCuota ?? c.__raw.cuota ?? c.__raw.idCuota_id),
          c.__raw && (c.__raw.id ?? c.__raw.pk),
          c.__raw && c.__raw.idCuota && (c.__raw.idCuota.idCuota ?? c.__raw.idCuota.id ?? c.__raw.idCuota.pk)
        ];
        for (const x of cand) {
          const n = normalizeNumber(x);
          if (n) ids.add(n);
        }
        return Array.from(ids);
      };
      const extractRelatedIdFromRel = (rel: any) => {
        if (!rel) return null;
        const rc = rel?.idCuota ?? rel?.idCuota_id ?? rel?.id ?? rel?.cuota ?? null;
        return normalizeNumber(rc);
      };

      // marcar notas/pagos como unused para evitar reutilización
      const unusedNotas = (Array.isArray(notasResp) ? notasResp.slice() : []).map(n => ({ ...n, __used: false }));
      const unusedPagos = (Array.isArray(pagosResp) ? pagosResp.slice() : []).map(p => ({ ...p, __used: false }));

      // si la propia cuota trae estadoPAGADO aplicarlo inmediatamente
      const applyRawCuotaState = (c: any) => {
        const rawEstado = (c.estadoPago ?? c.estado ?? (c.__raw && (c.__raw.estadoPago ?? c.__raw.estado)) ?? '').toString().toUpperCase();
        if (rawEstado === 'PAGADO' || rawEstado === 'PAGADA' || rawEstado.includes('PAGAD')) {
          c.estadoPago = 'PAGADO';
          c.pagoConfirmado = true;
          c.disabled = true;
          return true;
        }
        return false;
      };

      // recorrer inscripciones y resolver cuotas
      const enriched = (insData || []).map((ins: any) => {
        const insId = normalizeNumber(ins?.idInscripcion ?? ins?.id ?? ins?.pk) ?? null;
        const cuotasRaw = extractCuotasFromInscripcion(ins);
        const notasIns = ins?.notas ?? ins?.notas_prefetch ?? ins?.nota_inscripcion_detail ?? [];
        const cuotas = (cuotasRaw || []).map((c: any) => ({
          ...c,
          pendingPayment: false,
          pagoConfirmado: false,
          pagoTemporalId: null,
          disabled: false,
        }));

        const usedRelatedIds = new Set<number>();
        const usedMontoCount = new Map<number, number>();

        for (let i = 0; i < cuotas.length; i++) {
          const c = cuotas[i];
          const cuotaIds = getAllIdsFromCuota(c);
          const monto = Number(c.valorCuota ?? 0);

          // 0) PRIORIDAD: estado en la propia cuota
          if (applyRawCuotaState(c)) {
            console.log('[Cuotas-debug] cuota marcada PAGADO por estado en la propia cuota:', insId, c.nombreCuota);
            continue;
          }

          // 1) NOTAS LOCALES
          let matchedLocal = false;
          for (const nota of (Array.isArray(notasIns) ? notasIns : [])) {
            try {
              const tipo = String(nota?.tipoArticulo ?? nota?.tipo ?? '').toUpperCase();
              const estado = String(nota?.estado ?? '').toUpperCase();
              if (tipo !== 'CUOTA') continue;
              const relatedId = extractRelatedIdFromRel(Array.isArray(nota?.relaciones) && nota.relaciones.length ? nota.relaciones[0] : (nota?.relaciones_detail?.[0] ?? null));
              const montoNota = Number(nota?.totalNota ?? nota?.total ?? nota?.monto ?? 0);
              const notaConfirmada = isConfirmed(nota);

              if (relatedId && cuotaIds.includes(relatedId) && !usedRelatedIds.has(relatedId)) {
                c.estadoPago = notaConfirmada ? 'PAGADO' : 'PENDIENTE';
                c.pagoConfirmado = !!notaConfirmada;
                c.pendingPayment = !notaConfirmada;
                c.disabled = true;
                usedRelatedIds.add(relatedId);
                matchedLocal = true; break;
              } else if ((!relatedId) && montoNota && montoNota === monto && (usedMontoCount.get(montoNota) ?? 0) === 0) {
                c.estadoPago = notaConfirmada ? 'PAGADO' : 'PENDIENTE';
                c.pagoConfirmado = !!notaConfirmada;
                c.pendingPayment = !notaConfirmada;
                c.disabled = true;
                usedMontoCount.set(montoNota, 1);
                matchedLocal = true; break;
              }
            } catch { /* skip */ }
          }
          if (matchedLocal) { console.log('[Cuotas-debug] cuota marcada por nota local:', insId, c.nombreCuota); continue; }

          // 2) PAGOS LOCALES
          let matchedPagoLocal = false;
          for (const pago of unusedPagos) {
            if (pago.__used) continue;
            try {
              const notaRel = pago?.idNota ?? pago?.nota ?? pago?.nota_detail ?? pago?.idNota_detail ?? null;
              let relatedId = null;
              if (notaRel && Array.isArray(notaRel?.relaciones) && notaRel.relaciones.length) {
                relatedId = extractRelatedIdFromRel(notaRel.relaciones[0]);
              }
              if (!relatedId && (pago?.idCuota || pago?.cuota_id)) {
                relatedId = normalizeNumber(pago?.idCuota ?? pago?.cuota_id);
              }

              // intentar inscripcion asociada al pago
              let pagoIns = null;
              if (pago?.idInscripcion || pago?.inscripcion || pago?.inscripcion_id) {
                pagoIns = normalizeNumber(pago?.idInscripcion ?? pago?.inscripcion ?? pago?.inscripcion_id);
              } else if (notaRel && Array.isArray(notaRel?.relaciones) && notaRel.relaciones.length) {
                pagoIns = normalizeNumber(notaRel.relaciones[0]?.idInscripcion ?? notaRel.relaciones[0]?.idInscripcion_id);
              }

              const montoPago = Number(pago?.monto ?? pago?.amount ?? 0);
              const confirmado = isConfirmed(pago);

              if (relatedId && cuotaIds.includes(relatedId) && (!pagoIns || pagoIns === insId)) {
                pago.__used = true;
                usedRelatedIds.add(relatedId);
                c.estadoPago = confirmado ? 'PAGADO' : 'PENDIENTE';
                c.pagoConfirmado = confirmado;
                c.pendingPayment = !confirmado;
                c.disabled = true;
                matchedPagoLocal = true;
                break;
              }
              if ((!relatedId) && montoPago && montoPago === monto && (usedMontoCount.get(montoPago) ?? 0) === 0) {
                pago.__used = true;
                usedMontoCount.set(montoPago, 1);
                c.estadoPago = confirmado ? 'PAGADO' : 'PENDIENTE';
                c.pagoConfirmado = confirmado;
                c.pendingPayment = !confirmado;
                c.disabled = true;
                matchedPagoLocal = true;
                break;
              }
            } catch { /* skip */ }
          }
          if (matchedPagoLocal) { console.log('[Cuotas-debug] cuota marcada por pago local:', insId, c.nombreCuota); continue; }

          // 3) MATCH GLOBAL - notas
          let matchedGlobal = false;
          for (const nota of unusedNotas) {
            if (nota.__used) continue;
            try {
              const tipo = String(nota?.tipoArticulo ?? nota?.tipo ?? '').toUpperCase();
              if (tipo !== 'CUOTA') continue;
              const relatedId = extractRelatedIdFromRel(Array.isArray(nota?.relaciones) && nota.relaciones.length ? nota.relaciones[0] : (nota?.relaciones_detail?.[0] ?? null));
              const montoNota = Number(nota?.totalNota ?? nota?.total ?? nota?.monto ?? 0);
              const notaConfirmada = isConfirmed(nota);

              if (relatedId && cuotaIds.includes(relatedId) && !usedRelatedIds.has(relatedId)) {
                nota.__used = true; usedRelatedIds.add(relatedId);
                c.estadoPago = notaConfirmada ? 'PAGADO' : 'PENDIENTE';
                c.pagoConfirmado = !!notaConfirmada;
                c.pendingPayment = !notaConfirmada;
                c.disabled = true;
                matchedGlobal = true; break;
              }
              if ((!relatedId) && montoNota && montoNota === monto && (usedMontoCount.get(montoNota) ?? 0) === 0) {
                nota.__used = true; usedMontoCount.set(montoNota, 1);
                c.estadoPago = notaConfirmada ? 'PAGADO' : 'PENDIENTE';
                c.pagoConfirmado = !!notaConfirmada;
                c.pendingPayment = !notaConfirmada;
                c.disabled = true;
                matchedGlobal = true; break;
              }
            } catch { /* skip */ }
          }
          if (matchedGlobal) { console.log('[Cuotas-debug] cuota marcada por nota global:', insId, c.nombreCuota); continue; }

          // pagos globales
          for (const pago of unusedPagos) {
            if (pago.__used) continue;
            try {
              const notaRel = pago?.idNota ?? pago?.nota ?? pago?.nota_detail ?? pago?.idNota_detail ?? null;
              let relatedId = null;
              if (notaRel && Array.isArray(notaRel?.relaciones) && notaRel.relaciones.length) {
                relatedId = extractRelatedIdFromRel(notaRel.relaciones[0]);
              }
              if (!relatedId && (pago?.idCuota || pago?.cuota_id)) {
                relatedId = normalizeNumber(pago?.idCuota ?? pago?.cuota_id);
              }
              const montoPago = Number(pago?.monto ?? pago?.amount ?? 0);
              const confirmado = isConfirmed(pago);

              if (relatedId && cuotaIds.includes(relatedId) && !usedRelatedIds.has(relatedId)) {
                pago.__used = true; usedRelatedIds.add(relatedId);
                c.estadoPago = confirmado ? 'PAGADO' : 'PENDIENTE';
                c.pagoConfirmado = confirmado;
                c.pendingPayment = !confirmado;
                c.disabled = true;
                matchedGlobal = true; break;
              }
              if ((!relatedId) && montoPago && montoPago === monto && (usedMontoCount.get(montoPago) ?? 0) === 0) {
                pago.__used = true; usedMontoCount.set(montoPago, 1);
                c.estadoPago = confirmado ? 'PAGADO' : 'PENDIENTE';
                c.pagoConfirmado = confirmado;
                c.pendingPayment = !confirmado;
                c.disabled = true;
                matchedGlobal = true; break;
              }
            } catch { /* skip */ }
          }
          if (matchedGlobal) { console.log('[Cuotas-debug] cuota marcada por pago global:', insId, c.nombreCuota); continue; }

          // default: EN ESPERA
          c.estadoPago = String(c.estadoPago ?? '').toUpperCase() || 'EN ESPERA';
        } // end for cuotas

        // --- PASADA DE CONSISTENCIA: asegurar que pagoConfirmado => estadoPago = 'PAGADO' ---
        for (const c of cuotas) {
          if (c.pagoConfirmado) {
            // forzamos valores coherentes
            c.estadoPago = 'PAGADO';
            c.pendingPayment = false;
            c.disabled = true;
          } else if (String(c.estadoPago ?? '').toUpperCase() === 'PAGADO' && !c.pagoConfirmado) {
            // si backend devolvió "PAGADO" pero no lo marcamos como confirmado, normalizamos
            c.pagoConfirmado = true;
            c.pendingPayment = false;
            c.disabled = true;
          }
        }

        // bloqueo por pago de inscripción
        const pagoInscripcionConfirmado = detectPagoInscripcionConfirmado(ins);
        if (!pagoInscripcionConfirmado) {
          for (const q of cuotas) {
            q.disabled = true; q._blockedByInscripcion = true;
            q.estadoPago = String(q.estadoPago ?? '').toUpperCase() || 'BLOQUEADA';
          }
        } else {
          // habilitar solo la primera EN ESPERA que no tenga pending ni pagoConfirmado
          const firstUnpaidIndex = cuotas.findIndex((q: any) => {
            const st = String(q.estadoPago ?? '').toUpperCase();
            return (st === 'EN ESPERA' || st === '' ) && !q.pendingPayment && !q.pagoConfirmado;
          });
          for (let i = 0; i < cuotas.length; i++) {
            const q = cuotas[i];
            const estado = String(q.estadoPago ?? '').toUpperCase();
            q.disabled = estado === 'PAGADO' || estado === 'PENDIENTE' || (firstUnpaidIndex !== -1 && i !== firstUnpaidIndex);
          }
        }

        return {
          ...ins,
          cuotas,
          pago_inscripcion_confirmada: detectPagoInscripcionConfirmado(ins),
        };
      });

      console.log('[Cuotas-debug] enriched inscripciones (final):', enriched);

      // aplicar enriched
      setInscripciones(enriched);

      // reaplicar pagos locales pendientes (optimista) después de cargar desde backend
      // usamos el estado actual de pendingLocalPayments
      reapplyLocalPendings(pendingLocalPayments || []);
    } catch (e: any) {
      console.error('Error cargando inscripciones en CuotasPorPagar', e?.response?.data ?? e);
      Alert.alert('Error', e?.response?.data?.detail ?? 'No se pudieron cargar las inscripciones');
      setInscripciones([]);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [user, pendingLocalPayments, reapplyLocalPendings]);

  useEffect(() => {
    loadInscripciones();
  }, [loadInscripciones]);

  const handleToggleAccordion = (insId: number) => {
    setExpandedId(prev => (prev === insId ? null : insId));
  };

  const onRefresh = async () => {
    setRefreshing(true);
    await loadInscripciones();
    setRefreshing(false);
  };

  const openPagoModal = (inscripcion: InscripcionLite, cuota: CuotaLite) => {
    if (cuota.pendingPayment) {
      Alert.alert('Pago en revisión', 'Ya existe un pago en revisión para esta cuota. Espere la confirmación administrativa.');
      return;
    }
    if (cuota.disabled) {
      Alert.alert('No disponible', 'Esta cuota no está disponible para pago en este momento.');
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

  // En handleSolicitarPago, modifica esta parte:
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
      idInscripcion: modalPayload.inscripcion.idInscripcion ?? modalPayload.inscripcion.id ?? modalPayload.inscripcion.pk,
      nombreCuota: modalPayload.cuota.nombreCuota,
      monto: modalPayload.cuota.valorCuota,
      referencia: referencia.trim(),
      observaciones: observaciones.trim(),
    };

    console.log('[Pago Cuota] Enviando payload:', payload);
    const res = await api.post('/api/pagos/cuota/create/', payload);

    if (res.status === 200 || res.status === 201) {
      const data = res.data?.data ?? res.data;
      const pagoTemporalId = data?.idPagoTemporal ?? data?.idPago ?? data?.id ?? null;
      
      // 🔥 USAR EL ESTADO REAL DEL BACKEND AHORA
      const estadoNota = data?.estado_nota ?? 'PENDIENTE';
      const confirmado = estadoNota === 'PAGADO' || data?.confirmado === true;

      const insId = modalPayload?.inscripcion?.idInscripcion ?? modalPayload?.inscripcion?.id ?? modalPayload?.inscripcion?.pk;
      const cuotaIdent = {
        idCuota: modalPayload?.cuota?.idCuota ?? modalPayload?.cuota?.id ?? null,
        nombreCuota: (modalPayload?.cuota?.nombreCuota ?? '').toString().trim(),
        monto: Number(modalPayload?.cuota?.valorCuota ?? 0),
      };

      // 1) ACTUALIZACIÓN OPTIMISTA BASADA EN RESPUESTA REAL DEL BACKEND
      setInscripciones(prev => prev.map((ins: any) => {
        const curInsId = ins.idInscripcion ?? ins.id ?? null;
        if (insId && curInsId !== insId) return ins;
        
        const cuotas = (ins.cuotas || []).map((c: any) => {
          const sameName = String(c.nombreCuota ?? '').toLowerCase() === String(cuotaIdent.nombreCuota ?? '').toLowerCase();
          const sameMonto = Math.abs(Number(c.valorCuota ?? 0) - Number(cuotaIdent.monto ?? 0)) < 0.01;
          const sameId = cuotaIdent.idCuota && (Number(c.idCuota) === Number(cuotaIdent.idCuota) || Number(c.id) === Number(cuotaIdent.idCuota));
          
          if (sameId || (sameName && sameMonto)) {
            console.log('[Pago-debug] Marcando cuota con estado:', estadoNota, 'Confirmado:', confirmado);
            return {
              ...c,
              estadoPago: estadoNota === 'PAGADO' ? 'PAGADO' : 'PENDIENTE',
              pendingPayment: estadoNota !== 'PAGADO',
              pagoConfirmado: confirmado,
              pagoTemporalId: pagoTemporalId,
              disabled: true,
            };
          }
          return c;
        });
        
        return { ...ins, cuotas };
      }));

      // 2) AGREGAR A PAGOS LOCALES PENDIENTES SOLO SI NO ESTÁ CONFIRMADO
      if (!confirmado) {
        const newPending = {
          insId,
          ...cuotaIdent,
          pagoTemporalId,
          idNota: data?.idNota ?? null,
          confirmado: false,
          referencia: referencia.trim(),
          timestamp: Date.now(),
        };

        setPendingLocalPayments(prev => {
          const filtered = prev.filter(p => 
            !(p.insId === insId && 
              p.nombreCuota === cuotaIdent.nombreCuota)
          );
          return [...filtered, newPending];
        });
      }

      closeModal();

      // 3) MENSAJE BASADO EN ESTADO REAL
      if (confirmado) {
        Alert.alert('Pago confirmado', 'El pago ha sido confirmado automáticamente por el sistema.');
      } else {
        Alert.alert(
          'Solicitud enviada', 
          'Pago pendiente de revisión administrativa. El estado se actualizará cuando sea procesado.'
        );
      }

      // 4) RECARGAR PARA SINCRONIZAR
      setTimeout(() => {
        loadInscripciones();
      }, 1500);

    } else {
      const msg = res.data?.message || res.data?.error || 'No se pudo registrar la solicitud.';
      Alert.alert('Error', msg);
    }
  } catch (e: any) {
    console.error('Error al solicitar pago de cuota', e?.response?.data ?? e);
    const errors = e?.response?.data?.errors ?? e?.response?.data?.error ?? e?.response?.data;
    let msg = 'Error desconocido';
    if (errors) {
      if (typeof errors === 'string') msg = errors;
      else if (typeof errors === 'object') {
        try {
          msg = Object.keys(errors).map(k => `${k}: ${Array.isArray(errors[k]) ? errors[k].join(', ') : String(errors[k])}`).join('\n');
        } catch { msg = JSON.stringify(errors); }
      } else msg = String(errors);
    } else {
      msg = e?.message ?? String(e);
    }
    Alert.alert('Error al enviar el pago', msg);
    
    // Revertir en caso de error
    setTimeout(() => {
      loadInscripciones();
    }, 1000);
  } finally {
    setSubmitting(false);
  }
};

  const renderInscripcionItem = ({ item }: { item: InscripcionLite }) => {
  const idKey = item.idInscripcion ?? item.id ?? null;
  const tituloForm = item.idFormacion_detail?.nombreFormacion ?? item.idFormacion_detail?.nombre ?? item.formacion?.nombre ?? 'Sin nombre';
  const cohName = item.idCohorte_detail?.nombreCohorte ?? item.idCohorte?.nombreCohorte ?? '—';
  const fecha = item.fechaInscripcion ? new Date(item.fechaInscripcion).toLocaleDateString() : '—';

  const cuotas: CuotaLite[] = item.cuotas ?? [];

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
          {!item.pago_inscripcion_confirmada ? (
            <View style={styles.emptyRow}>
              <Icon name="alert-circle-outline" size={22} color="#856404" />
              <Text style={styles.emptyText}>
                Las cuotas están visibles, pero no se pueden pagar hasta confirmar el pago de la inscripción.
              </Text>
            </View>
          ) : cuotas.length === 0 ? (
            <View style={styles.emptyRow}>
              <Icon name="calendar-remove" size={28} color="#dee2e6" />
              <Text style={styles.emptyText}>No hay cuotas configuradas para esta inscripción.</Text>
            </View>
          ) : (
            <>
              {cuotas.map((c: CuotaLite, index: number) => {
                const estado = String(c.estadoPago ?? '').toUpperCase();
                const isPaid = estado === 'PAGADO' || c.pagoConfirmado === true;
                const isPending = estado === 'PENDIENTE' || c.pendingPayment === true;
                // 🔥 MEJORAR LÓGICA DE HABILITACIÓN
                const canPay = !isPaid && !isPending && !c.disabled && 
                              (c.estadoPago === 'EN ESPERA' || !c.estadoPago);

                console.log(`[UI-debug] Cuota ${c.nombreCuota}:`, {
                  estado,
                  isPaid,
                  isPending,
                  disabled: c.disabled,
                  canPay,
                  pagoConfirmado: c.pagoConfirmado,
                  pendingPayment: c.pendingPayment
                });

                return (
                  <View key={String(c.id ?? c.idCuota ?? index)} style={styles.cuotaRow}>
                    <View style={{ flex: 1 }}>
                      <Text style={[styles.cuotaNombre, isPaid ? styles.cuotaPaidText : {}]}>
                        {c.nombreCuota}
                      </Text>
                      <Text style={styles.cuotaSub}>{fmtMoney(c.valorCuota)}</Text>
                      {/* 🔥 MOSTRAR DEBUG INFO EN DESARROLLO */}
                      {__DEV__ && (
                        <Text style={styles.debugText}>
                          Estado: {estado} | Confirmado: {c.pagoConfirmado ? 'Sí' : 'No'} | Pendiente: {c.pendingPayment ? 'Sí' : 'No'}
                        </Text>
                      )}
                    </View>

                    <View style={styles.cuotaActions}>
                      {isPaid ? (
                        <View style={styles.paidBadge}>
                          <Icon name="check-circle" size={16} color="#155724" />
                          <Text style={styles.paidBadgeText}>PAGADA</Text>
                        </View>
                      ) : isPending ? (
                        <View style={styles.pendingBadge}>
                          <Icon name="clock-outline" size={16} color="#856404" />
                          <Text style={styles.pendingBadgeText}>
                            {c.pagoConfirmado ? 'CONFIRMADO' : 'EN REVISIÓN'}
                          </Text>
                        </View>
                      ) : (
                        <TouchableOpacity
                          style={[styles.payButton, !canPay ? styles.payButtonDisabled : {}]}
                          disabled={!canPay}
                          onPress={() => openPagoModal(item, c)}
                        >
                          <Text style={[styles.payButtonText, !canPay ? styles.payButtonTextDisabled : {}]}>
                            Pagar
                          </Text>
                        </TouchableOpacity>
                      )}
                    </View>
                  </View>
                );
              })}

              <View style={styles.infoRow}>
                <Text style={styles.smallNote}>
                  Solo puede pagar la primera cuota pendiente. Las demás se habilitan tras la confirmación.
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
                      <Text style={styles.submitText}>{submitting ? 'Enviando...' : 'Solicitar pago'}</Text>
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

/* estilos: pega los tuyos si prefieres */
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
  debugText: { fontSize: 11, color: '#6c757d', marginTop: 4 },
  cuotaActions: { minWidth: 110, alignItems: 'flex-end' },
  payButton: { backgroundColor: '#2b6cb0', paddingHorizontal: 14, paddingVertical: 8, borderRadius: 8 },
  payButtonText: { color: '#fff', fontWeight: '700' },
  payButtonDisabled: { backgroundColor: '#cbd5e1' },
  payButtonTextDisabled: { color: '#7b8794' },
  paidBadge: { flexDirection: 'row', alignItems: 'center', backgroundColor: '#d4edda', paddingHorizontal: 10, paddingVertical: 6, borderRadius: 12 },
  paidBadgeText: { color: '#155724', fontWeight: '700', marginLeft: 6 },
  pendingBadge: { flexDirection: 'row', alignItems: 'center', backgroundColor: '#ffeeba', paddingHorizontal: 10, paddingVertical: 6, borderRadius: 12 },
  pendingBadgeText: { color: '#856404', fontWeight: '700', marginLeft: 6 },
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
