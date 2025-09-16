import 'react-native-gesture-handler';
import * as React from 'react';
import { NavigationContainer } from '@react-navigation/native';
import { createStackNavigator } from '@react-navigation/stack';
import LoginScreen from './src/screens/LoginScreen';
import AppNavigator from './AppNavigator';
import PantallaPersonas from './src/screens/personas';

export type RootStackParamList = {
  Login: undefined;
  Main: undefined;
  Personas: undefined;
};

const Stack = createStackNavigator<RootStackParamList>();

export default function App() {
  return (
    <NavigationContainer>
      <Stack.Navigator initialRouteName="Login">
        <Stack.Screen
          name="Login"
          component={LoginScreen}
          options={{ headerShown: false }}
        />
        <Stack.Screen
          name="Main"
          component={AppNavigator}
          options={{ headerShown: false }}
        />
        <Stack.Screen
          name="Personas"
          component={PantallaPersonas}
          options={{ title: 'Mi Sistema' }}
        />
      </Stack.Navigator>
    </NavigationContainer>
  );
}