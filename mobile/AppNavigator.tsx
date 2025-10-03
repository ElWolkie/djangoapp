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
import { 
  View, 
  Text, 
  Image, 
  StyleSheet, 
  TouchableOpacity, 
  Animated, 
  Easing, 
  Platform,
  ScrollView 
} from 'react-native';
import Icon from 'react-native-vector-icons/MaterialCommunityIcons';
import { ReloadContext } from './src/contexts/ReloadContext';
import { AuthContext } from './src/contexts/AuthContext';

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

  /* ---------- GESTIONAR TRÁMITE ---------- */
  const [openTramPanel, setOpenTramPanel] = useState(false);
  const animTramPanel = useRef(new Animated.Value(0)).current;

  const toggleTramPanel = () => {
    const toValue = openTramPanel ? 0 : 1;
    setOpenTramPanel(!openTramPanel);
    Animated.timing(animTramPanel, { 
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
  const rotateTramPanel = animTramPanel.interpolate({ 
    inputRange: [0,1], 
    outputRange: ['0deg','180deg'] 
  });

  // Alturas animadas - usando maxHeight en lugar de height
  const academicaMaxHeight = animAcademica.interpolate({
    inputRange: [0, 1],
    outputRange: [0, 1000] // Valor suficientemente alto
  });

  const tramPanelMaxHeight = animTramPanel.interpolate({
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
          label="Gestión de Personas"
          icon={({ color, size }) => <Icon name="account-group" color={color} size={size} />}
          onPress={() => navigateTo('Personas')}
          labelStyle={styles.drawerLabel}
        />

        {/* ACORDEÓN: ACADEMICA - ahora SIN sub-acordeón (solo acordeón principal) */} 
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
            {/* Antes había un sub-acordeón (Formaciones) — lo comenté/eliminé para simplificar */}
            {/* Mantengo Inscripciones visible dentro del acordeón para consistencia */}
            
            {/* Formaciones y TipoFormaciones comentados (puedo reactivar luego si deseas) */}
            {/*
            <DrawerItem
              label="Formaciones"
              icon={({ color, size }) => <Icon name="school" color={color} size={size} />}
              onPress={() => navigateTo('Formaciones')}
              labelStyle={styles.submenuText}
              style={styles.submenuItem}
            />
            <DrawerItem
              label="Tipo Formaciones"
              icon={({ color, size }) => <Icon name="format-list-bulleted" color={color} size={size} />}
              onPress={() => navigateTo('TipoFormaciones')}
              labelStyle={styles.submenuText}
              style={styles.submenuItem}
            />
            */}

            {/* Otros items académicos (comentados excepto Inscripciones) */}
            {/*
            <DrawerItem
              label="Materias"
              icon={({ color, size }) => <Icon name="book-open-variant" color={color} size={size} />}
              onPress={() => navigateTo('Materias')}
              labelStyle={styles.submenuText}
              style={styles.submenuItem}
            />
            <DrawerItem
              label="Cohortes"
              icon={({ color, size }) => <Icon name="calendar-multiple" color={color} size={size} />}
              onPress={() => navigateTo('Cohortes')}
              labelStyle={styles.submenuText}
              style={styles.submenuItem}
            />
            <DrawerItem
              label="Cargos"
              icon={({ color, size }) => <Icon name="briefcase" color={color} size={size} />}
              onPress={() => navigateTo('Cargos')}
              labelStyle={styles.submenuText}
              style={styles.submenuItem}
            />
            <DrawerItem
              label="Honorarios"
              icon={({ color, size }) => <Icon name="currency-usd" color={color} size={size} />}
              onPress={() => navigateTo('Honorarios')}
              labelStyle={styles.submenuText}
              style={styles.submenuItem}
            />
            */}

            {/* Inscripciones queda activo */}
            <DrawerItem
              label="Inscripciones"
              icon={({ color, size }) => <Icon name="clipboard-list" color={color} size={size} />}
              onPress={() => navigateTo('Inscripciones')}
              labelStyle={styles.submenuText}
              style={styles.submenuItem}
            />
          </Animated.View>
        </View>

        {/* TRÁMITE - ahora SIN sub-acordeón (solo acordeón principal) */} 
        <View style={styles.sectionContainer}>
          <TouchableOpacity 
            style={styles.accordionHeader} 
            onPress={toggleTramPanel}
            activeOpacity={0.7}
          >
            <View style={styles.accordionTitleRow}>
              <Icon name="file-document-multiple-outline" size={20} color="#4f8cff" />
              <Text style={styles.accordionTitle}>Gestionar Trámite</Text>
            </View>
            <Animated.View style={{ transform: [{ rotate: rotateTramPanel }] }}>
              <Icon name="chevron-down" size={22} color="#4f8cff" />
            </Animated.View>
          </TouchableOpacity>

          <Animated.View style={[
            styles.accordionContent, 
            { maxHeight: tramPanelMaxHeight }
          ]}>
            {/* Sub-acordeón eliminado: dejo Solicitudes visible aquí y comento el resto */}
            <DrawerItem
              label="Solicitudes"
              icon={({ color, size }) => <Icon name="file-document" color={color} size={size} />}
              onPress={() => navigateTo('Solicitudes')}
              labelStyle={styles.submenuText}
              style={styles.submenuItem}
            />

            {/* Trámites, Servicios y Requisitos comentados por ahora */}
            {/*
            <DrawerItem
              label="Trámites"
              icon={({ color, size }) => <Icon name="file-certificate" color={color} size={size} />}
              onPress={() => navigateTo('Tramites')}
              labelStyle={styles.submenuText}
              style={styles.submenuItem}
            />
            <DrawerItem
              label="Servicio Expedito"
              icon={({ color, size }) => <Icon name="truck-fast" color={color} size={size} />}
              onPress={() => navigateTo('Servicios')}
              labelStyle={styles.submenuText}
              style={styles.submenuItem}
            />
            <DrawerItem
              label="Requisitos"
              icon={({ color, size }) => <Icon name="check-circle-outline" color={color} size={size} />}
              onPress={() => navigateTo('Requisitos')}
              labelStyle={styles.submenuText}
              style={styles.submenuItem}
            />
            */}
          </Animated.View>
        </View>

        {/* FINANZAS - comentado por completo (no lo necesitamos ahora) */}
        {/*
        <View style={styles.sectionContainer}>
          <TouchableOpacity 
            style={styles.accordionHeader} 
            onPress={toggleFinanzas}
            activeOpacity={0.7}
          >
            <View style={styles.accordionTitleRow}>
              <Icon name="finance" size={20} color="#4f8cff" />
              <Text style={styles.accordionTitle}>Finanzas</Text>
            </View>
            <Animated.View style={{ transform: [{ rotate: rotateFin }] }}>
              <Icon name="chevron-down" size={22} color="#4f8cff" />
            </Animated.View>
          </TouchableOpacity>

          <Animated.View style={[
            styles.accordionContent, 
            { maxHeight: finanzasMaxHeight }
          ]}>
            <DrawerItem
              label="Monedas"
              icon={({ color, size }) => <Icon name="currency-usd-circle" color={color} size={size} />}
              onPress={() => navigateTo('Monedas')}
              labelStyle={styles.submenuText}
              style={styles.submenuItem}
            />
            <DrawerItem
              label="Tasas"
              icon={({ color, size }) => <Icon name="percent" color={color} size={size} />}
              onPress={() => navigateTo('Tasas')}
              labelStyle={styles.submenuText}
              style={styles.submenuItem}
            />
          </Animated.View>
        </View>
        */}

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
      <Drawer.Screen name="Personas" component={PantallaPersonas} options={{ title: 'Gestión de Personas' }} />
      <Drawer.Screen name="Formaciones" component={PantallaFormaciones} options={{ title: 'Formaciones' }} />
      <Drawer.Screen name="TipoFormaciones" component={PantallaTPFormaciones} options={{ title: 'Tipo Formaciones' }} />
      <Drawer.Screen name="Materias" component={PantallaMaterias} options={{ title: 'Materias' }} />
      <Drawer.Screen name="Cohortes" component={PantallaCohortes} options={{ title: 'Cohortes' }} />
      <Drawer.Screen name="Cargos" component={PantallaCargos} options={{ title: 'Cargos' }} />
      <Drawer.Screen name="Honorarios" component={PantallaHonorarios} options={{ title: 'Honorarios' }} />
      <Drawer.Screen name="Inscripciones" component={PantallaInscripciones} options={{ title: 'Inscripciones' }} />
      <Drawer.Screen name="Solicitudes" component={PantallaSolicitudes} options={{ title: 'Solicitudes' }} />
      <Drawer.Screen name="Tramites" component={PantallaTramites} options={{ title: 'Trámites' }} />
      <Drawer.Screen name="Servicios" component={PantallaServicios} options={{ title: 'Servicios' }} />
      <Drawer.Screen name="Requisitos" component={PantallaRequisitos} options={{ title: 'Requisitos' }} />
      <Drawer.Screen name="Monedas" component={PantallaMonedas} options={{ title: 'Monedas' }} />
      <Drawer.Screen name="Tasas" component={PantallaTasas} options={{ title: 'Tasas' }} />
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
  subAccordionHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingVertical: 10,
    paddingHorizontal: 16,
    backgroundColor: '#f8f9fa',
    marginTop: 4,
  },
  subAccordionTitleRow: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  subAccordionTitle: {
    marginLeft: 10,
    fontSize: 14,
    color: '#4f8cff',
    fontWeight: '700',
  },
  subAccordionContent: {
    overflow: 'hidden',
    backgroundColor: '#fff',
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
