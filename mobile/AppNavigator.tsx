// AppNavigator.tsx
import React, { useContext, useRef, useState } from 'react';
import {
  createDrawerNavigator,
  DrawerContentScrollView,
  DrawerItem,
} from '@react-navigation/drawer';
import DashboardScreen from './src/screens/DashboardScreen';
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
import PagoScreen from './src/screens/pago'; // 🆕 IMPORTAR PAGO SCREEN
import PagoMovilFicticioScreen from './src/screens/PagoMovilFicticioScreen';
import { 
  View, 
  Text, 
  Image, 
  StyleSheet, 
  TouchableOpacity, 
  Animated, 
  Easing,
  ScrollView 
} from 'react-native';
import Icon from 'react-native-vector-icons/MaterialCommunityIcons';
import { ReloadContext } from './src/contexts/ReloadContext';
import { AuthContext } from './src/contexts/AuthContext';

// 🆕 Crear el Drawer Navigator sin tipos complejos temporalmente
const Drawer = createDrawerNavigator();

function CustomDrawerContent(props: any) {
  const { navigation } = props;
  const { logout, user } = useContext(AuthContext);

  /* ---------- GESTIÓN ACADÉMICA ---------- */
  const [openAcademica, setOpenAcademica] = useState(false);
  const animAcademica = useRef(new Animated.Value(0)).current;

  const toggleAcademica = () => {
    const toValue = openAcademica ? 0 : 1;
    setOpenAcademica(!openAcademica);
    Animated.timing(animAcademica, { 
      toValue, 
      duration: 300, 
      easing: Easing.out(Easing.cubic), 
      useNativeDriver: false 
    }).start();
  };

  /* ---------- GESTIÓN FINANCIERA ---------- */
  const [openFinanzas, setOpenFinanzas] = useState(false);
  const animFinanzas = useRef(new Animated.Value(0)).current;

  const toggleFinanzas = () => {
    const toValue = openFinanzas ? 0 : 1;
    setOpenFinanzas(!openFinanzas);
    Animated.timing(animFinanzas, { 
      toValue, 
      duration: 300, 
      easing: Easing.out(Easing.cubic), 
      useNativeDriver: false 
    }).start();
  };

  const navigateTo = (screenName: string) => {
    navigation.navigate(screenName);
    // Cerrar el drawer después de navegar (opcional)
    navigation.closeDrawer();
  };

  // Animaciones de rotación
  const rotateAcademica = animAcademica.interpolate({ 
    inputRange: [0,1], 
    outputRange: ['0deg','180deg'] 
  });
  const rotateFinanzas = animFinanzas.interpolate({ 
    inputRange: [0,1], 
    outputRange: ['0deg','180deg'] 
  });

  // Alturas animadas - usando maxHeight en lugar de height
  const academicaMaxHeight = animAcademica.interpolate({
    inputRange: [0, 1],
    outputRange: [0, 1000]
  });

  const finanzasMaxHeight = animFinanzas.interpolate({
    inputRange: [0, 1],
    outputRange: [0, 800]
  });

  // displayName fallback
  const userDisplay = user?.displayName ?? user?.nombres ?? user?.name ?? null;

  return (
    <View style={styles.container}>
      <DrawerContentScrollView 
        {...props}
        contentContainerStyle={styles.scrollContainer}
        showsVerticalScrollIndicator={true}
        scrollEnabled={true}
      >
        <View style={styles.drawerHeader}>
          <Image source={require('./assets/SACFU.png')} style={styles.drawerLogo} resizeMode="contain" />
          <Text style={styles.drawerTitle}>ADMINISTRATIVO</Text>
          {userDisplay && <Text style={styles.userText}>{userDisplay}</Text>}
        </View>

        <DrawerItem
          label="Inicio"
          icon={({ color, size }) => <Icon name="view-dashboard" color={color} size={size} />}
          onPress={() => navigateTo('Dashboard')}
          labelStyle={styles.drawerLabel}
        />

        <DrawerItem
          label="Mi Perfil"
          icon={({ color, size }) => <Icon name="account" color={color} size={size} />}
          onPress={() => navigateTo('Personas')}
          labelStyle={styles.drawerLabel}
        />

        {/* ACORDEÓN: ACADEMICA */}
        <View style={styles.sectionContainer}>
          <TouchableOpacity 
            style={styles.accordionHeader} 
            onPress={toggleAcademica}
            activeOpacity={0.7}
          >
            <View style={styles.accordionTitleRow}>
              <Icon name="school-outline" size={20} color="#4f8cff" />
              <Text style={styles.accordionTitle}>Gestión Académica</Text>
            </View>
            <Animated.View style={{ transform: [{ rotate: rotateAcademica }] }}>
              <Icon name="chevron-down" size={22} color="#4f8cff" />
            </Animated.View>
          </TouchableOpacity>

          <Animated.View style={[
            styles.accordionContent, 
            { maxHeight: academicaMaxHeight }
          ]}>
            {/* Inscripciones activo */}
            <DrawerItem
              label="Inscripciones"
              icon={({ color, size }) => <Icon name="clipboard-list" color={color} size={size} />}
              onPress={() => navigateTo('Inscripciones')}
              labelStyle={styles.submenuText}
              style={styles.submenuItem}
            />
          </Animated.View>
        </View>

        {/* 🆕 ACORDEÓN: FINANZAS */}
        <View style={styles.sectionContainer}>
          <TouchableOpacity 
            style={styles.accordionHeader} 
            onPress={toggleFinanzas}
            activeOpacity={0.7}
          >
            <View style={styles.accordionTitleRow}>
              <Icon name="cash-multiple" size={20} color="#4f8cff" />
              <Text style={styles.accordionTitle}>Gestión Financiera</Text>
            </View>
            <Animated.View style={{ transform: [{ rotate: rotateFinanzas }] }}>
              <Icon name="chevron-down" size={22} color="#4f8cff" />
            </Animated.View>
          </TouchableOpacity>

          <Animated.View style={[
            styles.accordionContent, 
            { maxHeight: finanzasMaxHeight }
          ]}>
            {/* Pago activo */}
            <DrawerItem
              label="Procesar Pagos"
              icon={({ color, size }) => <Icon name="credit-card-check" color={color} size={size} />}
              onPress={() => navigateTo('Pagos')}
              labelStyle={styles.submenuText}
              style={styles.submenuItem}
            />
          </Animated.View>
        </View>

        {/* Espacio para empujar el logout hacia abajo */}
        <View style={styles.spacer} />
      </DrawerContentScrollView>

      {/* Botón de cerrar sesión fuera del ScrollView */} 
      <View style={styles.logoutContainer}>
        <DrawerItem
          label="Cerrar Sesión"
          icon={({ color, size }) => <Icon name="logout" color="#e63946" size={size} />}
          onPress={async () => {
            try {
              await logout();
            } catch (e) {
              console.warn('Logout error', e);
            }
            navigation.reset({ index: 0, routes: [{ name: 'Login' }] });
          }}
          labelStyle={styles.logoutText}
        />
      </View>
    </View>
  );
}

export default function AppNavigator() {
  const { triggerReload } = React.useContext(ReloadContext);

  const renderReloadButton = () => (
    <TouchableOpacity onPress={() => { triggerReload(); }} style={{ marginRight: 16 }}>
      <Icon name="reload" size={22} color="#fff" />
    </TouchableOpacity>
  );

  return (
    <Drawer.Navigator
      drawerContent={(props) => <CustomDrawerContent {...props} />}
      screenOptions={{
        headerStyle: { backgroundColor: '#4f8cff' },
        headerTintColor: '#fff',
        drawerActiveTintColor: '#4f8cff',
        drawerLabelStyle: { fontWeight: '600', fontSize: 14 },
        headerRight: () => renderReloadButton(),
        drawerStyle: {
          width: 320,
        },
      }}
    >
      <Drawer.Screen name="Dashboard" component={DashboardScreen} options={{ title: 'Inicio' }} />
      <Drawer.Screen name="Personas" component={PantallaPersonas} options={{ title: 'Mi Perfil' }} />
      <Drawer.Screen name="Formaciones" component={PantallaFormaciones} options={{ title: 'Formaciones' }} />
      <Drawer.Screen name="TipoFormaciones" component={PantallaTPFormaciones} options={{ title: 'Tipo Formaciones' }} />
      <Drawer.Screen name="Materias" component={PantallaMaterias} options={{ title: 'Materias' }} />
      <Drawer.Screen name="Cohortes" component={PantallaCohortes} options={{ title: 'Cohortes' }} />
      <Drawer.Screen name="Cargos" component={PantallaCargos} options={{ title: 'Cargos' }} />
      <Drawer.Screen name="Honorarios" component={PantallaHonorarios} options={{ title: 'Honorarios' }} />
      <Drawer.Screen name="Inscripciones" component={PantallaInscripciones} options={{ title: 'Inscripciones' }} />
      {/* 🆕 AGREGAR PANTALLA DE PAGOS AL DRAWER */}
      <Drawer.Screen name="Pagos" component={PagoScreen} options={{ title: 'Procesar Pagos' }} />
      <Drawer.Screen name="Solicitudes" component={PantallaSolicitudes} options={{ title: 'Solicitudes' }} />
      <Drawer.Screen name="Tramites" component={PantallaTramites} options={{ title: 'Trámites' }} />
      <Drawer.Screen name="Servicios" component={PantallaServicios} options={{ title: 'Servicios' }} />
      <Drawer.Screen name="Requisitos" component={PantallaRequisitos} options={{ title: 'Requisitos' }} />
      <Drawer.Screen name="Monedas" component={PantallaMonedas} options={{ title: 'Monedas' }} />
      <Drawer.Screen name="Tasas" component={PantallaTasas} options={{ title: 'Tasas' }} />
      <Drawer.Screen name="PagoMovilFicticio" component={PagoMovilFicticioScreen} options={{ title: 'Pago Móvil' }} />
    </Drawer.Navigator>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  scrollContainer: {
    flexGrow: 1,
    paddingBottom: 10,
  },
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
  },
  drawerTitle: {
    fontWeight: 'bold',
    color: '#4f8cff',
    fontSize: 16,
    letterSpacing: 1,
  },
  userText: {
    marginTop: 6,
    color: '#666',
    fontWeight: '600',
    fontSize: 14,
  },
  drawerLabel: {
    fontWeight: '700',
    color: '#222',
    fontSize: 14,
  },
  sectionContainer: {
    marginTop: 8,
    paddingHorizontal: 8,
  },
  accordionHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingVertical: 12,
    paddingHorizontal: 12,
    borderRadius: 8,
    backgroundColor: '#f8f9fa',
    marginBottom: 4,
  },
  accordionTitleRow: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  accordionTitle: {
    marginLeft: 10,
    fontSize: 16,
    color: '#4f8cff',
    fontWeight: '700',
  },
  accordionContent: {
    overflow: 'hidden',
    backgroundColor: '#fff',
    borderBottomLeftRadius: 8,
    borderBottomRightRadius: 8,
    marginBottom: 8,
  },
  submenuItem: {
    paddingHorizontal: 8,
    paddingVertical: 4,
  },
  submenuText: {
    fontSize: 13,
    color: '#444',
    marginLeft: 8,
    fontWeight: '600',
  },
  spacer: {
    height: 20,
  },
  logoutContainer: {
    borderTopWidth: 1,
    borderTopColor: '#eee',
    backgroundColor: '#fff',
  },
  logoutText: {
    color: '#e63946',
    fontWeight: 'bold',
    fontSize: 14,
  },
});