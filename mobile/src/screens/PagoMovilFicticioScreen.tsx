// src/screens/PagoMovilFicticioScreen.tsx
import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  TouchableOpacity,
  Alert,
  Image,
  StyleSheet,
  ScrollView,
  ActivityIndicator,
} from 'react-native';
import * as ImagePicker from 'react-native-image-picker';
import Icon from 'react-native-vector-icons/MaterialCommunityIcons';
import { useRoute, useNavigation } from '@react-navigation/native';

// Definimos los tipos para los parámetros
interface PagoMovilParams {
  monto: number;
  referencia: string;
  formaPago: string;
  notaData?: {
    idNota: number;
    numeroNota: string;
    totalNota: number;
    persona?: {
      nombre: string;
      cedula: string;
    };
  };
  userData?: {
    nombre: string;
    cedula: string;
    telefono?: string;
    bancoPreferido?: string;
  };
}

// Datos de bancos para Venezuela
const BANCOS_VENEZUELA = [
  { nombre: 'Banco de Venezuela', codigo: '0102' },
  { nombre: 'Banesco', codigo: '0134' },
  { nombre: 'Mercantil', codigo: '0105' },
  { nombre: 'Provincial', codigo: '0108' },
  { nombre: 'Bancaribe', codigo: '0114' },
  { nombre: 'Banco Bicentenario', codigo: '0175' },
  { nombre: 'Banco Fondo Común', codigo: '0151' },
  { nombre: 'Banco Plaza', codigo: '0138' },
  { nombre: 'Banco Exterior', codigo: '0115' },
  { nombre: 'Banco Occidental de Descuento', codigo: '0116' },
];

const PagoMovilFicticioScreen = () => {
  const route = useRoute();
  const navigation = useNavigation();
  const params = route.params as PagoMovilParams;
  
  const [image, setImage] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [datosUsuario, setDatosUsuario] = useState({
    telefono: '0412-1234567',
    banco: 'Banco de Venezuela',
    cedula: 'V-12345678',
  });

  // Inicializar con datos reales del usuario
  useEffect(() => {
    if (params?.userData) {
      setDatosUsuario(prev => ({
        ...prev,
        cedula: params.userData?.cedula || prev.cedula,
        telefono: params.userData?.telefono || prev.telefono,
        banco: params.userData?.bancoPreferido || prev.banco,
      }));
    }
  }, [params]);

  const seleccionarImagen = () => {
    ImagePicker.launchImageLibrary(
      {
        mediaType: 'photo',
        includeBase64: false,
        maxHeight: 200,
        maxWidth: 200,
      },
      (response) => {
        if (response.didCancel) {
          console.log('Usuario canceló la selección');
        } else if (response.errorCode) {
          console.log('Error: ', response.errorMessage);
        } else {
          if (response.assets && response.assets[0].uri) {
            setImage(response.assets[0].uri);
          }
        }
      },
    );
  };

  const procesarPagoFicticio = () => {
    if (!image) {
      Alert.alert('Error', 'Por favor sube una captura del comprobante de pago');
      return;
    }

    setLoading(true);

    // Simulamos un envío al servidor con un timeout
    setTimeout(() => {
      setLoading(false);
      Alert.alert(
        '¡Pago Enviado! 🎉',
        `Su pago de $${params?.monto || '0.00'} está pendiente por confirmación.\n\nLe notificaremos cuando sea procesado.`,
        [
          {
            text: 'Aceptar',
            onPress: () => {
              // Navegar de regreso o a la pantalla de confirmación
              navigation.goBack();
            },
          },
        ],
      );
    }, 2000);
  };

  const formatCurrency = (amount: number): string => {
    return new Intl.NumberFormat('es-VE', {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2
    }).format(amount);
  };

  const cambiarBanco = () => {
    Alert.alert(
      'Seleccionar Banco',
      'Elija su banco para Pago Móvil',
      BANCOS_VENEZUELA.map(banco => ({
        text: banco.nombre,
        onPress: () => setDatosUsuario(prev => ({ ...prev, banco: banco.nombre }))
      }))
    );
  };

  const cambiarTelefono = () => {
    Alert.prompt(
      'Número de Teléfono',
      'Ingrese su número para Pago Móvil',
      [
        { text: 'Cancelar', style: 'cancel' },
        {
          text: 'OK',
          onPress: (telefono: any) => {
            if (telefono) {
              setDatosUsuario(prev => ({ ...prev, telefono }));
            }
          },
        },
      ],
      'plain-text',
      datosUsuario.telefono
    );
  };

  return (
    <ScrollView style={styles.container}>
      <View style={styles.header}>
        <Icon name="cellphone" size={40} color="#4f8cff" />
        <Text style={styles.title}>Pago Móvil</Text>
        <Text style={styles.subtitle}>
          Complete los datos y suba el comprobante de pago
        </Text>
      </View>

      <View style={styles.formCard}>
        {/* Información del pago con datos reales */}
        <View style={styles.infoSection}>
          <Text style={styles.sectionTitle}>Información de Pago</Text>
          
          <View style={styles.infoRow}>
            <Text style={styles.infoLabel}>Nota de Cobro:</Text>
            <Text style={styles.infoValue}>
              {params?.notaData?.numeroNota || 'N/A'}
            </Text>
          </View>
          
          {params?.notaData?.persona && (
            <View style={styles.infoRow}>
              <Text style={styles.infoLabel}>Estudiante:</Text>
              <Text style={styles.infoValue}>
                {params.notaData.persona.nombre}
              </Text>
            </View>
          )}
          
          <TouchableOpacity style={styles.infoRow} onPress={cambiarBanco}>
            <Text style={styles.infoLabel}>Banco Emisor:</Text>
            <View style={styles.editableField}>
              <Text style={styles.infoValue}>{datosUsuario.banco}</Text>
              <Icon name="pencil" size={16} color="#4f8cff" />
            </View>
          </TouchableOpacity>
          
          <TouchableOpacity style={styles.infoRow} onPress={cambiarTelefono}>
            <Text style={styles.infoLabel}>Teléfono:</Text>
            <View style={styles.editableField}>
              <Text style={styles.infoValue}>{datosUsuario.telefono}</Text>
              <Icon name="pencil" size={16} color="#4f8cff" />
            </View>
          </TouchableOpacity>
          
          <View style={styles.infoRow}>
            <Text style={styles.infoLabel}>Cédula:</Text>
            <Text style={styles.infoValue}>{datosUsuario.cedula}</Text>
          </View>
          
          <View style={styles.infoRow}>
            <Text style={styles.infoLabel}>Monto a Pagar:</Text>
            <Text style={[styles.infoValue, styles.montoText]}>
              ${formatCurrency(params?.monto || 0)}
            </Text>
          </View>
          
          <View style={styles.infoRow}>
            <Text style={styles.infoLabel}>Referencia:</Text>
            <Text style={styles.infoValue}>
              {params?.referencia || 'Por generar'}
            </Text>
          </View>
        </View>

        {/* Instrucciones para Pago Móvil */}
        <View style={styles.instructionsSection}>
          <Text style={styles.sectionTitle}>Instrucciones para Pagar</Text>
          
          <View style={styles.instructionStep}>
            <View style={styles.stepNumber}>
              <Text style={styles.stepNumberText}>1</Text>
            </View>
            <Text style={styles.instructionText}>
              Abra la aplicación de su banco ({datosUsuario.banco})
            </Text>
          </View>
          
          <View style={styles.instructionStep}>
            <View style={styles.stepNumber}>
              <Text style={styles.stepNumberText}>2</Text>
            </View>
            <Text style={styles.instructionText}>
              Seleccione la opción "Pago Móvil"
            </Text>
          </View>
          
          <View style={styles.instructionStep}>
            <View style={styles.stepNumber}>
              <Text style={styles.stepNumberText}>3</Text>
            </View>
            <Text style={styles.instructionText}>
              Ingrese los siguientes datos:
            </Text>
          </View>
          
          <View style={styles.paymentDetails}>
            <View style={styles.detailRow}>
              <Text style={styles.detailLabel}>Banco Destino:</Text>
              <Text style={styles.detailValue}>Banco de Venezuela</Text>
            </View>
            <View style={styles.detailRow}>
              <Text style={styles.detailLabel}>Teléfono Destino:</Text>
              <Text style={styles.detailValue}>0414-1234567</Text>
            </View>
            <View style={styles.detailRow}>
              <Text style={styles.detailLabel}>Cédula Destino:</Text>
              <Text style={styles.detailValue}>V-12345678</Text>
            </View>
            <View style={styles.detailRow}>
              <Text style={styles.detailLabel}>Monto:</Text>
              <Text style={styles.detailValue}>
                ${formatCurrency(params?.monto || 0)}
              </Text>
            </View>
          </View>
        </View>

        {/* Selector de imagen */}
        <View style={styles.uploadSection}>
          <Text style={styles.sectionTitle}>Comprobante de Pago</Text>
          <Text style={styles.uploadDescription}>
            Tome una captura de pantalla del comprobante de pago móvil y súbala aquí
          </Text>

          <TouchableOpacity
            style={styles.uploadButton}
            onPress={seleccionarImagen}
          >
            <Icon name="camera" size={24} color="#4f8cff" />
            <Text style={styles.uploadButtonText}>
              {image ? 'Cambiar Imagen' : 'Seleccionar Imagen'}
            </Text>
          </TouchableOpacity>

          {image && (
            <View style={styles.imagePreview}>
              <Image source={{ uri: image }} style={styles.image} />
              <TouchableOpacity
                style={styles.deleteImageButton}
                onPress={() => setImage(null)}
              >
                <Icon name="close" size={20} color="#fff" />
              </TouchableOpacity>
            </View>
          )}
        </View>

        {/* Botón de enviar */}
        <TouchableOpacity
          style={[styles.submitButton, loading && styles.submitButtonDisabled]}
          onPress={procesarPagoFicticio}
          disabled={loading}
        >
          {loading ? (
            <ActivityIndicator color="#fff" size="small" />
          ) : (
            <>
              <Icon name="check-circle" size={20} color="#fff" />
              <Text style={styles.submitButtonText}>Enviar Comprobante</Text>
            </>
          )}
        </TouchableOpacity>

        {/* Información adicional */}
        <View style={styles.noteSection}>
          <Icon name="information" size={20} color="#6c757d" />
          <Text style={styles.noteText}>
            Su pago será verificado en un plazo de 24-48 horas. Recibirá una notificación cuando sea confirmado.
          </Text>
        </View>
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
    padding: 24,
    alignItems: 'center',
    borderBottomWidth: 1,
    borderBottomColor: '#e9ecef',
  },
  title: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#343a40',
    marginTop: 12,
    marginBottom: 4,
  },
  subtitle: {
    fontSize: 16,
    color: '#6c757d',
    textAlign: 'center',
  },
  formCard: {
    backgroundColor: '#fff',
    margin: 16,
    padding: 20,
    borderRadius: 12,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 6,
    elevation: 3,
  },
  infoSection: {
    marginBottom: 24,
  },
  sectionTitle: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#495057',
    marginBottom: 16,
  },
  infoRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: 8,
    borderBottomWidth: 1,
    borderBottomColor: '#f1f3f4',
  },
  infoLabel: {
    fontSize: 16,
    color: '#6c757d',
    fontWeight: '500',
  },
  infoValue: {
    fontSize: 16,
    color: '#495057',
    fontWeight: '600',
  },
  montoText: {
    color: '#28a745',
    fontWeight: 'bold',
  },
  editableField: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  instructionsSection: {
    marginBottom: 24,
    backgroundColor: '#f8f9fa',
    padding: 16,
    borderRadius: 8,
  },
  instructionStep: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    marginBottom: 12,
  },
  stepNumber: {
    backgroundColor: '#4f8cff',
    width: 24,
    height: 24,
    borderRadius: 12,
    alignItems: 'center',
    justifyContent: 'center',
    marginRight: 12,
    marginTop: 2,
  },
  stepNumberText: {
    color: '#fff',
    fontWeight: 'bold',
    fontSize: 12,
  },
  instructionText: {
    flex: 1,
    fontSize: 14,
    color: '#495057',
    lineHeight: 20,
  },
  paymentDetails: {
    backgroundColor: '#fff',
    padding: 12,
    borderRadius: 6,
    marginTop: 8,
    borderLeftWidth: 4,
    borderLeftColor: '#4f8cff',
  },
  detailRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginBottom: 4,
  },
  detailLabel: {
    fontSize: 14,
    color: '#6c757d',
    fontWeight: '500',
  },
  detailValue: {
    fontSize: 14,
    color: '#495057',
    fontWeight: '600',
  },
  uploadSection: {
    marginBottom: 24,
  },
  uploadDescription: {
    fontSize: 14,
    color: '#6c757d',
    marginBottom: 16,
    lineHeight: 20,
  },
  uploadButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: '#f8f9fa',
    borderWidth: 2,
    borderColor: '#4f8cff',
    borderStyle: 'dashed',
    borderRadius: 8,
    padding: 16,
    marginBottom: 16,
  },
  uploadButtonText: {
    fontSize: 16,
    color: '#4f8cff',
    fontWeight: '600',
    marginLeft: 8,
  },
  imagePreview: {
    position: 'relative',
    alignItems: 'center',
  },
  image: {
    width: 200,
    height: 200,
    borderRadius: 8,
  },
  deleteImageButton: {
    position: 'absolute',
    top: -10,
    right: -10,
    backgroundColor: '#dc3545',
    borderRadius: 12,
    width: 24,
    height: 24,
    alignItems: 'center',
    justifyContent: 'center',
  },
  submitButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: '#28a745',
    padding: 16,
    borderRadius: 8,
    marginBottom: 16,
  },
  submitButtonDisabled: {
    backgroundColor: '#6c757d',
  },
  submitButtonText: {
    color: '#fff',
    fontSize: 18,
    fontWeight: 'bold',
    marginLeft: 8,
  },
  noteSection: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    backgroundColor: '#e7f3ff',
    padding: 12,
    borderRadius: 8,
  },
  noteText: {
    flex: 1,
    fontSize: 14,
    color: '#6c757d',
    marginLeft: 8,
    lineHeight: 18,
  },
});

export default PagoMovilFicticioScreen;