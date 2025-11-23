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
  TextInput,
  ScrollView,
  Platform,
  KeyboardAvoidingView,
  useWindowDimensions,
} from 'react-native';
import Modal from 'react-native-modal';
import Icon from 'react-native-vector-icons/MaterialCommunityIcons';
import { AuthContext } from '../contexts/AuthContext';
import api from '../api/api';
import { useNavigation, useFocusEffect } from '@react-navigation/native';

// --- Tipos (relajados) ---
type CuotaLite = any;
type InscripcionLite = any;
type ModalPayload = { inscripcion?: InscripcionLite; cuota?: CuotaLite } | null;

const fmtMoney = (v: any) => {
  const n = Number(v) || 0;
  return `$${n.toFixed(2)}`;
};

const normalizeCedula = (ced: any) => String(ced ?? '').replace(/\D/g, '');

// Función mejorada para verificar si el usuario actual es el dueño de la inscripción
const isUserInscripcionOwner = (inscripcion: any, userCedula: string) => {
  if (!userCedula || !inscripcion) return false;

  const userCedNormalized = normalizeCedula(userCedula);

  // Verificar diferentes campos donde puede estar la cédula en la inscripción
  const cedulaCandidates = [
    inscripcion.idPersona?.cedula,
    inscripcion.idPersona?.cedulaPersona,
    inscripcion.cedula,
    inscripcion.cedulaPersona,
    inscripcion.idPersona_detail?.cedula,
    inscripcion.idPersona_detail?.cedulaPersona,
  ];

  return cedulaCandidates.some(ced => {
    if (!ced) return false;
    return normalizeCedula(ced) === userCedNormalized;
  });
};

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
  const { width, height } = useWindowDimensions();
  const isSmallScreen = width <= 620;
  const isLargeScreen = width >= 900;

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

  // Configuración de cuenta bancaria (cargada desde API)
  const [configuracion, setConfiguracion] = useState<any>(null);
  const [loadingConfig, setLoadingConfig] = useState<boolean>(false);

  const detectPagoInscripcionConfirmado = (ins: any) => {
    if (ins?.pago_inscripcion_confirmada === true || ins?.pagoInscripcionConfirmado === true || ins?.inscripcionPagoConfirmado === true) return true;

    const pagos = ins?.pago_temporal_set ?? ins?.pagos ?? ins?.pagostemporales ?? ins?.pagos_temporales ?? [];
    if (Array.isArray(pagos) && pagos.some((p: any) => p?.confirmado === true || String(p?.confirmado).toLowerCase() === 'true')) return true;

    const notas = ins?.notas ?? ins?.nota_inscripcion_detail ?? [];
    if (Array.isArray(notas) && notas.some((n: any) => (n?.tipoArticulo ?? '').toString().toUpperCase() === 'INSCRIPCION' && (n?.estado ?? '').toString().toUpperCase() === 'PAGADO')) return true;

    return false;
  };

  // Función para verificar si todas las cuotas están pagadas
  const areAllCuotasPaid = (cuotas: CuotaLite[]) => {
    if (!cuotas || cuotas.length === 0) return false;
    return cuotas.every(c => 
      String(c.estadoPago ?? '').toUpperCase() === 'PAGADO' || 
      c.pagoConfirmado === true
    );
  };

  // Cargar configuración (cuenta bancaria) al montar
  useEffect(() => {
    let mounted = true;
    const loadConfig = async () => {
      setLoadingConfig(true);
      try {
        const res = await api.get('/api/configuracion/');
        // soportar varias formas de respuesta:
        // - res.data puede ser directamente el objeto config
        // - res.data puede ser wrapper { success: true, data: {...} }
        // - o el servidor puede devolver el objeto directamente (res.data === {...})
        let cfg: any = null;
        if (res && res.data) {
          if (res.data.data) cfg = res.data.data;     // wrapper { success: true, data: {...} }
          else cfg = res.data;                       // objeto directo
        } else if (res) {
          cfg = res;
        }
        // Si accidentalmente recibes { success:true, data:{data:...} } esta línea intenta destripar más
        if (cfg && cfg.data && typeof cfg.data === 'object' && Object.keys(cfg).length === 1) {
          cfg = cfg.data;
        }

        if (mounted) setConfiguracion(cfg);
      } catch (e: any) {
        console.warn('[Cuotas] No se pudo cargar configuracion de cuenta bancaria', e?.response?.data ?? e);
        if (mounted) setConfiguracion(null);
      } finally {
        if (mounted) setLoadingConfig(false);
      }
    };
    loadConfig();
    return () => { mounted = false; };
  }, []);

  const loadInscripciones = useCallback(async () => {
  setLoading(true);
  try {
    if (!user) {
      setInscripciones([]);
      return;
    }

    // Intentar cargar configuración (para mostrar datos de cuenta en modal)
    try {
      console.log('[Cuotas] cargando /api/configuracion/');
      const cfgRes = await api.get('/api/configuracion/');
      // tu endpoint puede devolver { success: true, data: {...} } o el objeto directamente
      const cfgData = cfgRes.data?.data ?? cfgRes.data ?? null;
      if (cfgData) {
        // opcional: puedes guardar en un estado si lo necesitas en la pantalla
        // setConfiguracion(cfgData);
        console.log('[Cuotas] configuracion cargada:', cfgData);
      } else {
        console.warn('[Cuotas] respuesta /api/configuracion/ vacía o inesperada:', cfgRes.data);
      }
    } catch (err: any) {
      console.warn('[Cuotas] No se pudo cargar configuracion de cuenta bancaria ', err?.response?.data ?? err);
      // no hacemos throw: la pantalla sigue funcionando sin la config
    }

    const userCedRaw = (user.cedula ?? user.username ?? '').toString();
    const cedulaDigits = normalizeCedula(userCedRaw) || userCedRaw;
    const candidates = [userCedRaw, cedulaDigits, `V-${cedulaDigits}`, `E-${cedulaDigits}`].filter(Boolean);
    console.log('[Cuotas] probaré estas variantes de cédula:', candidates);

    // helpers locales
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

    const fetchInscripciones = async (ced: string) => {
      try {
        const endpoint = `/api/inscripcion/usuario/?cedula=${encodeURIComponent(ced)}`;
        console.log('[Cuotas] GET', endpoint);
        const res = await api.get(endpoint);
        const d = normalizeResponse(res);
        console.log('[Cuotas-debug] respuesta inscripciones para', ced, '->', d.length);
        // Filtrar solo las inscripciones que pertenecen al usuario actual (por cédula)
        const filtered = d.filter((ins: any) => isUserInscripcionOwner(ins, userCedRaw));
        console.log('[Cuotas-debug] inscripciones después del filtro:', filtered.length);
        return filtered;
      } catch (err: any) {
        console.warn('[Cuotas] error fetching inscripciones para', ced, err?.response?.data ?? err);
        return [];
      }
    };

    // Buscar inscripciones probando variantes de cédula
    let insData: any[] = [];
    for (const cand of candidates) {
      insData = await fetchInscripciones(cand);
      if (insData && insData.length > 0) {
        console.log('[Cuotas] encontrada inscripciones con variante:', cand);
        break;
      }
    }

    // Cargar notas y pagos globales (servidor)
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

    // --- Helpers para matching robusto ---
    const isConfirmed = (obj: any) => {
      if (obj == null) return false;
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

    const getPersonaIdFromIns = (ins: any) => {
      return ins?.idPersona?.id ?? ins?.idPersona?.idPersona ?? ins?.idPersona ?? ins?.persona ?? null;
    };
    const getPersonaIdFromNotaOrPago = (obj: any) => {
      if (!obj) return null;
      return obj?.idPersona?.id ?? obj?.idPersona ?? obj?.persona?.id ?? obj?.persona ?? null;
    };
    const samePersona = (obj: any, ins: any) => {
      const pidIns = getPersonaIdFromIns(ins);
      const pidObj = getPersonaIdFromNotaOrPago(obj);
      if (pidIns && pidObj) {
        try {
          return Number(pidIns) === Number(pidObj);
        } catch { /* fallthrough */ }
      }
      const cedIns = (ins?.idPersona?.cedula ?? ins?.cedula ?? '').toString().replace(/\D/g,'');
      const cedObj = (obj?.idPersona?.cedula ?? obj?.cedula ?? obj?.cedulaPersona ?? '').toString().replace(/\D/g,'');
      if (cedIns && cedObj) return cedIns === cedObj;
      return false;
    };

    // marcar arrays de notas/pagos como "no usadas"
    const unusedNotas = (Array.isArray(notasResp) ? notasResp.slice() : []).map(n => ({ ...n, __used: false }));
    const unusedPagos = (Array.isArray(pagosResp) ? pagosResp.slice() : []).map(p => ({ ...p, __used: false }));

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

    // enrich inscripciones
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
      const usedMontoCount = new Map<any, number>();

      for (let i = 0; i < cuotas.length; i++) {
        const c = cuotas[i];
        const cuotaIds = getAllIdsFromCuota(c);
        const monto = Number(c.valorCuota ?? 0);

        if (applyRawCuotaState(c)) {
          console.log('[Cuotas-debug] cuota marcada PAGADO por estado en la propia cuota:', insId, c.nombreCuota);
          continue;
        }

        // 1) match por nota local (prioritario) — solo si nota pertenece a la misma persona/inscripción
        let matchedLocal = false;
        for (const nota of (Array.isArray(notasIns) ? notasIns : [])) {
          try {
            const tipo = String(nota?.tipoArticulo ?? nota?.tipo ?? '').toUpperCase();
            if (tipo !== 'CUOTA') continue;
            const relatedId = extractRelatedIdFromRel(Array.isArray(nota?.relaciones) && nota.relaciones.length ? nota.relaciones[0] : (nota?.relaciones_detail?.[0] ?? null));
            const montoNota = Number(nota?.totalNota ?? nota?.total ?? nota?.monto ?? 0);
            const notaConfirmada = isConfirmed(nota);

            const personaMatch = samePersona(nota, ins) || (nota?.relaciones && nota.relaciones.some((r: any) => {
              const rid = extractRelatedIdFromRel(r);
              return rid && cuotaIds.includes(rid);
            }));
            if (!personaMatch) continue;

            if (relatedId && cuotaIds.includes(relatedId)) {
              c.estadoPago = notaConfirmada ? 'PAGADO' : 'PENDIENTE';
              c.pagoConfirmado = !!notaConfirmada;
              c.pendingPayment = !notaConfirmada;
              c.disabled = true;
              matchedLocal = true; break;
            } else if ((!relatedId) && montoNota && montoNota === monto) {
              c.estadoPago = notaConfirmada ? 'PAGADO' : 'PENDIENTE';
              c.pagoConfirmado = !!notaConfirmada;
              c.pendingPayment = !notaConfirmada;
              c.disabled = true;
              matchedLocal = true; break;
            }
          } catch { /* skip */ }
        }
        if (matchedLocal) { console.log('[Cuotas-debug] cuota marcada por nota local:', insId, c.nombreCuota); continue; }

        // 2) match por pagos locales (solo si mismo inscripcion/persona)
        let matchedPagoLocal = false;
        for (const pago of unusedPagos) {
          if (pago.__used) continue;
          try {
            const pagoIns = normalizeNumber(pago?.idInscripcion ?? pago?.inscripcion ?? pago?.inscripcion_id);
            if (pagoIns && insId && pagoIns !== insId) continue;
            if (!pagoIns && !samePersona(pago, ins)) continue;

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

            if (relatedId && cuotaIds.includes(relatedId)) {
              pago.__used = true;
              usedRelatedIds.add(relatedId);
              c.estadoPago = confirmado ? 'PAGADO' : 'PENDIENTE';
              c.pagoConfirmado = confirmado;
              c.pendingPayment = !confirmado;
              c.disabled = true;
              matchedPagoLocal = true;
              break;
            }
            // match by monto solo si la persona coincide
            if ((!relatedId) && montoPago && montoPago === monto && samePersona(pago, ins)) {
              pago.__used = true;
              const key = `${montoPago}-${getPersonaIdFromNotaOrPago(pago) || 'anon'}`;
              usedMontoCount.set(key, (usedMontoCount.get(key) ?? 0) + 1);
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

        // 3) match por notas/pagos globales (con restricción de persona)
        let matchedGlobal = false;
        for (const nota of unusedNotas) {
          if (nota.__used) continue;
          try {
            const tipo = String(nota?.tipoArticulo ?? nota?.tipo ?? '').toUpperCase();
            if (tipo !== 'CUOTA') continue;
            if (!samePersona(nota, ins)) continue;

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
            if ((!relatedId) && montoNota && montoNota === monto) {
              nota.__used = true;
              usedMontoCount.set(montoNota, (usedMontoCount.get(montoNota) ?? 0) + 1);
              c.estadoPago = notaConfirmada ? 'PAGADO' : 'PENDIENTE';
              c.pagoConfirmado = !!notaConfirmada;
              c.pendingPayment = !notaConfirmada;
              c.disabled = true;
              matchedGlobal = true; break;
            }
          } catch { /* skip */ }
        }
        if (matchedGlobal) { console.log('[Cuotas-debug] cuota marcada por nota global:', insId, c.nombreCuota); continue; }

        // fallback
        c.estadoPago = String(c.estadoPago ?? '').toUpperCase() || 'EN ESPERA';
      }

      // normalizar estados finales
      for (const c of cuotas) {
        if (c.pagoConfirmado) {
          c.estadoPago = 'PAGADO';
          c.pendingPayment = false;
          c.disabled = true;
        } else if (String(c.estadoPago ?? '').toUpperCase() === 'PAGADO' && !c.pagoConfirmado) {
          c.pagoConfirmado = true;
          c.pendingPayment = false;
          c.disabled = true;
        }
      }

      const pagoInscripcionConfirmado = detectPagoInscripcionConfirmado(ins);
      if (!pagoInscripcionConfirmado) {
        for (const q of cuotas) {
          q.disabled = true; q._blockedByInscripcion = true;
          q.estadoPago = String(q.estadoPago ?? '').toUpperCase() || 'BLOQUEADA';
        }
      } else {
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
        todasLasCuotasPagadas: areAllCuotasPaid(cuotas),
      };
    });

    console.log('[Cuotas-debug] enriched inscripciones (final):', enriched);

    // Filtrar inscripciones: mostrar solo las que tienen cuotas pendientes O no tienen pago de inscripción confirmado
    const filteredInscripciones = enriched.filter(ins =>
      !ins.todasLasCuotasPagadas || !ins.pago_inscripcion_confirmada
    );

    setInscripciones(filteredInscripciones);
  } catch (e: any) {
    console.error('Error cargando inscripciones en CuotasPorPagar', e?.response?.data ?? e);
    Alert.alert('Error', e?.response?.data?.detail ?? 'No se pudieron cargar las inscripciones');
    setInscripciones([]);
  } finally {
    setLoading(false);
    setRefreshing(false);
  }
}, [user]);


  // Recargar cuando la pantalla recibe foco
  useFocusEffect(
    useCallback(() => {
      // recarga cada vez que la pantalla se enfoca
      loadInscripciones();
      return () => { /* cleanup si se necesitara */ };
    }, [loadInscripciones])
  );

  useEffect(() => {
    // carga inicial (queda, pero useFocusEffect también la cubrirá)
    loadInscripciones();
  }, [loadInscripciones]);

  const handleToggleAccordion = (insId: number) => {
    setExpandedId(prev => (prev === insId ? null : insId));
  };

  const onRefresh = async () => {
    try {
      setRefreshing(true);
      await loadInscripciones();
    } catch (e) {
      console.warn('[Cuotas] onRefresh error', e);
    } finally {
      setRefreshing(false);
    }
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
      // Ajusta el endpoint si tu backend usa otro path para pagos de cuota
      const res = await api.post('/api/cuota/pago/create/', payload).catch(async (e) => {
        // si tu API anterior era /api/pagos/cuota/create/ intenta ese fallback
        if (e?.response?.status === 404) {
          return await api.post('/api/pagos/cuota/create/', payload);
        }
        throw e;
      });

      if (res.status === 200 || res.status === 201) {
        const data = res.data?.data ?? res.data;
        const confirmado = !!data?.confirmado;

        // Actualización optimista más robusta
        setInscripciones(prev => {
          const nuevasInscripciones = prev.map((ins: any) => {
            const insId = modalPayload?.inscripcion?.idInscripcion ?? modalPayload?.inscripcion?.id;
            if (insId && ins.idInscripcion !== insId && ins.id !== insId) return ins;

            const cuotasActualizadas = (ins.cuotas || []).map((c: any) => {
              if ((String(c.nombreCuota ?? '').toLowerCase() === String(modalPayload?.cuota?.nombreCuota ?? '').toLowerCase()) || 
                  Number(c.idCuota) === Number(modalPayload?.cuota?.idCuota) || 
                  Number(c.id) === Number(modalPayload?.cuota?.id)) {
                return {
                  ...c,
                  estadoPago: confirmado ? 'PAGADO' : 'PENDIENTE',
                  pendingPayment: !confirmado,
                  pagoConfirmado: confirmado,
                  pagoTemporalId: data?.idPagoTemporal ?? c.pagoTemporalId ?? null,
                  disabled: true,
                };
              }
              return c;
            });

            // Verificar si después de este pago todas las cuotas están pagadas
            const todasPagadas = areAllCuotasPaid(cuotasActualizadas);

            return { 
              ...ins, 
              cuotas: cuotasActualizadas,
              todasLasCuotasPagadas: todasPagadas
            };
          });

          // Filtrar para remover inscripciones que ya tienen todas las cuotas pagadas
          return nuevasInscripciones.filter(ins => 
            !ins.todasLasCuotasPagadas || !ins.pago_inscripcion_confirmada
          );
        });

        closeModal();

        // Recargar para sincronizar con backend (pero ya tenemos la actualización optimista)
        setTimeout(() => {
          loadInscripciones();
        }, 1000);

        Alert.alert(
          confirmado ? 'Pago confirmado' : 'Solicitud enviada', 
          confirmado ? 'Pago confirmado por el sistema.' : 'Pago pendiente de revisión administrativa.'
        );
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
    } finally {
      setSubmitting(false);
    }
  };

  // Componente reutilizable de cuenta bancaria (sólo dentro del modal)
  const InfoCuentaBancaria = () => {
    // Fallbacks múltiples por nombres distintos que puede devolver el serializer/backend
    const banco = configuracion?.nombre_banco
      || configuracion?.idCuentaBanco?.banco
      || configuracion?.banco
      || configuracion?.nombreBanco
      || '';

    const tipoCuenta = configuracion?.tipo_cuenta
      || configuracion?.idCuentaBanco?.tipoProducto
      || configuracion?.tipoCuenta
      || configuracion?.tipo_cuenta
      || '';

    const numeroCuenta = configuracion?.numero_cuenta
      || configuracion?.idCuentaBanco?.numeroCuentaBanco
      || configuracion?.numero_cuenta
      || configuracion?.numeroCuenta
      || '';

    const cedulaRif = configuracion?.cedulaCuenta || configuracion?.rif || configuracion?.rifCuenta || '';

    const titular = configuracion?.nombreInstitucion || configuracion?.institucion || '';

    if (loadingConfig) {
      return (
        <View style={styles.cuentaBancariaCard}>
          <View style={styles.cuentaHeader}>
            <Icon name="bank" size={20} color="#2dce89" />
            <Text style={styles.cuentaTitle}>Información para Transferencia</Text>
          </View>
          <View style={{ padding: 12 }}>
            <ActivityIndicator size="small" />
            <Text style={{ marginTop: 8, color: '#666' }}>Cargando cuenta bancaria...</Text>
          </View>
        </View>
      );
    }

    return (
      <View style={styles.cuentaBancariaCard}>
        <View style={styles.cuentaHeader}>
          <Icon name="bank" size={20} color="#2dce89" />
          <Text style={styles.cuentaTitle}>Información para Transferencia</Text>
        </View>

        <View style={styles.cuentaGrid}>
          <View style={styles.cuentaItem}>
            <Text style={styles.cuentaLabel}>Banco:</Text>
            <Text style={styles.cuentaValue}>{banco || 'No especificado'}</Text>
          </View>

          <View style={styles.cuentaItem}>
            <Text style={styles.cuentaLabel}>Tipo de Cuenta:</Text>
            <Text style={styles.cuentaValue}>{tipoCuenta || 'No especificado'}</Text>
          </View>

          <View style={styles.cuentaItem}>
            <Text style={styles.cuentaLabel}>Número de Cuenta:</Text>
            <Text style={[styles.cuentaValue, styles.cuentaDestacado]}>
              {numeroCuenta || 'No especificado'}
            </Text>
          </View>

          <View style={styles.cuentaItem}>
            <Text style={styles.cuentaLabel}>Cédula/RIF:</Text>
            <Text style={[styles.cuentaValue, styles.cuentaDestacado]}>
              {cedulaRif || 'No especificado'}
            </Text>
          </View>

          <View style={styles.cuentaItem}>
            <Text style={styles.cuentaLabel}>Titular:</Text>
            <Text style={styles.cuentaValue}>{titular || 'Institución'}</Text>
          </View>
        </View>

        <View style={styles.cuentaInstrucciones}>
          <Text style={styles.instruccionesTitle}>📋 Instrucciones:</Text>
          <Text style={styles.instruccionesText}>
            1. Realice la transferencia a la cuenta mostrada arriba{'\n'}
            2. Guarde el número de referencia de la transferencia{'\n'}
            3. Complete el formulario con la referencia y fecha{'\n'}
            4. Envíe el comprobante por correo si es requerido
          </Text>
        </View>
      </View>
    );
  };

  const renderInscripcionItem = ({ item }: { item: InscripcionLite }) => {
    const idKey = item.idInscripcion ?? item.id ?? null;
    const tituloForm = item.idFormacion_detail?.nombreFormacion ?? item.idFormacion_detail?.nombre ?? item.formacion?.nombre ?? 'Sin nombre';
    const cohName = item.idCohorte_detail?.nombreCohorte ?? item.idCohorte?.nombreCohorte ?? '—';
    const fecha = item.fechaInscripcion ? new Date(item.fechaInscripcion).toLocaleDateString() : '—';

    const cuotas: CuotaLite[] = item.cuotas ?? [];
    const todasPagadas = item.todasLasCuotasPagadas;

    return (
      <View style={[styles.card, isSmallScreen && styles.cardSmall]}>
        <TouchableOpacity onPress={() => idKey && handleToggleAccordion(Number(idKey))} style={[styles.cardHeader, isSmallScreen && styles.cardHeaderSmall]}>
          <View style={{ flex: 1 }}>
            <Text style={[styles.cardTitle, isSmallScreen && styles.cardTitleSmall]}>{tituloForm}</Text>
            <Text style={[styles.cardSubtitle, isSmallScreen && styles.cardSubtitleSmall]}>{cohName} · Inscripción: {fecha}</Text>
            {todasPagadas && (
              <View style={[styles.completamentePagadaBadge, isSmallScreen && styles.completamentePagadaBadgeSmall]}>
                <Icon name="check-all" size={isSmallScreen ? 12 : 14} color="#155724" />
                <Text style={[styles.completamentePagadaText, isSmallScreen && styles.completamentePagadaTextSmall]}>COMPLETAMENTE PAGADA</Text>
              </View>
            )}
          </View>
          <View style={[styles.chevContainer, isSmallScreen && styles.chevContainerSmall]}>
            <Icon name={expandedId === idKey ? 'chevron-up' : 'chevron-down'} size={isSmallScreen ? 18 : 22} color="#4f8cff" />
          </View>
        </TouchableOpacity>

        {expandedId === idKey && (
          <View style={[styles.cardBody, isSmallScreen && styles.cardBodySmall]}>
            {todasPagadas ? (
              <View style={[styles.completamentePagadaContainer, isSmallScreen && styles.completamentePagadaContainerSmall]}>
                <Icon name="check-circle-outline" size={isSmallScreen ? 36 : 48} color="#28a745" />
                <Text style={[styles.completamentePagadaTitle, isSmallScreen && styles.completamentePagadaTitleSmall]}>Todas las cuotas pagadas</Text>
                <Text style={[styles.completamentePagadaSubtitle, isSmallScreen && styles.completamentePagadaSubtitleSmall]}>
                  Esta formación está completamente pagada. No hay cuotas pendientes.
                </Text>
              </View>
            ) : !item.pago_inscripcion_confirmada ? (
              <View style={[styles.emptyRow, isSmallScreen && styles.emptyRowSmall]}>
                <Icon name="alert-circle-outline" size={isSmallScreen ? 18 : 22} color="#856404" />
                <Text style={[styles.emptyText, isSmallScreen && styles.emptyTextSmall]}>
                  Las cuotas están visibles, pero no se pueden pagar hasta confirmar el pago de la inscripción.
                </Text>
              </View>
            ) : cuotas.length === 0 ? (
              <View style={[styles.emptyRow, isSmallScreen && styles.emptyRowSmall]}>
                <Icon name="calendar-remove" size={isSmallScreen ? 22 : 28} color="#dee2e6" />
                <Text style={[styles.emptyText, isSmallScreen && styles.emptyTextSmall]}>No hay cuotas configuradas para esta inscripción.</Text>
              </View>
            ) : (
              <>
                {cuotas.map((c: CuotaLite, index: number) => (
                  <View key={String(c.id ?? c.idCuota ?? index)} style={[styles.cuotaRow, isSmallScreen && styles.cuotaRowSmall]}>
                    <View style={{ flex: 1 }}>
                      <Text style={[styles.cuotaNombre, isSmallScreen && styles.cuotaNombreSmall, c.estadoPago === 'PAGADO' ? styles.cuotaPaidText : {}]}>
                        {c.nombreCuota}
                      </Text>
                      <Text style={[styles.cuotaSub, isSmallScreen && styles.cuotaSubSmall]}>{fmtMoney(c.valorCuota)}</Text>
                    </View>

                    <View style={[styles.cuotaActions, isSmallScreen && styles.cuotaActionsSmall]}>
                      {String(c.estadoPago ?? '').toUpperCase() === 'PAGADO' ? (
                        <View style={[styles.paidBadge, isSmallScreen && styles.paidBadgeSmall]}>
                          <Icon name="check-circle" size={isSmallScreen ? 14 : 16} color="#155724" />
                          <Text style={[styles.paidBadgeText, isSmallScreen && styles.paidBadgeTextSmall]}>PAGADA</Text>
                        </View>
                      ) : (c.pendingPayment || String(c.estadoPago ?? '').toUpperCase() === 'PENDIENTE') ? (
                        <View style={[styles.pendingBadge, isSmallScreen && styles.pendingBadgeSmall]}>
                          <Icon name="clock-outline" size={isSmallScreen ? 14 : 16} color="#856404" />
                          <Text style={[styles.pendingBadgeText, isSmallScreen && styles.pendingBadgeTextSmall]}>{c.pagoConfirmado ? 'CONFIRMADO' : 'EN REVISIÓN'}</Text>
                        </View>
                      ) : (
                        <TouchableOpacity
                          style={[styles.payButton, isSmallScreen && styles.payButtonSmall, c.disabled ? styles.payButtonDisabled : {}]}
                          disabled={c.disabled}
                          onPress={() => openPagoModal(item, c)}
                        >
                          <Text style={[styles.payButtonText, isSmallScreen && styles.payButtonTextSmall, c.disabled ? styles.payButtonTextDisabled : {}]}>Pagar</Text>
                        </TouchableOpacity>
                      )}
                    </View>
                  </View>
                ))}
                <View style={[styles.infoRow, isSmallScreen && styles.infoRowSmall]}>
                  <Text style={[styles.smallNote, isSmallScreen && styles.smallNoteSmall]}>
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
      {/* HEADER */}
      <View style={[styles.header, isSmallScreen && styles.headerSmall]}>
        <View style={styles.headerTitleContainer}>
          <Text style={[styles.title, isSmallScreen && styles.titleSmall]}>Cuotas por Pagar</Text>
          {user?.cedula && (
            <Text style={[styles.userCedula, isSmallScreen && styles.userCedulaSmall]}>Cédula: {user.cedula}</Text>
          )}
        </View>

        {/* Botón de recarga manual */}
        <TouchableOpacity
          style={[styles.headerRefreshButton, isSmallScreen && { right: 10, top: 12 }]}
          onPress={onRefresh}
          disabled={refreshing || loading}
        >
          <Icon name="refresh" size={20} color={refreshing || loading ? '#cbd5e1' : '#4f8cff'} />
        </TouchableOpacity>
      </View>

      {/* SUBTITLE */}
      <View style={[styles.subtitleContainer, isSmallScreen && styles.subtitleContainerSmall]}>
        <Text style={[styles.subtitle, isSmallScreen && styles.subtitleSmall]}>
          Paga tus cuotas en orden — la administración confirmará los pagos
        </Text>
      </View>

      {loading ? (
        <View style={styles.center}><ActivityIndicator size="large" color="#4f8cff" /></View>
      ) : inscripciones.length === 0 ? (
        <View style={styles.emptyContainer}>
          <Icon name="file-check" size={isSmallScreen ? 60 : 80} color="#e9ecef" />
          <Text style={[styles.emptyTitle, isSmallScreen && styles.emptyTitleSmall]}>No tienes cuotas pendientes</Text>
          <Text style={[styles.emptySubtitle, isSmallScreen && styles.emptySubtitleSmall]}>
            {user ? `Todas tus formaciones están completamente pagadas o no tienes inscripciones activas` : 'Inicia sesión para ver tus cuotas'}
          </Text>
        </View>
      ) : (
        <FlatList
          data={inscripciones}
          keyExtractor={(i) => String(i.idInscripcion ?? i.id ?? Math.random())}
          renderItem={renderInscripcionItem}
          contentContainerStyle={[styles.listContent, isSmallScreen && styles.listContentSmall]}
          refreshing={refreshing}
          onRefresh={onRefresh}
        />
      )}

      {/* MODAL DE PAGO - ahora contiene InfoCuentaBancaria */}
      <Modal
        isVisible={modalVisible}
        onBackdropPress={() => !submitting && closeModal()}
        style={[styles.modal, styles.formModal, isSmallScreen && styles.modalSmall]}
        avoidKeyboard
      >
        <KeyboardAvoidingView behavior={Platform.OS === 'ios' ? 'padding' : undefined} style={[styles.keyboardAvoid, { minHeight: Math.min(height * 0.9, 900) }]}>
          <View style={[styles.formModalContent, isSmallScreen ? styles.formModalContentSmall : {}, { maxHeight: Math.min(height * 0.95, 1000), width: isLargeScreen ? Math.min(720, width * 0.8) : undefined }]}>
            <View style={[styles.modalHeader, isSmallScreen && styles.modalHeaderSmall]}>
              <Text style={[styles.modalTitle, isSmallScreen && styles.modalTitleSmall]}>Pagar Cuota</Text>
              <TouchableOpacity style={[styles.closeButton, isSmallScreen && styles.closeButtonSmall]} onPress={() => !submitting && closeModal()} disabled={submitting}>
                <Icon name="close" size={isSmallScreen ? 20 : 22} color="#666" />
              </TouchableOpacity>
            </View>

            <ScrollView style={styles.formBody} showsVerticalScrollIndicator keyboardShouldPersistTaps="handled" contentContainerStyle={[styles.formContent, isSmallScreen && styles.formContentSmall, { paddingBottom: 24 }]}>
              {/* Información de la Cuota */}
              <View style={styles.formSection}>
                <View style={styles.sectionHeader}>
                  <Icon name="cash" size={isSmallScreen ? 18 : 20} color="#4f8cff" />
                  <Text style={[styles.sectionTitle, isSmallScreen && styles.sectionTitleSmall]}>Información de la Cuota</Text>
                </View>

                <View style={[styles.fieldContainer, isSmallScreen && styles.fieldContainerSmall]}>
                  <Text style={[styles.label, isSmallScreen && styles.labelSmall]}>Formación</Text>
                  <View style={[styles.cedulaFijaContainer, isSmallScreen && styles.cedulaFijaContainerSmall]}>
                    <Text style={[styles.cedulaFijaText, isSmallScreen && styles.cedulaFijaTextSmall]}>
                      {modalPayload?.inscripcion?.idFormacion_detail?.nombreFormacion ?? modalPayload?.inscripcion?.idFormacion_detail?.nombre ?? '—'}
                    </Text>
                  </View>
                </View>

                <View style={[styles.fieldContainer, isSmallScreen && styles.fieldContainerSmall]}>
                  <Text style={[styles.label, isSmallScreen && styles.labelSmall]}>Cuota</Text>
                  <View style={[styles.cedulaFijaContainer, isSmallScreen && styles.cedulaFijaContainerSmall]}>
                    <Text style={[styles.cedulaFijaText, isSmallScreen && styles.cedulaFijaTextSmall]}>
                      {modalPayload?.cuota?.nombreCuota} — {fmtMoney(modalPayload?.cuota?.valorCuota)}
                    </Text>
                  </View>
                </View>
              </View>

              {/* INFO DE CUENTA BANCARIA DENTRO DEL MODAL */}
              <InfoCuentaBancaria />

              {/* Información de Pago */}
              <View style={styles.formSection}>
                <View style={styles.sectionHeader}>
                  <Icon name="credit-card" size={isSmallScreen ? 18 : 20} color="#4f8cff" />
                  <Text style={[styles.sectionTitle, isSmallScreen && styles.sectionTitleSmall]}>Información de Pago</Text>
                </View>

                <View style={[styles.fieldContainer, isSmallScreen && styles.fieldContainerSmall]}>
                  <Text style={[styles.label, isSmallScreen && styles.labelSmall]}>Número de Referencia *</Text>
                  <TextInput 
                    value={referencia} 
                    onChangeText={setReferencia} 
                    placeholder="Ej: 123456789" 
                    style={[styles.input, isSmallScreen && styles.inputSmall]}
                    placeholderTextColor="#999"
                  />
                  <Text style={[styles.helpText, isSmallScreen && styles.helpTextSmall]}>Ingrese el número de referencia de su transferencia o depósito</Text>
                </View>

                <View style={[styles.fieldContainer, isSmallScreen && styles.fieldContainerSmall]}>
                  <Text style={[styles.label, isSmallScreen && styles.labelSmall]}>Fecha de Pago *</Text>
                  <View style={[styles.fechaContainer, isSmallScreen && styles.fechaContainerSmall]}>
                    <Text style={[styles.fechaText, isSmallScreen && styles.fechaTextSmall]}>{fechaPago}</Text>
                  </View>
                  <Text style={[styles.helpText, isSmallScreen && styles.helpTextSmall]}>Fecha automática (solo lectura)</Text>
                </View>

                <View style={[styles.fieldContainer, isSmallScreen && styles.fieldContainerSmall]}>
                  <Text style={[styles.label, isSmallScreen && styles.labelSmall]}>Observaciones (Opcional)</Text>
                  <TextInput 
                    value={observaciones} 
                    onChangeText={setObservaciones} 
                    placeholder="Ej: Pago cuota 1, transferencia bancaria" 
                    style={[styles.input, isSmallScreen && styles.inputSmall]}
                    placeholderTextColor="#999"
                    multiline
                    numberOfLines={3}
                    textAlignVertical="top"
                  />
                  <Text style={[styles.helpText, isSmallScreen && styles.helpTextSmall]}>Información adicional sobre el pago</Text>
                </View>
              </View>
            </ScrollView>

            <View style={[styles.formFooter, isSmallScreen && styles.formFooterSmall]}>
              <TouchableOpacity style={[styles.formButton, styles.cancelButton, isSmallScreen && styles.formButtonSmall]} onPress={closeModal} disabled={submitting}>
                <Text style={[styles.cancelButtonText, isSmallScreen && styles.cancelButtonTextSmall]}>Cancelar</Text>
              </TouchableOpacity>

              <TouchableOpacity style={[styles.formButton, styles.submitButton, isSmallScreen && styles.submitButton, isSmallScreen && styles.formButtonSmall]} onPress={handleSolicitarPago} disabled={submitting || !referencia.trim()}>
                {submitting ? <ActivityIndicator color="#fff" size="small" /> : <>
                  <Icon name="credit-card-check-outline" size={isSmallScreen ? 16 : 18} color="#fff" />
                  <Text style={[styles.submitButtonText, isSmallScreen && styles.submitButtonTextSmall]}>Solicitar Pago</Text>
                </>}
              </TouchableOpacity>
            </View>
          </View>
        </KeyboardAvoidingView>
      </Modal>
    </View>
  );
};

/* ESTILOS ACTUALIZADOS - IDÉNTICOS AL DE INSCRIPCIÓN + estilos de cuenta bancaria */
const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#f5f7fa' },

  // Header
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    paddingHorizontal: 16,
    paddingTop: 12,
    paddingBottom: 8,
    backgroundColor: '#fff',
    borderBottomWidth: 1,
    borderBottomColor: '#e1e5e9',
  },
  headerSmall: {
    paddingHorizontal: 12,
    paddingTop: 10,
    paddingBottom: 6,
  },
  headerTitleContainer: {
    flex: 1,
  },
  title: {
    fontSize: 20,
    fontWeight: '700',
    color: '#1a365d',
    marginBottom: 2,
  },
  titleSmall: {
    fontSize: 18,
  },
  userCedula: {
    fontSize: 12,
    color: '#666',
    fontWeight: '500',
  },
  userCedulaSmall: {
    fontSize: 11,
  },

  // Header refresh button
  headerRefreshButton: {
    padding: 8,
    alignSelf: 'center',
  },

  // Subtitle
  subtitleContainer: {
    paddingHorizontal: 16,
    paddingVertical: 8,
    backgroundColor: '#fff',
    borderBottomWidth: 1,
    borderBottomColor: '#e1e5e9',
  },
  subtitleContainerSmall: {
    paddingHorizontal: 12,
    paddingVertical: 6,
  },
  subtitle: {
    fontSize: 14,
    color: '#666',
    fontStyle: 'italic',
  },
  subtitleSmall: {
    fontSize: 13,
  },

  center: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: '#f5f7fa',
    padding: 20,
  },

  // List
  listContent: {
    padding: 12,
    paddingTop: 8,
    paddingBottom: 24,
  },
  listContentSmall: {
    padding: 10,
    paddingTop: 6,
  },

  // Cards
  card: {
    backgroundColor: '#fff',
    borderRadius: 12,
    padding: 14,
    marginBottom: 10,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.1,
    shadowRadius: 2,
    elevation: 2,
    borderWidth: 1,
    borderColor: '#f1f3f4',
  },
  cardSmall: {
    padding: 12,
    borderRadius: 10,
    marginBottom: 8,
  },
  cardHeader: {
    marginBottom: 10,
  },
  cardHeaderSmall: {
    marginBottom: 8,
  },
  cardTitle: {
    fontSize: 16,
    fontWeight: '600',
    color: '#1a365d',
    flex: 1,
    marginRight: 8,
  },
  cardTitleSmall: {
    fontSize: 15,
    marginRight: 0,
  },
  cardSubtitle: {
    fontSize: 13,
    color: '#6c757d',
    marginTop: 4,
  },
  cardSubtitleSmall: {
    fontSize: 12,
  },
  cardBody: {
    padding: 12,
    borderTopWidth: 1,
    borderTopColor: '#f1f3f4',
  },
  cardBodySmall: {
    padding: 10,
  },

  // Badges
  completamentePagadaBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#d4edda',
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 8,
    marginTop: 4,
    alignSelf: 'flex-start'
  },
  completamentePagadaBadgeSmall: {
    paddingHorizontal: 6,
    paddingVertical: 3,
    borderRadius: 6,
  },
  completamentePagadaText: {
    color: '#155724',
    fontWeight: '700',
    fontSize: 11,
    marginLeft: 4
  },
  completamentePagadaTextSmall: {
    fontSize: 10,
    marginLeft: 3
  },
  chevContainer: { paddingLeft: 8, paddingRight: 8 },
  chevContainerSmall: { paddingLeft: 6, paddingRight: 6 },

  // Estados
  completamentePagadaContainer: {
    alignItems: 'center',
    padding: 20,
    backgroundColor: '#f8fff9',
    borderRadius: 8,
    borderWidth: 1,
    borderColor: '#d4edda'
  },
  completamentePagadaContainerSmall: {
    padding: 16,
    borderRadius: 6,
  },
  completamentePagadaTitle: {
    fontSize: 16,
    fontWeight: '700',
    color: '#155724',
    marginTop: 8
  },
  completamentePagadaTitleSmall: {
    fontSize: 15,
    marginTop: 6,
  },
  completamentePagadaSubtitle: {
    fontSize: 14,
    color: '#28a745',
    textAlign: 'center',
    marginTop: 4
  },
  completamentePagadaSubtitleSmall: {
    fontSize: 13,
    marginTop: 3,
  },
  emptyRow: {
    alignItems: 'center',
    padding: 12,
    flexDirection: 'row',
    backgroundColor: '#fff8e1',
    borderRadius: 8
  },
  emptyRowSmall: {
    padding: 10,
    borderRadius: 6,
  },
  emptyText: {
    flex: 1,
    marginLeft: 10,
    color: '#856404',
    fontSize: 14,
  },
  emptyTextSmall: {
    fontSize: 13,
    marginLeft: 8,
  },

  // Cuotas
  cuotaRow: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: 10,
    borderBottomWidth: 1,
    borderBottomColor: '#f4f6f8'
  },
  cuotaRowSmall: {
    paddingVertical: 8,
  },
  cuotaNombre: {
    fontWeight: '600',
    color: '#2d3748',
    fontSize: 14,
  },
  cuotaNombreSmall: {
    fontSize: 13,
  },
  cuotaPaidText: {
    color: '#6c757d',
    textDecorationLine: 'line-through'
  },
  cuotaSub: {
    fontSize: 13,
    color: '#6c757d',
    marginTop: 4
  },
  cuotaSubSmall: {
    fontSize: 12,
    marginTop: 3,
  },
  cuotaActions: {
    minWidth: 110,
    alignItems: 'flex-end'
  },
  cuotaActionsSmall: {
    minWidth: 100,
  },

  // Botones de pago
  payButton: {
    backgroundColor: '#2b6cb0',
    paddingHorizontal: 14,
    paddingVertical: 8,
    borderRadius: 8
  },
  payButtonSmall: {
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 6,
  },
  payButtonText: {
    color: '#fff',
    fontWeight: '700',
    fontSize: 12,
  },
  payButtonTextSmall: {
    fontSize: 11,
  },
  payButtonDisabled: {
    backgroundColor: '#cbd5e1'
  },
  payButtonTextDisabled: {
    color: '#7b8794'
  },

  // Badges de estado
  paidBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#d4edda',
    paddingHorizontal: 10,
    paddingVertical: 6,
    borderRadius: 12
  },
  paidBadgeSmall: {
    paddingHorizontal: 8,
    paddingVertical: 5,
    borderRadius: 10,
  },
  paidBadgeText: {
    color: '#155724',
    fontWeight: '700',
    marginLeft: 6,
    fontSize: 11,
  },
  paidBadgeTextSmall: {
    fontSize: 10,
    marginLeft: 4,
  },
  pendingBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#ffeeba',
    paddingHorizontal: 10,
    paddingVertical: 6,
    borderRadius: 12
  },
  pendingBadgeSmall: {
    paddingHorizontal: 8,
    paddingVertical: 5,
    borderRadius: 10,
  },
  pendingBadgeText: {
    color: '#856404',
    fontWeight: '700',
    marginLeft: 6,
    fontSize: 11,
  },
  pendingBadgeTextSmall: {
    fontSize: 10,
    marginLeft: 4,
  },

  // Información adicional
  infoRow: {
    marginTop: 10
  },
  infoRowSmall: {
    marginTop: 8,
  },
  smallNote: {
    fontSize: 12,
    color: '#6c757d',
    fontStyle: 'italic'
  },
  smallNoteSmall: {
    fontSize: 11,
  },

  // Empty state
  emptyContainer: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    padding: 20
  },
  emptyTitle: {
    fontSize: 18,
    fontWeight: '700',
    color: '#495057',
    marginTop: 12
  },
  emptyTitleSmall: {
    fontSize: 16,
    marginTop: 10,
  },
  emptySubtitle: {
    fontSize: 14,
    color: '#6c757d',
    marginTop: 6,
    textAlign: 'center'
  },
  emptySubtitleSmall: {
    fontSize: 13,
    marginTop: 5,
  },

  // Modal (copiado de inscripciones)
  modal: {
    margin: 0,
    justifyContent: 'center',
    alignItems: 'center',
  },
  modalSmall: {
    paddingHorizontal: 8,
  },
  formModal: {
    margin: 0,
  },
  keyboardAvoid: {
    width: '100%',
    alignItems: 'center',
    flex: 1,
  },
  formModalContent: {
    backgroundColor: '#fff',
    borderRadius: 16,
    width: '90%',
    maxWidth: 500,
    maxHeight: '90%',
    overflow: 'hidden',
  },
  formModalContentSmall: {
    width: '95%',
    maxHeight: '95%',
    borderRadius: 14,
  },
  modalHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: 16,
    paddingBottom: 12,
    borderBottomWidth: 1,
    borderBottomColor: '#e1e5e9',
  },
  modalHeaderSmall: {
    padding: 14,
    paddingBottom: 10,
  },
  modalTitle: {
    fontSize: 18,
    fontWeight: '700',
    color: '#1a365d',
    flex: 1,
  },
  modalTitleSmall: {
    fontSize: 16,
  },
  closeButton: {
    padding: 4,
  },
  closeButtonSmall: {
    padding: 2,
  },
  formBody: {
    flex: 1,
  },
  formContent: {
    paddingBottom: 16,
  },
  formContentSmall: {
    paddingBottom: 14,
  },

  // Form sections
  formSection: {
    marginBottom: 8,
  },
  sectionHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    marginBottom: 12,
    paddingHorizontal: 16,
  },
  sectionTitle: {
    fontSize: 16,
    fontWeight: '700',
    color: '#2d3748',
  },
  sectionTitleSmall: {
    fontSize: 15,
  },
  fieldContainer: {
    marginBottom: 14,
    paddingHorizontal: 16,
  },
  fieldContainerSmall: {
    marginBottom: 12,
    paddingHorizontal: 14,
  },
  label: {
    fontWeight: '600',
    color: '#4a5568',
    marginBottom: 6,
    fontSize: 14,
  },
  labelSmall: {
    fontSize: 13,
    marginBottom: 4,
  },

  // Campos de solo lectura
  cedulaFijaContainer: {
    backgroundColor: '#f8f9fa',
    borderRadius: 10,
    paddingHorizontal: 12,
    paddingVertical: 10,
    borderWidth: 1,
    borderColor: '#e1e5e9',
  },
  cedulaFijaContainerSmall: {
    paddingHorizontal: 10,
    paddingVertical: 8,
    borderRadius: 8,
  },
  cedulaFijaText: {
    fontSize: 14,
    fontWeight: '600',
    color: '#4a5568',
  },
  cedulaFijaTextSmall: {
    fontSize: 13,
  },
  fechaContainer: {
    backgroundColor: '#f0fff4',
    borderRadius: 10,
    paddingHorizontal: 12,
    paddingVertical: 10,
    borderWidth: 1,
    borderColor: '#9ae6b4',
  },
  fechaContainerSmall: {
    paddingHorizontal: 10,
    paddingVertical: 8,
    borderRadius: 8,
  },
  fechaText: {
    fontSize: 14,
    fontWeight: '600',
    color: '#22543d',
  },
  fechaTextSmall: {
    fontSize: 13,
  },

  // Inputs editables
  input: {
    borderWidth: 1,
    borderColor: '#e1e5e9',
    borderRadius: 10,
    backgroundColor: '#fff',
    paddingHorizontal: 12,
    paddingVertical: 10,
    fontSize: 14,
    color: '#333',
  },
  inputSmall: {
    paddingHorizontal: 10,
    paddingVertical: 8,
    borderRadius: 8,
    fontSize: 13,
  },

  // Texto de ayuda
  helpText: {
    fontSize: 11,
    color: '#6c757d',
    marginTop: 4,
    fontStyle: 'italic',
  },
  helpTextSmall: {
    fontSize: 10,
  },

  // Footer del formulario
  formFooter: {
    flexDirection: 'row',
    padding: 16,
    paddingTop: 12,
    borderTopWidth: 1,
    borderTopColor: '#e1e5e9',
    gap: 10,
  },
  formFooterSmall: {
    padding: 14,
    paddingTop: 10,
    gap: 8,
  },
  formButton: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: 12,
    borderRadius: 10,
    gap: 6,
  },
  formButtonSmall: {
    paddingVertical: 10,
    borderRadius: 8,
    gap: 4,
  },
  cancelButton: {
    backgroundColor: '#fff',
    borderWidth: 1,
    borderColor: '#e1e5e9',
  },
  cancelButtonText: {
    color: '#4a5568',
    fontWeight: '600',
    fontSize: 14,
  },
  cancelButtonTextSmall: {
    fontSize: 13,
  },
  submitButton: {
    backgroundColor: '#4f8cff',
  },
  submitButtonText: {
    color: '#fff',
    fontWeight: '600',
    fontSize: 14,
  },
  submitButtonTextSmall: {
    fontSize: 13,
  },

  // ===== estilos de cuenta bancaria =====
  cuentaBancariaCard: {
    backgroundColor: '#fff',
    borderRadius: 12,
    padding: 12,
    marginVertical: 10,
    borderWidth: 1,
    borderColor: '#eef2f6',
  },
  cuentaHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 10,
  },
  cuentaTitle: {
    marginLeft: 8,
    fontSize: 15,
    fontWeight: '700',
    color: '#1f3b6e',
  },
  cuentaGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    marginTop: 6,
  },
  cuentaItem: {
    width: '50%',
    paddingVertical: 6,
  },
  cuentaLabel: {
    fontSize: 12,
    color: '#6c757d',
    marginBottom: 2,
  },
  cuentaValue: {
    fontSize: 14,
    color: '#213547',
    fontWeight: '600',
  },
  cuentaDestacado: {
    fontWeight: '800',
    color: '#0b2545',
  },
  cuentaInstrucciones: {
    marginTop: 10,
    backgroundColor: '#f8fafc',
    padding: 10,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: '#eef6f8',
  },
  instruccionesTitle: {
    fontWeight: '700',
    color: '#0b3b2f',
    marginBottom: 6,
  },
  instruccionesText: {
    color: '#495057',
    fontSize: 13,
    lineHeight: 18,
  },
});

export default CuotasPorPagarScreen;
