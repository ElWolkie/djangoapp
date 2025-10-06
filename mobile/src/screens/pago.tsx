// src/screens/PagoScreen.tsx
import React, { useState } from 'react';
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  ScrollView,
  Alert,
  ActivityIndicator,
  StyleSheet
} from 'react-native';
import { useNavigation, useRoute } from '@react-navigation/native';
import api from '../api/api';

// Usar any temporalmente para evitar problemas de tipos
const PagoScreen = () => {
  const navigation = useNavigation<any>();
  const route = useRoute<any>();
  
  const { notaData, inscripcionId } = route.params;
  
  const [loading, setLoading] = useState(false);
  const [formData, setFormData] = useState({
    idNota: notaData.idNota,
    formaPago: 'TRANSFERENCIA',
    monto: notaData.totalNota.toString(),
    referencia: '',
    observaciones: '',
    fechaPago: new Date().toISOString().split('T')[0]
  });

  const [errors, setErrors] = useState<{[key: string]: string}>({});

  // Validar formulario
  const validateForm = (): boolean => {
    const newErrors: {[key: string]: string} = {};

    if (!formData.formaPago) {
      newErrors.formaPago = 'Seleccione forma de pago';
    }

    if (!formData.monto || parseFloat(formData.monto) <= 0) {
      newErrors.monto = 'Monto debe ser mayor a 0';
    } else if (parseFloat(formData.monto) > notaData.totalNota) {
      newErrors.monto = `Monto no puede ser mayor a ${notaData.totalNota}`;
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
        idNota: formData.idNota,
        formaPago: formData.formaPago,
        monto: parseFloat(formData.monto),
        referencia: formData.referencia,
        observaciones: formData.observaciones,
        fechaPago: formData.fechaPago,
        idTasa: 1, // Moneda base fija (ID=1)
        idCuentaBanco: null // Se determinará en el backend según la forma de pago
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
              onPress: () => navigation.navigate('Inscripciones')
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

  return (
    <ScrollView style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.title}>Procesar Pago</Text>
        <Text style={styles.subtitle}>Complete los datos para registrar el pago</Text>
      </View>

      {/* Información de la Nota */}
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
  formCard: {
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