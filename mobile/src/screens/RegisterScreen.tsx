// RegisterScreen.tsx - VERSIÓN CORREGIDA
import React, { useEffect, useState } from 'react';
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
  RegisterUser: { person: any } | undefined;
};

type RegisterScreenNavigationProp = StackNavigationProp<RootStackParamList, 'Register'>;
type RegisterScreenRouteProp = RouteProp<RootStackParamList, 'Register'>;

interface Props {
  navigation: RegisterScreenNavigationProp;
}

type PersonFormData = {
  tipo_cedula: 'V' | 'E' | 'P';
  numero_cedula: string;
  rif?: string;
  nombres: string;
  apellidos: string;
  email?: string;
  telefono: string; // ¡AHORA ES OBLIGATORIO!
  direccion: string;
};

export default function RegisterScreen({ navigation }: Props) {
  const route = useRoute<RegisterScreenRouteProp>();
  const initial = (route.params && route.params.form) ? (route.params.form as Partial<PersonFormData>) : {};

  const [form, setForm] = useState<PersonFormData>({
    tipo_cedula: (initial.tipo_cedula as any) ?? 'V',
    numero_cedula: initial.numero_cedula ?? '',
    rif: initial.rif ?? '',
    nombres: initial.nombres ?? '',
    apellidos: initial.apellidos ?? '',
    email: initial.email ?? '',
    telefono: initial.telefono ?? '', // ¡OBLIGATORIO!
    direccion: initial.direccion ?? '',
  });

  const [loading, setLoading] = useState(false);
  const [validationErrors, setValidationErrors] = useState<Record<string, string>>({});

  useEffect(() => {
    if (route.params?.form) {
      const f = route.params.form as Partial<PersonFormData>;
      setForm(prev => ({ ...prev, ...(f as Partial<PersonFormData>) }));
    }
  }, [route.params]);

  const screenWidth = Dimensions.get('window').width;
  const isWide = screenWidth >= 1000;

  const changeField = <K extends keyof PersonFormData>(key: K, value: PersonFormData[K]) => {
    setForm(prev => ({ ...prev, [key]: value }));
    setValidationErrors(prev => {
      const cp = { ...prev };
      delete cp[String(key)];
      return cp;
    });
  };

  const normalizeDigits = (s?: string) => (s ? s.replace(/\D+/g, '') : '');

  // Sanitizers and formatters
  const sanitizeName = (raw: string) => {
    const allowed = raw.replace(/[^A-Za-zÁÉÍÓÚáéíóúÑñ'’\-\s]/g, '');
    return allowed.replace(/\s{2,}/g, ' ').slice(0, 100);
  };

  const formatTelefono = (raw: string) => {
    const digits = raw.replace(/\D+/g, '').slice(0, 11);
    if (digits.length <= 4) return digits;
    return digits.slice(0, 4) + '-' + digits.slice(4);
  };

  const changeCedula = (raw: string) => {
    const nums = raw.replace(/\D+/g, '');
    const max = form.tipo_cedula === 'V' ? 8 : 20;
    const trimmed = nums.slice(0, max);
    changeField('numero_cedula', trimmed);
    if (form.tipo_cedula === 'V') {
      try {
        const rifGen = generarRif('V', trimmed);
        changeField('rif', rifGen);
      } catch { /* ignore */ }
    }
  };

  const changeRif = (raw: string) => {
    const up = raw.toUpperCase().replace(/[^A-Z0-9-]/g, '').slice(0, 14);
    changeField('rif', up);
  };

  // Validations ACTUALIZADAS
  const validCedula = () => {
    const num = normalizeDigits(form.numero_cedula);
    if (form.tipo_cedula === 'V') return num.length >= 6 && num.length <= 8;
    return num.length >= 4 && num.length <= 20;
  };

  const validRif = () => {
    if (form.tipo_cedula !== 'V') return true;
    if (!form.rif) return false;
    const re = /^[A-Z]-\d{8}-\d{1}$/;
    return re.test(form.rif.trim());
  };

  const validEmail = () => {
    if (!form.email) return true; // Email es opcional en tu modelo
    const re = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return re.test(form.email.trim().toLowerCase());
  };

  const validTelefono = () => {
    // Teléfono es OBLIGATORIO - mínimo 7 dígitos
    const dig = normalizeDigits(form.telefono);
    return dig.length >= 7 && dig.length <= 11;
  };

  const validNames = () => !!(form.nombres && form.nombres.trim().length > 1 && form.apellidos && form.apellidos.trim().length > 1);
  
  const validDireccion = () => !!(form.direccion && form.direccion.trim().length > 6);
  
  const canSave = () => validCedula() && validNames() && validRif() && validEmail() && validTelefono() && validDireccion() && !loading;

  // RIF generator
  function calcularDigitoVerificador(rifBaseNumerico: string) {
    const multiplicadores = [4, 3, 2, 7, 6, 5, 4, 3, 2];
    let suma = 0;
    for (let i = 0; i < multiplicadores.length; i++) {
      suma += parseInt(rifBaseNumerico[i] || '0', 10) * multiplicadores[i];
    }
    const resto = suma % 11;
    const digito = 11 - resto;
    return digito === 10 || digito === 11 ? 0 : digito;
  }

  function generarRif(tipo: string, cedulaRaw: string) {
    const tipoMapeo: Record<string, number> = { V: 1, E: 2, J: 3, P: 4, G: 5 };
    const letra = (tipo || 'V').toUpperCase().charAt(0);
    const nums = (cedulaRaw || '').replace(/\D+/g, '').padStart(8, '0').slice(-8);
    const baseNumerico = `${tipoMapeo[letra]}${nums}`;
    const digito = calcularDigitoVerificador(baseNumerico);
    return `${letra}-${nums}-${digito}`;
  }

  // -----------------------------
  // GUARDADO CORREGIDO
  // -----------------------------
  const savePerson = async () => {
    // Validaciones del formulario
    setValidationErrors({});
    const errs: Record<string, string> = {};
    if (!validCedula()) errs.numero_cedula = 'Cédula inválida (revisar tipo/longitud).';
    if (!validNames()) errs.nombres = 'Ingrese nombres y apellidos válidos.';
    if (!validRif()) errs.rif = 'RIF inválido (ej: J-12345678-9).';
    if (!validEmail()) errs.email = 'Correo inválido.';
    if (!validTelefono()) errs.telefono = 'Teléfono inválido (mín. 7 dígitos).';
    if (!validDireccion()) errs.direccion = 'Dirección inválida (mín. 6 caracteres).';

    if (Object.keys(errs).length > 0) {
      setValidationErrors(errs);
      Alert.alert('Formulario incompleto', 'Por favor complete todos los campos correctamente.');
      return;
    }

    setLoading(true);

    try {
      const cedulaCompleta = `${form.tipo_cedula}${normalizeDigits(form.numero_cedula)}`;
      
      // PAYLOAD CORREGIDO - solo campos que el backend espera
      const payload = {
        tipo_cedula: form.tipo_cedula,
        numero_cedula: normalizeDigits(form.numero_cedula),
        nombres: form.nombres.trim(),
        apellidos: form.apellidos.trim(),
        email: form.email ? form.email.trim().toLowerCase() : '', // Se mapea a 'correo' en backend
        telefono: form.telefono.trim(), // ¡OBLIGATORIO!
        direccion: form.direccion.trim(),
        rif: form.rif ? form.rif.trim() : '',
      };

      console.log('📤 Enviando datos CORREGIDOS:', payload);

      const response = await api.post('/api/registrar_persona/', payload);
      
      // DIAGNÓSTICO MEJORADO
      console.log('🔍 RESPUESTA COMPLETA:', {
        status: response.status,
        statusText: response.statusText,
        data: response.data,
        dataType: typeof response.data,
      });

      // Verificar si la respuesta es HTML (error)
      if (typeof response.data === 'string') {
        console.log('❌ El backend devolvió HTML en lugar de JSON');
        console.log('📄 Contenido HTML (primeros 200 chars):', response.data.substring(0, 200));
        
        Alert.alert(
          'Error del Servidor', 
          'El servidor respondió con una página de error. Revisa los logs del backend.'
        );
        return;
      }

      // Si es objeto JSON, procesar respuesta
      if (typeof response.data === 'object') {
        if (response.data.error) {
          // Error del backend
          Alert.alert('Error', response.data.error);
          return;
        }
        
        if (response.status === 201) {
          // ¡ÉXITO!
          const personaCreada = response.data;
          console.log('✅ Persona creada exitosamente:', personaCreada);
          
          Alert.alert(
            '¡Éxito!', 
            `Persona ${personaCreada.nombres} ${personaCreada.apellidos} registrada correctamente.`,
            [
              {
                text: 'Crear Usuario',
                onPress: () => navigation.navigate('RegisterUser', { person: personaCreada })
              },
              {
                text: 'Registrar Otra Persona',
                style: 'default',
                onPress: () => clearForm()
              }
            ]
          );
          
          clearForm();
        }
      }

    } catch (error: any) {
      console.error('❌ Error al crear persona:', error);
      
      let errorMessage = 'Error al registrar la persona';
      
      if (error.response) {
        const status = error.response.status;
        const data = error.response.data;
        
        if (status === 400) {
          errorMessage = data.error || 'Datos inválidos. Verifica la información.';
        } else if (status === 500) {
          errorMessage = 'Error interno del servidor. Intente más tarde.';
        } else if (status === 403) {
          errorMessage = 'Acceso denegado. El endpoint requiere configuración adicional.';
        } else {
          errorMessage = `Error ${status}: ${JSON.stringify(data)}`;
        }
      } else if (error.request) {
        errorMessage = 'No se pudo conectar al servidor. Verifica tu conexión.';
      }
      
      Alert.alert('Error', errorMessage);
    } finally {
      setLoading(false);
    }
  };

  const onTipoCedulaChange = (v: 'V' | 'E' | 'P') => {
    changeField('tipo_cedula', v);
    if (v !== 'V') changeField('rif', '');
    const max = v === 'V' ? 8 : 20;
    if (form.numero_cedula.length > max) changeField('numero_cedula', form.numero_cedula.slice(0, max));
  };

  const goBackToLogin = () => navigation.navigate('Login');
  
  const clearForm = () => {
    setForm({
      tipo_cedula: 'V',
      numero_cedula: '',
      rif: '',
      nombres: '',
      apellidos: '',
      email: '',
      telefono: '', // ¡NO OLVIDAR!
      direccion: '',
    });
    setValidationErrors({});
  };

  return (
    <KeyboardAvoidingView style={styles.wrapper} behavior={Platform.OS === 'ios' ? 'padding' : undefined}>
      <Image style={styles.bgImage} source={require('../../assets/frontImg.jpg')} blurRadius={4} />
      <View style={styles.overlay} />

      <ScrollView contentContainerStyle={styles.container}>
        <View style={[styles.card, isWide && { width: 920 }]}>
          <Text style={styles.title}>Registro de Persona</Text>
          <Text style={styles.subtitle}>
            Complete todos los campos obligatorios para registrar una nueva persona.
          </Text>

          <View style={styles.rowTwo}>
            <View style={styles.col}>
              <Text style={styles.label}>Tipo de cédula *</Text>
              <View style={styles.pickerWrapInline}>
                <Picker 
                  selectedValue={form.tipo_cedula} 
                  onValueChange={onTipoCedulaChange} 
                  mode="dropdown" 
                  style={styles.pickerInner}
                >
                  <Picker.Item label="Venezolano (V)" value="V" />
                  <Picker.Item label="Extranjero (E)" value="E" />
                  <Picker.Item label="Pasaporte (P)" value="P" />
                </Picker>
              </View>

              <Text style={styles.label}>Número de cédula *</Text>
              <TextInput
                placeholder="12345678"
                placeholderTextColor="#9aa"
                value={form.numero_cedula}
                onChangeText={changeCedula}
                keyboardType="numeric"
                style={styles.input}
                editable={!loading}
                maxLength={form.tipo_cedula === 'V' ? 8 : 20}
              />
              {validationErrors.numero_cedula && (
                <Text style={styles.errorSmall}>{validationErrors.numero_cedula}</Text>
              )}

              <Text style={[styles.label, { marginTop: 10 }]}>
                RIF {form.tipo_cedula !== 'V' ? '(deshabilitado para E/P)' : ''}
              </Text>
              <TextInput
                placeholder="J-12345678-9"
                placeholderTextColor="#9aa"
                value={form.rif}
                onChangeText={changeRif}
                style={[styles.input, form.tipo_cedula !== 'V' && styles.inputDisabled]}
                editable={form.tipo_cedula === 'V' && !loading}
                maxLength={14}
              />
              {validationErrors.rif && <Text style={styles.errorSmall}>{validationErrors.rif}</Text>}
            </View>

            <View style={styles.col}>
              <Text style={styles.label}>Nombres *</Text>
              <TextInput
                placeholder="Nombres"
                placeholderTextColor="#9aa"
                value={form.nombres}
                onChangeText={(t) => changeField('nombres', sanitizeName(t))}
                style={styles.input}
                editable={!loading}
                maxLength={100}
                autoCapitalize="words"
              />
              {validationErrors.nombres && <Text style={styles.errorSmall}>{validationErrors.nombres}</Text>}

              <Text style={styles.label}>Apellidos *</Text>
              <TextInput
                placeholder="Apellidos"
                placeholderTextColor="#9aa"
                value={form.apellidos}
                onChangeText={(t) => changeField('apellidos', sanitizeName(t))}
                style={styles.input}
                editable={!loading}
                maxLength={100}
                autoCapitalize="words"
              />
              {validationErrors.apellidos && <Text style={styles.errorSmall}>{validationErrors.apellidos}</Text>}

              <Text style={styles.label}>Teléfono *</Text>
              <TextInput
                placeholder="0412-1234567"
                placeholderTextColor="#9aa"
                value={form.telefono}
                onChangeText={(t) => changeField('telefono', formatTelefono(t))}
                style={styles.input}
                keyboardType="phone-pad"
                editable={!loading}
                maxLength={12}
              />
              {validationErrors.telefono && <Text style={styles.errorSmall}>{validationErrors.telefono}</Text>}

              <Text style={styles.label}>Correo electrónico</Text>
              <TextInput
                placeholder="correo@ejemplo.com"
                placeholderTextColor="#9aa"
                value={form.email}
                onChangeText={(t) => changeField('email', t.trim())}
                style={styles.input}
                keyboardType="email-address"
                editable={!loading}
                autoCapitalize="none"
                maxLength={128}
              />
              {validationErrors.email && <Text style={styles.errorSmall}>{validationErrors.email}</Text>}
            </View>
          </View>

          <View style={{ marginTop: 10 }}>
            <Text style={styles.label}>Dirección completa *</Text>
            <TextInput
              placeholder="Dirección completa (mínimo 6 caracteres)"
              placeholderTextColor="#9aa"
              value={form.direccion}
              onChangeText={(t) => changeField('direccion', t)}
              style={[styles.input, { height: 100, textAlignVertical: 'top' }]}
              multiline
              editable={!loading}
              maxLength={400}
            />
            {validationErrors.direccion && <Text style={styles.errorSmall}>{validationErrors.direccion}</Text>}
          </View>

          <View style={styles.buttonsRow}>
            <TouchableOpacity
              style={[styles.btn, styles.btnPrimary, !canSave() && styles.btnDisabled]}
              onPress={savePerson}
              disabled={!canSave()}
              activeOpacity={0.85}
            >
              {loading ? (
                <ActivityIndicator color="#fff" />
              ) : (
                <Text style={styles.btnText}>Registrar Persona</Text>
              )}
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

// Estilos (los mismos que antes)
const styles = StyleSheet.create({
  // ... (mantener los mismos estilos que tenías)
  wrapper: { flex: 1, backgroundColor: '#f3f6fb' },
  bgImage: { position: 'absolute', width: '100%', height: '100%', resizeMode: 'cover', top: 0, left: 0 },
  overlay: { ...StyleSheet.absoluteFillObject, backgroundColor: 'rgba(0,0,40,0.35)' },
  container: { padding: 18, alignItems: 'center', justifyContent: 'center', paddingVertical: 26 },
  card: {
    width: '100%', maxWidth: 920, backgroundColor: 'rgba(255,255,255,0.94)', borderRadius: 12, padding: 18,
    elevation: 8, shadowColor: '#000', shadowOpacity: 0.12, shadowOffset: { width: 0, height: 8 },
  },
  title: { fontSize: 20, fontWeight: '800', marginBottom: 4, color: '#222', textAlign: 'center' },
  subtitle: { fontSize: 14, color: '#666', marginBottom: 12, textAlign: 'center' },
  rowTwo: { flexDirection: 'row', gap: 12 },
  col: { flex: 1, paddingRight: 6 },
  label: { fontSize: 13, color: '#444', marginBottom: 6, fontWeight: '700' },
  input: {
    borderWidth: 1, borderColor: '#eef2ff', borderRadius: 8, paddingHorizontal: 12, height: 46,
    backgroundColor: '#fff', color: '#222',
  },
  inputDisabled: { backgroundColor: '#f2f4f8', color: '#9aa' },
  errorSmall: { color: '#e63946', fontSize: 12, marginTop: 6 },
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
    backgroundColor: '#fff', height: 46, justifyContent: 'center',
  },
  pickerInner: { height: 46 },
});