import React, { useRef, useEffect } from 'react';
import {
  StyleSheet,
  Text,
  View,
  ScrollView,
  Dimensions,
  Animated,
  StatusBar,
} from 'react-native';
import { useNavigation, NavigationProp } from '@react-navigation/native';
import Icon from 'react-native-vector-icons/MaterialCommunityIcons';

const { width } = Dimensions.get('window');

type RootStackParamList = {
  Personas: undefined;
  Formaciones: undefined;
  TipoFormaciones: undefined;
  Materias: undefined;
  // Agrega aquí otras pantallas si es necesario
};

export default function DashboardScreen() {
  const navigation = useNavigation<NavigationProp<RootStackParamList>>();

  // Animaciones para las cards (ahora solo 2 cards)
  const cardsAnim = useRef([new Animated.Value(0), new Animated.Value(0)]).current;

  useEffect(() => {
    // Solo animaciones de entrada
    Animated.stagger(120, [
      Animated.spring(cardsAnim[0], { toValue: 1, useNativeDriver: true }),
      Animated.spring(cardsAnim[1], { toValue: 1, useNativeDriver: true }),
    ]).start();
  }, []);

  // Datos (sin finanzas / contabilidad)
  const stats = [
    {
      title: 'Solicitudes activas',
      value: 12,
      icon: 'file-document-multiple',
      color: '#fb6340',
      subtitle: 'Último registro: 12/07/2025',
    },
    {
      title: 'Servicios activos',
      value: 7,
      icon: 'truck-fast',
      color: '#2dce89',
      subtitle: 'Más pedido: Certificado',
    },
  ];

  return (
    <View style={styles.container}>
      <StatusBar barStyle="light-content" backgroundColor="#4f8cff" />
      <View style={styles.header}>
        <Text style={styles.headerTitle}>¡Bienvenido!</Text>
      </View>
      <ScrollView
        contentContainerStyle={styles.scrollContent}
        showsVerticalScrollIndicator={false}
      >
        <View style={styles.cardsRow}>
          {stats.map((item, idx) => (
            <Animated.View
              key={item.title}
              style={[
                styles.card,
                {
                  opacity: cardsAnim[idx],
                  transform: [
                    {
                      translateY: cardsAnim[idx].interpolate({
                        inputRange: [0, 1],
                        outputRange: [40, 0],
                      }),
                    },
                  ],
                },
              ]}
            >
              <View style={[styles.iconCircle, { backgroundColor: item.color }]}>
                <Icon name={item.icon} size={28} color="#fff" />
              </View>
              <Text style={styles.cardTitle}>{item.title}</Text>
              <Text style={styles.cardValue}>{item.value}</Text>
              <Text style={styles.cardSubtitle}>{item.subtitle}</Text>
            </Animated.View>
          ))}
        </View>
        {/* Aquí puedes agregar más secciones, gráficas, etc. */}
      </ScrollView>
    </View>
  );
}

const CARD_WIDTH = (width * 0.9 - 24) / 2;

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f5f7fa',
  },
  header: {
    backgroundColor: '#4f8cff',
    paddingTop: 48,
    paddingBottom: 28,
    paddingHorizontal: 24,
    borderBottomLeftRadius: 24,
    borderBottomRightRadius: 24,
    alignItems: 'flex-start',
    elevation: 8,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 8 },
    shadowOpacity: 0.18,
    shadowRadius: 12,
  },
  headerTitle: {
    color: '#fff',
    fontSize: 28,
    fontWeight: 'bold',
    letterSpacing: 0.5,
    textShadowColor: 'rgba(0,0,0,0.15)',
    textShadowOffset: { width: 1, height: 2 },
    textShadowRadius: 4,
  },
  headerSubtitle: {
    color: '#e0eaff',
    fontSize: 16,
    marginTop: 4,
    fontWeight: '600',
  },
  scrollContent: {
    alignItems: 'center',
    paddingVertical: 24,
  },
  cardsRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    justifyContent: 'center',
    gap: 12,
    width: '94%',
  },
  card: {
    width: CARD_WIDTH,
    backgroundColor: '#fff',
    borderRadius: 18,
    padding: 18,
    margin: 6,
    alignItems: 'center',
    shadowColor: '#4f8cff',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.13,
    shadowRadius: 8,
    elevation: 6,
  },
  iconCircle: {
    width: 44,
    height: 44,
    borderRadius: 22,
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: 8,
    shadowColor: '#000',
    shadowOpacity: 0.12,
    shadowOffset: { width: 0, height: 2 },
    shadowRadius: 4,
    elevation: 4,
  },
  cardTitle: {
    fontSize: 13,
    color: '#7b7b93',
    fontWeight: 'bold',
    textAlign: 'center',
    marginBottom: 2,
    textTransform: 'uppercase',
    letterSpacing: 0.2,
  },
  cardValue: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#22223b',
    marginBottom: 2,
    textAlign: 'center',
  },
  cardSubtitle: {
    fontSize: 12,
    color: '#4f8cff',
    textAlign: 'center',
    marginTop: 2,
  },
  sectionContainer: {
    marginTop: 32,
    width: '94%',
    backgroundColor: '#fff',
    borderRadius: 16,
    padding: 18,
    alignItems: 'center',
    shadowColor: '#4f8cff',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.10,
    shadowRadius: 8,
    elevation: 4,
  },
  sectionTitle: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#4f8cff',
    marginBottom: 10,
  },
  sectionButton: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#4f8cff',
    paddingVertical: 10,
    paddingHorizontal: 18,
    borderRadius: 30,
    marginTop: 6,
  },
  sectionButtonText: {
    color: '#fff',
    fontWeight: 'bold',
    fontSize: 16,
  },
});
