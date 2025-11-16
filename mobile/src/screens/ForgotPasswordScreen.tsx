// src/screens/ForgotPasswordScreen.tsx
import React, { useCallback, useEffect, useRef, useState } from 'react';
import {
  View,
  Text,
  TextInput,
  StyleSheet,
  TouchableOpacity,
  ActivityIndicator,
  Alert,
  KeyboardAvoidingView,
  Platform,
  ScrollView,
  Dimensions,
} from 'react-native';
import Icon from 'react-native-vector-icons/MaterialCommunityIcons';
import type { StackNavigationProp } from '@react-navigation/stack';
import { useNavigation } from '@react-navigation/native';
import api from '../api/api';

type RootStackParamList = {
  Login: undefined;
  // ... otros screens
};

type NavigationProp = StackNavigationProp<RootStackParamList, 'Login'>;

const { width: screenWidth } = Dimensions.get('window');
const isSmallScreen = screenWidth < 375;

const normalizeCedulaDigits = (v?: string) => String(v ?? '').replace(/[\.\-\s]/g, '').toUpperCase();

/**
 * Pantalla "Olvidó su contraseña"
 *
 * Nota sobre endpoints:
 * - GET  /api/usuarios/por_cedula/?cedula=XXX  -> devuelve { exists: true, preguntaSeguridad: '¿...?', username, idUsuario, ... }
 *   (si tu endpoint es distinto, cámbialo en fetchUserByCedula)
 *
 * - POST /api/usuarios/validar_respuesta/  { cedula, respuesta } -> { success: true/false, message?: '' }
 *   (si prefieres validar localmente con datos devueltos en GET, adapta validateSecurityAnswer)
 *
 * - POST /api/usuarios/reset_password/ { cedula, password } -> { success: true, ... }
 *   (ajusta ruta si tu backend usa otra)
 */

export default function ForgotPasswordScreen() {
  const navigation = useNavigation<NavigationProp>();

  // pasos: 1 = verificar cédula, 2 = responder pregunta, 3 = nueva contraseña
  const [step, setStep] = useState<number>(1);

  // inputs
  const [cedula, setCedula] = useState<string>('');
  const [preguntaSeguridad, setPreguntaSeguridad] = useState<string>('');
  const [respuesta, setRespuesta] = useState<string>('');
  const [newPassword, setNewPassword] = useState<string>('');
  const [confirmPassword, setConfirmPassword] = useState<string>('');

  // UX
  const [loading, setLoading] = useState<boolean>(false);
  const [verifying, setVerifying] = useState<boolean>(false);
  const [showPassword, setShowPassword] = useState<boolean>(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState<boolean>(false);

  // información devuelta por backend (puede contener username/id para usar en reset)
  const [backendPayload, setBackendPayload] = useState<any>(null);

  // refs para avanzar con Next
  const respuestaRef = useRef<TextInput | null>(null);
  const passwordRef = useRef<TextInput | null>(null);

  // Validadores simples
  const validCedulaLocal = (c: string) => {
    const d = normalizeCedulaDigits(c).replace(/[^0-9A-Z]/g, '');
    // si comienza con V/E/J/P permitimos alfanumérico; si solo numérico permitimos 6-8
    const onlyDigits = d.replace(/\D/g, '');
    if (/^[0-9]{6,8}$/.test(onlyDigits)) return true;
    // fallback: exigir al menos 4 caracteres alfanuméricos
    return d.length >= 4;
  };

  const validRespuesta = (r: string) => {
    return (r || '').trim().length >= 1;
  };

  const validPassword = (p: string) => {
    // regla sencilla: minimo 8, contenar letra+numero (puedes personalizar)
    if (!p || p.length < 8) return false;
    const hasNumber = /[0-9]/.test(p);
    const hasLetter = /[A-Za-zÁÉÍÓÚáéíóúÑñ]/.test(p);
    return hasNumber && hasLetter;
  };

  // ---------- API calls (ajusta las rutas si tu backend difiere) ----------

  const fetchUserByCedula = useCallback(async (ced: string) => {
    // Normalizar
    const cedNorm = normalizeCedulaDigits(ced);
    setLoading(true);
    try {
      // AJUSTA AQUÍ LA RUTA si tu backend expone otro endpoint
      // Ejemplo: /api/usuarios/por_cedula/?cedula=...
      const resp = await api.get(`/api/usuarios/por_cedula/?cedula=${encodeURIComponent(cedNorm)}`);
      // Esperamos un objeto con datos. Acomoda según tu respuesta real.
      const data = resp.data;
      if (!data) {
        Alert.alert('No hay respuesta', 'El servidor no devolvió información.');
        return null;
      }
      // Caso esperado:
      // { exists: true, preguntaSeguridad: '¿...?', username: 'juan', id: 12 }
      if (data.exists === false) {
        return { exists: false, message: data.message || 'Usuario no encontrado' };
      }
      // fallback: si viene preguntaSeguridad en otra propiedad, intenta leerla
      const pregunta = data.preguntaSeguridad ?? data.pregunta ?? data.security_question ?? '';
      return { exists: true, pregunta, raw: data };
    } catch (err: any) {
      console.error('fetchUserByCedula error', err?.response ?? err);
      // Intentar interpretar distintos formatos
      const errMsg = err?.response?.data?.detail ?? err?.response?.data?.message ?? err?.message ?? 'Error conectando al servidor';
      return { error: true, message: String(errMsg) };
    } finally {
      setLoading(false);
    }
  }, []);

  const validateSecurityAnswer = useCallback(async (ced: string, ans: string) => {
    setVerifying(true);
    try {
      // AJUSTA LA RUTA según backend
      // POST { cedula, respuesta } -> { success: true/false, message?, token? }
      const payload = { cedula: normalizeCedulaDigits(ced), respuesta: (ans || '').trim() };
      const resp = await api.post('/api/usuarios/validar_respuesta/', payload);
      const data = resp.data;
      // Data esperado: { success: true, ... }
      if (data && (data.success === true || data.valid === true)) {
        return { ok: true, data };
      }
      // si backend devuelve boolean false:
      return { ok: false, message: data?.message ?? 'Respuesta incorrecta' };
    } catch (err: any) {
      console.error('validateSecurityAnswer error', err?.response ?? err);
      const msg = err?.response?.data?.message ?? err?.response?.data?.detail ?? err?.message ?? 'Error validando respuesta';
      return { ok: false, message: String(msg) };
    } finally {
      setVerifying(false);
    }
  }, []);

  const resetPasswordRequest = useCallback(async (ced: string, password: string) => {
    setLoading(true);
    try {
      // AJUSTA LA RUTA según backend: POST { cedula, password } -> { success: true }
      const payload = { cedula: normalizeCedulaDigits(ced), password };
      const resp = await api.post('/api/usuarios/reset_password/', payload);
      const data = resp.data;
      if (data && (data.success === true || resp.status === 200 || resp.status === 204)) {
        return { ok: true, data };
      }
      return { ok: false, message: data?.message ?? 'No fue posible cambiar la contraseña' };
    } catch (err: any) {
      console.error('resetPasswordRequest error', err?.response ?? err);
      const msg = err?.response?.data?.message ?? err?.response?.data ?? err?.message ?? 'Error al resetear contraseña';
      return { ok: false, message: String(msg) };
    } finally {
      setLoading(false);
    }
  }, []);

  // ---------- Handlers UI ----------

  const handleVerifyCedula = async () => {
    if (!validCedulaLocal(cedula)) {
      Alert.alert('Cédula inválida', 'Ingrese una cédula válida antes de continuar.');
      return;
    }
    setLoading(true);
    const result = await fetchUserByCedula(cedula);
    setLoading(false);
    if (!result) {
      Alert.alert('Error', 'No se pudo obtener información del servidor.');
      return;
    }
    if (result.error) {
      Alert.alert('Error', result.message || 'Error desconocido');
      return;
    }
    if (result.exists === false) {
      Alert.alert('No encontrado', result.message || 'No existe usuario con esa cédula.');
      return;
    }
    // ok
    setPreguntaSeguridad(result.pregunta ?? '');
    setBackendPayload(result.raw ?? null);
    // pasar a paso 2
    setStep(2);
    // focus en respuesta
    setTimeout(() => respuestaRef.current?.focus(), 250);
  };

  const handleVerifyRespuesta = async () => {
    if (!validRespuesta(respuesta)) {
      Alert.alert('Respuesta requerida', 'Ingrese la respuesta de seguridad.');
      return;
    }

    setVerifying(true);
    const res = await validateSecurityAnswer(cedula, respuesta);
    setVerifying(false);

    if (!res.ok) {
      Alert.alert('Incorrecto', res.message || 'Respuesta incorrecta.');
      return;
    }

    // ok -> siguiente paso
    setStep(3);
    setTimeout(() => passwordRef.current?.focus(), 250);
  };

  const handleSaveNewPassword = async () => {
    if (!validPassword(newPassword)) {
      Alert.alert('Contraseña débil', 'La contraseña debe tener al menos 8 caracteres, incluir letras y números.');
      return;
    }
    if (newPassword !== confirmPassword) {
      Alert.alert('No coinciden', 'Las contraseñas no coinciden. Verifica ambos campos.');
      return;
    }

    setLoading(true);
    const res = await resetPasswordRequest(cedula, newPassword);
    setLoading(false);

    if (!res.ok) {
      Alert.alert('Error', res.message || 'No se pudo actualizar la contraseña.');
      return;
    }

    Alert.alert('Contraseña actualizada', 'Tu contraseña se ha actualizado correctamente. Inicia sesión con tu nueva contraseña.', [
      { text: 'Ir al inicio', onPress: () => navigation.navigate('Login') }
    ]);
  };

  const handleBack = () => {
    // si está en paso >1, vuelve a paso previo; si no, vuelve a login
    if (step === 1) navigation.navigate('Login');
    else setStep(prev => prev - 1);
  };

  // ---------- render ----------

  return (
    <KeyboardAvoidingView
      behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
      keyboardVerticalOffset={Platform.OS === 'ios' ? 60 : 80}
      style={styles.wrapper}
    >
      <ScrollView contentContainerStyle={styles.container} keyboardShouldPersistTaps="handled">
        <View style={[styles.card, isSmallScreen && styles.cardSmall]}>
          <Text style={[styles.title, isSmallScreen && styles.titleSmall]}>Olvidó su contraseña</Text>
          <Text style={[styles.subtitle, isSmallScreen && styles.subtitleSmall]}>
            Recupera el acceso mediante tu pregunta de seguridad.
          </Text>

          {/* STEP 1 - Cedula */}
          {step === 1 && (
            <>
              <Text style={styles.label}>Ingrese su cédula</Text>
              <TextInput
                placeholder="Ej: V-12345678 o 12345678"
                placeholderTextColor="#9aa"
                value={cedula}
                onChangeText={setCedula}
                style={[styles.input, isSmallScreen && styles.inputSmall]}
                editable={!loading && !verifying}
                autoCapitalize="characters"
                returnKeyType="done"
              />

              <View style={styles.buttonsRow}>
                <TouchableOpacity onPress={handleBack} style={[styles.btn, styles.btnOutline]}>
                  <Text style={styles.btnOutlineText}>Volver</Text>
                </TouchableOpacity>

                <TouchableOpacity
                  onPress={handleVerifyCedula}
                  style={[styles.btn, styles.btnPrimary, (loading || !validCedulaLocal(cedula)) && styles.btnDisabled]}
                  disabled={loading || !validCedulaLocal(cedula)}
                >
                  {loading ? <ActivityIndicator color="#fff" /> : <Text style={styles.btnText}>Verificar</Text>}
                </TouchableOpacity>
              </View>
            </>
          )}

          {/* STEP 2 - Pregunta seguridad */}
          {step === 2 && (
            <>
              <Text style={styles.label}>Pregunta de seguridad</Text>
              <View style={[styles.fieldFixed]}>
                <Text style={styles.fieldFixedText}>{preguntaSeguridad || '—'}</Text>
              </View>

              <Text style={[styles.label, { marginTop: 12 }]}>Respuesta</Text>
              <TextInput
                ref={respuestaRef}
                placeholder="Respuesta de seguridad"
                placeholderTextColor="#9aa"
                value={respuesta}
                onChangeText={setRespuesta}
                style={[styles.input, isSmallScreen && styles.inputSmall]}
                editable={!verifying && !loading}
                returnKeyType="done"
              />

              <View style={styles.buttonsRow}>
                <TouchableOpacity onPress={handleBack} style={[styles.btn, styles.btnOutline]}>
                  <Text style={styles.btnOutlineText}>Volver</Text>
                </TouchableOpacity>

                <TouchableOpacity
                  onPress={handleVerifyRespuesta}
                  style={[styles.btn, styles.btnPrimary, (verifying || !validRespuesta(respuesta)) && styles.btnDisabled]}
                  disabled={verifying || !validRespuesta(respuesta)}
                >
                  {verifying ? <ActivityIndicator color="#fff" /> : <Text style={styles.btnText}>Verificar respuesta</Text>}
                </TouchableOpacity>
              </View>
            </>
          )}

          {/* STEP 3 - Nueva contraseña */}
          {step === 3 && (
            <>
              <Text style={styles.label}>Nueva contraseña</Text>
              <View style={styles.passwordRow}>
                <TextInput
                  ref={passwordRef}
                  placeholder="Escriba nueva contraseña"
                  placeholderTextColor="#9aa"
                  secureTextEntry={!showPassword}
                  value={newPassword}
                  onChangeText={setNewPassword}
                  style={[styles.input, styles.inputPassword, isSmallScreen && styles.inputSmall]}
                  editable={!loading}
                  returnKeyType="next"
                />
                <TouchableOpacity onPress={() => setShowPassword(v => !v)} style={styles.eyeBtn}>
                  <Icon name={showPassword ? 'eye-off' : 'eye'} size={20} color="#666" />
                </TouchableOpacity>
              </View>
              <Text style={styles.helpText}>Mínimo 8 caracteres. Debe incluir letras y números.</Text>

              <Text style={[styles.label, { marginTop: 12 }]}>Confirmar contraseña</Text>
              <View style={styles.passwordRow}>
                <TextInput
                  placeholder="Confirmar contraseña"
                  placeholderTextColor="#9aa"
                  secureTextEntry={!showConfirmPassword}
                  value={confirmPassword}
                  onChangeText={setConfirmPassword}
                  style={[styles.input, styles.inputPassword, isSmallScreen && styles.inputSmall]}
                  editable={!loading}
                  returnKeyType="done"
                />
                <TouchableOpacity onPress={() => setShowConfirmPassword(v => !v)} style={styles.eyeBtn}>
                  <Icon name={showConfirmPassword ? 'eye-off' : 'eye'} size={20} color="#666" />
                </TouchableOpacity>
              </View>

              <View style={styles.buttonsRow}>
                <TouchableOpacity onPress={handleBack} style={[styles.btn, styles.btnOutline]}>
                  <Text style={styles.btnOutlineText}>Volver</Text>
                </TouchableOpacity>

                <TouchableOpacity
                  onPress={handleSaveNewPassword}
                  style={[styles.btn, styles.btnPrimary, (loading || !validPassword(newPassword) || newPassword !== confirmPassword) && styles.btnDisabled]}
                  disabled={loading || !validPassword(newPassword) || newPassword !== confirmPassword}
                >
                  {loading ? <ActivityIndicator color="#fff" /> : <Text style={styles.btnText}>Guardar contraseña</Text>}
                </TouchableOpacity>
              </View>
            </>
          )}
        </View>
      </ScrollView>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  wrapper: { flex: 1, backgroundColor: '#f3f6fb' },
  container: {
    padding: 18,
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: 24,
    minHeight: '100%',
  },
  card: {
    backgroundColor: 'rgba(255,255,255,0.98)',
    borderRadius: 12,
    padding: 18,
    elevation: 6,
    shadowColor: '#000',
    shadowOpacity: 0.08,
    shadowOffset: { width: 0, height: 6 },
    width: '100%',
    maxWidth: 720,
  },
  cardSmall: { padding: 14 },
  title: {
    fontSize: 20,
    fontWeight: '800',
    color: '#1a365d',
    textAlign: 'center',
    marginBottom: 6,
  },
  titleSmall: { fontSize: 18 },
  subtitle: {
    fontSize: 13,
    color: '#6c757d',
    textAlign: 'center',
    marginBottom: 14,
  },
  subtitleSmall: { fontSize: 12 },
  label: { fontSize: 13, fontWeight: '700', color: '#2d3748', marginBottom: 8 },
  input: {
    borderWidth: 1,
    borderColor: '#eef2ff',
    borderRadius: 8,
    paddingHorizontal: 12,
    height: 46,
    backgroundColor: '#fff',
    color: '#222',
  },
  inputSmall: { height: 42, fontSize: 14 },
  fieldFixed: {
    backgroundColor: '#f8f9fb',
    borderRadius: 8,
    padding: 12,
    borderWidth: 1,
    borderColor: '#eef2ff'
  },
  fieldFixedText: {
    color: '#34495e',
    fontSize: 14,
  },
  buttonsRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    gap: 12,
    marginTop: 14,
  },
  btn: {
    flex: 1,
    paddingVertical: 12,
    borderRadius: 10,
    alignItems: 'center',
    minWidth: 120,
  },
  btnPrimary: {
    backgroundColor: '#4f8cff',
  },
  btnText: { color: '#fff', fontWeight: '700', fontSize: 15 },
  btnOutline: {
    backgroundColor: '#fff',
    borderWidth: 1,
    borderColor: '#e1e5e9',
    marginRight: 8,
  },
  btnOutlineText: { color: '#4f8cff', fontWeight: '700' },
  btnDisabled: {
    opacity: 0.6,
    backgroundColor: '#9aa4b2',
  },
  helpText: { fontSize: 12, color: '#6c757d', marginTop: 6 },
  passwordRow: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  inputPassword: { flex: 1 },
  eyeBtn: { padding: 10, marginLeft: 8 },
});
