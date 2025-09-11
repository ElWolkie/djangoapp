import React, { useState, useEffect } from 'react';
import { View, Text, FlatList, StyleSheet, ActivityIndicator, TextInput, TouchableOpacity } from 'react-native';
import { getLibroDiario } from '../api';

interface Asiento {
  idAsiento: number;
  numeroAsiento: string;
  fechaAsiento: string;
  conceptoAsiento: string;
  detalles: Detalle[];
}

interface Detalle {
  idDetalle: number;
  idPlanCuenta: {
    codigoPlanCuenta: string;
    nombrePlanCuenta: string;
  };
  debe: number;
  haber: number;
}

interface Row {
  id: string;
  numeroAsiento: string;
  fechaAsiento: string;
  conceptoAsiento: string;
  cuenta: string;
  debe: number;
  haber: number;
}

const LibroDiarioScreen: React.FC = () => {
  const [asientos, setAsientos] = useState<Asiento[]>([]);
  const [rows, setRows] = useState<Row[]>([]);
  const [filteredRows, setFilteredRows] = useState<Row[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchText, setSearchText] = useState('');
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');
  const [currentPage, setCurrentPage] = useState(1);
  const rowsPerPage = 10;

  useEffect(() => {
    fetchData();
  }, []);

  useEffect(() => {
    const flattened = asientos.flatMap(asiento =>
      asiento.detalles.map(detalle => ({
        id: `${asiento.idAsiento}-${detalle.idDetalle}`,
        numeroAsiento: asiento.numeroAsiento,
        fechaAsiento: asiento.fechaAsiento,
        conceptoAsiento: asiento.conceptoAsiento,
        cuenta: `${detalle.idPlanCuenta.codigoPlanCuenta} - ${detalle.idPlanCuenta.nombrePlanCuenta}`,
        debe: detalle.debe,
        haber: detalle.haber,
      }))
    );
    setRows(flattened);
  }, [asientos]);

  useEffect(() => {
    filterRows();
  }, [rows, searchText, startDate, endDate]);

  const fetchData = async () => {
    try {
      const data = await getLibroDiario();
      setAsientos(data);
    } catch (error) {
      console.error('Error fetching libro diario:', error);
    } finally {
      setLoading(false);
    }
  };

  const filterRows = () => {
    let filtered = rows;

    if (searchText) {
      filtered = filtered.filter(row =>
        row.numeroAsiento.toLowerCase().includes(searchText.toLowerCase()) ||
        row.conceptoAsiento.toLowerCase().includes(searchText.toLowerCase()) ||
        row.cuenta.toLowerCase().includes(searchText.toLowerCase())
      );
    }

    if (startDate) {
      filtered = filtered.filter(row => new Date(row.fechaAsiento) >= new Date(startDate));
    }

    if (endDate) {
      filtered = filtered.filter(row => new Date(row.fechaAsiento) <= new Date(endDate));
    }

    setFilteredRows(filtered);
    setCurrentPage(1);
  };

  const totalDebe = filteredRows.reduce((sum, r) => sum + r.debe, 0);
  const totalHaber = filteredRows.reduce((sum, r) => sum + r.haber, 0);

  const paginatedRows = filteredRows.slice((currentPage - 1) * rowsPerPage, currentPage * rowsPerPage);

  const handleFilter = () => {
    filterRows();
  };

  const handlePrevPage = () => {
    if (currentPage > 1) setCurrentPage(currentPage - 1);
  };

  const handleNextPage = () => {
    if (currentPage < Math.ceil(filteredRows.length / rowsPerPage)) setCurrentPage(currentPage + 1);
  };

  const renderRow = ({ item }: { item: Row }) => (
    <View style={styles.rowContainer}>
      <Text style={styles.cell}>{item.numeroAsiento}</Text>
      <Text style={styles.cell}>{item.fechaAsiento}</Text>
      <TouchableOpacity style={styles.conceptoButton} onPress={() => alert(item.conceptoAsiento)}>
        <Text style={styles.buttonText}>Ver</Text>
      </TouchableOpacity>
      <Text style={styles.cell}>{item.cuenta}</Text>
      <Text style={[styles.cell, styles.highlightDebe]}>{item.debe.toFixed(2)}</Text>
      <Text style={[styles.cell, styles.highlightHaber]}>{item.haber.toFixed(2)}</Text>
      <View style={styles.actions}>
        <TouchableOpacity style={styles.actionButton}>
          <Text style={styles.actionText}>Editar</Text>
        </TouchableOpacity>
        <TouchableOpacity style={styles.actionButton}>
          <Text style={styles.actionText}>Eliminar</Text>
        </TouchableOpacity>
      </View>
    </View>
  );

  const totalPages = Math.ceil(filteredRows.length / rowsPerPage);

  if (loading) {
    return (
      <View style={styles.center}>
        <ActivityIndicator size="large" color="#5e72e4" />
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <Text style={styles.title}>Libro Diario</Text>
      <Text style={styles.subtitle}>Registro cronológico de transacciones</Text>
      <View style={styles.filtersContainer}>
        <TextInput
          style={styles.input}
          placeholder="Buscar por número de asiento, concepto o cuenta..."
          value={searchText}
          onChangeText={setSearchText}
        />
        <TextInput
          style={styles.input}
          placeholder="Fecha inicio (YYYY-MM-DD)"
          value={startDate}
          onChangeText={setStartDate}
        />
        <TextInput
          style={styles.input}
          placeholder="Fecha fin (YYYY-MM-DD)"
          value={endDate}
          onChangeText={setEndDate}
        />
        <TouchableOpacity style={styles.filterButton} onPress={handleFilter}>
          <Text style={styles.filterButtonText}>Filtrar</Text>
        </TouchableOpacity>
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
      <View style={styles.tableHeader}>
        <Text style={styles.headerCell}>N° Asiento</Text>
        <Text style={styles.headerCell}>Fecha</Text>
        <Text style={styles.headerCell}>Concepto</Text>
        <Text style={styles.headerCell}>Cuenta</Text>
        <Text style={styles.headerCell}>Debe</Text>
        <Text style={styles.headerCell}>Haber</Text>
        <Text style={styles.headerCell}>Acciones</Text>
      </View>
      <FlatList
        data={paginatedRows}
        renderItem={renderRow}
        keyExtractor={(item) => item.id}
        contentContainerStyle={styles.listContainer}
      />
      <View style={styles.paginationContainer}>
        <TouchableOpacity style={[styles.pageButton, currentPage === 1 && styles.disabled]} onPress={handlePrevPage}>
          <Text style={styles.pageButtonText}>Anterior</Text>
        </TouchableOpacity>
        <Text style={styles.pageInfo}>
          Página {currentPage} de {totalPages}
        </Text>
        <TouchableOpacity style={[styles.pageButton, currentPage === totalPages && styles.disabled]} onPress={handleNextPage}>
          <Text style={styles.pageButtonText}>Siguiente</Text>
        </TouchableOpacity>
      </View>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f8f9fe',
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
  filtersContainer: {
    backgroundColor: 'white',
    borderRadius: 10,
    padding: 15,
    marginBottom: 15,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.05,
    shadowRadius: 4,
    elevation: 2,
  },
  input: {
    borderWidth: 1,
    borderColor: '#ddd',
    borderRadius: 5,
    padding: 10,
    marginBottom: 10,
    fontSize: 14,
  },
  filterButton: {
    backgroundColor: '#fb6340',
    borderRadius: 5,
    padding: 10,
    alignItems: 'center',
  },
  filterButtonText: {
    color: 'white',
    fontSize: 14,
    fontWeight: '600',
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
  tableHeader: {
    flexDirection: 'row',
    backgroundColor: '#5e72e4',
    padding: 10,
    borderRadius: 5,
    marginBottom: 10,
  },
  headerCell: {
    flex: 1,
    color: 'white',
    fontWeight: '600',
    textAlign: 'center',
    fontSize: 12,
  },
  listContainer: {
    paddingBottom: 20,
  },
  rowContainer: {
    flexDirection: 'row',
    backgroundColor: 'white',
    padding: 10,
    marginBottom: 5,
    borderRadius: 5,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.05,
    shadowRadius: 2,
    elevation: 1,
  },
  cell: {
    flex: 1,
    fontSize: 12,
    textAlign: 'center',
    color: '#333',
  },
  conceptoButton: {
    flex: 1,
    backgroundColor: '#11cdef',
    borderRadius: 5,
    padding: 5,
    alignItems: 'center',
  },
  buttonText: {
    color: 'white',
    fontSize: 10,
  },
  highlightDebe: {
    backgroundColor: 'rgba(45, 206, 137, 0.1)',
    fontWeight: '600',
    color: '#2dce89',
  },
  highlightHaber: {
    backgroundColor: 'rgba(245, 54, 92, 0.1)',
    fontWeight: '600',
    color: '#f5365c',
  },
  actions: {
    flex: 1,
    flexDirection: 'row',
    justifyContent: 'space-around',
  },
  actionButton: {
    backgroundColor: '#5e72e4',
    borderRadius: 5,
    padding: 5,
    alignItems: 'center',
    marginHorizontal: 2,
  },
  actionText: {
    color: 'white',
    fontSize: 10,
  },
  paginationContainer: {
    flexDirection: 'row',
    justifyContent: 'center',
    alignItems: 'center',
    marginTop: 10,
  },
  pageButton: {
    backgroundColor: '#fb6340',
    borderRadius: 5,
    padding: 10,
    marginHorizontal: 10,
  },
  pageButtonText: {
    color: 'white',
    fontSize: 14,
  },
  disabled: {
    backgroundColor: '#ccc',
  },
  pageInfo: {
    fontSize: 14,
    color: '#525f7f',
  },
});

export default LibroDiarioScreen;
