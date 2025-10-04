// src/screens/RegisterUserScreen.tsx
import React, { useEffect, useState, useLayoutEffect } from 'react';
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
  Image,
} from 'react-native';
import type { StackNavigationProp } from '@react-navigation/stack';
import { RouteProp, useRoute } from '@react-navigation/native';
import api from '../api/api';
import { Picker } from '@react-native-picker/picker';

type RootStackParamList = {
  Login: undefined;
  Main: undefined;
  Register: { form?: any } | undefined;
  RegisterUser: { person?: any } | undefined;
};

type RegisterUserScreenNavigationProp = StackNavigationProp<RootStackParamList, 'RegisterUser'>;
type RegisterUserScreenRouteProp = RouteProp<RootStackParamList, 'RegisterUser'>;

interface Props {
  navigation: RegisterUserScreenNavigationProp;
}

const PREGUNTAS_SEGURIDAD = [
  "¿Cuál es el nombre de tu primera mascota?",
  "¿En qué ciudad naciste?",
  "¿Cuál es el nombre de soltera de tu madre?",
  "¿Cuál era el nombre de tu escuela primaria?",
  "¿Cuál es tu película favorita?",
  "¿Cuál es tu color favorito?",
];

type FormState = {
  tipo_cedula: 'V' | 'E' | 'P';
  numero_cedula: string; // sólo números
  password: string;
  confirmPassword: string;
  preguntaSeguridad: string;
  respuestaSeguridad: string;
  nombres?: string;
};

function normalizeIncomingCedula(raw?: string): { tipo: 'V' | 'E' | 'P'; numero: string } {
  if (!raw) return { tipo: 'V', numero: '' };
  const s = String(raw).toUpperCase().replace(/\s+/g, '');
  // Acepta: V-1234, V1234, 1234
  if (s.includes('-')) {
    const [t, n] = s.split('-', 2);
    return { tipo: (t === 'E' || t === 'P') ? t as 'E'|'P' : 'V', numero: n.replace(/\D+/g, '') };
  }
  if (s.length && isNaN(Number(s[0]))) {
    return { tipo: (s[0] === 'E' || s[0] === 'P') ? s[0] as 'E'|'P' : 'V', numero: s.slice(1).replace(/\D+/g, '') };
  }
  return { tipo: 'V', numero: s.replace(/\D+/g, '') };
}

export default function RegisterUserScreen({ navigation }: Props) {
  // ocultar header superior del stack (barra blanca con flecha)
  useLayoutEffect(() => {
    navigation.setOptions?.({ headerShown: false });
  }, [navigation]);

  const route = useRoute<RegisterUserScreenRouteProp>();
  const personFromPreviousScreen = route.params?.person;

  const incoming = normalizeIncomingCedula(personFromPreviousScreen?.cedula);

  const initialForm: FormState = {
    tipo_cedula: incoming.tipo,
    numero_cedula: incoming.numero,
    password: '',
    confirmPassword: '',
    preguntaSeguridad: '',
    respuestaSeguridad: '',
    nombres: personFromPreviousScreen?.nombres ?? '',
  };

  const [form, setForm] = useState<FormState>(initialForm);
  const [loading, setLoading] = useState(false);
  const [errors, setErrors] = useState<Record<string, string>>({});

  useEffect(() => {
    if (route.params?.person) {
      const p = route.params.person;
      const incoming2 = normalizeIncomingCedula(p.cedula);
      setForm(prev => ({
        ...prev,
        tipo_cedula: incoming2.tipo,
        numero_cedula: incoming2.numero,
        nombres: p.nombres ?? prev.nombres,
      }));
      setErrors({});
    }
  }, [route.params?.person]);

  const screenWidth = Dimensions.get('window').width;
  const isWide = screenWidth >= 1000;

  const changeField = (key: keyof FormState, value: string) => {
    setForm(prev => ({ ...prev, [key]: value }));
    if (errors[key]) {
      setErrors(prev => {
        const cp = { ...prev };
        delete cp[key];
        return cp;
      });
    }
  };

  const validateForm = () => {
    const newErrors: Record<string, string> = {};
    const numero = form.numero_cedula.replace(/\D+/g, '');
    if (!numero || numero.length < 6) newErrors.cedula = 'Número de cédula inválido (mín. 6 dígitos).';
    if (!form.password || form.password.length < 8) newErrors.password = 'La contraseña debe tener al menos 8 caracteres.';
    if (form.password !== form.confirmPassword) newErrors.confirmPassword = 'Las contraseñas no coinciden.';
    if (!form.preguntaSeguridad) newErrors.preguntaSeguridad = 'Seleccione una pregunta de seguridad.';
    if (!form.respuestaSeguridad || !form.respuestaSeguridad.trim()) newErrors.respuestaSeguridad = 'La respuesta es requerida.';
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const buildCedulaFormatted = () => {
    const num = String(form.numero_cedula).replace(/\D+/g, '');
    return `${form.tipo_cedula}-${num}`;
  };

  const handleRegisterUser = async () => {
    if (!validateForm()) {
      Alert.alert('Formulario inválido', 'Por favor corrija los errores antes de continuar.');
      return;
    }

    setLoading(true);
    try {
      const payload = {
        cedula: buildCedulaFormatted(), // ej: V-12345678 (OBLIGATORIO)
        password: form.password,
        preguntaSeguridad: form.preguntaSeguridad,
        respuestaSeguridad: form.respuestaSeguridad.trim(),
      };

      console.log('📤 Enviando para crear usuario:', payload);
      const response = await api.post('/api/registrar_usuario/', payload);

      if (response.status === 201 || response.status === 200) {
        const mensaje = (response.data && (response.data.mensaje || response.data.message)) ?? 'Usuario creado correctamente';
        Alert.alert('¡Usuario Creado!', mensaje, [
          { text: 'Ir a Iniciar Sesión', onPress: () => navigation.replace('Login') },
        ]);
      } else {
        Alert.alert('Registro', 'Respuesta del servidor: ' + JSON.stringify(response.data));
      }
    } catch (error: any) {
      console.error('❌ Error al crear usuario:', error.response?.data || error);
      const errorMessage =
        error.response?.data?.error ||
        error.response?.data?.message ||
        (typeof error.response?.data === 'string' ? error.response?.data : null) ||
        'Ocurrió un error inesperado. Intente más tarde.';
      Alert.alert('Error en el registro', String(errorMessage));
    } finally {
      setLoading(false);
    }
  };

  const goBackToLogin = () => navigation.navigate('Login');

  const clearForm = () => {
    setForm({
      tipo_cedula: personFromPreviousScreen ? normalizeIncomingCedula(personFromPreviousScreen.cedula).tipo : 'V',
      numero_cedula: personFromPreviousScreen ? normalizeIncomingCedula(personFromPreviousScreen.cedula).numero : '',
      password: '',
      confirmPassword: '',
      preguntaSeguridad: '',
      respuestaSeguridad: '',
      nombres: personFromPreviousScreen?.nombres ?? '',
    });
    setErrors({});
  };

  return (
    <KeyboardAvoidingView style={styles.wrapper} behavior={Platform.OS === 'ios' ? 'padding' : undefined}>
      <Image style={styles.bgImage} source={require('../../assets/frontImg.jpg')} blurRadius={4} />
      <View style={styles.overlay} />

      <ScrollView contentContainerStyle={styles.container}>
        <View style={[styles.card, isWide && { width: 920 }]}>
          <Text style={styles.title}>Crear Cuenta de Usuario</Text>

          {form.nombres ? (
            <Text style={styles.subtitle}>
              Estás creando una cuenta para: <Text style={{ fontWeight: '800' }}>{form.nombres}</Text>
            </Text>
          ) : (
            <Text style={styles.subtitle}>
              Complete los campos para crear la cuenta.
            </Text>
          )}

          <View style={{ marginTop: 6 }}>
            <Text style={styles.label}>Tipo de cédula *</Text>
            <View style={styles.pickerWrapInline}>
              <Picker
                selectedValue={form.tipo_cedula}
                onValueChange={(itemValue) => changeField('tipo_cedula', itemValue as 'V'|'E'|'P')}
                mode="dropdown"
                enabled={!loading}
                style={styles.pickerInner}
              >
                <Picker.Item label="V (Venezolano)" value="V" />
                <Picker.Item label="E (Extranjero)" value="E" />
                <Picker.Item label="P (Pasaporte)" value="P" />
              </Picker>
            </View>

            <Text style={styles.label}>Número de cédula *</Text>
            <TextInput
              style={styles.input}
              placeholder="Ej: 12345678"
              placeholderTextColor="#9aa"
              value={form.numero_cedula}
              onChangeText={(v) => changeField('numero_cedula', v.replace(/\D+/g, ''))}
              editable={!loading}
              keyboardType="numeric"
              returnKeyType="next"
              maxLength={20}
            />
            {errors.cedula && <Text style={styles.errorSmall}>{errors.cedula}</Text>}

            <Text style={styles.label}>Cédula completa</Text>
            <Text style={{ marginBottom: 8 }}>{buildCedulaFormatted()}</Text>

            <Text style={styles.label}>Contraseña *</Text>
            <TextInput
              style={styles.input}
              placeholder="Mínimo 8 caracteres"
              placeholderTextColor="#9aa"
              value={form.password}
              onChangeText={(v) => changeField('password', v)}
              secureTextEntry
              editable={!loading}
            />
            {errors.password && <Text style={styles.errorSmall}>{errors.password}</Text>}

            <Text style={styles.label}>Confirmar Contraseña *</Text>
            <TextInput
              style={styles.input}
              placeholder="Repita la contraseña"
              placeholderTextColor="#9aa"
              value={form.confirmPassword}
              onChangeText={(v) => changeField('confirmPassword', v)}
              secureTextEntry
              editable={!loading}
            />
            {errors.confirmPassword && <Text style={styles.errorSmall}>{errors.confirmPassword}</Text>}

            <Text style={styles.label}>Pregunta de Seguridad *</Text>
            <View style={styles.pickerWrapInline}>
              <Picker
                selectedValue={form.preguntaSeguridad}
                onValueChange={(itemValue) => changeField('preguntaSeguridad', itemValue)}
                mode="dropdown"
                enabled={!loading}
                style={styles.pickerInner}
              >
                <Picker.Item label="-- Seleccione una pregunta --" value="" />
                {PREGUNTAS_SEGURIDAD.map(q => <Picker.Item key={q} label={q} value={q} />)}
              </Picker>
            </View>
            {errors.preguntaSeguridad && <Text style={styles.errorSmall}>{errors.preguntaSeguridad}</Text>}

            <Text style={styles.label}>Respuesta de Seguridad *</Text>
            <TextInput
              style={styles.input}
              placeholder="Su respuesta secreta"
              placeholderTextColor="#9aa"
              value={form.respuestaSeguridad}
              onChangeText={(v) => changeField('respuestaSeguridad', v)}
              editable={!loading}
            />
            {errors.respuestaSeguridad && <Text style={styles.errorSmall}>{errors.respuestaSeguridad}</Text>}
          </View>

          <View style={styles.buttonsRow}>
            <TouchableOpacity
              style={[styles.btn, styles.btnPrimary, loading && styles.btnDisabled]}
              onPress={handleRegisterUser}
              disabled={loading}
              activeOpacity={0.85}
            >
              {loading ? <ActivityIndicator color="#fff" /> : <Text style={styles.btnText}>Crear Usuario</Text>}
            </TouchableOpacity>
          </View>

          <View style={styles.footerRow}>
            <TouchableOpacity onPress={goBackToLogin} style={styles.linkBtn}>
              <Text style={styles.linkText}>Volver al inicio de sesión</Text>
            </TouchableOpacity>

            <TouchableOpacity onPress={clearForm} style={styles.linkBtn}>
              <Text style={styles.linkText}>Limpiar formulario</Text>
            </TouchableOpacity>
          </View>

          <Text style={styles.requiredHint}>* Campos obligatorios</Text>
        </View>
      </ScrollView>
    </KeyboardAvoidingView>
  );
}

// Mantén los estilos previos (copiar desde tu archivo actual)
const styles = StyleSheet.create({
  wrapper: { flex: 1, backgroundColor: '#f3f6fb' },
  bgImage: { position: 'absolute', width: '100%', height: '100%', resizeMode: 'cover', top: 0, left: 0 },
  overlay: { ...StyleSheet.absoluteFillObject, backgroundColor: 'rgba(0,0,40,0.35)' },
  container: { padding: 18, alignItems: 'center', justifyContent: 'center', paddingVertical: 26 },
  card: {
    width: '100%', maxWidth: 920, backgroundColor: 'rgba(255,255,255,0.94)', borderRadius: 12, padding: 18,
    elevation: 8, shadowColor: '#000', shadowOpacity: 0.12, shadowOffset: { width: 0, height: 8 },
  },
  title: { fontSize: 20, fontWeight: '800', marginBottom: 6, color: '#222', textAlign: 'center' },
  subtitle: { fontSize: 14, color: '#666', marginBottom: 12, textAlign: 'center' },
  label: { fontSize: 13, color: '#444', marginBottom: 6, fontWeight: '700' },
  input: {
    borderWidth: 1, borderColor: '#eef2ff', borderRadius: 8, paddingHorizontal: 12, height: 46,
    backgroundColor: '#fff', color: '#222', marginBottom: 8,
  },
  inputDisabled: { backgroundColor: '#f2f4f8', color: '#9aa' },
  errorSmall: { color: '#e63946', fontSize: 12, marginTop: 2, marginBottom: 6 },
  buttonsRow: { flexDirection: 'row', justifyContent: 'center', marginTop: 12 },
  btn: { paddingVertical: 12, borderRadius: 10, alignItems: 'center', minWidth: 200 },
  btnPrimary: { backgroundColor: '#1f6fff' },
  btnDisabled: { backgroundColor: '#a0a0a0', opacity: 0.6 },
  btnText: { color: '#fff', fontWeight: '800', fontSize: 16 },
  footerRow: { flexDirection: 'row', justifyContent: 'space-between', marginTop: 14 },
  linkBtn: { padding: 6 },
  linkText: { color: '#4f8cff', fontWeight: '700' },
  requiredHint: { fontSize: 12, color: '#666', marginTop: 10, textAlign: 'center', fontStyle: 'italic' },
  pickerWrapInline: {
    borderWidth: 1, borderColor: '#eef2ff', borderRadius: 8, overflow: 'hidden',
    backgroundColor: '#fff', height: 46, justifyContent: 'center', marginBottom: 8,
  },
  pickerInner: { height: 46 },
});
