// AppNavigator.tsx
import React from 'react';
import {
  createDrawerNavigator,
  DrawerContentScrollView,
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
import PagoScreen from './src/screens/pago';
import PagoMovilFicticioScreen from './src/screens/PagoMovilFicticioScreen';
import CuotasPorPagarScreen from './src/screens/cuotasPorPagar';
import ForgotPasswordScreen from './src/screens/ForgotPasswordScreen';
import {
  View,
  Text,
  Image,
  StyleSheet,
  TouchableOpacity,
  Dimensions,
  Platform,
} from 'react-native';
import Icon from 'react-native-vector-icons/MaterialCommunityIcons';
import { ReloadContext } from './src/contexts/ReloadContext';
import { AuthContext } from './src/contexts/AuthContext';

const Drawer = createDrawerNavigator();
const { height: screenHeight } = Dimensions.get('window');

function CustomDrawerContent(props: any) {
  const { navigation, state } = props;
  const { logout, user } = React.useContext(AuthContext);

  const navigateTo = (screenName: string) => {
    navigation.closeDrawer();
    // ligero delay para que cierre el drawer antes de navegar
    setTimeout(() => navigation.navigate(screenName), 10);
  };

  const userDisplay = user?.displayName ?? user?.nombres ?? user?.name ?? null;
  const isRouteActive = (routeName: string) => state.routes[state.index].name === routeName;

  const handleNavigation = (screenName: string) => navigateTo(screenName);

  return (
    <View style={styles.container}>
      <DrawerContentScrollView
        {...props}
        contentContainerStyle={styles.scrollContainer}
        showsVerticalScrollIndicator={false}
      >
        <View style={styles.drawerHeader}>
          <Image source={require('./assets/SACFU.png')} style={styles.drawerLogo} resizeMode="contain" />
          <Text style={styles.drawerTitle}>SISTEMA ACADÉMICO</Text>
          {userDisplay && <Text style={styles.userText}>{userDisplay}</Text>}
        </View>

        <View style={styles.menuSection}>
          {/* Dashboard */}
          <TouchableOpacity
            style={[styles.menuItem, isRouteActive('Dashboard') && styles.menuItemActive]}
            onPress={() => handleNavigation('Dashboard')}
            activeOpacity={0.7}
          >
            <View style={styles.menuItemContent}>
              <View style={[styles.iconContainer, isRouteActive('Dashboard') && styles.iconContainerActive]}>
                <Icon name="view-dashboard" size={22} color={isRouteActive('Dashboard') ? '#fff' : '#4f8cff'} />
              </View>
              <Text style={[styles.menuItemText, isRouteActive('Dashboard') && styles.menuItemTextActive]}>Inicio</Text>
            </View>
            {isRouteActive('Dashboard') && <View style={styles.activeIndicator} />}
          </TouchableOpacity>

          {/* Personas */}
          <TouchableOpacity
            style={[styles.menuItem, isRouteActive('Personas') && styles.menuItemActive]}
            onPress={() => handleNavigation('Personas')}
            activeOpacity={0.7}
          >
            <View style={styles.menuItemContent}>
              <View style={[styles.iconContainer, isRouteActive('Personas') && styles.iconContainerActive]}>
                <Icon name="account" size={22} color={isRouteActive('Personas') ? '#fff' : '#4f8cff'} />
              </View>
              <Text style={[styles.menuItemText, isRouteActive('Personas') && styles.menuItemTextActive]}>Mi Perfil</Text>
            </View>
            {isRouteActive('Personas') && <View style={styles.activeIndicator} />}
          </TouchableOpacity>

          {/* Inscripciones */}
          <TouchableOpacity
            style={[styles.menuItem, isRouteActive('Inscripciones') && styles.menuItemActive]}
            onPress={() => handleNavigation('Inscripciones')}
            activeOpacity={0.7}
          >
            <View style={styles.menuItemContent}>
              <View style={[styles.iconContainer, isRouteActive('Inscripciones') && styles.iconContainerActive]}>
                <Icon name="clipboard-list" size={22} color={isRouteActive('Inscripciones') ? '#fff' : '#4f8cff'} />
              </View>
              <Text style={[styles.menuItemText, isRouteActive('Inscripciones') && styles.menuItemTextActive]}>Mis Inscripciones</Text>
            </View>
            {isRouteActive('Inscripciones') && <View style={styles.activeIndicator} />}
          </TouchableOpacity>

          {/* Pagos */}
          <TouchableOpacity
            style={[styles.menuItem, isRouteActive('Pagos') && styles.menuItemActive]}
            onPress={() => handleNavigation('Pagos')}
            activeOpacity={0.7}
          >
            <View style={styles.menuItemContent}>
              <View style={[styles.iconContainer, isRouteActive('Pagos') && styles.iconContainerActive]}>
                <Icon name="credit-card-check" size={22} color={isRouteActive('Pagos') ? '#fff' : '#4f8cff'} />
              </View>
              <Text style={[styles.menuItemText, isRouteActive('Pagos') && styles.menuItemTextActive]}>Procesar Pagos</Text>
            </View>
            {isRouteActive('Pagos') && <View style={styles.activeIndicator} />}
          </TouchableOpacity>

          {/* Cuotas */}
          <TouchableOpacity
            style={[styles.menuItem, isRouteActive('Cuotas') && styles.menuItemActive]}
            onPress={() => handleNavigation('Cuotas')}
            activeOpacity={0.7}
          >
            <View style={styles.menuItemContent}>
              <View style={[styles.iconContainer, isRouteActive('Cuotas') && styles.iconContainerActive]}>
                <Icon name="cash-multiple" size={22} color={isRouteActive('Cuotas') ? '#fff' : '#4f8cff'} />
              </View>
              <Text style={[styles.menuItemText, isRouteActive('Cuotas') && styles.menuItemTextActive]}>Cuotas por pagar</Text>
            </View>
            {isRouteActive('Cuotas') && <View style={styles.activeIndicator} />}
          </TouchableOpacity>
        </View>

      </DrawerContentScrollView>

      <View style={styles.logoutContainer}>
        <TouchableOpacity
          style={styles.logoutButton}
          onPress={async () => {
            try {
              await logout();
            } catch (e) {
              console.warn('Logout error', e);
            }
            props.navigation.reset({ index: 0, routes: [{ name: 'Login' }] });
          }}
          activeOpacity={0.7}
        >
          <View style={styles.logoutIconContainer}>
            <Icon name="logout" size={20} color="#e63946" />
          </View>
          <Text style={styles.logoutText}>Cerrar Sesión</Text>
        </TouchableOpacity>
      </View>
    </View>
  );
}

export default function AppNavigator() {
  const { triggerReload } = React.useContext(ReloadContext);

  return (
    <Drawer.Navigator
      drawerContent={(props) => <CustomDrawerContent {...props} />}
      screenOptions={{
        headerStyle: { backgroundColor: '#4f8cff', elevation: 0, shadowOpacity: 0, borderBottomWidth: 0 },
        headerTintColor: '#fff',
        headerTitleStyle: { fontWeight: '700', fontSize: 18 },
        drawerStyle: { width: Platform.OS === 'web' ? 320 : 280, backgroundColor: '#fff' },
        drawerType: Platform.OS === 'web' ? 'front' : 'slide',
        overlayColor: 'rgba(0,0,0,0.5)',
      }}
    >
      {/* Solo Screen/Group/Fragment como hijos del Navigator */}
      <Drawer.Screen name="Dashboard" component={DashboardScreen} options={{ title: 'Inicio' }} />
      <Drawer.Screen name="Personas" component={PantallaPersonas} options={{ title: 'Mi Perfil' }} />
      <Drawer.Screen name="Formaciones" component={PantallaFormaciones} options={{ title: 'Formaciones' }} />
      <Drawer.Screen name="TipoFormaciones" component={PantallaTPFormaciones} options={{ title: 'Tipo Formaciones' }} />
      <Drawer.Screen name="Materias" component={PantallaMaterias} options={{ title: 'Materias' }} />
      <Drawer.Screen name="Cohortes" component={PantallaCohortes} options={{ title: 'Cohortes' }} />
      <Drawer.Screen name="Cargos" component={PantallaCargos} options={{ title: 'Cargos' }} />
      <Drawer.Screen name="Honorarios" component={PantallaHonorarios} options={{ title: 'Honorarios' }} />
      <Drawer.Screen name="Inscripciones" component={PantallaInscripciones} options={{ title: 'Inscripciones' }} />
      <Drawer.Screen name="Pagos" component={PagoScreen} options={{ title: 'Procesar Pagos' }} />
      <Drawer.Screen name="Cuotas" component={CuotasPorPagarScreen} options={{ title: 'Cuotas por pagar' }} />
      <Drawer.Screen name="Solicitudes" component={PantallaSolicitudes} options={{ title: 'Solicitudes' }} />
      <Drawer.Screen name="Tramites" component={PantallaTramites} options={{ title: 'Trámites' }} />
      <Drawer.Screen name="Servicios" component={PantallaServicios} options={{ title: 'Servicios' }} />
      <Drawer.Screen name="Requisitos" component={PantallaRequisitos} options={{ title: 'Requisitos' }} />
      <Drawer.Screen name="Monedas" component={PantallaMonedas} options={{ title: 'Monedas' }} />
      <Drawer.Screen name="Tasas" component={PantallaTasas} options={{ title: 'Tasas' }} />
      <Drawer.Screen name="PagoMovilFicticio" component={PagoMovilFicticioScreen} options={{ title: 'Pago Móvil' }} />
      <Drawer.Screen name="ForgotPassword" component={ForgotPasswordScreen} options={{ title: 'Recuperar Contraseña' }} />
    </Drawer.Navigator>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#fff' },
  scrollContainer: { flexGrow: 1, paddingBottom: 10 },
  drawerHeader: { alignItems: 'center', paddingVertical: 28, paddingHorizontal: 20, borderBottomWidth: 1, borderBottomColor: '#f0f2f5' },
  drawerLogo: { width: 150, height: 65, marginBottom: 10 },
  drawerTitle: { fontWeight: '800', color: '#4f8cff', fontSize: 16, letterSpacing: 0.5, textAlign: 'center' },
  userText: { marginTop: 8, color: '#666', fontWeight: '600', fontSize: 14, textAlign: 'center' },
  menuSection: { flex: 1, paddingHorizontal: 12, paddingTop: 16 },
  menuItem: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', paddingVertical: 14, paddingHorizontal: 16, marginBottom: 6, borderRadius: 12, backgroundColor: '#fff' },
  menuItemActive: { backgroundColor: '#4f8cff' },
  menuItemContent: { flexDirection: 'row', alignItems: 'center', flex: 1 },
  iconContainer: { width: 40, height: 40, borderRadius: 10, backgroundColor: '#f0f7ff', justifyContent: 'center', alignItems: 'center', marginRight: 12 },
  iconContainerActive: { backgroundColor: 'rgba(255,255,255,0.2)' },
  menuItemText: { fontWeight: '600', color: '#333', fontSize: 15, flex: 1 },
  menuItemTextActive: { color: '#fff', fontWeight: '700' },
  activeIndicator: { width: 4, height: 20, backgroundColor: '#fff', borderRadius: 2, marginLeft: 8 },
  flexSpacer: { flex: 1, minHeight: 20 },
  logoutContainer: { borderTopWidth: 1, borderTopColor: '#f0f2f5', paddingHorizontal: 20, paddingVertical: Platform.OS === 'ios' ? 24 : 20 },
  logoutButton: { flexDirection: 'row', alignItems: 'center', paddingVertical: 14, paddingHorizontal: 16, borderRadius: 12, backgroundColor: '#fff' },
  logoutIconContainer: { width: 36, height: 36, borderRadius: 10, backgroundColor: '#ffeaea', justifyContent: 'center', alignItems: 'center', marginRight: 12 },
  logoutText: { color: '#e63946', fontWeight: '700', fontSize: 15 },
});
