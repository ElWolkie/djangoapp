// src/screens/LoginScreen.tsx
import React, { useState, useRef, useEffect, useContext } from 'react';
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
import { AuthContext } from '../contexts/AuthContext';

type RootStackParamList = {
  Login: undefined;
  Main: undefined;
};
type LoginScreenNavigationProp = StackNavigationProp<RootStackParamList, 'Login'>;

interface LoginScreenProps {
  navigation: LoginScreenNavigationProp;
}

const { width } = Dimensions.get('window');

export default function LoginScreen({ navigation }: LoginScreenProps) {
  const [cedula, setCedula] = useState(''); // guardamos solo dígitos
  const [password, setPassword] = useState('');
  const [focusField, setFocusField] = useState<'cedula' | 'password' | null>(null);
  const [errors, setErrors] = useState<{ cedula?: string; password?: string }>({});
  const [buttonScale] = useState(new Animated.Value(1));
  const [loading, setLoading] = useState(false);
  const formAnim = useRef(new Animated.Value(0)).current;
  const logoAnim = useRef(new Animated.Value(0)).current;

  const { loginWithTokens } = useContext(AuthContext);

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

  // Intenta obtener tokens desde endpoints y shapes
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
            return {
              access: d.data.access ?? d.data.token,
              refresh: d.data.refresh ?? null,
              raw: d,
              usedUrl: url,
              usedPayload: payload,
            };
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

  // Buscar perfil en persona/usuario usando la cédula (no requiere endpoint /api/me/)
  const fetchProfileIfNeeded = async (maybeUser: any, accessToken?: string, digitsForLookup?: string) => {
    if (maybeUser && typeof maybeUser === 'object' && (maybeUser.displayName || maybeUser.nombres || maybeUser.name || maybeUser.username || maybeUser.email)) {
      return maybeUser;
    }

    const prevAuth = api.defaults.headers.common['Authorization'];

    try {
      if (accessToken) api.defaults.headers.common['Authorization'] = `Bearer ${accessToken}`;

      if (digitsForLookup) {
        // 1) Buscar en personas
        const r = await api.get(`/api/personas/?cedula=${encodeURIComponent(digitsForLookup)}`).catch(() => null);
        if (r && r.data) {
          const persona = Array.isArray(r.data) ? (r.data[0] ?? null) : (r.data ?? null);
          if (persona) {
            const maybeName =
              persona.displayName ??
              persona.nombre ??
              persona.nombres ??
              (`${persona.nombre || persona.nombres || ''} ${persona.apellido || persona.apellidos || ''}`.trim()) ??
              persona.full_name ??
              null;

            const userObj = { displayName: maybeName || `Usuario ${persona.id ?? ''}`, persona };
            if (prevAuth) api.defaults.headers.common['Authorization'] = prevAuth;
            else delete api.defaults.headers.common['Authorization'];
            return userObj;
          }
        }

        // 2) Buscar en usuario relacionado (endpoint list)
        const ru = await api.get(`/api/usuario/?idPersona__cedula=${encodeURIComponent(digitsForLookup)}`).catch(() => null);
        if (ru && ru.data) {
          const usuario = Array.isArray(ru.data) ? (ru.data[0] ?? null) : (ru.data ?? null);
          if (usuario) {
            const persona = usuario.idPersona ?? usuario.persona ?? null;
            const maybeName =
              usuario.displayName ??
              persona?.nombre ??
              persona?.nombres ??
              `${persona?.nombre || persona?.nombres || ''} ${persona?.apellido || persona?.apellidos || ''}`.trim() ??
              usuario.username ??
              null;
            const userObj = { displayName: maybeName || `Usuario ${usuario.id ?? ''}`, usuario, persona };
            if (prevAuth) api.defaults.headers.common['Authorization'] = prevAuth;
            else delete api.defaults.headers.common['Authorization'];
            return userObj;
          }
        }
      }
    } catch (e) {
      // ignore
    } finally {
      if (prevAuth) api.defaults.headers.common['Authorization'] = prevAuth;
      else delete api.defaults.headers.common['Authorization'];
    }

    return null;
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

      // opción: verificar-cedula (no crítico)
      try {
        await api.get(`/api/verificar-cedula/?cedula=${encodeURIComponent(digits)}`).catch(() => null);
      } catch {}

      const result = await tryObtainToken(digits, password);

      if (!result) {
        Alert.alert('Error', 'No se obtuvo respuesta del servidor.');
        setLoading(false);
        return;
      }

      if ((result as any).error) {
        const e = (result as any).error;
        const textErr =
          e.detail ||
          e.non_field_errors?.join?.(', ') ||
          Object.entries(e).map(([k, v]) => `${k}: ${Array.isArray(v) ? v.join('; ') : String(v)}`).join('\n') ||
          String(e);
        Alert.alert('Error de autenticación', textErr);
        setLoading(false);
        return;
      }

      const access = (result as any).access as string | undefined;
      const refresh = (result as any).refresh as string | undefined;
      let returnedUser = (result as any).user ?? (result as any).raw?.user ?? null;

      if (!returnedUser && access) {
        returnedUser = await fetchProfileIfNeeded(null, access, digits);
      }

      if (!access) {
        Alert.alert('Error', 'El servidor no devolvió token de acceso válido.');
        setLoading(false);
        return;
      }

      // Usa loginWithTokens del AuthContext (se encargará de persistir tokens + user)
      try {
        await loginWithTokens(access, refresh ?? null, returnedUser ?? null);
      } catch (e) {
        // si falla guardar, aún seguimos pero informamos
        console.warn('loginWithTokens fallo', e);
      }

      // navegar al Main
      navigation.reset({ index: 0, routes: [{ name: 'Main' }] });
    } catch (err: any) {
      console.error('Login error', err);
      Alert.alert('Error', err?.message ?? 'Error al intentar iniciar sesión');
    } finally {
      setLoading(false);
    }
  };

  return (
    <KeyboardAvoidingView style={styles.container} behavior={Platform.OS === 'ios' ? 'padding' : undefined}>
      <Image style={styles.bgImage} source={require('../../assets/frontImg.jpg')} blurRadius={3} />
      <View style={styles.overlay} />
      <Animated.View
        style={[
          styles.logoContainer,
          {
            transform: [
              {
                scale: logoAnim.interpolate({ inputRange: [0, 1], outputRange: [0.7, 1] }),
              },
              {
                translateY: logoAnim.interpolate({ inputRange: [0, 1], outputRange: [-40, 0] }),
              },
            ],
            opacity: logoAnim,
          },
        ]}
      >
        <Text style={styles.logoTitle}>FUNDACIÓN UPTYAB</Text>
        <Text style={styles.logoSubtitle}>Trámites académicos</Text>
      </Animated.View>

      <Animated.View
        style={[
          styles.form,
          {
            opacity: formAnim,
            transform: [{ translateY: formAnim.interpolate({ inputRange: [0, 1], outputRange: [80, 0] }) }],
          },
        ]}
      >
        <View style={[styles.inputContainer, focusField === 'cedula' && styles.inputContainerFocused, errors.cedula && styles.inputContainerError]}>
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

        <View style={[styles.inputContainer, focusField === 'password' && styles.inputContainerFocused, errors.password && styles.inputContainerError]}>
          <Icon name="lock" size={24} color={focusField === 'password' ? '#4f8cff' : errors.password ? '#e63946' : '#aaa'} style={styles.inputIcon} />
          <TextInput
            style={styles.inputs}
            placeholder="Contraseña"
            secureTextEntry
            placeholderTextColor="#aaa"
            value={password}
            onChangeText={(text) => {
              setPassword(text);
              if (errors.password) setErrors({ ...errors, password: undefined });
            }}
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
  form: { width: width * 0.88, backgroundColor: 'rgba(255,255,255,0.96)', borderRadius: 22, padding: 26, alignItems: 'center', elevation: 10 },
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
});
