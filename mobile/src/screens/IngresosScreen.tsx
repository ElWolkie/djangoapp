import React, { useState, useEffect } from 'react';
import { View, Text, FlatList, StyleSheet, ActivityIndicator } from 'react-native';
import { getIngresos } from '../api';

interface Ingreso {
  idPlanCuenta: number;
  codigoPlanCuenta: string;
  nombrePlanCuenta: string;
  total_ingreso: number;
}

const IngresosScreen: React.FC = () => {
  const [ingresos, setIngresos] = useState<Ingreso[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      const data = await getIngresos();
      setIngresos(data);
    } catch (error) {
      console.error('Error fetching ingresos:', error);
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

  const renderIngreso = ({ item }: { item: Ingreso }) => (
    <View style={styles.ingresoContainer}>
      <Text style={styles.ingresoHeader}>
        {item.codigoPlanCuenta} - {item.nombrePlanCuenta}
      </Text>
      <Text style={styles.monto}>Total Ingreso: {item.total_ingreso.toFixed(2)}</Text>
    </View>
  );

  const totalIngresos = ingresos.reduce((sum, ingreso) => sum + ingreso.total_ingreso, 0);

  return (
    <View style={styles.container}>
      <Text style={styles.title}>Ingresos</Text>
      <View style={styles.totalContainer}>
        <Text style={styles.totalText}>Total Ingresos: {totalIngresos.toFixed(2)}</Text>
      </View>
      <FlatList
        data={ingresos}
        renderItem={renderIngreso}
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
    backgroundColor: '#28a745',
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
  ingresoContainer: {
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
  ingresoHeader: {
    fontSize: 16,
    fontWeight: 'bold',
    marginBottom: 5,
    color: '#333',
  },
  monto: {
    fontSize: 14,
    color: '#28a745',
    fontWeight: 'bold',
  },
});

export default IngresosScreen;
