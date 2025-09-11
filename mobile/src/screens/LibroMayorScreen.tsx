import React, { useState, useEffect } from 'react';
import { View, Text, FlatList, StyleSheet, ActivityIndicator, TextInput } from 'react-native';
import { getLibroMayor } from '../api';

interface Cuenta {
  idPlanCuenta: number;
  codigoPlanCuenta: string;
  nombrePlanCuenta: string;
  tipoPlanCuenta: string;
  total_debe: number;
  total_haber: number;
}

const LibroMayorScreen: React.FC = () => {
  const [cuentas, setCuentas] = useState<Cuenta[]>([]);
  const [filteredCuentas, setFilteredCuentas] = useState<Cuenta[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchText, setSearchText] = useState('');
  const [currentPage, setCurrentPage] = useState(1);
  const rowsPerPage = 5;

  useEffect(() => {
    fetchData();
  }, []);

  useEffect(() => {
    filterCuentas(searchText);
  }, [cuentas, searchText]);

  const fetchData = async () => {
    try {
      const data = await getLibroMayor();
      setCuentas(data);
    } catch (error) {
      console.error('Error fetching libro mayor:', error);
    } finally {
      setLoading(false);
    }
  };

  const filterCuentas = (text: string) => {
    const filtered = cuentas.filter(cuenta =>
      cuenta.codigoPlanCuenta.toLowerCase().includes(text.toLowerCase()) ||
      cuenta.nombrePlanCuenta.toLowerCase().includes(text.toLowerCase())
    );
    setFilteredCuentas(filtered);
    setCurrentPage(1);
  };

  const totalDebe = filteredCuentas.reduce((sum, c) => sum + (c.total_debe || 0), 0);
  const totalHaber = filteredCuentas.reduce((sum, c) => sum + (c.total_haber || 0), 0);

  const paginatedCuentas = filteredCuentas.slice((currentPage - 1) * rowsPerPage, currentPage * rowsPerPage);

  const renderCuenta = ({ item }: { item: Cuenta }) => {
    const saldo = (item.total_debe || 0) - (item.total_haber || 0);
    return (
      <View style={styles.cuentaContainer}>
        <Text style={styles.cuentaHeader}>
          {item.codigoPlanCuenta} - {item.nombrePlanCuenta}
        </Text>
        <Text style={styles.tipo}>Tipo: {item.tipoPlanCuenta}</Text>
        <View style={styles.montosContainer}>
          <Text style={styles.monto}>Debe: {(item.total_debe || 0).toFixed(2)}</Text>
          <Text style={styles.monto}>Haber: {(item.total_haber || 0).toFixed(2)}</Text>
          <Text style={[styles.monto, saldo >= 0 ? styles.saldoPositivo : styles.saldoNegativo]}>
            Saldo: {Math.abs(saldo).toFixed(2)}
          </Text>
        </View>
      </View>
    );
  };

  const totalPages = Math.ceil(filteredCuentas.length / rowsPerPage);

  const handlePrevPage = () => {
    if (currentPage > 1) setCurrentPage(currentPage - 1);
  };

  const handleNextPage = () => {
    if (currentPage < totalPages) setCurrentPage(currentPage + 1);
  };

  if (loading) {
    return (
      <View style={styles.center}>
        <ActivityIndicator size="large" color="#5e72e4" />
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <Text style={styles.title}>Libro Mayor</Text>
      <Text style={styles.subtitle}>Resumen de movimientos por cuenta</Text>
      <View style={styles.searchContainer}>
        <TextInput
          style={styles.searchInput}
          placeholder="Buscar por código o nombre de cuenta..."
          value={searchText}
          onChangeText={setSearchText}
        />
      </View>
      <View style={styles.totalsContainer}>
        <View style={[styles.totalCard, styles.totalDebe]}>
          <Text style={styles.totalLabel}>Total Debe</Text>
          <Text style={styles.totalValue}>{totalDebe.toFixed(2)}</Text>
        </View>
        <View style={[styles.totalCard, styles.totalHaber]}>
          <Text style={styles.totalLabel}>Total Haber</Text>
          <Text style={styles.totalValue}>{totalHaber.toFixed(2)}</Text>
        </View>
      </View>
      <FlatList
        data={paginatedCuentas}
        renderItem={renderCuenta}
        keyExtractor={(item) => item.idPlanCuenta.toString()}
        contentContainerStyle={styles.listContainer}
      />
      <View style={styles.paginationContainer}>
        <Text style={[styles.pageButton, currentPage === 1 && styles.disabled]} onPress={handlePrevPage}>
          Anterior
        </Text>
        <Text style={styles.pageInfo}>
          Página {currentPage} de {totalPages}
        </Text>
        <Text style={[styles.pageButton, currentPage === totalPages && styles.disabled]} onPress={handleNextPage}>
          Siguiente
        </Text>
      </View>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f5f5f5',
    padding: 15,
  },
  center: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
  },
  title: {
    fontSize: 24,
    fontWeight: '600',
    color: '#5e72e4',
    textAlign: 'center',
    marginBottom: 4,
  },
  subtitle: {
    fontSize: 14,
    color: '#6c757d',
    textAlign: 'center',
    marginBottom: 12,
  },
  searchContainer: {
    backgroundColor: 'white',
    borderRadius: 10,
    paddingHorizontal: 10,
    paddingVertical: 6,
    marginBottom: 15,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
  },
  searchInput: {
    height: 40,
    fontSize: 14,
    color: '#495057',
  },
  totalsContainer: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginBottom: 15,
  },
  totalCard: {
    flex: 1,
    minWidth: 150,
    backgroundColor: 'white',
    borderRadius: 10,
    padding: 15,
    marginHorizontal: 5,
    alignItems: 'center',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.05,
    shadowRadius: 4,
    elevation: 2,
  },
  totalDebe: {
    borderColor: '#2dce89',
    borderWidth: 2,
  },
  totalHaber: {
    borderColor: '#f5365c',
    borderWidth: 2,
  },
  totalLabel: {
    fontSize: 16,
    color: '#525f7f',
    marginBottom: 6,
  },
  totalValue: {
    fontSize: 20,
    fontWeight: '700',
  },
  listContainer: {
    paddingBottom: 20,
  },
  cuentaContainer: {
    backgroundColor: 'white',
    borderRadius: 10,
    padding: 15,
    marginBottom: 10,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
  },
  cuentaHeader: {
    fontSize: 16,
    fontWeight: '700',
    marginBottom: 6,
    color: '#333',
  },
  tipo: {
    fontSize: 14,
    color: '#6c757d',
    marginBottom: 10,
  },
  montosContainer: {
    flexDirection: 'row',
    justifyContent: 'space-between',
  },
  monto: {
    fontSize: 12,
    color: '#333',
    flex: 1,
    textAlign: 'center',
  },
  saldoPositivo: {
    color: '#2dce89',
    fontWeight: '700',
  },
  saldoNegativo: {
    color: '#f5365c',
    fontWeight: '700',
  },
  paginationContainer: {
    flexDirection: 'row',
    justifyContent: 'center',
    alignItems: 'center',
    marginTop: 10,
  },
  pageButton: {
    fontSize: 14,
    color: '#fb6340',
    marginHorizontal: 20,
  },
  disabled: {
    color: '#ccc',
  },
  pageInfo: {
    fontSize: 14,
    color: '#525f7f',
  },
});

export default LibroMayorScreen;
