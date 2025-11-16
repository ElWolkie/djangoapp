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
  useWindowDimensions,
} from 'react-native';
import Icon from 'react-native-vector-icons/MaterialCommunityIcons';
import type { StackNavigationProp } from '@react-navigation/stack';
import axios from 'axios';
import { AuthContext } from '../contexts/AuthContext';

type RootStackParamList = {
  Login: undefined;
  Main: undefined;
  Register: { form?: any } | undefined;
  RegisterPerson: { form?: any } | undefined;
  RegisterScreen: { form?: any } | undefined;
  RegisterUser: { person: any } | undefined;
  ForgotPassword: undefined;
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

  const { width, height } = useWindowDimensions();
  const isSmallScreen = width < 375;
  const isMediumScreen = width >= 375 && width < 768;
  const isLargeScreen = width >= 768;

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

  const getFormWidth = () => {
    if (isSmallScreen) return width * 0.92;
    if (isMediumScreen) return Math.min(500, width * 0.85);
    if (isLargeScreen) return Math.min(560, width * 0.5);
    return Math.min(560, width * 0.8);
  };

  const getLogoFontSize = () => {
    if (isSmallScreen) return { title: 22, subtitle: 14 };
    if (isMediumScreen) return { title: 24, subtitle: 15 };
    if (isLargeScreen) return { title: 28, subtitle: 16 };
    return { title: 26, subtitle: 16 };
  };

  const getFormPadding = () => {
    if (isSmallScreen) return 20;
    if (isMediumScreen) return 24;
    return 28;
  };

  const logoSize = getLogoFontSize();
  const formWidth = getFormWidth();
  const formPadding = getFormPadding();

  return (
    <KeyboardAvoidingView 
      style={styles.container} 
      behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
    >
      <Image 
        style={styles.bgImage} 
        source={require('../../assets/frontImg.jpg')} 
        blurRadius={3} 
      />
      <View style={styles.overlay} />
      
      <ScrollView 
        contentContainerStyle={[
          styles.scrollContainer,
          isSmallScreen && styles.scrollContainerSmall,
          isLargeScreen && styles.scrollContainerLarge
        ]}
        showsVerticalScrollIndicator={false}
        keyboardShouldPersistTaps="handled"
        style={isSmallScreen ? { flex: 1 } : undefined}
      >
        <Animated.View style={[
          styles.logoContainer, 
          isSmallScreen && styles.logoContainerSmall,
          isLargeScreen && styles.logoContainerLarge,
          { 
            transform: [
              { 
                scale: logoAnim.interpolate({ 
                  inputRange: [0, 1], 
                  outputRange: [0.7, 1] 
                }) 
              }, 
              { 
                translateY: logoAnim.interpolate({ 
                  inputRange: [0, 1], 
                  outputRange: isSmallScreen ? [-20, 0] : [-40, 0]
                }) 
              }
            ], 
            opacity: logoAnim 
          }
        ]}>
          <Text style={[
            styles.logoTitle, 
            { fontSize: logoSize.title },
            isSmallScreen && styles.logoTitleSmall,
            isLargeScreen && styles.logoTitleLarge
          ]}>
            FUNDACIÓN UPTYAB
          </Text>
          <Text style={[
            styles.logoSubtitle, 
            { fontSize: logoSize.subtitle },
            isSmallScreen && styles.logoSubtitleSmall,
            isLargeScreen && styles.logoSubtitleLarge
          ]}>
            Trámites académicos
          </Text>
        </Animated.View>

        <Animated.View style={[
          styles.form, 
          { 
            width: formWidth,
            padding: formPadding,
            opacity: formAnim, 
            transform: [
              { 
                translateY: formAnim.interpolate({ 
                  inputRange: [0, 1], 
                  outputRange: [80, 0] 
                }) 
              }
            ] 
          },
          isSmallScreen && styles.formSmall,
          isLargeScreen && styles.formLarge
        ]}>
          {/* Campo Cédula */}
          <View style={[
            styles.inputContainer, 
            focusField === 'cedula' && styles.inputContainerFocused, 
            errors.cedula && styles.inputContainerError,
            isSmallScreen && styles.inputContainerSmall,
            isLargeScreen && styles.inputContainerLarge
          ]}>
            <Icon 
              name="card-account-details" 
              size={isSmallScreen ? 18 : isLargeScreen ? 22 : 20} 
              color={focusField === 'cedula' ? '#4f8cff' : errors.cedula ? '#e63946' : '#aaa'} 
              style={styles.inputIcon} 
            />
            <TextInput
              style={[
                styles.inputs, 
                { fontSize: isSmallScreen ? 14 : isLargeScreen ? 16 : 15 },
                isSmallScreen && styles.inputsSmall,
                isLargeScreen && styles.inputsLarge
              ]}
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
          {errors.cedula && (
            <Text style={[
              styles.errorText,
              isSmallScreen && styles.errorTextSmall,
              isLargeScreen && styles.errorTextLarge
            ]}>
              {errors.cedula}
            </Text>
          )}

          {/* Campo Contraseña */}
          <View style={[
            styles.inputContainer, 
            focusField === 'password' && styles.inputContainerFocused, 
            errors.password && styles.inputContainerError,
            isSmallScreen && styles.inputContainerSmall,
            isLargeScreen && styles.inputContainerLarge
          ]}>
            <Icon 
              name="lock" 
              size={isSmallScreen ? 18 : isLargeScreen ? 22 : 20} 
              color={focusField === 'password' ? '#4f8cff' : errors.password ? '#e63946' : '#aaa'} 
              style={styles.inputIcon} 
            />
            <TextInput
              style={[
                styles.inputs, 
                { fontSize: isSmallScreen ? 14 : isLargeScreen ? 16 : 15 },
                isSmallScreen && styles.inputsSmall,
                isLargeScreen && styles.inputsLarge
              ]}
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
              onSubmitEditing={handleLogin}
            />
          </View>
          {errors.password && (
            <Text style={[
              styles.errorText,
              isSmallScreen && styles.errorTextSmall,
              isLargeScreen && styles.errorTextLarge
            ]}>
              {errors.password}
            </Text>
          )}

          {/* Olvidó contraseña */}
          <TouchableOpacity 
            style={[
              styles.btnForgotPassword,
              isSmallScreen && styles.btnForgotPasswordSmall,
              isLargeScreen && styles.btnForgotPasswordLarge
            ]} 
            onPress={() => navigation.navigate('ForgotPassword')}
            disabled={loading}
          >
            <Text style={[
              styles.btnForgotText, 
              { fontSize: isSmallScreen ? 12 : isLargeScreen ? 14 : 13 },
              isSmallScreen && styles.btnForgotTextSmall,
              isLargeScreen && styles.btnForgotTextLarge
            ]}>
              ¿Olvidó su contraseña?
            </Text>
          </TouchableOpacity>

          {/* Botón Entrar */}
          <Animated.View style={{ width: '100%', transform: [{ scale: buttonScale }] }}>
            <TouchableOpacity 
              style={[
                styles.buttonContainer, 
                styles.loginButton, 
                loading && styles.loginButtonDisabled,
                { height: isSmallScreen ? 44 : isLargeScreen ? 52 : 48 },
                isSmallScreen && styles.loginButtonSmall,
                isLargeScreen && styles.loginButtonLarge
              ]} 
              onPress={handleLogin} 
              activeOpacity={0.85} 
              disabled={loading}
            >
              {loading ? (
                <>
                  <ActivityIndicator color="#fff" size="small" style={{ marginRight: 8 }} />
                  <Text style={[
                    styles.loginText, 
                    { fontSize: isSmallScreen ? 15 : isLargeScreen ? 17 : 16 },
                    isSmallScreen && styles.loginTextSmall,
                    isLargeScreen && styles.loginTextLarge
                  ]}>
                    Entrando...
                  </Text>
                </>
              ) : (
                <Text style={[
                  styles.loginText, 
                  { fontSize: isSmallScreen ? 15 : isLargeScreen ? 17 : 16 },
                  isSmallScreen && styles.loginTextSmall,
                  isLargeScreen && styles.loginTextLarge
                ]}>
                  Entrar
                </Text>
              )}
            </TouchableOpacity>
          </Animated.View>

          {/* Sección de Registro */}
          <View style={[
            styles.registerSection,
            isSmallScreen && styles.registerSectionSmall,
            isLargeScreen && styles.registerSectionLarge
          ]}>
            <Text style={[
              styles.registerHint,
              { fontSize: isSmallScreen ? 13 : isLargeScreen ? 15 : 14 },
              isSmallScreen && styles.registerHintSmall,
              isLargeScreen && styles.registerHintLarge
            ]}>
              ¿No estás registrado?
            </Text>

            <View style={[
              styles.registerButtonsGroup,
              isSmallScreen && styles.registerButtonsGroupSmall,
              isMediumScreen && styles.registerButtonsGroupMedium,
              isLargeScreen && styles.registerButtonsGroupLarge
            ]}>
              <TouchableOpacity 
                style={[
                  styles.registerButton,
                  isSmallScreen && styles.registerButtonSmall,
                  isMediumScreen && styles.registerButtonMedium,
                  isLargeScreen && styles.registerButtonLarge
                ]} 
                onPress={openRegister} 
                activeOpacity={0.85}
                disabled={loading}
              >
                <Icon 
                  name="account-plus" 
                  size={isSmallScreen ? 16 : isLargeScreen ? 20 : 18} 
                  color="#fff" 
                  style={{ marginRight: 6 }} 
                />
                <Text style={[
                  styles.registerText,
                  isSmallScreen && styles.registerTextSmall,
                  isMediumScreen && styles.registerTextMedium,
                  isLargeScreen && styles.registerTextLarge
                ]}>
                  Registrarse
                </Text>
              </TouchableOpacity>

              <TouchableOpacity 
                style={[
                  styles.registerUserButton,
                  isSmallScreen && styles.registerUserButtonSmall,
                  isMediumScreen && styles.registerUserButtonMedium,
                  isLargeScreen && styles.registerUserButtonLarge
                ]} 
                onPress={openRegisterUser} 
                activeOpacity={0.85}
                disabled={loading}
              >
                <Icon 
                  name="account-key" 
                  size={isSmallScreen ? 14 : isLargeScreen ? 18 : 16} 
                  color="#fff" 
                  style={{ marginRight: 6 }} 
                />
                <Text style={[
                  styles.registerUserText,
                  isSmallScreen && styles.registerUserTextSmall,
                  isMediumScreen && styles.registerUserTextMedium,
                  isLargeScreen && styles.registerUserTextLarge
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
    minHeight: '100%',
  },
  scrollContainerSmall: {
    paddingVertical: 16,
    justifyContent: 'center',
    paddingTop: 0,
    minHeight: Math.max(screenHeight, 600),
  },
  scrollContainerLarge: {
    paddingVertical: 40,
    justifyContent: 'center',
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
  logoContainerSmall: {
    marginBottom: 25,
    paddingHorizontal: 16,
    marginTop: 10,
  },
  logoContainerLarge: {
    marginBottom: 40,
    paddingHorizontal: 24,
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
  logoTitleSmall: {
    letterSpacing: 0.5,
    textShadowRadius: 2,
  },
  logoTitleLarge: {
    letterSpacing: 1.5,
    textShadowRadius: 4,
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
  logoSubtitleSmall: {
    marginTop: 2,
    textShadowRadius: 1,
  },
  logoSubtitleLarge: {
    marginTop: 6,
    textShadowRadius: 3,
  },
  form: { 
    backgroundColor: 'rgba(255,255,255,0.96)', 
    borderRadius: 22, 
    alignItems: 'center', 
    elevation: 10,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.1,
    shadowRadius: 8,
  },
  formSmall: {
    borderRadius: 18,
    elevation: 8,
    shadowRadius: 6,
  },
  formLarge: {
    borderRadius: 24,
    elevation: 12,
    shadowRadius: 12,
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
  inputContainerSmall: {
    height: 44,
    borderRadius: 22,
    marginBottom: 8,
    paddingHorizontal: 10,
  },
  inputContainerLarge: {
    height: 54,
    borderRadius: 27,
    marginBottom: 12,
    paddingHorizontal: 16,
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
  inputsSmall: {
    height: 40,
    marginLeft: 8,
  },
  inputsLarge: {
    height: 50,
    marginLeft: 12,
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
  errorTextSmall: {
    fontSize: 11,
    marginLeft: 10,
  },
  errorTextLarge: {
    fontSize: 13,
    marginLeft: 14,
  },
  btnForgotPassword: { 
    alignSelf: 'flex-end', 
    marginBottom: 10 
  },
  btnForgotPasswordSmall: {
    marginBottom: 8,
  },
  btnForgotPasswordLarge: {
    marginBottom: 12,
  },
  btnForgotText: { 
    color: '#4f8cff', 
    fontWeight: 'bold' 
  },
  btnForgotTextSmall: {
    fontWeight: '600',
  },
  btnForgotTextLarge: {
    fontWeight: '700',
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
  loginButtonDisabled: {
    opacity: 0.7,
  },
  loginButtonSmall: {
    borderRadius: 22,
  },
  loginButtonLarge: {
    borderRadius: 27,
  },
  loginText: { 
    color: 'white', 
    fontWeight: 'bold' 
  },
  loginTextSmall: {
    fontWeight: '600',
  },
  loginTextLarge: {
    fontWeight: '700',
  },
  registerSection: {
    width: '100%',
    marginTop: 12,
    alignItems: 'center',
  },
  registerSectionSmall: {
    marginTop: 8,
  },
  registerSectionLarge: {
    marginTop: 16,
  },
  registerHint: {
    color: '#555',
    marginBottom: 12,
    textAlign: 'center',
  },
  registerHintSmall: {
    marginBottom: 10,
  },
  registerHintLarge: {
    marginBottom: 14,
  },
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
  registerButtonsGroupLarge: {
    gap: 10,
  },
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
  registerButtonLarge: {
    paddingVertical: 12,
    paddingHorizontal: 18,
    minWidth: 140,
    borderRadius: 26,
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
  registerTextLarge: {
    fontSize: 15,
  },
  registerUserButton: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#2b8cff',
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
  registerUserButtonLarge: {
    paddingVertical: 12,
    paddingHorizontal: 18,
    minWidth: 160,
    borderRadius: 26,
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
  registerUserTextLarge: {
    fontSize: 15,
  },
});