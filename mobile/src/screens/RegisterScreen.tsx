// src/screens/RegisterScreen.tsx - VERSIÓN MEJORADA Y RESPONSIVE (limites + KeyboardAvoiding)
import React, { useEffect, useRef, useState } from 'react';
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
  Modal as RNModal,
  NativeSyntheticEvent,
  TextInputSubmitEditingEventData,
} from 'react-native';
import type { StackNavigationProp } from '@react-navigation/stack';
import { RouteProp, useRoute } from '@react-navigation/native';
import api from '../api/api';

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
  correo?: string;
  telefono: string;
  direccion: string;
};

const { width: screenWidth } = Dimensions.get('window');
const isSmallScreen = screenWidth < 375;
const isMediumScreen = screenWidth >= 375 && screenWidth < 768;
const isLargeScreen = screenWidth >= 768;

export default function RegisterScreen({ navigation }: Props) {
  const route = useRoute<RegisterScreenRouteProp>();
  const initial = (route.params && route.params.form) ? (route.params.form as Partial<PersonFormData>) : {};

  const [form, setForm] = useState<PersonFormData>({
    tipo_cedula: (initial.tipo_cedula as any) ?? 'V',
    numero_cedula: initial.numero_cedula ?? '',
    rif: initial.rif ?? '',
    nombres: initial.nombres ?? '',
    apellidos: initial.apellidos ?? '',
    correo: initial.correo ?? '',
    telefono: initial.telefono ?? '',
    direccion: initial.direccion ?? '',
  });

  const [loading, setLoading] = useState(false);
  const [validationErrors, setValidationErrors] = useState<Record<string, string>>({});

  // estado para modal del select tipo_cedula
  const [showTipoCedulaModal, setShowTipoCedulaModal] = useState(false);

  // refs para navegación entre inputs (mejora UX cuando presionas "next")
  const apellidoRef = useRef<TextInput | null>(null);
  const telefonoRef = useRef<TextInput | null>(null);
  const correoRef = useRef<TextInput | null>(null);
  const direccionRef = useRef<TextInput | null>(null);

  useEffect(() => {
    if (route.params?.form) {
      const f = route.params.form as Partial<PersonFormData>;
      setForm(prev => ({ ...prev, ...(f as Partial<PersonFormData>) }));
    }
  }, [route.params]);

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

  // NUEVO: handler robusto para numero_cedula que aplica limites y saneamiento según tipo
  const handleNumeroCedulaChange = (raw: string) => {
    if (form.tipo_cedula === 'V') {
      // solo dígitos, max 8
      const nums = raw.replace(/\D+/g, '').slice(0, 8);
      changeField('numero_cedula', nums);
      if (nums.length >= 6) {
        try { changeField('rif', generarRif('V', nums)); } catch { /* ignore */ }
      } else {
        // limpiar rif si cedula quedó corta
        changeField('rif', '');
      }
    } else {
      // E / P -> alfanumérico, mayúsculas, max 20
      const cleaned = raw.replace(/[^A-Za-z0-9]/g, '').slice(0, 20).toUpperCase();
      changeField('numero_cedula', cleaned);
      // no tocar rif para E/P (debe permanecer vacío)
    }
  };

  const changeRif = (raw: string) => {
    // Solo permitir editar RIF para tipo V
    if (form.tipo_cedula !== 'V') return;
    const up = raw.toUpperCase().replace(/[^A-Z0-9-]/g, '').slice(0, 14);
    changeField('rif', up);
  };

  // Validaciones MEJORADAS
  const validCedula = () => {
    const num = normalizeDigits(form.numero_cedula);
    if (form.tipo_cedula === 'V') return num.length >= 6 && num.length <= 8;
    // para E/P permitimos entre 4 y 20 caracteres alfanuméricos
    const alt = (form.numero_cedula ?? '').replace(/[^A-Za-z0-9]/g, '');
    return alt.length >= 4 && alt.length <= 20;
  };

  const validRif = () => {
    if (form.tipo_cedula !== 'V') return true;
    if (!form.rif || form.rif.trim() === '') return false;
    const re = /^[A-Z]-\d{8}-\d{1}$/;
    return re.test(form.rif.trim());
  };

  const validEmail = () => {
    if (!form.correo || form.correo.trim() === '') return true;
    const re = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return re.test(form.correo.trim().toLowerCase());
  };

  const validTelefono = () => {
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

  // GUARDADO MEJORADO
  const savePerson = async () => {
    setValidationErrors({});
    const errs: Record<string, string> = {};

    if (!validCedula()) errs.numero_cedula = 'Cédula inválida (revisar tipo/longitud).';
    if (!validNames()) errs.nombres = 'Ingrese nombres y apellidos válidos.';
    if (!validRif()) errs.rif = 'RIF inválido (ej: V-12345678-9).';
    if (!validEmail()) errs.correo = 'Correo inválido.';
    if (!validTelefono()) errs.telefono = 'Teléfono inválido (mín. 7 dígitos).';
    if (!validDireccion()) errs.direccion = 'Dirección inválida (mín. 6 caracteres).';

    if (Object.keys(errs).length > 0) {
      setValidationErrors(errs);
      Alert.alert('Formulario incompleto', 'Por favor complete todos los campos correctamente.');
      return;
    }

    setLoading(true);

    try {
      const payload = {
        tipo_cedula: form.tipo_cedula,
        numero_cedula: normalizeDigits(form.numero_cedula),
        nombres: form.nombres.trim(),
        apellidos: form.apellidos.trim(),
        correo: form.correo ? form.correo.trim().toLowerCase() : '',
        telefono: form.telefono.trim(),
        direccion: form.direccion.trim(),
        rif: form.tipo_cedula === 'V' ? (form.rif ? form.rif.trim() : '') : ''
      };

      console.log('📤 Enviando datos CORREGIDOS:', payload);

      const response = await api.post('/api/registrar_persona/', payload);

      if (typeof response.data === 'string') {
        console.log('❌ El backend devolvió HTML en lugar de JSON');
        Alert.alert(
          'Error del Servidor',
          'El servidor respondió con una página de error. Revisa los logs del backend.'
        );
        return;
      }

      if (typeof response.data === 'object') {
        if (response.data.error) {
          Alert.alert('Error', response.data.error);
          return;
        }

        if (response.status === 201) {
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
          if (data.includes?.('RIF_DUPLICADO') || data.codigo === 'RIF_DUPLICADO') {
            errorMessage = 'Error del sistema: Ya existe un registro con RIF vacío. Contacte al administrador.';
          } else {
            errorMessage = 'Error interno del servidor. Intente más tarde.';
          }
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

    // Limpiar RIF para E/P
    if (v !== 'V') {
      changeField('rif', '');
    } else {
      // Para V, generar RIF si aplica
      if (form.numero_cedula && form.numero_cedula.length >= 6) {
        try {
          const rifGen = generarRif('V', form.numero_cedula);
          changeField('rif', rifGen);
        } catch { /* ignore */ }
      }
    }

    const max = v === 'V' ? 8 : 20;
    if (form.numero_cedula.length > max) {
      // truncamos inmediatamente para que no quede texto infinito
      changeField('numero_cedula', form.numero_cedula.slice(0, max));
    }
  };

  const goBackToLogin = () => navigation.navigate('Login');

  const clearForm = () => {
    setForm({
      tipo_cedula: 'V',
      numero_cedula: '',
      rif: '',
      nombres: '',
      apellidos: '',
      correo: '',
      telefono: '',
      direccion: '',
    });
    setValidationErrors({});
  };

  // Cálculos responsivos
  const getCardWidth = () => {
    if (isSmallScreen) return '95%';
    if (isMediumScreen) return '90%';
    return Math.min(920, screenWidth * 0.85);
  };

  const cardWidth = getCardWidth();

  // keyboardVerticalOffset para que KeyboardAvoiding sitúe correctamente (ajusta si tienes header)
  const keyboardVerticalOffset = Platform.OS === 'ios' ? 60 : 80;

  // helper para avanzar focus con "next"
    const onSubmitNext = (nextRef?: React.RefObject<TextInput | null>) => (_e?: NativeSyntheticEvent<TextInputSubmitEditingEventData>) => {
      if (nextRef && nextRef.current) {
        const curr = nextRef.current;
        if (curr) curr.focus();
      }
    };

  return (
    <KeyboardAvoidingView
      style={styles.wrapper}
      behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
      keyboardVerticalOffset={keyboardVerticalOffset}
    >
      <Image style={styles.bgImage} source={require('../../assets/frontImg.jpg')} blurRadius={4} />
      <View style={styles.overlay} />

      <ScrollView
        contentContainerStyle={[styles.container, { paddingBottom: 260 }]} // espacio extra para teclado
        showsVerticalScrollIndicator={false}
        keyboardShouldPersistTaps="handled"
        keyboardDismissMode="interactive"
      >
        <View style={[styles.card, { width: cardWidth }]}>
          <Text style={[styles.title, isSmallScreen && styles.titleSmall]}>Registro de Persona</Text>
          <Text style={[styles.subtitle, isSmallScreen && styles.subtitleSmall]}>
            Complete todos los campos obligatorios para registrar una nueva persona.
          </Text>

          <View style={[styles.rowTwo, isSmallScreen && styles.rowTwoSmall]}>
            <View style={[styles.col, isSmallScreen && styles.colSmall]}>
              <Text style={[styles.label, isSmallScreen && styles.labelSmall]}>Tipo de cédula *</Text>

              {/* CUSTOM SELECT (modal) en lugar de Picker */}
              <TouchableOpacity
                style={[styles.customSelectButton, isSmallScreen && styles.customSelectButtonSmall]}
                onPress={() => setShowTipoCedulaModal(true)}
                disabled={loading}
              >
                <Text style={[styles.customSelectText, isSmallScreen && styles.customSelectTextSmall]}>
                  {form.tipo_cedula === 'V' ? 'Venezolano (V)' :
                    form.tipo_cedula === 'E' ? 'Extranjero (E)' :
                    form.tipo_cedula === 'P' ? 'Pasaporte (P)' : 'Seleccione tipo de cédula'}
                </Text>
                <Text style={[styles.customSelectArrow, isSmallScreen && styles.customSelectArrowSmall]}>▼</Text>
              </TouchableOpacity>

              <Text style={[styles.label, isSmallScreen && styles.labelSmall, { marginTop: 10 }]}>Número de cédula *</Text>
              <TextInput
                placeholder={form.tipo_cedula === 'V' ? '12345678' : 'Alfanumérico (máx 20)'}
                placeholderTextColor="#9aa"
                value={form.numero_cedula}
                onChangeText={handleNumeroCedulaChange}
                keyboardType={form.tipo_cedula === 'V' ? 'number-pad' : 'default'}
                style={[styles.input, isSmallScreen && styles.inputSmall]}
                editable={!loading}
                maxLength={form.tipo_cedula === 'V' ? 8 : 20}
                returnKeyType="next"
                onSubmitEditing={onSubmitNext(apellidoRef)}
              />
              {validationErrors.numero_cedula && (
                <Text style={[styles.errorSmall, isSmallScreen && styles.errorSmallText]}>{validationErrors.numero_cedula}</Text>
              )}

              <Text style={[styles.label, isSmallScreen && styles.labelSmall, { marginTop: 10 }]}>
                RIF {form.tipo_cedula !== 'V' ? '(no aplica para E/P)' : '*'}
              </Text>
              <TextInput
                placeholder={form.tipo_cedula === 'V' ? "V-12345678-9" : "No aplica"}
                placeholderTextColor="#9aa"
                value={form.rif}
                onChangeText={changeRif}
                style={[
                  styles.input,
                  isSmallScreen && styles.inputSmall,
                  form.tipo_cedula !== 'V' && styles.inputDisabled
                ]}
                editable={form.tipo_cedula === 'V' && !loading}
                maxLength={14}
                returnKeyType="next"
                onSubmitEditing={onSubmitNext(telefonoRef)}
              />
              {validationErrors.rif && (
                <Text style={[styles.errorSmall, isSmallScreen && styles.errorSmallText]}>{validationErrors.rif}</Text>
              )}
            </View>

            <View style={[styles.col, isSmallScreen && styles.colSmall]}>
              <Text style={[styles.label, isSmallScreen && styles.labelSmall]}>Nombres *</Text>
              <TextInput
                placeholder="Nombres"
                placeholderTextColor="#9aa"
                value={form.nombres}
                onChangeText={(t) => changeField('nombres', sanitizeName(t))}
                style={[styles.input, isSmallScreen && styles.inputSmall]}
                editable={!loading}
                maxLength={100}
                autoCapitalize="words"
                returnKeyType="next"
                onSubmitEditing={onSubmitNext(apellidoRef)}
              />
              {validationErrors.nombres && (
                <Text style={[styles.errorSmall, isSmallScreen && styles.errorSmallText]}>{validationErrors.nombres}</Text>
              )}

              <Text style={[styles.label, isSmallScreen && styles.labelSmall]}>Apellidos *</Text>
              <TextInput
                ref={apellidoRef}
                placeholder="Apellidos"
                placeholderTextColor="#9aa"
                value={form.apellidos}
                onChangeText={(t) => changeField('apellidos', sanitizeName(t))}
                style={[styles.input, isSmallScreen && styles.inputSmall]}
                editable={!loading}
                maxLength={100}
                autoCapitalize="words"
                returnKeyType="next"
                onSubmitEditing={onSubmitNext(telefonoRef)}
              />
              {validationErrors.apellidos && (
                <Text style={[styles.errorSmall, isSmallScreen && styles.errorSmallText]}>{validationErrors.apellidos}</Text>
              )}

              <Text style={[styles.label, isSmallScreen && styles.labelSmall]}>Teléfono *</Text>
              <TextInput
                ref={telefonoRef}
                placeholder="0412-1234567"
                placeholderTextColor="#9aa"
                value={form.telefono}
                onChangeText={(t) => changeField('telefono', formatTelefono(t))}
                style={[styles.input, isSmallScreen && styles.inputSmall]}
                keyboardType="phone-pad"
                editable={!loading}
                maxLength={12}
                returnKeyType="next"
                onSubmitEditing={onSubmitNext(correoRef)}
              />
              {validationErrors.telefono && (
                <Text style={[styles.errorSmall, isSmallScreen && styles.errorSmallText]}>{validationErrors.telefono}</Text>
              )}

              <Text style={[styles.label, isSmallScreen && styles.labelSmall]}>Correo electrónico</Text>
              <TextInput
                ref={correoRef}
                placeholder="correo@ejemplo.com"
                placeholderTextColor="#9aa"
                value={form.correo}
                onChangeText={(t) => changeField('correo', t.trim())}
                style={[styles.input, isSmallScreen && styles.inputSmall]}
                keyboardType="email-address"
                editable={!loading}
                autoCapitalize="none"
                maxLength={128}
                returnKeyType="next"
                onSubmitEditing={onSubmitNext(direccionRef)}
              />
              {validationErrors.correo && (
                <Text style={[styles.errorSmall, isSmallScreen && styles.errorSmallText]}>{validationErrors.correo}</Text>
              )}
            </View>
          </View>

          <View style={{ marginTop: isSmallScreen ? 8 : 10 }}>
            <Text style={[styles.label, isSmallScreen && styles.labelSmall]}>Dirección completa *</Text>
            <TextInput
              ref={direccionRef}
              placeholder="Dirección completa (mínimo 6 caracteres)"
              placeholderTextColor="#9aa"
              value={form.direccion}
              onChangeText={(t) => changeField('direccion', t)}
              style={[
                styles.input,
                isSmallScreen && styles.inputSmall,
                { height: isSmallScreen ? 80 : 100, textAlignVertical: 'top' }
              ]}
              multiline
              editable={!loading}
              maxLength={400}
            />
            {validationErrors.direccion && (
              <Text style={[styles.errorSmall, isSmallScreen && styles.errorSmallText]}>{validationErrors.direccion}</Text>
            )}
          </View>

          <View style={[styles.buttonsRow, isSmallScreen && styles.buttonsRowSmall]}>
            <TouchableOpacity
              style={[styles.btn, styles.btnPrimary, !canSave() && styles.btnDisabled, isSmallScreen && styles.btnSmall]}
              onPress={savePerson}
              disabled={!canSave()}
              activeOpacity={0.85}
            >
              {loading ? (
                <ActivityIndicator color="#fff" size={isSmallScreen ? 'small' : 'large'} />
              ) : (
                <Text style={[styles.btnText, isSmallScreen && styles.btnTextSmall]}>Registrar Persona</Text>
              )}
            </TouchableOpacity>
          </View>

          <View style={[styles.footerRow, isSmallScreen && styles.footerRowSmall]}>
            <TouchableOpacity onPress={goBackToLogin} style={styles.linkBtn}>
              <Text style={[styles.linkText, isSmallScreen && styles.linkTextSmall]}>Volver al inicio de sesión</Text>
            </TouchableOpacity>

            <TouchableOpacity onPress={clearForm} style={styles.linkBtn}>
              <Text style={[styles.linkText, isSmallScreen && styles.linkTextSmall]}>Limpiar formulario</Text>
            </TouchableOpacity>
          </View>

          <Text style={[styles.requiredHint, isSmallScreen && styles.requiredHintSmall]}>* Campos obligatorios</Text>
        </View>

        {/* MODAL PARA TIPO DE CÉDULA */}
        <RNModal
          visible={showTipoCedulaModal}
          transparent={true}
          animationType="slide"
          onRequestClose={() => setShowTipoCedulaModal(false)}
        >
          <View style={styles.modalOverlay}>
            <View style={[styles.modalContent, isSmallScreen && styles.modalContentSmall]}>
              <Text style={[styles.modalTitle, isSmallScreen && styles.modalTitleSmall]}>
                Seleccionar Tipo de Cédula
              </Text>

              {['V', 'E', 'P'].map((tipo) => (
                <TouchableOpacity
                  key={tipo}
                  style={[
                    styles.modalOption,
                    isSmallScreen && styles.modalOptionSmall,
                    form.tipo_cedula === tipo && styles.modalOptionSelected
                  ]}
                  onPress={() => {
                    onTipoCedulaChange(tipo as 'V' | 'E' | 'P');
                    setShowTipoCedulaModal(false);
                  }}
                >
                  <Text style={[
                    styles.modalOptionText,
                    isSmallScreen && styles.modalOptionTextSmall,
                    form.tipo_cedula === tipo && styles.modalOptionTextSelected
                  ]}>
                    {tipo === 'V' ? 'Venezolano (V)' :
                      tipo === 'E' ? 'Extranjero (E)' : 'Pasaporte (P)'}
                  </Text>
                </TouchableOpacity>
              ))}

              <TouchableOpacity
                style={[styles.modalCloseButton, isSmallScreen && styles.modalCloseButtonSmall]}
                onPress={() => setShowTipoCedulaModal(false)}
              >
                <Text style={[styles.modalCloseText, isSmallScreen && styles.modalCloseTextSmall]}>Cancelar</Text>
              </TouchableOpacity>
            </View>
          </View>
        </RNModal>
      </ScrollView>
    </KeyboardAvoidingView>
  );
}

// ESTILOS (idénticos a los previos, con select + modal)
const styles = StyleSheet.create({
  wrapper: {
    flex: 1,
    backgroundColor: '#f3f6fb'
  },
  bgImage: {
    position: 'absolute',
    width: '100%',
    height: '100%',
    resizeMode: 'cover',
    top: 0,
    left: 0
  },
  overlay: {
    ...StyleSheet.absoluteFillObject,
    backgroundColor: 'rgba(0,0,40,0.35)'
  },
  container: {
    padding: 18,
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: 26,
    minHeight: '100%',
  },
  card: {
    backgroundColor: 'rgba(255,255,255,0.94)',
    borderRadius: 12,
    padding: 18,
    elevation: 8,
    shadowColor: '#000',
    shadowOpacity: 0.12,
    shadowOffset: { width: 0, height: 8 },
    maxWidth: '100%',
  },
  title: {
    fontSize: 20,
    fontWeight: '800',
    marginBottom: 4,
    color: '#222',
    textAlign: 'center'
  },
  titleSmall: {
    fontSize: 18,
  },
  subtitle: {
    fontSize: 14,
    color: '#666',
    marginBottom: 12,
    textAlign: 'center'
  },
  subtitleSmall: {
    fontSize: 12,
  },
  rowTwo: {
    flexDirection: 'row',
    gap: 12
  },
  rowTwoSmall: {
    flexDirection: 'column',
    gap: 8,
  },
  col: {
    flex: 1,
    paddingRight: 6
  },
  colSmall: {
    paddingRight: 0,
    width: '100%',
  },
  label: {
    fontSize: 13,
    color: '#444',
    marginBottom: 6,
    fontWeight: '700'
  },
  labelSmall: {
    fontSize: 12,
  },
  input: {
    borderWidth: 1,
    borderColor: '#eef2ff',
    borderRadius: 8,
    paddingHorizontal: 12,
    height: 46,
    backgroundColor: '#fff',
    color: '#222',
  },
  inputSmall: {
    height: 42,
    fontSize: 14,
  },
  inputDisabled: {
    backgroundColor: '#f2f4f8',
    color: '#9aa'
  },
  errorSmall: {
    color: '#e63946',
    fontSize: 12,
    marginTop: 6
  },
  errorSmallText: {
    fontSize: 11,
  },
  buttonsRow: {
    flexDirection: 'row',
    justifyContent: 'center',
    marginTop: 12
  },
  buttonsRowSmall: {
    marginTop: 10,
  },
  btn: {
    paddingVertical: 12,
    borderRadius: 10,
    alignItems: 'center',
    minWidth: 200
  },
  btnSmall: {
    paddingVertical: 10,
    minWidth: 160,
  },
  btnPrimary: {
    backgroundColor: '#1f6fff'
  },
  btnDisabled: {
    backgroundColor: '#a0a0a0',
    opacity: 0.6
  },
  btnText: {
    color: '#fff',
    fontWeight: '800',
    fontSize: 16
  },
  btnTextSmall: {
    fontSize: 14,
  },
  footerRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginTop: 14
  },
  footerRowSmall: {
    flexDirection: 'column',
    alignItems: 'center',
    gap: 8,
  },
  linkBtn: {
    padding: 6
  },
  linkText: {
    color: '#4f8cff',
    fontWeight: '700'
  },
  linkTextSmall: {
    fontSize: 12,
  },
  requiredHint: {
    fontSize: 12,
    color: '#666',
    marginTop: 10,
    textAlign: 'center',
    fontStyle: 'italic'
  },
  requiredHintSmall: {
    fontSize: 11,
  },

  // custom select styles
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
  customSelectButtonSmall: {
    height: 42,
    paddingHorizontal: 10,
  },
  customSelectText: {
    fontSize: 16,
    color: '#222',
    flex: 1,
  },
  customSelectTextSmall: {
    fontSize: 14,
  },
  customSelectPlaceholder: {
    color: '#9aa',
  },
  customSelectArrow: {
    fontSize: 12,
    color: '#4f8cff',
    marginLeft: 8,
  },
  customSelectArrowSmall: {
    fontSize: 10,
  },

  // modal styles
  modalOverlay: {
    flex: 1,
    backgroundColor: 'rgba(0,0,0,0.5)',
    justifyContent: 'center',
    alignItems: 'center',
    padding: 20,
  },
  modalContent: {
    backgroundColor: 'white',
    borderRadius: 12,
    padding: 20,
    width: '90%',
    maxHeight: '80%',
  },
  modalContentSmall: {
    padding: 16,
    width: '95%',
  },
  modalTitle: {
    fontSize: 18,
    fontWeight: '700',
    marginBottom: 16,
    textAlign: 'center',
    color: '#222',
  },
  modalTitleSmall: {
    fontSize: 16,
    marginBottom: 12,
  },
  modalOption: {
    paddingVertical: 12,
    paddingHorizontal: 16,
    borderBottomWidth: 1,
    borderBottomColor: '#f0f0f0',
  },
  modalOptionSmall: {
    paddingVertical: 10,
    paddingHorizontal: 12,
  },
  modalOptionSelected: {
    backgroundColor: '#eef2ff',
  },
  modalOptionText: {
    fontSize: 16,
    color: '#222',
  },
  modalOptionTextSmall: {
    fontSize: 14,
    lineHeight: 18,
  },
  modalOptionTextSelected: {
    color: '#1f6fff',
    fontWeight: '600',
  },
  modalCloseButton: {
    marginTop: 16,
    paddingVertical: 12,
    backgroundColor: '#6c757d',
    borderRadius: 8,
    alignItems: 'center',
  },
  modalCloseButtonSmall: {
    paddingVertical: 10,
  },
  modalCloseText: {
    color: 'white',
    fontSize: 16,
    fontWeight: '600',
  },
  modalCloseTextSmall: {
    fontSize: 14,
  },
});
