// src/screens/inscripciones.tsx
import React, { useCallback, useEffect, useState, useContext } from 'react';
import {
  View,
  Text,
  FlatList,
  ActivityIndicator,
  useWindowDimensions,
  TouchableOpacity,
  TextInput,
  ScrollView,
  KeyboardAvoidingView,
  Platform,
  Alert,
  StyleSheet,
} from 'react-native';
import Icon from 'react-native-vector-icons/MaterialCommunityIcons';
import Modal from 'react-native-modal';
import { useNavigation } from '@react-navigation/native';
import api from '../api/api';
import { AuthContext } from '../contexts/AuthContext';
import {
  TipoFormacion,
  Formacion,
  Cohorte,
  Inscripcion,
  Cuota
} from '../types/inscripciones';

// ---------- HELPERS LOCALES ----------
const fmtMoney = (v: any) => {
  const n = Number(v);
  if (!isFinite(n)) return '—';
  return `$${n.toFixed(2)}`;
};

const normalizarCedula = (cedula: string): string => {
  if (!cedula) return '';
  let normalizada = cedula.toString().toUpperCase().replace(/[\.\-\s]/g, '');
  if (/^[VEJG]/.test(normalizada)) {
    normalizada = normalizada.substring(1);
  }
  return normalizada;
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
        const replaced = val.replace(/'/g, '"');
        return JSON.parse(replaced);
      } catch {
        return null;
      }
    }
  }
  return null;
};

const normalizeCuotas = (raw: any): Cuota[] => {
  const out: Cuota[] = [];
  const parsed = safeParseJson(raw);
  if (!parsed) return out;

  if (Array.isArray(parsed)) {
    parsed.forEach((c: any) => {
      if (typeof c === 'number') {
        out.push({ nombreCuota: 'Cuota', valorCuota: Number(c) });
      } else if (typeof c === 'string') {
        const n = Number(c);
        out.push({ nombreCuota: 'Cuota', valorCuota: isFinite(n) ? n : 0 });
      } else if (typeof c === 'object') {
        const nombre = c.nombreCuota || c.nombre || c.descripcion || c.label || 'Cuota';
        const valor = Number(c.valorCuota ?? c.valor ?? c.monto ?? c.amount ?? 0) || 0;
        out.push({ nombreCuota: String(nombre), valorCuota: valor });
      }
    });
  } else if (typeof parsed === 'object') {
    const keys = Object.keys(parsed);
    const isKeyValue = keys.every(k => typeof parsed[k] === 'number' || !isNaN(Number(parsed[k])));
    if (isKeyValue) {
      keys.forEach(k => {
        out.push({ nombreCuota: k, valorCuota: Number(parsed[k]) || 0 });
      });
    } else {
      const nombre = parsed.nombreCuota || parsed.nombre || 'Cuota';
      const valor = Number(parsed.valorCuota ?? parsed.valor ?? parsed.monto ?? 0) || 0;
      out.push({ nombreCuota: String(nombre), valorCuota: valor });
    }
  }
  return out;
};

const cuotasFromFormacionObj = (f: any): Cuota[] => {
  if (!f) return [];
  if (f.cuotas && Array.isArray(f.cuotas)) return normalizeCuotas(f.cuotas);
  const candidate = (f.cuotas_json ?? f.cuotasData ?? f.cuotas_list ?? f.cuotasJson ?? f.cuotas) || null;
  if (candidate) return normalizeCuotas(candidate);
  if (f.inscripcioncuota_set && Array.isArray(f.inscripcioncuota_set)) return normalizeCuotas(f.inscripcioncuota_set);
  return [];
};

const parseToDate = (v: any): Date | null => {
  if (!v) return null;
  try {
    const d = new Date(String(v));
    if (!isNaN(d.getTime())) return d;
    return null;
  } catch {
    return null;
  }
};

const isCohorteActiva = (coh: any) => {
  if (!coh) return false;

  const fechaInicioRaw = coh.fechaInicio ?? coh.start_date ?? coh.startDate ?? coh.raw?.fechaInicio ?? coh.raw?.start_date ?? null;
  const start = parseToDate(fechaInicioRaw);
  if (!start) return false;

  const fechaFinRaw = coh.fechaFin ?? coh.end_date ?? coh.endDate ?? coh.raw?.fechaFin ?? coh.raw?.end_date ?? null;
  let end = parseToDate(fechaFinRaw);

  if (!end) {
    const lapso = Number(coh.lapsoInscripcion ?? coh.lapso ?? coh.lap ?? coh.raw?.lapsoInscripcion ?? 0);
    if (isFinite(lapso) && lapso > 0) {
      end = new Date(start);
      end.setDate(end.getDate() + lapso);
    } else {
      return false;
    }
  }

  const now = new Date();
  const startDay = new Date(start.getFullYear(), start.getMonth(), start.getDate()).getTime();
  const endDay = new Date(end.getFullYear(), end.getMonth(), end.getDate()).getTime();
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate()).getTime();

  const estado = String(coh.estadoCohorte ?? coh.estado ?? '').toUpperCase();
  if (estado === 'INACTIVO' || estado === 'CERRADO') return false;

  return today >= startDay && today <= endDay;
};

// ---------- COMPONENT ----------
const InscripcionesScreen = () => {
  const navigation = useNavigation<any>();
  const { user } = useContext(AuthContext);

  // ----------------------------------------
  // Hooks
  // ----------------------------------------
  const { width, height } = useWindowDimensions();
  const isSmallScreen = width <= 620;
  const isLargeScreen = width >= 900;

  const [formDataLoading, setFormDataLoading] = useState(false);
  const [items, setItems] = useState<Inscripcion[]>([]);
  const [mostradas, setMostradas] = useState<Inscripcion[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchText, setSearchText] = useState('');
  const [detailModalVisible, setDetailModalVisible] = useState(false);
  const [selected, setSelected] = useState<Inscripcion | null>(null);

  // Form modal
  const [formModalVisible, setFormModalVisible] = useState(false);
  const [creating, setCreating] = useState(false);

  // Datos del formulario
  const [tiposFormacion, setTiposFormacion] = useState<TipoFormacion[]>([]);
  const [formaciones, setFormaciones] = useState<Formacion[]>([]);
  const [availableFormaciones, setAvailableFormaciones] = useState<Formacion[]>([]);
  const [formacionesFiltradas, setFormacionesFiltradas] = useState<Formacion[]>([]);
  const [cohortes, setCohortes] = useState<Cohorte[]>([]);

  const [selectedTipoFormacion, setSelectedTipoFormacion] = useState<number | null>(null);
  const [selectedFormacion, setSelectedFormacion] = useState<number | null>(null);
  const [selectedCohorte, setSelectedCohorte] = useState<number | null>(null);

  const [valorInscripcion, setValorInscripcion] = useState(0);
  const [cuotas, setCuotas] = useState<Cuota[]>([]);
  const [totalCuotas, setTotalCuotas] = useState(0);
  const [montoTotal, setMontoTotal] = useState(0);

  const [fechaInscripcion, setFechaInscripcion] = useState<string>('');
  const [formErrors, setFormErrors] = useState<Record<string, string>>({});
  const [formacionDetailsMap, setFormacionDetailsMap] = useState<Record<number, any>>({});

  // --- Selecciones con modal (reemplazan los Pickers)
  const [showTipoModal, setShowTipoModal] = useState(false);
  const [showFormacionModal, setShowFormacionModal] = useState(false);
  const [searchFormacionModal, setSearchFormacionModal] = useState('');

  const handleTipoSelect = (idTF: number | null) => {
    setSelectedTipoFormacion(idTF);
    setShowTipoModal(false);
  };

  const handleFormacionSelect = (idForm: number | null) => {
    setSelectedFormacion(idForm);
    setShowFormacionModal(false);
    const coh = findActiveCohorteForFormacion(idForm ?? undefined);
    if (coh) setSelectedCohorte(Number(coh.idCohorte));
    else setSelectedCohorte(null);
  };

  // ---------- API helpers ----------
  const fetchCuotasForFormacion = async (idFormacion: number): Promise<Cuota[]> => {
    if (!idFormacion) return [];
    try {
      const res = await api.get(`/api/formaciones/${idFormacion}/cuotas/`);
      const data = Array.isArray(res.data) ? res.data : (res.data.results ?? []);
      return data.map((c: any) => ({
        nombreCuota: c.nombreCuota ?? c.nombre ?? `Cuota ${c.id ?? ''}`,
        valorCuota: Number(c.valorCuota ?? c.valor ?? c.monto ?? 0),
      }));
    } catch (err) {
      console.warn('Error cargando cuotas de formacion', idFormacion, err);
      return [];
    }
  };

  const getFormacionDetails = async (idFormacion: number) => {
    if (!idFormacion) return null;
    if (formacionDetailsMap[idFormacion]) return formacionDetailsMap[idFormacion];
    try {
      const res = await api.get(`/api/formaciones/${idFormacion}/`);
      setFormacionDetailsMap(prev => ({ ...prev, [idFormacion]: res.data }));
      return res.data;
    } catch (e) {
      console.warn(`No se pudo obtener detalle de formacion ${idFormacion}`, e);
      return null;
    }
  };

  // ---------- Inscripciones (mejorada: chequeo pago temporal) ----------
  const fetchInscripciones = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      if (!user?.cedula) {
        setItems([]);
        setMostradas([]);
        setLoading(false);
        return;
      }
      const cedulaUsuarioNormalizada = normalizarCedula(user.cedula);
      const res = await api.get('/api/inscripcion/');
      const todas = Array.isArray(res.data) ? res.data : (res.data.results ?? []);

      // Intentar obtener pagos temporales (si existe endpoint). Si falla, seguimos sin esa info.
      let pagosTemp: any[] = [];
      try {
        const rPago = await api.get('/api/pago-temporal/'); // <--- ajusta si tu endpoint se llama distinto
        pagosTemp = Array.isArray(rPago.data) ? rPago.data : (rPago.data.results ?? []);
      } catch (err: any) {
        console.warn('No se pudo obtener pago-temporal (se ignorará):', err?.message ?? err);
        pagosTemp = [];
      }

      const inscripcionesUsuario = todas.filter((ins: any) => {
        const cedulaInscripcion = ins.idPersona_detail?.cedula || ins.idPersona?.cedula;
        if (!cedulaInscripcion) return false;
        return normalizarCedula(cedulaInscripcion) === cedulaUsuarioNormalizada;
      }).map((ins: any) => {
        const rawForm = ins.idFormacion_detail ?? ins.idFormacion ?? ins.formacion ?? null;
        const formNormalized = rawForm
          ? {
              idFormacion: Number(rawForm.idFormacion ?? rawForm.id ?? rawForm.pk ?? 0),
              nombreFormacion: rawForm.nombreFormacion ?? rawForm.nombre ?? rawForm.title ?? rawForm.name ?? null,
              valorInscripcion: Number(rawForm.valorInscripcion ?? rawForm.precio ?? rawForm.costo ?? rawForm.valor ?? 0),
              cuotas: rawForm.cuotas ?? rawForm.cuotas_json ?? rawForm.inscripcioncuota_set ?? []
            }
          : null;

        const rawCoh = ins.idCohorte ?? ins.idCohorte_detail ?? ins.cohorte ?? null;
        const cohNormalized = rawCoh
          ? {
              idCohorte: Number(rawCoh.idCohorte ?? rawCoh.id ?? 0),
              nombreCohorte: rawCoh.nombreCohorte ?? rawCoh.nombre ?? rawCoh.title ?? null,
              idFormacion: (typeof rawCoh.idFormacion === 'object' && rawCoh.idFormacion !== null)
                ? {
                    idFormacion: Number(rawCoh.idFormacion.idFormacion ?? rawCoh.idFormacion.id ?? 0),
                    nombreFormacion: rawCoh.idFormacion.nombreFormacion ?? rawCoh.idFormacion.nombre ?? null,
                    valorInscripcion: Number(rawCoh.idFormacion.valorInscripcion ?? 0)
                  }
                : (rawCoh.idFormacion ? { idFormacion: Number(rawCoh.idFormacion) } : null)
            }
          : null;

        const fecha = ins.fechaInscripcion ?? ins.fecha ?? ins.created_at ?? null;
        const montoTot = Number(ins.montoTotal ?? ins.total ?? ins.monto ?? ins.valor ?? 0);
        const montoPag = Number(ins.montoPagado ?? ins.pagado ?? 0);

        // --- comprobar pagos temporales: si existe uno confirmado para esta inscripcion => marcar PAGADO
        let estadoPagoFinal = ins.estadoPago ?? 'PENDIENTE';
        let montoPagFinal = montoPag;
        try {
          if (pagosTemp && pagosTemp.length) {
            const match = pagosTemp.find((pt: any) => {
              const ptIns = pt.idInscripcion ?? pt.inscripcion ?? pt.inscripcion_id ?? pt.related_inscripcion ?? pt.id_inscripcion ?? null;
              const confirmado = !!(pt.confirmado || pt.confirmado === true || pt.confirmado === 'true' || pt.confirmado === '1' || String(pt.estado || '').toUpperCase() === 'CONFIRMADO' || String(pt.is_confirmed || '').toLowerCase() === 'true' || pt.confirmation === true);
              if (!ptIns) return false;
              const ptInsNum = Number(ptIns);
              const insId = Number(ins.idInscripcion ?? ins.id ?? ins.pk ?? 0);
              return ptInsNum === insId && confirmado;
            });
            if (match) {
              estadoPagoFinal = 'PAGADO';
              montoPagFinal = montoTot;
            }
          }
        } catch (e) {
          console.warn('Error evaluando pagoTemporal para inscripcion', ins.idInscripcion, e);
        }

        return {
          ...ins,
          fechaInscripcion: fecha,
          montoTotal: montoTot,
          montoPagado: montoPagFinal,
          idCohorte_detail: cohNormalized,
          idFormacion_detail: formNormalized,
          estadoPago: estadoPagoFinal
        } as Inscripcion;
      });

      setItems(inscripcionesUsuario);
      setMostradas(inscripcionesUsuario);
    } catch (e: any) {
      setError(e?.response?.data?.detail ?? e?.message ?? 'Error al cargar inscripciones');
    } finally {
      setLoading(false);
    }
  }, [user?.cedula]);

  // ---------- Fetch tipos/formaciones/cohortes ----------
  const fetchDatosFormulario = useCallback(async () => {
    setFormDataLoading(true);
    try {
      const requests = [
        api.get('/api/tipo-formaciones/'),
        api.get('/api/formaciones/'),
        api.get('/api/cohorte/'),
      ];
      const results = await Promise.allSettled(requests);

      const tiposData = results[0].status === 'fulfilled' ? results[0].value.data : [];
      const formacionesData = results[1].status === 'fulfilled' ? results[1].value.data : [];
      const cohortesData = results[2].status === 'fulfilled' ? results[2].value.data : [];

      const toArray = (resp: any) => {
        if (!resp) return [];
        if (Array.isArray(resp)) return resp;
        if (resp.results && Array.isArray(resp.results)) return resp.results;
        if (resp.data && Array.isArray(resp.data)) return resp.data;
        if (typeof resp === 'object') return [resp];
        return [];
      };

      const tiposArr = toArray(tiposData);
      const formsArr = toArray(formacionesData);
      const cohortesArr = toArray(cohortesData);

      const extract = (items: any[], tipo: string) => items.map((item: any) => {
        if (tipo === 'tipos') {
          const idTF = Number(item.idTF ?? item.id ?? item.tipo_id ?? item.id_tipo ?? 0);
          return { idTF, nombreTipoFormacion: item.nombreTipoFormacion ?? item.nombre ?? item.descripcion ?? 'Sin nombre' };
        }

        if (tipo === 'formaciones') {
          const idTF = Number(
            item.idTF ??
            item.tipo_formacion ??
            item.tipoFormacion?.idTF ??
            item.tipo?.id ??
            item.tipo_id ??
            item.tipoId ??
            item.id_tipo ??
            0
          );

          const idFormacion = Number(item.idFormacion ?? item.id ?? item.pk ?? 0);
          const cuotasParsed = cuotasFromFormacionObj(item);

          return {
            idFormacion,
            nombreFormacion: item.nombreFormacion ?? item.nombre ?? item.title ?? 'Sin nombre',
            idTF,
            valorInscripcion: Number(item.valorInscripcion ?? item.precio ?? item.costo ?? item.valor ?? 0),
            tieneCuotas: Boolean((item.cuotas && item.cuotas.length) || cuotasParsed.length),
            cantidad_cuotas: Number(item.cantidad_cuotas ?? cuotasParsed.length ?? 0),
            cuotas: cuotasParsed,
            raw: item
          };
        }

        if (tipo === 'cohortes') {
          const idFormRaw = item.idFormacion ?? item.idFormacion_detail ?? item.formacion ?? item.id_formacion ?? null;
          const idFormacionObj = (typeof idFormRaw === 'object' && idFormRaw !== null)
            ? { idFormacion: Number(idFormRaw.idFormacion ?? idFormRaw.id ?? idFormRaw.pk ?? 0), nombreFormacion: idFormRaw.nombreFormacion ?? idFormRaw.nombre ?? null, valorInscripcion: Number(idFormRaw.valorInscripcion ?? idFormRaw.precio ?? 0) }
            : (idFormRaw ? { idFormacion: Number(idFormRaw) } : null);

          const idCohorte = Number(item.idCohorte ?? item.id ?? item.pk ?? 0);
          const idFormacionId = idFormacionObj ? Number(idFormacionObj.idFormacion ?? 0) : (typeof idFormRaw === 'number' ? Number(idFormRaw) : 0);

          return {
            idCohorte,
            nombreCohorte: item.nombreCohorte ?? item.nombre ?? item.title ?? 'Sin nombre',
            lapsoInscripcion: Number(item.lapsoInscripcion ?? item.lapso ?? 0),
            fechaInicio: item.fechaInicio ?? item.start_date ?? item.startDate ?? item.raw?.fechaInicio ?? null,
            fechaFin: item.fechaFin ?? item.end_date ?? item.endDate ?? item.raw?.fechaFin ?? null,
            estadoCohorte: item.estadoCohorte ?? item.estado ?? 'INACTIVO',
            idFormacion: idFormacionObj,
            idFormacionId,
            raw: item
          };
        }
        return item;
      });

      const tipos = extract(tiposArr, 'tipos');
      const forms = extract(formsArr, 'formaciones');
      const cohorts = extract(cohortesArr, 'cohortes');

      setTiposFormacion(tipos);
      setFormaciones(forms);
      setCohortes(cohorts);
    } catch (e) {
      console.warn('Error fetchDatosFormulario', e);
      Alert.alert('Error', 'No se pudieron cargar los datos del formulario');
    } finally {
      setFormDataLoading(false);
    }
  }, []);

  // ---------- Fecha por defecto ----------
  const establecerFechaActual = () => {
    const ahora = new Date();
    const fecha = ahora.toISOString().split('T')[0];
    setFechaInscripcion(fecha);
  };

  useEffect(() => {
    if (formModalVisible) {
      establecerFechaActual();
      fetchDatosFormulario();
    }
  }, [formModalVisible, fetchDatosFormulario]);

  useEffect(() => {
    fetchInscripciones();
  }, [fetchInscripciones]);

  // ---------- Calcular formaciones disponibles (solo las que tengan cohorte activa) ----------
  useEffect(() => {
    const activeCohortesByFormacion: Record<number, Cohorte[]> = {};

    cohortes.forEach((coh: any) => {
      let idFormacionNum = 0;
      if (coh.idFormacionId) idFormacionNum = Number(coh.idFormacionId);
      else if (coh.idFormacion && typeof coh.idFormacion === 'object') idFormacionNum = Number(coh.idFormacion.idFormacion ?? coh.idFormacion.id ?? 0);
      else if (coh.raw && coh.raw.idFormacion) idFormacionNum = Number(coh.raw.idFormacion);
      else if (typeof coh.idFormacion === 'number') idFormacionNum = Number(coh.idFormacion);

      if (!idFormacionNum) return;

      if (isCohorteActiva(coh)) {
        if (!activeCohortesByFormacion[idFormacionNum]) activeCohortesByFormacion[idFormacionNum] = [];
        activeCohortesByFormacion[idFormacionNum].push(coh);
      }
    });

    const available = formaciones.filter(f => {
      const idF = Number((f as any).idFormacion ?? (f as any).id ?? 0);
      return Boolean(activeCohortesByFormacion[idF] && activeCohortesByFormacion[idF].length > 0);
    });

    if (available.length === 0) {
      setAvailableFormaciones(formaciones);
    } else {
      setAvailableFormaciones(available);
    }
  }, [formaciones, cohortes]);

  // ---------- Filtrado formaciones por tipo (ahora usa availableFormaciones) ----------
  useEffect(() => {
    if (!availableFormaciones || availableFormaciones.length === 0) {
      setFormacionesFiltradas([]);
      return;
    }

    if (selectedTipoFormacion !== null && selectedTipoFormacion !== undefined) {
      const selectedTipoNum = Number(selectedTipoFormacion);
      const filtradas = availableFormaciones.filter(f => Number((f as any).idTF) === selectedTipoNum);
      setFormacionesFiltradas(filtradas);
      setSelectedFormacion(null);

      if (filtradas.length === 1) {
        const autoId = Number(filtradas[0].idFormacion);
        setSelectedFormacion(autoId);
        const coh = findActiveCohorteForFormacion(autoId);
        if (coh) setSelectedCohorte(Number(coh.idCohorte));
      }
    } else {
      setFormacionesFiltradas(availableFormaciones);
    }
  }, [selectedTipoFormacion, availableFormaciones]);

  const findActiveCohorteForFormacion = (idFormacion: number | undefined | null): any => {
    if (!idFormacion) return null;
    const matches = cohortes
      .filter((c: any) => {
        let idF = 0;
        if (c.idFormacionId) idF = Number(c.idFormacionId);
        else if (c.idFormacion && typeof c.idFormacion === 'object') idF = Number(c.idFormacion.idFormacion ?? c.idFormacion.id ?? 0);
        else if (c.raw && c.raw.idFormacion) idF = Number(c.raw.idFormacion);
        else if (typeof c.idFormacion === 'number') idF = Number(c.idFormacion);
        return idF === Number(idFormacion) && isCohorteActiva(c);
      })
      .sort((a: any, b: any) => {
        const da = parseToDate(a.fechaInicio ?? a.start_date ?? a.startDate ?? 0)?.getTime() ?? 0;
        const db = parseToDate(b.fechaInicio ?? b.start_date ?? b.startDate ?? 0)?.getTime() ?? 0;
        return da - db;
      });

    return matches.length ? matches[0] : null;
  };

  // ---------- Cuando cambia selectedFormacion -> autoseleccionar cohorte asociada y calcular costos ----------
  useEffect(() => {
    let mounted = true;
    const compute = async () => {
      if (selectedFormacion === null || selectedFormacion === undefined) {
        if (!mounted) return;
        setValorInscripcion(0);
        setCuotas([]);
        setTotalCuotas(0);
        setMontoTotal(0);
        setSelectedCohorte(null);
        return;
      }

      const coh: any = findActiveCohorteForFormacion(selectedFormacion);
      if (coh) {
        setSelectedCohorte(Number(coh.idCohorte));
        const idFormObj = (coh.idFormacion && typeof coh.idFormacion === 'object') ? coh.idFormacion : null;
        const valorFromCohForm = Number(idFormObj?.valorInscripcion ?? coh.raw?.valorInscripcion ?? 0);
        if (isFinite(valorFromCohForm) && valorFromCohForm > 0) {
          setValorInscripcion(Number(valorFromCohForm));
        }
      } else {
        setSelectedCohorte(null);
      }

      const formacionLocal = formaciones.find(f => Number(f.idFormacion) === Number(selectedFormacion)) as any;
      let valorMatricula = Number(formacionLocal?.valorInscripcion ?? 0);

      let cuotasData: Cuota[] = [];
      try {
        cuotasData = await fetchCuotasForFormacion(Number(selectedFormacion));
      } catch {
        cuotasData = [];
      }

      if ((!valorMatricula || valorMatricula === 0) && selectedFormacion) {
        try {
          const detalle = await api.get(`/api/formaciones/${selectedFormacion}/`);
          const det = detalle.data;
          if (det) {
            valorMatricula = Number(det.valorInscripcion ?? det.precio ?? valorMatricula ?? 0);
            if (!cuotasData.length) {
              const cuotasFromDetail = det.cuotas ?? det.cuotas_json ?? det.inscripcioncuota_set ?? null;
              if (cuotasFromDetail) {
                const parsed = safeParseJson(cuotasFromDetail);
                if (Array.isArray(parsed) && parsed.length > 0) {
                  const mapped = parsed.map((c: any) => ({
                    nombreCuota: c.nombreCuota ?? c.nombre ?? `Cuota`,
                    valorCuota: Number(c.valorCuota ?? c.valor ?? c.monto ?? 0),
                  }));
                  if (mounted) setCuotas(mapped);
                  const totalC = mapped.reduce((s: number, x: any) => s + (Number(x.valorCuota) || 0), 0);
                  if (mounted) {
                    setTotalCuotas(totalC);
                    setMontoTotal(Number(valorMatricula) + totalC);
                    setValorInscripcion(Number(valorMatricula));
                  }
                  return;
                }
              }
            }
          }
        } catch (e) { /* ignore - use what we have */ }
      }

      const totalCtas = cuotasData.reduce((sum, c) => sum + (Number(c.valorCuota) || 0), 0);
      const totalFinal = Number(valorMatricula) + totalCtas;
      if (!mounted) return;
      setValorInscripcion(Number(valorMatricula || 0));
      setCuotas(cuotasData);
      setTotalCuotas(totalCtas);
      setMontoTotal(totalFinal);
    };

    compute();
    return () => { mounted = false; };
  }, [selectedFormacion, formaciones]);

  // ---------- Buscador simple ----------
  useEffect(() => {
    const q = searchText.trim().toLowerCase();
    if (!q) {
      setMostradas(items);
      return;
    }
    setMostradas(items.filter(i => {
      const ced = (i.idPersona_detail?.cedula ?? '').toString().toLowerCase();
      const form = (i.idFormacion_detail?.nombreFormacion ?? i.idFormacion_detail?.nombre ?? '').toString().toLowerCase();
      const coh = (i.idCohorte_detail?.nombreCohorte ?? '').toString().toLowerCase();
      const estado = (i.estadoPago ?? '').toString().toLowerCase();
      return ced.includes(q) || form.includes(q) || coh.includes(q) || estado.includes(q);
    }));
  }, [searchText, items]);

  // ---------- Detalle ----------
  const openDetail = async (item: any) => {
    let merged = { ...item };
    try {
      const idForm = Number(item.idFormacion ?? item.idFormacion_detail?.idFormacion ?? item.idFormacion_detail?.id);
      if (idForm) {
        const cuotasRealtime = await fetchCuotasForFormacion(idForm);
        if (cuotasRealtime && cuotasRealtime.length > 0) {
          merged = {
            ...merged,
            idFormacion_detail: {
              ...(merged.idFormacion_detail || {}),
              cuotas: cuotasRealtime,
              valorInscripcion: merged.idFormacion_detail?.valorInscripcion ?? merged.montoTotal ?? 0,
              nombreFormacion: merged.idFormacion_detail?.nombreFormacion ?? merged.idFormacion_detail?.nombre ?? merged.idFormacion_detail?.title ?? null
            }
          };
        } else {
          try {
            const d = await api.get(`/api/formaciones/${idForm}/`);
            if (d?.data) {
              const det = d.data;
              merged = {
                ...merged,
                idFormacion_detail: {
                  ...(merged.idFormacion_detail || {}),
                  idFormacion: Number(det.idFormacion ?? det.id ?? idForm),
                  nombreFormacion: det.nombreFormacion ?? det.nombre ?? det.title ?? det.name ?? merged.idFormacion_detail?.nombreFormacion,
                  valorInscripcion: Number(det.valorInscripcion ?? det.precio ?? det.costo ?? merged.idFormacion_detail?.valorInscripcion ?? 0),
                  cuotas: det.cuotas ?? det.inscripcioncuota_set ?? merged.idFormacion_detail?.cuotas ?? []
                }
              };
            }
          } catch (e) { /* ignore */ }
        }
      }
    } catch (e) {
      console.warn('openDetail: error obteniendo cuotas', e);
    }
    setSelected(merged);
    setDetailModalVisible(true);
  };

  // ---------- Validación y creación ----------
  const validateCreateForm = () => {
    const errs: Record<string, string> = {};
    if (selectedTipoFormacion === null) errs.tipoFormacion = 'Seleccione un tipo de formación';
    if (selectedFormacion === null) errs.formacion = 'Seleccione una formación';
    if (selectedCohorte === null) errs.cohorte = 'No se encontró una cohorte activa para la formación seleccionada';
    if (!user) errs.usuario = 'No se pudo obtener la información del usuario. Por favor, cierre sesión y vuelva a ingresar.';
    setFormErrors(errs);
    return Object.keys(errs).length === 0;
  };

  const handleCreateInscripcion = async () => {
    if (!validateCreateForm()) {
      Alert.alert('Formulario inválido', 'Corrige los errores antes de continuar.');
      return;
    }
    let idPersonaEnviar: number | null = null;
    if (!user) {
      Alert.alert('Error', 'No se pudo identificar su usuario. Por favor, cierre sesión y vuelva a ingresar.');
      return;
    }
    if (typeof user.idPersona === 'object' && user.idPersona !== null) {
      idPersonaEnviar = Number((user.idPersona as any).idPersona ?? (user.idPersona as any).id ?? null);
    } else {
      idPersonaEnviar = Number(user.idPersona ?? null);
    }
    if (!idPersonaEnviar) {
      Alert.alert('Error', 'No se pudo obtener el idPersona del usuario.');
      return;
    }

    setCreating(true);
    try {
      const payload = {
        idPersona: idPersonaEnviar,
        idCohorte: selectedCohorte,
        montoTotal: montoTotal,
        montoPagado: 0,
        estadoPago: 'PENDIENTE',
        fechaInscripcion: new Date().toISOString().slice(0, 19).replace('T', ' ')
      };

      const res = await api.post('/api/inscripcion/', payload);
      if (res.status === 201 || res.status === 200) {
        try {
          const notaResponse = await api.post('/api/nota-cobro/create/', { idInscripcion: res.data.idInscripcion });
          if (notaResponse.data.success) {
            navigation.navigate('pago', {
              notaData: notaResponse.data.data,
              inscripcionId: res.data.idInscripcion
            });
            Alert.alert('Éxito', 'Inscripción y nota de cobro creadas correctamente. Proceda al pago.');
          } else {
            throw new Error(notaResponse.data.message || 'Error creando nota');
          }
        } catch (notaError) {
          Alert.alert('Atención', 'Inscripción creada pero hubo un error al generar la nota de cobro. Contacte al administrador.');
        }
        setFormModalVisible(false);
        resetForm();
        await fetchInscripciones();
      }
    } catch (err: any) {
      if (err.response?.status === 400) {
        let errorMessage = 'Errores de validación:\n';
        if (err.response.data && typeof err.response.data === 'object') {
          Object.keys(err.response.data).forEach(key => {
            if (Array.isArray(err.response.data[key])) {
              errorMessage += `• ${key}: ${err.response.data[key].join(', ')}\n`;
            } else {
              errorMessage += `• ${key}: ${err.response.data[key]}\n`;
            }
          });
        } else {
          errorMessage = err.response.data?.detail || JSON.stringify(err.response.data);
        }
        Alert.alert('Error de Validación', errorMessage);
        setCreating(false);
        return;
      }
      Alert.alert('Error', err.response?.data?.detail ?? err.message ?? 'Error desconocido al crear inscripción');
    } finally {
      setCreating(false);
    }
  };

  const resetForm = () => {
    setSelectedTipoFormacion(null);
    setSelectedFormacion(null);
    setSelectedCohorte(null);
    setFormErrors({});
    setValorInscripcion(0);
    setCuotas([]);
    setTotalCuotas(0);
    setMontoTotal(0);
  };

  const deriveStatus = (item: any) => {
    if (String(item.estadoPago ?? '').toUpperCase() === 'PAGADO') return 'PAGADO';
    const paid = Number(item.montoPagado ?? 0) || 0;
    const total = Number(item.montoTotal ?? item.montoTotal ?? 0) || 0;
    if (total > 0 && paid >= total) return 'PAGADO';
    if (paid > 0 && paid < total) return 'PARCIAL';
    return (item.estadoPago ?? 'PENDIENTE') as string;
  };

  const statusColor = (status: string) => {
    if (status === 'PAGADO') return styles.badgeActive;
    if (status === 'PARCIAL') return styles.badgePartial;
    return styles.badgeInactive;
  };

  if (loading) return <View style={styles.center}><ActivityIndicator size="large" color="#4f8cff" /></View>;
  if (error) return <View style={styles.center}><Text style={styles.errorText}>{error}</Text></View>;

  // Handler para selección de formación: autoselecciona cohorte activa asociada
  const handleSelectFormacion = (v: any) => {
    const id = (v === undefined || v === null) ? null : Number(v);
    setSelectedFormacion(id);
    const coh = findActiveCohorteForFormacion(id ?? undefined);
    if (coh) setSelectedCohorte(Number(coh.idCohorte));
    else setSelectedCohorte(null);
  };

  // Filtrado de formaciones en modal por búsqueda
  const formacionesFiltradasParaModal = formacionesFiltradas.filter((f: any) => {
    if (!searchFormacionModal) return true;
    return (f.nombreFormacion || '').toLowerCase().includes(searchFormacionModal.toLowerCase());
  });

  return (
    <View style={styles.container}>
      {/* HEADER */}
      <View style={[styles.header, isSmallScreen && styles.headerSmall]}>
        <View style={styles.headerTitleContainer}>
          <Text style={[styles.title, isSmallScreen && styles.titleSmall]}>Mis Inscripciones</Text>
          {user?.cedula && (
            <Text style={[styles.userCedula, isSmallScreen && styles.userCedulaSmall]}>Cédula: {user.cedula}</Text>
          )}
        </View>
        <TouchableOpacity
          style={[styles.addButton, isSmallScreen && styles.addButtonSmall]}
          onPress={() => setFormModalVisible(true)}
        >
          <Icon name="plus" size={isSmallScreen ? 18 : 22} color="#fff" />
          <Text style={[styles.addButtonText, isSmallScreen && styles.addButtonTextSmall]}>Nueva</Text>
        </TouchableOpacity>
      </View>

      {/* SEARCH */}
      <View style={[styles.searchContainer, isSmallScreen && styles.searchContainerSmall]}>
        <View style={[styles.searchWrapper, isSmallScreen && styles.searchWrapperSmall]}>
          <Icon name="magnify" size={isSmallScreen ? 16 : 18} color="#666" />
          <TextInput
            placeholder="Buscar formación, cohorte..."
            value={searchText}
            onChangeText={setSearchText}
            style={[styles.searchInput, isSmallScreen && styles.searchInputSmall]}
            placeholderTextColor="#999"
            returnKeyType="search"
          />
          {searchText.length > 0 && (
            <TouchableOpacity onPress={() => setSearchText('')}>
              <Icon name="close-circle" size={isSmallScreen ? 16 : 18} color="#999" />
            </TouchableOpacity>
          )}
        </View>
      </View>

      {/* COUNT */}
      <View style={[styles.counterContainer, isSmallScreen && styles.counterContainerSmall]}>
        <Text style={[styles.counterText, isSmallScreen && styles.counterTextSmall]}>
          {mostradas.length} de {items.length} inscripciones
        </Text>
      </View>

      {/* LIST */}
      <FlatList
        data={mostradas}
        keyExtractor={(i) => String(i.idInscripcion ?? (i as any).id ?? Math.random())}
        renderItem={({ item }) => {
          const status = deriveStatus(item);
          const nombreFormacionDisplay = item.idFormacion_detail?.nombreFormacion ?? item.idFormacion_detail?.nombre ?? '—';
          const valorDisplay = item.idFormacion_detail?.valorInscripcion ?? item.idFormacion_detail?.valor ?? item.montoTotal ?? 0;
          const cohorteDisplay = item.idCohorte_detail?.nombreCohorte ?? item.idCohorte?.nombreCohorte ?? '—';
          const fechaDisplay = item.fechaInscripcion ? new Date(item.fechaInscripcion).toLocaleDateString() : '—';

          return (
            <TouchableOpacity
              style={[styles.card, isSmallScreen && styles.cardSmall]}
              onPress={() => openDetail(item)}
            >
              <View style={styles.cardHeader}>
                <View style={[styles.cardTitleContainer, isSmallScreen && styles.cardTitleContainerSmall]}>
                  <Text style={[styles.cardTitle, isSmallScreen && styles.cardTitleSmall]} numberOfLines={2}>
                    {nombreFormacionDisplay}
                  </Text>
                  <View style={[styles.badge, statusColor(status), isSmallScreen && styles.badgeSmall]}>
                    <Text style={[styles.badgeText, isSmallScreen && styles.badgeTextSmall]}>{status}</Text>
                  </View>
                </View>
              </View>

              <View style={[styles.cardContent, isSmallScreen && styles.cardContentSmall]}>
                <View style={[styles.detailRow, isSmallScreen && styles.detailRowSmall]}>
                  <View style={styles.detailItem}>
                    <Icon name="domain" size={isSmallScreen ? 12 : 14} color="#666" />
                    <Text style={[styles.detailText, isSmallScreen && styles.detailTextSmall]}>
                      Cohorte: {cohorteDisplay}
                    </Text>
                  </View>
                  <View style={styles.detailItem}>
                    <Icon name="calendar" size={isSmallScreen ? 12 : 14} color="#666" />
                    <Text style={[styles.detailText, isSmallScreen && styles.detailTextSmall]}>
                      Fecha de Inscripción: {fechaDisplay}
                    </Text>
                  </View>
                </View>

                <View style={[styles.detailRow, isSmallScreen && styles.detailRowSmall]}>
                  <View style={[styles.detailItem, { flex: 1 }]}>
                    <Icon name="cash" size={isSmallScreen ? 12 : 14} color="#666" />
                    <Text style={[styles.detailText, isSmallScreen && styles.detailTextSmall]}>
                      Valor de Inscripción: {fmtMoney(valorDisplay)}
                    </Text>
                  </View>
                </View>
              </View>

              <View style={[styles.cardFooter, isSmallScreen && styles.cardFooterSmall]}>
                <Text style={[styles.cardButtonText, isSmallScreen && styles.cardButtonTextSmall]}>Tocar para ver detalles</Text>
                <Icon name="chevron-right" size={isSmallScreen ? 16 : 18} color="#4f8cff" />
              </View>
            </TouchableOpacity>
          );
        }}
        contentContainerStyle={[styles.listContent, isSmallScreen && styles.listContentSmall]}
        ListEmptyComponent={
          <View style={styles.emptyState}>
            <Icon name="clipboard-text-outline" size={isSmallScreen ? 40 : 50} color="#ccc" />
            <Text style={[styles.emptyText, isSmallScreen && styles.emptyTextSmall]}>
              {loading ? 'Cargando...' : 'No tienes inscripciones registradas'}
            </Text>
            <TouchableOpacity
              style={[styles.addButton, isSmallScreen && styles.addButtonSmall, styles.emptyButton]}
              onPress={() => setFormModalVisible(true)}
            >
              <Icon name="plus" size={isSmallScreen ? 16 : 18} color="#fff" />
              <Text style={[styles.addButtonText, isSmallScreen && styles.addButtonTextSmall]}>Crear primera inscripción</Text>
            </TouchableOpacity>
          </View>
        }
      />

      {/* DETAIL MODAL */}
      <Modal
        isVisible={detailModalVisible}
        onBackdropPress={() => setDetailModalVisible(false)}
        style={[styles.modal, isSmallScreen && styles.modalSmall]}
        avoidKeyboard
      >
        <View style={[
          styles.modalContent,
          isSmallScreen && styles.modalContentSmall,
          { maxHeight: Math.min(height * 0.85, 720), width: isLargeScreen ? '80%' : undefined }
        ]}>
          <View style={[styles.modalHeader, isSmallScreen && styles.modalHeaderSmall]}>
            <Text style={[styles.modalTitle, isSmallScreen && styles.modalTitleSmall]}>Detalles de Inscripción</Text>
            <TouchableOpacity style={[styles.closeButton, isSmallScreen && styles.closeButtonSmall]} onPress={() => setDetailModalVisible(false)}>
              <Icon name="close" size={isSmallScreen ? 20 : 22} color="#666" />
            </TouchableOpacity>
          </View>

          <ScrollView style={styles.modalBody} contentContainerStyle={{ paddingBottom: 12 }}>
            {selected ? (
              <View style={[styles.detailGrid, isSmallScreen && styles.detailGridSmall]}>
                <View style={[styles.detailCell, isSmallScreen ? styles.detailCellFull : styles.detailCellHalf]}>
                  <Text style={[styles.detailLabel, isSmallScreen && styles.detailLabelSmall]}>Formación</Text>
                  <Text style={[styles.detailValue, isSmallScreen && styles.detailValueSmall]}>
                    {selected.idFormacion_detail?.nombreFormacion ?? selected.idFormacion_detail?.nombre ?? '—'}
                  </Text>
                </View>

                <View style={[styles.detailCell, isSmallScreen ? styles.detailCellFull : styles.detailCellHalf]}>
                  <Text style={[styles.detailLabel, isSmallScreen && styles.detailLabelSmall]}>Cohorte</Text>
                  <Text style={[styles.detailValue, isSmallScreen && styles.detailValueSmall]}>
                    {selected.idCohorte_detail?.nombreCohorte ?? '—'}
                  </Text>
                </View>

                <View style={[styles.detailCell, isSmallScreen ? styles.detailCellFull : styles.detailCellHalf]}>
                  <Text style={[styles.detailLabel, isSmallScreen && styles.detailLabelSmall]}>Valor inscripción</Text>
                  <Text style={[styles.detailValue, isSmallScreen && styles.detailValueSmall]}>
                    {fmtMoney(selected.idFormacion_detail?.valorInscripcion ?? selected.montoTotal ?? 0)}
                  </Text>
                </View>

                <View style={[styles.detailCell, isSmallScreen ? styles.detailCellFull : styles.detailCellHalf]}>
                  <Text style={[styles.detailLabel, isSmallScreen && styles.detailLabelSmall]}>Estado pago</Text>
                  <Text style={[styles.detailValue, isSmallScreen && styles.detailValueSmall]}>
                    {deriveStatus(selected)}
                  </Text>
                </View>

                <View style={[styles.detailCell, isSmallScreen ? styles.detailCellFull : styles.detailCellHalf]}>
                  <Text style={[styles.detailLabel, isSmallScreen && styles.detailLabelSmall]}>Monto total</Text>
                  <Text style={[styles.detailValue, isSmallScreen && styles.detailValueSmall]}>
                    {fmtMoney(selected.montoTotal)}
                  </Text>
                </View>

                <View style={[styles.detailCell, isSmallScreen ? styles.detailCellFull : styles.detailCellHalf]}>
                  <Text style={[styles.detailLabel, isSmallScreen && styles.detailLabelSmall]}>Fecha inscripción</Text>
                  <Text style={[styles.detailValue, isSmallScreen && styles.detailValueSmall]}>
                    {selected.fechaInscripcion ? new Date(selected.fechaInscripcion).toLocaleDateString() : '—'}
                  </Text>
                </View>

                {(() => {
                  const f = selected.idFormacion_detail ?? null;
                  const cuotasDetalle = cuotasFromFormacionObj(f);
                  if (!cuotasDetalle || cuotasDetalle.length === 0) return null;
                  return (
                    <View style={[styles.detailCell, { width: '100%' }]}>
                      <Text style={[styles.detailLabel, isSmallScreen && styles.detailLabelSmall]}>Cuotas</Text>
                      {cuotasDetalle.map((c: Cuota, idx: number) => (
                        <View key={idx} style={{ flexDirection: 'row', justifyContent: 'space-between', paddingVertical: 6 }}>
                          <Text style={[styles.detailValueSmall, { color: '#4a5568', fontWeight: '600' }]}>{c.nombreCuota}</Text>
                          <Text style={[styles.detailValueSmall, { color: '#1a365d', fontWeight: '700' }]}>{fmtMoney(c.valorCuota)}</Text>
                        </View>
                      ))}
                    </View>
                  );
                })()}
              </View>
            ) : null}
          </ScrollView>

          <View style={[styles.modalFooter, isSmallScreen && styles.modalFooterSmall]}>
            <TouchableOpacity style={[styles.modalButton, isSmallScreen && styles.modalButtonSmall]} onPress={() => setDetailModalVisible(false)}>
              <Text style={[styles.modalButtonText, isSmallScreen && styles.modalButtonTextSmall]}>Cerrar</Text>
            </TouchableOpacity>
          </View>
        </View>
      </Modal>

      {/* FORM MODAL */}
      <Modal
        isVisible={formModalVisible}
        onBackdropPress={() => !creating && setFormModalVisible(false)}
        style={[styles.modal, styles.formModal, isSmallScreen && styles.modalSmall]}
        avoidKeyboard
      >
        <KeyboardAvoidingView
          behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
          keyboardVerticalOffset={Platform.OS === 'ios' ? 80 : 0}
          style={[styles.keyboardAvoid, { minHeight: Math.min(height * 0.9, 900) }]}
        >
          <View style={[styles.formModalContent, isSmallScreen ? styles.formModalContentSmall : {}, { maxHeight: Math.min(height * 0.95, 1000), width: isLargeScreen ? Math.min(720, width * 0.8) : undefined }]}>
            <View style={[styles.modalHeader, isSmallScreen && styles.modalHeaderSmall]}>
              <Text style={[styles.modalTitle, isSmallScreen && styles.modalTitleSmall]}>Nueva Inscripción</Text>
              <TouchableOpacity style={[styles.closeButton, isSmallScreen && styles.closeButtonSmall]} onPress={() => !creating && setFormModalVisible(false)} disabled={creating}>
                <Icon name="close" size={isSmallScreen ? 20 : 22} color="#666" />
              </TouchableOpacity>
            </View>

            { formDataLoading ? (
              <View style={{ padding: 20, alignItems: 'center' }}>
                <ActivityIndicator size="large" color="#4f8cff" />
                <Text style={{ marginTop: 8, color: '#666' }}>Cargando formaciones y cohortes...</Text>
              </View>
            ) : (
              <ScrollView style={styles.formBody} showsVerticalScrollIndicator keyboardShouldPersistTaps="handled" contentContainerStyle={[styles.formContent, isSmallScreen && styles.formContentSmall, { paddingBottom: 24 }]}>
                {/* Información Personal */}
                <View style={styles.formSection}>
                  <View style={styles.sectionHeader}>
                    <Icon name="account" size={isSmallScreen ? 18 : 20} color="#4f8cff" />
                    <Text style={[styles.sectionTitle, isSmallScreen && styles.sectionTitleSmall]}>Información Personal</Text>
                  </View>

                  <View style={[styles.fieldContainer, isSmallScreen && styles.fieldContainerSmall]}>
                    <Text style={[styles.label, isSmallScreen && styles.labelSmall]}>Cédula</Text>
                    <View style={[styles.cedulaFijaContainer, isSmallScreen && styles.cedulaFijaContainerSmall]}>
                      <Text style={[styles.cedulaFijaText, isSmallScreen && styles.cedulaFijaTextSmall]}>{user?.cedula || 'No disponible'}</Text>
                    </View>
                    <Text style={[styles.helpText, isSmallScreen && styles.helpTextSmall]}>{user?.nombres && user?.apellidos ? `${user.nombres} ${user.apellidos}` : 'Usuario actual'}</Text>
                  </View>
                </View>

                {/* Información Académica */}
                <View style={styles.formSection}>
                  <View style={styles.sectionHeader}>
                    <Icon name="school" size={isSmallScreen ? 18 : 20} color="#4f8cff" />
                    <Text style={[styles.sectionTitle, isSmallScreen && styles.sectionTitleSmall]}>Información Académica</Text>
                  </View>

                  {/* Tipo de Formación (custom select) */}
                  <View style={[styles.fieldContainer, isSmallScreen && styles.fieldContainerSmall]}>
                    <Text style={[styles.label, isSmallScreen && styles.labelSmall]}>Tipo de Formación *</Text>

                    <TouchableOpacity
                      style={[styles.customSelectButton, isSmallScreen && styles.customSelectButtonSmall]}
                      onPress={() => setShowTipoModal(true)}
                      disabled={formDataLoading}
                    >
                      <Text style={[styles.customSelectText, isSmallScreen && styles.customSelectTextSmall]}>
                        {selectedTipoFormacion
                          ? (tiposFormacion.find(t => Number(t.idTF) === Number(selectedTipoFormacion))?.nombreTipoFormacion ?? `Tipo ${selectedTipoFormacion}`)
                          : 'Seleccione tipo...'}
                      </Text>
                      <Text style={[styles.customSelectArrow, isSmallScreen && styles.customSelectArrowSmall]}>▾</Text>
                    </TouchableOpacity>

                    {formErrors.tipoFormacion && <Text style={[styles.errorText, isSmallScreen && styles.errorTextSmall]}>{formErrors.tipoFormacion}</Text>}
                  </View>

                  {/* Formación (custom select) */}
                  <View style={[styles.fieldContainer, isSmallScreen && styles.fieldContainerSmall]}>
                    <Text style={[styles.label, isSmallScreen && styles.labelSmall]}>Formación *</Text>

                    <TouchableOpacity
                      style={[styles.customSelectButton, isSmallScreen && styles.customSelectButtonSmall, (formacionesFiltradas.length === 0) && { opacity: 0.7 }]}
                      onPress={() => {
                        if (formacionesFiltradas.length > 0) setShowFormacionModal(true);
                      }}
                      disabled={formacionesFiltradas.length === 0 || formDataLoading}
                    >
                      <Text numberOfLines={1} style={[styles.customSelectText, isSmallScreen && styles.customSelectTextSmall]}>
                        {selectedFormacion
                          ? (formacionesFiltradas.find(f => Number(f.idFormacion) === Number(selectedFormacion))?.nombreFormacion ?? `Formación ${selectedFormacion}`)
                          : (formacionesFiltradas.length === 0 ? 'No hay formaciones disponibles' : 'Seleccione formación...')}
                      </Text>
                      <Text style={[styles.customSelectArrow, isSmallScreen && styles.customSelectArrowSmall]}>▾</Text>
                    </TouchableOpacity>

                    {formErrors.formacion && <Text style={[styles.errorText, isSmallScreen && styles.errorTextSmall]}>{formErrors.formacion}</Text>}
                    {formErrors.cohorte && <Text style={[styles.errorText, isSmallScreen && styles.errorTextSmall]}>{formErrors.cohorte}</Text>}
                    <Text style={[styles.helpText, isSmallScreen && styles.helpTextSmall]}>
                      Nota: solo se muestran formaciones con cohorte de inscripción abierta. Al seleccionar una formación la cohorte se asigna automáticamente.
                    </Text>
                  </View>
                </View>

                {/* Resumen de costos */}
                <View style={styles.formSection}>
                  <View style={styles.sectionHeader}>
                    <Icon name="cash" size={isSmallScreen ? 18 : 20} color="#4f8cff" />
                    <Text style={[styles.sectionTitle, isSmallScreen && styles.sectionTitleSmall]}>Resumen de Costos</Text>
                  </View>

                  <View style={[styles.costosContainer, isSmallScreen && styles.costosContainerSmall]}>
                    <View style={[styles.costoItem, isSmallScreen && styles.costoItemSmall]}>
                      <Text style={[styles.costoLabel, isSmallScreen && styles.costoLabelSmall]}>Inscripción:</Text>
                      <Text style={[styles.costoValue, isSmallScreen && styles.costoValueSmall]}>{fmtMoney(valorInscripcion)}</Text>
                    </View>

                    {cuotas.length > 0 ? (
                      <>
                        {cuotas.map((cuota, index) => (
                          <View key={index} style={[styles.costoItem, isSmallScreen && styles.costoItemSmall]}>
                            <Text style={[styles.costoLabel, isSmallScreen && styles.costoLabelSmall]}>{cuota.nombreCuota}:</Text>
                            <Text style={[styles.costoValue, isSmallScreen && styles.costoValueSmall]}>{fmtMoney(cuota.valorCuota)}</Text>
                          </View>
                        ))}
                        <View style={[styles.costoItem, styles.costoTotal, isSmallScreen && styles.costoItemSmall]}>
                          <Text style={[styles.costoLabel, isSmallScreen && styles.costoLabelSmall]}>Total Cuotas:</Text>
                          <Text style={[styles.costoValue, isSmallScreen && styles.costoValueSmall]}>{fmtMoney(totalCuotas)}</Text>
                        </View>
                      </>
                    ) : (
                      <View style={[styles.costoItem, isSmallScreen && styles.costoItemSmall]}>
                        <Text style={[styles.costoLabel, styles.noCuotas, isSmallScreen && styles.costoLabelSmall]}>No hay cuotas configuradas</Text>
                      </View>
                    )}

                    <View style={[styles.costoItem, styles.costoGrandTotal, isSmallScreen && styles.costoItemSmall]}>
                      <Text style={[styles.costoLabel, styles.costoGrandTotalLabel, isSmallScreen && styles.costoLabelSmall]}>TOTAL A PAGAR:</Text>
                      <Text style={[styles.costoValue, styles.costoGrandTotalValue, isSmallScreen && styles.costoValueSmall]}>{fmtMoney(montoTotal)}</Text>
                    </View>
                  </View>
                </View>

                {/* Fecha (automática) */}
                <View style={styles.formSection}>
                  <View style={styles.sectionHeader}>
                    <Icon name="calendar-clock" size={isSmallScreen ? 18 : 20} color="#4f8cff" />
                    <Text style={[styles.sectionTitle, isSmallScreen && styles.sectionTitleSmall]}>Información de Registro</Text>
                  </View>

                  <View style={[styles.fieldContainer, isSmallScreen && styles.fieldContainerSmall]}>
                    <View style={[styles.fechaContainer, isSmallScreen && styles.fechaContainerSmall]}>
                      <Text style={[styles.fechaText, isSmallScreen && styles.fechaTextSmall]}>{fechaInscripcion}</Text>
                    </View>
                    <Text style={[styles.helpText, isSmallScreen && styles.helpTextSmall]}>Fecha (automática)</Text>
                  </View>
                </View>
              </ScrollView>
            )}

            <View style={[styles.formFooter, isSmallScreen && styles.formFooterSmall]}>
              <TouchableOpacity style={[styles.formButton, styles.cancelButton, isSmallScreen && styles.formButtonSmall]} onPress={() => setFormModalVisible(false)} disabled={creating}>
                <Text style={[styles.cancelButtonText, isSmallScreen && styles.cancelButtonTextSmall]}>Cancelar</Text>
              </TouchableOpacity>

              <TouchableOpacity style={[styles.formButton, styles.submitButton, isSmallScreen && styles.formButtonSmall]} onPress={handleCreateInscripcion} disabled={creating}>
                {creating ? <ActivityIndicator color="#fff" size="small" /> : <>
                  <Icon name="check" size={isSmallScreen ? 16 : 18} color="#fff" />
                  <Text style={[styles.submitButtonText, isSmallScreen && styles.submitButtonTextSmall]}>Crear Inscripción</Text>
                </>}
              </TouchableOpacity>
            </View>
          </View>
        </KeyboardAvoidingView>
      </Modal>

      {/* Modal Tipo de Formación */}
      <Modal
        isVisible={showTipoModal}
        onBackdropPress={() => setShowTipoModal(false)}
        backdropOpacity={0.4}
      >
        <View style={styles.modalOverlay}>
          <View style={[styles.modalContent, isSmallScreen && styles.modalContentSmall]}>
            <Text style={[styles.modalTitle, isSmallScreen && styles.modalTitleSmall]}>Seleccionar Tipo de Formación</Text>
            <ScrollView style={styles.modalScrollView}>
              {tiposFormacion.map(tf => (
                <TouchableOpacity
                  key={tf.idTF}
                  style={[
                    styles.modalOption,
                    selectedTipoFormacion === Number(tf.idTF) && styles.modalOptionSelected
                  ]}
                  onPress={() => handleTipoSelect(Number(tf.idTF))}
                >
                  <Text style={[styles.modalOptionText, selectedTipoFormacion === Number(tf.idTF) && styles.modalOptionTextSelected]}>
                    {tf.nombreTipoFormacion}
                  </Text>
                </TouchableOpacity>
              ))}
            </ScrollView>
            <TouchableOpacity style={[styles.modalCloseButton, isSmallScreen && styles.modalCloseButtonSmall]} onPress={() => setShowTipoModal(false)}>
              <Text style={[styles.modalCloseText, isSmallScreen && styles.modalCloseTextSmall]}>Cancelar</Text>
            </TouchableOpacity>
          </View>
        </View>
      </Modal>

      {/* Modal Formaciones (filtradas) */}
      <Modal
        isVisible={showFormacionModal}
        onBackdropPress={() => setShowFormacionModal(false)}
        backdropOpacity={0.4}
      >
        <View style={styles.modalOverlay}>
          <View style={[styles.modalContent, isSmallScreen && styles.modalContentSmall, { maxHeight: '80%' }]}>
            <Text style={[styles.modalTitle, isSmallScreen && styles.modalTitleSmall]}>Seleccionar Formación</Text>

            <View style={{ paddingHorizontal: 8, paddingBottom: 8 }}>
              <TextInput
                placeholder="Buscar formación..."
                value={searchFormacionModal}
                onChangeText={setSearchFormacionModal}
                style={{ borderWidth: 1, borderColor: '#eef2ff', borderRadius: 8, paddingHorizontal: 10, height: 40 }}
                placeholderTextColor="#999"
              />
            </View>

            <ScrollView style={styles.modalScrollView}>
              {formacionesFiltradasParaModal.length === 0 ? (
                <View style={{ padding: 16 }}>
                  <Text style={{ color: '#666' }}>No se encontraron formaciones</Text>
                </View>
              ) : (
                formacionesFiltradasParaModal.map((f: any) => (
                  <TouchableOpacity
                    key={f.idFormacion}
                    style={[
                      styles.modalOption,
                      selectedFormacion === Number(f.idFormacion) && styles.modalOptionSelected
                    ]}
                    onPress={() => handleFormacionSelect(Number(f.idFormacion))}
                  >
                    <Text style={[styles.modalOptionText, selectedFormacion === Number(f.idFormacion) && styles.modalOptionTextSelected]}>
                      {`${f.nombreFormacion} — ${fmtMoney(f.valorInscripcion)}`}
                    </Text>
                    <Text style={styles.modalOptionSub}>{f.tieneCuotas ? `${f.cantidad_cuotas} cuotas` : 'Sin cuotas'}</Text>
                  </TouchableOpacity>
                ))
              )}
            </ScrollView>

            <TouchableOpacity style={[styles.modalCloseButton, isSmallScreen && styles.modalCloseButtonSmall]} onPress={() => setShowFormacionModal(false)}>
              <Text style={[styles.modalCloseText, isSmallScreen && styles.modalCloseTextSmall]}>Cancelar</Text>
            </TouchableOpacity>
          </View>
        </View>
      </Modal>
    </View>
  );
};

// ESTILOS (los tuyos + estilos nuevos para selects y modales)
const styles = StyleSheet.create({
  center: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: '#f5f7fa',
    padding: 20,
  },
  container: {
    flex: 1,
    backgroundColor: '#f5f7fa',
  },

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
  addButton: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#4f8cff',
    paddingHorizontal: 12,
    paddingVertical: 8,
    borderRadius: 8,
    gap: 6,
    marginLeft: 8,
  },
  addButtonSmall: {
    paddingHorizontal: 10,
    paddingVertical: 6,
    gap: 4,
    borderRadius: 6,
  },
  addButtonText: {
    color: '#fff',
    fontWeight: '600',
    fontSize: 14,
  },
  addButtonTextSmall: {
    fontSize: 12,
  },

  // Search
  searchContainer: {
    padding: 12,
    backgroundColor: '#fff',
    borderBottomWidth: 1,
    borderBottomColor: '#e1e5e9',
  },
  searchContainerSmall: {
    padding: 10,
  },
  searchWrapper: {
    flexDirection: 'row',
    backgroundColor: '#f8f9fa',
    borderRadius: 10,
    alignItems: 'center',
    paddingHorizontal: 12,
    height: 40,
    borderWidth: 1,
    borderColor: '#e1e5e9',
  },
  searchWrapperSmall: {
    paddingHorizontal: 10,
    height: 38,
    borderRadius: 8,
  },
  searchInput: {
    flex: 1,
    fontSize: 14,
    marginLeft: 8,
    color: '#333',
    paddingVertical: 0,
  },
  searchInputSmall: {
    fontSize: 13,
    marginLeft: 6,
  },

  // Counter
  counterContainer: {
    paddingHorizontal: 16,
    paddingVertical: 8,
    backgroundColor: '#f8f9fa',
  },
  counterContainerSmall: {
    paddingHorizontal: 12,
    paddingVertical: 6,
  },
  counterText: {
    fontSize: 12,
    color: '#666',
    fontWeight: '500',
  },
  counterTextSmall: {
    fontSize: 11,
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
  cardTitleContainer: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    marginBottom: 6,
  },
  cardTitleContainerSmall: {
    marginBottom: 4,
    flexDirection: 'column',
    gap: 6,
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
  cardContent: {
    marginBottom: 10,
  },
  cardContentSmall: {
    marginBottom: 8,
  },
  cardFooter: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingTop: 10,
    borderTopWidth: 1,
    borderTopColor: '#f1f3f4',
  },
  cardFooterSmall: {
    paddingTop: 8,
  },
  detailRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginBottom: 8,
  },
  detailRowSmall: {
    marginBottom: 6,
    flexDirection: 'column',
    gap: 6,
  },
  detailItem: {
    flexDirection: 'row',
    alignItems: 'center',
    flex: 1,
  },
  detailText: {
    marginLeft: 6,
    fontSize: 13,
    color: '#555',
    fontWeight: '500',
  },
  detailTextSmall: {
    fontSize: 12,
    marginLeft: 4,
  },
  cardButtonText: {
    color: '#4f8cff',
    fontWeight: '500',
    fontSize: 12,
  },
  cardButtonTextSmall: {
    fontSize: 11,
  },

  // Badge
  badge: {
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 12,
    minWidth: 60,
    alignItems: 'center',
  },
  badgeSmall: {
    paddingHorizontal: 6,
    paddingVertical: 3,
    minWidth: 50,
    borderRadius: 10,
  },
  badgeActive: {
    backgroundColor: '#2dce89',
  },
  badgePartial: {
    backgroundColor: '#f1a43a',
  },
  badgeInactive: {
    backgroundColor: '#f5365c',
  },
  badgeText: {
    color: '#fff',
    fontSize: 10,
    fontWeight: '700',
    textAlign: 'center',
  },
  badgeTextSmall: {
    fontSize: 9,
  },

  // Empty
  emptyState: {
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: 40,
    paddingHorizontal: 20,
  },
  emptyText: {
    marginTop: 12,
    textAlign: 'center',
    color: '#999',
    fontStyle: 'italic',
    fontSize: 14,
    marginBottom: 16,
  },
  emptyTextSmall: {
    fontSize: 13,
    marginTop: 10,
  },
  emptyButton: {
    alignSelf: 'center',
  },

  // Error
  errorText: {
    color: '#e53e3e',
    fontSize: 14,
    marginTop: 4,
    fontWeight: '500',
  },
  errorTextSmall: {
    fontSize: 12,
  },

  // Modal
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
  modalContent: {
    backgroundColor: '#fff',
    borderRadius: 16,
    width: '90%',
    maxWidth: 500,
    maxHeight: '80%',
    overflow: 'hidden',
  },
  modalContentSmall: {
    width: '95%',
    maxHeight: '85%',
    borderRadius: 14,
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
  modalBody: {
    flex: 1,
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
  modalFooter: {
    padding: 16,
    paddingTop: 12,
    borderTopWidth: 1,
    borderTopColor: '#e1e5e9',
  },
  modalFooterSmall: {
    padding: 14,
    paddingTop: 10,
  },

  // DETAIL GRID (nuevo)
  detailGrid: {
    paddingHorizontal: 12,
    paddingVertical: 8,
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 12,
  },
  detailGridSmall: {
    paddingHorizontal: 10,
  },
  detailCell: {
    padding: 12,
    borderRadius: 10,
    backgroundColor: '#fff',
    borderWidth: 1,
    borderColor: '#f1f3f4',
    marginBottom: 10,
  },
  detailCellHalf: {
    width: '48%',
  },
  detailCellFull: {
    width: '100%',
  },
  detailLabel: {
    fontWeight: '700',
    fontSize: 13,
    color: '#4a5568',
    marginBottom: 6,
  },
  detailLabelSmall: {
    fontSize: 12,
  },
  detailValue: {
    fontSize: 15,
    color: '#1a365d',
    fontWeight: '600',
  },
  detailValueSmall: {
    fontSize: 14,
  },

  detailRowModal: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    paddingVertical: 10,
    paddingHorizontal: 16,
    borderBottomWidth: 1,
    borderBottomColor: '#f8f9fa',
  },
  detailRowModalSmall: {
    paddingVertical: 8,
    paddingHorizontal: 14,
    flexDirection: 'column',
    gap: 2,
  },
  detailLabelUnused: {
    fontWeight: '600',
    fontSize: 14,
    color: '#4a5568',
    flex: 1,
  },
  detailLabelSmallUnused: {
    fontSize: 13,
  },
  detailValueUnused: {
    flex: 1,
    fontSize: 14,
    color: '#2d3748',
    textAlign: 'right',
    fontWeight: '500',
  },
  detailValueSmallUnused: {
    fontSize: 13,
    textAlign: 'left',
  },
  modalButton: {
    backgroundColor: '#4f8cff',
    paddingVertical: 12,
    borderRadius: 10,
    alignItems: 'center',
  },
  modalButtonSmall: {
    paddingVertical: 10,
    borderRadius: 8,
  },
  modalButtonText: {
    color: '#fff',
    fontWeight: '600',
    fontSize: 14,
  },
  modalButtonTextSmall: {
    fontSize: 13,
  },

  // Form
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
  helpText: {
    fontSize: 11,
    color: '#6c757d',
    marginTop: 4,
    fontStyle: 'italic',
  },
  helpTextSmall: {
    fontSize: 10,
  },
  pickerContainer: {
    borderWidth: 1,
    borderColor: '#e1e5e9',
    borderRadius: 10,
    backgroundColor: '#fff',
    overflow: 'hidden',
  },
  pickerContainerSmall: {
    borderRadius: 8,
  },
  picker: {
    height: 46,
    width: '100%',
  },
  pickerSmall: {
    height: 42,
  },

  // Costos
  costosContainer: {
    backgroundColor: '#f8f9fa',
    borderRadius: 10,
    padding: 12,
    marginHorizontal: 16,
    borderWidth: 1,
    borderColor: '#e1e5e9',
  },
  costosContainerSmall: {
    padding: 10,
    marginHorizontal: 14,
    borderRadius: 8,
  },
  costoItem: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: 6,
    borderBottomWidth: 1,
    borderBottomColor: '#e9ecef',
  },
  costoItemSmall: {
    paddingVertical: 5,
  },
  costoTotal: {
    borderBottomWidth: 2,
    borderBottomColor: '#dee2e6',
    paddingTop: 8,
    marginTop: 4,
  },
  costoGrandTotal: {
    backgroundColor: '#d4edda',
    borderRadius: 6,
    paddingHorizontal: 8,
    paddingVertical: 8,
    marginTop: 8,
    borderBottomWidth: 0,
  },
  costoLabel: {
    fontSize: 14,
    color: '#4a5568',
    fontWeight: '500',
  },
  costoLabelSmall: {
    fontSize: 13,
  },
  costoGrandTotalLabel: {
    fontWeight: '700',
    color: '#155724',
  },
  costoValue: {
    fontSize: 14,
    color: '#4a5568',
    fontWeight: '600',
  },
  costoValueSmall: {
    fontSize: 13,
  },
  costoGrandTotalValue: {
    fontWeight: '700',
    color: '#155724',
    fontSize: 16,
  },
  noCuotas: {
    color: '#999',
    fontStyle: 'italic',
    textAlign: 'center',
    flex: 1,
  },

  // Form footer
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

  // ---- estilos añadidos: selects personalizados y modales ----
  customSelectButton: {
    borderWidth: 1,
    borderColor: '#eef2ff',
    borderRadius: 8,
    paddingHorizontal: 12,
    height: 46,
    backgroundColor: '#fff',
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  customSelectButtonSmall: { height: 42, paddingHorizontal: 10 },
  customSelectText: { fontSize: 15, color: '#222', flex: 1 },
  customSelectTextSmall: { fontSize: 14 },
  customSelectPlaceholder: { color: '#9aa' },
  customSelectArrow: { fontSize: 12, color: '#4f8cff', marginLeft: 8 },
  customSelectArrowSmall: { fontSize: 10 },

  modalOverlay: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: 20,
  },
  modalScrollView: { maxHeight: 350 },

  modalOption: {
    paddingVertical: 12,
    paddingHorizontal: 8,
    borderBottomWidth: 1,
    borderBottomColor: '#f0f0f0',
  },
  modalOptionSmall: { paddingVertical: 10, paddingHorizontal: 12 },
  modalOptionSelected: { backgroundColor: '#eef2ff' },
  modalOptionText: { fontSize: 15, color: '#222' },
  modalOptionTextSelected: { color: '#1f6fff', fontWeight: '600' },
  modalOptionSub: { fontSize: 12, color: '#666', marginTop: 4 },

  modalCloseButton: {
    marginTop: 12,
    paddingVertical: 10,
    borderRadius: 8,
    backgroundColor: '#6c757d',
    alignItems: 'center',
  },
  modalCloseButtonSmall: { paddingVertical: 10 },
  modalCloseText: { color: '#fff', fontSize: 15, fontWeight: '600' },
  modalCloseTextSmall: { fontSize: 14 },
});

export default InscripcionesScreen;
