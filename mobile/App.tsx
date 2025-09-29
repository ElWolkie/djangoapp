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
import PantallaCohortes from './src/screens/cohortes';
import PantallaCargos from './src/screens/cargos';
import PantallaHonorarios from './src/screens/honorarios';
import PantallaInscripciones from './src/screens/inscripciones';
import PantallaSolicitudes from './src/screens/solicitudes';
import PantallaTramites from './src/screens/tramites';
import PantallaServicios from './src/screens/servicios';
import PantallaRequisitos from './src/screens/requisitos';
import PantallaMonedas from './src/screens/monedas';
import PantallaTasas from './src/screens/tasas';
import { AuthProvider } from './src/contexts/AuthContext';
import { ReloadProvider } from './src/contexts/ReloadContext';

export type RootStackParamList = {
  Login: undefined;
  Main: undefined;
  Personas: undefined;
  Formaciones: undefined;
  TipoFormaciones: undefined;
  Materias: undefined;
  Cohortes: undefined;
  Cargos: undefined;
  Honorarios: undefined;
  Inscripciones: undefined;
  Solicitudes: undefined;
  Tramites: undefined;
  Servicios: undefined;
  Requisitos: undefined;
  Monedas: undefined;
  Tasas: undefined;
  // Agrega aquí otras pantallas si es necesario
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
            <Stack.Screen name="TipoFormaciones" component={PantallaTPFormaciones} options={{ title: 'Tipo Formaciones' }} />
            <Stack.Screen name="Materias" component={PantallaMaterias} options={{ title: 'Materias' }} />
            <Stack.Screen name="Cohortes" component={PantallaCohortes} options={{ title: 'Cohortes' }} />
            <Stack.Screen name="Cargos" component={PantallaCargos} options={{ title: 'Cargos' }} />
            <Stack.Screen name="Honorarios" component={PantallaHonorarios} options={{ title: 'Honorarios' }} />
            <Stack.Screen name="Inscripciones" component={PantallaInscripciones} options={{ title: 'Inscripciones' }} />
            <Stack.Screen name="Solicitudes" component={PantallaSolicitudes} options={{ title: 'Solicitudes' }} />
            <Stack.Screen name="Tramites" component={PantallaTramites} options={{ title: 'Trámites' }} />
            <Stack.Screen name="Servicios" component={PantallaServicios} options={{ title: 'Servicios' }} />
            <Stack.Screen name="Requisitos" component={PantallaRequisitos} options={{ title: 'Requisitos' }} />
            <Stack.Screen name="Monedas" component={PantallaMonedas} options={{ title: 'Monedas' }} />
            <Stack.Screen name="Tasas" component={PantallaTasas} options={{ title: 'Tasas' }} />
          </Stack.Navigator>
        </NavigationContainer>
      </ReloadProvider>
    </AuthProvider>
  );
}
