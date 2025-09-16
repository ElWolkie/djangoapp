// App.tsx
import 'react-native-gesture-handler';
import * as React from 'react';
import { NavigationContainer } from '@react-navigation/native';
import { createStackNavigator } from '@react-navigation/stack';
import LoginScreen from './src/screens/LoginScreen';
import AppNavigator from './AppNavigator';
import PantallaPersonas from './src/screens/personas';
import PantallaFormaciones from './src/screens/formaciones';
import PantallaTPFormaciones from './src/screens/tipoFormaciones';
import PantallaMaterias from './src/screens/materias';
import { AuthProvider } from './src/contexts/AuthContext';
import { ReloadProvider } from './src/contexts/ReloadContext';

export type RootStackParamList = {
  Login: undefined;
  Main: undefined;
  Personas: undefined;
  Formaciones: undefined;
  TipoFormaciones: undefined;
  Materias: undefined;
};

const Stack = createStackNavigator<RootStackParamList>();

export default function App() {
  return (
    <AuthProvider>
      <ReloadProvider>
        <NavigationContainer>
          <Stack.Navigator initialRouteName="Login">
            <Stack.Screen name="Login" component={LoginScreen} options={{ headerShown: false }} />
            <Stack.Screen name="Main" component={AppNavigator} options={{ headerShown: false }} />
            <Stack.Screen name="Personas" component={PantallaPersonas} options={{ title: 'Mi Sistema' }} />
            <Stack.Screen name="Formaciones" component={PantallaFormaciones} options={{ title: 'Formaciones' }} />
            <Stack.Screen name="TipoFormaciones" component={PantallaTPFormaciones} options={{ title: 'Formaciones' }} />
            <Stack.Screen name="Materias" component={PantallaMaterias} options={{ title: 'Materias' }} />
          </Stack.Navigator>
        </NavigationContainer>
      </ReloadProvider>
    </AuthProvider>
  );
}
