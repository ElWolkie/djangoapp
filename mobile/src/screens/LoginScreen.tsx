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

// IMPORTANTE: Usa el tipo RootStackParamList del App.tsx
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
  const [cedula, setCedula] = useState('');
  const [password, setPassword] = useState('');
  const [focusField, setFocusField] = useState<'cedula' | 'password' | null>(null);
  const [errors, setErrors] = useState<{ cedula?: string; password?: string }>({});
  const [buttonScale] = useState(new Animated.Value(1));
  const [loading, setLoading] = useState(false);
  const formAnim = useRef(new Animated.Value(0)).current;
  const logoAnim = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    Animated.parallel([
      Animated.spring(formAnim, {
        toValue: 1,
        useNativeDriver: true,
        friction: 7,
      }),
      Animated.spring(logoAnim, {
        toValue: 1,
        useNativeDriver: true,
        friction: 3,
        tension: 80,
      }),
    ]).start();
  }, []);

  const validate = () => {
    let valid = true;
    const newErrors: { cedula?: string; password?: string } = {};
    if (!cedula) {
      newErrors.cedula = 'Ingrese su cédula';
      valid = false;
    }
    if (!password) {
      newErrors.password = 'Ingrese su contraseña';
      valid = false;
    }
    setErrors(newErrors);
    return valid;
  };

  const handleLogin = () => {
    if (!validate()) return;
    setLoading(true);
    Animated.sequence([
      Animated.spring(buttonScale, {
        toValue: 0.93,
        useNativeDriver: true,
      }),
      Animated.spring(buttonScale, {
        toValue: 1,
        friction: 3,
        tension: 80,
        useNativeDriver: true,
      }),
    ]).start();

    setTimeout(() => {
      setLoading(false);
      navigation.navigate('Main');
    }, 1500);
  };

  return (
    <KeyboardAvoidingView
      style={styles.container}
      behavior={Platform.OS === 'ios' ? 'padding' : undefined}
    >
      <Image
        style={styles.bgImage}
        source={require('../../assets/frontImg.jpg')}
        blurRadius={3}
      />
      <View style={styles.overlay} />
      <Animated.View
        style={[
          styles.logoContainer,
          {
            transform: [
              {
                scale: logoAnim.interpolate({
                  inputRange: [0, 1],
                  outputRange: [0.7, 1],
                }),
              },
              {
                translateY: logoAnim.interpolate({
                  inputRange: [0, 1],
                  outputRange: [-40, 0],
                }),
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
            transform: [
              {
                translateY: formAnim.interpolate({
                  inputRange: [0, 1],
                  outputRange: [80, 0],
                }),
              },
            ],
          },
        ]}
      >
        <View
          style={[
            styles.inputContainer,
            focusField === 'cedula' && styles.inputContainerFocused,
            errors.cedula && styles.inputContainerError,
          ]}
        >
          <Icon
            name="card-account-details"
            size={24}
            color={focusField === 'cedula' ? '#4f8cff' : errors.cedula ? '#e63946' : '#aaa'}
            style={styles.inputIcon}
          />
          <TextInput
            style={styles.inputs}
            placeholder="Cédula"
            keyboardType="numeric"
            placeholderTextColor="#aaa"
            value={cedula}
            onChangeText={text => {
              setCedula(text);
              if (errors.cedula) setErrors({ ...errors, cedula: undefined });
            }}
            onFocus={() => setFocusField('cedula')}
            onBlur={() => setFocusField(null)}
            returnKeyType="next"
            editable={!loading}
          />
        </View>
        {errors.cedula && <Text style={styles.errorText}>{errors.cedula}</Text>}
        <View
          style={[
            styles.inputContainer,
            focusField === 'password' && styles.inputContainerFocused,
            errors.password && styles.inputContainerError,
          ]}
        >
          <Icon
            name="lock"
            size={24}
            color={focusField === 'password' ? '#4f8cff' : errors.password ? '#e63946' : '#aaa'}
            style={styles.inputIcon}
          />
          <TextInput
            style={styles.inputs}
            placeholder="Contraseña"
            secureTextEntry
            placeholderTextColor="#aaa"
            value={password}
            onChangeText={text => {
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
        <TouchableOpacity
          style={styles.btnForgotPassword}
          onPress={() => Alert.alert('Recuperar contraseña', 'Funcionalidad próximamente disponible')}
          disabled={loading}
        >
          <Text style={styles.btnForgotText}>¿Olvidó su contraseña?</Text>
        </TouchableOpacity>
        <Animated.View style={{ width: '100%', transform: [{ scale: buttonScale }] }}>
          <TouchableOpacity
            style={[styles.buttonContainer, styles.loginButton, loading && { opacity: 0.7 }]}
            onPress={handleLogin}
            activeOpacity={0.85}
            disabled={loading}
          >
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
  container: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: '#DCDCDC',
  },
  bgImage: {
    position: 'absolute',
    width: '100%',
    height: '100%',
    resizeMode: 'cover',
    top: 0,
    left: 0,
  },
  overlay: {
    ...StyleSheet.absoluteFillObject,
    backgroundColor: 'rgba(0,0,40,0.35)',
  },
  logoContainer: {
    alignItems: 'center',
    marginBottom: 40,
  },
  logoTitle: {
    color: '#fff',
    fontWeight: 'bold',
    fontSize: 26,
    textShadowColor: 'rgba(0,0,0,0.9)',
    textShadowOffset: { width: 2, height: 2 },
    textShadowRadius: 4,
    textAlign: 'center',
    letterSpacing: 1,
  },
  logoSubtitle: {
    color: '#fff',
    fontWeight: '600',
    fontSize: 16,
    textShadowColor: 'rgba(0,0,0,0.7)',
    textShadowOffset: { width: 1, height: 1 },
    textShadowRadius: 3,
    textAlign: 'center',
    marginTop: 2,
  },
  form: {
    width: width * 0.88,
    backgroundColor: 'rgba(255,255,255,0.96)',
    borderRadius: 22,
    padding: 26,
    alignItems: 'center',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 8 },
    shadowOpacity: 0.14,
    shadowRadius: 18,
    elevation: 10,
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
    shadowColor: '#808080',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.13,
    shadowRadius: 3.84,
    elevation: 4,
    borderWidth: 1.2,
    borderColor: 'transparent',
  },
  inputContainerFocused: {
    borderColor: '#4f8cff',
    shadowColor: '#4f8cff',
    shadowOpacity: 0.25,
    elevation: 8,
  },
  inputContainerError: {
    borderColor: '#e63946',
    shadowColor: '#e63946',
    shadowOpacity: 0.25,
  },
  inputs: {
    flex: 1,
    height: 45,
    marginLeft: 10,
    color: '#22223b',
    fontSize: 16,
    letterSpacing: 0.2,
  },
  inputIcon: {
    marginLeft: 2,
    marginRight: 2,
  },
  errorText: {
    color: '#e63946',
    fontSize: 13,
    marginBottom: 6,
    alignSelf: 'flex-start',
    marginLeft: 8,
  },
  btnForgotPassword: {
    alignSelf: 'flex-end',
    marginBottom: 10,
  },
  btnForgotText: {
    color: '#4f8cff',
    fontWeight: 'bold',
    fontSize: 14,
    textShadowColor: 'rgba(0,0,0,0.08)',
    textShadowOffset: { width: 1, height: 1 },
    textShadowRadius: 1,
  },
  buttonContainer: {
    height: 48,
    flexDirection: 'row',
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: 10,
    width: '100%',
    borderRadius: 30,
    backgroundColor: 'transparent',
  },
  loginButton: {
    backgroundColor: '#4f8cff',
    shadowColor: '#4f8cff',
    shadowOffset: { width: 0, height: 9 },
    shadowOpacity: 0.5,
    shadowRadius: 12.35,
    elevation: 19,
  },
  loginText: {
    color: 'white',
    fontWeight: 'bold',
    fontSize: 17,
    letterSpacing: 0.5,
  },
});