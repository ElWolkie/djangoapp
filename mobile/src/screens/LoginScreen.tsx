// src/screens/LoginScreen.tsx
import React, { useState, useRef, useEffect } from 'react';
import {
  StyleSheet,
  Text,
  View,
  TextInput,
  TouchableOpacity,
  Image,
  Alert,
  KeyboardAvoidingView,
  Platform,
  Dimensions,
  Animated,
  ActivityIndicator,
} from 'react-native';
import Icon from 'react-native-vector-icons/MaterialCommunityIcons';
import type { StackNavigationProp } from '@react-navigation/stack';
import api from '../api/api';
import { storeTokens } from '../api/auth'; // tu helper

// NOTE: Ajusté los nombres para compatibilidad con diferentes navegators
type RootStackParamList = {
  Login: undefined;
  Main: undefined;
  Register: { form?: any } | undefined; // coincide con App.tsx (Register -> RegisterScreen.tsx)
  RegisterPerson: { form?: any } | undefined; // alternativa
  RegisterScreen: { form?: any } | undefined; // alternativa
  RegisterUser: { person: any } | undefined;
};
type LoginScreenNavigationProp = StackNavigationProp<RootStackParamList, 'Login'>;

interface LoginScreenProps {
  navigation: LoginScreenNavigationProp;
}

const { width: screenWidth } = Dimensions.get('window');

export default function LoginScreen({ navigation }: LoginScreenProps) {
  const [cedula, setCedula] = useState(''); // aquí guardaremos sólo dígitos
  const [password, setPassword] = useState('');
  const [focusField, setFocusField] = useState<'cedula' | 'password' | null>(null);
  const [errors, setErrors] = useState<{ cedula?: string; password?: string }>({});
  const [buttonScale] = useState(new Animated.Value(1));
  const [loading, setLoading] = useState(false);
  const formAnim = useRef(new Animated.Value(0)).current;
  const logoAnim = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    Animated.parallel([
      Animated.spring(formAnim, { toValue: 1, useNativeDriver: true, friction: 7 }),
      Animated.spring(logoAnim, { toValue: 1, useNativeDriver: true, friction: 3, tension: 80 }),
    ]).start();
  }, []);

  const validate = () => {
    const newErrors: { cedula?: string; password?: string } = {};
    let valid = true;
    if (!cedula || cedula.trim().length < 6) {
      newErrors.cedula = 'Ingrese su cédula (solo números, mínimo 6 dígitos)';
      valid = false;
    }
    if (!password || password.trim().length === 0) {
      newErrors.password = 'Ingrese su contraseña';
      valid = false;
    }
    setErrors(newErrors);
    return valid;
  };

  const normalizeCedulaToDigits = (raw: string) => {
    if (!raw) return '';
    return String(raw).replace(/\D+/g, '');
  };

  /**
   * Intenta obtener tokens desde varios endpoints y shapes.
   * - Primero prueba token_cedula (tu endpoint personalizado)
   * - Luego prueba token (simplejwt)
   */
  const tryObtainToken = async (digits: string, passwordValue: string) => {
    const endpoints = ['/api/token_cedula/', '/api/token/'];
    const payloadCandidates: Record<string, any>[] = [
      { cedula: digits, password: passwordValue },
      { username: digits, password: passwordValue },
      { documento: digits, password: passwordValue },
      { id: digits, password: passwordValue },
      { email: digits, password: passwordValue },
    ];

    let lastError: any = null;

    for (const url of endpoints) {
      for (const payload of payloadCandidates) {
        try {
          const res = await api.post(url, payload);
          const d = res?.data ?? {};

          const access = d.access ?? d.access_token ?? d.token ?? null;
          const refresh = d.refresh ?? d.refresh_token ?? null;

          if (access) {
            return { access, refresh, raw: d, usedUrl: url, usedPayload: payload };
          }

          if (d.data && (d.data.access || d.data.token)) {
            return { access: d.data.access ?? d.data.token, refresh: d.data.refresh ?? null, raw: d, usedUrl: url, usedPayload: payload };
          }

          lastError = { url, payload, response: d };
        } catch (err: any) {
          lastError = err;
          if (err?.response?.data) {
            return { error: err.response.data, rawErr: err, usedUrl: url, usedPayload: payload };
          }
        }
      }
    }

    return { error: lastError ?? 'No response' };
  };

  const handleLogin = async () => {
    if (!validate()) return;

    setLoading(true);
    Animated.sequence([
      Animated.spring(buttonScale, { toValue: 0.93, useNativeDriver: true }),
      Animated.spring(buttonScale, { toValue: 1, friction: 3, tension: 80, useNativeDriver: true }),
    ]).start();

    try {
      const digits = normalizeCedulaToDigits(cedula);
      if (!digits || digits.length < 6) {
        Alert.alert('Cédula inválida', 'Debe ingresar al menos 6 dígitos de cédula.');
        setLoading(false);
        return;
      }

      // opcional: llamada para verificar-cedula (no crítica)
      try {
        await api.get(`/api/verificar-cedula/?cedula=${encodeURIComponent(digits)}`).catch(() => null);
      } catch { /* noop */ }

      const result = await tryObtainToken(digits, password);

      if (result == null) {
        Alert.alert('Error', 'No se obtuvo respuesta del servidor.');
        setLoading(false);
        return;
      }

      if ((result as any).error) {
        const e = (result as any).error;
        if (typeof e === 'object') {
          const textErr =
            e.detail ||
            e.non_field_errors?.join?.(', ') ||
            Object.entries(e).map(([k, v]) => `${k}: ${Array.isArray(v) ? v.join('; ') : String(v)}`).join('\n') ||
            JSON.stringify(e);
          Alert.alert('Error de autenticación', textErr);
        } else {
          Alert.alert('Error de conexión', String(e));
        }
        setLoading(false);
        return;
      }

      const access = (result as any).access as string | undefined;
      const refresh = (result as any).refresh as string | undefined;

      if (!access) {
        Alert.alert('Error', 'El servidor no devolvió token de acceso válido.');
        setLoading(false);
        return;
      }

      // Guardar tokens y usuario (ajusta storeTokens a tu helper)
      await storeTokens(access, refresh ?? null, (result as any).user ?? null);

      // navegar al Main (reset para evitar volver al login)
      navigation.reset({ index: 0, routes: [{ name: 'Main' }] });
    } catch (err: any) {
      console.error('Login error', err);
      Alert.alert('Error', err?.message ?? 'Error al intentar iniciar sesión');
    } finally {
      setLoading(false);
    }
  };

  // NUEVO: navegar directo a la pantalla "Register" (registrada en App.tsx)
  const openRegister = () => {
    const cedulaDigits = normalizeCedulaToDigits(cedula);
    const prefill = { form: { cedula: cedulaDigits } };
    console.log('openRegister fired — prefill:', prefill);

    // Navegar a la ruta que registraste en App.tsx: "Register"
    navigation.navigate('Register' as any, prefill);

    // Verificación rápida: si la navegación no ocurre por alguna razón,
    // avisamos al desarrollador (esto rara vez se mostrará en producción).
    setTimeout(() => {
      try {
        const state = (navigation as any).getState?.();
        const current = state?.routes?.[state.index]?.name;
        if (current === 'Login') {
          Alert.alert(
            'Registro',
            'No se pudo navegar a "Register". Verifica que la ruta "Register" esté registrada en tu Stack Navigator (App.tsx).'
          );
        }
      } catch (e) {
        // noop
      }
    }, 300);
  };

  // NUEVO: navegar directo a la pantalla "RegisterUser" (la de crear cuenta de usuario para una persona ya registrada)
  const openRegisterUser = () => {
    const cedulaDigits = normalizeCedulaToDigits(cedula);
    const personParam = { cedula: cedulaDigits ? cedulaDigits : undefined };
    console.log('openRegisterUser fired — personParam:', personParam);

    // Intentamos navegar a 'RegisterUser' pasando { person: { cedula } }
    // Nota: asegúrate de registrar RegisterUser en App.tsx si aún no está.
    navigation.navigate('RegisterUser' as any, { person: personParam });

    // Heurística de verificación (útil si la ruta no existe)
    setTimeout(() => {
      try {
        const state = (navigation as any).getState?.();
        const current = state?.routes?.[state.index]?.name;
        if (current === 'Login') {
          Alert.alert(
            'Registro de Usuario',
            'No se pudo navegar a "RegisterUser". Verifica que la ruta "RegisterUser" esté registrada en tu Stack Navigator (App.tsx).'
          );
        }
      } catch (e) {
        // noop
      }
    }, 300);
  };

  // Responsive width para PC: si pantalla ancha, usar caja más estrecha y centrada
  const isWide = screenWidth >= 1000;
  const formWidth = isWide ? 560 : Math.min(720, screenWidth * 0.88);

  return (
    <KeyboardAvoidingView style={styles.container} behavior={Platform.OS === 'ios' ? 'padding' : undefined}>
      <Image style={styles.bgImage} source={require('../../assets/frontImg.jpg')} blurRadius={3} />
      <View style={styles.overlay} />
      <Animated.View style={[styles.logoContainer, { transform: [{ scale: logoAnim.interpolate({ inputRange: [0, 1], outputRange: [0.7, 1] }) }, { translateY: logoAnim.interpolate({ inputRange: [0, 1], outputRange: [-40, 0] }) }], opacity: logoAnim }]}>
        <Text style={styles.logoTitle}>FUNDACIÓN UPTYAB</Text>
        <Text style={styles.logoSubtitle}>Trámites académicos</Text>
      </Animated.View>

      <Animated.View style={[ styles.form, { width: formWidth, opacity: formAnim, transform: [{ translateY: formAnim.interpolate({ inputRange: [0,1], outputRange: [80,0] }) }] } ]}>
        <View style={[ styles.inputContainer, focusField === 'cedula' && styles.inputContainerFocused, errors.cedula && styles.inputContainerError ]}>
          <Icon name="card-account-details" size={24} color={focusField === 'cedula' ? '#4f8cff' : errors.cedula ? '#e63946' : '#aaa'} style={styles.inputIcon} />
          <TextInput
            style={styles.inputs}
            placeholder="Cédula (solo números)"
            keyboardType="numeric"
            placeholderTextColor="#aaa"
            value={cedula}
            onChangeText={(text) => {
              const onlyDigits = text.replace(/\D+/g, '');
              setCedula(onlyDigits);
              if (errors.cedula) setErrors({ ...errors, cedula: undefined });
            }}
            onFocus={() => setFocusField('cedula')}
            onBlur={() => setFocusField(null)}
            returnKeyType="next"
            editable={!loading}
          />
        </View>
        {errors.cedula && <Text style={styles.errorText}>{errors.cedula}</Text>}

        <View style={[ styles.inputContainer, focusField === 'password' && styles.inputContainerFocused, errors.password && styles.inputContainerError ]}>
          <Icon name="lock" size={24} color={focusField === 'password' ? '#4f8cff' : errors.password ? '#e63946' : '#aaa'} style={styles.inputIcon} />
          <TextInput
            style={styles.inputs}
            placeholder="Contraseña"
            secureTextEntry
            placeholderTextColor="#aaa"
            value={password}
            onChangeText={(text) => { setPassword(text); if (errors.password) setErrors({ ...errors, password: undefined }); }}
            onFocus={() => setFocusField('password')}
            onBlur={() => setFocusField(null)}
            returnKeyType="done"
            editable={!loading}
          />
        </View>
        {errors.password && <Text style={styles.errorText}>{errors.password}</Text>}

        <TouchableOpacity style={styles.btnForgotPassword} onPress={() => Alert.alert('Recuperar contraseña', 'Funcionalidad próximamente disponible')} disabled={loading}>
          <Text style={styles.btnForgotText}>¿Olvidó su contraseña?</Text>
        </TouchableOpacity>

        <Animated.View style={{ width: '100%', transform: [{ scale: buttonScale }] }}>
          <TouchableOpacity style={[styles.buttonContainer, styles.loginButton, loading && { opacity: 0.8 }]} onPress={handleLogin} activeOpacity={0.85} disabled={loading}>
            {loading ? (
              <>
                <ActivityIndicator color="#fff" size="small" style={{ marginRight: 8 }} />
                <Text style={styles.loginText}>Entrando...</Text>
              </>
            ) : (
              <Text style={styles.loginText}>Entrar</Text>
            )}
          </TouchableOpacity>
        </Animated.View>

        {/* Registrarse: dos opciones
            - "Registrarse" (persona) -> openRegister (usa la ruta 'Register' ya en App.tsx)
            - "Registrar usuario" (crear cuenta para persona ya registrada) -> openRegisterUser (ruta 'RegisterUser')
        */}
        <View style={styles.registerRow}>
          <Text style={styles.registerHint}>¿No estás registrado?</Text>

          <View style={styles.registerButtonsGroup}>
            <TouchableOpacity style={styles.registerButton} onPress={openRegister} activeOpacity={0.85}>
              <Icon name="account-plus" size={18} color="#fff" style={{ marginRight: 8 }} />
              <Text style={styles.registerText}>Registrarse</Text>
            </TouchableOpacity>

            <TouchableOpacity style={styles.registerUserButton} onPress={openRegisterUser} activeOpacity={0.85}>
              <Icon name="account-key" size={16} color="#fff" style={{ marginRight: 8 }} />
              <Text style={styles.registerUserText}>Registrar usuario</Text>
            </TouchableOpacity>
          </View>
        </View>
      </Animated.View>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, alignItems: 'center', justifyContent: 'center', backgroundColor: '#DCDCDC' },
  bgImage: { position: 'absolute', width: '100%', height: '100%', resizeMode: 'cover', top: 0, left: 0 },
  overlay: { ...StyleSheet.absoluteFillObject, backgroundColor: 'rgba(0,0,40,0.35)' },
  logoContainer: { alignItems: 'center', marginBottom: 40 },
  logoTitle: { color: '#fff', fontWeight: 'bold', fontSize: 26, textAlign: 'center', letterSpacing: 1 },
  logoSubtitle: { color: '#fff', fontWeight: '600', fontSize: 16, textAlign: 'center', marginTop: 2 },
  form: { width: screenWidth * 0.88, backgroundColor: 'rgba(255,255,255,0.96)', borderRadius: 22, padding: 26, alignItems: 'center', elevation: 10 },
  inputContainer: { flexDirection: 'row', alignItems: 'center', backgroundColor: '#fff', borderRadius: 30, height: 50, marginBottom: 10, width: '100%', paddingHorizontal: 12, borderWidth: 1.2, borderColor: 'transparent' },
  inputContainerFocused: { borderColor: '#4f8cff' },
  inputContainerError: { borderColor: '#e63946' },
  inputs: { flex: 1, height: 45, marginLeft: 10, color: '#22223b', fontSize: 16 },
  inputIcon: { marginLeft: 2, marginRight: 2 },
  errorText: { color: '#e63946', fontSize: 13, marginBottom: 6, alignSelf: 'flex-start', marginLeft: 8 },
  btnForgotPassword: { alignSelf: 'flex-end', marginBottom: 10 },
  btnForgotText: { color: '#4f8cff', fontWeight: 'bold', fontSize: 14 },
  buttonContainer: { height: 48, flexDirection: 'row', justifyContent: 'center', alignItems: 'center', marginBottom: 10, width: '100%', borderRadius: 30, backgroundColor: 'transparent' },
  loginButton: { backgroundColor: '#4f8cff' },
  loginText: { color: 'white', fontWeight: 'bold', fontSize: 17 },
  registerRow: { width: '100%', marginTop: 8, flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' },
  registerHint: { color: '#555', fontSize: 14 },

  /* agrupación de botones a la derecha */
  registerButtonsGroup: { flexDirection: 'row', alignItems: 'center', gap: 8 },

  registerButton: { flexDirection: 'row', alignItems: 'center', backgroundColor: '#2b8cff', paddingVertical: 8, paddingHorizontal: 12, borderRadius: 24, marginLeft: 8 },
  registerText: { color: '#fff', fontWeight: '700', fontSize: 14 },

  /* nuevo: botón para registrar usuario */
  registerUserButton: { flexDirection: 'row', alignItems: 'center', backgroundColor: '#1f6fe0', paddingVertical: 8, paddingHorizontal: 12, borderRadius: 24, marginLeft: 8 },
  registerUserText: { color: '#fff', fontWeight: '700', fontSize: 13 },

});
