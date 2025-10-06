import React, { useState, useEffect, useContext } from 'react';
import { AuthContext } from '../contexts/AuthContext';
import {
  View,
  Text,
  StyleSheet,
  Dimensions,
  Image,
  ScrollView,
  ActivityIndicator,
} from 'react-native';
import Icon from 'react-native-vector-icons/MaterialCommunityIcons';
import api from '../api/api';

const { width } = Dimensions.get('window');
const CARD_WIDTH = width - 48;
interface Persona {
  idPersona: number;
  nombres: string;
  apellidos: string;
  cedula: string;
  telefono: string;
  correo: string;
  rif?: string;
  tipos: { idTP: number; nombreTP: string }[];
  estadoPersona: 'ACTIVO' | 'INACTIVO';
  fechaPersona: string;
  direccion?: string;
}

export default function MiPerfil() {
  const { user } = useContext(AuthContext);

  const [persona, setPersona] = useState<Persona | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const res = await api.get<Persona[]>('/api/personas/');
        const data = res.data.map(p => ({ ...p, tipos: p.tipos ?? [] }));

        console.log('🔍 Datos obtenidos del backend:', data);
        console.log('👤 Cédula del usuario autenticado:', user?.cedula);

        console.log('📋 Todos los datos obtenidos:', data);

        if (user?.cedula) {
          const filteredData = data.filter(persona => {
            const cleanedCedula = persona.cedula.replace(/^[A-Z]-/, ''); // Eliminar prefijo de letra y guion
            return cleanedCedula === user.cedula;
          });
          console.log('📋 Datos filtrados:', filteredData);
          setPersona(filteredData[0] || null);
        } else {
          setError('No se encontró información del usuario autenticado.');
        }
      } catch (err: any) {
        console.error('❌ Error al obtener datos:', err);
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [user]);

  if (loading) {
    return <View style={styles.center}><ActivityIndicator size="large" color="#4f8cff" /></View>;
  }

  if (error) {
    return <View style={styles.center}><Text style={styles.errorText}>{error}</Text></View>;
  }

  if (!persona) {
    return (
      <View style={styles.center}>
        <Text style={styles.errorText}>No se encontraron datos del usuario.</Text>
      </View>
    );
  }

  return (
    <ScrollView contentContainerStyle={styles.container}>
      <View style={styles.card}>
        <Icon
          name="account-circle"
          size={100}
          color="#4f8cff"
          style={styles.profileImage}
        />
        <Text style={styles.name}>{persona.nombres} {persona.apellidos}</Text>
        <Text style={styles.cedula}>Cédula: {persona.cedula}</Text>

        <View style={styles.infoRow}>
          <Icon name="phone" size={20} color="#4f8cff" />
          <Text style={styles.infoText}>{persona.telefono}</Text>
        </View>

        <View style={styles.infoRow}>
          <Icon name="email" size={20} color="#4f8cff" />
          <Text style={styles.infoText}>{persona.correo}</Text>
        </View>

        {persona.rif && (
          <View style={styles.infoRow}>
        <Icon name="file-document" size={20} color="#4f8cff" />
        <Text style={styles.infoText}>RIF: {persona.rif}</Text>
          </View>
        )}

        <View style={styles.infoRow}>
          <Icon name="account" size={20} color="#4f8cff" />
          <Text style={styles.infoText}>Estado: {persona.estadoPersona}</Text>
        </View>

        <View style={styles.infoRow}>
          <Icon name="calendar" size={20} color="#4f8cff" />
          <Text style={styles.infoText}>Registrado: {persona.fechaPersona}</Text>
        </View>

        <View style={styles.infoRow}>
          <Icon name="account-group" size={20} color="#4f8cff" />
          <Text style={styles.infoText}>Tipos: {persona.tipos.map(tp => tp.nombreTP).join(', ') || '—'}</Text>
        </View>

        {persona.direccion && (
          <View style={styles.infoRow}>
            <Icon name="map-marker" size={20} color="#4f8cff" />
            <Text style={styles.infoText}>Dirección: {persona.direccion}</Text>
          </View>
        )}
      </View>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: {
    flexGrow: 1,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: '#f5f7fa',
    paddingVertical: 24,
  },
  card: {
    width: CARD_WIDTH,
    backgroundColor: '#fff',
    borderRadius: 16,
    padding: 24,
    alignItems: 'center',
    shadowColor: '#000',
    shadowOpacity: 0.1,
    shadowOffset: { width: 0, height: 4 },
    shadowRadius: 8,
    elevation: 4,
  },
  profileImage: {
    width: 100,
    height: 100,
    borderRadius: 50,
    marginBottom: 16,
  },
  name: {
    fontSize: 22,
    fontWeight: '700',
    color: '#222',
    marginBottom: 8,
  },
  cedula: {
    fontSize: 16,
    color: '#525f7f',
    marginBottom: 16,
  },
  infoRow: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 12,
  },
  infoText: {
    marginLeft: 8,
    fontSize: 16,
    color: '#525f7f',
  },
  center: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
  },
  errorText: {
    color: 'red',
    fontSize: 16,
  },
});
