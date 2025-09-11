import React, { useState, useEffect } from 'react';
import { View, Text, FlatList, StyleSheet, ActivityIndicator } from 'react-native';
import { getBalanceCuentas } from '../api';

interface TipoCuenta {
  tipoPlanCuenta: string;
  total_debe: number;
  total_haber: number;
  saldo: string;
}

const BalanceCuentasScreen: React.FC = () => {
  const [tiposCuentas, setTiposCuentas] = useState<TipoCuenta[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      const data = await getBalanceCuentas();
      setTiposCuentas(data);
    } catch (error) {
      console.error('Error fetching balance de cuentas:', error);
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

  const renderTipoCuenta = ({ item }: { item: TipoCuenta }) => (
    <View style={styles.tipoContainer}>
      <Text style={styles.tipoHeader}>{item.tipoPlanCuenta.toUpperCase()}</Text>
      <View style={styles.montosContainer}>
        <Text style={styles.monto}>Debe: {(item.total_debe || 0).toFixed(2)}</Text>
        <Text style={styles.monto}>Haber: {(item.total_haber || 0).toFixed(2)}</Text>
      </View>
      <Text style={styles.saldo}>{item.saldo}</Text>
    </View>
  );

  return (
    <View style={styles.container}>
      <Text style={styles.title}>Balance de Cuentas</Text>
      <FlatList
        data={tiposCuentas}
        renderItem={renderTipoCuenta}
        keyExtractor={(item) => item.tipoPlanCuenta}
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
  listContainer: {
    padding: 10,
  },
  tipoContainer: {
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
  tipoHeader: {
    fontSize: 18,
    fontWeight: 'bold',
    marginBottom: 10,
    color: '#333',
    textAlign: 'center',
  },
  montosContainer: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginBottom: 10,
  },
  monto: {
    fontSize: 14,
    color: '#555',
    flex: 1,
    textAlign: 'center',
  },
  saldo: {
    fontSize: 16,
    fontWeight: 'bold',
    textAlign: 'center',
    color: '#4f8cff',
  },
});

export default BalanceCuentasScreen;
