import React, { useState, useEffect } from 'react';
import { View, Text, FlatList, StyleSheet, ActivityIndicator } from 'react-native';
import { getEgresos } from '../api';

interface Egreso {
  idPlanCuenta: number;
  codigoPlanCuenta: string;
  nombrePlanCuenta: string;
  total_egreso: number;
}

const EgresosScreen: React.FC = () => {
  const [egresos, setEgresos] = useState<Egreso[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      const data = await getEgresos();
      setEgresos(data);
    } catch (error) {
      console.error('Error fetching egresos:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <View style={styles.center}>
        <ActivityIndicator size="large" color="#4f8cff" />
      </View>
    );
  }

  const renderEgreso = ({ item }: { item: Egreso }) => (
    <View style={styles.egresoContainer}>
      <Text style={styles.egresoHeader}>
        {item.codigoPlanCuenta} - {item.nombrePlanCuenta}
      </Text>
      <Text style={styles.monto}>Total Egreso: {item.total_egreso.toFixed(2)}</Text>
    </View>
  );

  const totalEgresos = egresos.reduce((sum, egreso) => sum + egreso.total_egreso, 0);

  return (
    <View style={styles.container}>
      <Text style={styles.title}>Egresos</Text>
      <View style={styles.totalContainer}>
        <Text style={styles.totalText}>Total Egresos: {totalEgresos.toFixed(2)}</Text>
      </View>
      <FlatList
        data={egresos}
        renderItem={renderEgreso}
        keyExtractor={(item) => item.idPlanCuenta.toString()}
        contentContainerStyle={styles.listContainer}
      />
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f5f5f5',
  },
  center: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
  },
  title: {
    fontSize: 24,
    fontWeight: 'bold',
    textAlign: 'center',
    marginVertical: 20,
    color: '#4f8cff',
  },
  totalContainer: {
    backgroundColor: '#dc3545',
    padding: 15,
    marginHorizontal: 10,
    borderRadius: 8,
    marginBottom: 10,
  },
  totalText: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#fff',
    textAlign: 'center',
  },
  listContainer: {
    padding: 10,
  },
  egresoContainer: {
    backgroundColor: '#fff',
    borderRadius: 8,
    padding: 15,
    marginBottom: 10,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
  },
  egresoHeader: {
    fontSize: 16,
    fontWeight: 'bold',
    marginBottom: 5,
    color: '#333',
  },
  monto: {
    fontSize: 14,
    color: '#dc3545',
    fontWeight: 'bold',
  },
});

export default EgresosScreen;
