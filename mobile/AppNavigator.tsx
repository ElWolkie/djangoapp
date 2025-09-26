// AppNavigator.tsx
import React, { useContext, useState } from 'react';
import {
  createDrawerNavigator,
  DrawerContentScrollView,
  DrawerItemList,
  DrawerItem,
} from '@react-navigation/drawer';
import DashboardScreen from './src/screens/DashboardScreen';
import PantallaPersonas from './src/screens/personas';
import PantallaFormaciones from './src/screens/formaciones';
import PantallaTPFormaciones from './src/screens/tipoFormaciones';
import PantallaMaterias from './src/screens/materias';
import { View, Text, Image, StyleSheet, TouchableOpacity } from 'react-native';
import Icon from 'react-native-vector-icons/MaterialCommunityIcons';
import { ReloadContext } from './src/contexts/ReloadContext';

const Drawer = createDrawerNavigator();

function CustomDrawerContent(props: any) {

  const navigateTo = (screenName: string) => {
    props.navigation.navigate(screenName);
  };

  return (
    <DrawerContentScrollView {...props} contentContainerStyle={{ flex: 1 }}>
      <View style={styles.drawerHeader}>
        <Image source={require('./assets/SACFU.png')} style={styles.drawerLogo} resizeMode="contain" />
        <Text style={styles.drawerTitle}>ADMINISTRATIVO</Text>
      </View>

      <DrawerItemList {...props} />

      <View style={{ flex: 1 }} />

      <DrawerItem
        label="Cerrar Sesión"
        icon={({ color, size }) => <Icon name="logout" color="#e63946" size={size} />}
        onPress={() => {
          props.navigation.replace('Login');
        }}
        labelStyle={{ color: '#e63946', fontWeight: 'bold' }}
      />
    </DrawerContentScrollView>
  );
}

export default function AppNavigator() {
  // Usamos ReloadContext para triggerReload (botón funcional)
  const { triggerReload } = useContext(ReloadContext);

  const renderReloadButton = () => (
    <TouchableOpacity onPress={() => { triggerReload(); }} style={{ marginRight: 16 }}>
      <Icon name="reload" size={22} color="#fff" />
    </TouchableOpacity>
  );

  return (
    <Drawer.Navigator
      drawerContent={props => <CustomDrawerContent {...props} />}
      screenOptions={{
        headerStyle: { backgroundColor: '#4f8cff' },
        headerTintColor: '#fff',
        drawerActiveTintColor: '#4f8cff',
        drawerLabelStyle: { fontWeight: 'bold' },
        headerRight: () => renderReloadButton(),
      }}
    >
      <Drawer.Screen
        name="Dashboard"
        component={DashboardScreen}
        options={{
          drawerIcon: ({ color, size }) => <Icon name="view-dashboard" color={color} size={size} />,
          title: 'Inicio',
        }}
      />
      <Drawer.Screen
        name="Personas"
        component={PantallaPersonas}
        options={{
          drawerIcon: ({ color, size }) => <Icon name="account-group" color={color} size={size} />,
          title: 'Gestión de Personas',
        }}
      />
      <Drawer.Screen
        name="Formaciones"
        component={PantallaFormaciones}
        options={{
          drawerIcon: ({ color, size }) => <Icon name="school" color={color} size={size} />,
          title: 'Formaciones',
        }}
      />
      <Drawer.Screen
        name="TipoFormaciones"
        component={PantallaTPFormaciones}
        options={{
          drawerIcon: ({ color, size }) => <Icon name="format-list-bulleted" color={color} size={size} />,
          title: 'Tipo Formaciones',
        }}
      />
      <Drawer.Screen
        name="Materias"
        component={PantallaMaterias}
        options={{
          drawerIcon: ({ color, size }) => <Icon name="format-list-bulleted" color={color} size={size} />,
          title: 'Materias',
        }}
      />
    </Drawer.Navigator>
  );
}

const styles = StyleSheet.create({
  drawerHeader: {
    alignItems: 'center',
    paddingVertical: 24,
    borderBottomWidth: 1,
    borderBottomColor: '#eee',
    backgroundColor: '#fff',
  },
  drawerLogo: {
    width: 140,
    height: 60,
    marginBottom: 8,
    borderRadius: 0,
  },
  drawerTitle: {
    fontWeight: 'bold',
    color: '#4f8cff',
    fontSize: 16,
    letterSpacing: 1,
  },
  menuSection: {
    marginTop: 10,
  },
  menuItem: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: 12,
    paddingHorizontal: 16,
    backgroundColor: '#f8f9fa',
    borderRadius: 8,
    marginHorizontal: 10,
    marginBottom: 5,
  },
  menuText: {
    flex: 1,
    fontSize: 16,
    fontWeight: 'bold',
    color: '#4f8cff',
    marginLeft: 10,
  },
  submenu: {
    marginLeft: 20,
    marginRight: 10,
  },
  submenuItem: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: 10,
    paddingHorizontal: 16,
    backgroundColor: '#fff',
    borderRadius: 6,
    marginBottom: 2,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.1,
    shadowRadius: 2,
    elevation: 1,
  },
  submenuText: {
    fontSize: 14,
    color: '#666',
    marginLeft: 10,
  },
});
