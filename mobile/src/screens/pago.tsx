// src/screens/PagoScreen.tsx - VERSIÓN MEJORADA CON TABLA
import React, { useState, useEffect, useContext } from 'react';
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  ScrollView,
  Alert,
  ActivityIndicator,
  StyleSheet,
  FlatList,
  RefreshControl
} from 'react-native';
import { useNavigation, useRoute } from '@react-navigation/native';
import Icon from 'react-native-vector-icons/MaterialCommunityIcons';
import api from '../api/api';
import { AuthContext } from '../contexts/AuthContext';

interface NotaItem {
  idNota: number;
  numeroNota: string;
  fechaEmision: string;
  totalNota: number;
  estado: string;
  formacion: {
    nombreFormacion: string;
  };
  persona: {
    nombre: string;
    cedula: string;
  };
}

const PagoScreen = () => {
  const navigation = useNavigation<any>();
  const route = useRoute<any>();
  const { user } = useContext(AuthContext);
  
  // Obtener parámetros de la ruta (si vienen desde inscripción)
  const { notaData, inscripcionId } = route.params || {};
  
  const [loading, setLoading] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [formData, setFormData] = useState({
    idNota: notaData?.idNota || '',
    formaPago: 'TRANSFERENCIA',
    monto: notaData?.totalNota?.toString() || '',
    referencia: '',
    observaciones: '',
    fechaPago: new Date().toISOString().split('T')[0]
  });

  const [errors, setErrors] = useState<{[key: string]: string}>({});
  const [modoDirecto, setModoDirecto] = useState(!notaData);
  const [notasUsuario, setNotasUsuario] = useState<NotaItem[]>([]);
  const [cargandoNotas, setCargandoNotas] = useState(false);
  const [notaSeleccionada, setNotaSeleccionada] = useState<NotaItem | null>(notaData || null);

  // Cargar notas del usuario al montar el componente
  useEffect(() => {
    if (modoDirecto && user) {
      cargarNotasUsuario();
    }
  }, [modoDirecto, user]);

  // Cargar notas del usuario actual
  const cargarNotasUsuario = async () => {
    if (!user?.cedula) {
      Alert.alert('Error', 'No se pudo obtener la información del usuario');
      return;
    }

    setCargandoNotas(true);
    try {
      // Endpoint para obtener notas del usuario por cédula
      const response = await api.get(`/api/notas/usuario/${user.cedula}/`);
      
      if (response.data.success) {
        setNotasUsuario(response.data.data);
      } else {
        Alert.alert('Error', 'No se pudieron cargar las notas');
      }
    } catch (error) {
      console.error('Error cargando notas:', error);
      Alert.alert('Error', 'No se pudieron cargar las notas del usuario');
    } finally {
      setCargandoNotas(false);
    }
  };

  // Refrescar lista
  const onRefresh = async () => {
    setRefreshing(true);
    await cargarNotasUsuario();
    setRefreshing(false);
  };

  // Seleccionar nota para pago
  const seleccionarNota = (nota: NotaItem) => {
    setNotaSeleccionada(nota);
    setFormData(prev => ({
      ...prev,
      idNota: nota.idNota.toString(),
      monto: nota.totalNota.toString()
    }));
  };

  // Validar formulario
  const validateForm = (): boolean => {
    const newErrors: {[key: string]: string} = {};

    if (!formData.idNota) {
      newErrors.idNota = 'Debe seleccionar una nota';
    }

    if (!formData.formaPago) {
      newErrors.formaPago = 'Seleccione forma de pago';
    }

    if (!formData.monto || parseFloat(formData.monto) <= 0) {
      newErrors.monto = 'Monto debe ser mayor a 0';
    }

    if (formData.formaPago !== 'EFECTIVO' && !formData.referencia) {
      newErrors.referencia = 'Referencia es requerida para este tipo de pago';
    }

    if (!formData.fechaPago) {
      newErrors.fechaPago = 'Fecha de pago es requerida';
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  // Manejar cambio en inputs
  const handleInputChange = (field: string, value: string) => {
    setFormData(prev => ({
      ...prev,
      [field]: value
    }));
    
    // Limpiar error del campo cuando el usuario empiece a escribir
    if (errors[field]) {
      setErrors(prev => ({
        ...prev,
        [field]: ''
      }));
    }
  };

  // Procesar pago
  const handleProcesarPago = async () => {
    if (!validateForm()) {
      Alert.alert('Error', 'Por favor complete todos los campos requeridos');
      return;
    }

    setLoading(true);

    try {
      const payload = {
        idNota: parseInt(formData.idNota),
        formaPago: formData.formaPago,
        monto: parseFloat(formData.monto),
        referencia: formData.referencia,
        observaciones: formData.observaciones,
        fechaPago: formData.fechaPago,
        idTasa: 1,
        idCuentaBanco: null
      };

      console.log('📤 Enviando pago:', payload);

      const response = await api.post('/api/pagos/create/', payload);

      if (response.data.success) {
        Alert.alert(
          '¡Pago Exitoso!',
          `Pago procesado correctamente.\nNúmero de transacción: ${response.data.data.numeroPago}`,
          [
            {
              text: 'Aceptar',
              onPress: () => {
                // Recargar notas y limpiar selección
                cargarNotasUsuario();
                setNotaSeleccionada(null);
                setFormData({
                  idNota: '',
                  formaPago: 'TRANSFERENCIA',
                  monto: '',
                  referencia: '',
                  observaciones: '',
                  fechaPago: new Date().toISOString().split('T')[0]
                });
              }
            }
          ]
        );
      } else {
        throw new Error(response.data.message);
      }

    } catch (error: any) {
      console.error('❌ Error procesando pago:', error);
      Alert.alert(
        'Error en Pago',
        error.response?.data?.message || error.message || 'Error al procesar el pago'
      );
    } finally {
      setLoading(false);
    }
  };

  // Formatear monto para display
  const formatCurrency = (amount: number): string => {
    return new Intl.NumberFormat('es-VE', {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2
    }).format(amount);
  };

  // Formatear fecha
  const formatDate = (dateString: string): string => {
    const date = new Date(dateString);
    return date.toLocaleDateString('es-VE');
  };

  // Render item de la lista de notas
  const renderNotaItem = ({ item }: { item: NotaItem }) => (
    <TouchableOpacity
      style={[
        styles.notaItem,
        notaSeleccionada?.idNota === item.idNota && styles.notaItemSeleccionada
      ]}
      onPress={() => seleccionarNota(item)}
    >
      <View style={styles.notaHeader}>
        <Text style={styles.notaNumero}>{item.numeroNota}</Text>
        <View style={[
          styles.estadoBadge,
          item.estado === 'PAGADA' ? styles.estadoPagada : 
          item.estado === 'PARCIAL' ? styles.estadoParcial : styles.estadoPendiente
        ]}>
          <Text style={styles.estadoText}>
            {item.estado === 'PAGADA' ? 'Pagada' : 
             item.estado === 'PARCIAL' ? 'Parcial' : 'Pendiente'}
          </Text>
        </View>
      </View>
      
      <Text style={styles.notaFormacion}>{item.formacion.nombreFormacion}</Text>
      
      <View style={styles.notaFooter}>
        <Text style={styles.notaFecha}>{formatDate(item.fechaEmision)}</Text>
        <Text style={styles.notaMonto}>${formatCurrency(item.totalNota)}</Text>
      </View>

      {notaSeleccionada?.idNota === item.idNota && (
        <View style={styles.seleccionadoIndicator}>
          <Icon name="check-circle" size={20} color="#28a745" />
          <Text style={styles.seleccionadoText}>Seleccionada para pago</Text>
        </View>
      )}
    </TouchableOpacity>
  );

  // Si estamos en modo directo (sin datos de nota), mostrar tabla de notas
  if (modoDirecto) {
    return (
      <View style={styles.container}>
        <View style={styles.header}>
          <Text style={styles.title}>Mis Notas de Cobro</Text>
          <Text style={styles.subtitle}>Seleccione una nota para proceder al pago</Text>
        </View>

        {/* Lista de notas */}
        <View style={styles.listaContainer}>
          {cargandoNotas ? (
            <View style={styles.loadingContainer}>
              <ActivityIndicator size="large" color="#4f8cff" />
              <Text style={styles.loadingText}>Cargando notas...</Text>
            </View>
          ) : notasUsuario.length === 0 ? (
            <View style={styles.emptyContainer}>
              <Icon name="file-alert" size={60} color="#6c757d" />
              <Text style={styles.emptyText}>No tienes notas pendientes</Text>
              <Text style={styles.emptySubtext}>
                Realiza una inscripción para generar una nota de cobro
              </Text>
            </View>
          ) : (
            <FlatList
              data={notasUsuario}
              renderItem={renderNotaItem}
              keyExtractor={(item) => item.idNota.toString()}
              refreshControl={
                <RefreshControl
                  refreshing={refreshing}
                  onRefresh={onRefresh}
                  colors={['#4f8cff']}
                />
              }
              contentContainerStyle={styles.listaContent}
              showsVerticalScrollIndicator={false}
            />
          )}
        </View>

        {/* Formulario de pago (solo si hay nota seleccionada) */}
        {notaSeleccionada && (
          <View style={styles.formularioContainer}>
            <ScrollView style={styles.formScrollView}>
              <View style={styles.formCard}>
                <View style={styles.formHeader}>
                  <Text style={styles.formTitle}>Procesar Pago</Text>
                  <TouchableOpacity 
                    onPress={() => setNotaSeleccionada(null)}
                    style={styles.cancelarBtn}
                  >
                    <Icon name="close" size={20} color="#6c757d" />
                  </TouchableOpacity>
                </View>

                {/* Información de la nota seleccionada */}
                <View style={styles.infoCard}>
                  <Text style={styles.infoTitle}>Nota Seleccionada</Text>
                  <View style={styles.infoRow}>
                    <Text style={styles.infoLabel}>Número:</Text>
                    <Text style={styles.infoValue}>{notaSeleccionada.numeroNota}</Text>
                  </View>
                  <View style={styles.infoRow}>
                    <Text style={styles.infoLabel}>Formación:</Text>
                    <Text style={styles.infoValue}>{notaSeleccionada.formacion.nombreFormacion}</Text>
                  </View>
                  <View style={styles.infoRow}>
                    <Text style={styles.infoLabel}>Total:</Text>
                    <Text style={styles.infoValue}>${formatCurrency(notaSeleccionada.totalNota)}</Text>
                  </View>
                </View>

                {/* Forma de Pago */}
                <View style={styles.inputGroup}>
                  <Text style={styles.label}>Forma de Pago *</Text>
                  <View style={styles.radioGroup}>
                    {['TRANSFERENCIA', 'PAGO_MOVIL', 'EFECTIVO'].map((tipo) => (
                      <TouchableOpacity
                        key={tipo}
                        style={styles.radioOption}
                        onPress={() => handleInputChange('formaPago', tipo)}
                      >
                        <View style={styles.radioCircle}>
                          {formData.formaPago === tipo && <View style={styles.radioSelected} />}
                        </View>
                        <Text style={styles.radioLabel}>
                          {tipo === 'TRANSFERENCIA' ? 'Transferencia' : 
                           tipo === 'PAGO_MOVIL' ? 'Pago Móvil' : 'Efectivo'}
                        </Text>
                      </TouchableOpacity>
                    ))}
                  </View>
                  {errors.formaPago && <Text style={styles.errorText}>{errors.formaPago}</Text>}
                </View>

                {/* Monto */}
                <View style={styles.inputGroup}>
                  <Text style={styles.label}>Monto a Pagar *</Text>
                  <TextInput
                    style={[styles.input, errors.monto && styles.inputError]}
                    value={formData.monto}
                    onChangeText={(value) => handleInputChange('monto', value)}
                    placeholder="0.00"
                    keyboardType="numeric"
                    editable={true}
                  />
                  <Text style={styles.helperText}>
                    Máximo permitido: ${formatCurrency(notaSeleccionada.totalNota)}
                  </Text>
                  {errors.monto && <Text style={styles.errorText}>{errors.monto}</Text>}
                </View>

                {/* Referencia (solo para no efectivo) */}
                {formData.formaPago !== 'EFECTIVO' && (
                  <View style={styles.inputGroup}>
                    <Text style={styles.label}>Número de Referencia *</Text>
                    <TextInput
                      style={[styles.input, errors.referencia && styles.inputError]}
                      value={formData.referencia}
                      onChangeText={(value) => handleInputChange('referencia', value)}
                      placeholder="Ej: 123456789"
                      maxLength={14}
                      keyboardType="numeric"
                    />
                    <Text style={styles.helperText}>Número de transacción/transferencia</Text>
                    {errors.referencia && <Text style={styles.errorText}>{errors.referencia}</Text>}
                  </View>
                )}

                {/* Fecha de Pago */}
                <View style={styles.inputGroup}>
                  <Text style={styles.label}>Fecha de Pago *</Text>
                  <TextInput
                    style={[styles.input, errors.fechaPago && styles.inputError]}
                    value={formData.fechaPago}
                    onChangeText={(value) => handleInputChange('fechaPago', value)}
                    placeholder="YYYY-MM-DD"
                  />
                  <Text style={styles.helperText}>Formato: Año-Mes-Día</Text>
                  {errors.fechaPago && <Text style={styles.errorText}>{errors.fechaPago}</Text>}
                </View>

                {/* Observaciones */}
                <View style={styles.inputGroup}>
                  <Text style={styles.label}>Observaciones</Text>
                  <TextInput
                    style={[styles.input, styles.textArea]}
                    value={formData.observaciones}
                    onChangeText={(value) => handleInputChange('observaciones', value)}
                    placeholder="Observaciones adicionales..."
                    multiline
                    numberOfLines={3}
                  />
                </View>

                {/* Botón de Procesar */}
                <TouchableOpacity
                  style={[styles.submitButton, loading && styles.submitButtonDisabled]}
                  onPress={handleProcesarPago}
                  disabled={loading}
                >
                  {loading ? (
                    <ActivityIndicator color="#fff" />
                  ) : (
                    <Text style={styles.submitButtonText}>Procesar Pago</Text>
                  )}
                </TouchableOpacity>
              </View>
            </ScrollView>
          </View>
        )}
      </View>
    );
  }

  // Modo automático (desde inscripción)
  return (
    <ScrollView style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.title}>Procesar Pago</Text>
        <Text style={styles.subtitle}>Complete los datos para registrar el pago</Text>
      </View>

      {/* Información de la Nota */}
      {notaData && (
        <View style={styles.infoCard}>
          <Text style={styles.infoTitle}>Información de la Nota</Text>
          <View style={styles.infoRow}>
            <Text style={styles.infoLabel}>Número de Nota:</Text>
            <Text style={styles.infoValue}>{notaData.numeroNota}</Text>
          </View>
          <View style={styles.infoRow}>
            <Text style={styles.infoLabel}>Formación:</Text>
            <Text style={styles.infoValue}>{notaData.formacion.nombreFormacion}</Text>
          </View>
          <View style={styles.infoRow}>
            <Text style={styles.infoLabel}>Estudiante:</Text>
            <Text style={styles.infoValue}>{notaData.persona.nombre}</Text>
          </View>
          <View style={styles.infoRow}>
            <Text style={styles.infoLabel}>Cédula:</Text>
            <Text style={styles.infoValue}>{notaData.persona.cedula}</Text>
          </View>
          <View style={[styles.infoRow, styles.totalRow]}>
            <Text style={styles.totalLabel}>Total a Pagar:</Text>
            <Text style={styles.totalValue}>${formatCurrency(notaData.totalNota)}</Text>
          </View>
        </View>
      )}

      {/* Formulario de Pago */}
      <View style={styles.formCard}>
        <Text style={styles.formTitle}>Datos del Pago</Text>

        
        {/* Forma de Pago */}
        <View style={styles.inputGroup}>
          <Text style={styles.label}>Forma de Pago *</Text>
          <View style={styles.radioGroup}>
            {['TRANSFERENCIA', 'PAGO_MOVIL', 'EFECTIVO'].map((tipo) => (
              <TouchableOpacity
                key={tipo}
                style={styles.radioOption}
                onPress={() => handleInputChange('formaPago', tipo)}
              >
                <View style={styles.radioCircle}>
                  {formData.formaPago === tipo && <View style={styles.radioSelected} />}
                </View>
                <Text style={styles.radioLabel}>
                  {tipo === 'TRANSFERENCIA' ? 'Transferencia' : 
                   tipo === 'PAGO_MOVIL' ? 'Pago Móvil' : 'Efectivo'}
                </Text>
              </TouchableOpacity>
            ))}
          </View>
          {errors.formaPago && <Text style={styles.errorText}>{errors.formaPago}</Text>}
        </View>

        {/* Monto */}
        <View style={styles.inputGroup}>
          <Text style={styles.label}>Monto a Pagar *</Text>
          <TextInput
            style={[styles.input, errors.monto && styles.inputError]}
            value={formData.monto}
            onChangeText={(value) => handleInputChange('monto', value)}
            placeholder="0.00"
            keyboardType="numeric"
            editable={true}
          />
          <Text style={styles.helperText}>
            Máximo permitido: ${formatCurrency(notaData.totalNota)}
          </Text>
          {errors.monto && <Text style={styles.errorText}>{errors.monto}</Text>}
        </View>

        {/* Referencia (solo para no efectivo) */}
        {formData.formaPago !== 'EFECTIVO' && (
          <View style={styles.inputGroup}>
            <Text style={styles.label}>Número de Referencia *</Text>
            <TextInput
              style={[styles.input, errors.referencia && styles.inputError]}
              value={formData.referencia}
              onChangeText={(value) => handleInputChange('referencia', value)}
              placeholder="Ej: 123456789"
              maxLength={14}
              keyboardType="numeric"
            />
            <Text style={styles.helperText}>Número de transacción/transferencia</Text>
            {errors.referencia && <Text style={styles.errorText}>{errors.referencia}</Text>}
          </View>
        )}

        {/* Fecha de Pago */}
        <View style={styles.inputGroup}>
          <Text style={styles.label}>Fecha de Pago *</Text>
          <TextInput
            style={[styles.input, errors.fechaPago && styles.inputError]}
            value={formData.fechaPago}
            onChangeText={(value) => handleInputChange('fechaPago', value)}
            placeholder="YYYY-MM-DD"
          />
          <Text style={styles.helperText}>Formato: Año-Mes-Día</Text>
          {errors.fechaPago && <Text style={styles.errorText}>{errors.fechaPago}</Text>}
        </View>

        {/* Observaciones */}
        <View style={styles.inputGroup}>
          <Text style={styles.label}>Observaciones</Text>
          <TextInput
            style={[styles.input, styles.textArea]}
            value={formData.observaciones}
            onChangeText={(value) => handleInputChange('observaciones', value)}
            placeholder="Observaciones adicionales..."
            multiline
            numberOfLines={3}
          />
        </View>

        {/* Botón de Procesar */}
        <TouchableOpacity
          style={[styles.submitButton, loading && styles.submitButtonDisabled]}
          onPress={handleProcesarPago}
          disabled={loading}
        >
          {loading ? (
            <ActivityIndicator color="#fff" />
          ) : (
            <Text style={styles.submitButtonText}>Procesar Pago</Text>
          )}
        </TouchableOpacity>
      </View>
    </ScrollView>
  );
};

// ESTILOS ACTUALIZADOS
const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f8f9fa',
  },
  header: {
    backgroundColor: '#fff',
    padding: 20,
    borderBottomWidth: 1,
    borderBottomColor: '#e9ecef',
  },
  title: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#343a40',
    marginBottom: 5,
  },
  subtitle: {
    fontSize: 16,
    color: '#6c757d',
  },
  // Estilos para la lista de notas
  listaContainer: {
    flex: 1,
    padding: 15,
  },
  listaContent: {
    paddingBottom: 20,
  },
  loadingContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    paddingVertical: 50,
  },
  loadingText: {
    marginTop: 10,
    color: '#6c757d',
    fontSize: 16,
  },
  emptyContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    paddingVertical: 50,
  },
  emptyText: {
    fontSize: 18,
    color: '#6c757d',
    fontWeight: '600',
    marginTop: 10,
  },
  emptySubtext: {
    fontSize: 14,
    color: '#6c757d',
    textAlign: 'center',
    marginTop: 5,
    paddingHorizontal: 20,
  },
  // Estilos para items de nota
  notaItem: {
    backgroundColor: '#fff',
    padding: 15,
    borderRadius: 10,
    marginBottom: 10,
    borderWidth: 2,
    borderColor: 'transparent',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.1,
    shadowRadius: 3,
    elevation: 2,
  },
  notaItemSeleccionada: {
    borderColor: '#28a745',
    backgroundColor: '#f8fff9',
  },
  notaHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 8,
  },
  notaNumero: {
    fontSize: 16,
    fontWeight: 'bold',
    color: '#343a40',
  },
  estadoBadge: {
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 12,
  },
  estadoPendiente: {
    backgroundColor: '#fff3cd',
  },
  estadoParcial: {
    backgroundColor: '#d1ecf1',
  },
  estadoPagada: {
    backgroundColor: '#d4edda',
  },
  estadoText: {
    fontSize: 12,
    fontWeight: 'bold',
  },
  notaFormacion: {
    fontSize: 14,
    color: '#495057',
    marginBottom: 8,
  },
  notaFooter: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  notaFecha: {
    fontSize: 12,
    color: '#6c757d',
  },
  notaMonto: {
    fontSize: 16,
    fontWeight: 'bold',
    color: '#28a745',
  },
  seleccionadoIndicator: {
    flexDirection: 'row',
    alignItems: 'center',
    marginTop: 8,
    paddingTop: 8,
    borderTopWidth: 1,
    borderTopColor: '#e9ecef',
  },
  seleccionadoText: {
    marginLeft: 5,
    color: '#28a745',
    fontWeight: '600',
  },
  // Estilos para el formulario flotante
  formularioContainer: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    backgroundColor: 'rgba(0,0,0,0.5)',
  },
  formScrollView: {
    flex: 1,
    backgroundColor: 'transparent',
  },
  formCard: {
    backgroundColor: '#fff',
    margin: 15,
    padding: 20,
    borderRadius: 10,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.25,
    shadowRadius: 5,
    elevation: 5,
  },
  formHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 20,
  },
  cancelarBtn: {
    padding: 5,
  },
  // Estilos existentes...
  infoCard: {
    backgroundColor: '#fff',
    margin: 15,
    padding: 20,
    borderRadius: 10,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
  },
  infoTitle: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#495057',
    marginBottom: 15,
  },
  infoRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginBottom: 8,
  },
  infoLabel: {
    fontSize: 14,
    color: '#6c757d',
    fontWeight: '500',
  },
  infoValue: {
    fontSize: 14,
    color: '#495057',
    fontWeight: '400',
  },
  totalRow: {
    borderTopWidth: 1,
    borderTopColor: '#e9ecef',
    paddingTop: 10,
    marginTop: 5,
  },
  totalLabel: {
    fontSize: 16,
    fontWeight: 'bold',
    color: '#495057',
  },
  totalValue: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#28a745',
  },
  formTitle: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#495057',
    marginBottom: 20,
  },
  inputGroup: {
    marginBottom: 20,
  },
  label: {
    fontSize: 16,
    fontWeight: '600',
    color: '#495057',
    marginBottom: 8,
  },
  input: {
    borderWidth: 1,
    borderColor: '#ced4da',
    borderRadius: 8,
    padding: 12,
    fontSize: 16,
    backgroundColor: '#fff',
  },
  inputError: {
    borderColor: '#dc3545',
  },
  textArea: {
    height: 80,
    textAlignVertical: 'top',
  },
  helperText: {
    fontSize: 12,
    color: '#6c757d',
    marginTop: 4,
  },
  errorText: {
    fontSize: 12,
    color: '#dc3545',
    marginTop: 4,
  },
  radioGroup: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    justifyContent: 'space-between',
  },
  radioOption: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 10,
    flex: 1,
    minWidth: '30%',
  },
  radioCircle: {
    height: 20,
    width: 20,
    borderRadius: 10,
    borderWidth: 2,
    borderColor: '#007bff',
    alignItems: 'center',
    justifyContent: 'center',
    marginRight: 8,
  },
  radioSelected: {
    height: 10,
    width: 10,
    borderRadius: 5,
    backgroundColor: '#007bff',
  },
  radioLabel: {
    fontSize: 14,
    color: '#495057',
  },
  submitButton: {
    backgroundColor: '#28a745',
    padding: 15,
    borderRadius: 8,
    alignItems: 'center',
    marginTop: 10,
  },
  submitButtonDisabled: {
    backgroundColor: '#6c757d',
  },
  submitButtonText: {
    color: '#fff',
    fontSize: 18,
    fontWeight: 'bold',
  },
});

export default PagoScreen;