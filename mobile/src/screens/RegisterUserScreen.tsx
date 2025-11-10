// src/screens/RegisterUserScreen.tsx - VERSIÓN COMPLETA CON MODALES PARA SELECTS
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
  useWindowDimensions,
  Modal as RNModal, // 👈 NUEVO: Importar Modal
} from 'react-native';
import type { StackNavigationProp } from '@react-navigation/stack';
import { RouteProp, useRoute } from '@react-navigation/native';
import api from '../api/api';

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
  numero_cedula: string;
  password: string;
  confirmPassword: string;
  preguntaSeguridad: string;
  respuestaSeguridad: string;
  nombres?: string;
};

export default function RegisterUserScreen({ navigation }: Props) {
  const { width, height } = useWindowDimensions();
  const isSmallScreen = width < 375;
  const isMediumScreen = width >= 375 && width < 768;
  const isLargeScreen = width >= 768;

  // 👇 NUEVOS ESTADOS PARA MODALES
  const [showTipoCedulaModal, setShowTipoCedulaModal] = useState(false);
  const [showPreguntaModal, setShowPreguntaModal] = useState(false);

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
    
    if (!numero || numero.length < 6) 
      newErrors.cedula = 'Número de cédula inválido (mín. 6 dígitos).';
    if (!form.password || form.password.length < 8) 
      newErrors.password = 'La contraseña debe tener al menos 8 caracteres.';
    if (form.password !== form.confirmPassword) 
      newErrors.confirmPassword = 'Las contraseñas no coinciden.';
    if (!form.preguntaSeguridad) 
      newErrors.preguntaSeguridad = 'Seleccione una pregunta de seguridad.';
    if (!form.respuestaSeguridad || !form.respuestaSeguridad.trim()) 
      newErrors.respuestaSeguridad = 'La respuesta es requerida.';
    
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
        cedula: buildCedulaFormatted(),
        password: form.password,
        preguntaSeguridad: form.preguntaSeguridad,
        respuestaSeguridad: form.respuestaSeguridad.trim(),
      };

      console.log('📤 Enviando para crear usuario:', payload);
      const response = await api.post('/api/registrar_usuario/', payload);

      if (response.status === 201 || response.status === 200) {
        const mensaje = (response.data && (response.data.mensaje || response.data.message)) ?? '✅ Usuario creado correctamente';
        
        Alert.alert(
          '¡Éxito!', 
          `${mensaje}\n\nAhora puede iniciar sesión con su cédula y contraseña.`,
          [
            { 
              text: 'Ir a Iniciar Sesión', 
              onPress: () => navigation.replace('Login')
            },
          ]
        );
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

  const getCardWidth = () => {
    if (isSmallScreen) return '95%';
    if (isMediumScreen) return '90%';
    if (isLargeScreen) return Math.min(920, width * 0.85);
    return '90%';
  };

  const cardWidth = getCardWidth();

  const renderFormContent = () => {
    if (isLargeScreen) {
      return (
        <View style={styles.twoColumnsLayout}>
          {/* Columna Izquierda */}
          <View style={styles.column}>
            <View style={styles.formSection}>
              <Text style={[styles.sectionTitle, isSmallScreen && styles.sectionTitleSmall]}>
                Información de Identificación
              </Text>
              
              {/* 👇 SELECTOR DE TIPO CÉDULA CON MODAL */}
              <View style={styles.fieldContainer}>
                <Text style={[styles.label, isSmallScreen && styles.labelSmall]}>Tipo de cédula *</Text>
                <TouchableOpacity 
                  style={[styles.customSelectButton, isSmallScreen && styles.customSelectButtonSmall]}
                  onPress={() => setShowTipoCedulaModal(true)}
                  disabled={loading}
                >
                  <Text style={[
                    styles.customSelectText, 
                    isSmallScreen && styles.customSelectTextSmall,
                    !form.tipo_cedula && styles.customSelectPlaceholder
                  ]}>
                    {form.tipo_cedula === 'V' ? 'Venezolano (V)' : 
                     form.tipo_cedula === 'E' ? 'Extranjero (E)' : 
                     form.tipo_cedula === 'P' ? 'Pasaporte (P)' : 'Seleccione tipo de cédula'}
                  </Text>
                  <Text style={[styles.customSelectArrow, isSmallScreen && styles.customSelectArrowSmall]}>▼</Text>
                </TouchableOpacity>
              </View>

              <View style={styles.fieldContainer}>
                <Text style={[styles.label, isSmallScreen && styles.labelSmall]}>Número de cédula *</Text>
                <TextInput
                  style={[styles.input, isSmallScreen && styles.inputSmall]}
                  placeholder="Ej: 12345678"
                  placeholderTextColor="#9aa"
                  value={form.numero_cedula}
                  onChangeText={(v) => changeField('numero_cedula', v.replace(/\D+/g, ''))}
                  editable={!loading}
                  keyboardType="numeric"
                  returnKeyType="next"
                  maxLength={20}
                />
                {errors.cedula && (
                  <Text style={[styles.errorSmall, isSmallScreen && styles.errorSmallText]}>
                    {errors.cedula}
                  </Text>
                )}
              </View>

              <View style={styles.fieldContainer}>
                <Text style={[styles.label, isSmallScreen && styles.labelSmall]}>Cédula completa</Text>
                <View style={[styles.cedulaCompletaContainer, isSmallScreen && styles.cedulaCompletaContainerSmall]}>
                  <Text style={[styles.cedulaCompleta, isSmallScreen && styles.cedulaCompletaSmall]}>
                    {buildCedulaFormatted()}
                  </Text>
                </View>
                <Text style={[styles.helpText, isSmallScreen && styles.helpTextSmall]}>
                  Esta será su nombre de usuario para iniciar sesión
                </Text>
              </View>
            </View>
          </View>

          {/* Columna Derecha */}
          <View style={styles.column}>
            <View style={styles.formSection}>
              <Text style={[styles.sectionTitle, isSmallScreen && styles.sectionTitleSmall]}>
                Contraseña de Seguridad
              </Text>

              <View style={styles.fieldContainer}>
                <Text style={[styles.label, isSmallScreen && styles.labelSmall]}>Contraseña *</Text>
                <TextInput
                  style={[styles.input, isSmallScreen && styles.inputSmall]}
                  placeholder="Mínimo 8 caracteres"
                  placeholderTextColor="#9aa"
                  value={form.password}
                  onChangeText={(v) => changeField('password', v)}
                  secureTextEntry
                  editable={!loading}
                />
                {errors.password && (
                  <Text style={[styles.errorSmall, isSmallScreen && styles.errorSmallText]}>
                    {errors.password}
                  </Text>
                )}
                <Text style={[styles.helpText, isSmallScreen && styles.helpTextSmall]}>
                  La contraseña debe tener al menos 8 caracteres
                </Text>
              </View>

              <View style={styles.fieldContainer}>
                <Text style={[styles.label, isSmallScreen && styles.labelSmall]}>Confirmar Contraseña *</Text>
                <TextInput
                  style={[styles.input, isSmallScreen && styles.inputSmall]}
                  placeholder="Repita la contraseña"
                  placeholderTextColor="#9aa"
                  value={form.confirmPassword}
                  onChangeText={(v) => changeField('confirmPassword', v)}
                  secureTextEntry
                  editable={!loading}
                />
                {errors.confirmPassword && (
                  <Text style={[styles.errorSmall, isSmallScreen && styles.errorSmallText]}>
                    {errors.confirmPassword}
                  </Text>
                )}
              </View>
            </View>

            <View style={styles.formSection}>
              <Text style={[styles.sectionTitle, isSmallScreen && styles.sectionTitleSmall]}>
                Pregunta de Seguridad
              </Text>

              {/* 👇 SELECTOR DE PREGUNTA CON MODAL */}
              <View style={styles.fieldContainer}>
                <Text style={[styles.label, isSmallScreen && styles.labelSmall]}>Pregunta de Seguridad *</Text>
                <TouchableOpacity 
                  style={[styles.customSelectButton, isSmallScreen && styles.customSelectButtonSmall]}
                  onPress={() => setShowPreguntaModal(true)}
                  disabled={loading}
                >
                  <Text 
                    style={[
                      styles.customSelectText, 
                      isSmallScreen && styles.customSelectTextSmall,
                      !form.preguntaSeguridad && styles.customSelectPlaceholder,
                      { flex: 1 }
                    ]}
                    numberOfLines={1}
                    ellipsizeMode="tail"
                  >
                    {form.preguntaSeguridad || 'Seleccione una pregunta de seguridad'}
                  </Text>
                  <Text style={[styles.customSelectArrow, isSmallScreen && styles.customSelectArrowSmall]}>▼</Text>
                </TouchableOpacity>
                {errors.preguntaSeguridad && (
                  <Text style={[styles.errorSmall, isSmallScreen && styles.errorSmallText]}>
                    {errors.preguntaSeguridad}
                  </Text>
                )}
              </View>

              <View style={styles.fieldContainer}>
                <Text style={[styles.label, isSmallScreen && styles.labelSmall]}>Respuesta de Seguridad *</Text>
                <TextInput
                  style={[styles.input, isSmallScreen && styles.inputSmall]}
                  placeholder="Su respuesta secreta"
                  placeholderTextColor="#9aa"
                  value={form.respuestaSeguridad}
                  onChangeText={(v) => changeField('respuestaSeguridad', v)}
                  editable={!loading}
                />
                {errors.respuestaSeguridad && (
                  <Text style={[styles.errorSmall, isSmallScreen && styles.errorSmallText]}>
                    {errors.respuestaSeguridad}
                  </Text>
                )}
                <Text style={[styles.helpText, isSmallScreen && styles.helpTextSmall]}>
                  Esta respuesta le ayudará a recuperar su cuenta si olvida la contraseña
                </Text>
              </View>
            </View>
          </View>
        </View>
      );
    } else {
      return (
        <View style={[styles.formContent, isSmallScreen && styles.formContentSmall]}>
          <View style={styles.formSection}>
            <Text style={[styles.sectionTitle, isSmallScreen && styles.sectionTitleSmall]}>
              Información de Identificación
            </Text>
            
            {/* 👇 SELECTOR DE TIPO CÉDULA CON MODAL */}
            <View style={styles.fieldContainer}>
              <Text style={[styles.label, isSmallScreen && styles.labelSmall]}>Tipo de cédula *</Text>
              <TouchableOpacity 
                style={[styles.customSelectButton, isSmallScreen && styles.customSelectButtonSmall]}
                onPress={() => setShowTipoCedulaModal(true)}
                disabled={loading}
              >
                <Text style={[
                  styles.customSelectText, 
                  isSmallScreen && styles.customSelectTextSmall,
                  !form.tipo_cedula && styles.customSelectPlaceholder
                ]}>
                  {form.tipo_cedula === 'V' ? 'Venezolano (V)' : 
                   form.tipo_cedula === 'E' ? 'Extranjero (E)' : 
                   form.tipo_cedula === 'P' ? 'Pasaporte (P)' : 'Seleccione tipo de cédula'}
                </Text>
                <Text style={[styles.customSelectArrow, isSmallScreen && styles.customSelectArrowSmall]}>▼</Text>
              </TouchableOpacity>
            </View>

            <View style={styles.fieldContainer}>
              <Text style={[styles.label, isSmallScreen && styles.labelSmall]}>Número de cédula *</Text>
              <TextInput
                style={[styles.input, isSmallScreen && styles.inputSmall]}
                placeholder="Ej: 12345678"
                placeholderTextColor="#9aa"
                value={form.numero_cedula}
                onChangeText={(v) => changeField('numero_cedula', v.replace(/\D+/g, ''))}
                editable={!loading}
                keyboardType="numeric"
                returnKeyType="next"
                maxLength={20}
              />
              {errors.cedula && (
                <Text style={[styles.errorSmall, isSmallScreen && styles.errorSmallText]}>
                  {errors.cedula}
                </Text>
              )}
            </View>

            <View style={styles.fieldContainer}>
              <Text style={[styles.label, isSmallScreen && styles.labelSmall]}>Cédula completa</Text>
              <View style={[styles.cedulaCompletaContainer, isSmallScreen && styles.cedulaCompletaContainerSmall]}>
                <Text style={[styles.cedulaCompleta, isSmallScreen && styles.cedulaCompletaSmall]}>
                  {buildCedulaFormatted()}
                </Text>
              </View>
              <Text style={[styles.helpText, isSmallScreen && styles.helpTextSmall]}>
                Esta será su nombre de usuario para iniciar sesión
              </Text>
            </View>
          </View>

          <View style={styles.formSection}>
            <Text style={[styles.sectionTitle, isSmallScreen && styles.sectionTitleSmall]}>
              Contraseña de Seguridad
            </Text>

            <View style={styles.fieldContainer}>
              <Text style={[styles.label, isSmallScreen && styles.labelSmall]}>Contraseña *</Text>
              <TextInput
                style={[styles.input, isSmallScreen && styles.inputSmall]}
                placeholder="Mínimo 8 caracteres"
                placeholderTextColor="#9aa"
                value={form.password}
                onChangeText={(v) => changeField('password', v)}
                secureTextEntry
                editable={!loading}
              />
              {errors.password && (
                <Text style={[styles.errorSmall, isSmallScreen && styles.errorSmallText]}>
                  {errors.password}
                </Text>
              )}
              <Text style={[styles.helpText, isSmallScreen && styles.helpTextSmall]}>
                La contraseña debe tener al menos 8 caracteres
              </Text>
            </View>

            <View style={styles.fieldContainer}>
              <Text style={[styles.label, isSmallScreen && styles.labelSmall]}>Confirmar Contraseña *</Text>
              <TextInput
                style={[styles.input, isSmallScreen && styles.inputSmall]}
                placeholder="Repita la contraseña"
                placeholderTextColor="#9aa"
                value={form.confirmPassword}
                onChangeText={(v) => changeField('confirmPassword', v)}
                secureTextEntry
                editable={!loading}
              />
              {errors.confirmPassword && (
                <Text style={[styles.errorSmall, isSmallScreen && styles.errorSmallText]}>
                  {errors.confirmPassword}
                </Text>
              )}
            </View>
          </View>

          <View style={styles.formSection}>
            <Text style={[styles.sectionTitle, isSmallScreen && styles.sectionTitleSmall]}>
              Pregunta de Seguridad
            </Text>

            {/* 👇 SELECTOR DE PREGUNTA CON MODAL */}
            <View style={styles.fieldContainer}>
              <Text style={[styles.label, isSmallScreen && styles.labelSmall]}>Pregunta de Seguridad *</Text>
              <TouchableOpacity 
                style={[styles.customSelectButton, isSmallScreen && styles.customSelectButtonSmall]}
                onPress={() => setShowPreguntaModal(true)}
                disabled={loading}
              >
                <Text 
                  style={[
                    styles.customSelectText, 
                    isSmallScreen && styles.customSelectTextSmall,
                    !form.preguntaSeguridad && styles.customSelectPlaceholder,
                    { flex: 1 }
                  ]}
                  numberOfLines={1}
                  ellipsizeMode="tail"
                >
                  {form.preguntaSeguridad || 'Seleccione una pregunta de seguridad'}
                </Text>
                <Text style={[styles.customSelectArrow, isSmallScreen && styles.customSelectArrowSmall]}>▼</Text>
              </TouchableOpacity>
              {errors.preguntaSeguridad && (
                <Text style={[styles.errorSmall, isSmallScreen && styles.errorSmallText]}>
                  {errors.preguntaSeguridad}
                </Text>
              )}
            </View>

            <View style={styles.fieldContainer}>
              <Text style={[styles.label, isSmallScreen && styles.labelSmall]}>Respuesta de Seguridad *</Text>
              <TextInput
                style={[styles.input, isSmallScreen && styles.inputSmall]}
                placeholder="Su respuesta secreta"
                placeholderTextColor="#9aa"
                value={form.respuestaSeguridad}
                onChangeText={(v) => changeField('respuestaSeguridad', v)}
                editable={!loading}
              />
              {errors.respuestaSeguridad && (
                <Text style={[styles.errorSmall, isSmallScreen && styles.errorSmallText]}>
                  {errors.respuestaSeguridad}
                </Text>
              )}
              <Text style={[styles.helpText, isSmallScreen && styles.helpTextSmall]}>
                Esta respuesta le ayudará a recuperar su cuenta si olvida la contraseña
              </Text>
            </View>
          </View>
        </View>
      );
    }
  };

  return (
    <KeyboardAvoidingView style={styles.wrapper} behavior={Platform.OS === 'ios' ? 'padding' : 'height'}>
      <Image style={styles.bgImage} source={require('../../assets/frontImg.jpg')} blurRadius={4} />
      <View style={styles.overlay} />

      <ScrollView 
        contentContainerStyle={[
          styles.container,
          isSmallScreen && styles.containerSmall,
          isLargeScreen && styles.containerLarge
        ]}
        showsVerticalScrollIndicator={false}
      >
        <View style={[styles.card, { width: cardWidth }, isLargeScreen && styles.cardLarge]}>
          <Text style={[styles.title, isSmallScreen && styles.titleSmall, isLargeScreen && styles.titleLarge]}>
            Crear Cuenta de Usuario
          </Text>

          {form.nombres ? (
            <Text style={[styles.subtitle, isSmallScreen && styles.subtitleSmall, isLargeScreen && styles.subtitleLarge]}>
              Estás creando una cuenta para: <Text style={styles.highlightedName}>{form.nombres}</Text>
            </Text>
          ) : (
            <Text style={[styles.subtitle, isSmallScreen && styles.subtitleSmall, isLargeScreen && styles.subtitleLarge]}>
              Complete los campos para crear la cuenta de usuario.
            </Text>
          )}

          {renderFormContent()}

          <View style={[styles.buttonsRow, isSmallScreen && styles.buttonsRowSmall, isLargeScreen && styles.buttonsRowLarge]}>
            <TouchableOpacity
              style={[styles.btn, styles.btnPrimary, loading && styles.btnDisabled, isSmallScreen && styles.btnSmall, isLargeScreen && styles.btnLarge]}
              onPress={handleRegisterUser}
              disabled={loading}
              activeOpacity={0.85}
            >
              {loading ? (
                <ActivityIndicator color="#fff" size={isSmallScreen ? 'small' : 'large'} />
              ) : (
                <Text style={[styles.btnText, isSmallScreen && styles.btnTextSmall, isLargeScreen && styles.btnTextLarge]}>
                  Crear Usuario
                </Text>
              )}
            </TouchableOpacity>
          </View>

          <View style={[styles.footerRow, isSmallScreen && styles.footerRowSmall, isLargeScreen && styles.footerRowLarge]}>
            <TouchableOpacity onPress={goBackToLogin} style={styles.linkBtn}>
              <Text style={[styles.linkText, isSmallScreen && styles.linkTextSmall, isLargeScreen && styles.linkTextLarge]}>
                Volver al inicio de sesión
              </Text>
            </TouchableOpacity>

            <TouchableOpacity onPress={clearForm} style={styles.linkBtn}>
              <Text style={[styles.linkText, isSmallScreen && styles.linkTextSmall, isLargeScreen && styles.linkTextLarge]}>
                Limpiar formulario
              </Text>
            </TouchableOpacity>
          </View>

          <Text style={[styles.requiredHint, isSmallScreen && styles.requiredHintSmall, isLargeScreen && styles.requiredHintLarge]}>
            * Campos obligatorios
          </Text>
        </View>

        {/* 👇 MODAL PARA TIPO DE CÉDULA */}
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
                    changeField('tipo_cedula', tipo as 'V' | 'E' | 'P');
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
                <Text style={[styles.modalCloseText, isSmallScreen && styles.modalCloseTextSmall]}>
                  Cancelar
                </Text>
              </TouchableOpacity>
            </View>
          </View>
        </RNModal>

        {/* 👇 MODAL PARA PREGUNTA DE SEGURIDAD */}
        <RNModal
          visible={showPreguntaModal}
          transparent={true}
          animationType="slide"
          onRequestClose={() => setShowPreguntaModal(false)}
        >
          <View style={styles.modalOverlay}>
            <View style={[styles.modalContent, isSmallScreen && styles.modalContentSmall]}>
              <Text style={[styles.modalTitle, isSmallScreen && styles.modalTitleSmall]}>
                Seleccionar Pregunta de Seguridad
              </Text>
              
              <ScrollView style={styles.modalScrollView}>
                {PREGUNTAS_SEGURIDAD.map((pregunta, index) => (
                  <TouchableOpacity
                    key={index}
                    style={[
                      styles.modalOption,
                      isSmallScreen && styles.modalOptionSmall,
                      form.preguntaSeguridad === pregunta && styles.modalOptionSelected
                    ]}
                    onPress={() => {
                      changeField('preguntaSeguridad', pregunta);
                      setShowPreguntaModal(false);
                    }}
                  >
                    <Text style={[
                      styles.modalOptionText,
                      isSmallScreen && styles.modalOptionTextSmall,
                      form.preguntaSeguridad === pregunta && styles.modalOptionTextSelected
                    ]}>
                      {pregunta}
                    </Text>
                  </TouchableOpacity>
                ))}
              </ScrollView>
              
              <TouchableOpacity
                style={[styles.modalCloseButton, isSmallScreen && styles.modalCloseButtonSmall]}
                onPress={() => setShowPreguntaModal(false)}
              >
                <Text style={[styles.modalCloseText, isSmallScreen && styles.modalCloseTextSmall]}>
                  Cancelar
                </Text>
              </TouchableOpacity>
            </View>
          </View>
        </RNModal>
      </ScrollView>
    </KeyboardAvoidingView>
  );
}

function normalizeIncomingCedula(raw?: string): { tipo: 'V' | 'E' | 'P'; numero: string } {
  if (!raw) return { tipo: 'V', numero: '' };
  const s = String(raw).toUpperCase().replace(/\s+/g, '');
  if (s.includes('-')) {
    const [t, n] = s.split('-', 2);
    return { tipo: (t === 'E' || t === 'P') ? t as 'E'|'P' : 'V', numero: n.replace(/\D+/g, '') };
  }
  if (s.length && isNaN(Number(s[0]))) {
    return { tipo: (s[0] === 'E' || s[0] === 'P') ? s[0] as 'E'|'P' : 'V', numero: s.slice(1).replace(/\D+/g, '') };
  }
  return { tipo: 'V', numero: s.replace(/\D+/g, '') };
}

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
  containerSmall: {
    padding: 16,
    paddingVertical: 20,
  },
  containerLarge: {
    padding: 24,
    paddingVertical: 30,
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
  cardLarge: {
    borderRadius: 16,
    padding: 24,
    maxWidth: 920,
  },
  title: { 
    fontSize: 20, 
    fontWeight: '800', 
    marginBottom: 6, 
    color: '#222', 
    textAlign: 'center' 
  },
  titleSmall: {
    fontSize: 18,
  },
  titleLarge: {
    fontSize: 24,
    marginBottom: 8,
  },
  subtitle: { 
    fontSize: 14, 
    color: '#666', 
    marginBottom: 16, 
    textAlign: 'center',
    lineHeight: 20,
  },
  subtitleSmall: {
    fontSize: 12,
    lineHeight: 18,
  },
  subtitleLarge: {
    fontSize: 16,
    lineHeight: 22,
    marginBottom: 20,
  },
  highlightedName: {
    fontWeight: '800',
    color: '#1f6fff',
  },
  formContent: {
    marginBottom: 8,
  },
  formContentSmall: {
    marginBottom: 4,
  },
  twoColumnsLayout: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    gap: 24,
    marginBottom: 8,
  },
  column: {
    flex: 1,
  },
  formSection: {
    marginBottom: 16,
    paddingBottom: 12,
    borderBottomWidth: 1,
    borderBottomColor: '#f0f0f0',
  },
  sectionTitle: {
    fontSize: 16,
    fontWeight: '700',
    color: '#2d3748',
    marginBottom: 12,
    paddingBottom: 6,
    borderBottomWidth: 2,
    borderBottomColor: '#eef2ff',
  },
  sectionTitleSmall: {
    fontSize: 15,
    marginBottom: 10,
  },
  fieldContainer: {
    marginBottom: 12,
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
  cedulaCompletaContainer: {
    backgroundColor: '#f8f9fa',
    borderRadius: 8,
    paddingHorizontal: 12,
    paddingVertical: 12,
    borderWidth: 1,
    borderColor: '#e1e5e9',
  },
  cedulaCompletaContainerSmall: {
    paddingVertical: 10,
  },
  cedulaCompleta: {
    fontSize: 16,
    fontWeight: '600',
    color: '#4a5568',
    textAlign: 'center',
  },
  cedulaCompletaSmall: {
    fontSize: 15,
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
  errorSmall: { 
    color: '#e63946', 
    fontSize: 12, 
    marginTop: 4,
  },
  errorSmallText: {
    fontSize: 11,
  },
  buttonsRow: { 
    flexDirection: 'row', 
    justifyContent: 'center', 
    marginTop: 16 
  },
  buttonsRowSmall: {
    marginTop: 12,
  },
  buttonsRowLarge: {
    marginTop: 20,
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
  btnLarge: {
    paddingVertical: 14,
    minWidth: 220,
    borderRadius: 12,
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
  btnTextLarge: {
    fontSize: 17,
  },
  footerRow: { 
    flexDirection: 'row', 
    justifyContent: 'space-between', 
    marginTop: 16 
  },
  footerRowSmall: {
    flexDirection: 'column',
    alignItems: 'center',
    gap: 8,
    marginTop: 12,
  },
  footerRowLarge: {
    marginTop: 20,
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
  linkTextLarge: {
    fontSize: 14,
  },
  requiredHint: { 
    fontSize: 12, 
    color: '#666', 
    marginTop: 12, 
    textAlign: 'center', 
    fontStyle: 'italic' 
  },
  requiredHintSmall: {
    fontSize: 11,
  },
  requiredHintLarge: {
    fontSize: 13,
  },
  // 👇 NUEVOS ESTILOS PARA SELECTS PERSONALIZADOS
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
  // 👇 ESTILOS PARA MODALES
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
  modalScrollView: {
    maxHeight: 300,
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