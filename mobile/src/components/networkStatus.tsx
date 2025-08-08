// src/components/networkStatus.js
import { useEffect } from 'react';
import { Alert } from 'react-native';
import NetInfo from '@react-native-community/netinfo';

const NetworkStatus = () => {
  useEffect(() => {
    const unsubscribe = NetInfo.addEventListener((state) => {
      if (!state.isConnected) {
        Alert.alert('Sin conexión', 'La aplicación funcionará en modo offline', [{ text: 'OK' }]);
      }
    });

    return () => unsubscribe();
  }, []);

  return null;
};

export default NetworkStatus;
