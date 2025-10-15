// src/screens/pago.tsx - MODIFICADO PARA PAGO FICTICIO
import React, { useState, useEffect, useContext } from 'react';
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  ScrollView,
  Alert,
  StyleSheet,
  FlatList,
  RefreshControl,
  KeyboardAvoidingView,
  Platform
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
  
  const { notaData, inscripcionId } = route.params || {};
  
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

  useEffect(() => {
    if (modoDirecto && user) {
      cargarNotasUsuario();
    }
  }, [modoDirecto, user]);

  const cargarNotasUsuario = async () => {
    console.log('🔄 Cargando notas para usuario autenticado');
    setCargandoNotas(true);
    
    try {
      const response = await api.get('/api/notas/usuario/autenticado/');
      console.log('📋 Respuesta del API:', response.data);
      
      if (response.data.success) {
        console.log(`✅ Se cargaron ${response.data.data.length} notas`);
        setNotasUsuario(response.data.data);
      } else {
        Alert.alert('Error', response.data.message || 'No se pudieron cargar las notas');
      }
    } catch (error: any) {
      console.error('❌ Error cargando notas:', error);
      
      if (error.response?.status === 401) {
        Alert.alert('Error de autenticación', 'Por favor inicie sesión nuevamente');
      } else if (error.response?.status === 404) {
        Alert.alert('Perfil no encontrado', 'No se encontró el perfil de persona asociado a su usuario');
      } else {
        Alert.alert('Error', 'No se pudieron cargar las notas. Verifica tu conexión.');
      }
    } finally {
      setCargandoNotas(false);
    }
  };

  const onRefresh = async () => {
    setRefreshing(true);
    await cargarNotasUsuario();
    setRefreshing(false);
  };

  const seleccionarNota = (nota: NotaItem) => {
    setNotaSeleccionada(nota);
    setFormData(prev => ({
      ...prev,
      idNota: nota.idNota.toString(),
      monto: nota.totalNota.toString()
    }));
  };

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
    } else if (notaSeleccionada && parseFloat(formData.monto) > notaSeleccionada.totalNota) {
      newErrors.monto = `El monto no puede ser mayor a $${formatCurrency(notaSeleccionada.totalNota)}`;
    }

    if (!formData.referencia.trim()) {
      newErrors.referencia = 'Número de referencia es requerido';
    }

    if (!formData.fechaPago) {
      newErrors.fechaPago = 'Fecha de pago es requerida';
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleInputChange = (field: string, value: string) => {
    setFormData(prev => ({
      ...prev,
      [field]: value
    }));
    
    if (errors[field]) {
      setErrors(prev => ({
        ...prev,
        [field]: ''
      }));
    }
  };

  // 🚀 FUNCIÓN MODIFICADA - AHORA NAVEGA A PAGO MÓVIL FICTICIO
  const handleProcesarPago = () => {
    if (!validateForm()) {
      Alert.alert('Error', 'Por favor complete todos los campos requeridos');
      return;
    }

    console.log('🚀 [PAGO-FICTICIO] Navegando a pantalla de pago móvil...');
    
    // Preparar datos para la pantalla de pago móvil
    const pagoParams = {
      monto: parseFloat(formData.monto),
      referencia: formData.referencia,
      formaPago: formData.formaPago,
      notaData: notaSeleccionada || notaData,
      userData: user ? {
        nombre: user.nombre,
        cedula: user.cedula,
        telefono: user.telefono, // si está disponible en tu contexto
        bancoPreferido: user.bancoPreferido // si está disponible
      } : undefined
    };

    console.log('📤 [PAGO-FICTICIO] Parámetros:', pagoParams);

    // Navegar a la pantalla ficticia de pago móvil
    navigation.navigate('PagoMovilFicticio', pagoParams);
  };

  const formatCurrency = (amount: number): string => {
    return new Intl.NumberFormat('es-VE', {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2
    }).format(amount);
  };

  const formatDate = (dateString: string): string => {
    const date = new Date(dateString);
    return date.toLocaleDateString('es-VE');
  };

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
      
      <Text style={styles.notaFormacion} numberOfLines={2}>
        {item.formacion.nombreFormacion}
      </Text>
      
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

  // Modo directo (selección de notas)
  if (modoDirecto) {
    return (
      <KeyboardAvoidingView 
        style={styles.container}
        behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
      >
        {/* Header Mejorado */}
        <View style={styles.header}>
          <View style={styles.headerContent}>
            <Text style={styles.title}>Mis Notas de Cobro</Text>
            <Text style={styles.subtitle}>Seleccione una nota para proceder al pago</Text>
          </View>
          <View style={styles.headerIcon}>
            <Icon name="file-document-multiple" size={28} color="#4f8cff" />
          </View>
        </View>

        {/* Lista de notas */}
        <View style={styles.listaContainer}>
          {cargandoNotas ? (
            <View style={styles.loadingContainer}>
              <Text style={styles.loadingText}>Cargando notas...</Text>
            </View>
          ) : notasUsuario.length === 0 ? (
            <View style={styles.emptyContainer}>
              <Icon name="file-alert" size={70} color="#dee2e6" />
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
                  tintColor="#4f8cff"
                />
              }
              contentContainerStyle={styles.listaContent}
              showsVerticalScrollIndicator={false}
            />
          )}
        </View>

        {/* Formulario de pago flotante */}
        {notaSeleccionada && (
          <View style={styles.formularioOverlay}>
            <ScrollView 
              style={styles.formScrollView}
              contentContainerStyle={styles.formScrollContent}
            >
              <View style={styles.formCard}>
                {/* Header del formulario */}
                <View style={styles.formHeader}>
                  <View style={styles.formTitleContainer}>
                    <Icon name="credit-card-check" size={24} color="#28a745" />
                    <Text style={styles.formTitle}>Procesar Pago</Text>
                  </View>
                  <TouchableOpacity 
                    onPress={() => setNotaSeleccionada(null)}
                    style={styles.cancelarBtn}
                  >
                    <Icon name="close" size={22} color="#6c757d" />
                  </TouchableOpacity>
                </View>

                {/* Información de la nota seleccionada */}
                <View style={styles.infoCard}>
                  <View style={styles.infoHeader}>
                    <Icon name="file-document" size={18} color="#495057" />
                    <Text style={styles.infoTitle}>Nota Seleccionada</Text>
                  </View>
                  <View style={styles.infoGrid}>
                    <View style={styles.infoItem}>
                      <Text style={styles.infoLabel}>Número:</Text>
                      <Text style={styles.infoValue}>{notaSeleccionada.numeroNota}</Text>
                    </View>
                    <View style={styles.infoItem}>
                      <Text style={styles.infoLabel}>Formación:</Text>
                      <Text style={styles.infoValue} numberOfLines={2}>
                        {notaSeleccionada.formacion.nombreFormacion}
                      </Text>
                    </View>
                    <View style={styles.infoItem}>
                      <Text style={styles.infoLabel}>Total:</Text>
                      <Text style={styles.totalValue}>${formatCurrency(notaSeleccionada.totalNota)}</Text>
                    </View>
                  </View>
                </View>

                {/* Forma de Pago - SOLO TRANSFERENCIA Y PAGO MÓVIL */}
                <View style={styles.inputGroup}>
                  <Text style={styles.label}>Forma de Pago *</Text>
                  <View style={styles.radioGroup}>
                    {['TRANSFERENCIA', 'PAGO_MOVIL'].map((tipo) => (
                      <TouchableOpacity
                        key={tipo}
                        style={[
                          styles.radioOption,
                          formData.formaPago === tipo && styles.radioOptionSelected
                        ]}
                        onPress={() => handleInputChange('formaPago', tipo)}
                      >
                        <View style={styles.radioContent}>
                          <View style={styles.radioCircle}>
                            {formData.formaPago === tipo && <View style={styles.radioSelected} />}
                          </View>
                          <Text style={[
                            styles.radioLabel,
                            formData.formaPago === tipo && styles.radioLabelSelected
                          ]}>
                            {tipo === 'TRANSFERENCIA' ? 'Transferencia Bancaria' : 'Pago Móvil'}
                          </Text>
                        </View>
                        <Icon 
                          name={tipo === 'TRANSFERENCIA' ? 'bank-transfer' : 'cellphone'} 
                          size={20} 
                          color={formData.formaPago === tipo ? '#4f8cff' : '#6c757d'} 
                        />
                      </TouchableOpacity>
                    ))}
                  </View>
                  {errors.formaPago && (
                    <View style={styles.errorContainer}>
                      <Icon name="alert-circle" size={16} color="#dc3545" />
                      <Text style={styles.errorText}>{errors.formaPago}</Text>
                    </View>
                  )}
                </View>

                {/* Monto */}
                <View style={styles.inputGroup}>
                  <Text style={styles.label}>Monto a Pagar *</Text>
                  <View style={styles.inputContainer}>
                    <Text style={styles.currencySymbol}>$</Text>
                    <TextInput
                      style={[styles.input, errors.monto && styles.inputError]}
                      value={formData.monto}
                      onChangeText={(value) => handleInputChange('monto', value)}
                      placeholder="0.00"
                      keyboardType="numeric"
                      placeholderTextColor="#6c757d"
                    />
                  </View>
                  <Text style={styles.helperText}>
                    Máximo permitido: <Text style={styles.helperTextBold}>${formatCurrency(notaSeleccionada.totalNota)}</Text>
                  </Text>
                  {errors.monto && (
                    <View style={styles.errorContainer}>
                      <Icon name="alert-circle" size={16} color="#dc3545" />
                      <Text style={styles.errorText}>{errors.monto}</Text>
                    </View>
                  )}
                </View>

                {/* Referencia - SIEMPRE REQUERIDA */}
                <View style={styles.inputGroup}>
                  <Text style={styles.label}>Número de Referencia *</Text>
                  <TextInput
                    style={[styles.input, errors.referencia && styles.inputError]}
                    value={formData.referencia}
                    onChangeText={(value) => handleInputChange('referencia', value)}
                    placeholder="Ej: 123456789"
                    maxLength={14}
                    keyboardType="numeric"
                    placeholderTextColor="#6c757d"
                  />
                  <Text style={styles.helperText}>
                    Número de transacción/transferencia de su banco
                  </Text>
                  {errors.referencia && (
                    <View style={styles.errorContainer}>
                      <Icon name="alert-circle" size={16} color="#dc3545" />
                      <Text style={styles.errorText}>{errors.referencia}</Text>
                    </View>
                  )}
                </View>

                {/* Fecha de Pago */}
                <View style={styles.inputGroup}>
                  <Text style={styles.label}>Fecha de Pago *</Text>
                  <View style={styles.inputContainer}>
                    <Icon name="calendar" size={20} color="#6c757d" style={styles.inputIcon} />
                    <TextInput
                      style={[styles.input, errors.fechaPago && styles.inputError]}
                      value={formData.fechaPago}
                      onChangeText={(value) => handleInputChange('fechaPago', value)}
                      placeholder="AAAA-MM-DD"
                      placeholderTextColor="#6c757d"
                    />
                  </View>
                  <Text style={styles.helperText}>Formato: Año-Mes-Día (Ej: 2024-01-15)</Text>
                  {errors.fechaPago && (
                    <View style={styles.errorContainer}>
                      <Icon name="alert-circle" size={16} color="#dc3545" />
                      <Text style={styles.errorText}>{errors.fechaPago}</Text>
                    </View>
                  )}
                </View>

                {/* Observaciones */}
                <View style={styles.inputGroup}>
                  <Text style={styles.label}>Observaciones</Text>
                  <TextInput
                    style={[styles.input, styles.textArea]}
                    value={formData.observaciones}
                    onChangeText={(value) => handleInputChange('observaciones', value)}
                    placeholder="Observaciones adicionales sobre el pago..."
                    multiline
                    numberOfLines={3}
                    textAlignVertical="top"
                    placeholderTextColor="#6c757d"
                  />
                </View>

                {/* Botón de Procesar - AHORA NAVEGA A PAGO MÓVIL */}
                <TouchableOpacity
                  style={styles.submitButton}
                  onPress={handleProcesarPago}
                >
                  <View style={styles.submitButtonContent}>
                    <Icon name="arrow-right" size={20} color="#fff" />
                    <Text style={styles.submitButtonText}>Continuar al Pago</Text>
                  </View>
                </TouchableOpacity>
              </View>
            </ScrollView>
          </View>
        )}
      </KeyboardAvoidingView>
    );
  }

  // Modo automático (desde inscripción) - También actualizado
  return (
    <KeyboardAvoidingView 
      style={styles.container}
      behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
    >
      <ScrollView style={styles.scrollView} contentContainerStyle={styles.scrollContent}>
        <View style={styles.header}>
          <View style={styles.headerContent}>
            <Text style={styles.title}>Procesar Pago</Text>
            <Text style={styles.subtitle}>Complete los datos para registrar el pago</Text>
          </View>
          <View style={styles.headerIcon}>
            <Icon name="credit-card-scan" size={28} color="#4f8cff" />
          </View>
        </View>

        {/* Información de la Nota */}
        {notaData && (
          <View style={styles.infoCard}>
            <View style={styles.infoHeader}>
              <Icon name="file-document" size={18} color="#495057" />
              <Text style={styles.infoTitle}>Información de la Nota</Text>
            </View>
            <View style={styles.infoGrid}>
              <View style={styles.infoItem}>
                <Text style={styles.infoLabel}>Número:</Text>
                <Text style={styles.infoValue}>{notaData.numeroNota}</Text>
              </View>
              <View style={styles.infoItem}>
                <Text style={styles.infoLabel}>Formación:</Text>
                <Text style={styles.infoValue}>{notaData.formacion.nombreFormacion}</Text>
              </View>
              <View style={styles.infoItem}>
                <Text style={styles.infoLabel}>Estudiante:</Text>
                <Text style={styles.infoValue}>{notaData.persona.nombre}</Text>
              </View>
              <View style={styles.infoItem}>
                <Text style={styles.infoLabel}>Cédula:</Text>
                <Text style={styles.infoValue}>{notaData.persona.cedula}</Text>
              </View>
              <View style={[styles.infoItem, styles.totalItem]}>
                <Text style={styles.totalLabel}>Total a Pagar:</Text>
                <Text style={styles.totalValue}>${formatCurrency(notaData.totalNota)}</Text>
              </View>
            </View>
          </View>
        )}

        {/* Formulario de Pago */}
        <View style={styles.formCard}>
          <View style={styles.formTitleContainer}>
            <Icon name="credit-card-outline" size={24} color="#495057" />
            <Text style={styles.formTitle}>Datos del Pago</Text>
          </View>

          {/* Forma de Pago */}
          <View style={styles.inputGroup}>
            <Text style={styles.label}>Forma de Pago *</Text>
            <View style={styles.radioGroup}>
              {['TRANSFERENCIA', 'PAGO_MOVIL'].map((tipo) => (
                <TouchableOpacity
                  key={tipo}
                  style={[
                    styles.radioOption,
                    formData.formaPago === tipo && styles.radioOptionSelected
                  ]}
                  onPress={() => handleInputChange('formaPago', tipo)}
                >
                  <View style={styles.radioContent}>
                    <View style={styles.radioCircle}>
                      {formData.formaPago === tipo && <View style={styles.radioSelected} />}
                    </View>
                    <Text style={[
                      styles.radioLabel,
                      formData.formaPago === tipo && styles.radioLabelSelected
                    ]}>
                      {tipo === 'TRANSFERENCIA' ? 'Transferencia Bancaria' : 'Pago Móvil'}
                    </Text>
                  </View>
                  <Icon 
                    name={tipo === 'TRANSFERENCIA' ? 'bank-transfer' : 'cellphone'} 
                    size={20} 
                    color={formData.formaPago === tipo ? '#4f8cff' : '#6c757d'} 
                  />
                </TouchableOpacity>
              ))}
            </View>
            {errors.formaPago && (
              <View style={styles.errorContainer}>
                <Icon name="alert-circle" size={16} color="#dc3545" />
                <Text style={styles.errorText}>{errors.formaPago}</Text>
              </View>
            )}
          </View>

          {/* Monto */}
          <View style={styles.inputGroup}>
            <Text style={styles.label}>Monto a Pagar *</Text>
            <View style={styles.inputContainer}>
              <Text style={styles.currencySymbol}>$</Text>
              <TextInput
                style={[styles.input, errors.monto && styles.inputError]}
                value={formData.monto}
                onChangeText={(value) => handleInputChange('monto', value)}
                placeholder="0.00"
                keyboardType="numeric"
                placeholderTextColor="#6c757d"
              />
            </View>
            <Text style={styles.helperText}>
              Máximo permitido: <Text style={styles.helperTextBold}>${formatCurrency(notaData.totalNota)}</Text>
            </Text>
            {errors.monto && (
              <View style={styles.errorContainer}>
                <Icon name="alert-circle" size={16} color="#dc3545" />
                <Text style={styles.errorText}>{errors.monto}</Text>
              </View>
            )}
          </View>

          {/* Referencia */}
          <View style={styles.inputGroup}>
            <Text style={styles.label}>Número de Referencia *</Text>
            <TextInput
              style={[styles.input, errors.referencia && styles.inputError]}
              value={formData.referencia}
              onChangeText={(value) => handleInputChange('referencia', value)}
              placeholder="Ej: 123456789"
              maxLength={14}
              keyboardType="numeric"
              placeholderTextColor="#6c757d"
            />
            <Text style={styles.helperText}>
              Número de transacción/transferencia de su banco
            </Text>
            {errors.referencia && (
              <View style={styles.errorContainer}>
                <Icon name="alert-circle" size={16} color="#dc3545" />
                <Text style={styles.errorText}>{errors.referencia}</Text>
              </View>
            )}
          </View>

          {/* Fecha de Pago */}
          <View style={styles.inputGroup}>
            <Text style={styles.label}>Fecha de Pago *</Text>
            <View style={styles.inputContainer}>
              <Icon name="calendar" size={20} color="#6c757d" style={styles.inputIcon} />
              <TextInput
                style={[styles.input, errors.fechaPago && styles.inputError]}
                value={formData.fechaPago}
                onChangeText={(value) => handleInputChange('fechaPago', value)}
                placeholder="AAAA-MM-DD"
                placeholderTextColor="#6c757d"
              />
            </View>
            <Text style={styles.helperText}>Formato: Año-Mes-Día (Ej: 2024-01-15)</Text>
            {errors.fechaPago && (
              <View style={styles.errorContainer}>
                <Icon name="alert-circle" size={16} color="#dc3545" />
                <Text style={styles.errorText}>{errors.fechaPago}</Text>
              </View>
            )}
          </View>

          {/* Observaciones */}
          <View style={styles.inputGroup}>
            <Text style={styles.label}>Observaciones</Text>
            <TextInput
              style={[styles.input, styles.textArea]}
              value={formData.observaciones}
              onChangeText={(value) => handleInputChange('observaciones', value)}
              placeholder="Observaciones adicionales sobre el pago..."
              multiline
              numberOfLines={3}
              textAlignVertical="top"
              placeholderTextColor="#6c757d"
            />
          </View>

          {/* Botón de Procesar - AHORA NAVEGA A PAGO MÓVIL */}
          <TouchableOpacity
            style={styles.submitButton}
            onPress={handleProcesarPago}
          >
            <View style={styles.submitButtonContent}>
              <Icon name="arrow-right" size={20} color="#fff" />
              <Text style={styles.submitButtonText}>Continuar al Pago</Text>
            </View>
          </TouchableOpacity>
        </View>
      </ScrollView>
    </KeyboardAvoidingView>
  );
};

// ESTILOS PROFESIONALES ACTUALIZADOS
const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f8f9fa',
  },
  scrollView: {
    flex: 1,
  },
  scrollContent: {
    flexGrow: 1,
  },
  // Header mejorado
  header: {
    backgroundColor: '#fff',
    padding: 24,
    borderBottomWidth: 1,
    borderBottomColor: '#e9ecef',
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.05,
    shadowRadius: 8,
    elevation: 3,
  },
  headerContent: {
    flex: 1,
  },
  headerIcon: {
    padding: 8,
    backgroundColor: '#f8f9fa',
    borderRadius: 12,
  },
  title: {
    fontSize: 26,
    fontWeight: 'bold',
    color: '#343a40',
    marginBottom: 4,
  },
  subtitle: {
    fontSize: 16,
    color: '#6c757d',
    fontWeight: '500',
  },
  // Lista de notas
  listaContainer: {
    flex: 1,
    padding: 16,
  },
  listaContent: {
    paddingBottom: 20,
  },
  loadingContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    paddingVertical: 60,
  },
  loadingText: {
    marginTop: 12,
    color: '#6c757d',
    fontSize: 16,
    fontWeight: '500',
  },
  emptyContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    paddingVertical: 80,
  },
  emptyText: {
    fontSize: 18,
    color: '#6c757d',
    fontWeight: '600',
    marginTop: 16,
    textAlign: 'center',
  },
  emptySubtext: {
    fontSize: 14,
    color: '#6c757d',
    textAlign: 'center',
    marginTop: 8,
    paddingHorizontal: 40,
    lineHeight: 20,
  },
  // Items de nota
  notaItem: {
    backgroundColor: '#fff',
    padding: 20,
    borderRadius: 12,
    marginBottom: 12,
    borderWidth: 2,
    borderColor: 'transparent',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.08,
    shadowRadius: 6,
    elevation: 3,
  },
  notaItemSeleccionada: {
    borderColor: '#28a745',
    backgroundColor: '#f8fff9',
    shadowColor: '#28a745',
    shadowOpacity: 0.15,
  },
  notaHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 12,
  },
  notaNumero: {
    fontSize: 17,
    fontWeight: 'bold',
    color: '#343a40',
  },
  estadoBadge: {
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 20,
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
    color: '#000',
  },
  notaFormacion: {
    fontSize: 15,
    color: '#495057',
    marginBottom: 12,
    lineHeight: 20,
  },
  notaFooter: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  notaFecha: {
    fontSize: 13,
    color: '#6c757d',
    fontWeight: '500',
  },
  notaMonto: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#28a745',
  },
  seleccionadoIndicator: {
    flexDirection: 'row',
    alignItems: 'center',
    marginTop: 12,
    paddingTop: 12,
    borderTopWidth: 1,
    borderTopColor: '#e9ecef',
  },
  seleccionadoText: {
    marginLeft: 8,
    color: '#28a745',
    fontWeight: '600',
    fontSize: 14,
  },
  // Formulario flotante
  formularioOverlay: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    backgroundColor: 'rgba(0,0,0,0.6)',
  },
  formScrollView: {
    flex: 1,
  },
  formScrollContent: {
    flexGrow: 1,
    justifyContent: 'center',
    padding: 16,
  },
  formCard: {
    backgroundColor: '#fff',
    borderRadius: 16,
    padding: 24,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.15,
    shadowRadius: 12,
    elevation: 8,
  },
  formHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 24,
  },
  formTitleContainer: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  formTitle: {
    fontSize: 22,
    fontWeight: 'bold',
    color: '#343a40',
    marginLeft: 8,
  },
  cancelarBtn: {
    padding: 8,
    borderRadius: 8,
    backgroundColor: '#f8f9fa',
  },
  // Cards de información
  infoCard: {
    backgroundColor: '#fff',
    marginBottom: 24,
    padding: 20,
    borderRadius: 12,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.08,
    shadowRadius: 6,
    elevation: 3,
    borderLeftWidth: 4,
    borderLeftColor: '#4f8cff',
  },
  infoHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 16,
  },
  infoTitle: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#495057',
    marginLeft: 8,
  },
  infoGrid: {
    gap: 12,
  },
  infoItem: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
  },
  totalItem: {
    borderTopWidth: 1,
    borderTopColor: '#e9ecef',
    paddingTop: 12,
    marginTop: 4,
  },
  infoLabel: {
    fontSize: 14,
    color: '#6c757d',
    fontWeight: '500',
    flex: 1,
  },
  infoValue: {
    fontSize: 14,
    color: '#495057',
    fontWeight: '400',
    flex: 2,
    textAlign: 'right',
  },
  totalLabel: {
    fontSize: 16,
    fontWeight: 'bold',
    color: '#495057',
    flex: 1,
  },
  totalValue: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#28a745',
    flex: 2,
    textAlign: 'right',
  },
  // Grupos de input
  inputGroup: {
    marginBottom: 24,
  },
  label: {
    fontSize: 16,
    fontWeight: '600',
    color: '#495057',
    marginBottom: 12,
  },
  inputContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    borderWidth: 1,
    borderColor: '#ced4da',
    borderRadius: 8,
    backgroundColor: '#fff',
  },
  currencySymbol: {
    fontSize: 16,
    fontWeight: '600',
    color: '#495057',
    paddingHorizontal: 12,
    backgroundColor: '#f8f9fa',
    borderRightWidth: 1,
    borderRightColor: '#ced4da',
    height: 48,
    textAlignVertical: 'center',
  },
  inputIcon: {
    paddingHorizontal: 12,
  },
  input: {
    flex: 1,
    padding: 12,
    fontSize: 16,
    color: '#495057',
    minHeight: 48,
  },
  inputError: {
    borderColor: '#dc3545',
  },
  textArea: {
    height: 100,
    textAlignVertical: 'top',
  },
  helperText: {
    fontSize: 13,
    color: '#6c757d',
    marginTop: 6,
  },
  helperTextBold: {
    fontWeight: '600',
    color: '#495057',
  },
  // Radio buttons mejorados
  radioGroup: {
    gap: 12,
  },
  radioOption: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    padding: 16,
    borderWidth: 2,
    borderColor: '#e9ecef',
    borderRadius: 12,
    backgroundColor: '#fff',
  },
  radioOptionSelected: {
    borderColor: '#4f8cff',
    backgroundColor: '#f0f7ff',
  },
  radioContent: {
    flexDirection: 'row',
    alignItems: 'center',
    flex: 1,
  },
  radioCircle: {
    height: 24,
    width: 24,
    borderRadius: 12,
    borderWidth: 2,
    borderColor: '#ced4da',
    alignItems: 'center',
    justifyContent: 'center',
    marginRight: 12,
  },
  radioSelected: {
    height: 12,
    width: 12,
    borderRadius: 6,
    backgroundColor: '#4f8cff',
  },
  radioLabel: {
    fontSize: 16,
    color: '#495057',
    fontWeight: '500',
  },
  radioLabelSelected: {
    color: '#4f8cff',
    fontWeight: '600',
  },
  // Errores
  errorContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    marginTop: 6,
  },
  errorText: {
    fontSize: 13,
    color: '#dc3545',
    marginLeft: 6,
    fontWeight: '500',
  },
  // Botón de enviar
  submitButton: {
    backgroundColor: '#28a745',
    padding: 16,
    borderRadius: 12,
    alignItems: 'center',
    marginTop: 8,
    shadowColor: '#28a745',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.3,
    shadowRadius: 8,
    elevation: 4,
  },
  submitButtonDisabled: {
    backgroundColor: '#6c757d',
    shadowColor: '#6c757d',
  },
  submitButtonContent: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  submitButtonText: {
    color: '#fff',
    fontSize: 18,
    fontWeight: 'bold',
    marginLeft: 8,
  },
});

export default PagoScreen;