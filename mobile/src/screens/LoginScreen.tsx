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
  ScrollView,
} from 'react-native';
import Icon from 'react-native-vector-icons/MaterialCommunityIcons';
import type { StackNavigationProp } from '@react-navigation/stack';
import AsyncStorage from '@react-native-async-storage/async-storage';
import axios from 'axios';
import { AuthContext } from '../contexts/AuthContext';

type RootStackParamList = {
  Login: undefined;
  Main: undefined;
  Register: { form?: any } | undefined;
  RegisterPerson: { form?: any } | undefined;
  RegisterScreen: { form?: any } | undefined;
  RegisterUser: { person: any } | undefined;
};
type LoginScreenNavigationProp = StackNavigationProp<RootStackParamList, 'Login'>;

interface LoginScreenProps {
  navigation: LoginScreenNavigationProp;
}

const { width: screenWidth, height: screenHeight } = Dimensions.get('window');
const BASE_URL = 'https://djangoapp-6wxv.onrender.com';

export default function LoginScreen({ navigation }: LoginScreenProps) {
  const { loginWithTokens } = useContext(AuthContext);
  const [cedula, setCedula] = useState('');
  const [password, setPassword] = useState('');
  const [focusField, setFocusField] = useState<'cedula' | 'password' | null>(null);
  const [errors, setErrors] = useState<{ cedula?: string; password?: string }>({});
  const [buttonScale] = useState(new Animated.Value(1));
  const [loading, setLoading] = useState(false);
  const formAnim = useRef(new Animated.Value(0)).current;
  const logoAnim = useRef(new Animated.Value(0)).current;

  const isSmallScreen = screenWidth < 375;
  const isMediumScreen = screenWidth >= 375 && screenWidth < 768;
  const isLargeScreen = screenWidth >= 768;

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

  const tryObtainToken = async (digits: string, passwordValue: string) => {
    try {
      console.log('[login] 🔄 Iniciando proceso de login para cédula:', digits);
      
      // PRIMERO: Obtener el idPersona del backend
      console.log('[login] 1. Buscando idPersona...');
      let userInfo = null;
      
      try {
        const personaRes = await axios.get(
          `${BASE_URL}/api/obtener-persona-login/?cedula=${encodeURIComponent(digits)}`,
          {
            headers: {
              'Content-Type': 'application/json',
              'Accept': 'application/json',
            },
            timeout: 15000,
          }
        );
        
        console.log('[login] Respuesta obtener-persona-login:', personaRes.data);
        
        if (personaRes.data.idPersona) {
          userInfo = {
            idPersona: personaRes.data.idPersona,
            cedula: digits,
            nombres: personaRes.data.nombres || '',
            apellidos: personaRes.data.apellidos || '',
            correo: personaRes.data.correo || '',
            displayName: `${personaRes.data.nombres || ''} ${personaRes.data.apellidos || ''}`.trim()
          };
          console.log('[login] ✅ Información de usuario obtenida:', userInfo);
        } else {
          console.log('[login] ❌ No se encontró idPersona');
          return { 
            error: { detail: 'No se encontró usuario con esta cédula' } 
          };
        }
      } catch (err: any) {
        console.error('[login] ❌ Error al buscar persona:', err.response?.data || err.message);
        return { 
          error: { detail: 'Error al verificar cédula en el servidor' } 
        };
      }

      // SEGUNDO: Hacer login con el idPersona obtenido
      console.log('[login] 2. Haciendo login con idPersona...');
      const payload = {
        idPersona: userInfo.idPersona,
        password: passwordValue
      };
      
      console.log('[login] Payload de login:', payload);
      
      const res = await axios.post(
        `${BASE_URL}/api/token/`, 
        payload,
        {
          headers: {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
          },
          timeout: 15000,
        }
      );
      
      console.log('[login] ✅ Login exitoso, tokens recibidos');
      
      return { 
        access: res.data.access, 
        refresh: res.data.refresh,
        user: userInfo
      };
      
    } catch (err: any) {
      console.error('[login] ❌ Error en login:', err.response?.data || err.message);
      return { 
        error: err.response?.data || { detail: 'Error de autenticación' } 
      };
    }
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

      const result: any = await tryObtainToken(digits, password);

      if (!result) {
        Alert.alert('Error', 'No se obtuvo respuesta del servidor.');
        setLoading(false);
        return;
      }

      if (result.error) {
        const e = result.error;
        if (typeof e === 'object') {
          const textErr =
            e.detail ||
            e.non_field_errors?.join?.(', ') ||
            Object.entries(e).map(([k, v]) => `${k}: ${Array.isArray(v) ? v.join('; ') : String(v)}`).join('\n') ||
            JSON.stringify(e);
          Alert.alert('Error de autenticación', textErr);
        } else {
          Alert.alert('Error', String(e));
        }
        setLoading(false);
        return;
      }

      const access = result.access as string | undefined;
      const refresh = result.refresh as string | undefined;
      const user = result.user;

      if (!access) {
        Alert.alert('Error', 'El servidor no devolvió token de acceso válido.');
        setLoading(false);
        return;
      }

      console.log('[login] 📝 Guardando tokens e información de usuario...');
      await loginWithTokens(access, refresh, user);
      
      console.log('[login] ✅ Login completado exitosamente');
      
      navigation.reset({ index: 0, routes: [{ name: 'Main' }] });
    } catch (err: any) {
      console.error('Login error', err);
      Alert.alert('Error', err?.message ?? 'Error al intentar iniciar sesión');
    } finally {
      setLoading(false);
    }
  };

  const openRegister = () => {
    const cedulaDigits = normalizeCedulaToDigits(cedula);
    navigation.navigate('Register' as any, { form: { cedula: cedulaDigits } });
  };

  const openRegisterUser = () => {
    const cedulaDigits = normalizeCedulaToDigits(cedula);
    navigation.navigate('RegisterUser' as any, { person: { cedula: cedulaDigits } });
  };

  // Cálculos responsivos
  const getFormWidth = () => {
    if (isSmallScreen) return screenWidth * 0.92;
    if (isMediumScreen) return Math.min(500, screenWidth * 0.85);
    return Math.min(560, screenWidth * 0.8);
  };

  const getLogoFontSize = () => {
    if (isSmallScreen) return { title: 22, subtitle: 14 };
    if (isMediumScreen) return { title: 24, subtitle: 15 };
    return { title: 26, subtitle: 16 };
  };

  const logoSize = getLogoFontSize();
  const formWidth = getFormWidth();

  return (
    <KeyboardAvoidingView style={styles.container} behavior={Platform.OS === 'ios' ? 'padding' : undefined}>
      <Image style={styles.bgImage} source={require('../../assets/frontImg.jpg')} blurRadius={3} />
      <View style={styles.overlay} />
      
      <ScrollView 
        contentContainerStyle={styles.scrollContainer}
        showsVerticalScrollIndicator={false}
      >
        <Animated.View style={[
          styles.logoContainer, 
          { 
            transform: [
              { scale: logoAnim.interpolate({ inputRange: [0, 1], outputRange: [0.7, 1] }) }, 
              { translateY: logoAnim.interpolate({ inputRange: [0, 1], outputRange: [-40, 0] }) }
            ], 
            opacity: logoAnim 
          }
        ]}>
          <Text style={[styles.logoTitle, { fontSize: logoSize.title }]}>FUNDACIÓN UPTYAB</Text>
          <Text style={[styles.logoSubtitle, { fontSize: logoSize.subtitle }]}>Trámites académicos</Text>
        </Animated.View>

        <Animated.View style={[
          styles.form, 
          { 
            width: formWidth, 
            opacity: formAnim, 
            transform: [
              { translateY: formAnim.interpolate({ inputRange: [0,1], outputRange: [80,0] }) }
            ] 
          }
        ]}>
          {/* Campo Cédula */}
          <View style={[
            styles.inputContainer, 
            focusField === 'cedula' && styles.inputContainerFocused, 
            errors.cedula && styles.inputContainerError
          ]}>
            <Icon 
              name="card-account-details" 
              size={isSmallScreen ? 20 : 24} 
              color={focusField === 'cedula' ? '#4f8cff' : errors.cedula ? '#e63946' : '#aaa'} 
              style={styles.inputIcon} 
            />
            <TextInput
              style={[styles.inputs, { fontSize: isSmallScreen ? 14 : 16 }]}
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

          {/* Campo Contraseña */}
          <View style={[
            styles.inputContainer, 
            focusField === 'password' && styles.inputContainerFocused, 
            errors.password && styles.inputContainerError
          ]}>
            <Icon 
              name="lock" 
              size={isSmallScreen ? 20 : 24} 
              color={focusField === 'password' ? '#4f8cff' : errors.password ? '#e63946' : '#aaa'} 
              style={styles.inputIcon} 
            />
            <TextInput
              style={[styles.inputs, { fontSize: isSmallScreen ? 14 : 16 }]}
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

          {/* Olvidó contraseña */}
          <TouchableOpacity 
            style={styles.btnForgotPassword} 
            onPress={() => Alert.alert('Recuperar contraseña', 'Funcionalidad próximamente disponible')} 
            disabled={loading}
          >
            <Text style={[styles.btnForgotText, { fontSize: isSmallScreen ? 12 : 14 }]}>
              ¿Olvidó su contraseña?
            </Text>
          </TouchableOpacity>

          {/* Botón Entrar */}
          <Animated.View style={{ width: '100%', transform: [{ scale: buttonScale }] }}>
            <TouchableOpacity 
              style={[
                styles.buttonContainer, 
                styles.loginButton, 
                loading && { opacity: 0.8 },
                { height: isSmallScreen ? 44 : 48 }
              ]} 
              onPress={handleLogin} 
              activeOpacity={0.85} 
              disabled={loading}
            >
              {loading ? (
                <>
                  <ActivityIndicator color="#fff" size="small" style={{ marginRight: 8 }} />
                  <Text style={[styles.loginText, { fontSize: isSmallScreen ? 15 : 17 }]}>
                    Entrando...
                  </Text>
                </>
              ) : (
                <Text style={[styles.loginText, { fontSize: isSmallScreen ? 15 : 17 }]}>
                  Entrar
                </Text>
              )}
            </TouchableOpacity>
          </Animated.View>

          {/* Sección de Registro - MEJORADO Y RESPONSIVE */}
          <View style={[
            styles.registerSection,
            isSmallScreen && styles.registerSectionSmall
          ]}>
            <Text style={[
              styles.registerHint,
              { fontSize: isSmallScreen ? 13 : 14 }
            ]}>
              ¿No estás registrado?
            </Text>

            <View style={[
              styles.registerButtonsGroup,
              isSmallScreen && styles.registerButtonsGroupSmall,
              isMediumScreen && styles.registerButtonsGroupMedium
            ]}>
              <TouchableOpacity 
                style={[
                  styles.registerButton,
                  isSmallScreen && styles.registerButtonSmall,
                  isMediumScreen && styles.registerButtonMedium
                ]} 
                onPress={openRegister} 
                activeOpacity={0.85}
              >
                <Icon 
                  name="account-plus" 
                  size={isSmallScreen ? 16 : 18} 
                  color="#fff" 
                  style={{ marginRight: 6 }} 
                />
                <Text style={[
                  styles.registerText,
                  isSmallScreen && styles.registerTextSmall,
                  isMediumScreen && styles.registerTextMedium
                ]}>
                   Registrarse
                </Text>
              </TouchableOpacity>

              <TouchableOpacity 
                style={[
                  styles.registerUserButton,
                  isSmallScreen && styles.registerUserButtonSmall,
                  isMediumScreen && styles.registerUserButtonMedium
                ]} 
                onPress={openRegisterUser} 
                activeOpacity={0.85}
              >
                <Icon 
                  name="account-key" 
                  size={isSmallScreen ? 14 : 16} 
                  color="#fff" 
                  style={{ marginRight: 6 }} 
                />
                <Text style={[
                  styles.registerUserText,
                  isSmallScreen && styles.registerUserTextSmall,
                  isMediumScreen && styles.registerUserTextMedium
                ]}>
                   Registrar usuario
                </Text>
              </TouchableOpacity>
            </View>
          </View>
        </Animated.View>
      </ScrollView>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  container: { 
    flex: 1, 
    backgroundColor: '#DCDCDC' 
  },
  scrollContainer: {
    flexGrow: 1,
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: 20,
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
  logoContainer: { 
    alignItems: 'center', 
    marginBottom: 30,
    paddingHorizontal: 20,
  },
  logoTitle: { 
    color: '#fff', 
    fontWeight: 'bold', 
    textAlign: 'center', 
    letterSpacing: 1,
    textShadowColor: 'rgba(0,0,0,0.3)',
    textShadowOffset: { width: 1, height: 1 },
    textShadowRadius: 3,
  },
  logoSubtitle: { 
    color: '#fff', 
    fontWeight: '600', 
    textAlign: 'center', 
    marginTop: 4,
    textShadowColor: 'rgba(0,0,0,0.3)',
    textShadowOffset: { width: 1, height: 1 },
    textShadowRadius: 2,
  },
  form: { 
    backgroundColor: 'rgba(255,255,255,0.96)', 
    borderRadius: 22, 
    padding: 26, 
    alignItems: 'center', 
    elevation: 10,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.1,
    shadowRadius: 8,
  },
  inputContainer: { 
    flexDirection: 'row', 
    alignItems: 'center', 
    backgroundColor: '#fff', 
    borderRadius: 30, 
    height: 50, 
    marginBottom: 10, 
    width: '100%', 
    paddingHorizontal: 12, 
    borderWidth: 1.2, 
    borderColor: 'transparent' 
  },
  inputContainerFocused: { 
    borderColor: '#4f8cff' 
  },
  inputContainerError: { 
    borderColor: '#e63946' 
  },
  inputs: { 
    flex: 1, 
    height: 45, 
    marginLeft: 10, 
    color: '#22223b',
  },
  inputIcon: { 
    marginLeft: 2, 
    marginRight: 2 
  },
  errorText: { 
    color: '#e63946', 
    fontSize: 12, 
    marginBottom: 6, 
    alignSelf: 'flex-start', 
    marginLeft: 12 
  },
  btnForgotPassword: { 
    alignSelf: 'flex-end', 
    marginBottom: 10 
  },
  btnForgotText: { 
    color: '#4f8cff', 
    fontWeight: 'bold' 
  },
  buttonContainer: { 
    flexDirection: 'row', 
    justifyContent: 'center', 
    alignItems: 'center', 
    marginBottom: 10, 
    width: '100%', 
    borderRadius: 30, 
    backgroundColor: 'transparent' 
  },
  loginButton: { 
    backgroundColor: '#4f8cff' 
  },
  loginText: { 
    color: 'white', 
    fontWeight: 'bold' 
  },
  
  // Sección de registro - Estilos base
  registerSection: {
    width: '100%',
    marginTop: 12,
    alignItems: 'center',
  },
  registerSectionSmall: {
    marginTop: 8,
  },
  registerHint: {
    color: '#555',
    marginBottom: 12,
    textAlign: 'center',
  },
  
  // Grupo de botones de registro
  registerButtonsGroup: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    flexWrap: 'wrap',
    gap: 8,
    width: '100%',
  },
  registerButtonsGroupSmall: {
    flexDirection: 'column',
    gap: 6,
  },
  registerButtonsGroupMedium: {
    gap: 6,
  },
  
  // Botón Registrarse
  registerButton: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#2b8cff',
    paddingVertical: 10,
    paddingHorizontal: 16,
    borderRadius: 24,
    minWidth: 120,
    justifyContent: 'center',
  },
  registerButtonSmall: {
    paddingVertical: 8,
    paddingHorizontal: 12,
    minWidth: '100%',
    borderRadius: 20,
  },
  registerButtonMedium: {
    paddingVertical: 9,
    paddingHorizontal: 14,
    minWidth: 110,
  },
  registerText: {
    color: '#fff',
    fontWeight: '700',
  },
  registerTextSmall: {
    fontSize: 13,
  },
  registerTextMedium: {
    fontSize: 13,
  },
  
  // Botón Registrar Usuario
  registerUserButton: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#2b8cff', // Mismo color que Registrarse
    paddingVertical: 10,
    paddingHorizontal: 16,
    borderRadius: 24,
    minWidth: 140,
    justifyContent: 'center',
  },
  registerUserButtonSmall: {
    paddingVertical: 8,
    paddingHorizontal: 12,
    minWidth: '100%',
    borderRadius: 20,
  },
  registerUserButtonMedium: {
    paddingVertical: 9,
    paddingHorizontal: 14,
    minWidth: 130,
  },
  registerUserText: {
    color: '#fff',
    fontWeight: '700',
  },
  registerUserTextSmall: {
    fontSize: 13,
  },
  registerUserTextMedium: {
    fontSize: 13,
  },
});