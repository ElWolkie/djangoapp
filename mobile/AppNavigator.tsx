// AppNavigator.tsx (completo con reload support)
import React, { useState } from 'react';
import { createDrawerNavigator, DrawerContentScrollView, DrawerItemList, DrawerItem } from '@react-navigation/drawer';
import DashboardScreen from './src/screens/DashboardScreen';
import PantallaPersonas from './src/screens/personas';
import { View, Text, Image, StyleSheet, TouchableOpacity } from 'react-native';
import Icon from 'react-native-vector-icons/MaterialCommunityIcons';

const Drawer = createDrawerNavigator();

function CustomDrawerContent(props: any) {
  return (
    <DrawerContentScrollView {...props} contentContainerStyle={{ flex: 1 }}>
      <View style={styles.drawerHeader}>
        <Image
          source={require('./assets/SACFU.png')}
          style={styles.drawerLogo}
          resizeMode="contain"
        />
        <Text style={styles.drawerTitle}>ADMINISTRATIVO</Text>
      </View>
      <DrawerItemList {...props} />
      <View style={{ flex: 1 }} />
      <DrawerItem
        label="Cerrar Sesión"
        icon={({ color, size }) => (
          <Icon name="logout" color="#e63946" size={size} />
        )}
        onPress={() => {
          props.navigation.replace('Login');
        }}
        labelStyle={{ color: '#e63946', fontWeight: 'bold' }}
      />
    </DrawerContentScrollView>
  );
}

export default function AppNavigator() {
  // clave para reiniciar pantalla
  const [reloadKey, setReloadKey] = useState(0);

  const handleReload = () => {
    setReloadKey(prev => prev + 1);
  };

  const renderReloadButton = () => (
    <TouchableOpacity onPress={handleReload} style={{ marginRight: 16 }}>
      <Icon name="reload" size={22} color="#fff" />
    </TouchableOpacity>
  );

  return (
    <Drawer.Navigator
      key={reloadKey} // fuerza a reiniciar la pantalla al cambiar
      drawerContent={props => <CustomDrawerContent {...props} />}
      screenOptions={{
        headerStyle: { backgroundColor: '#4f8cff' },
        headerTintColor: '#fff',
        drawerActiveTintColor: '#4f8cff',
        drawerLabelStyle: { fontWeight: 'bold' },
        headerRight: () => renderReloadButton(), // botón de recarga en el header
      }}
    >
      <Drawer.Screen
        name="Dashboard"
        component={DashboardScreen}
        options={{
          drawerIcon: ({ color, size }) => (
            <Icon name="view-dashboard" color={color} size={size} />
          ),
          title: 'Inicio',
        }}
      />
      <Drawer.Screen
        name="Personas"
        component={PantallaPersonas}
        options={{
          drawerIcon: ({ color, size }) => (
            <Icon name="account-group" color={color} size={size} />
          ),
          title: 'Gestión de Personas',
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
});
